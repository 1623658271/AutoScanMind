# -*- mode: python ; coding: utf-8 -*-
# AutoScanMind PyInstaller spec file
# Usage: pyinstaller autoscanmind.spec

import os
import sys

# ════════════════════════════════════════════════════════════════════
#  环境隔离：禁止 PyInstaller 检测 conda 环境
#  如果 build.bat 已清洗 PATH，这里只是双保险。
#  conda 环境会导致打包出依赖 conda 的 python310.dll。
# ════════════════════════════════════════════════════════════════════
os.environ.pop("CONDA_PREFIX", None)
os.environ.pop("CONDA_DEFAULT_ENV", None)
os.environ.pop("CONDA_PROMPT_MODIFIER", None)

from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

ROOT = Path(".").resolve()

# ── 验证 Python 来源 ──────────────────────────────────────────────
# 打印当前 Python 可执行文件路径，确保不包含 conda/Miniconda
_current_python = Path(sys.executable).resolve()
_current_base = Path(sys.base_prefix).resolve()
print(f"[spec] Python executable : {_current_python}")
print(f"[spec] Python base_prefix: {_current_base}")
for _keyword in ["conda", "miniconda", "anaconda"]:
    if _keyword in str(_current_python).lower():
        print(f"[spec] WARNING: Python appears to come from a conda environment!")
        print(f"[spec]          {_current_python}")
        print(f"[spec]          This may produce a non-portable executable.")
        break

block_cipher = None

# ════════════════════════════════════════════════════════════════════
#  收集各库的动态链接库 (.dll / .pyd / .so)
#  使用 collect_dynamic_libs() 自动处理 MKL 路径解析，
#  避免 hook-torch "failed to collect MKL DLLs" 警告。
# ════════════════════════════════════════════════════════════════════

_extra_binaries = []

# ── torch（c10, torch_cpu, fbgemm, asmjit 等）──────────────────────
_extra_binaries += collect_dynamic_libs("torch")

# ── paddlepaddle（libiomp5md, mkldnn, common 等）───────────────────
_extra_binaries += collect_dynamic_libs("paddle")

# ── faiss（openblas, flang, libomp 等）────────────────────────────
# faiss 不是标准 package，collect_dynamic_libs 可能返回空，需手动兜底。
try:
    _faiss_bins = collect_dynamic_libs("faiss")
    if _faiss_bins:
        _extra_binaries += _faiss_bins
except Exception:
    pass

# 手动收集 faiss_cpu.libs 目录（包含 openblas / flang / libomp 等 DLL）
_venv_site = Path(sys.prefix) / "Lib" / "site-packages"
_faiss_libs_dir = _venv_site / "faiss_cpu.libs"
if _faiss_libs_dir.is_dir():
    for _f in _faiss_libs_dir.glob("*.dll"):
        _extra_binaries.append((str(_f), "faiss_cpu.libs"))
        print(f"[spec] Collected DLL: {_f.name} -> faiss_cpu.libs")

# ── paddleocr（其 C++ 推理引擎依赖的 DLL）──────────────────────────
try:
    _ocr_bins = collect_dynamic_libs("paddleocr")
    if _ocr_bins:
        _extra_binaries += _ocr_bins
except Exception:
    pass

# ── torchvision（如已安装）────────────────────────────────────────
try:
    _tv_bins = collect_dynamic_libs("torchvision")
    if _tv_bins:
        _extra_binaries += _tv_bins
except Exception:
    pass

print(f"[spec] Total extra binaries collected: {len(_extra_binaries)}")

# ════════════════════════════════════════════════════════════════════
#  额外的数据文件
# ════════════════════════════════════════════════════════════════════

_extra_datas = []

# 前端资源 (CSS, JS, HTML)
_extra_datas.append((str(ROOT / "frontend"), "frontend"))

# paddleocr 的 C++ 推理引擎配置文件
try:
    _paddleocr_data = collect_data_files("paddleocr")
    if _paddleocr_data:
        _extra_datas += _paddleocr_data
except Exception:
    pass

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=_extra_binaries,
    datas=_extra_datas,
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
        "paddle.base",
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
        "conda_support",
        "conda",
        "conda_package_handling",
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
    console=True,
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
