"""PaddleOCR 文字识别引擎
提取图片中的中英文文字内容，供文字索引和检索使用
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from loguru import logger

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import OCR_LANG, OCR_USE_GPU

# PaddlePaddle C++ 推理引擎无法处理含中文/特殊字符的路径（如 C:\Users\浪客飞\.paddleocr\），
# 因此使用项目内纯英文路径存放模型，初始化时显式指定模型目录。
_PADDLEOCR_MODEL_DIR = ROOT / "backend" / "models" / "paddleocr"
_PADDLEOCR_DET_DIR = str(_PADDLEOCR_MODEL_DIR / "det")
_PADDLEOCR_REC_DIR = str(_PADDLEOCR_MODEL_DIR / "rec")
_PADDLEOCR_CLS_DIR = str(_PADDLEOCR_MODEL_DIR / "cls")


class OCREngine:
    """PaddleOCR 引擎封装（单例模式）。"""

    _instance: "OCREngine | None" = None

    def __new__(cls) -> "OCREngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._ocr = None
        logger.info("OCREngine 初始化")

    def load(self) -> None:
        """加载 PaddleOCR 模型（首次调用时执行）。"""
        if self._ocr is not None:
            return
        logger.info("正在加载 PaddleOCR 模型...")
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=OCR_LANG,
                use_gpu=OCR_USE_GPU,
                show_log=False,
                det_model_dir=_PADDLEOCR_DET_DIR,
                rec_model_dir=_PADDLEOCR_REC_DIR,
                cls_model_dir=_PADDLEOCR_CLS_DIR,
            )
            logger.success("PaddleOCR 模型加载完成")
        except Exception as e:
            logger.error(f"PaddleOCR 加载失败: {e}")
            raise

    def _ensure_loaded(self) -> None:
        if self._ocr is None:
            self.load()

    def extract_text(self, image_path: str) -> str:
        """
        提取单张图片中的全部文字，返回合并字符串。

        Args:
            image_path: 图片绝对路径

        Returns:
            识别到的文字，各行用空格拼接；识别失败或无文字返回空字符串
        """
        self._ensure_loaded()
        try:
            result = self._ocr.ocr(image_path, cls=True)
            if not result or result[0] is None:
                return ""
            texts: List[str] = []
            for line in result[0]:
                if line and len(line) >= 2:
                    text_conf = line[1]
                    if text_conf and len(text_conf) >= 2:
                        text = str(text_conf[0])
                        confidence = float(text_conf[1])
                        if confidence >= 0.5 and text.strip():
                            texts.append(text.strip())
            return " ".join(texts)
        except Exception as e:
            logger.warning(f"OCR 提取失败: {image_path} | {e}")
            return ""

    def extract_text_batch(self, image_paths: List[str]) -> List[str]:
        """
        批量提取图片文字。

        Returns:
            与 image_paths 等长的文字列表，失败项为空字符串
        """
        return [self.extract_text(p) for p in image_paths]
