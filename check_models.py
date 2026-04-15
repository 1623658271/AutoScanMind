"""
AutoScanMind 模型检查脚本
用于验证运行所需的 AI 模型是否已正确安装

使用方法:
    python check_models.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))


def check_models():
    """检查模型文件是否存在"""
    print("=" * 50)
    print("AutoScanMind 模型检查")
    print("=" * 50)
    print()

    # 导入配置
    try:
        from config import get_clip_model_path, get_ocr_model_dir, _DEFAULT_CLIP_MODEL_NAME, _DEFAULT_OCR_MODEL_DIR
    except ImportError as e:
        print(f"[错误] 无法导入配置: {e}")
        return False

    models_dir = ROOT / "models"
    exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else ROOT

    print(f"程序目录: {exe_dir}")
    print(f"模型目录: {models_dir}")
    print()

    all_ok = True

    # 检查 CLIP 模型
    clip_model = Path(get_clip_model_path())
    clip_files = ["config.json", "pytorch_model.bin", "vocab.txt"]
    clip_ok = clip_model.exists() and clip_model.is_dir()

    print(f"[{'OK' if clip_ok else 'MISSING'}] Chinese-CLIP 模型")
    print(f"    路径: {clip_model}")
    if clip_ok:
        for f in clip_files:
            exists = (clip_model / f).exists()
            print(f"      {'+' if exists else '-'} {f}")
    else:
        print(f"    提示: 可从以下位置获取模型:")
        print(f"      - models/chinese-clip-vit-large-patch14/")
        print(f"      - {_DEFAULT_CLIP_MODEL_NAME}")
    print()

    # 检查 PaddleOCR 模型
    ocr_model = Path(get_ocr_model_dir())
    paddle_dirs = ["det", "rec", "cls"]
    paddle_ok = ocr_model.exists() and ocr_model.is_dir()

    print(f"[{'OK' if paddle_ok else 'MISSING'}] PaddleOCR 模型")
    print(f"    路径: {ocr_model}")
    if paddle_ok:
        for d in paddle_dirs:
            exists = (ocr_model / d).exists()
            print(f"      {'+' if exists else '-'} {d}/")
    else:
        print(f"    提示: 可从以下位置获取模型:")
        print(f"      - models/paddleocr/")
        print(f"      - {_DEFAULT_OCR_MODEL_DIR}")
    print()

    # 结果总结
    print("=" * 50)
    if clip_ok and paddle_ok:
        print("[OK] 所有模型已正确安装！")
        print("=" * 50)
        return True
    else:
        print("[WARNING] 部分模型缺失！")
        print()
        print("请将模型文件夹复制到以下目录之一:")
        print(f"  1. {models_dir}")
        print(f"  2. {ROOT / 'backend' / 'models'}")
        print()
        print("所需模型:")
        if not clip_ok:
            print("  - chinese-clip-vit-large-patch14/  (~1.5GB)")
            print("    下载: https://huggingface.co/OFA-Sys/chinese-clip-vit-large-patch14")
        if not paddle_ok:
            print("  - paddleocr/  (~50MB)")
            print("    下载: https://paddlepaddle.org.cn/paddleocr")
        print("=" * 50)
        return False


if __name__ == "__main__":
    ok = check_models()
    sys.exit(0 if ok else 1)
