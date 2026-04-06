@echo off
chcp 65001 >nul

echo.
echo  AutoScanMind — 快速启动脚本（开发模式）
echo.

:: 激活虚拟环境（如果存在）
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python main.py
pause
