# 🎨 Wallpaper Manager

> **⚠️ 仅支持 Windows 10/11 平台。** 壁纸设置功能依赖 Windows API 和 Wallpaper Engine 官方 CLI，无法在 macOS / Linux 上运行。

Wallpaper Engine 本地壁纸库管理工具 — 扫描、预览、搜索、收藏你的 WE 壁纸库。（本项目为AI生成）

![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078d4?logo=windows)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-green)
![Tests](https://img.shields.io/badge/Tests-187%20passed-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ 功能

- 📂 **自动扫描** — 解析 Wallpaper Engine workshop 目录，提取 `project.json` 元数据
- 🖼️ **网格预览** — 卡片式布局，支持缩略图 + 主题色边框
- 🔍 **高级搜索** — 简单/精确/正则三种模式，300ms 防抖
- ❤️ **收藏管理** — 一键收藏/取消，支持仅收藏过滤
- 📋 **大图预览** — 弹窗查看完整预览图 + 详细元信息（支持视频壁纸）
- 📊 **统计面板** — 实时显示壁纸总数、类型分布、收藏数
- 📂 **多目录管理** — 支持同时管理多个壁纸库目录
- 📤 **导入/导出** — 收藏列表 JSON 导入导出
- 🖱️ **多选操作** — Ctrl/Shift 多选 + 右键批量操作
- 🖼️ **壁纸设置** — 一键设为桌面壁纸 + WE 动态壁纸（[官方 CLI](https://help.wallpaperengine.io/en/functionality/cli.html)）
- 🔄 **定时轮换** — 随机/顺序/收藏模式自动切换壁纸
- 🎨 **多主题** — 暗色/亮色主题一键切换，偏好持久化
- 📐 **卡片尺寸** — 小/中/大三种网格尺寸
- 🏷️ **标签管理** — 重命名/合并/删除标签
- 🏷️ **内容分级** — 按 Everyone/Mature 等分级筛选壁纸

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行

```bash
python app.py
```

程序会自动尝试发现 Wallpaper Engine 的 workshop 目录。如果未找到，手动选择包含壁纸子文件夹的目录即可。

### 打包为 exe

```bash
python scripts/build.py
```

或使用 Windows 一键打包：

```bash
build.bat
```

生成文件在 `dist/WallpaperManager/` 目录。

## 📁 项目结构

```
wallpaper-manager/
├── app.py                  # 应用入口
├── config.py               # JSON 配置文件读写
├── build.spec              # PyInstaller 打包配置
├── build.bat               # Windows 一键打包脚本
├── core/                   # 业务逻辑层
│   ├── models.py           # Wallpaper 数据类
│   ├── db.py               # SQLite CRUD + Schema 迁移 + 高级搜索 + 分级过滤
│   ├── scanner.py          # 目录扫描 + project.json 解析
│   ├── thumbnail_worker.py # 缩略图缓存生成 + 清理
│   ├── export_worker.py    # 导入/导出后台线程
│   ├── wallpaper_setter.py # 壁纸设置（Windows API + WE 官方 CLI）
│   ├── rotation_worker.py  # 壁纸定时轮换
│   └── tag_manager.py      # 标签管理
├── ui/                     # 界面层
│   ├── theme.py            # 多主题系统（暗色/亮色）
│   ├── main_window.py      # 主窗口（网格 + 过滤 + 扫描）
│   ├── wallpaper_card.py   # 壁纸卡片组件（可变尺寸）
│   ├── filter_bar.py       # 顶部搜索过滤栏
│   ├── preview_dialog.py   # 大图/视频预览弹窗
│   ├── context_menu.py     # 右键上下文菜单
│   ├── dir_manager_dialog.py # 多目录管理对话框
│   └── tag_manager_dialog.py # 标签管理对话框
├── deprecated/             # 已废弃模块（保留供参考）
│   ├── we_controller.py    # WE WebSocket PoC（已确认无公开 API）
│   └── test_we_controller.py
├── scripts/
│   └── build.py            # 跨平台打包脚本
├── tests/                  # 单元测试 (187 passed)
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_db.py
│   ├── test_scanner.py
│   ├── test_wallpaper_setter.py
│   ├── test_rotation_worker.py
│   ├── test_tag_manager.py
│   └── test_advanced_search.py
├── docs/
│   ├── PRD.md              # 需求文档
│   └── DEV.md              # 开发文档
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 📂 数据存储

所有用户数据存储在 `%USERPROFILE%\.wallpaper-manager\`：

| 文件 | 说明 |
|------|------|
| `wallpapers.db` | SQLite 数据库，壁纸索引（WAL 模式） |
| `config.json` | 用户配置（目录路径、偏好） |
| `thumbs/` | 缩略图缓存（320×180 JPEG） |

## 🔧 配置

首次运行后编辑 `%USERPROFILE%\.wallpaper-manager\config.json`：

```json
{
  "wallpaper_dirs": ["D:\\SteamLibrary\\steamapps\\workshop\\content\\431960"],
  "last_used_dir": "D:\\SteamLibrary\\steamapps\\workshop\\content\\431960",
  "card_size": "medium",
  "theme": "dark",
  "thumb_quality": 85,
  "thumb_size": [320, 180]
}
```

| 键 | 默认值 | 说明 |
|---|---|---|
| `card_size` | `"medium"` | 卡片尺寸：`small`(160×120) / `medium`(220×160) / `large`(320×240) |
| `theme` | `"dark"` | 主题：`dark`（暗色）/ `light`（亮色） |

## 🧪 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

当前测试覆盖：187 个测试用例，覆盖全部核心模块。

## 📄 License

MIT
