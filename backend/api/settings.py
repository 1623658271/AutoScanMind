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

from config import SCAN_EXCLUDE_DIRS, SETTINGS_PATH, set_clip_device
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


@router.get("/device-status")
async def get_device_status() -> dict:
    """获取当前 CLIP 设备状态（实际使用的设备）。"""
    try:
        from backend.engine.clip_engine import CLIPEngine
        clip = CLIPEngine()
        actual_device = clip.get_device()
        cuda_available = False
        try:
            import torch
            cuda_available = torch.cuda.is_available()
        except Exception:
            pass
        return {
            "actual_device": actual_device,
            "cuda_available": cuda_available,
        }
    except Exception as e:
        logger.warning(f"获取设备状态失败: {e}")
        return {"actual_device": "cpu", "cuda_available": False}


@router.post("", response_model=OkResponse)
async def update_settings(new_settings: AppSettings) -> OkResponse:
    """更新设置。"""
    try:
        # 检查设备设置变更
        old_settings = get_settings_obj()
        device_result = None  # 设备切换结果
        
        # 获取当前实际设备状态
        try:
            from backend.engine.clip_engine import CLIPEngine
            clip = CLIPEngine()
            current_actual_device = clip.get_device()
        except Exception:
            current_actual_device = "cpu"
        
        # 需要切换设备的条件：
        # 1. 设置变更了，或
        # 2. 设置是 GPU/CUDA 但实际设备是 CPU（CUDA 不可用导致的回退）
        new_device_value = new_settings.device.value if hasattr(new_settings.device, "value") else str(new_settings.device)
        old_device_value = old_settings.device.value if hasattr(old_settings.device, "value") else str(old_settings.device)
        need_switch = (
            old_settings.device != new_settings.device or
            (new_device_value in ("cuda", "gpu") and current_actual_device == "cpu")
        )
        logger.info(f"[DeviceCheck] old={old_device_value}, new={new_device_value}, actual={current_actual_device}, need_switch={need_switch}")
        
        if need_switch:
            logger.info(f"设备设置变更: {old_settings.device} -> {new_settings.device} (实际当前: {current_actual_device})")
            # 更新全局设备配置
            set_clip_device(new_device_value)
            # 通知 CLIP 引擎切换设备
            try:
                success = clip.set_device(new_device_value)
                actual_device = clip.get_device()
                device_result = {
                    "success": success,
                    "requested": new_device_value,
                    "actual": actual_device,
                }
                if not success:
                    logger.warning(f"设备切换失败: 请求 {new_device_value}, 实际 {actual_device}")
            except Exception as e:
                logger.warning(f"切换 CLIP 设备失败: {e}")
                device_result = {"success": False, "error": str(e)}
        
        save_settings_obj(new_settings)
        
        # 构造返回消息
        if device_result:
            if device_result.get("success"):
                req = device_result["requested"]
                act = device_result["actual"]
                if req != act:
                    # auto 模式回退
                    msg = f"设置已保存！设备已切换为 {act.upper()}（自动检测）"
                else:
                    msg = f"设置已保存！设备已切换为 {act.upper()}"
            else:
                err = device_result.get("error", "未知错误")
                msg = f"设置已保存，但设备切换失败: {err}"
            return OkResponse(message=msg)
        
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
