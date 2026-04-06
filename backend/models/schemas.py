"""
Pydantic 数据模型定义
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── 枚举 ─────────────────────────────────────────────────────────
class IndexStatus(str, Enum):
    IDLE = "idle"
    SCANNING = "scanning"
    INDEXING = "indexing"
    SAVING = "saving"
    COMPLETED = "completed"
    ERROR = "error"


class SearchMode(str, Enum):
    HYBRID = "hybrid"    # CLIP + OCR 融合
    CLIP_ONLY = "clip"   # 仅 CLIP 语义
    OCR_ONLY = "ocr"     # 仅 OCR 文字


# ── 搜索相关 ──────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="搜索关键词")
    top_n: int = Field(default=30, ge=1, le=200, description="返回结果数量")
    mode: SearchMode = Field(default=SearchMode.HYBRID, description="搜索模式")
    alpha: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="CLIP 权重（覆盖全局设置）")


class SearchResultItem(BaseModel):
    path: str = Field(..., description="图片绝对路径")
    file_name: str = Field(..., description="文件名")
    score: float = Field(..., description="综合相关性分数 [0,1]")
    clip_score: float = Field(default=0.0, description="CLIP 语义分数")
    ocr_score: float = Field(default=0.0, description="OCR 文字匹配分数")
    ocr_text: str = Field(default="", description="图片中识别到的文字")
    thumbnail_url: str = Field(default="", description="缩略图 URL（Base64 或 HTTP 路径）")
    width: int = Field(default=0, description="图片宽度")
    height: int = Field(default=0, description="图片高度")
    file_size: int = Field(default=0, description="文件大小（字节）")


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total: int
    elapsed_ms: float = Field(..., description="搜索耗时（毫秒）")


# ── 索引管理相关 ──────────────────────────────────────────────────
class IndexProgressInfo(BaseModel):
    status: IndexStatus = IndexStatus.IDLE
    total_files: int = 0
    processed_files: int = 0
    current_file: str = ""
    progress_pct: float = 0.0
    error_msg: str = ""
    indexed_count: int = 0          # 当前已索引图片总数
    last_update_time: str = ""      # 上次完成索引的时间（ISO 格式）

    @property
    def progress_percent(self) -> float:
        if self.total_files == 0:
            return 0.0
        return round(self.processed_files / self.total_files * 100, 1)


class StartIndexRequest(BaseModel):
    directories: List[str] = Field(..., min_length=1, description="要扫描的目录路径列表")
    full_rebuild: bool = Field(default=False, description="是否全量重建索引")


# ── 设置相关 ──────────────────────────────────────────────────────
class AppSettings(BaseModel):
    scan_directories: List[str] = Field(default_factory=list, description="扫描目录列表")
    full_disk_scan: bool = Field(default=False, description="是否扫描整个磁盘")
    alpha: float = Field(default=0.6, ge=0.0, le=1.0, description="CLIP 融合权重")
    top_n: int = Field(default=30, ge=1, le=200, description="默认返回结果数")
    ocr_enabled: bool = Field(default=True, description="是否启用 OCR 识别")
    auto_index_on_start: bool = Field(default=False, description="启动时自动索引")
    exclude_dirs: List[str] = Field(default_factory=list, description="扫描时排除的目录名")


# ── 文件操作相关 ──────────────────────────────────────────────────
class OpenFileRequest(BaseModel):
    path: str = Field(..., description="文件绝对路径")


class OpenFolderRequest(BaseModel):
    path: str = Field(..., description="目录绝对路径，或文件所在目录")


# ── 通用响应 ──────────────────────────────────────────────────────
class OkResponse(BaseModel):
    ok: bool = True
    message: str = ""


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    detail: str = ""
