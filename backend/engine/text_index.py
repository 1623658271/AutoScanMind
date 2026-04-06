"""
文字倒排索引 (BM25)
基于 PaddleOCR 提取的图片文字，构建 BM25 检索索引
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from loguru import logger
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import TEXT_INDEX_PATH


def _tokenize(text: str) -> List[str]:
    """
    简单分词：
    - 英文按空格/标点切分
    - 中文按单字切分
    - 过滤空 token
    """
    if not text:
        return []
    # 分离中英文
    tokens: List[str] = []
    # 用正则匹配中文字符和英文单词
    pattern = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+")
    for match in pattern.finditer(text.lower()):
        token = match.group()
        if len(token) >= 1:
            tokens.append(token)
    return tokens


class TextIndex:
    """BM25 文字倒排索引（单例模式）。"""

    _instance: "TextIndex | None" = None

    def __new__(cls) -> "TextIndex":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        # 索引数据
        self._paths: List[str] = []          # 路径列表，与 _corpus 对齐
        self._corpus: List[List[str]] = []   # tokenized 语料库
        self._path_to_idx: Dict[str, int] = {}  # 路径 -> 语料库位置
        self._bm25: BM25Okapi | None = None
        self._dirty = False                  # 标记是否需要重建 BM25
        logger.info("TextIndex 初始化")

    def load_or_create(self) -> None:
        """从磁盘加载文字索引，不存在则初始化空索引。"""
        if Path(TEXT_INDEX_PATH).exists():
            try:
                with open(TEXT_INDEX_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._paths = data["paths"]
                self._corpus = data["corpus"]
                self._path_to_idx = {p: i for i, p in enumerate(self._paths)}
                self._rebuild_bm25()
                logger.success(f"文字索引已加载，共 {len(self._paths)} 条记录")
                return
            except Exception as e:
                logger.warning(f"文字索引加载失败，重新创建: {e}")
        self._paths = []
        self._corpus = []
        self._path_to_idx = {}
        self._bm25 = None
        logger.info("文字索引已初始化（空）")

    def _rebuild_bm25(self) -> None:
        """重建 BM25 模型。"""
        if self._corpus:
            self._bm25 = BM25Okapi(self._corpus)
        else:
            self._bm25 = None
        self._dirty = False

    # ── 增删改 ───────────────────────────────────────────────────
    def add(self, image_path: str, text: str) -> None:
        """添加或更新一条图片文字记录。"""
        tokens = _tokenize(text)
        if image_path in self._path_to_idx:
            idx = self._path_to_idx[image_path]
            self._corpus[idx] = tokens
        else:
            idx = len(self._paths)
            self._paths.append(image_path)
            self._corpus.append(tokens)
            self._path_to_idx[image_path] = idx
        self._dirty = True

    def add_batch(self, image_paths: List[str], texts: List[str]) -> None:
        """批量添加文字记录。"""
        for path, text in zip(image_paths, texts):
            self.add(path, text)

    def remove(self, image_path: str) -> bool:
        """从文字索引中删除指定路径（标记为空 token）。"""
        if image_path not in self._path_to_idx:
            return False
        idx = self._path_to_idx[image_path]
        self._corpus[idx] = []
        self._dirty = True
        return True

    def remove_batch(self, image_paths: List[str]) -> int:
        """批量从文字索引中删除，返回删除数量。"""
        count = 0
        for p in image_paths:
            if self.remove(p):
                count += 1
        return count

    # ── 检索 ─────────────────────────────────────────────────────
    def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        BM25 文字检索。

        Args:
            query: 查询字符串
            top_k: 返回候选数量

        Returns:
            [(image_path, normalized_score)] 按分数降序，score in [0, 1]
        """
        if not self._paths:
            return []

        if self._dirty:
            self._rebuild_bm25()

        if self._bm25 is None:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        # 归一化分数到 [0, 1]
        max_score = float(max(scores)) if len(scores) > 0 else 0.0
        if max_score <= 0:
            return []

        # 取 top_k 结果
        top_indices = scores.argsort()[::-1][:top_k]
        results: List[Tuple[str, float]] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                break
            path = self._paths[idx]
            # 跳过已删除（空 corpus）的条目
            if not self._corpus[idx]:
                continue
            normalized = score / max_score
            results.append((path, normalized))

        return results

    # ── 持久化 ───────────────────────────────────────────────────
    def save(self) -> None:
        """将文字索引持久化到磁盘。"""
        try:
            data = {
                "paths": self._paths,
                "corpus": self._corpus,
            }
            with open(TEXT_INDEX_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            logger.info(f"文字索引已保存，共 {len(self._paths)} 条记录")
        except Exception as e:
            logger.error(f"文字索引保存失败: {e}")
            raise

    # ── 统计 ─────────────────────────────────────────────────────
    @property
    def total(self) -> int:
        """文字索引中有效记录数（非空）。"""
        return sum(1 for c in self._corpus if c)

    def contains(self, image_path: str) -> bool:
        return image_path in self._path_to_idx

    def get_text(self, image_path: str) -> str:
        """获取某图片的 OCR 文字（原始，非 token）—— 从 DB 读更准，此处仅返回 tokens 拼接。"""
        if image_path not in self._path_to_idx:
            return ""
        idx = self._path_to_idx[image_path]
        return " ".join(self._corpus[idx])

    def rebuild(self) -> None:
        """清空并重建文字索引。"""
        self._paths = []
        self._corpus = []
        self._path_to_idx = {}
        self._bm25 = None
        self._dirty = False
        logger.info("文字索引已重置")
