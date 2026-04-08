"""
CLIP 特征提取引擎
支持 OpenAI CLIP 和 Chinese-CLIP (OFA-Sys)，自动检测模型类型
带下载进度条
"""
from __future__ import annotations

import os

# ── 解决 OpenMP 重复链接问题（torch / paddleocr 各自带了一份 libiomp5md.dll）──
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys
import threading
import time
from pathlib import Path
from typing import List

import numpy as np
import requests
import torch
from loguru import logger
from PIL import Image
from transformers import AutoModel, AutoProcessor

# 将项目根目录加入路径
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import CLIP_BATCH_SIZE, CLIP_MODEL_NAME, get_clip_device


# ══════════════════════════════════════════════════════════════════
#  下载进度条（跨线程安全，直接写 stdout 确保在后台线程中可见）
# ══════════════════════════════════════════════════════════════════
class _ProgressTracker:
    """追踪文件下载进度并周期性打印到控制台。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._done = 0
        self._total = 0
        self._filename = ""
        self._active = False
        self._printer: threading.Thread | None = None

    def begin(self, filename: str, total_size: int):
        with self._lock:
            self._done = 0
            self._total = total_size
            self._filename = filename
            self._active = True
        self._printer = threading.Thread(target=self._loop, daemon=True)
        self._printer.start()

    def update(self, chunk_size: int):
        with self._lock:
            self._done += chunk_size

    def finish(self):
        with self._lock:
            self._active = False
            mb = self._done / (1024 * 1024)
            fname = self._filename
        sys.stdout.write(f"\r  [OK] {fname} ({mb:.1f} MB)\n")
        sys.stdout.flush()

    def _loop(self):
        while True:
            time.sleep(0.3)
            with self._lock:
                if not self._active:
                    return
                done = self._done
                total = self._total
                fname = self._filename
            if total <= 0:
                continue
            pct = min(done * 100 / total, 100)
            mb_d = done / (1024 * 1024)
            mb_t = total / (1024 * 1024)
            bar_w = 30
            filled = int(bar_w * pct / 100)
            bar = "#" * filled + "-" * (bar_w - filled)
            sys.stdout.write(
                f"\r  DL {fname}: [{bar}] {pct:5.1f}% {mb_d:.1f}/{mb_t:.1f} MB  "
            )
            sys.stdout.flush()


_progress = _ProgressTracker()


class CLIPEngine:
    """CLIP 特征提取引擎（单例模式），支持标准 CLIP 和 Chinese-CLIP。"""

    _instance: "CLIPEngine | None" = None

    def __new__(cls) -> "CLIPEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        requested_device = get_clip_device()
        # 验证设备可用性，如果不可用则回退到 CPU
        if requested_device == "cuda" and not torch.cuda.is_available():
            logger.warning(f"请求设备 {requested_device} 不可用，回退到 CPU")
            self._device_name = "cpu"
        else:
            self._device_name = requested_device
        self.device = torch.device(self._device_name)
        self.model = None
        self.processor = None
        self._feature_dim = 0
        logger.info(f"CLIPEngine 初始化，设备: {self.device}，模型: {CLIP_MODEL_NAME}")

    def set_device(self, device_name: str) -> bool:
        """
        切换推理设备。
        
        Args:
            device_name: "cpu", "cuda", 或 "auto"
        
        Returns:
            True 表示切换成功，False 表示切换失败
        """
        # 处理 auto 模式
        if device_name == "auto":
            actual_device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"自动检测设备: auto -> {actual_device}")
            device_name = actual_device
        
        if device_name == self._device_name:
            return True
        
        # 验证设备可用性
        if device_name == "cuda" and not torch.cuda.is_available():
            logger.error("CUDA 不可用，无法切换到 GPU")
            return False
        
        logger.info(f"切换 CLIP 设备: {self._device_name} -> {device_name}")
        self._device_name = device_name
        self.device = torch.device(device_name)
        
        # 如果模型已加载，需要重新加载到新设备
        if self.model is not None:
            logger.info("重新加载模型到新设备...")
            self.model = self.model.to(self.device)
            logger.success(f"模型已切换到 {device_name}")
        
        return True

    def get_device(self) -> str:
        """获取当前设备名称。"""
        return self._device_name

    @property
    def feature_dim(self) -> int:
        """返回模型输出特征维度。"""
        return self._feature_dim

    def load(self) -> None:
        """加载 CLIP 模型（首次调用时执行，带下载进度条）。"""
        if self.model is not None:
            return
        logger.info(f"正在加载 CLIP 模型: {CLIP_MODEL_NAME}")

        try:
            is_local = Path(CLIP_MODEL_NAME).is_dir()

            if not is_local:
                # ── 远程模型：检查缓存 + 按需下载（带进度条）─────────
                from huggingface_hub import try_to_load_from_cache

                model_files = [
                    "config.json",
                    "preprocessor_config.json",
                    "model.safetensors",
                    "pytorch_model.bin",
                ]
                need_download = False
                for fname in model_files:
                    cache_info = try_to_load_from_cache(CLIP_MODEL_NAME, fname)
                    if cache_info is None:
                        need_download = True
                        break

                if need_download:
                    # ── 注入 requests hook 追踪下载进度 ────────────────
                    original_get = requests.Session.get

                    def _patched_get(self_session, url, **kwargs):
                        resp = original_get(self_session, url, **kwargs)
                        if resp.status_code == 200 and "content-length" in resp.headers:
                            total = int(resp.headers["content-length"])
                            fname = url.split("/")[-1].split("?")[0]
                            if total > 1024 * 1024:  # 只追踪 >1MB
                                _progress.begin(fname, total)
                                original_iter_content = resp.iter_content

                                def _tracked_iter_content(*a, **kw):
                                    for chunk in original_iter_content(*a, **kw):
                                        _progress.update(len(chunk))
                                        yield chunk
                                    _progress.finish()

                                resp.iter_content = _tracked_iter_content
                        return resp

                    requests.Session.get = _patched_get

                    try:
                        from huggingface_hub import hf_hub_download

                        logger.info("正在从 HuggingFace 下载模型...")
                        for fname in model_files:
                            try:
                                hf_hub_download(CLIP_MODEL_NAME, fname, local_files_only=False)
                            except Exception:
                                pass
                        logger.info("模型文件下载完成，正在加载到内存...")
                    finally:
                        requests.Session.get = original_get
            else:
                logger.info(f"使用本地模型: {CLIP_MODEL_NAME}")

            # ── 使用 AutoModel/AutoProcessor 自动适配 CLIP 变体 ──
            self.processor = AutoProcessor.from_pretrained(CLIP_MODEL_NAME, local_files_only=is_local)
            self.model = AutoModel.from_pretrained(CLIP_MODEL_NAME, local_files_only=is_local).to(self.device)
            self.model.eval()

            # 自动检测特征维度
            if hasattr(self.model.config, "projection_dim"):
                self._feature_dim = self.model.config.projection_dim
            elif hasattr(self.model.config, "hidden_size"):
                self._feature_dim = self.model.config.hidden_size
            else:
                # 临时推理获取实际维度
                dummy = self.processor(
                    images=[Image.new("RGB", (224, 224))],
                    return_tensors="pt",
                ).to(self.device)
                with torch.no_grad():
                    feat = self.model.get_image_features(**dummy)
                self._feature_dim = feat.shape[-1]

            logger.success(f"CLIP 模型加载完成，特征维度: {self._feature_dim}")
        except Exception as e:
            logger.error(f"CLIP 模型加载失败: {e}")
            raise

    def _ensure_loaded(self) -> None:
        if self.model is None:
            self.load()

    # ── 图像特征提取 ────────────────────────────────────────────
    @torch.no_grad()
    def encode_images(self, image_paths: List[str]) -> np.ndarray:
        """
        批量提取图像特征向量。

        Returns:
            shape (N, dim) 的 float32 归一化特征向量数组
        """
        self._ensure_loaded()
        dim = self._feature_dim
        all_features: List[np.ndarray] = []

        for i in range(0, len(image_paths), CLIP_BATCH_SIZE):
            batch_paths = image_paths[i : i + CLIP_BATCH_SIZE]
            images: List[Image.Image] = []
            valid_indices: List[int] = []

            for j, path in enumerate(batch_paths):
                try:
                    img = Image.open(path).convert("RGB")
                    images.append(img)
                    valid_indices.append(j)
                except Exception as e:
                    logger.warning(f"图片读取失败，跳过: {path} | {e}")

            if not images:
                all_features.append(np.zeros((len(batch_paths), dim), dtype=np.float32))
                continue

            inputs = self.processor(images=images, return_tensors="pt", padding=True).to(self.device)
            features = self.model.get_image_features(**inputs)
            features = features / features.norm(p=2, dim=-1, keepdim=True)
            features_np = features.cpu().numpy().astype(np.float32)

            batch_result = np.zeros((len(batch_paths), dim), dtype=np.float32)
            for idx, feat in zip(valid_indices, features_np):
                batch_result[idx] = feat
            all_features.append(batch_result)

        return np.vstack(all_features) if all_features else np.empty((0, dim), dtype=np.float32)

    @torch.no_grad()
    def encode_image(self, image_path: str) -> np.ndarray:
        """提取单张图像特征向量。"""
        return self.encode_images([image_path])[0]

    # ── 文本特征提取 ────────────────────────────────────────────
    @torch.no_grad()
    def encode_text(self, text: str) -> np.ndarray:
        """
        提取文本特征向量。
        Chinese-CLIP 原生支持中文，搜索效果远优于原版 CLIP。
        """
        self._ensure_loaded()
        inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(self.device)
        features = self.model.get_text_features(**inputs)
        features = features / features.norm(p=2, dim=-1, keepdim=True)
        return features.cpu().numpy()[0].astype(np.float32)

    # ── 相似度计算 ──────────────────────────────────────────────
    def cosine_similarity(self, query_vec: np.ndarray, image_vecs: np.ndarray) -> np.ndarray:
        """
        计算查询向量与图像向量集合的余弦相似度（已归一化向量直接点积）。

        Returns:
            shape (N,) 的相似度分数，映射到 [0, 1]
        """
        scores = image_vecs @ query_vec
        return ((scores + 1) / 2).astype(np.float32)
