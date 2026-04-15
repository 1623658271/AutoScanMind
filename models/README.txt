AutoScanMind 模型目录
==================

首次运行前，请确保本目录包含以下模型文件夹：

1. chinese-clip-vit-large-patch14/
   - CLIP 中文语义识别模型
   - 下载地址: https://huggingface.co/uer/chinese-clip-vit-large-patch14

2. paddleocr/
   - PaddleOCR 文字识别模型
   - 建议使用 PaddleOCR 自动下载的模型
   - 或从 https://paddlepaddle.org.cn/paddleocr 下载

模型加载顺序：
1. 首先检查 settings.json 中用户自定义的路径
2. 如果没有自定义路径，查找 module/ 目录
3. 最后使用程序内置的默认路径

提示：在程序设置界面中可以修改模型路径配置。
