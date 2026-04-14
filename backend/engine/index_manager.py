"""
索引管理器（IndexManager）
协调扫描器、CLIP 引擎、OCR 引擎、FAISS 索引、文字索引和数据库，
在后台线程中完成图片索引构建与增量更新。
"""
from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import CLIP_BATCH_SIZE
from backend.db.metadata_db import MetadataDB
from backend.engine.clip_engine import CLIPEngine
from backend.engine.faiss_store import FAISSStore
from backend.engine.ocr_engine import OCREngine
from backend.engine.scanner import FileScanner, compute_file_hash
from backend.engine.text_index import TextIndex
from backend.pretrained.schemas import IndexProgressInfo, IndexStatus


def _count_images_in_dir(
    directory: str,
    extensions: set,
    exclude_dirs: set,
    _depth: int = 0,
    _max_depth: int = 30,
) -> int:
    """
    递归统计指定目录下的图片文件总数（仅计数，不计算哈希）。

    Args:
        directory: 要扫描的目录路径
        extensions: 支持的图片扩展名集合（小写，含点号）
        exclude_dirs: 要排除的目录名集合
        _depth: 当前递归深度（内部使用）
        _max_depth: 最大递归深度，防止栈溢出

    Returns:
        图片文件数量
    """
    count = 0
    try:
        base = Path(directory)
        if not base.exists() or not base.is_dir():
            return 0
        if _depth >= _max_depth:
            return 0
        with os.scandir(base) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name in exclude_dirs or entry.name.startswith("."):
                            continue
                        count += _count_images_in_dir(entry.path, extensions, exclude_dirs, _depth + 1, _max_depth)
                    elif entry.is_file(follow_symlinks=False):
                        if Path(entry.path).suffix.lower() in extensions:
                            count += 1
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    return count


class IndexManager:
    """索引管理器：单例，线程安全。"""

    _instance: "IndexManager | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "IndexManager":
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

        self.db = MetadataDB()
        self.clip = CLIPEngine()
        self.ocr = OCREngine()
        self.faiss = FAISSStore()
        self.text = TextIndex()
        self.scanner = FileScanner()

        self._progress = IndexProgressInfo()
        self._progress_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._last_update_time: str = ""
        logger.info("IndexManager 初始化完成")

    # ── 进度管理 ─────────────────────────────────────────────────
    def get_progress(self) -> IndexProgressInfo:
        with self._progress_lock:
            info = self._progress.model_copy()
            info.indexed_count = self.faiss.total
            info.last_update_time = self._last_update_time
            return info

    def _set_status(self, status: IndexStatus, **kwargs) -> None:
        with self._progress_lock:
            self._progress.status = status
            for k, v in kwargs.items():
                setattr(self._progress, k, v)

    # ── 初始化存储 ───────────────────────────────────────────────
    def initialize(self) -> None:
        """启动时初始化所有存储（加载已有索引）。"""
        self.db.connect()
        self.faiss.load_or_create()
        self.text.load_or_create()
        self._check_consistency()
        self._auto_index_if_needed()
        logger.success("IndexManager 存储初始化完成")

    def _check_consistency(self) -> None:
        """检测 DB 与 FAISS 索引的一致性，不一致时自动修复。"""
        db_count = self.db.count()
        faiss_count = self.faiss.total

        if db_count > 0 and faiss_count == 0:
            logger.warning(
                f"数据一致性异常：DB 有 {db_count} 条记录但 FAISS 索引为空，"
                "将从数据库重新构建索引…"
            )
            self._rebuild_from_db()

    def _auto_index_if_needed(self) -> None:
        """DB 和 FAISS 均为空时，自动触发一次索引（如果有配置扫描目录）。"""
        db_count = self.db.count()
        faiss_count = self.faiss.total

        if db_count > 0 or faiss_count > 0:
            return  # 已有数据，无需自动索引

        try:
            from backend.api.settings import get_settings_obj
            settings = get_settings_obj()
            dirs = settings.scan_directories
            if not dirs:
                return

            logger.info("检测到索引为空且已配置扫描目录，自动启动索引…")
            self.start_indexing(
                directories=dirs,
                full_rebuild=False,
                ocr_enabled=settings.ocr_enabled,
            )
        except Exception as e:
            logger.warning(f"自动索引启动失败: {e}")

    def _rebuild_from_db(self) -> None:
        """从数据库已有记录重建 FAISS 向量索引和文字索引（无需重新 OCR）。"""
        try:
            self.clip.load()

            rows = self.db.get_all_metadata()
            if not rows:
                logger.info("数据库无有效记录，跳过重建")
                return

            paths = [r["path"] for r in rows if Path(r["path"]).exists()]
            if not paths:
                logger.warning("数据库中的图片文件均不存在，无法重建索引")
                # 清理无效的数据库记录
                self.db.delete_all()
                return

            logger.info(f"从数据库重建索引：{len(paths)} 张图片")
            for i in range(0, len(paths), CLIP_BATCH_SIZE):
                batch = paths[i : i + CLIP_BATCH_SIZE]
                clip_vectors = self.clip.encode_images(batch)
                self.faiss.add_batch(batch, clip_vectors)

                # 从数据库已有的 OCR 文字恢复文字索引
                row_map = {r["path"]: r for r in rows}
                texts = [row_map.get(p, {}).get("ocr_text", "") for p in batch]
                self.text.add_batch(batch, texts)

            self.faiss.save()
            self.text.save()
            self._last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.success(f"索引重建完成：{self.faiss.total} 张图片")
        except Exception as e:
            logger.error(f"从数据库重建索引失败: {e}")

    # ── 开始索引 ─────────────────────────────────────────────────
    def start_indexing(
        self,
        directories: List[str],
        full_rebuild: bool = False,
        ocr_enabled: bool = True,
    ) -> bool:
        """
        在后台线程中开始索引（已在运行中则返回 False）。

        Args:
            directories: 要扫描的目录列表
            full_rebuild: 是否全量重建（清空现有索引）
            ocr_enabled: 是否启用 OCR

        Returns:
            True 表示成功启动，False 表示已有任务正在运行
        """
        with self._progress_lock:
            if self._progress.status in (IndexStatus.SCANNING, IndexStatus.INDEXING, IndexStatus.SAVING):
                logger.warning("索引任务已在运行中，忽略本次启动请求")
                return False

        self.scanner.reset_stop()
        # 记录当前正在索引的目录（前端可用于恢复进度和提示）
        self._set_status(IndexStatus.IDLE, indexing_directories=directories)
        self._thread = threading.Thread(
            target=self._index_worker,
            args=(directories, full_rebuild, ocr_enabled),
            daemon=True,
            name="index-worker",
        )
        self._thread.start()
        logger.info(f"索引任务已启动，目录: {directories}，全量重建: {full_rebuild}")
        return True

    def stop_indexing(self) -> None:
        """请求停止正在进行的索引任务。"""
        self.scanner.stop()
        logger.info("已发送索引停止信号")

    def purge_by_directory(self, directory: str) -> int:
        """
        清理指定目录下所有已索引文件（从 DB、FAISS、TextIndex 中移除）。

        Args:
            directory: 要清理的目录路径

        Returns:
            被清理的文件数量
        """
        root = str(Path(directory).resolve()).lower()
        all_indexed = self.db.all_paths()
        to_remove = [
            p for p in all_indexed
            if str(Path(p).resolve()).lower().startswith(root)
        ]

        if not to_remove:
            return 0

        logger.info(f"清理目录 {directory} 下的 {len(to_remove)} 个索引文件…")
        for p in to_remove:
            self.faiss.remove(p)
        self.text.remove_batch(to_remove)
        self.db.delete_batch(to_remove)
        self.faiss.save()
        self.text.save()
        logger.success(f"已清理 {len(to_remove)} 个文件的索引")
        return len(to_remove)

    def get_indexed_directories(self) -> List[dict]:
        """
        统计当前索引中各目录的图片数量，以及该目录下实际的图片文件总数。

        Returns:
            [{"directory": "...", "count": N, "total_images": M}, ...] 按 count 降序
        """
        from collections import Counter
        from config import SUPPORTED_EXTENSIONS, SCAN_EXCLUDE_DIRS

        all_paths = self.db.all_paths()
        dir_counter: Counter = Counter()
        for p in all_paths:
            try:
                parent = str(Path(p).parent)
                dir_counter[parent] += 1
            except Exception:
                pass

        result = []
        for d, c in dir_counter.most_common():
            # 快速统计该目录下实际图片文件总数（递归，仅计数不计算哈希）
            total = _count_images_in_dir(d, SUPPORTED_EXTENSIONS, SCAN_EXCLUDE_DIRS)
            result.append({"directory": d, "count": c, "total_images": total})
        return result

    # ── 后台工作线程 ─────────────────────────────────────────────
    def _index_worker(
        self,
        directories: List[str],
        full_rebuild: bool,
        ocr_enabled: bool,
    ) -> None:
        """后台索引工作线程主函数。"""
        try:
            if full_rebuild:
                logger.info("全量重建：清空现有索引")
                self.faiss.rebuild()
                self.text.rebuild()

            # ── 阶段 1：扫描变更文件 ────────────────────────────
            self._set_status(IndexStatus.SCANNING, current_file="扫描文件中...")
            logger.info("开始扫描文件变更...")

            changes = self.scanner.detect_changes(
                directories=directories,
                get_known_mtime=self.db.get_mtime,
                get_known_hash=self.db.get_hash,
            )
            to_process = changes["new"] + changes["modified"]
            total = len(to_process)
            logger.info(f"扫描完成：新增 {len(changes['new'])} | 变更 {len(changes['modified'])} | 扫描总数 {changes['total_scanned']}")

            if total == 0:
                self._set_status(
                    IndexStatus.COMPLETED,
                    total_files=0,
                    processed_files=0,
                    progress_pct=100.0,
                    indexing_directories=[],
                )
                self._last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.success("无需更新，索引已是最新状态")
                return

            # ── 阶段 2：批量提取特征 ─────────────────────────────
            self._set_status(
                IndexStatus.INDEXING,
                total_files=total,
                processed_files=0,
                progress_pct=0.0,
            )

            # 预加载模型
            logger.info("加载 CLIP 模型...")
            self.clip.load()
            if ocr_enabled:
                logger.info("加载 OCR 模型...")
                self.ocr.load()

            processed = 0
            for i in range(0, total, CLIP_BATCH_SIZE):
                if self.scanner.is_stopped:
                    logger.info("索引任务已被用户中止")
                    self._set_status(IndexStatus.IDLE, indexing_directories=[])
                    return

                batch_paths = to_process[i : i + CLIP_BATCH_SIZE]
                self._set_status(
                    IndexStatus.INDEXING,
                    current_file=Path(batch_paths[0]).name,
                    processed_files=processed,
                    progress_pct=round(processed / total * 100, 1),
                )

                # 提取 CLIP 特征
                clip_vectors = self.clip.encode_images(batch_paths)

                # OCR 文字提取
                ocr_texts: List[str]
                if ocr_enabled:
                    ocr_texts = self.ocr.extract_text_batch(batch_paths)
                else:
                    ocr_texts = [""] * len(batch_paths)

                # 写入 FAISS 向量索引
                self.faiss.add_batch(batch_paths, clip_vectors)

                # 写入文字索引
                self.text.add_batch(batch_paths, ocr_texts)

                # 写入数据库元数据
                db_records = []
                for path, ocr_text in zip(batch_paths, ocr_texts):
                    try:
                        stat = os.stat(path)
                        p = Path(path)
                        # 获取图片尺寸
                        width, height = 0, 0
                        try:
                            from PIL import Image as PILImage
                            with PILImage.open(path) as img:
                                width, height = img.size
                        except Exception:
                            pass
                        db_records.append({
                            "path": path,
                            "file_name": p.name,
                            "file_size": stat.st_size,
                            "mtime": stat.st_mtime,
                            "hash": compute_file_hash(path),
                            "ocr_text": ocr_text,
                            "indexed_at": time.time(),
                            "width": width,
                            "height": height,
                        })
                    except Exception as e:
                        logger.warning(f"获取文件元数据失败: {path} | {e}")

                if db_records:
                    self.db.upsert_batch(db_records)

                processed += len(batch_paths)

            # ── 阶段 3：持久化索引 ───────────────────────────────
            self._set_status(IndexStatus.SAVING, progress_pct=100.0, processed_files=total)
            logger.info("正在保存索引到磁盘...")
            self.faiss.save()
            self.text.save()

            self._last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._set_status(
                IndexStatus.COMPLETED,
                total_files=total,
                processed_files=total,
                progress_pct=100.0,
                current_file="",
                indexing_directories=[],
            )
            logger.success(f"索引构建完成！共处理 {total} 张图片，索引总量: {self.faiss.total}")

        except Exception as e:
            logger.exception(f"索引任务异常: {e}")
            self._set_status(IndexStatus.ERROR, error_msg=str(e), indexing_directories=[])
