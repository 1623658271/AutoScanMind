"""
FAISS 向量索引管理
构建、持久化、加载和检索 CLIP 图像特征向量索引
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import faiss
import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import FAISS_DIM, FAISS_ID_MAP_PATH, FAISS_INDEX_PATH, FAISS_TOP_K


class FAISSStore:
    """FAISS 向量索引管理器（单例模式）。"""

    _instance: "FAISSStore | None" = None

    def __new__(cls) -> "FAISSStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.index: faiss.IndexFlatIP | None = None
        # id_map: faiss 内部连续 ID -> 图片路径
        self.id_map: Dict[int, str] = {}
        # path_to_id: 图片路径 -> faiss 内部 ID（用于删除/更新）
        self.path_to_id: Dict[str, int] = {}
        self._next_id = 0
        logger.info("FAISSStore 初始化")

    # ── 初始化索引 ───────────────────────────────────────────────
    def _create_index(self) -> faiss.IndexIDMap:
        """创建 IndexIDMap 包装 IndexFlatIP（内积 = 归一化余弦相似度）。"""
        base_index = faiss.IndexFlatIP(FAISS_DIM)
        index = faiss.IndexIDMap(base_index)
        return index

    def load_or_create(self) -> None:
        """从磁盘加载索引，不存在则创建新索引。"""
        if self.index is not None:
            return
        if Path(FAISS_INDEX_PATH).exists() and Path(FAISS_ID_MAP_PATH).exists():
            try:
                self.index = faiss.read_index(str(FAISS_INDEX_PATH))
                with open(FAISS_ID_MAP_PATH, "r", encoding="utf-8") as f:
                    raw: Dict[str, str] = json.load(f)
                self.id_map = {int(k): v for k, v in raw.items()}
                self.path_to_id = {v: int(k) for k, v in raw.items()}
                self._next_id = max(self.id_map.keys(), default=-1) + 1
                logger.success(f"FAISS 索引已加载，共 {len(self.id_map)} 条记录")
                return
            except Exception as e:
                logger.warning(f"FAISS 索引加载失败，重新创建: {e}")
        self.index = self._create_index()
        self.id_map = {}
        self.path_to_id = {}
        self._next_id = 0
        logger.info("FAISS 新索引已创建")

    def _ensure_loaded(self) -> None:
        if self.index is None:
            self.load_or_create()

    # ── 增删改 ───────────────────────────────────────────────────
    def add(self, image_path: str, vector: np.ndarray) -> int:
        """
        添加或更新一条图像向量记录。

        Args:
            image_path: 图片绝对路径
            vector: shape (dim,) 归一化 float32 向量

        Returns:
            分配的 FAISS ID
        """
        self._ensure_loaded()
        # 若已存在则先删除旧向量
        if image_path in self.path_to_id:
            self.remove(image_path)

        fid = self._next_id
        self._next_id += 1
        vec = vector.reshape(1, -1).astype(np.float32)
        ids = np.array([fid], dtype=np.int64)
        self.index.add_with_ids(vec, ids)  # type: ignore[attr-defined]
        self.id_map[fid] = image_path
        self.path_to_id[image_path] = fid
        return fid

    def add_batch(self, image_paths: List[str], vectors: np.ndarray) -> List[int]:
        """
        批量添加向量记录。

        Args:
            image_paths: 图片路径列表，与 vectors 一一对应
            vectors: shape (N, dim) float32 归一化向量
        """
        self._ensure_loaded()
        fids = []
        new_paths: List[str] = []
        new_vecs: List[np.ndarray] = []

        for path, vec in zip(image_paths, vectors):
            if path in self.path_to_id:
                self.remove(path)
            fid = self._next_id
            self._next_id += 1
            self.id_map[fid] = path
            self.path_to_id[path] = fid
            new_paths.append(path)
            new_vecs.append(vec)
            fids.append(fid)

        if new_vecs:
            batch_vecs = np.array(new_vecs, dtype=np.float32)
            batch_ids = np.array(fids, dtype=np.int64)
            self.index.add_with_ids(batch_vecs, batch_ids)  # type: ignore[attr-defined]

        return fids

    def remove(self, image_path: str) -> bool:
        """从索引中删除指定图片的向量。"""
        self._ensure_loaded()
        if image_path not in self.path_to_id:
            return False
        fid = self.path_to_id.pop(image_path)
        self.id_map.pop(fid, None)
        ids_to_remove = faiss.IDSelectorArray(np.array([fid], dtype=np.int64))
        self.index.remove_ids(ids_to_remove)  # type: ignore[attr-defined]
        return True

    # ── 检索 ─────────────────────────────────────────────────────
    def search(
        self, query_vec: np.ndarray, top_k: int = FAISS_TOP_K
    ) -> List[Tuple[str, float]]:
        """
        相似度检索。

        Args:
            query_vec: shape (dim,) 归一化查询向量
            top_k: 返回候选数量

        Returns:
            [(image_path, score)] 按 score 降序，score in [0, 1]
        """
        self._ensure_loaded()
        if len(self.id_map) == 0:
            return []

        actual_k = min(top_k, len(self.id_map))
        vec = query_vec.reshape(1, -1).astype(np.float32)
        scores, ids = self.index.search(vec, actual_k)  # type: ignore[attr-defined]

        results: List[Tuple[str, float]] = []
        for score, fid in zip(scores[0], ids[0]):
            if fid == -1:
                continue
            path = self.id_map.get(int(fid))
            if path:
                # 内积相似度映射到 [0,1]
                normalized_score = float((score + 1) / 2)
                results.append((path, normalized_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    # ── 持久化 ───────────────────────────────────────────────────
    def save(self) -> None:
        """将索引和 ID 映射持久化到磁盘。"""
        self._ensure_loaded()
        try:
            faiss.write_index(self.index, str(FAISS_INDEX_PATH))
            with open(FAISS_ID_MAP_PATH, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self.id_map.items()}, f, ensure_ascii=False)
            logger.info(f"FAISS 索引已保存，共 {len(self.id_map)} 条记录")
        except Exception as e:
            logger.error(f"FAISS 索引保存失败: {e}")
            raise

    # ── 统计 ─────────────────────────────────────────────────────
    @property
    def total(self) -> int:
        """索引中的图片总数。"""
        return len(self.id_map)

    def contains(self, image_path: str) -> bool:
        """检查路径是否已被索引。"""
        return image_path in self.path_to_id

    def rebuild(self) -> None:
        """清空并重建索引（全量重建时使用）。"""
        self.index = self._create_index()
        self.id_map = {}
        self.path_to_id = {}
        self._next_id = 0
        logger.info("FAISS 索引已重置")
