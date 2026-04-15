# AutoScanMind 模型说明
# 此目录包含程序运行所需的 AI 模型文件

## 目录结构
models/
├── chinese-clip-vit-large-patch14/  # Chinese-CLIP 语义搜索模型 (~1.5GB)
├── paddleocr/                        # PaddleOCR 文字识别模型 (~50MB)
└── README.md                          # 本文件

## 使用说明
首次运行程序前，请确保本目录包含以下两个模型文件夹：
1. chinese-clip-vit-large-patch14 - CLIP 语义特征提取模型
2. paddleocr - OCR 文字识别模型

模型文件应放在与程序主程序 (AutoScanMind.exe) 同一目录下的 models 文件夹中。

## 版本信息
AutoScanMind 版本: 1.0.0

