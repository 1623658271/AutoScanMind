# AutoScanMind

> **本地智能图片搜索工具** — 融合 CLIP 语义理解与 PaddleOCR 文字识别，完全离线运行

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightblue)](https://www.microsoft.com/windows)

---

## 功能特性

- **自然语言搜索**：输入"猫"、"合同"、"海边日落"，同时匹配图像视觉内容（CLIP）与图片内嵌文字（PaddleOCR）
- **双路融合检索**：CLIP 语义相似度 + BM25 文字匹配，加权融合排序，找到视觉和文字双维度最相关的图片
- **灵活搜索范围**：支持指定单个/多个文件夹，或扫描整个计算机（需管理员权限）
- **增量索引更新**：仅重新索引变化的文件，避免全量重建，节省时间
- **完全离线运行**：所有模型本地加载，无需网络和付费 API，保障隐私
- **现代化界面**：基于 pywebview 的玻璃拟态深色主题桌面 GUI

## 技术栈

| 组件 | 技术 |
|------|------|
| 桌面 GUI | pywebview 5.x + HTML/CSS/JS |
| 语义搜索 | CLIP ViT-B/32 (HuggingFace transformers) |
| 向量索引 | FAISS (faiss-cpu) |
| OCR 识别 | PaddleOCR (中英文) |
| 文字检索 | BM25 (rank_bm25) |
| 后端服务 | FastAPI + uvicorn |
| 数据库 | SQLite |
| 文件监控 | watchdog |

## 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11
- 内存 >= 4GB（建议 8GB 以上）

### 安装

```bash
# 克隆项目
git clone https://github.com/yourname/autoscanmind.git
cd autoscanmind

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 首次运行

```bash
python main.py
```

程序启动后会自动下载 CLIP 模型（也可从项目一并下载，约 600MB），此后完全离线运行。

### 打包为 .exe

```bash
build.bat
```

打包产物在 `dist/AutoScanMind/` 目录，可直接分发。

## 项目结构

```
autoscanmind/
├── main.py                 # 程序入口
├── config.py               # 全局配置
├── requirements.txt        # Python 依赖
├── build.bat               # 打包脚本
├── backend/
│   ├── app.py              # FastAPI 应用
│   ├── api/                # API 路由层
│   ├── engine/             # 核心引擎层
│   ├── models/             # Pydantic 数据模型
│   └── db/                 # 数据库操作层
├── frontend/
│   ├── index.html          # 主界面
│   ├── css/style.css       # 玻璃拟态样式
│   └── js/                 # 前端交互逻辑
└── data/                   # 运行时数据（索引、数据库、日志）
```

## 使用说明

1. **建立索引**：点击右侧设置面板，添加要扫描的文件夹路径，点击"开始索引"
2. **搜索图片**：在搜索框输入自然语言，如"海边日落""身份证""猫咪"，按回车搜索
3. **查看结果**：结果网格展示匹配图片，hover 显示文件路径，点击可打开文件或所在目录
4. **调整权重**：设置面板中可调节 CLIP 语义与 OCR 文字的融合权重

## 配置说明

编辑 `config.py` 可调整：

- `DEFAULT_ALPHA`：CLIP 语义权重（默认 0.6），`1 - alpha` 为 OCR 文字权重
- `CLIP_DEVICE`：推理设备，`"cpu"` 或 `"cuda"`
- `FAISS_TOP_K`：FAISS 候选集大小
- `SCAN_EXCLUDE_DIRS`：扫描时排除的目录名

## License

[MIT License](LICENSE)

## 致谢

- [OpenAI CLIP](https://github.com/openai/CLIP)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [FAISS](https://github.com/facebookresearch/faiss)
- [pywebview](https://pywebview.flowrl.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
