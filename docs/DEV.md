# 开发文档

## 架构概览

```
┌──────────────────────────────────────────────────────┐
│                      app.py                          │
│                (入口 + 全局 QSS 样式)                  │
├──────────────────────────────────────────────────────┤
│                       UI 层                           │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐           │
│  │FilterBar │ │CardGrid  │ │PreviewDlg  │           │
│  │搜索/过滤  │ │网格+多选  │ │图片+视频    │           │
│  │导入/导出  │ │右键菜单   │ │QMediaPlayer│           │
│  │目录管理   │ │缩略图缓存 │ │             │           │
│  └────┬─────┘ └────┬─────┘ └─────┬──────┘           │
│       │             │             │                   │
│  ┌────▼──────┐ ┌────▼──────┐     │                  │
│  │DirManager │ │ContextMenu│     │                  │
│  │多目录管理  │ │批量操作    │     │                  │
│  └───────────┘ └───────────┘     │                  │
├──────────────────────────────────────────────────────┤
│                    Core 业务层                        │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐           │
│  │scanner.py│ │  db.py   │ │ models.py  │           │
│  │多目录扫描 │ │SQLite CRUD│ │数据模型     │           │
│  └──────────┘ └──────────┘ └────────────┘           │
│  ┌───────────────────┐ ┌──────────────────┐         │
│  │thumbnail_worker.py│ │export_worker.py  │         │
│  │后台缩略图生成      │ │导入/导出         │         │
│  └───────────────────┘ └──────────────────┘         │
├──────────────────────────────────────────────────────┤
│              config.py (配置持久化)                    │
├──────────────────────────────────────────────────────┤
│   ~/.wallpaper-manager/                              │
│   ├── wallpapers.db    (SQLite)                      │
│   ├── config.json      (用户配置)                     │
│   └── thumbs/          (缩略图缓存)                   │
└──────────────────────────────────────────────────────┘
```

## 数据模型

### Wallpaper (core/models.py)

```python
@dataclass
class Wallpaper:
    id: Optional[int]          # 数据库主键
    folder_path: str           # 壁纸文件夹绝对路径（唯一键）
    workshop_id: str           # Steam Workshop ID
    title: str                 # 壁纸标题
    wp_type: str               # 类型: video / scene / web / application
    file: str                  # 壁纸实际文件名
    preview: str               # 预览图文件名
    tags: list[str]            # 标签列表
    content_rating: str        # 内容分级
    description: str           # 描述
    scheme_color: str          # WE 主题色（"0.51373 0.54510 0.70588"）
    is_favorite: bool          # 是否收藏
```

计算属性：
- `preview_path` → 预览图绝对路径
- `wallpaper_file_path` → 壁纸文件绝对路径
- `tags_display` → 逗号分隔的标签字符串
- `type_emoji` → 类型对应的 emoji
- `scheme_color_hex` → 转换为 `#838BB4` 格式

### 数据库表结构 (core/db.py)

```sql
CREATE TABLE wallpapers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path     TEXT UNIQUE NOT NULL,
    workshop_id     TEXT DEFAULT '',
    title           TEXT DEFAULT '',
    wp_type         TEXT DEFAULT '',
    file            TEXT DEFAULT '',
    preview         TEXT DEFAULT '',
    tags            TEXT DEFAULT '[]',       -- JSON array
    content_rating  TEXT DEFAULT '',
    description     TEXT DEFAULT '',
    scheme_color    TEXT DEFAULT '',
    is_favorite     INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 核心模块 API

### scanner.py

```python
def parse_project_json(folder_path: Path) -> Optional[Wallpaper]
def scan_directory(root_dir: str, progress_callback=None) -> dict
```

### db.py

| 函数 | 说明 |
|------|------|
| `init_db()` | 创建表结构（幂等） |
| `upsert_wallpaper(wp)` | 插入或更新（按 folder_path 冲突更新） |
| `toggle_favorite(id)` | 切换收藏状态 |
| `query_wallpapers(search, wp_type, tags, favorites_only, order_by)` | 多条件查询 |
| `get_all_tags()` | 获取所有去重标签 |
| `get_stats()` | 统计信息 |
| `remove_wallpaper(path)` | 按路径删除记录 |

### thumbnail_worker.py

```python
def get_thumb_path(preview_path: str) -> Path
# 根据原图路径生成缓存路径（MD5 hash）

class ThumbnailWorker(QThread):
    progress = Signal(int, int, str)  # current, total, title
    finished = Signal(int)            # generated count
    def __init__(self, wallpapers, force=False)
    def cancel(self)
```

- 缓存目录：`~/.wallpaper-manager/thumbs/`
- 统一尺寸：320×180（16:9）
- 格式：JPEG quality=85
- 支持 PNG alpha 通道转 RGB 背景

### export_worker.py

```python
class ExportWorker(QThread):
    finished = Signal(bool, str)  # success, message
    def __init__(self, output_path, favorites_only=True)

class ImportWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(dict)       # stats
    def __init__(self, input_path)
```

导出 JSON 格式：
```json
{
  "version": "1.0",
  "exported_at": "2026-04-25T22:30:00",
  "count": 12,
  "wallpapers": [{ ... }]
}
```

## UI 组件

### WallpaperCard

- 固定尺寸：236×232（含外边距）
- 支持选中状态（蓝色边框高亮）
- 信号：`clicked`, `ctrl_clicked`, `shift_clicked`, `favorite_toggled`, `context_menu_requested`
- 优先加载缩略图缓存，回退到原始预览图

### FilterBar

- 搜索框（防抖 300ms）
- 类型/标签/排序下拉
- 收藏过滤复选框
- 📤导出 / 📥导入 / 📂目录 / 🔄扫描 按钮

### PreviewDialog

- 图片模式：QScrollArea + QLabel
- 视频模式：QMediaPlayer + QVideoWidget
- 视频控制栏：播放/暂停 + 进度条 + 时间显示
- 自动检测壁纸类型，切换显示模式
- PySide6-Multimedia 可选依赖（无则显示占位提示）

### DirManagerDialog

- QListWidget 展示目录列表（✅/❌ 标记存在状态）
- 添加/移除目录
- 扫描全部按钮

### WallpaperContextMenu

- 单选时：预览 / 打开文件夹 / 复制路径 / 收藏
- 多选时：批量收藏 / 取消收藏 / 导出选中

## 后台线程一览

| 线程 | 用途 | 不阻塞 UI |
|------|------|-----------|
| `ScanWorker` | 多目录扫描入库 | ✅ QThread |
| `ThumbnailWorker` | 缩略图生成 | ✅ QThread |
| `ExportWorker` | 导出 JSON | ✅ QThread |
| `ImportWorker` | 导入 JSON | ✅ QThread |

## 多选机制

- **普通点击**：清除其他选中，打开预览
- **Ctrl+点击**：切换当前卡片选中状态
- **Shift+点击**：从上次点击位置到当前位置范围选中
- 选中卡片显示蓝色边框 + 信息栏显示选中数量
- 右键菜单根据选中数量动态切换单选/批量操作

## 样式主题

| 元素 | 颜色 |
|------|------|
| 主背景 | `#0f0f1a` |
| 面板背景 | `#1a1a2e` |
| 输入框背景 | `#16213e` |
| 边框 | `#2a2a4a` |
| 悬停边框 | `#4a4a8a` |
| 选中边框 | `#4a9eff` |
| 按钮背景 | `#2a2a5a` |
| 强调按钮 | `#4a4a8a` |
| 文字 | `#e0e0e0` |
| 次要文字 | `#888` / `#c0c0c0` |
| 视频控制滑块 | `#4a4a8a` |

## 打包

```bash
pyinstaller build.spec
```

输出：`dist/WallpaperManager/WallpaperManager.exe`

注意：视频预览功能需要额外安装 `PySide6-Multimedia`：
```bash
pip install PySide6-Multimedia
```
