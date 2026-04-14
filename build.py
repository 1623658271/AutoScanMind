"""
AutoScanMind - Build Script
用法: python build.py
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
os.chdir(ROOT)


def run(cmd: list[str]) -> int:
    print(f"\n[CMD] {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def build(debug: bool = False) -> int:
    # 清理旧构建
    if (ROOT / "build").exists():
        shutil.rmtree(ROOT / "build")
    if (ROOT / "dist").exists():
        shutil.rmtree(ROOT / "dist")

    # 删除旧的 spec 文件
    spec_file = ROOT / "AutoScanMind.spec"
    if spec_file.exists():
        spec_file.unlink()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "main.py",
        "--name", "AutoScanMind",
        "--onedir",
        "--add-data", f"frontend{os.pathsep}frontend",
        "--add-data", f"backend{os.pathsep}backend",
        "--add-data", f"config.py{os.pathsep}.",
        "--clean", "--noconfirm",
    ]

    if debug:
        cmd.append("--console")
    else:
        cmd.append("--windowed")

    hidden_imports = [
        # uvicorn
        "uvicorn", "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
        "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan", "uvicorn.lifespan.on",
        # starlette
        "starlette", "starlette.routing", "starlette.middleware", "starlette.middleware.cors",
        # fastapi
        "fastapi", "python_multipart", "pydantic", "pydantic.fields", "pydantic.main",
        # loguru
        "loguru",
        # PIL
        "PIL", "PIL.Image",
        # webview
        "webview", "webview.window",
        # torch
        "torch", "torch.nn", "torch.cuda", "torch.utils", "torch.utils.data",
        "torch.export", "torch.fx", "torch.fx.passes",
        "torch._dispatch", "torch._dispatch.python",
        # timm
        "timm", "timm.models",
        # transformers
        "transformers", "transformers.modeling_utils",
        # clip
        "clip",
        # paddleocr
        "paddleocr", "paddle", "paddle.nn",
        "ppocr", "ppocr.utils", "ppocr.modeling", "ppocr.post_processing",
        # other
        "faiss", "numpy.core._multiarray_umath", "shapely", "imgaug", "cv2",
        # unittest (critical for torch)
        "unittest", "unittest.mock",
    ]

    for mod in hidden_imports:
        cmd.extend(["--hidden-import", mod])

    ret = run(cmd)
    if ret != 0:
        return ret

    # 创建 models 目录结构
    dist_models = ROOT / "dist" / "AutoScanMind" / "models"
    dist_models.mkdir(parents=True, exist_ok=True)

    for sub in ["chinese-clip-vit-large-patch14", "paddleocr"]:
        (dist_models / sub).mkdir(exist_ok=True)

    # 写入 README
    readme = dist_models / "README.txt"
    readme.write_text(
        "================================================\n"
        "  AutoScanMind - AI Model Directory\n"
        "================================================\n\n"
        "Place your downloaded model folders here:\n\n"
        "  models\\\n"
        "    chinese-clip-vit-large-patch14\\   << CLIP semantic model\n"
        "    paddleocr\\                         << OCR model\n\n"
        "Model Download:\n"
        "  CLIP:     https://huggingface.co/OFA-Sys/chinese-clip-vit-large-patch14\n"
        "  PaddleOCR: https://paddlepaddle.org.cn/paddleocr\n\n"
        "================================================\n",
        encoding="utf-8",
    )

    print(f"\n{'='*50}")
    print("Build complete! Output: dist\\AutoScanMind\\")
    print("="*50)
    return 0


if __name__ == "__main__":
    debug = "--debug" in sys.argv or "-d" in sys.argv
    sys.exit(build(debug=debug))
