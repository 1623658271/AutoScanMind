"""
双路检索结果融合引擎
CLIP 语义相似度 + BM25 文字匹配加权融合排序
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_ALPHA, DEFAULT_TOP_N, FAISS_TOP_K, MIN_SCORE_THRESHOLD


class SearchFusion:
    """
    双路检索融合器。

    融合公式：
        final_score = alpha * clip_score + (1 - alpha) * ocr_score

    其中：
        alpha: CLIP 权重，默认 0.6
        clip_score: FAISS 返回的归一化余弦相似度 [0, 1]
        ocr_score: BM25 归一化得分 [0, 1]
    """

    def __init__(self, alpha: float = DEFAULT_ALPHA) -> None:
        self.alpha = alpha

    def fuse(
        self,
        clip_results: List[Tuple[str, float]],
        ocr_results: List[Tuple[str, float]],
        top_n: int = DEFAULT_TOP_N,
    ) -> List[Dict]:
        """
        融合 CLIP 和 OCR 检索结果。

        Args:
            clip_results: [(path, clip_score)] CLIP 检索结果，已归一化
            ocr_results: [(path, ocr_score)] BM25 文字检索结果，已归一化
            top_n: 最终返回结果数量

        Returns:
            [{"path": str, "score": float, "clip_score": float, "ocr_score": float}]
            按 score 降序排列
        """
        clip_map: Dict[str, float] = {p: s for p, s in clip_results}
        ocr_map: Dict[str, float] = {p: s for p, s in ocr_results}

        # 合并所有候选路径
        all_paths = set(clip_map.keys()) | set(ocr_map.keys())

        if not all_paths:
            return []

        results = []
        for path in all_paths:
            cs = clip_map.get(path, 0.0)
            os_ = ocr_map.get(path, 0.0)
            final = self.alpha * cs + (1 - self.alpha) * os_
            if final >= MIN_SCORE_THRESHOLD:
                results.append({
                    "path": path,
                    "score": round(final, 4),
                    "clip_score": round(cs, 4),
                    "ocr_score": round(os_, 4),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    def fuse_clip_only(
        self,
        clip_results: List[Tuple[str, float]],
        top_n: int = DEFAULT_TOP_N,
    ) -> List[Dict]:
        """仅使用 CLIP 结果（OCR 无匹配时降级处理）。"""
        return self.fuse(clip_results, [], top_n)

    def fuse_ocr_only(
        self,
        ocr_results: List[Tuple[str, float]],
        top_n: int = DEFAULT_TOP_N,
    ) -> List[Dict]:
        """仅使用 OCR 结果（CLIP 无匹配时降级处理）。"""
        return self.fuse([], ocr_results, top_n)
