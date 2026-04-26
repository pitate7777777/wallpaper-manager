"""主题系统 - 集中管理所有颜色常量和样式表生成

支持多主题切换。每个主题是一个完整的 COLORS 字典。
"""

# ── 暗色主题（默认）──────────────────────────────────────────

DARK_THEME = {
    # ── 基础背景 ──────────────────────────────────────────────
    "bg_main": "#0f0f1a",            # 主窗口、滚动区域、对话框、滚动条背景
    "bg_panel": "#1a1a2e",           # 面板背景（过滤栏、卡片、进度条、消息框）
    "bg_input": "#16213e",           # 输入框、下拉框、列表控件背景
    "bg_preview": "#0a0a15",         # 预览图区域背景
    "bg_info": "#12122a",            # 信息栏、状态栏背景
    "bg_selected": "#1a2040",        # 选中卡片背景
    "bg_card_hover": "#1e1e35",      # 卡片悬停背景
    "bg_selected_hover": "#1e2550",  # 选中卡片悬停背景
    "bg_dropdown": "#1e1e35",        # 下拉项悬停背景

    # ── 边框 ──────────────────────────────────────────────────
    "border": "#2a2a4a",             # 默认边框色
    "border_focus": "#4a4a8a",       # 聚焦/悬停边框色
    "border_selected": "#4a9eff",    # 选中状态边框色
    "border_selected_hover": "#5ab0ff",  # 选中悬停边框色
    "border_button": "#3a3a5a",      # 按钮边框

    # ── 文本 ──────────────────────────────────────────────────
    "text_primary": "#e0e0e0",       # 主要文本
    "text_secondary": "#c0c0c0",     # 次要文本（复选框、标题标签）
    "text_muted": "#888",            # 弱化文本（状态栏、时间标签）
    "text_dim": "#aaa",              # 暗淡文本（清除按钮）
    "text_placeholder": "#666",      # 占位文本

    # ── 选择 ──────────────────────────────────────────────────
    "selection_bg": "#2a2a6a",       # 选择/选中项背景
    "selection_text": "#4a9eff",     # 选择状态文本

    # ── 按钮 ──────────────────────────────────────────────────
    "btn_bg": "#2a2a5a",             # 按钮默认背景
    "btn_hover": "#3a3a7a",          # 按钮悬停背景
    "btn_pressed": "#1a1a4a",        # 按钮按下背景
    "btn_scan_bg": "#4a4a8a",        # 扫描按钮背景
    "btn_scan_hover": "#5a5aaa",     # 扫描按钮悬停
    "btn_clear_bg": "#2a2a4a",       # 清除选择按钮背景
    "btn_clear_hover": "#3a3a6a",    # 清除选择按钮悬停

    # ── 分隔线 ────────────────────────────────────────────────
    "separator": "#2a2a4a",          # 分隔线
}


def generate_stylesheet(theme_name: str | None = None, colors: dict[str, str] | None = None) -> str:
    """生成完整的 QSS 样式表。

    Args:
        theme_name: 主题名称（"dark"/"light"），优先级高于 colors。
        colors: 直接传入颜色字典（向后兼容）。若同时指定 theme_name，以 theme_name 为准。
    """
    if theme_name is not None:
        c = THEMES.get(theme_name, COLORS)
    elif colors is not None:
        c = colors
    else:
        c = COLORS
    return f"""
QMainWindow {{
    background-color: {c['bg_main']};
}}

/* ── 过滤栏 ─────────────────────────── */
#filterBar {{
    background-color: {c['bg_panel']};
    border-bottom: 1px solid {c['border']};
}}
#filterBarScroll {{
    background: transparent;
    border: none;
}}
#filterBarContainer {{
    background: transparent;
}}

QLineEdit {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}}
QLineEdit:focus {{
    border-color: {c['border_focus']};
}}

QComboBox {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 5px 10px;
    min-width: 80px;
}}
QComboBox:hover {{
    border-color: {c['border_focus']};
}}
QComboBox::drop-down {{
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    selection-background-color: {c['selection_bg']};
}}

QCheckBox {{
    color: {c['text_secondary']};
    spacing: 4px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
}}

/* ── 按钮 ────────────────────────────── */
QPushButton {{
    background-color: {c['btn_bg']};
    color: {c['text_primary']};
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {c['btn_hover']};
}}
QPushButton:pressed {{
    background-color: {c['btn_pressed']};
}}

#scanBtn {{
    background-color: {c['btn_scan_bg']};
    font-weight: bold;
}}
#scanBtn:hover {{
    background-color: {c['btn_scan_hover']};
}}

#favBtn {{
    background: transparent;
    font-size: 14px;
    padding: 2px;
}}
#favBtn:hover {{
    background: rgba(255,255,255,0.1);
}}

/* ── 壁纸卡片 ────────────────────────── */
#wallpaperCard {{
    background-color: {c['bg_panel']};
    border: 2px solid {c['border']};
    border-bottom: 3px solid {c['border']};
    border-radius: 8px;
}}
#wallpaperCard:hover {{
    border-color: {c['border_focus']};
    background-color: {c['bg_card_hover']};
}}

#previewLabel {{
    background-color: {c['bg_preview']};
    border-radius: 6px;
}}

#titleLabel {{
    color: {c['text_secondary']};
    font-size: 11px;
}}

/* ── 信息栏 ──────────────────────────── */
#infoBar {{
    background-color: {c['bg_info']};
    border-bottom: 1px solid {c['border']};
}}

#clearSelBtn {{
    background-color: {c['btn_clear_bg']};
    color: {c['text_dim']};
    border: 1px solid {c['border_button']};
}}
#clearSelBtn:hover {{
    background-color: {c['btn_clear_hover']};
    color: {c['text_primary']};
}}

/* ── 滚动区域 ────────────────────────── */
QScrollArea {{
    border: none;
    background-color: {c['bg_main']};
}}

QScrollBar:vertical {{
    background: {c['bg_main']};
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {c['border_button']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c['border_focus']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── 状态栏 ──────────────────────────── */
QStatusBar {{
    background-color: {c['bg_info']};
    color: {c['text_muted']};
    border-top: 1px solid {c['border']};
}}

QProgressBar {{
    background-color: {c['bg_panel']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    text-align: center;
    color: {c['text_primary']};
    font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: {c['border_focus']};
    border-radius: 3px;
}}

/* ── 对话框 ──────────────────────────── */
QDialog {{
    background-color: {c['bg_main']};
    color: {c['text_primary']};
}}
QDialog QLabel {{
    color: {c['text_primary']};
}}

QMessageBox {{
    background-color: {c['bg_panel']};
    color: {c['text_primary']};
}}
QMessageBox QLabel {{
    color: {c['text_primary']};
}}

QInputDialog {{
    background-color: {c['bg_panel']};
    color: {c['text_primary']};
}}
QInputDialog QLabel {{
    color: {c['text_primary']};
}}
QInputDialog QLineEdit {{
    background-color: {c['bg_input']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 4px 8px;
}}

/* ── 视频控制栏 ──────────────────────── */
QSlider::groove:horizontal {{
    background: {c['border']};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {c['border_focus']};
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{
    background: {c['btn_scan_hover']};
}}
QSlider::sub-page:horizontal {{
    background: {c['border_focus']};
    border-radius: 2px;
}}

/* ── 提示框 ──────────────────────────── */
QToolTip {{
    background-color: {c['bg_panel']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 4px 8px;
}}

/* ── 分组框 ──────────────────────────── */
QGroupBox {{
    color: {c['text_primary']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 16px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}
"""


# ── 亮色主题 ──────────────────────────────────────────────────

LIGHT_THEME = {
    # ── 基础背景 ──────────────────────────────────────────────
    "bg_main": "#f5f5f7",
    "bg_panel": "#ffffff",
    "bg_input": "#e8e8ed",
    "bg_preview": "#e0e0e5",
    "bg_info": "#ececf0",
    "bg_selected": "#d0d8f0",
    "bg_card_hover": "#eaeaf0",
    "bg_selected_hover": "#c0c8e8",
    "bg_dropdown": "#ffffff",

    # ── 边框 ──────────────────────────────────────────────────
    "border": "#c8c8d0",
    "border_focus": "#8888b0",
    "border_selected": "#4a7aff",
    "border_selected_hover": "#3a6aef",
    "border_button": "#b0b0b8",

    # ── 文本 ──────────────────────────────────────────────────
    "text_primary": "#1a1a2e",
    "text_secondary": "#3a3a50",
    "text_muted": "#5a5a6a",
    "text_dim": "#4a4a5a",
    "text_placeholder": "#5c5c6c",

    # ── 选择 ──────────────────────────────────────────────────
    "selection_bg": "#c0c8e0",
    "selection_text": "#2a5adf",

    # ── 按钮 ──────────────────────────────────────────────────
    "btn_bg": "#e0e0e8",
    "btn_hover": "#d0d0e0",
    "btn_pressed": "#c0c0d0",
    "btn_scan_bg": "#4a7aff",
    "btn_scan_hover": "#3a6aef",
    "btn_clear_bg": "#d8d8e0",
    "btn_clear_hover": "#c8c8d8",

    # ── 分隔线 ────────────────────────────────────────────────
    "separator": "#c8c8d0",
}


# ── 主题注册表 ────────────────────────────────────────────────

THEMES: dict[str, dict[str, str]] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}

# 主题键一致性校验（模块加载时执行一次）
_expected_keys = set(DARK_THEME.keys())
for _tname, _tcolors in THEMES.items():
    _actual = set(_tcolors.keys())
    if _actual != _expected_keys:
        _missing = _expected_keys - _actual
        _extra = _actual - _expected_keys
        raise ValueError(
            f"主题 '{_tname}' 键与 DARK_THEME 不一致"
            + (f"，缺失: {_missing}" if _missing else "")
            + (f"，多余: {_extra}" if _extra else "")
        )

# 当前活跃主题（模块级可变状态）
_current_theme_name = "dark"
COLORS = dict(DARK_THEME)


def get_theme_names() -> list[str]:
    """返回所有可用主题名称"""
    return list(THEMES.keys())


def get_current_theme_name() -> str:
    """返回当前主题名称"""
    return _current_theme_name


def set_theme(name: str) -> None:
    """切换当前主题。

    Args:
        name: 主题名称（必须在 THEMES 中注册）

    Raises:
        KeyError: 主题名称不存在
    """
    global _current_theme_name
    if name not in THEMES:
        raise KeyError(f"未知主题: {name}，可用: {list(THEMES.keys())}")
    # 原地更新 COLORS，保持引用不变（模块级 import 不会失效）
    COLORS.clear()
    COLORS.update(THEMES[name])
    _current_theme_name = name


def register_theme(name: str, colors: dict[str, str]) -> None:
    """注册自定义主题。

    Args:
        name: 主题名称
        colors: 完整的颜色字典（需包含 DARK_THEME 的所有 key）
    """
    THEMES[name] = dict(colors)
