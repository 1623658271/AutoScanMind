"""
索引管理 API 路由
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastapi import APIRouter
from loguru import logger

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.engine.index_manager import IndexManager
from backend.pretrained.schemas import (
    IndexProgressInfo,
    OkResponse,
    StartIndexRequest,
)

router = APIRouter(prefix="/api/index", tags=["index"])


@router.post("/start", response_model=OkResponse)
async def start_index(req: StartIndexRequest) -> OkResponse:
    """启动索引任务（后台线程异步执行）。"""
    from backend.api.settings import get_settings_obj
    settings = get_settings_obj()
    ocr_enabled = settings.ocr_enabled

    manager = IndexManager()
    started = manager.start_indexing(
        directories=req.directories,
        full_rebuild=req.full_rebuild,
        ocr_enabled=ocr_enabled,
    )
    if started:
        return OkResponse(message="索引任务已启动")
    return OkResponse(ok=False, message="索引任务已在运行中，请稍后重试")


@router.post("/stop", response_model=OkResponse)
async def stop_index() -> OkResponse:
    """请求停止当前索引任务。"""
    IndexManager().stop_indexing()
    return OkResponse(message="停止信号已发送")


@router.get("/indexed-dirs")
async def get_indexed_directories():
    """获取当前索引中各目录的图片数量统计（含磁盘实际图片总数）。"""
    manager = IndexManager()
    loop = asyncio.get_event_loop()
    dirs = await loop.run_in_executor(None, manager.get_indexed_directories)
    return {"directories": dirs}


@router.post("/purge-directory")
async def purge_directory(req: dict) -> OkResponse:
    """清理指定目录下的所有索引数据。"""
    directory = req.get("directory", "").strip()
    if not directory:
        return OkResponse(ok=False, message="请指定要清理的目录")

    manager = IndexManager()
    count = manager.purge_by_directory(directory)
    if count > 0:
        return OkResponse(message=f"已清理 {count} 个文件的索引")
    return OkResponse(message="该目录下没有需要清理的索引")


@router.get("/progress", response_model=IndexProgressInfo)
async def get_progress() -> IndexProgressInfo:
    """获取索引进度信息。"""
    return IndexManager().get_progress()
