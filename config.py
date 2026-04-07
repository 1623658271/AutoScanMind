"""
AutoScanMind - Global Configuration
"""
from pathlib import Path
import os
import sys

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
BASE_DIR = _BUNDLE_DIR

# ── Data directory (persistent, beside exe) ───────────────────
DATA_DIR = _EXE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── CLIP model config ─────────────────────────────────────────
CLIP_MODEL_NAME = str(_EXE_DIR / "backend" / "models" / "chinese-clip-vit-large-patch14")
CLIP_DEVICE = "cpu"
CLIP_BATCH_SIZE = 8
CLIP_IMAGE_SIZE = 224

# ── FAISS index config ────────────────────────────────────────
FAISS_INDEX_PATH = DATA_DIR / "faiss.index"
FAISS_ID_MAP_PATH = DATA_DIR / "faiss_id_map.json"
FAISS_DIM = 768
FAISS_TOP_K = 50

# ── OCR config ────────────────────────────────────────────────
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
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_LEVEL = "INFO"

# ── Settings ──────────────────────────────────────────────────
SETTINGS_PATH = DATA_DIR / "settings.json"

# ── Thumbnail cache ───────────────────────────────────────────
THUMBNAIL_DIR = DATA_DIR / "thumbnails"
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAIL_SIZE = (300, 300)

# ── PyInstaller resource path helper ──────────────────────────
def get_resource_path(relative_path: str) -> Path:
    """Get path to a bundled resource, compatible with PyInstaller."""
    return _BUNDLE_DIR / relative_path
