# 开发文档

## 架构概览

```
┌──────────────────────────────────────────────────────┐
│                      app.py                          │
│          (入口 + config 读取主题 + QSS 生成)           │
├──────────────────────────────────────────────────────┤
│                  UI 层 (ui/)                          │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐           │
│  │FilterBar │ │CardGrid  │ │PreviewDlg  │           │
│  │搜索/过滤  │ │网格+多选  │ │图片+视频    │           │
│  │导入/导出  │ │可调尺寸   │ │收藏联动     │           │
│  │目录管理   │ │缩略图缓存 │ │             │           │
│  │主题切换   │ │           │ │             │           │
│  │尺寸选择   │ │           │ │             │           │
│  │分级过滤   │ │           │ │             │           │
│  └────┬─────┘ └────┬─────┘ └─────┬──────┘           │
│       │             │             │                   │
│  ┌────▼──────┐ ┌────▼──────┐ ┌────▼──────┐          │
│  │DirManager │ │ContextMenu│ │TagManager │          │
│  │多目录管理  │ │批量操作    │ │标签管理    │          │
│  └───────────┘ └───────────┘ └───────────┘          │
│  ┌──────────────────────────────────────┐           │
│  │ theme.py — 多主题系统 + QSS 生成       │           │
│  │ THEMES + set_theme() + COLORS dict   │           │
│  │ DARK_THEME / LIGHT_THEME             │           │
│  └──────────────────────────────────────┘           │
├──────────────────────────────────────────────────────┤
│                  Core 业务层 (core/)                   │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐           │
│  │scanner.py│ │  db.py   │ │ models.py  │           │
│  │多目录扫描 │ │SQLite CRUD│ │数据模型     │           │
│  │          │ │+ 迁移框架 │ │             │           │
│  │          │ │+ 高级搜索 │ │             │           │
│  │          │ │+ 分级过滤 │ │             │           │
│  └──────────┘ └──────────┘ └────────────┘           │
│  ┌───────────────────┐ ┌──────────────────┐         │
│  │thumbnail_worker.py│ │export_worker.py  │         │
│  │缩略图生成 + 清理   │ │导入/导出(可取消)  │         │
│  └───────────────────┘ └──────────────────┘         │
│  ┌───────────────────┐ ┌──────────────────┐         │
│  │wallpaper_setter.py│ │rotation_worker.py│         │
│  │壁纸设置(API+CLI)  │ │定时轮换          │         │
│  └───────────────────┘ └──────────────────┘         │
│  ┌───────────────────┐ ┌──────────────────┐         │
│  │  tag_manager.py   │ │ version_check.py │         │
│  │标签重命名/合并/删除│ │GitHub版本检查     │         │
│  └───────────────────┘ └──────────────────┘         │
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

- `SCHEMA_VERSION` 常量标记当前 schema 版本（目前为 2）
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
| `upsert_wallpaper(wp)` | 插入或更新（按 folder_path 冲突更新；有意不覆盖 is_favorite） |
| `toggle_favorite(id)` | 切换收藏状态，返回新状态 |
| `set_favorite(id, bool)` | 强制设置收藏状态 |
| `query_wallpapers(search, wp_type, tags, favorites_only, order_by, search_mode, tags_mode, exclude_tags, content_rating)` | 多条件查询 |
| `get_all_tags()` | 获取所有去重标签（字母排序） |
| `get_all_ratings()` | 获取所有去重内容分级（按出现频次降序） |
| `get_stats()` | 统计信息（total / favorites / by_type） |
| `remove_wallpaper(path)` | 按路径删除记录 |
| `rename_tag(old, new)` | 重命名标签，返回受影响壁纸数 |
| `merge_tags(sources, target)` | 合并多个标签为一个，返回受影响壁纸数 |
| `delete_tag(name)` | 从所有壁纸中删除标签，返回受影响壁纸数 |
| `update_wallpaper_tags(id, tags)` | 直接更新指定壁纸的标签列表 |
| `get_tag_stats()` | 标签使用次数统计（`[{"name": ..., "count": ...}]`，按次数降序） |
| `backup_database(max_backups)` | 备份数据库文件，返回备份路径或 None |

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

### wallpaper_setter.py

```python
class WallpaperSetter:
    @staticmethod
    def set_wallpaper(image_path: str, style: str = "stretch") -> bool
    # 通过 Windows API SystemParametersInfoW 设置桌面壁纸
    # 支持 JPG/PNG/BMP/GIF/TIFF/WebP

    @staticmethod
    def get_current_wallpaper() -> Optional[str]
    # 获取当前桌面壁纸路径（注册表 + API）

    @staticmethod
    def set_wallpaper_we(wallpaper_path, we_exe_path=None, monitor=None) -> bool
    # 通过官方 CLI 设置 WE 动态壁纸
    # 格式: wallpaper64.exe -control openWallpaper -file <path> [-monitor N]

    @staticmethod
    def find_we_install() -> Optional[Path]
    # 自动检测 WE 安装路径（Steam 库 + 注册表 + 常见路径）

    # WE CLI 辅助命令
    @staticmethod
    def we_pause(we_exe_path=None) -> bool
    @staticmethod
    def we_play(we_exe_path=None) -> bool
    @staticmethod
    def we_stop(we_exe_path=None) -> bool
    @staticmethod
    def we_mute(we_exe_path=None) -> bool
    @staticmethod
    def we_unmute(we_exe_path=None) -> bool
    @staticmethod
    def we_next_wallpaper(we_exe_path=None) -> bool
    @staticmethod
    def we_get_current_wallpaper(monitor=None) -> Optional[str]
```

- Windows-only 操作通过 `IS_WINDOWS` 平台检测守卫
- WE CLI 参考: https://help.wallpaperengine.io/en/functionality/cli.html
- `_find_we_exe()`: 统一 WE 可执行文件查找（wallpaper64.exe → wallpaper32.exe）
- `_resolve_we_target()`: 根据壁纸类型解析 `-file` 参数值
  - Scene → `project.json`
  - Video → `.mp4` 文件
  - Web → `index.html`
- WE 安装检测：解析 Steam `libraryfolders.vdf` + 注册表 + 常见路径
- 静态壁纸设置：先注册表写入路径，再 `SystemParametersInfoW` 生效

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

### tag_manager.py

```python
def rename_tag(old_name: str, new_name: str) -> int
def merge_tags(source_tags: list[str], target_tag: str) -> int
def delete_tag(tag_name: str) -> int
def get_tag_stats() -> list[dict]  # [{"name": "anime", "count": 42}, ...]
```

- 底层委托 `db.py` 执行，本模块负责日志记录
- `db.py` 中的实现：遍历匹配的壁纸 → 修改 tags JSON 数组 → 去重 → commit
- `TagManagerDialog`（`ui/tag_manager_dialog.py`）提供可视化管理界面

### version_check.py

```python
def _parse_version(v: str) -> tuple[int, ...]
def fetch_latest_release() -> Optional[dict]

class VersionCheckWorker(QThread):
    result = Signal(dict)  # {"has_update": bool, "current": str, "latest": str, "url": str}
    def __init__(self, current_version: str, parent=None)
```

- 启动时在后台线程请求 GitHub API（10s 超时）
- 版本比较：`v0.4.1` → `(0, 4, 1)` 元组比较
- 无更新时静默；有更新时通过 `result` 信号通知 UI 弹窗
- `app.py` 中 `window._version_checker` 引用防止 QThread 被 GC 回收

### db.py 备份机制

```python
def backup_database(max_backups: int = 3) -> Optional[Path]
```

- `init_db()` 检测到需要迁移时自动调用备份
- 备份位置：`~/.wallpaper-manager/backups/wallpapers_YYYYMMDD_HHMMSS.db`
- 自动清理：保留最近 `max_backups` 份，超出按修改时间淘汰
- 使用 `shutil.copy2` 保留文件元数据

### db.py 高级搜索

`query_wallpapers()` 新增参数：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `search_mode` | str | `"simple"` | `simple`(LIKE) / `regex` / `exact` |
| `tags_mode` | str | `"any"` | `any`(匹配任一) / `all`(匹配全部) |
| `exclude_tags` | list | None | 排除的标签列表 |

- 正则搜索在 SQLite 引擎侧通过自定义 `REGEXP` 函数过滤（`db.py` 注册 `_sqlite_regexp`），无效正则直接返回空结果（不抛异常）
- 排除标签在 Python 侧后处理

## 主题系统 (ui/theme.py)

支持多主题切换。所有颜色集中在主题字典中，QSS 通过 `generate_stylesheet()` 函数生成：

```python
from ui.theme import COLORS, generate_stylesheet, set_theme, THEMES

# 切换主题（原地更新 COLORS，所有 import 引用自动生效）
set_theme("light")   # 切到亮色
set_theme("dark")    # 切回暗色

# 生成完整样式表
app.setStyleSheet(generate_stylesheet())           # 当前主题
app.setStyleSheet(generate_stylesheet("light"))    # 指定主题

# 查看可用主题
get_theme_names()  # ["dark", "light"]

# 注册自定义主题
register_theme("ocean", { ... })
```

### 内置主题

| 主题 | 说明 |
|------|------|
| `dark` | 暗色主题（默认），深蓝背景 + 浅色文字 |
| `light` | 亮色主题，浅灰背景 + 深色文字 |

### 主题切换机制

1. **启动时**：`app.py` 从 `config.json` 读取 `theme` 字段，调用 `set_theme()` 初始化
2. **运行时**：FilterBar 主题按钮（🌙/☀️）触发 `theme_changed` 信号
3. **MainWindow** 接收信号 → `set_theme()` → `generate_stylesheet()` → `app.setStyleSheet()`
4. **持久化**：保存到 `config.json`，下次启动自动应用

### `set_theme()` 原地更新策略

`COLORS` 是模块级字典。`set_theme()` 使用 `COLORS.clear()` + `COLORS.update()` 而非重新赋值，
确保通过 `from ui.theme import COLORS` 导入的引用不会失效。

### 主题键一致性校验

模块加载时自动验证所有注册主题的键集合与 `DARK_THEME` 一致，缺失或多余的键会抛出 `ValueError`。

### 颜色分类

- **bg_***: 背景色（main, panel, input, preview, info, selected, hover, dropdown）
- **border_***: 边框色（default, focus, selected, selected_hover, button）
- **text_***: 文本色（primary, secondary, muted, dim, placeholder）
- **btn_***: 按钮色（bg, hover, pressed, scan, clear）
- **selection_***: 选择色
- **separator**: 分隔线色

## UI 组件

### WallpaperCard

- 可调尺寸：small(160×120) / medium(220×160) / large(320×240)
- 尺寸通过 `CARD_SIZES` 字典预设，`get_card_dimensions(size)` 查询
- `__init__` 接受 `size` 参数，默认 `"medium"`
- 支持选中状态（蓝色边框高亮）
- 信号：`clicked`, `ctrl_clicked`, `shift_clicked`, `favorite_toggled`, `context_menu_requested`
- 优先加载缩略图缓存，回退到原始预览图
- 样式使用 `COLORS` 常量，支持主题色边框

### FilterBar

- 搜索框（防抖 300ms）+ 搜索模式切换（简单/正则/精确）
- 类型/排序下拉
- 标签多选弹出面板 + 排除标签
- 收藏过滤复选框
- 📤导出 / 📥导入 / 📂目录 / 🔄扫描 按钮
- 🔄 自动轮换按钮（右键设置间隔和模式）
- 📐 卡片尺寸下拉（小/中/大），触发 `card_size_changed` 信号
- 🌙/☀️ 主题切换按钮，触发 `theme_changed` 信号
- 🏷️ 标签管理按钮

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
| `VersionCheckWorker` | 检查 GitHub 最新 Release | ❌ | ✅ QThread |

所有线程在 `MainWindow.closeEvent` 中统一清理（cancel + wait 2s）。`VersionCheckWorker` 的引用保存在 `window._version_checker` 以防 GC 提前回收。

## 多选机制

- **普通点击**：清除其他选中，打开预览
- **Ctrl+点击**：切换当前卡片选中状态
- **Shift+点击**：从上次点击位置到当前位置范围选中
- 选中卡片显示蓝色边框 + 信息栏显示选中数量
- 右键菜单根据选中数量动态切换单选/批量操作

## 样式主题

颜色定义在 `ui/theme.py` 的主题字典中。内置 `DARK_THEME`（暗色）和 `LIGHT_THEME`（亮色），通过 `THEMES` 字典注册。

暗色主题色板：

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

亮色主题色板：

| 元素 | 色值 | 键名 |
|------|------|------|
| 主背景 | `#f5f5f7` | `bg_main` |
| 面板背景 | `#ffffff` | `bg_panel` |
| 输入框背景 | `#e8e8ed` | `bg_input` |
| 边框 | `#c8c8d0` | `border` |
| 悬停边框 | `#8888b0` | `border_focus` |
| 选中边框 | `#4a7aff` | `border_selected` |
| 按钮背景 | `#e0e0e8` | `btn_bg` |
| 强调按钮 | `#4a7aff` | `btn_scan_bg` |
| 主文字 | `#1a1a2e` | `text_primary` |
| 次要文字 | `#3a3a50` | `text_secondary` |
| 弱化文字 | `#888898` | `text_muted` |

## 测试

```bash
python -m pytest tests/ -v
```

当前 205 个测试用例（rotation_worker 12 个需 PySide6 显示环境）：

| 文件 | 用例数 | 覆盖范围 |
|------|--------|----------|
| `test_db.py` | 40 | CRUD、查询过滤、排序、标签去重、统计、内容分级 |
| `test_tag_manager.py` | 33 | 标签管理、重命名、合并、删除 |
| `test_wallpaper_setter.py` | 31 | 平台检测、VDF 解析、常量、WE CLI、目标解析 |
| `test_models.py` | 27 | Wallpaper 数据类属性、边界值、默认值 |
| `test_advanced_search.py` | 27 | 高级搜索、正则、精确匹配、排除标签 |
| `test_scanner.py` | 16 | project.json 解析、畸形数据容错、Unicode |
| `test_theme.py` | 13 | 主题切换、键一致性、样式表生成 |
| `test_rotation_worker.py` | 12 | 初始化、pick_next、刷新、生命周期（需 PySide6） |

测试策略：
- db 测试通过 `monkeypatch` 重定向到临时数据库，不污染真实数据
- scanner 测试用 `tmp_path` 创建假壁纸目录结构
- wallpaper_setter 测试用 `unittest.mock` 模拟 subprocess 调用
- 每个测试用例独立，autouse fixture 自动初始化空库

## 打包

```bash
python scripts/build.py          # 跨平台打包脚本（推荐）
build.bat                        # Windows 一键打包
pyinstaller build.spec           # 直接调用 PyInstaller
```

输出：`dist/WallpaperManager/WallpaperManager.exe`

`scripts/build.py` 流程：clean → 检查依赖 → PyInstaller → verify → 打开输出目录。
支持 `--clean-only`、`--no-open`、`--spec` 参数。

注意：视频预览功能需要额外安装 `PySide6-Multimedia`：
```bash
pip install PySide6-Multimedia
```

## 已知限制

1. **WE WebSocket 控制不可用** — Wallpaper Engine 没有公开 API，相关代码已清理
2. **仅支持 Windows** — 壁纸设置功能依赖 Windows API 和 WE 官方 CLI
3. **无自动更新机制** — 已集成 GitHub Release 版本检查，但需用户手动下载

## Code Review 记录

### 2026-04-26 全面审查

**已修复问题：**

| # | 严重度 | 文件 | 问题 | 修复 |
|---|--------|------|------|------|
| 1 | 🟡 中 | `core/db.py` | `query_wallpapers` 使用可变默认参数 `tags: list[str] = None` | 改为 `list[str] \| None = None` |
| 2 | 🟡 中 | `core/wallpaper_setter.py` | `_we_simple_command` 注释为 fire-and-forget 但实际 `proc.wait(timeout=5)` 阻塞 5 秒 | 改为 `DEVNULL` + 不等待 |
| 3 | 🟡 中 | `ui/main_window.py` | `_on_theme_change` 中 `stats_label` 使用 `text_muted` 硬编码，主题切换后对比度不足 | 统一改为 `text_secondary` |
| 4 | 🟢 低 | `ui/main_window.py` | `_populate_grid` 空状态提示使用 `text_muted`，亮色主题下可读性差 | 改为 `text_secondary` |
| 5 | 🟢 低 | `core/export_worker.py` | `run()` 在查询后未检查 `_cancelled` 标志 | 查询后增加取消检查 |
| 6 | 🟢 低 | `config.py` | 函数缺少类型注解和 docstring | 补齐 |

**审查结论：**

- 核心业务逻辑（db/scanner/models）质量良好，SQL 参数化查询无注入风险
- UI 层 inline 样式需注意主题切换后的一致性（已部分修复）
- 多线程模型合理：ScanWorker/ThumbnailWorker/ExportWorker/ImportWorker 均为 QThread，closeEvent 统一清理
- 测试覆盖充分，monkeypatch 隔离策略正确

### 2026-04-26 性能优化（三个已知限制）

| # | 问题 | 方案 | 文件 |
|---|------|------|------|
| 1 | 正则搜索大库加载全部记录到 Python | 注册 SQLite 自定义 `REGEXP` 函数，正则过滤下推到数据库引擎 | `core/db.py` |
| 2 | 缩略图缓存无上限 | 新增 LRU 淘汰机制（默认上限 500MB），按文件 atime 排序淘汰最久未访问的 | `core/thumbnail_worker.py` |
| 3 | 单线程扫描大库慢 | `parse_project_json` 改用 `ThreadPoolExecutor(8)` 并行解析，数据库批量写入改用单事务 | `core/scanner.py` |

**Code Review 修复（第二轮）：**

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| 1 | `core/scanner.py` | 每个壁纸单独 `upsert_wallpaper()` 开连接 + commit，500 张 = 500 次事务 | 改为单事务批量写入（`with get_connection()` + `conn.commit()`） |
| 2 | `core/thumbnail_worker.py` | `_evict_lru` 日志释放空间计算有 bug（`_get_cache_size() - current_size` 为负值） | 用 `original_size - current_size` 计算实际释放量 |

### 2026-04-26 工程质量提升审查

**本次变更范围：** 版本检查 / 数据备份 / 日志持久化 / 扫描容错 / extra_data / 多目录并行 / 清理 deprecated

**已修复问题：**

| # | 严重度 | 文件 | 问题 | 修复 |
|---|--------|------|------|------|
| 1 | 🟡 中 | `core/db.py` | `_migrate_v2` ALTER TABLE 与 CREATE TABLE 冲突（CREATE TABLE 已含 extra_data 列时迁移报 duplicate column） | 迁移改为幂等：先 `PRAGMA table_info` 检查列是否存在 |
| 2 | 🟡 中 | `core/scanner.py` | `tags` 字段未校验类型，混入整数/对象时 `json.dumps` 可能异常 | 增加 `isinstance` 校验，非列表降级为空列表，混入数字自动转字符串 |
| 3 | 🟢 低 | `core/scanner.py` | `project.json` 顶层非对象（如数组）时 `data.get()` 抛 AttributeError | 增加 `isinstance(data, dict)` 前置检查 |
| 4 | 🟢 低 | `core/db.py` | `backup_database` docstring 声称返回值与实现不一致 | 修正为"数据库不存在或备份失败返回 None" |
| 5 | 🟢 低 | `core/scanner.py` | version 字段注释块未完成（残留空注释行） | 合并为单行注释 |

**审查结论：**

- **版本检查**（`version_check.py`）：网络请求有 10s 超时，`TimeoutError` 被 `OSError` 捕获，异常安全 ✅
- **数据库备份**：迁移前自动备份 + 最多保留 3 份，`shutil.copy2` 保留元数据 ✅
- **扫描容错**：标签类型校验 + 顶层类型检查 + 错误详情收集，三重防护 ✅
- **多目录并行**：`ThreadPoolExecutor(max_workers=min(N, 4))` 限制并发，避免资源争用 ✅
- **extra_data 保留**：`_PARSED_KEYS` frozenset 精确控制已解析字段，其余完整保留 ✅
- **GC 防护**：`window._version_checker` 防止 QThread 被提前回收 ✅
- **测试覆盖**：205 个测试全部通过，新增 18 个覆盖标签校验/extra_data/Schema 迁移/备份 ✅

## 变更日志

### v0.5.0 (2026-04-26) — 工程质量全面提升

**新增：**
- `core/version_check.py` — GitHub Release 版本检查（后台线程 + 10s 超时 + 弹窗提示）
- `app.py` — 日志文件持久化（`~/.wallpaper-manager/logs/`，5MB 轮转 3 份）
- `core/db.py` — Schema v2（`extra_data` 列）+ 迁移前自动备份（保留 3 份）
- `core/models.py` — `Wallpaper.extra_data` 字段

**改进：**
- `core/scanner.py` — 非壁纸容错：tags 类型校验 + 顶层类型检查 + extra_data 保留 + 错误详情收集
- `ui/main_window.py` — 多目录并行扫描（`ThreadPoolExecutor`）+ 错误详情弹窗
- 测试用例 187 → 205（+18）

**清理：** 删除 `deprecated/` 目录

### v0.3.0 (2026-04-26)

- 新增多主题支持：`DARK_THEME` + `LIGHT_THEME`，`THEMES` 注册表，`set_theme()` 原地更新
- `generate_stylesheet()` 新增 `theme_name` 参数（向后兼容 `colors` 参数）
- `app.py` 启动时从 config 读取主题并应用
- `FilterBar` 新增主题切换按钮（🌙/☀️）和卡片尺寸下拉（小/中/大）
- `WallpaperCard` 支持动态尺寸：`CARD_SIZES` 预设 + `size` 参数
- `MainWindow` 主题切换保存 config + 刷新样式表，尺寸切换重建网格
- 新增 `core/tag_manager.py` + `ui/tag_manager_dialog.py`（标签重命名/合并/删除）
- `db.py` 新增 `rename_tag()` / `merge_tags()` / `delete_tag()` / `get_tag_stats()` / `update_wallpaper_tags()`
- `db.py` `query_wallpapers()` 新增 `search_mode`（simple/regex/exact）、`tags_mode`（any/all）、`exclude_tags`
- `FilterBar` 新增搜索模式切换按钮、标签多选弹出面板、排除标签按钮
- 新增 `scripts/build.py` 跨平台打包脚本
- 更新 `build.spec` / `build.bat` 包含所有新模块
- 新增 `tests/test_tag_manager.py`（33 个测试）+ `tests/test_advanced_search.py`（27 个测试）
- `theme.py` 模块加载时自动校验主题键一致性
- `config.py` 默认配置新增 `card_size` 和 `theme` 字段
- 全部 186 个测试通过（12 skipped）

### v0.4.0 (2026-04-26)

- `core/wallpaper_setter.py` 重写 WE 壁纸设置
  - 使用官方 CLI `-control openWallpaper -file <path>` 替代 `-path`
  - 新增 `_resolve_we_target()` 按壁纸类型解析目标文件（scene→project.json, video→.mp4, web→index.html）
  - 新增 `_find_we_exe()` 统一 WE 可执行文件查找
  - 新增 `-monitor` 多显示器支持
  - 新增 `we_pause/play/stop/mute/unmute/next_wallpaper/get_current` 辅助命令
  - 移除无文档依据的 `_apply_we_config` 配置文件回退
  - 移除 `get_we_wallpaper_list()`（与 `core/scanner.py` 重复）
- `core/db.py` 新增内容分级筛选
  - `query_wallpapers()` 新增 `content_rating` 参数
  - `get_all_ratings()` 获取所有去重分级
- `ui/filter_bar.py` 新增 `rating_combo` 内容分级下拉框 + `rating_changed` 信号
- `ui/main_window.py` 新增 `_on_rating_filter` / `_update_ratings`
- `ui/main_window.py` 主题切换后刷新所有卡片 inline 样式 + filter_bar 分隔线
- `ui/context_menu.py` / `ui/filter_bar.py` 非 Windows 平台隐藏壁纸设置/轮换 UI
- `core/we_controller.py` → `deprecated/we_controller.py`（WE 无公开 WebSocket API）
- 移除 `websockets` 依赖
- `tests/test_wallpaper_setter.py` 重写（15→31 用例），`tests/test_db.py` 新增 5 个内容分级测试
- 全部 205 个测试通过

### v0.4.1 (2026-04-26)

- `core/wallpaper_setter.py` `_apply_we_cli` 改用 Popen 非阻塞（不再阻塞 UI 线程）
- `core/wallpaper_setter.py` `_find_we_exe` 首次查找后缓存结果（`_we_exe_cache` 模块变量）
- `core/wallpaper_setter.py` `_we_simple_command` 改用 Popen 非阻塞
- `ui/filter_bar.py` 内容区包裹 `QScrollArea`，窗口过窄时水平滚动替代重叠
- `ui/theme.py` 亮色主题 `text_muted` / `text_dim` / `text_placeholder` 对比度提升至 WCAG AA
- `ui/theme.py` 新增 `#filterBarScroll` / `#filterBarContainer` 透明背景规则

### v0.2.0 (2026-04-26)

- 新增 `core/wallpaper_setter.py`（壁纸设置，Windows API + WE 命令行，514 行）
- 新增 `core/rotation_worker.py`（定时轮换，QTimer，200 行）
- 新增 `core/we_controller.py`（WE WebSocket PoC，464 行）
- 新增 `tests/test_wallpaper_setter.py`（13 个测试）
- 新增 `tests/test_rotation_worker.py`（12 个测试）
- 新增 `tests/test_we_controller.py`（20 个测试）
- 右键菜单新增"设为桌面壁纸"和"设为 WE 壁纸"
- FilterBar 新增轮换按钮 + 间隔/模式设置
- `requirements.txt` 新增 `websockets>=12.0`
- 全部 103 个测试通过（12 skipped）

### v0.1.0 (2026-04-25)

- 初始版本，Phase 1 核心功能全部完成
