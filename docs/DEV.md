# 开发文档

## 架构概览

```
┌──────────────────────────────────────────────────────┐
│                      app.py                          │
│                (入口 + theme.py 生成 QSS)              │
├──────────────────────────────────────────────────────┤
│                  UI 层 (ui/)                          │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐           │
│  │FilterBar │ │CardGrid  │ │PreviewDlg  │           │
│  │搜索/过滤  │ │网格+多选  │ │图片+视频    │           │
│  │导入/导出  │ │右键菜单   │ │QMediaPlayer│           │
│  │目录管理   │ │缩略图缓存 │ │收藏联动     │           │
│  └────┬─────┘ └────┬─────┘ └─────┬──────┘           │
│       │             │             │                   │
│  ┌────▼──────┐ ┌────▼──────┐     │                  │
│  │DirManager │ │ContextMenu│     │                  │
│  │多目录管理  │ │批量操作    │     │                  │
│  └───────────┘ └───────────┘     │                  │
│  ┌──────────────────────────────────────┐           │
│  │ theme.py — 颜色常量 + QSS 生成        │           │
│  │ COLORS dict + generate_stylesheet()  │           │
│  └──────────────────────────────────────┘           │
├──────────────────────────────────────────────────────┤
│                  Core 业务层 (core/)                   │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐           │
│  │scanner.py│ │  db.py   │ │ models.py  │           │
│  │多目录扫描 │ │SQLite CRUD│ │数据模型     │           │
│  │          │ │+ 迁移框架 │ │             │           │
│  └──────────┘ └──────────┘ └────────────┘           │
│  ┌───────────────────┐ ┌──────────────────┐         │
│  │thumbnail_worker.py│ │export_worker.py  │         │
│  │缩略图生成 + 清理   │ │导入/导出(可取消)  │         │
│  └───────────────────┘ └──────────────────┘         │
│  ┌──────────────────────────────────────┐           │
│  │ we_controller.py — WE WebSocket PoC  │           │
│  │ (调研 + 概念验证，非生产就绪)          │           │
│  └──────────────────────────────────────┘           │
├──────────────────────────────────────────────────────┤
│              config.py (配置持久化)                    │
├──────────────────────────────────────────────────────┤
│   ~/.wallpaper-manager/                              │
│   ├── wallpapers.db    (SQLite, WAL 模式)            │
│   ├── config.json      (用户配置)                     │
│   └── thumbs/          (缩略图缓存, 自动清理)         │
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

-- Schema 版本追踪
CREATE TABLE schema_version (
    version INTEGER NOT NULL
);
```

### Schema 迁移机制

`db.py` 内置了轻量级 schema 迁移框架：

- `SCHEMA_VERSION` 常量标记当前 schema 版本（目前为 1）
- `schema_version` 表记录数据库当前版本
- `_run_migrations()` 在 `init_db()` 中自动检测版本差距并执行迁移
- 新增迁移：编写 `_migrate_vN(conn)` 函数，注册到 `_MIGRATIONS` 字典

```python
# 示例：添加 Phase 2 的壁纸设置表
SCHEMA_VERSION = 2

def _migrate_v2(conn):
    conn.execute("CREATE TABLE wallpaper_settings (...)")

_MIGRATIONS = {1: _migrate_v1, 2: _migrate_v2}
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
| `init_db()` | 创建表结构 + 执行 schema 迁移（幂等） |
| `upsert_wallpaper(wp)` | 插入或更新（按 folder_path 冲突更新） |
| `toggle_favorite(id)` | 切换收藏状态 |
| `set_favorite(id, bool)` | 强制设置收藏状态 |
| `query_wallpapers(search, wp_type, tags, favorites_only, order_by)` | 多条件查询 |
| `get_all_tags()` | 获取所有去重标签 |
| `get_stats()` | 统计信息 |
| `remove_wallpaper(path)` | 按路径删除记录 |

### thumbnail_worker.py

```python
def get_thumb_path(preview_path: str) -> Path
# 根据原图路径生成缓存路径（MD5 hash）

def cleanup_thumbs(valid_preview_paths: set[str]) -> int
# 清理过期缩略图缓存，返回删除数量

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
- 扫描后自动清理过期缓存

### export_worker.py

```python
class ExportWorker(QThread):
    finished = Signal(bool, str)  # success, message
    def __init__(self, output_path, favorites_only=True, wallpaper_ids=None)
    def cancel(self)

class ImportWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(dict)       # stats
    def __init__(self, input_path)
    def cancel(self)
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

### we_controller.py (PoC)

```python
class WallpaperEngineController:
    async def connect(self) -> bool
    async def disconnect(self)
    async def get_wallpapers(self) -> list[dict]
    async def set_wallpaper(wallpaper_id) -> bool
    async def get_status(self) -> dict
    # 同步包装器: connect_sync(), get_wallpapers_sync(), etc.
```

> ⚠️ **注意**：Wallpaper Engine 没有公开的 WebSocket 控制 API。此模块为调研 PoC，
> 尝试连接多个可能的端点。生产环境建议使用 Windows API (`SystemParametersInfo`)
> 或修改 WE 配置文件的方式。

### wallpaper_setter.py

```python
class WallpaperSetter:
    @staticmethod
    def set_wallpaper(image_path: str) -> bool
    # 通过 Windows API SystemParametersInfoW 设置桌面壁纸
    # 支持 JPG/PNG/BMP/GIF/TIFF/WebP

    @staticmethod
    def get_current_wallpaper() -> Optional[str]
    # 获取当前桌面壁纸路径（注册表 + API）

    @staticmethod
    def set_wallpaper_we(wallpaper_path: str, we_exe_path=None) -> bool
    # 通过 WE 命令行或配置文件设置动态壁纸

    @staticmethod
    def find_we_install() -> Optional[Path]
    # 自动检测 WE 安装路径（Steam 库 + 注册表 + 常见路径）

    @staticmethod
    def get_we_wallpaper_list() -> list[dict]
    # 列出所有 WE 壁纸（Steam Workshop + 本地项目）
```

- Windows-only 操作通过 `IS_WINDOWS` 平台检测守卫
- WE 安装检测：解析 Steam `libraryfolders.vdf` + 注册表 + 常见路径
- 壁纸设置：先注册表写入路径，再 `SystemParametersInfoW` 生效

### rotation_worker.py

```python
class RotationWorker(QObject):
    wallpaper_changed = Signal(str, str)  # wallpaper_id, title
    rotation_started = Signal(int, str)   # interval_minutes, mode
    rotation_stopped = Signal()
    error_occurred = Signal(str)

    def start_rotation(interval_minutes, mode)
    def stop_rotation()
    def next_wallpaper()
    def cleanup()
```

- 使用 `QTimer`（非 QThread），不阻塞 UI
- 三种模式：`random`（随机）/ `sequential`（顺序）/ `favorite`（仅收藏）
- 可选间隔：5/15/30/60/120 分钟
- 壁纸列表在每次轮换时动态刷新（支持运行中收藏变化）

## 主题系统 (ui/theme.py)

所有颜色集中在 `COLORS` 字典中，QSS 通过 `generate_stylesheet()` 函数生成：

```python
from ui.theme import COLORS, generate_stylesheet

# 使用颜色常量
label.setStyleSheet(f"color: {COLORS['text_muted']};")

# 生成完整样式表（支持自定义颜色字典，为多主题预留）
app.setStyleSheet(generate_stylesheet())
```

颜色分类：
- **bg_***: 背景色（main, panel, input, preview, info, selected, hover）
- **border_***: 边框色（default, focus, selected, button）
- **text_***: 文本色（primary, secondary, muted, dim, placeholder）
- **btn_***: 按钮色（bg, hover, pressed, scan, clear）
- **selection_***: 选择色
- **separator**: 分隔线色

## UI 组件

### WallpaperCard

- 固定尺寸：236×232（含外边距）
- 支持选中状态（蓝色边框高亮）
- 信号：`clicked`, `ctrl_clicked`, `shift_clicked`, `favorite_toggled`, `context_menu_requested`
- 优先加载缩略图缓存，回退到原始预览图
- 样式使用 `COLORS` 常量，支持主题色边框

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
- 收藏按钮切换后通过 `favorite_toggled` 信号通知主窗口同步更新

### DirManagerDialog

- QListWidget 展示目录列表（✅/❌ 标记存在状态）
- 添加/移除目录
- 扫描全部按钮

### WallpaperContextMenu

- 单选时：预览 / 打开文件夹 / 复制路径 / 收藏
- 多选时：批量收藏 / 取消收藏 / 导出选中

## 后台线程一览

| 线程 | 用途 | 可取消 | 不阻塞 UI |
|------|------|--------|-----------|
| `ScanWorker` | 多目录扫描入库 | ❌ | ✅ QThread |
| `ThumbnailWorker` | 缩略图生成 | ✅ `cancel()` | ✅ QThread |
| `ExportWorker` | 导出 JSON | ✅ `cancel()` | ✅ QThread |
| `ImportWorker` | 导入 JSON | ✅ `cancel()` | ✅ QThread |

所有线程在 `MainWindow.closeEvent` 中统一清理（cancel + wait 2s）。

## 多选机制

- **普通点击**：清除其他选中，打开预览
- **Ctrl+点击**：切换当前卡片选中状态
- **Shift+点击**：从上次点击位置到当前位置范围选中
- 选中卡片显示蓝色边框 + 信息栏显示选中数量
- 右键菜单根据选中数量动态切换单选/批量操作

## 样式主题

所有颜色定义在 `ui/theme.py` 的 `COLORS` 字典中。当前主题色板：

| 元素 | 色值 | 键名 |
|------|------|------|
| 主背景 | `#0f0f1a` | `bg_main` |
| 面板背景 | `#1a1a2e` | `bg_panel` |
| 输入框背景 | `#16213e` | `bg_input` |
| 边框 | `#2a2a4a` | `border` |
| 悬停边框 | `#4a4a8a` | `border_focus` |
| 选中边框 | `#4a9eff` | `border_selected` |
| 按钮背景 | `#2a2a5a` | `btn_bg` |
| 强调按钮 | `#4a4a8a` | `btn_scan_bg` |
| 主文字 | `#e0e0e0` | `text_primary` |
| 次要文字 | `#c0c0c0` | `text_secondary` |
| 弱化文字 | `#888` | `text_muted` |

## 测试

```bash
python -m pytest tests/ -v
```

当前 101 个测试用例（12 skipped）：

| 文件 | 用例数 | 覆盖范围 |
|------|--------|----------|
| `test_models.py` | 26 | Wallpaper 数据类属性、边界值、默认值 |
| `test_db.py` | 25 | CRUD、查询过滤、排序、标签去重、统计 |
| `test_scanner.py` | 17 | project.json 解析、畸形数据容错、Unicode |
| `test_we_controller.py` | 20 | 初始化、连接、命令、同步包装器、探索函数 |
| `test_wallpaper_setter.py` | 13 | 平台检测、VDF 解析、常量验证 |
| `test_rotation_worker.py` | 12 (12 skip) | 初始化、pick_next、刷新、生命周期（需 PySide6） |

测试策略：
- db 测试通过 `monkeypatch` 重定向到临时数据库，不污染真实数据
- scanner 测试用 `tmp_path` 创建假壁纸目录结构
- 每个测试用例独立，autouse fixture 自动初始化空库
- WE 控制器测试使用 `unittest.mock` 模拟 WebSocket

## 打包

```bash
pyinstaller build.spec
```

输出：`dist/WallpaperManager/WallpaperManager.exe`

注意：视频预览功能需要额外安装 `PySide6-Multimedia`：
```bash
pip install PySide6-Multimedia
```

## 已知限制

1. **WE WebSocket 控制不可用** — Wallpaper Engine 没有公开 API，PoC 仅供参考
2. **仅支持 Windows** — 壁纸设置功能依赖 Windows API
3. **缩略图缓存无大小限制** — 大量壁纸时 thumbs 目录可能较大（通常 <100MB）
4. **单线程扫描** — 多目录顺序扫描，大库可能较慢

## 变更日志

### v0.2.0 (2026-04-26)

- 新增 `core/we_controller.py`（WE WebSocket PoC，464 行）
- 新增 `tests/test_we_controller.py`（20 个测试）
- `context_menu.py` 新增 `apply_wallpaper` 信号
- `main_window.py` 新增 `_apply_wallpaper_from_context()` 处理方法
- `requirements.txt` 新增 `websockets>=12.0`
- 全部 88 个测试通过

### v0.1.0 (2026-04-25)

- 初始版本，Phase 1 核心功能全部完成
