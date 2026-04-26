# 🎨 Wallpaper Manager

Wallpaper Engine 本地壁纸库管理工具 — 扫描、预览、搜索、收藏你的 WE 壁纸库。（本项目为AI生成）

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-green)
![Tests](https://img.shields.io/badge/Tests-101%20passed%20%7C%2012%20skipped-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ 功能

- 📂 **自动扫描** — 解析 Wallpaper Engine workshop 目录，提取 `project.json` 元数据
- 🖼️ **网格预览** — 卡片式布局，支持缩略图 + 主题色边框
- 🔍 **搜索过滤** — 按标题、标签、类型实时搜索，300ms 防抖
- ❤️ **收藏管理** — 一键收藏/取消，支持仅收藏过滤
- 📋 **大图预览** — 弹窗查看完整预览图 + 详细元信息（支持视频壁纸）
- 📊 **统计面板** — 实时显示壁纸总数、类型分布、收藏数
- 📂 **多目录管理** — 支持同时管理多个壁纸库目录
- 📤 **导入/导出** — 收藏列表 JSON 导入导出
- 🖱️ **多选操作** — Ctrl/Shift 多选 + 右键批量操作
- 🎨 **应用壁纸** — 右键一键在 Wallpaper Engine 中打开壁纸（PoC）

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
pip install pyinstaller
pyinstaller build.spec
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
│   ├── db.py               # SQLite 数据库 CRUD + Schema 迁移
│   ├── scanner.py          # 目录扫描 + project.json 解析
│   ├── thumbnail_worker.py # 缩略图缓存生成 + 清理
│   ├── export_worker.py    # 导入/导出后台线程
│   └── we_controller.py    # Wallpaper Engine WebSocket PoC
├── ui/                     # 界面层
│   ├── theme.py            # 主题颜色常量 + QSS 样式表生成
│   ├── main_window.py      # 主窗口（网格 + 过滤 + 扫描）
│   ├── wallpaper_card.py   # 壁纸卡片组件
│   ├── filter_bar.py       # 顶部搜索过滤栏
│   ├── preview_dialog.py   # 大图/视频预览弹窗
│   ├── context_menu.py     # 右键上下文菜单
│   ├── dir_manager_dialog.py # 多目录管理对话框
│   └── __init__.py
├── tests/                  # 单元测试 (88 tests)
│   ├── conftest.py         # pytest 配置
│   ├── test_models.py      # 数据模型测试
│   ├── test_db.py          # 数据库层测试
│   ├── test_scanner.py     # 扫描器测试
│   └── test_we_controller.py # WE 控制器测试
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
  "grid_card_size": "medium",
  "theme": "dark",
  "thumb_quality": 85,
  "thumb_size": [320, 180]
}
```

## 🧪 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

当前测试覆盖：88 个测试用例，覆盖 models、db、scanner、we_controller 四个模块。

## 📋 开发进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1 — 核心功能 | ✅ 完成 | 扫描、预览、搜索、收藏、导入导出 |
| Phase 2 — 壁纸设置 | 🔶 PoC | WE WebSocket 协议调研完成，控制器 PoC 已集成 |
| Phase 3 — 高级功能 | ⬜ 未开始 | 定时轮换、Windows API 直设壁纸 |

## 📄 License

MIT
