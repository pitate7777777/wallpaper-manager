"""壁纸卡片组件 - 支持多选 + 缩略图缓存"""
from pathlib import Path

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QFont

from core.models import Wallpaper
from core.thumbnail_worker import get_thumb_path

# 预览图尺寸
CARD_WIDTH = 220
CARD_HEIGHT = 160


class WallpaperCard(QFrame):
    """单张壁纸的卡片组件"""

    clicked = Signal(int)            # wallpaper id
    ctrl_clicked = Signal(int)       # Ctrl+点击，切换选中
    shift_clicked = Signal(int)      # Shift+点击，范围选中
    favorite_toggled = Signal(int)   # wallpaper id
    context_menu_requested = Signal(int, object)  # id, global_pos

    def __init__(self, wallpaper: Wallpaper, parent=None):
        super().__init__(parent)
        self.wallpaper = wallpaper
        self._selected = False
        self.setObjectName("wallpaperCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(CARD_WIDTH + 16, CARD_HEIGHT + 72)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(4)

        # 预览图
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
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
        # 先检查缩略图缓存
        preview_path = self.wallpaper.preview_path
        if preview_path:
            thumb_path = get_thumb_path(preview_path)
            if thumb_path.exists():
                pixmap = QPixmap(str(thumb_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        CARD_WIDTH, CARD_HEIGHT,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation,
                    )
                    self.preview_label.setPixmap(scaled)
                    return

        # 回退到原始预览图
        if preview_path and Path(preview_path).exists():
            pixmap = QPixmap(preview_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    CARD_WIDTH, CARD_HEIGHT,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                self.preview_label.setPixmap(scaled)
                return

        # 占位图
        type_emoji = {"video": "🎬", "scene": "🖼️", "web": "🌐"}.get(self.wallpaper.wp_type, "📄")
        self.preview_label.setText(f"{type_emoji}\n{self.wallpaper.wp_type or '未知类型'}")
        self.preview_label.setStyleSheet("color: #666; font-size: 12px; background: #0a0a15;")

    def set_selected(self, selected: bool):
        """设置选中状态"""
        if self._selected != selected:
            self._selected = selected
            self._update_style()

    def is_selected(self) -> bool:
        return self._selected

    def _update_style(self):
        """更新卡片样式（主题色 + 选中状态）"""
        border_color = "#4a9eff" if self._selected else "#2a2a4a"
        bottom_border = self.wallpaper.scheme_color_hex or "#2a2a4a"

        self.setStyleSheet(f"""
            #wallpaperCard {{
                background-color: {'#1a2040' if self._selected else '#1a1a2e'};
                border: 2px solid {border_color};
                border-bottom: 3px solid {bottom_border};
                border-radius: 8px;
            }}
            #wallpaperCard:hover {{
                border-color: {'#5ab0ff' if self._selected else '#4a4a8a'};
                background-color: {'#1e2550' if self._selected else '#1e1e35'};
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
