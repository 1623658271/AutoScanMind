"""
双路融合算法单元测试
"""
import pytest
from backend.engine.fusion import SearchFusion


def test_fuse_clip_only():
    fusion = SearchFusion(alpha=1.0)
    clip = [("a.jpg", 0.9), ("b.jpg", 0.7), ("c.jpg", 0.5)]
    result = fusion.fuse(clip, [], top_n=3)
    assert len(result) == 3
    assert result[0]["path"] == "a.jpg"
    assert abs(result[0]["score"] - 0.9) < 1e-4


def test_fuse_ocr_only():
    fusion = SearchFusion(alpha=0.0)
    ocr = [("x.jpg", 0.8), ("y.jpg", 0.6)]
    result = fusion.fuse([], ocr, top_n=5)
    assert len(result) == 2
    assert result[0]["path"] == "x.jpg"


def test_fuse_hybrid():
    fusion = SearchFusion(alpha=0.6)
    clip = [("a.jpg", 0.9), ("b.jpg", 0.3)]
    ocr  = [("b.jpg", 0.9), ("c.jpg", 0.5)]
    result = fusion.fuse(clip, ocr, top_n=10)

    paths = [r["path"] for r in result]
    # a.jpg score = 0.6*0.9 + 0.4*0 = 0.54
    # b.jpg score = 0.6*0.3 + 0.4*0.9 = 0.18+0.36 = 0.54
    # c.jpg score = 0.6*0 + 0.4*0.5 = 0.2
    assert "a.jpg" in paths
    assert "b.jpg" in paths
    assert "c.jpg" in paths
    # c.jpg 得分最低
    assert result[-1]["path"] == "c.jpg"


def test_top_n_limit():
    fusion = SearchFusion(alpha=0.5)
    clip = [(f"{i}.jpg", float(i)/10) for i in range(20)]
    result = fusion.fuse(clip, [], top_n=5)
    assert len(result) <= 5
