@echo off
chcp 65001 >nul
echo ========================================
echo   Wallpaper Manager - 构建脚本
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 检查/安装依赖
echo [1/3] 检查依赖...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

:: 检查/安装 PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [2/3] 安装 PyInstaller...
    pip install pyinstaller --quiet
) else (
    echo [2/3] PyInstaller 已安装
)

:: 打包
echo [3/3] 开始打包...
pyinstaller build.spec --clean

if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo   构建完成！
echo   输出目录: dist\WallpaperManager\
echo   运行: dist\WallpaperManager\WallpaperManager.exe
echo ========================================
pause
