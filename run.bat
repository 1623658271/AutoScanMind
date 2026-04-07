@echo off
chcp 65001 >nul

echo.
echo  AutoScanMind - Quick Start (dev mode)
echo.

:: Activate virtual environment if exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python main.py
pause
