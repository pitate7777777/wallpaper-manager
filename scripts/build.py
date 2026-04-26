#!/usr/bin/env python3
"""
打包脚本 - 自动化 PyInstaller 打包（跨平台）
用法: python scripts/build.py [--clean-only] [--no-open] [--spec PATH]
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path


# 强制 stdout/sderr 使用 UTF-8（CI 环境兼容性关键 fix）
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
SPEC_FILE = ROOT / "build.spec"


def log(msg: str, level: str = "INFO"):
    """带时间戳的日志输出（兼容 GBK/UTF-8 终端）"""
    ts = time.strftime("%H:%M:%S")
    prefix_map = {"INFO": "i", "OK": "*", "WARN": "!", "ERR": "x"}
    prefix = prefix_map.get(level, " ")
    # 尝试 UTF-8 输出，回退到 ASCII 前缀避免 GBK 编码错误
    try:
        emoji_prefix = {"INFO": "\u2139\ufe0f", "OK": "\u2705", "WARN": "\u26a0\ufe0f", "ERR": "\u274c"}.get(level, " ")
        print(f"[{ts}] {emoji_prefix} {msg}")
    except (UnicodeEncodeError, UnicodeError):
        print(f"[{ts}] [{level}] {msg}")


def check_python():
    """检查 Python 版本"""
    ver = sys.version_info
    log(f"Python {ver.major}.{ver.minor}.{ver.micro} ({sys.executable})")
    if ver < (3, 10):
        log("需要 Python 3.10+", "ERR")
        sys.exit(1)


def check_dependencies():
    """检查并安装项目依赖"""
    req_file = ROOT / "requirements.txt"
    if req_file.exists():
        log("检查项目依赖...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"],
            check=True,
        )
        log("依赖已就绪", "OK")
    else:
        log("requirements.txt 不存在，跳过依赖检查", "WARN")


def check_pyinstaller():
    """确保 PyInstaller 已安装"""
    try:
        import PyInstaller  # noqa: F401
        log(f"PyInstaller 已安装")
    except ImportError:
        log("安装 PyInstaller...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"],
            check=True,
        )
        log("PyInstaller 安装完成", "OK")


def clean():
    """清理旧的构建产物"""
    log("清理旧构建产物...")
    removed = 0
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
            log(f"  已删除 {d.name}/")
            removed += 1
    # 清理 __pycache__
    for pycache in ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)
    if removed == 0:
        log("无需清理", "OK")
    else:
        log(f"清理完成，删除了 {removed} 个目录", "OK")


def build(spec_file: Path = None):
    """执行 PyInstaller 打包"""
    spec = spec_file or SPEC_FILE
    if not spec.exists():
        log(f"spec 文件不存在: {spec}", "ERR")
        sys.exit(1)

    log(f"开始打包 ({spec.name})...")
    log(f"平台: {platform.system()} {platform.machine()}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec),
        "--clean",
        "--noconfirm",
    ]

    start = time.time()
    result = subprocess.run(cmd, cwd=str(ROOT))
    elapsed = time.time() - start

    if result.returncode != 0:
        log(f"打包失败 (退出码: {result.returncode})", "ERR")
        sys.exit(1)

    log(f"打包完成，耗时 {elapsed:.1f} 秒", "OK")


def verify():
    """验证打包结果"""
    log("验证构建结果...")

    dist = ROOT / "dist" / "WallpaperManager"
    if not dist.exists():
        log(f"输出目录不存在: {dist}", "ERR")
        sys.exit(1)

    # 检查可执行文件
    if platform.system() == "Windows":
        exe = dist / "WallpaperManager.exe"
    else:
        exe = dist / "WallpaperManager"

    if not exe.exists():
        log(f"可执行文件不存在: {exe}", "ERR")
        sys.exit(1)

    # 统计
    file_count = sum(1 for _ in dist.rglob("*") if _.is_file())
    total_size = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)

    log(f"可执行文件: {exe.name}", "OK")
    log(f"文件数量: {file_count}")
    log(f"总大小: {size_mb:.1f} MB")
    log(f"输出目录: {dist}")

    # 检查关键文件
    key_files = [
        "docs",
        "tests",
    ]
    for name in key_files:
        p = dist / name
        if p.exists():
            log(f"  [OK] {name}/")
        else:
            log(f"  [MISSING] {name}/", "WARN")


def open_output():
    """打开输出目录"""
    dist = ROOT / "dist" / "WallpaperManager"
    if not dist.exists():
        return

    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(str(dist))
        elif system == "Darwin":
            subprocess.Popen(["open", str(dist)])
        else:
            subprocess.Popen(["xdg-open", str(dist)])
    except Exception as e:
        log(f"无法打开目录: {e}", "WARN")


def main():
    parser = argparse.ArgumentParser(description="Wallpaper Manager 打包脚本")
    parser.add_argument("--clean-only", action="store_true", help="仅清理，不打包")
    parser.add_argument("--no-open", action="store_true", help="打包后不打开输出目录")
    parser.add_argument("--spec", type=str, help="指定 spec 文件路径")
    args = parser.parse_args()

    print("=" * 50)
    print("  Wallpaper Manager - 打包脚本")
    print("=" * 50)
    print()

    check_python()
    clean()

    if args.clean_only:
        return

    print()
    check_dependencies()
    check_pyinstaller()

    print()
    spec = Path(args.spec) if args.spec else None
    build(spec)

    print()
    verify()

    if not args.no_open:
        print()
        open_output()

    print()
    print("=" * 50)
    print("  全部完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
