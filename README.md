# 🎨 Wallpaper Manager

Wallpaper Engine 本地壁纸库管理工具 — 扫描、预览、搜索、收藏你的 WE 壁纸库。（本项目为AI生成）

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ 功能

- 📂 **自动扫描** — 解析 Wallpaper Engine workshop 目录，提取 `project.json` 元数据
- 🖼️ **网格预览** — 卡片式布局，支持缩略图 + 主题色边框
- 🔍 **搜索过滤** — 按标题、标签、类型实时搜索，300ms 防抖
- ❤️ **收藏管理** — 一键收藏/取消，支持仅收藏过滤
- 📋 **大图预览** — 弹窗查看完整预览图 + 详细元信息
- 📊 **统计面板** — 实时显示壁纸总数、类型分布、收藏数

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
├── app.py                  # 应用入口 + 全局 QSS 样式
├── config.py               # JSON 配置文件读写
├── build.spec              # PyInstaller 打包配置
├── core/                   # 业务逻辑层
│   ├── models.py           # Wallpaper 数据类
│   ├── db.py               # SQLite 数据库 CRUD
│   └── scanner.py          # 目录扫描 + project.json 解析
├── ui/                     # 界面层
│   ├── main_window.py      # 主窗口（网格 + 过滤 + 扫描）
│   ├── wallpaper_card.py   # 壁纸卡片组件
│   ├── filter_bar.py       # 顶部搜索过滤栏
│   └── preview_dialog.py   # 大图预览弹窗
├── docs/
│   └── DEV.md              # 开发文档
├── requirements.txt
└── README.md
```

## 📂 数据存储

所有用户数据存储在 `%USERPROFILE%\.wallpaper-manager\`：

| 文件 | 说明 |
|------|------|
| `wallpapers.db` | SQLite 数据库，壁纸索引 |
| `config.json` | 用户配置（目录路径、偏好） |

## 🔧 配置

首次运行后编辑 `%USERPROFILE%\.wallpaper-manager\config.json`：

```json
{
  "wallpaper_dirs": ["D:\\SteamLibrary\\steamapps\\workshop\\content\\431960"],
  "last_used_dir": "D:\\SteamLibrary\\steamapps\\workshop\\content\\431960",
  "grid_card_size": "medium",
  "theme": "dark"
}
```

## 📄 License

MIT
