"""
文件操作 API 路由
打开文件、打开所在目录、提供图片缩略图服务
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pretrained.schemas import OkResponse, OpenFileRequest, OpenFolderRequest

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/open", response_model=OkResponse)
async def open_file(req: OpenFileRequest) -> OkResponse:
    """用系统默认应用打开文件。"""
    p = Path(req.path)
    if not p.exists():
        return OkResponse(ok=False, message=f"文件不存在: {req.path}")
    try:
        os.startfile(str(p))  # Windows 专属
        return OkResponse(message=f"已打开: {p.name}")
    except Exception as e:
        logger.error(f"打开文件失败: {req.path} | {e}")
        return OkResponse(ok=False, message=str(e))


@router.post("/open-folder", response_model=OkResponse)
async def open_folder(req: OpenFolderRequest) -> OkResponse:
    """在文件资源管理器中打开目录，若传入的是文件路径则定位到该文件。"""
    p = Path(req.path)
    target_dir = p if p.is_dir() else p.parent
    if not target_dir.exists():
        return OkResponse(ok=False, message=f"目录不存在: {target_dir}")
    try:
        if p.is_file():
            # 选中并高亮该文件
            subprocess.Popen(f'explorer /select,"{p}"', shell=False)
        else:
            subprocess.Popen(f'explorer "{target_dir}"', shell=False)
        return OkResponse(message=f"已打开文件夹: {target_dir}")
    except Exception as e:
        logger.error(f"打开目录失败: {req.path} | {e}")
        return OkResponse(ok=False, message=str(e))


@router.get("/thumbnail")
async def get_thumbnail(path: str):
    """
    提供图片原图（前端可通过 img src 直接加载本地图片）。
    出于安全考虑，仅允许读取图片文件。
    """
    from config import SUPPORTED_EXTENSIONS
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="不支持的文件类型")
    return FileResponse(str(p))


@router.get("/drives")
async def list_drives():
    """列出 Windows 上所有可用的磁盘驱动器（用于全盘扫描选择）。"""
    drives = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append(drive)
    return {"drives": drives}


@router.get("/pick-folder")
async def pick_folder():
    """弹出系统目录选择对话框，返回用户选择的目录路径。"""
    path = await _pick_folder_impl()
    if path:
        return {"path": path}
    return {"path": ""}


async def _pick_folder_impl() -> str:
    """内部实现：弹出系统目录选择对话框，返回用户选择的目录路径。"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _pick_folder_impl_sync)
    except Exception as e:
        logger.error(f"目录选择失败: {e}")
        return ""


def _pick_folder_impl_sync() -> str:
    """同步实现：弹出系统目录选择对话框，返回用户选择的目录路径。"""
    import tkinter as tk
    from tkinter import filedialog

    try:
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        root.attributes("-topmost", True)  # 置顶
        selected = filedialog.askdirectory(title="选择文件夹")
        root.destroy()

        return selected if selected else ""
    except Exception as e:
        logger.error(f"目录选择失败: {e}")
        return ""
