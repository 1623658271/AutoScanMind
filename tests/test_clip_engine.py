"""
CLIP 特征提取引擎单元测试
"""
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_cosine_similarity_identical():
    """测试同向量余弦相似度应为 1 （映射后约为 1.0）。"""
    from backend.engine.clip_engine import CLIPEngine
    engine = CLIPEngine()
    vec = np.array([1.0, 0.0, 0.0] + [0.0] * 509, dtype=np.float32)
    # 归一化
    vec /= np.linalg.norm(vec)
    vecs = np.stack([vec])
    scores = engine.cosine_similarity(vec, vecs)
    assert abs(scores[0] - 1.0) < 1e-5


def test_cosine_similarity_orthogonal():
    """测试正交向量余弦相似度应为 0 （映射后约 0.5）。"""
    from backend.engine.clip_engine import CLIPEngine
    engine = CLIPEngine()
    v1 = np.zeros(512, dtype=np.float32)
    v2 = np.zeros(512, dtype=np.float32)
    v1[0] = 1.0
    v2[1] = 1.0
    vecs = np.stack([v2])
    scores = engine.cosine_similarity(v1, vecs)
    assert abs(scores[0] - 0.5) < 1e-5
