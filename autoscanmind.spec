# -*- mode: python ; coding: utf-8 -*-
# AutoScanMind PyInstaller spec file
# Usage: pyinstaller autoscanmind.spec

block_cipher = None

import sys
from pathlib import Path
ROOT = Path(".").resolve()

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Frontend assets (CSS, JS, HTML) - bundled into _MEIPASS
        (str(ROOT / "frontend"), "frontend"),
    ],
    hiddenimports=[
        # FastAPI / Starlette / Uvicorn
        "starlette",
        "starlette.staticfiles",
        "starlette.responses",
        "starlette.routing",
        "fastapi",
        "fastapi.responses",
        "fastapi.routing",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # transformers / CLIP / torch
        "transformers",
        "transformers.modeling_utils",
        "transformers.models.clip",
        "transformers.models.clip.modeling_clip",
        "torch",
        "torch._C",
        "torch.utils.data",
        # faiss
        "faiss",
        # paddleocr / paddlepaddle
        "paddleocr",
        "paddle",
        "paddle.fluid",
        # pywebview
        "webview",
        "webview.platforms",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "webview.platforms.cef",
        "webview.platforms.gtk",
        "webview.platforms.cocoa",
        "webview.platforms.qt",
        # PIL
        "PIL",
        "PIL.Image",
        "PIL.ImageOps",
        # Others
        "numpy",
        "sqlite3",
        "rank_bm25",
        "loguru",
        "pydantic",
        # json (for settings)
        "json",
        "httpx",
        "anyio._backends._asyncio",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "IPython",
        "notebook",
        "pytest",
        "setuptools",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AutoScanMind",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AutoScanMind",
)
