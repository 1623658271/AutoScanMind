"""
SQLite 元数据数据库操作层
存储图片元信息、OCR 文字内容、索引状态
"""
from __future__ import annotations

import sqlite3
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DB_PATH


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT    NOT NULL UNIQUE,
    file_name   TEXT    NOT NULL,
    file_size   INTEGER NOT NULL DEFAULT 0,
    mtime       REAL    NOT NULL DEFAULT 0,
    hash        TEXT    NOT NULL DEFAULT '',
    ocr_text    TEXT    NOT NULL DEFAULT '',
    indexed_at  REAL    NOT NULL DEFAULT 0,
    width       INTEGER NOT NULL DEFAULT 0,
    height      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_images_path ON images(path);
CREATE INDEX IF NOT EXISTS idx_images_indexed_at ON images(indexed_at);
"""


class MetadataDB:
    """SQLite 元数据数据库（线程安全，单例模式）。"""

    _instance: "MetadataDB | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "MetadataDB":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._conn_lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        logger.info("MetadataDB 初始化")

    def connect(self) -> None:
        """初始化数据库连接并建表。"""
        if self._conn is not None:
            return
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                str(DB_PATH),
                check_same_thread=False,
                timeout=30,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.executescript(CREATE_TABLE_SQL)
            self._conn.commit()
            logger.success(f"数据库连接已建立: {DB_PATH}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """获取线程安全的游标上下文。"""
        if self._conn is None:
            self.connect()
        with self._conn_lock:
            cursor = self._conn.cursor()
            try:
                yield cursor
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            finally:
                cursor.close()

    # ── CRUD ─────────────────────────────────────────────────────
    def upsert(
        self,
        path: str,
        file_name: str,
        file_size: int,
        mtime: float,
        hash_: str,
        ocr_text: str,
        indexed_at: float,
        width: int = 0,
        height: int = 0,
    ) -> None:
        """插入或更新一条图片元数据记录。"""
        sql = """
        INSERT INTO images
            (path, file_name, file_size, mtime, hash, ocr_text, indexed_at, width, height)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            file_name  = excluded.file_name,
            file_size  = excluded.file_size,
            mtime      = excluded.mtime,
            hash       = excluded.hash,
            ocr_text   = excluded.ocr_text,
            indexed_at = excluded.indexed_at,
            width      = excluded.width,
            height     = excluded.height
        """
        with self._cursor() as cur:
            cur.execute(sql, (path, file_name, file_size, mtime, hash_,
                              ocr_text, indexed_at, width, height))

    def upsert_batch(self, records: List[Dict]) -> None:
        """批量插入/更新图片元数据。

        records 中每项应包含 upsert 方法所需的键。
        """
        sql = """
        INSERT INTO images
            (path, file_name, file_size, mtime, hash, ocr_text, indexed_at, width, height)
        VALUES
            (:path, :file_name, :file_size, :mtime, :hash, :ocr_text, :indexed_at, :width, :height)
        ON CONFLICT(path) DO UPDATE SET
            file_name  = excluded.file_name,
            file_size  = excluded.file_size,
            mtime      = excluded.mtime,
            hash       = excluded.hash,
            ocr_text   = excluded.ocr_text,
            indexed_at = excluded.indexed_at,
            width      = excluded.width,
            height     = excluded.height
        """
        with self._cursor() as cur:
            cur.executemany(sql, records)

    def get(self, path: str) -> Optional[sqlite3.Row]:
        """根据路径获取记录。"""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM images WHERE path = ?", (path,))
            return cur.fetchone()

    def get_mtime(self, path: str) -> Optional[float]:
        """快速获取文件 mtime（用于增量检测）。"""
        with self._cursor() as cur:
            cur.execute("SELECT mtime FROM images WHERE path = ?", (path,))
            row = cur.fetchone()
            return float(row["mtime"]) if row else None

    def get_hash(self, path: str) -> Optional[str]:
        """快速获取文件哈希（用于增量检测）。"""
        with self._cursor() as cur:
            cur.execute("SELECT hash FROM images WHERE path = ?", (path,))
            row = cur.fetchone()
            return row["hash"] if row else None

    def get_ocr_text(self, path: str) -> str:
        """获取图片 OCR 文字。"""
        with self._cursor() as cur:
            cur.execute("SELECT ocr_text FROM images WHERE path = ?", (path,))
            row = cur.fetchone()
            return row["ocr_text"] if row else ""

    def delete(self, path: str) -> bool:
        """删除指定路径的记录。"""
        with self._cursor() as cur:
            cur.execute("DELETE FROM images WHERE path = ?", (path,))
            return cur.rowcount > 0

    def delete_batch(self, paths: List[str]) -> int:
        """批量删除记录，返回删除数量。"""
        with self._cursor() as cur:
            placeholders = ",".join("?" * len(paths))
            cur.execute(f"DELETE FROM images WHERE path IN ({placeholders})", paths)
            return cur.rowcount

    def count(self) -> int:
        """返回已索引图片总数。"""
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM images")
            return cur.fetchone()[0]

    def all_paths(self) -> List[str]:
        """返回所有已索引图片路径。"""
        with self._cursor() as cur:
            cur.execute("SELECT path FROM images")
            return [row["path"] for row in cur.fetchall()]

    def get_by_paths(self, paths: List[str]) -> List[sqlite3.Row]:
        """批量根据路径获取元数据。"""
        if not paths:
            return []
        placeholders = ",".join("?" * len(paths))
        with self._cursor() as cur:
            cur.execute(
                f"SELECT * FROM images WHERE path IN ({placeholders})", paths
            )
            return cur.fetchall()

    def get_all_metadata(self) -> List[sqlite3.Row]:
        """返回所有图片的完整元数据记录。"""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM images")
            return cur.fetchall()

    def delete_all(self) -> None:
        """清空所有图片记录。"""
        with self._cursor() as cur:
            cur.execute("DELETE FROM images")

    def close(self) -> None:
        """关闭数据库连接。"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("数据库连接已关闭")
