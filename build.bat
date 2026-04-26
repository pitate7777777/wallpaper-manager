@echo off
chcp 65001 >nul
echo ========================================
echo   Wallpaper Manager - 构建脚本
echo ========================================
echo.

:: 自动检测 Python 路径
set PYTHON_CMD=
where python >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :found_python
)
where python3 >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    goto :found_python
)
:: 尝试 py launcher
where py >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :found_python
)
:: 尝试常见安装路径
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
) do (
    if exist %%P (
        set PYTHON_CMD=%%P
        goto :found_python
)
echo [错误] 未找到 Python，请先安装 Python 3.10+
pause
exit /b 1

:found_python
echo [信息] 使用 Python: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

:: 清理旧的构建产物
echo [1/5] 清理旧构建...
if exist build (
    rmdir /s /q build
    echo       已删除 build/
)
if exist dist (
    rmdir /s /q dist
    echo       已删除 dist/
)
if exist __pycache__ (
    rmdir /s /q __pycache__
)
echo.

:: 检查/安装依赖
echo [2/5] 检查项目依赖...
%PYTHON_CMD% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo       依赖已就绪
echo.

:: 检查/安装 PyInstaller
echo [3/5] 检查 PyInstaller...
%PYTHON_CMD% -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo       安装 PyInstaller...
    %PYTHON_CMD% -m pip install pyinstaller --quiet
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
) else (
    echo       PyInstaller 已安装
)
echo.

:: 打包
echo [4/5] 开始打包（这可能需要几分钟）...
echo.
%PYTHON_CMD% -m PyInstaller build.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [错误] 打包失败，请检查上方错误信息
    pause
    exit /b 1
)
echo.

:: 验证输出
echo [5/5] 验证构建结果...
set OUTPUT_DIR=dist\WallpaperManager
set OUTPUT_EXE=%OUTPUT_DIR%\WallpaperManager.exe

if not exist "%OUTPUT_EXE%" (
    echo [错误] 未找到输出文件: %OUTPUT_EXE%
    pause
    exit /b 1
)

:: 统计文件数和大小
for /f %%A in ('dir /s /b "%OUTPUT_DIR%" 2^>nul ^| find /c /v ""') do set FILE_COUNT=%%A
echo       文件数量: %FILE_COUNT%
echo       输出目录: %OUTPUT_DIR%
echo       可执行文件: %OUTPUT_EXE%
echo.

echo ========================================
echo   构建完成！
echo   输出目录: %OUTPUT_DIR%
echo   运行: %OUTPUT_EXE%
echo ========================================
echo.

:: 自动打开输出目录
explorer "%OUTPUT_DIR%"

pause
