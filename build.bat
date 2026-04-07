@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo  ========================================================
echo        AutoScanMind  Build Script
echo        PyInstaller -^> .exe (single-folder mode)
echo  ========================================================
echo.

:: ── Check Python ──────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [INFO] Python: %PYVER%

:: ── Detect & activate venv ────────────────────────────────
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment .venv\...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment venv\...
    call venv\Scripts\activate.bat
) else (
    echo [WARN] No virtual environment found, using global Python.
    echo        Recommend: python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
)

:: ── Check PyInstaller ─────────────────────────────────────
python -c "import PyInstaller; print(PyInstaller.__version__)" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller==6.6.0
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause & exit /b 1
    )
)

:: ── Clean old build artifacts ─────────────────────────────
echo.
echo [INFO] Cleaning old build artifacts...
if exist build    rmdir /s /q build
if exist dist     rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

:: ── Build ────────────────────────────────────────────────
echo.
echo [INFO] Starting PyInstaller build...
echo [INFO] This may take several minutes, please wait...
echo.
pyinstaller autoscanmind.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed! Check the error messages above.
    pause & exit /b 1
)

:: ── Copy runtime resources ───────────────────────────────
echo.
echo [INFO] Copying runtime resources...

:: Create data directory
if not exist "dist\AutoScanMind\data" mkdir "dist\AutoScanMind\data"

:: Copy PaddleOCR models (required at runtime)
if not exist "dist\AutoScanMind\backend\models\paddleocr" (
    echo [INFO] Copying PaddleOCR models...
    xcopy "backend\models\paddleocr" "dist\AutoScanMind\backend\models\paddleocr\" /E /I /Q >nul
)

:: Copy CLIP model if it exists locally
if exist "backend\models\chinese-clip-vit-large-patch14" (
    if not exist "dist\AutoScanMind\backend\models\chinese-clip-vit-large-patch14" (
        echo [INFO] Copying CLIP model (this may take a while)...
        xcopy "backend\models\chinese-clip-vit-large-patch14" "dist\AutoScanMind\backend\models\chinese-clip-vit-large-patch14\" /E /I /Q >nul
    )
) else (
    echo [WARN] CLIP model not found locally. First run will need to download it.
)

:: ── Done ─────────────────────────────────────────────────
echo.
echo  ========================================================
echo        Build Successful!
echo  ========================================================
echo.
echo  Output directory : dist\AutoScanMind\
echo  Executable       : dist\AutoScanMind\AutoScanMind.exe
echo.
echo  Note: The dist\AutoScanMind\ folder can be zipped
echo        and distributed to other machines.
echo.

set /p RUN="Run AutoScanMind now? [y/N] "
if /i "!RUN!"=="y" (
    start "" "dist\AutoScanMind\AutoScanMind.exe"
)

pause
endlocal
