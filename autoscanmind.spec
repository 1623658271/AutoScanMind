; AutoScanMind PyInstaller 规格文件
; 使用方式：pyinstaller autoscanmind.spec

; 自动处理 CLIP / PaddleOCR / FAISS 等大型依赖的 binaries 和 datas

block_cipher = None

import sys
from pathlib import Path
ROOT = Path(".").resolve()

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # 前端资源
        (str(ROOT / "frontend"), "frontend"),
        # data 目录占位（运行时生成）
        (str(ROOT / "data" / ".gitkeep"), "data"),
    ],
    hiddenimports=[
        # FastAPI / Starlette
        "starlette",
        "starlette.staticfiles",
        "fastapi",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        # transformers / CLIP
        "transformers",
        "transformers.modeling_utils",
        "transformers.models.clip",
        # faiss
        "faiss",
        # paddleocr
        "paddleocr",
        "paddlepaddle",
        # webview
        "webview",
        # 其他
        "PIL",
        "PIL.Image",
        "numpy",
        "sqlite3",
        "rank_bm25",
        "watchdog",
        "loguru",
        "aiofiles",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "IPython", "notebook"],
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
    upx=True,
    console=False,          # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # TODO: 替换为 .ico 图标路径
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AutoScanMind",
)
