# 需求文档 (PRD)

> **项目名称**: Wallpaper Manager
> **版本**: v0.2.0
> **日期**: 2026-04-26
> **状态**: Phase 2 完成

---

## 1. 项目概述

### 1.1 背景

Wallpaper Engine 是 Steam 平台上的动态壁纸工具，用户通过 Workshop 订阅壁纸后，壁纸文件存储在本地 `steamapps/workshop/content/431960/` 目录下。每个壁纸是一个独立文件夹，包含 `project.json` 元数据、预览图和壁纸文件。

目前 Wallpaper Engine 自带的库管理界面功能有限，缺乏高效的搜索、筛选和批量管理能力，尤其在壁纸数量较多时体验较差。

### 1.2 目标

开发一个本地桌面工具，作为 Wallpaper Engine 的**库管理前端**，提供：
- 快速扫描和索引本地壁纸库
- 可视化网格预览
- 多维度搜索和过滤
- 收藏管理

### 1.3 目标用户

- Wallpaper Engine 活跃用户（本地壁纸 100+ 张）
- 需要高效管理和筛选壁纸的用户

### 1.4 技术选型

| 维度 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | 开发效率高，生态丰富 |
| GUI 框架 | PySide6 (Qt6) | 原生桌面体验，图片展示能力强，支持视频预览扩展 |
| 数据库 | SQLite | 零配置，单文件，适合本地工具 |
| 打包 | PyInstaller | 生成独立 exe，用户无需安装 Python |

---

## 2. 用户场景

### 场景一：首次导入

1. 用户启动程序
2. 程序自动检测 Wallpaper Engine workshop 目录
3. 用户确认或手动选择目录
4. 程序扫描目录，解析所有 `project.json`，建立索引
5. 显示壁纸网格，展示扫描结果统计

### 场景二：日常浏览

1. 用户启动程序，加载已有索引
2. 在网格中浏览壁纸缩略图
3. 通过搜索框输入关键词快速定位
4. 通过类型/标签下拉过滤
5. 点击卡片查看大图和详细信息

### 场景三：收藏管理

1. 浏览过程中，点击 ❤️ 收藏喜欢的壁纸
2. 勾选「仅收藏」过滤，快速查看收藏列表
3. 支持按收藏优先排序

### 场景四：库更新

1. 用户在 Wallpaper Engine 中订阅了新壁纸
2. 点击「扫描目录」按钮
3. 程序增量更新索引（新增/更新/移除）
4. 新壁纸出现在网格中

---

## 3. 功能需求

### 3.1 目录扫描

| 编号 | 需求 | 优先级 | 状态 |
|------|------|--------|------|
| F-001 | 自动检测 Wallpaper Engine workshop 目录 | P0 | ✅ 已实现 |
| F-002 | 手动选择任意目录 | P0 | ✅ 已实现 |
| F-003 | 解析 `project.json` 提取元数据 | P0 | ✅ 已实现 |
| F-004 | 增量扫描（新增/更新/移除检测） | P0 | ✅ 已实现 |
| F-005 | 扫描进度实时显示 | P1 | ✅ 已实现 |
| F-006 | 后台线程扫描，不阻塞 UI | P0 | ✅ 已实现 |

**自动检测逻辑**:
- 扫描常见 Steam 安装路径
- 解析 `libraryfolders.vdf` 发现 Steam 库目录
- 拼接 `steamapps/workshop/content/431960` 定位 WE 壁纸

**project.json 字段映射**:

| JSON 字段 | 用途 |
|-----------|------|
| `title` | 壁纸标题 |
| `type` | 类型（video/scene/web/application） |
| `file` | 壁纸文件名 |
| `preview` | 预览图文件名 |
| `tags` | 标签列表 |
| `workshopid` | Steam Workshop ID |
| `contentrating` | 内容分级 |
| `description` | 描述 |
| `general.properties.schemecolor.value` | 主题色 |

### 3.2 网格预览

| 编号 | 需求 | 优先级 | 状态 |
|------|------|--------|------|
| F-010 | 卡片式网格布局展示壁纸 | P0 | ✅ 已实现 |
| F-011 | 显示缩略图（preview.jpg） | P0 | ✅ 已实现 |
| F-012 | 显示壁纸标题 + 类型图标 | P0 | ✅ 已实现 |
| F-013 | 卡片底部显示主题色条 | P1 | ✅ 已实现 |
| F-014 | 窗口缩放时自动调整列数 | P0 | ✅ 已实现 |
| F-015 | 无壁纸时显示空状态提示 | P1 | ✅ 已实现 |

**卡片规格**:
- 固定尺寸：220×160（预览图）+ 72（信息区）
- 悬停高亮边框
- 收藏按钮（❤️/🤍）

### 3.3 搜索与过滤

| 编号 | 需求 | 优先级 | 状态 |
|------|------|--------|------|
| F-020 | 按标题关键词搜索 | P0 | ✅ 已实现 |
| F-021 | 按标签关键词搜索 | P0 | ✅ 已实现 |
| F-022 | 按类型下拉过滤（视频/场景/网页） | P0 | ✅ 已实现 |
| F-023 | 按标签下拉过滤 | P1 | ✅ 已实现 |
| F-024 | 仅显示收藏 | P0 | ✅ 已实现 |
| F-025 | 排序：标题/类型/最近添加/收藏优先 | P1 | ✅ 已实现 |
| F-026 | 搜索防抖（300ms） | P1 | ✅ 已实现 |

### 3.4 大图预览

| 编号 | 需求 | 优先级 | 状态 |
|------|------|--------|------|
| F-030 | 点击卡片弹出预览窗口 | P0 | ✅ 已实现 |
| F-031 | 显示完整预览图（可滚动） | P0 | ✅ 已实现 |
| F-032 | 显示详细元信息 | P0 | ✅ 已实现 |
| F-033 | 打开壁纸所在文件夹 | P1 | ✅ 已实现 |
| F-034 | ESC 快捷键关闭 | P1 | ✅ 已实现 |

**预览窗口元信息**:
- 标题、类型、标签、内容分级
- 文件名、Workshop ID
- 主题色色块

### 3.5 收藏管理

| 编号 | 需求 | 优先级 | 状态 |
|------|------|--------|------|
| F-040 | 卡片上一键切换收藏 | P0 | ✅ 已实现 |
| F-041 | 预览窗口中切换收藏 | P0 | ✅ 已实现 |
| F-042 | 收藏状态持久化到数据库 | P0 | ✅ 已实现 |
| F-043 | 统计面板显示收藏数量 | P1 | ✅ 已实现 |

### 3.6 统计面板

| 编号 | 需求 | 优先级 | 状态 |
|------|------|--------|------|
| F-050 | 显示壁纸总数 | P0 | ✅ 已实现 |
| F-051 | 按类型分布统计 | P1 | ✅ 已实现 |
| F-052 | 收藏数量统计 | P1 | ✅ 已实现 |

---

## 4. 非功能需求

### 4.1 性能

| 编号 | 需求 | 目标值 |
|------|------|--------|
| NF-001 | 扫描 200 个壁纸文件夹 | < 5 秒 |
| NF-002 | 网格渲染 200 张卡片 | < 1 秒 |
| NF-003 | 搜索响应（含防抖） | < 200ms |
| NF-004 | 内存占用 | < 200MB |

### 4.2 兼容性

| 编号 | 需求 | 说明 |
|------|------|------|
| NF-010 | 操作系统 | Windows 10/11 |
| NF-011 | Python 版本 | 3.10+ |
| NF-012 | 分辨率 | 支持 1080p 及以上，适配 DPI 缩放 |
| NF-013 | 壁纸类型 | video / scene / web / application |

### 4.3 数据安全

| 编号 | 需求 | 说明 |
|------|------|------|
| NF-020 | 只读访问壁纸文件 | 不修改、不删除原始壁纸文件 |
| NF-021 | 本地数据存储 | 数据库和配置仅存于本地，不联网 |
| NF-022 | 数据库 WAL 模式 | 防止意外中断导致数据损坏 |

### 4.4 可用性

| 编号 | 需求 | 说明 |
|------|------|------|
| NF-030 | 暗色主题 | 长时间使用不刺眼 |
| NF-031 | 中文界面 | 适配中文标题和标签 |
| NF-032 | 操作可逆 | 收藏等操作可撤销 |

---

## 5. 数据存储

### 5.1 存储位置

```
%USERPROFILE%\.wallpaper-manager\
├── wallpapers.db        # SQLite 数据库
├── config.json          # 用户配置
└── thumbs\              # (预留) 缩略图缓存
```

### 5.2 数据库表

**wallpapers 表**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| folder_path | TEXT | UNIQUE, NOT NULL | 壁纸文件夹路径 |
| workshop_id | TEXT | | Steam Workshop ID |
| title | TEXT | | 壁纸标题 |
| wp_type | TEXT | | 类型 |
| file | TEXT | | 壁纸文件名 |
| preview | TEXT | | 预览图文件名 |
| tags | TEXT | | JSON array 序列化 |
| content_rating | TEXT | | 内容分级 |
| description | TEXT | | 描述 |
| scheme_color | TEXT | | 主题色 RGB |
| is_favorite | INTEGER | DEFAULT 0 | 收藏标记 |
| created_at | TIMESTAMP | DEFAULT NOW | 入库时间 |

**索引**: workshop_id, title, wp_type, is_favorite

### 5.3 配置文件

```json
{
  "wallpaper_dirs": ["D:\\SteamLibrary\\steamapps\\workshop\\content\\431960"],
  "last_used_dir": "D:\\SteamLibrary\\steamapps\\workshop\\content\\431960",
  "grid_card_size": "medium",
  "theme": "dark"
}
```

---

## 6. UI 设计

### 6.1 主窗口布局

```
┌─────────────────────────────────────────────────┐
│  🔍 搜索...  │ 标签▼ │ 类型▼ │ ❤收藏 │ ⚙设置 │  ← FilterBar
├─────────────────────────────────────────────────┤
│         共 428 张壁纸 · ❤️ 12 收藏 · 🎬 380 视频  │  ← StatsLabel
├─────────────────────────────────────────────────┤
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐    │
│ │预览│ │预览│ │预览│ │预览│ │预览│ │预览│    │
│ │    │ │    │ │    │ │    │ │    │ │    │    │  ← ScrollArea
│ ├────┤ ├────┤ ├────┤ ├────┤ ├────┤ ├────┤    │    + GridLayout
│ │标题│ │标题│ │标题│ │标题│ │标题│ │标题│    │
│ │ ❤ ▶│ │ ❤ ▶│ │ ❤ ▶│ │ ❤ ▶│ │ ❤ ▶│ │ ❤ ▶│    │
│ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘    │
├─────────────────────────────────────────────────┤
│ 就绪                                进度条 ███░ │  ← StatusBar
└─────────────────────────────────────────────────┘
```

### 6.2 预览窗口布局

```
┌─────────────────────────────────────────┐
│  📋 壁纸标题                    ─ □ ✕  │
├─────────────────────────────────────────┤
│                                         │
│            ┌───────────────┐            │
│            │               │            │
│            │   完整预览图    │            │
│            │               │            │
│            └───────────────┘            │
│                                         │
├─────────────────────────────────────────┤
│ 标题: xxx          │ 🤠 收藏            │
│ 类型: 🎬 video     │ 📁 打开文件夹       │
│ 标签: Girls, 4K    │                     │
│ 分级: Everyone     │                     │
│ 文件: xxx.mp4      │                     │
│ Workshop: 37051... │                     │
│ 主题色: ■ #838BB4  │                     │
└─────────────────────────────────────────┘
```

### 6.3 主题色板

| 元素 | 色值 | 用途 |
|------|------|------|
| 主背景 | `#0f0f1a` | 窗口背景 |
| 面板 | `#1a1a2e` | 卡片、过滤栏 |
| 输入框 | `#16213e` | 搜索框、下拉框 |
| 边框 | `#2a2a4a` | 默认边框 |
| 悬停 | `#4a4a8a` | 交互高亮 |
| 按钮 | `#2a2a5a` | 默认按钮 |
| 强调 | `#4a4a8a` | 扫描按钮 |
| 文字 | `#e0e0e0` | 主文字 |
| 次文字 | `#888` | 统计、状态栏 |

---

## 7. 开发阶段

### Phase 1 — 核心功能 ✅ 完成

| 功能 | 状态 | 备注 |
|------|------|------|
| 目录扫描 + project.json 解析 | ✅ 完成 | 支持多目录 |
| SQLite 索引 | ✅ 完成 | WAL 模式 + Schema 迁移框架 |
| 网格预览 | ✅ 完成 | 缩略图缓存 + 自动清理 |
| 搜索过滤 | ✅ 完成 | 300ms 防抖 |
| 收藏管理 | ✅ 完成 | 预览窗口联动 |
| 大图预览 | ✅ 完成 | 支持视频壁纸 |
| 多目录管理 | ✅ 完成 | DirManagerDialog |
| 批量操作 | ✅ 完成 | Ctrl/Shift 多选 + 右键菜单 |
| 导入/导出 | ✅ 完成 | JSON 格式 |
| 主题系统 | ✅ 完成 | COLORS 常量 + generate_stylesheet() |
| 单元测试 | ✅ 完成 | 88 个测试用例 |
| PyInstaller 打包 | ✅ 完成 | |

### Phase 2 — 壁纸设置 ✅ 完成

| 功能 | 说明 | 状态 |
|------|------|------|
| WE 协议调研 | 确认无公开 API，PoC 已完成 | ✅ 完成 |
| 一键设置壁纸 | `wallpaper_setter.py` — Windows API `SystemParametersInfoW` | ✅ 完成 |
| WE 壁纸设置 | 命令行 + 配置文件方式，自动检测 WE 安装路径 | ✅ 完成 |
| 定时轮换 | `rotation_worker.py` — 随机/顺序/收藏模式 | ✅ 完成 |
| 右键菜单集成 | "设为桌面壁纸" + "设为 WE 壁纸" | ✅ 完成 |
| 轮换控制 UI | FilterBar 轮换按钮 + 间隔/模式设置 | ✅ 完成 |

> ⚠️ **WE WebSocket 方案已废弃**：经调研确认 Wallpaper Engine 没有公开的 WebSocket
> 控制 API（端口 7884 为社区猜测）。Phase 2 改用 Windows API + 配置文件路线。
> 详见 `core/we_controller.py` 中的调研记录。

### Phase 3 — 高级功能

| 功能 | 说明 |
|------|------|
| 多主题支持 | 亮色主题、自定义主题（theme.py 已预留接口） |
| 缩略图尺寸选择 | 小/中/大卡片（config 中已有 thumb_size） |
| 标签管理 | 标签重命名、合并、删除 |
| 云端同步 | 收藏列表云同步（可选） |

---

## 8. 项目结构

```
wallpaper-manager/
├── app.py                  # 应用入口
├── config.py               # 配置管理
├── build.spec              # PyInstaller 打包配置
├── build.bat               # Windows 一键打包
├── pyproject.toml          # 项目元数据
├── requirements.txt        # 依赖清单
├── core/                   # 业务逻辑层
│   ├── models.py           # 数据模型
│   ├── db.py               # 数据库操作 + Schema 迁移
│   ├── scanner.py          # 目录扫描
│   ├── thumbnail_worker.py # 缩略图生成 + 清理
│   ├── export_worker.py    # 导入/导出
│   └── we_controller.py    # WE WebSocket PoC (调研)
├── ui/                     # 界面层
│   ├── theme.py            # 主题颜色常量 + QSS 生成
│   ├── main_window.py      # 主窗口
│   ├── wallpaper_card.py   # 卡片组件
│   ├── filter_bar.py       # 过滤栏
│   ├── preview_dialog.py   # 预览弹窗
│   ├── context_menu.py     # 右键菜单
│   └── dir_manager_dialog.py # 目录管理
├── tests/                  # 单元测试 (88 tests)
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_db.py
│   ├── test_scanner.py
│   └── test_we_controller.py
├── docs/
│   ├── PRD.md              # 需求文档（本文件）
│   └── DEV.md              # 开发文档
└── README.md               # 项目说明
```

---

## 9. 约束与限制

1. **仅管理本地文件** — 不提供在线下载、上传功能
2. **只读壁纸文件** — 不修改、不删除原始壁纸文件
3. **Windows 平台** — 壁纸设置功能依赖 Windows API
4. **Wallpaper Engine 兼容** — 解析 WE 的 `project.json` 格式
5. **离线运行** — 不需要网络连接

---

## 10. 验收标准

### v0.1.1 验收清单

- [x] 程序能自动检测或手动选择 Wallpaper Engine 目录
- [x] 扫描 200 个壁纸文件夹，5 秒内完成
- [x] 网格正确显示所有壁纸缩略图
- [x] 搜索框输入关键词，300ms 内过滤结果
- [x] 类型/标签下拉过滤正常工作
- [x] 收藏操作持久化，重启后保留
- [x] 大图预览窗口正常显示
- [x] 窗口缩放时网格列数自适应
- [x] 多目录管理正常工作
- [x] 导入/导出 JSON 正常工作
- [x] 批量收藏/取消收藏正常工作
- [x] 缩略图缓存自动生成和清理
- [x] 预览窗口收藏按钮与网格卡片状态同步
- [x] 关闭时所有后台线程正确清理
- [x] 88 个单元测试全部通过
- [x] PyInstaller 打包后双击可运行

---

## 11. 变更日志

### v0.1.1 (2026-04-26) — 工程加固

**新增：**
- `ui/theme.py` — 主题系统，29 个颜色常量 + `generate_stylesheet()` 函数
- `core/we_controller.py` — Wallpaper Engine WebSocket 协议调研 + PoC
- `core/thumbnail_worker.py::cleanup_thumbs()` — 缩略图缓存清理
- `tests/` — 88 个单元测试（models/db/scanner/we_controller）
- `docs/PRD.md` 变更日志章节

**改进：**
- 所有 UI 文件迁移至统一主题系统，消除硬编码颜色值
- `db.py` 新增 schema migration 框架（`SCHEMA_VERSION` + `_MIGRATIONS`）
- `ExportWorker` / `ImportWorker` 新增 `cancel()` 方法
- `MainWindow.closeEvent` 统一清理全部 4 个后台线程
- `PreviewDialog` 收藏按钮切换后通过信号通知主窗口同步更新卡片

**修复：**
- `PreviewDialog` 收藏按钮未连接点击事件
- 关闭窗口时 `_export_worker` 和 `_import_worker` 未清理的线程泄漏

**废弃：**
- WE WebSocket 控制方案（确认无公开 API），Phase 2 改用 Windows API + 配置文件路线

### v0.1.0 (2026-04-25) — 初始版本

- 目录扫描 + project.json 解析
- SQLite 索引 + 网格预览
- 搜索过滤（300ms 防抖）
- 收藏管理 + 大图预览
- 多目录管理 + 导入导出
- 多选 + 右键批量操作
- 视频壁纸预览
- PyInstaller 打包

### v0.2.0 (2026-04-26) — Phase 2 壁纸设置

**新增：**
- `core/wallpaper_setter.py` — 壁纸设置模块（514 行）
  - `set_wallpaper()` — 通过 Windows API `SystemParametersInfoW` 设置桌面壁纸
  - `get_current_wallpaper()` — 获取当前壁纸路径
  - `set_wallpaper_we()` — 通过命令行或配置文件设置 WE 动态壁纸
  - `find_we_install()` — 自动检测 WE 安装路径（Steam 库 + 注册表）
  - `get_we_wallpaper_list()` — 列出所有 WE 壁纸
- `core/rotation_worker.py` — 壁纸定时轮换（200 行）
  - 三种模式：随机 / 顺序 / 收藏
  - 可选间隔：5/15/30/60/120 分钟
  - 信号：`wallpaper_changed` / `rotation_started` / `rotation_stopped`
- `tests/test_wallpaper_setter.py` — 13 个单元测试
- `tests/test_rotation_worker.py` — 12 个单元测试

**UI 集成：**
- 右键菜单新增"🖼️ 设为桌面壁纸"和"🎬 设为 WE 壁纸"
- FilterBar 新增"🔄 自动轮换"按钮 + 右键设置（间隔/模式）
- 主窗口集成轮换生命周期管理

**依赖：**
- `requirements.txt` 新增 `websockets>=12.0`
