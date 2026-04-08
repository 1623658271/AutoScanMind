"""
AutoScanMind — 程序主入口

启动流程：
1. 在后台线程中启动 FastAPI (uvicorn) 服务
2. 等待服务就绪
3. 用 pywebview 创建原生窗口，加载前端页面
4. 窗口关闭后优雅退出
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# ── 解决 OpenMP 重复链接问题（torch / paddleocr 各自带了一份 libiomp5md.dll）──
# 必须在 import torch / paddleocr 之前设置
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# ── 注册所有 DLL 子目录（PyInstaller 打包时必须手动补全）─────────────────────
# PyInstaller 只把 _MEIPASS 根目录加入 DLL 搜索路径，torch/paddle/faiss 等库
# 把自己的 DLL 放在子目录里，需要通过 os.add_dll_directory() 显式注册。
if getattr(sys, "frozen", False):
    _meipass = Path(sys._MEIPASS)
    _dll_subdirs = [
        # torch（核心 DLL 都在 lib 子目录）
        _meipass / "torch" / "lib",
        _meipass / "torch" / "bin",
        # paddle（DLL 在 libs 子目录）
        _meipass / "paddle" / "libs",
        # faiss（openblas / flang / libomp 等）
        _meipass / "faiss_cpu.libs",
    ]
    for _d in _dll_subdirs:
        if _d.is_dir():
            os.add_dll_directory(str(_d))

import threading
import time

from loguru import logger

# ── 确保项目根目录在 sys.path ─────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import API_BASE_URL, API_HOST, API_PORT, FRONTEND_DIR, LOG_DIR, LOG_LEVEL, get_resource_path

# ── 日志配置 ──────────────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
)
logger.add(
    str(LOG_DIR / "app_{time:YYYY-MM-DD}.log"),
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
)


# ══════════════════════════════════════════════════════════════════
#  后端服务（FastAPI + uvicorn）
# ══════════════════════════════════════════════════════════════════

# 用于在后端线程崩溃时通知主线程
_backend_error: Exception | None = None


def start_backend() -> None:
    """在当前线程中启动 uvicorn 服务（应在守护线程中调用）。"""
    global _backend_error
    try:
        import uvicorn
        from backend.app import create_app

        app = create_app()
        logger.info(f"启动 FastAPI 服务：{API_BASE_URL}")
        uvicorn.run(
            app,
            host=API_HOST,
            port=API_PORT,
            log_level="warning",
            access_log=False,
        )
    except Exception as e:
        import traceback
        _backend_error = e
        # 写入 crash.log（放在 exe 旁边）
        if getattr(sys, "frozen", False):
            crash_log = Path(sys.executable).parent / "crash.log"
        else:
            crash_log = ROOT / "crash.log"
        try:
            with open(crash_log, "w", encoding="utf-8") as f:
                f.write("=== Backend thread crashed ===\n")
                f.write(traceback.format_exc())
        except Exception:
            pass
        logger.critical(f"后端线程崩溃: {e}")
        logger.critical(traceback.format_exc())


def wait_for_backend(timeout: float = 10.0) -> bool:
    """
    轮询等待后端服务就绪（仅检查 HTTP 响应，不等待模型加载）。

    Returns:
        True 表示就绪，False 表示超时
    """
    import urllib.request
    deadline = time.time() + timeout
    url = f"{API_BASE_URL}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(0.5)
    return False


# ══════════════════════════════════════════════════════════════════
#  清除 WebView2 缓存
# ══════════════════════════════════════════════════════════════════
def _clear_webview2_cache() -> None:
    """
    清除 Microsoft Edge WebView2 的磁盘缓存，确保每次启动加载最新前端文件。
    WebView2 默认缓存目录: %LOCALAPPDATA%\\<AppName>\\EBWebView\\Default\\Cache
    """
    try:
        # pywebview 默认使用的 user_data_dir 名称
        app_name = "pywebview"
        cache_dir = Path(os.environ.get("LOCALAPPDATA", "")) / app_name / "EBWebView" / "Default" / "Cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
            logger.debug(f"WebView2 缓存已清除: {cache_dir}")
    except Exception as e:
        logger.debug(f"清除 WebView2 缓存失败（可忽略）: {e}")


# ══════════════════════════════════════════════════════════════════
#  主窗口（pywebview）
# ══════════════════════════════════════════════════════════════════
def launch_window() -> None:
    """创建并显示 pywebview 窗口。"""
    import webview

    # ── 清除 WebView2 磁盘缓存，避免加载旧版 JS/CSS ──
    _clear_webview2_cache()

    logger.info("正在创建主窗口…")

    # pywebview 5.x API
    window = webview.create_window(
        title="AutoScanMind — 智能图片搜索",
        url=f"{API_BASE_URL}/",
        width=1200,
        height=800,
        min_size=(900, 640),
        background_color="#06080f",
        text_select=False,
        confirm_close=False,
    )

    # 可选：暴露 Python API 给 JS（pywebview 5.x 用 expose 方式）
    # webview.expose(some_python_function, window=window)

    logger.success("主窗口已创建，启动 GUI 事件循环…")
    webview.start(
        debug=False,
        # 仅 Windows CEF/EdgeChromium 生效
        private_mode=False,
    )


# ══════════════════════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════════════════════
def main() -> None:
    logger.info("AutoScanMind 启动中…")

    # 1. 后台线程启动 FastAPI
    backend_thread = threading.Thread(
        target=start_backend,
        daemon=True,
        name="fastapi-server",
    )
    backend_thread.start()

    # 2. 等待服务就绪（仅 HTTP 层，模型在后台加载）
    logger.info("等待后端服务就绪…")
    ready = wait_for_backend(timeout=15)
    # 先检查是否有后端线程崩溃
    if _backend_error is not None:
        logger.error("后端服务启动失败（子线程异常），请查看 crash.log")
        sys.exit(1)
    if not ready:
        logger.error("后端服务启动超时，退出")
        sys.exit(1)
    logger.success(f"后端服务已就绪：{API_BASE_URL}")
    logger.info("提示：CLIP 模型正在后台加载，首次启动约需 1-5 分钟")

    # 3. 启动 GUI 窗口（阻塞直到窗口关闭）
    try:
        launch_window()
    except Exception as e:
        logger.exception(f"GUI 启动失败: {e}")
        sys.exit(1)

    logger.info("窗口已关闭，程序退出")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        crash_log = Path(__file__).parent / "crash.log"
        if getattr(sys, "frozen", False):
            crash_log = Path(sys.executable).parent / "crash.log"
        with open(crash_log, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        # Also print to stderr if console is available
        print(f"FATAL: {e}", file=sys.stderr)
        traceback.print_exc()
        input("Press Enter to exit...")
