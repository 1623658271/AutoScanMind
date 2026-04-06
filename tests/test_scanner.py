"""
文件扫描器单元测试
"""
import os
import tempfile
from pathlib import Path
import pytest
from backend.engine.scanner import FileScanner, is_image_file, compute_file_hash


def test_is_image_file():
    assert is_image_file("test.jpg") is True
    assert is_image_file("test.PNG") is True
    assert is_image_file("test.webp") is True
    assert is_image_file("test.txt") is False
    assert is_image_file("test.mp4") is False


def test_compute_hash_consistency():
    """同一文件哈希应相同。"""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"hello world test data for hash")
        path = f.name
    try:
        h1 = compute_file_hash(path)
        h2 = compute_file_hash(path)
        assert h1 == h2
        assert len(h1) == 32  # MD5 十六进制长度
    finally:
        os.unlink(path)


def test_scan_images_in_temp_dir():
    """测试在临时目录中扫描图片文件。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建一些测试文件
        (Path(tmpdir) / "photo.jpg").write_bytes(b"fake jpg")
        (Path(tmpdir) / "doc.txt").write_bytes(b"fake txt")
        (Path(tmpdir) / "img.png").write_bytes(b"fake png")
        subdir = Path(tmpdir) / "sub"
        subdir.mkdir()
        (subdir / "nested.webp").write_bytes(b"fake webp")

        scanner = FileScanner()
        found = list(scanner.iter_images([tmpdir]))
        names = {Path(p).name for p in found}

        assert "photo.jpg" in names
        assert "img.png" in names
        assert "nested.webp" in names
        assert "doc.txt" not in names
        assert len(names) == 3


def test_stop_scan():
    """测试停止信号能够中断扫描。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(100):
            (Path(tmpdir) / f"img_{i}.jpg").write_bytes(b"fake")
        scanner = FileScanner()
        scanner.stop()  # 立即停止
        found = list(scanner.iter_images([tmpdir]))
        assert len(found) == 0
