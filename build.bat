@echo off
chcp 65001 >nul
title AutoScanMind - Build Tool

echo ==========================================
echo   AutoScanMind Build Tool
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found!
    pause
    exit /b 1
)

echo Select build option:
echo.
echo  [1] Normal build   (no console, recommended)
echo  [2] Debug build    (with console, for troubleshooting)
echo  [3] Clean build files only
echo  [Q] Quit
echo.
set /p choice="Enter option (1/2/3/Q): "

if "%choice%"=="1" goto normal
if "%choice%"=="2" goto debug
if "%choice%"=="3" goto clean
if /i "%choice%"=="Q" goto end

echo Invalid option!
pause
exit /b 1

:normal
echo.
echo [Info] Building normal version...
python -m PyInstaller main.py ^
    --name "AutoScanMind" ^
    --windowed ^
    --onedir ^
    --add-data "frontend;frontend" ^
    --add-data "backend;backend" ^
    --add-data "config.py;." ^
    --clean --noconfirm ^
    --hidden-import uvicorn ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import starlette ^
    --hidden-import starlette.routing ^
    --hidden-import starlette.middleware ^
    --hidden-import starlette.middleware.cors ^
    --hidden-import fastapi ^
    --hidden-import python_multipart ^
    --hidden-import pydantic ^
    --hidden-import pydantic.fields ^
    --hidden-import pydantic.main ^
    --hidden-import loguru ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import webview ^
    --hidden-import webview.window ^
    --hidden-import torch ^
    --hidden-import torch.nn ^
    --hidden-import torch.cuda ^
    --hidden-import torch.utils ^
    --hidden-import torch.utils.data ^
    --hidden-import torch.export ^
    --hidden-import torch.fx ^
    --hidden-import torch.fx.passes ^
    --hidden-import torch._dispatch ^
    --hidden-import torch._dispatch.python ^
    --hidden-import timm ^
    --hidden-import timm.models ^
    --hidden-import transformers ^
    --hidden-import transformers.modeling_utils ^
    --hidden-import clip ^
    --hidden-import paddleocr ^
    --hidden-import paddle ^
    --hidden-import paddle.nn ^
    --hidden-import ppocr ^
    --hidden-import ppocr.utils ^
    --hidden-import ppocr.modeling ^
    --hidden-import ppocr.post_processing ^
    --hidden-import faiss ^
    --hidden-import numpy.core._multiarray_umath ^
    --hidden-import shapely ^
    --hidden-import imgaug ^
    --hidden-import cv2 ^
    --hidden-import unittest ^
    --hidden-import unittest.mock
if errorlevel 1 (
    echo.
    echo [Error] Build failed!
    pause
    exit /b 1
)
goto post_build

:debug
echo.
echo [Info] Building debug version (with console)...
python -m PyInstaller main.py ^
    --name "AutoScanMind" ^
    --console ^
    --onedir ^
    --add-data "frontend;frontend" ^
    --add-data "backend;backend" ^
    --add-data "config.py;." ^
    --clean --noconfirm ^
    --hidden-import uvicorn ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import starlette ^
    --hidden-import starlette.routing ^
    --hidden-import starlette.middleware ^
    --hidden-import starlette.middleware.cors ^
    --hidden-import fastapi ^
    --hidden-import python_multipart ^
    --hidden-import pydantic ^
    --hidden-import pydantic.fields ^
    --hidden-import pydantic.main ^
    --hidden-import loguru ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import webview ^
    --hidden-import webview.window ^
    --hidden-import torch ^
    --hidden-import torch.nn ^
    --hidden-import torch.cuda ^
    --hidden-import torch.utils ^
    --hidden-import torch.utils.data ^
    --hidden-import torch.export ^
    --hidden-import torch.fx ^
    --hidden-import torch.fx.passes ^
    --hidden-import torch._dispatch ^
    --hidden-import torch._dispatch.python ^
    --hidden-import timm ^
    --hidden-import timm.models ^
    --hidden-import transformers ^
    --hidden-import transformers.modeling_utils ^
    --hidden-import clip ^
    --hidden-import paddleocr ^
    --hidden-import paddle ^
    --hidden-import paddle.nn ^
    --hidden-import ppocr ^
    --hidden-import ppocr.utils ^
    --hidden-import ppocr.modeling ^
    --hidden-import ppocr.post_processing ^
    --hidden-import faiss ^
    --hidden-import numpy.core._multiarray_umath ^
    --hidden-import shapely ^
    --hidden-import imgaug ^
    --hidden-import cv2 ^
    --hidden-import unittest ^
    --hidden-import unittest.mock
if errorlevel 1 (
    echo.
    echo [Error] Build failed!
    pause
    exit /b 1
)

:post_build
echo.
echo [Info] Creating models directory structure...
if not exist "dist\AutoScanMind\models" mkdir "dist\AutoScanMind\models"
if not exist "dist\AutoScanMind\models\chinese-clip-vit-large-patch14" mkdir "dist\AutoScanMind\models\chinese-clip-vit-large-patch14"
if not exist "dist\AutoScanMind\models\paddleocr" mkdir "dist\AutoScanMind\models\paddleocr"

echo [Info] Writing README...
(
echo =================================================
echo   AutoScanMind - AI Model Directory
echo =================================================
echo.
echo Place your downloaded model folders here:
echo.
echo   models^\
echo     chinese-clip-vit-large-patch14^\   ^<^< CLIP semantic model
echo     paddleocr^                         ^<^< OCR model
echo.
echo Model Download:
echo   CLIP:     https://huggingface.co/OFA-Sys/chinese-clip-vit-large-patch14
echo   PaddleOCR: https://paddlepaddle.org.cn/paddleocr
echo.
echo =================================================
) > "dist\AutoScanMind\models\README.txt"

echo.
echo ==========================================
echo   Build Complete!
echo ==========================================
echo.
echo Output: dist\AutoScanMind\
echo.
echo Directory structure:
echo   dist\AutoScanMind^\
echo   +-- AutoScanMind.exe
echo   +-- models^\
echo   ^    +-- README.txt
echo   ^    +-- chinese-clip-vit-large-patch14^\
echo   ^    +-- paddleocr^\
echo   +-- _internal\   (Python runtime)
echo.
echo Next steps:
echo   1. Download CLIP model to models\chinese-clip-vit-large-patch14\
echo   2. Download PaddleOCR model to models\paddleocr\
echo   3. Run AutoScanMind.exe
echo.
pause
exit /b 0

:clean
echo.
echo [Info] Cleaning build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "*.spec" del /f /q "*.spec"
echo [Success] Clean complete!
pause
exit /b 0

:end
exit /b 0
