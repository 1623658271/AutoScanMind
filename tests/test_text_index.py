"""
文字索引 (BM25) 单元测试
"""
import pytest
from backend.engine.text_index import TextIndex, _tokenize


def test_tokenize_chinese():
    tokens = _tokenize("猫咪在家里睡觉")
    assert "猫" in tokens
    assert "咪" in tokens


def test_tokenize_english():
    tokens = _tokenize("hello world test")
    assert "hello" in tokens
    assert "world" in tokens


def test_tokenize_mixed():
    tokens = _tokenize("猫 cat 2024")
    assert "猫" in tokens
    assert "cat" in tokens
    assert "2024" in tokens


def test_add_and_search():
    index = TextIndex()
    index.rebuild()  # 清空

    index.add("cat.jpg", "一只橘猫在晒太阳")
    index.add("dog.jpg", "金毛犬在公园奔跑")
    index.add("receipt.jpg", "发票 金额 合计 税率 VAT")
    index._rebuild_bm25()

    results = index.search("猫")
    assert len(results) > 0
    paths = [r[0] for r in results]
    assert "cat.jpg" in paths

    results2 = index.search("发票")
    assert len(results2) > 0
    assert results2[0][0] == "receipt.jpg"


def test_remove():
    index = TextIndex()
    index.rebuild()
    index.add("a.jpg", "苹果 香蕉 西瓜")
    index.add("b.jpg", "苹果 手机 电脑")
    index._rebuild_bm25()

    index.remove("a.jpg")
    index._rebuild_bm25()

    results = index.search("西瓜")
    paths = [r[0] for r in results]
    assert "a.jpg" not in paths
