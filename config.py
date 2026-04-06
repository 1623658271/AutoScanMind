"""
AutoScanMind - 全局配置
"""
from pathlib import Path
import os

# ── 项目根目录 ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()

# ── 数据目录（运行时生成，不提交版本控制）──────────────────────
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── CLIP 模型配置 ───────────────────────────────────────────────
CLIP_MODEL_NAME = str(BASE_DIR / "backend" / "models" / "chinese-clip-vit-large-patch14")  # 本地模型路径
CLIP_DEVICE = "cpu"          # "cuda" if torch.cuda.is_available() else "cpu"
CLIP_BATCH_SIZE = 8          # 批量推理批次大小（large 模型显存/内存更大，减小批次）
CLIP_IMAGE_SIZE = 224        # 输入图片尺寸

# ── FAISS 索引配置 ──────────────────────────────────────────────
FAISS_INDEX_PATH = DATA_DIR / "faiss.index"        # FAISS 索引文件路径
FAISS_ID_MAP_PATH = DATA_DIR / "faiss_id_map.json" # 索引 ID -> 图片路径映射
FAISS_DIM = 768              # Chinese-CLIP-ViT-L/14 输出维度（原 ViT-B/32 是 512）
FAISS_TOP_K = 50             # FAISS 检索返回候选数量

# ── OCR 配置 ────────────────────────────────────────────────────
OCR_LANG = "ch"              # 语言：ch = 中英文混合
OCR_USE_GPU = False          # 是否使用 GPU（默认 CPU）

# ── 文字索引配置 ────────────────────────────────────────────────
TEXT_INDEX_PATH = DATA_DIR / "text_index.json"     # BM25 文字倒排索引持久化

# ── SQLite 数据库 ───────────────────────────────────────────────
DB_PATH = DATA_DIR / "metadata.db"

# ── 扫描配置 ────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp",
    ".tiff", ".tif", ".gif", ".heic", ".heif"
}
SCAN_EXCLUDE_DIRS = {
    "Windows", "System32", "SysWOW64", "Program Files",
    "Program Files (x86)", "$Recycle.Bin", "AppData",
    "node_modules", ".git", "__pycache__", ".cache",
}

# ── 搜索配置 ────────────────────────────────────────────────────
DEFAULT_ALPHA = 0.6          # CLIP 权重（1-alpha 为 OCR/BM25 权重）
DEFAULT_TOP_N = 30           # 搜索返回结果数量
MIN_SCORE_THRESHOLD = 0.0    # 最低相关性分数阈值（0 = 输出所有图片）

# ── FastAPI 服务配置 ────────────────────────────────────────────
API_HOST = "127.0.0.1"
API_PORT = 18765
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# ── 前端资源目录 ────────────────────────────────────────────────
FRONTEND_DIR = BASE_DIR / "frontend"

# ── 日志配置 ────────────────────────────────────────────────────
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_LEVEL = "INFO"

# ── 设置文件 ────────────────────────────────────────────────────
SETTINGS_PATH = DATA_DIR / "settings.json"

# ── 图片缩略图缓存 ──────────────────────────────────────────────
THUMBNAIL_DIR = DATA_DIR / "thumbnails"
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAIL_SIZE = (300, 300)

# ── PyInstaller 打包时资源路径兼容 ─────────────────────────────
def get_resource_path(relative_path: str) -> Path:
    """兼容 PyInstaller 打包后的资源路径。"""
    import sys
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller 单目录模式，资源在 _MEIPASS 临时目录
        return Path(sys._MEIPASS) / relative_path
    return BASE_DIR / relative_path
