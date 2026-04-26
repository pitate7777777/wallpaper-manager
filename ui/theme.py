"""主题系统 - 集中管理所有颜色常量和样式表生成"""


# ── 颜色常量 ────────────────────────────────────────────────────

COLORS = {
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


def generate_stylesheet(colors: dict[str, str] | None = None) -> str:
    """生成完整的 QSS 样式表。

    Args:
        colors: 颜色字典，默认使用 COLORS 常量。
    """
    c = colors or COLORS
    return f"""
QMainWindow {{
    background-color: {c['bg_main']};
}}

/* ── 过滤栏 ─────────────────────────── */
#filterBar {{
    background-color: {c['bg_panel']};
    border-bottom: 1px solid {c['border']};
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
QMessageBox {{
    background-color: {c['bg_panel']};
}}

QDialog {{
    background-color: {c['bg_main']};
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
"""
