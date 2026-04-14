# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('frontend', 'frontend'), ('backend', 'backend'), ('config.py', '.')],
    hiddenimports=['uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'starlette', 'starlette.routing', 'starlette.middleware', 'starlette.middleware.cors', 'fastapi', 'python_multipart', 'pydantic', 'pydantic.fields', 'pydantic.main', 'loguru', 'PIL', 'PIL.Image', 'webview', 'webview.window', 'torch', 'torch.nn', 'torch.cuda', 'torch.utils', 'torch.utils.data', 'torch.export', 'torch.fx', 'torch.fx.passes', 'torch._dispatch', 'torch._dispatch.python', 'timm', 'timm.models', 'transformers', 'transformers.modeling_utils', 'clip', 'paddleocr', 'paddle', 'paddle.nn', 'ppocr', 'ppocr.utils', 'ppocr.modeling', 'ppocr.post_processing', 'faiss', 'numpy.core._multiarray_umath', 'shapely', 'imgaug', 'cv2', 'unittest', 'unittest.mock'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoScanMind',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoScanMind',
)
