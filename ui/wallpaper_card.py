"""壁纸卡片组件 - 支持多选 + 缩略图缓存 + 可调尺寸"""
from pathlib import Path

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QFont

from core.models import Wallpaper
from core.thumbnail_worker import get_thumb_path
from ui.theme import COLORS

# 卡片尺寸预设 (preview_w, preview_h)
CARD_SIZES = {
    "small":  (160, 120),
    "medium": (220, 160),
    "large":  (320, 240),
}

# 默认尺寸（保持向后兼容）
CARD_WIDTH = 220
CARD_HEIGHT = 160


def get_card_dimensions(size: str = "medium") -> tuple[int, int]:
    """获取卡片预览尺寸

    Args:
        size: "small" / "medium" / "large"

    Returns:
        (preview_width, preview_height)
    """
    return CARD_SIZES.get(size, CARD_SIZES["medium"])


class WallpaperCard(QFrame):
    """单张壁纸的卡片组件"""

    clicked = Signal(int)            # wallpaper id
    ctrl_clicked = Signal(int)       # Ctrl+点击，切换选中
    shift_clicked = Signal(int)      # Shift+点击，范围选中
    favorite_toggled = Signal(int)   # wallpaper id
    context_menu_requested = Signal(int, object)  # id, global_pos

    def __init__(self, wallpaper: Wallpaper, size: str = "medium", parent=None):
        super().__init__(parent)
        self.wallpaper = wallpaper
        self._selected = False
        self._preview_w, self._preview_h = get_card_dimensions(size)
        self.setObjectName("wallpaperCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(self._preview_w + 16, self._preview_h + 72)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(4)

        # 预览图
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(self._preview_w, self._preview_h)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setObjectName("previewLabel")
        self._load_preview()
        layout.addWidget(self.preview_label)

        # 底部信息栏
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(4)

        # 类型图标 + 标题
        title_text = f"{self.wallpaper.type_emoji} {self.wallpaper.title}"
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setWordWrap(False)
        font = self.title_label.font()
        font.setPointSize(9)
        self.title_label.setFont(font)
        bottom.addWidget(self.title_label, 1)

        # 收藏按钮
        self.fav_btn = QPushButton("🤍" if not self.wallpaper.is_favorite else "❤️")
        self.fav_btn.setObjectName("favBtn")
        self.fav_btn.setFixedSize(24, 24)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.setFlat(True)
        self.fav_btn.clicked.connect(self._on_fav_clicked)
        bottom.addWidget(self.fav_btn)

        layout.addLayout(bottom)

        self._update_style()

    def _load_preview(self):
        """加载预览图（优先使用缩略图缓存）"""
        w, h = self._preview_w, self._preview_h
        # 先检查缩略图缓存
        preview_path = self.wallpaper.preview_path
        if preview_path:
            thumb_path = get_thumb_path(preview_path)
            if thumb_path.exists():
                pixmap = QPixmap(str(thumb_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        w, h,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation,
                    )
                    self.preview_label.setPixmap(scaled)
                    return

        # 回退到原始预览图
        if preview_path and Path(preview_path).exists():
            pixmap = QPixmap(preview_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    w, h,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                self.preview_label.setPixmap(scaled)
                return

        # 占位图
        type_emoji = {"video": "🎬", "scene": "🖼️", "web": "🌐"}.get(self.wallpaper.wp_type, "📄")
        self.preview_label.setText(f"{type_emoji}\n{self.wallpaper.wp_type or '未知类型'}")
        self.preview_label.setStyleSheet(
            f"color: {COLORS['text_placeholder']}; font-size: 12px; background: {COLORS['bg_preview']};"
        )

    def set_selected(self, selected: bool):
        """设置选中状态"""
        if self._selected != selected:
            self._selected = selected
            self._update_style()

    def is_selected(self) -> bool:
        return self._selected

    def _update_style(self):
        """更新卡片样式（主题色 + 选中状态）"""
        border_color = COLORS["border_selected"] if self._selected else COLORS["border"]
        bottom_border = self.wallpaper.scheme_color_hex or COLORS["border"]
        bg_color = COLORS["bg_selected"] if self._selected else COLORS["bg_panel"]
        hover_border = COLORS["border_selected_hover"] if self._selected else COLORS["border_focus"]
        hover_bg = COLORS["bg_selected_hover"] if self._selected else COLORS["bg_card_hover"]

        self.setStyleSheet(f"""
            #wallpaperCard {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-bottom: 3px solid {bottom_border};
                border-radius: 8px;
            }}
            #wallpaperCard:hover {{
                border-color: {hover_border};
                background-color: {hover_bg};
            }}
        """)

    def _on_fav_clicked(self):
        self.favorite_toggled.emit(self.wallpaper.id)

    def _on_context_menu(self, pos):
        self.context_menu_requested.emit(self.wallpaper.id, self.mapToGlobal(pos))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.fav_btn.geometry().contains(event.pos()):
                # 点击收藏按钮，让按钮自己处理，不触发卡片点击
                super().mousePressEvent(event)
                return

            modifiers = event.modifiers()
            if modifiers & Qt.ControlModifier:
                self.ctrl_clicked.emit(self.wallpaper.id)
            elif modifiers & Qt.ShiftModifier:
                self.shift_clicked.emit(self.wallpaper.id)
            else:
                self.clicked.emit(self.wallpaper.id)
        super().mousePressEvent(event)
