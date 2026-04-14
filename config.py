"""
AutoScanMind - Global Configuration
"""
from pathlib import Path
import json
import os
import sys

from loguru import logger

# ── Detect if running inside PyInstaller bundle ────────────────
# When frozen, sys.frozen=True and sys.executable points to the .exe
_FROZEN = getattr(sys, "frozen", False)
if _FROZEN:
    # PyInstaller single-folder mode:
    #   sys.executable = dist/AutoScanMind/AutoScanMind.exe
    #   sys._MEIPASS  = temp dir with bundled Python + resources
    _EXE_DIR = Path(sys.executable).parent.resolve()
    _BUNDLE_DIR = Path(sys._MEIPASS)
else:
    # Normal development mode
    _EXE_DIR = Path(__file__).parent.resolve()
    _BUNDLE_DIR = _EXE_DIR

# ── Project root (for source code imports) ────────────────────
ROOT = _BUNDLE_DIR
BASE_DIR = _BUNDLE_DIR

# ── Data directory (persistent, beside exe) ───────────────────
DATA_DIR = _EXE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Settings (必须在 CLIP 配置前定义) ─────────────────────────
SETTINGS_PATH = DATA_DIR / "settings.json"

# ── CLIP model config ─────────────────────────────────────────
# 优先从打包内嵌目录加载（_BUNDLE_DIR = _internal/）；
# 开发时使用项目根目录或外部 models/；
# 也可通过设置中的 clip_model_path 自定义
_BUNDLED_CLIP_MODEL = str(_BUNDLE_DIR / "backend" / "pretrained" / "chinese-clip-vit-large-patch14")
_DEV_CLIP_MODEL = str(Path(__file__).parent / "models" / "chinese-clip-vit-large-patch14")
_EXE_MODULE_CLIP_MODEL = str(_EXE_DIR / "models" / "chinese-clip-vit-large-patch14")
_DEFAULT_CLIP_MODEL_NAME = _BUNDLED_CLIP_MODEL if _FROZEN else _DEV_CLIP_MODEL

# 运行时可覆盖的模型路径
_clip_model_path_override = None

def get_clip_model_path() -> str:
    """获取 CLIP 模型路径，优先使用设置中的自定义路径。"""
    global _clip_model_path_override
    if _clip_model_path_override:
        return _clip_model_path_override
    # 尝试从设置文件读取
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            custom_path = settings.get("clip_model_path")
            if custom_path and Path(custom_path).exists():
                return custom_path
    except Exception as e:
        logger.warning(f"读取 CLIP 模型路径失败: {e}")
    # fallback 链：内嵌 → exe旁边models → 开发models
    for candidate in [_DEFAULT_CLIP_MODEL_NAME, _EXE_MODULE_CLIP_MODEL, _DEV_CLIP_MODEL]:
        if candidate and Path(candidate).exists():
            return candidate
    return _DEFAULT_CLIP_MODEL_NAME

def set_clip_model_path(path: str) -> None:
    """设置 CLIP 模型路径。"""
    global _clip_model_path_override
    if path:
        p = Path(path)
        if p.exists():
            _clip_model_path_override = str(p.resolve())
            logger.info(f"CLIP 模型路径已设置为: {_clip_model_path_override}")
        else:
            logger.warning(f"CLIP 模型路径不存在: {path}")
    else:
        _clip_model_path_override = None

# 兼容旧代码
CLIP_MODEL_NAME = get_clip_model_path()

CLIP_BATCH_SIZE = 8
CLIP_IMAGE_SIZE = 224

# 动态设备配置（可被设置覆盖）
_CLIP_DEVICE_OVERRIDE = None

def get_clip_device() -> str:
    """获取当前 CLIP 设备，优先使用设置中的配置。"""
    if _CLIP_DEVICE_OVERRIDE is not None:
        return _CLIP_DEVICE_OVERRIDE
    # 尝试从设置文件读取
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            device_setting = settings.get("device", "cpu")
            if device_setting == "auto":
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            return device_setting
    except Exception as e:
        logger.warning(f"读取设备设置失败: {e}")
    return "cpu"

def set_clip_device(device: str) -> None:
    """设置 CLIP 设备（运行时切换）。"""
    global _CLIP_DEVICE_OVERRIDE
    if device == "auto":
        import torch
        _CLIP_DEVICE_OVERRIDE = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        _CLIP_DEVICE_OVERRIDE = device
    logger.info(f"CLIP 设备已设置为: {_CLIP_DEVICE_OVERRIDE}")

# 向后兼容
CLIP_DEVICE = get_clip_device()

# ── FAISS index config ────────────────────────────────────────
FAISS_INDEX_PATH = DATA_DIR / "faiss.index"
FAISS_ID_MAP_PATH = DATA_DIR / "faiss_id_map.json"
FAISS_DIM = 768
FAISS_TOP_K = 50

# ── OCR config ────────────────────────────────────────────────
# 优先从打包内嵌目录加载（_BUNDLE_DIR = _internal/）；
# 开发时使用项目根目录或外部 models/；
# 也可通过设置中的 ocr_model_path 自定义
_BUNDLED_OCR_MODEL = str(_BUNDLE_DIR / "backend" / "models" / "paddleocr")
_DEV_OCR_MODEL = str(Path(__file__).parent / "models" / "paddleocr")
_EXE_MODULE_OCR_MODEL = str(_EXE_DIR / "models" / "paddleocr")
_DEFAULT_OCR_MODEL_DIR = _BUNDLED_OCR_MODEL if _FROZEN else _DEV_OCR_MODEL

# 运行时可覆盖的 OCR 模型路径
_ocr_model_path_override = None

def get_ocr_model_dir() -> str:
    """获取 OCR 模型目录，优先使用设置中的自定义路径。"""
    global _ocr_model_path_override
    if _ocr_model_path_override:
        return _ocr_model_path_override
    # 尝试从设置文件读取
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            custom_path = settings.get("ocr_model_path")
            if custom_path and Path(custom_path).exists():
                return custom_path
    except Exception as e:
        logger.warning(f"读取 OCR 模型路径失败: {e}")
    # fallback 链：内嵌 → exe旁边models → 开发models
    for candidate in [_DEFAULT_OCR_MODEL_DIR, _EXE_MODULE_OCR_MODEL, _DEV_OCR_MODEL]:
        if candidate and Path(candidate).exists():
            return candidate
    return _DEFAULT_OCR_MODEL_DIR

def set_ocr_model_dir(path: str) -> None:
    """设置 OCR 模型目录。"""
    global _ocr_model_path_override
    if path:
        p = Path(path)
        if p.exists():
            _ocr_model_path_override = str(p.resolve())
            logger.info(f"OCR 模型路径已设置为: {_ocr_model_path_override}")
        else:
            logger.warning(f"OCR 模型目录不存在: {path}")
    else:
        _ocr_model_path_override = None

OCR_LANG = "ch"
OCR_USE_GPU = False

# ── Text index config ─────────────────────────────────────────
TEXT_INDEX_PATH = DATA_DIR / "text_index.json"

# ── SQLite database ───────────────────────────────────────────
DB_PATH = DATA_DIR / "metadata.db"

# ── Scan config ───────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp",
    ".tiff", ".tif", ".gif", ".heic", ".heif"
}
SCAN_EXCLUDE_DIRS = {
    "Windows", "System32", "SysWOW64", "Program Files",
    "Program Files (x86)", "$Recycle.Bin", "AppData",
    "node_modules", ".git", "__pycache__", ".cache",
}

# ── Search config ─────────────────────────────────────────────
DEFAULT_ALPHA = 0.6
DEFAULT_TOP_N = 1000
MIN_SCORE_THRESHOLD = 0.0

# ── FastAPI config ────────────────────────────────────────────
API_HOST = "127.0.0.1"
API_PORT = 18765
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# ── Frontend assets dir (bundled into _MEIPASS) ───────────────
FRONTEND_DIR = _BUNDLE_DIR / "frontend"

# ── Logging ───────────────────────────────────────────────────
# 尝试使用 data/logs，如果失败则使用临时目录
try:
    LOG_DIR = DATA_DIR / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    import tempfile
    LOG_DIR = Path(tempfile.gettempdir()) / "AutoScanMind" / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_LEVEL = "INFO"

# ── Thumbnail cache ───────────────────────────────────────────
# 尝试使用 data/thumbnails，如果失败则使用临时目录
try:
    THUMBNAIL_DIR = DATA_DIR / "thumbnails"
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    import tempfile
    THUMBNAIL_DIR = Path(tempfile.gettempdir()) / "AutoScanMind" / "thumbnails"
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

THUMBNAIL_SIZE = (300, 300)

# ── PyInstaller resource path helper ──────────────────────────
def get_resource_path(relative_path: str) -> Path:
    """Get path to a bundled resource, compatible with PyInstaller."""
    return _BUNDLE_DIR / relative_path
