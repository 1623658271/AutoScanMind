"""
文件系统扫描器
遍历目录、过滤图片文件、增量检测（基于文件修改时间+哈希）
"""
from __future__ import annotations

import hashlib
import os
import sys
import threading
from pathlib import Path
from typing import Callable, Generator, List, Optional, Set

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import SCAN_EXCLUDE_DIRS, SUPPORTED_EXTENSIONS


def compute_file_hash(file_path: str, chunk_size: int = 65536) -> str:
    """
    计算文件 MD5 哈希（读取前 4MB 以加速大文件处理）。

    Args:
        file_path: 文件绝对路径

    Returns:
        MD5 十六进制字符串，失败返回空字符串
    """
    h = hashlib.md5()
    max_bytes = 4 * 1024 * 1024  # 前 4MB
    read_bytes = 0
    try:
        with open(file_path, "rb") as f:
            while read_bytes < max_bytes:
                chunk = f.read(min(chunk_size, max_bytes - read_bytes))
                if not chunk:
                    break
                h.update(chunk)
                read_bytes += len(chunk)
        return h.hexdigest()
    except OSError as e:
        logger.warning(f"哈希计算失败: {file_path} | {e}")
        return ""


def is_image_file(path: str) -> bool:
    """根据扩展名判断是否为支持的图片格式。"""
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


class FileScanner:
    """
    文件系统扫描器。

    职责：
    1. 递归遍历给定目录列表，找出所有图片文件
    2. 与数据库中的元信息对比，筛选出"新增"和"变更"文件
    3. 提供中止扫描的接口（stop_event）
    """

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        logger.info("FileScanner 初始化")

    def stop(self) -> None:
        """请求停止当前扫描。"""
        self._stop_event.set()

    def reset_stop(self) -> None:
        """重置停止标志（下次扫描前调用）。"""
        self._stop_event.clear()

    @property
    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    # ── 目录遍历 ─────────────────────────────────────────────────
    def iter_images(
        self,
        directories: List[str],
        exclude_dirs: Optional[Set[str]] = None,
    ) -> Generator[str, None, None]:
        """
        递归遍历目录列表，产出图片文件的绝对路径。

        Args:
            directories: 要扫描的目录路径列表
            exclude_dirs: 要排除的目录名集合（仅目录名，非绝对路径）

        Yields:
            图片文件绝对路径字符串
        """
        exclude = (exclude_dirs or SCAN_EXCLUDE_DIRS)

        for base_dir in directories:
            if self.is_stopped:
                logger.info("扫描已中止")
                return
            base = Path(base_dir)
            if not base.exists() or not base.is_dir():
                logger.warning(f"目录不存在或非目录: {base_dir}")
                continue
            yield from self._walk_dir(base, exclude)

    def _walk_dir(
        self,
        directory: Path,
        exclude_dirs: Set[str],
    ) -> Generator[str, None, None]:
        """内部递归遍历。"""
        if self.is_stopped:
            return
        try:
            with os.scandir(directory) as it:
                for entry in it:
                    if self.is_stopped:
                        return
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name in exclude_dirs or entry.name.startswith("."):
                            continue
                        yield from self._walk_dir(Path(entry.path), exclude_dirs)
                    elif entry.is_file(follow_symlinks=False):
                        if is_image_file(entry.path):
                            yield entry.path
        except PermissionError as e:
            logger.debug(f"无权限访问目录: {directory} | {e}")
        except Exception as e:
            logger.warning(f"遍历目录异常: {directory} | {e}")

    # ── 增量检测 ─────────────────────────────────────────────────
    def detect_changes(
        self,
        directories: List[str],
        get_known_mtime: Callable[[str], Optional[float]],
        get_known_hash: Callable[[str], Optional[str]],
        exclude_dirs: Optional[Set[str]] = None,
    ) -> dict:
        """
        扫描并检测文件变化。

        Args:
            directories: 要扫描的目录列表
            get_known_mtime: fn(path) -> 已记录的 mtime 或 None（新文件返回 None）
            get_known_hash: fn(path) -> 已记录的 MD5 或 None
            exclude_dirs: 排除目录名

        Returns:
            {
                "new": [path, ...],      # 新增文件
                "modified": [path, ...], # 修改文件
                "total_scanned": int,    # 扫描到的图片总数
            }
        """
        new_files: List[str] = []
        modified_files: List[str] = []
        total_scanned = 0

        for image_path in self.iter_images(directories, exclude_dirs):
            if self.is_stopped:
                break
            total_scanned += 1
            try:
                stat = os.stat(image_path)
                current_mtime = stat.st_mtime
                known_mtime = get_known_mtime(image_path)

                if known_mtime is None:
                    # 新文件
                    new_files.append(image_path)
                elif abs(current_mtime - known_mtime) > 1.0:
                    # mtime 变化，进一步验证哈希
                    known_hash = get_known_hash(image_path)
                    current_hash = compute_file_hash(image_path)
                    if current_hash and current_hash != known_hash:
                        modified_files.append(image_path)
            except OSError as e:
                logger.debug(f"文件状态获取失败: {image_path} | {e}")

        return {
            "new": new_files,
            "modified": modified_files,
            "total_scanned": total_scanned,
        }
