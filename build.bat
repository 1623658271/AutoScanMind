@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      AutoScanMind  打包脚本              ║
echo  ║      使用 PyInstaller 打包为 .exe        ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── 检查 Python ──────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请安装 Python 3.10+ 并添加到 PATH
    pause & exit /b 1
)

:: ── 检查虚拟环境 ─────────────────────────────────────────────────
if exist "venv\Scripts\activate.bat" (
    echo [信息] 激活虚拟环境 venv\...
    call venv\Scripts\activate.bat
) else (
    echo [警告] 未找到虚拟环境，使用全局 Python
    echo         建议先运行：python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
)

:: ── 检查 PyInstaller ──────────────────────────────────────────────
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [信息] 安装 PyInstaller...
    pip install pyinstaller==6.6.0
)

:: ── 清理旧构建产物 ────────────────────────────────────────────────
echo [信息] 清理旧构建产物...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist

:: ── 执行打包 ─────────────────────────────────────────────────────
echo [信息] 开始打包（这可能需要几分钟）...
echo.
pyinstaller autoscanmind.spec --clean --noconfirm

:: ── 检查结果 ─────────────────────────────────────────────────────
if errorlevel 1 (
    echo.
    echo [错误] 打包失败！请查看上方错误信息
    pause & exit /b 1
)

:: ── 拷贝运行时配置 ────────────────────────────────────────────────
echo.
echo [信息] 拷贝运行时资源...
if not exist "dist\AutoScanMind\data"     mkdir "dist\AutoScanMind\data"

:: ── 打包完成 ─────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  打包成功！                              ║
echo  ║  输出目录：dist\AutoScanMind\            ║
echo  ║  运行文件：dist\AutoScanMind\AutoScanMind.exe ║
echo  ╚══════════════════════════════════════════╝
echo.
echo 提示：dist\AutoScanMind\ 目录可直接压缩分发
echo       首次运行会自动下载 CLIP 模型（约 600MB）
echo.

:: 询问是否立即运行
set /p RUN="是否立即运行 AutoScanMind? [y/N] "
if /i "!RUN!"=="y" (
    start "" "dist\AutoScanMind\AutoScanMind.exe"
)

pause
endlocal
