# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置
用法: pyinstaller build.spec
输出: dist/WallpaperManager/
"""

import os
import sys
from pathlib import Path

block_cipher = None

# 项目根目录
ROOT = os.path.dirname(os.path.abspath(SPECPATH))

# 收集数据文件
datas = []

# docs 目录
docs_dir = os.path.join(ROOT, 'docs')
if os.path.isdir(docs_dir):
    datas.append((docs_dir, 'docs'))

# tests 目录（可选，用于诊断）
tests_dir = os.path.join(ROOT, 'tests')
if os.path.isdir(tests_dir):
    datas.append((tests_dir, 'tests'))

# 图标文件（如果存在）
icon_path = None
for icon_name in ['icon.ico', 'icon.png', 'app.ico']:
    candidate = os.path.join(ROOT, 'assets', icon_name)
    if os.path.isfile(candidate):
        icon_path = candidate
        break
    candidate = os.path.join(ROOT, icon_name)
    if os.path.isfile(candidate):
        icon_path = candidate
        break

a = Analysis(
    ['app.py'],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # PySide6 核心
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtCore',
        'PySide6.QtSvg',
        # PIL / Pillow
        'PIL',
        'PIL.Image',
        'PIL.ImageQt',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        # 项目模块
        'core',
        'core.db',
        'core.models',
        'core.scanner',
        'core.thumbnail_worker',
        'core.export_worker',
        'core.wallpaper_setter',
        'core.rotation_worker',
        'ui',
        'ui.main_window',
        'ui.filter_bar',
        'ui.wallpaper_card',
        'ui.preview_dialog',
        'ui.context_menu',
        'ui.dir_manager_dialog',
        'ui.tag_manager_dialog',
        'ui.theme',
        'config',
        # 标准库
        'json',
        'sqlite3',
        'logging',
        'subprocess',
        'threading',
        'dataclasses',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
        'unittest',
        'test',
        'distutils',
        'setuptools',
        'pip',
        'wheel',
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WallpaperManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WallpaperManager',
)
