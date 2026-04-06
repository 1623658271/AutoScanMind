"""
FastAPI 应用主入口
注册所有路由，配置 CORS、静态文件服务
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger


class NoCacheStaticFiles(StaticFiles):
    """StaticFiles 子类：为所有响应添加禁用缓存头，避免 pywebview 缓存旧 JS。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, scope, receive, send):
        scope = dict(scope)

        async def send_no_cache(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"cache-control", b"no-cache, no-store, must-revalidate"))
                headers.append((b"pragma", b"no-cache"))
                headers.append((b"expires", b"0"))
                message = dict(message)
                message["headers"] = headers
            await send(message)

        return super().__call__(scope, receive, send_no_cache)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import FRONTEND_DIR
from backend.api import files, index, search, settings
from backend.engine.index_manager import IndexManager


def create_app() -> FastAPI:
    """工厂函数：创建并配置 FastAPI 实例。"""

    app = FastAPI(
        title="AutoScanMind API",
        description="本地智能图片搜索后端 API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # ── CORS（pywebview 前端通过 fetch 调用本地 API）──────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 健康检查（必须在 mount 之前注册，否则会被 StaticFiles 拦截）──
    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    # ── 注册 API 路由 ──────────────────────────────────────────────
    app.include_router(search.router)
    app.include_router(index.router)
    app.include_router(settings.router)
    app.include_router(files.router)

    # ── 前端静态文件服务（必须放在所有路由之后，避免拦截 /api/* 请求）──
    if FRONTEND_DIR.exists():
        app.mount("/", NoCacheStaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    # ── 启动事件：异步初始化索引存储（不阻塞服务）───────────────
    @app.on_event("startup")
    async def startup_event():
        import threading
        logger.info("FastAPI 服务启动中...")

        def _init_in_background():
            """在后台线程中初始化 IndexManager，避免阻塞健康检查。"""
            try:
                manager = IndexManager()
                manager.initialize()
                logger.success("IndexManager 初始化完成")
            except Exception as e:
                logger.error(f"IndexManager 初始化失败: {e}")

        init_thread = threading.Thread(
            target=_init_in_background,
            daemon=True,
            name="index-init",
        )
        init_thread.start()
        logger.info("IndexManager 后台初始化已启动")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("FastAPI 服务正在关闭...")
        try:
            from backend.db.metadata_db import MetadataDB
            MetadataDB().close()
        except Exception:
            pass

    return app
