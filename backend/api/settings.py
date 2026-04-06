"""
设置 API 路由
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List

from fastapi import APIRouter
from loguru import logger

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import SCAN_EXCLUDE_DIRS, SETTINGS_PATH
from backend.models.schemas import AppSettings, OkResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])

# ── 默认设置 ──────────────────────────────────────────────────────
_DEFAULT_SETTINGS = AppSettings(
    scan_directories=[],
    full_disk_scan=False,
    alpha=0.6,
    top_n=30,
    ocr_enabled=True,
    auto_index_on_start=False,
    exclude_dirs=list(SCAN_EXCLUDE_DIRS),
)


def get_settings_obj() -> AppSettings:
    """读取当前设置（从磁盘加载，失败时返回默认值）。"""
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppSettings(**data)
        except Exception as e:
            logger.warning(f"设置加载失败，使用默认值: {e}")
    return _DEFAULT_SETTINGS.model_copy(deep=True)


def save_settings_obj(settings: AppSettings) -> None:
    """将设置持久化到磁盘。"""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)


@router.get("", response_model=AppSettings)
async def get_settings() -> AppSettings:
    """获取当前设置。"""
    return get_settings_obj()


@router.post("", response_model=OkResponse)
async def update_settings(new_settings: AppSettings) -> OkResponse:
    """更新设置。"""
    try:
        save_settings_obj(new_settings)
        return OkResponse(message="设置已保存")
    except Exception as e:
        logger.error(f"保存设置失败: {e}")
        return OkResponse(ok=False, message=f"保存失败: {e}")


@router.get("/directories", response_model=List[str])
async def get_directories() -> List[str]:
    """获取当前配置的扫描目录列表。"""
    return get_settings_obj().scan_directories


@router.post("/directories/add", response_model=OkResponse)
async def add_directory(body: dict) -> OkResponse:
    """添加扫描目录。"""
    path = body.get("path", "").strip()
    if not path:
        return OkResponse(ok=False, message="路径不能为空")
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return OkResponse(ok=False, message=f"目录不存在: {path}")
    settings = get_settings_obj()
    if path not in settings.scan_directories:
        settings.scan_directories.append(str(p.resolve()))
        save_settings_obj(settings)
    return OkResponse(message=f"已添加目录: {path}")


@router.post("/directories/remove", response_model=OkResponse)
async def remove_directory(body: dict) -> OkResponse:
    """移除扫描目录。"""
    path = body.get("path", "").strip()
    settings = get_settings_obj()
    if path in settings.scan_directories:
        settings.scan_directories.remove(path)
        save_settings_obj(settings)
        return OkResponse(message=f"已移除目录: {path}")
    return OkResponse(ok=False, message=f"目录不在列表中: {path}")
