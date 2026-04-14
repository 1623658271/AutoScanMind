"""
搜索 API 路由
"""
from __future__ import annotations

import base64
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import List

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger
from PIL import Image as PILImage

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_ALPHA, THUMBNAIL_SIZE
from backend.db.metadata_db import MetadataDB
from backend.engine.clip_engine import CLIPEngine
from backend.engine.faiss_store import FAISSStore
from backend.engine.fusion import SearchFusion
from backend.engine.index_manager import IndexManager
from backend.engine.text_index import TextIndex
from backend.pretrained.schemas import (
    IndexStatus,
    SearchMode,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

router = APIRouter(prefix="/api/search", tags=["search"])


def _make_thumbnail_base64(image_path: str) -> str:
    """生成图片缩略图的 Base64 Data URL。"""
    try:
        with PILImage.open(image_path) as img:
            img.thumbnail(THUMBNAIL_SIZE, PILImage.LANCZOS)
            buf = BytesIO()
            fmt = img.format or "JPEG"
            if fmt not in ("JPEG", "PNG", "WEBP"):
                fmt = "JPEG"
            if fmt == "JPEG" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buf, format=fmt, quality=80)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            mime = f"image/{fmt.lower()}"
            return f"data:{mime};base64,{b64}"
    except Exception as e:
        logger.debug(f"缩略图生成失败: {image_path} | {e}")
        return ""


@router.post("", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    """
    自然语言图片搜索接口。
    同时执行 CLIP 语义检索和 BM25 文字检索，融合排序返回结果。
    """
    t0 = time.perf_counter()

    alpha = req.alpha if req.alpha is not None else DEFAULT_ALPHA
    query = req.query.strip()

    # 检查索引状态：索引进行中且索引为空时，提示用户等待
    manager = IndexManager()
    progress = manager.get_progress()
    is_indexing = progress.status in (IndexStatus.SCANNING, IndexStatus.INDEXING, IndexStatus.SAVING)
    if is_indexing and progress.indexed_count == 0:
        logger.info(f"搜索 '{query}' 被拦截：索引进行中（{progress.status}），当前已索引 {progress.indexed_count} 条")
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return SearchResponse(
            query=query,
            results=[],
            total=0,
            elapsed_ms=elapsed_ms,
        )

    clip_engine = CLIPEngine()
    faiss_store = FAISSStore()
    text_index = TextIndex()
    db = MetadataDB()
    fusion = SearchFusion(alpha=alpha)

    # 确保引擎已加载
    try:
        clip_engine.load()
    except FileNotFoundError as e:
        logger.error(f"CLIP 模型缺失: {e}")
        return JSONResponse(
            status_code=503,
            content={"error_code": "MODEL_NOT_READY", "detail": str(e)},
        )
    except Exception as e:
        logger.error(f"CLIP 模型加载失败: {e}")
        return JSONResponse(
            status_code=503,
            content={"error_code": "MODEL_NOT_READY", "detail": f"CLIP 模型加载失败: {e}"},
        )

    # top_n = 0 表示不限制数量
    unlimited = (req.top_n == 0)
    effective_top_n = req.top_n if req.top_n > 0 else 999999

    clip_results = []
    ocr_results = []

    # ── CLIP 语义检索 ────────────────────────────────────────────
    if req.mode in (SearchMode.HYBRID, SearchMode.CLIP_ONLY):
        try:
            query_vec = clip_engine.encode_text(query)
            clip_results = faiss_store.search(query_vec, top_k=effective_top_n)
        except Exception as e:
            logger.error(f"CLIP 检索失败: {e}")

    # ── OCR 文字检索 ─────────────────────────────────────────────
    if req.mode in (SearchMode.HYBRID, SearchMode.OCR_ONLY):
        try:
            ocr_results = text_index.search(query, top_k=effective_top_n)
        except Exception as e:
            logger.error(f"文字检索失败: {e}")

    # ── 融合排序（不限制时不截断） ──────────────────────────────
    fuse_top_n = effective_top_n
    if req.mode == SearchMode.CLIP_ONLY:
        fused = fusion.fuse_clip_only(clip_results, top_n=fuse_top_n)
    elif req.mode == SearchMode.OCR_ONLY:
        fused = fusion.fuse_ocr_only(ocr_results, top_n=fuse_top_n)
    else:
        fused = fusion.fuse(clip_results, ocr_results, top_n=fuse_top_n)

    # ── 目录过滤 ─────────────────────────────────────────────────
    # directories 有值时按目录过滤；空列表 = 不返回任何结果；None = 搜索全部
    if req.directories is not None:
        logger.debug(f"搜索目录过滤: directories={req.directories}")
        if not req.directories:
            # 空列表 → 直接返回空结果
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            return SearchResponse(query=query, results=[], total=0, elapsed_ms=elapsed_ms)
        # 将指定目录统一为小写绝对路径，用于前缀匹配
        allowed_roots = [str(Path(d).resolve()).lower() for d in req.directories]
        filtered = []
        for item in fused:
            p_lower = str(Path(item["path"]).resolve()).lower()
            if any(p_lower.startswith(root) for root in allowed_roots):
                filtered.append(item)
        # 不限制时返回全部过滤结果，否则取 top_n
        fused = filtered if unlimited else filtered[:req.top_n]

    # ── 构建结果列表 ─────────────────────────────────────────────
    result_paths = [item["path"] for item in fused]
    db_rows = db.get_by_paths(result_paths)
    db_map = {row["path"]: row for row in db_rows}

    items: List[SearchResultItem] = []
    for item in fused:
        path = item["path"]
        p = Path(path)
        if not p.exists():
            continue
        row = db_map.get(path)
        ocr_text = row["ocr_text"] if row else ""
        width = row["width"] if row else 0
        height = row["height"] if row else 0
        file_size = row["file_size"] if row else 0

        thumbnail_url = _make_thumbnail_base64(path)

        items.append(SearchResultItem(
            path=path,
            file_name=p.name,
            score=item["score"],
            clip_score=item["clip_score"],
            ocr_score=item["ocr_score"],
            ocr_text=ocr_text,
            thumbnail_url=thumbnail_url,
            width=width,
            height=height,
            file_size=file_size,
        ))

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    logger.info(f"搜索 '{query}' → {len(items)} 条结果，耗时 {elapsed_ms}ms")

    return SearchResponse(
        query=query,
        results=items,
        total=len(items),
        elapsed_ms=elapsed_ms,
    )
