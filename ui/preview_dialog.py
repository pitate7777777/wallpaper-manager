"""壁纸大图预览对话框 - 支持视频预览"""
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QSizePolicy, QSlider, QStackedWidget,
)
from PySide6.QtCore import Qt, QSize, QUrl, QTimer, Signal
from PySide6.QtGui import QPixmap, QShortcut, QKeySequence

# 视频播放组件（可选导入）
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

from core.models import Wallpaper
from ui.theme import COLORS


class PreviewDialog(QDialog):
    """壁纸详情/大图/视频预览"""

    favorite_toggled = Signal(int)  # wallpaper id

    def __init__(self, wallpaper: Wallpaper, parent=None):
        super().__init__(parent)
        self.wallpaper = wallpaper
        self._player = None
        self._audio_output = None
        self.setWindowTitle(f"📋 {wallpaper.title}")
        self.setMinimumSize(600, 400)
        self.resize(900, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self._setup_ui()
        self._load_content()

        # ESC 关闭
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.close)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 内容区域 - 使用堆叠控件切换图片/视频
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {COLORS['bg_panel']}; border-radius: 8px;")

        # 图片预览页
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll_area.setWidget(self.image_label)
        self.stack.addWidget(self.scroll_area)  # index 0

        # 视频预览页
        self._setup_video_player()

        layout.addWidget(self.stack, 1)

        # 视频控制栏
        self.video_controls = QWidget()
        self.video_controls.setVisible(False)
        ctrl_layout = QHBoxLayout(self.video_controls)
        ctrl_layout.setContentsMargins(8, 0, 8, 0)

        self.play_btn = QPushButton("⏸ 暂停")
        self.play_btn.setFixedHeight(28)
        self.play_btn.clicked.connect(self._toggle_play)
        ctrl_layout.addWidget(self.play_btn)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self._seek_video)
        ctrl_layout.addWidget(self.position_slider, 1)

        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        self.time_label.setFixedWidth(90)
        ctrl_layout.addWidget(self.time_label)

        layout.addWidget(self.video_controls)

        # 信息区域
        info_layout = QHBoxLayout()

        # 左侧信息
        left_info = QVBoxLayout()
        left_info.setSpacing(4)

        _tc = COLORS['text_primary']
        _ts = COLORS['text_secondary']

        self.title_label = QLabel(
            f"<b style='color:{_tc}'>标题:</b> <span style='color:{_ts}'>{self.wallpaper.title}</span>"
        )
        self.title_label.setTextFormat(Qt.RichText)
        left_info.addWidget(self.title_label)

        self.type_label = QLabel(
            f"<b style='color:{_tc}'>类型:</b> <span style='color:{_ts}'>{self.wallpaper.type_emoji} {self.wallpaper.wp_type}</span>"
        )
        self.type_label.setTextFormat(Qt.RichText)
        left_info.addWidget(self.type_label)

        self.tags_label = QLabel(
            f"<b style='color:{_tc}'>标签:</b> <span style='color:{_ts}'>{self.wallpaper.tags_display or '无'}</span>"
        )
        self.tags_label.setTextFormat(Qt.RichText)
        left_info.addWidget(self.tags_label)

        self.rating_label = QLabel(
            f"<b style='color:{_tc}'>分级:</b> <span style='color:{_ts}'>{self.wallpaper.content_rating or '未知'}</span>"
        )
        self.rating_label.setTextFormat(Qt.RichText)
        left_info.addWidget(self.rating_label)

        self.file_label = QLabel(
            f"<b style='color:{_tc}'>文件:</b> <span style='color:{_ts}'>{self.wallpaper.file}</span>"
        )
        self.file_label.setTextFormat(Qt.RichText)
        self.file_label.setWordWrap(True)
        left_info.addWidget(self.file_label)

        self.workshop_label = QLabel(
            f"<b style='color:{_tc}'>Workshop ID:</b> <span style='color:{_ts}'>{self.wallpaper.workshop_id}</span>"
        )
        self.workshop_label.setTextFormat(Qt.RichText)
        left_info.addWidget(self.workshop_label)

        if self.wallpaper.scheme_color_hex:
            color_label = QLabel(
                f"<b style='color:{_tc}'>主题色:</b> "
                f"<span style='color:{self.wallpaper.scheme_color_hex}'>■</span> "
                f"<span style='color:{_ts}'>{self.wallpaper.scheme_color_hex}</span>"
            )
            color_label.setTextFormat(Qt.RichText)
            left_info.addWidget(color_label)

        info_layout.addLayout(left_info, 1)

        # 右侧按钮
        right_btns = QVBoxLayout()
        right_btns.setSpacing(8)

        self.fav_btn = QPushButton("❤️ 已收藏" if self.wallpaper.is_favorite else "🤍 收藏")
        self.fav_btn.setFixedHeight(36)
        self.fav_btn.setObjectName("favBtn")
        self.fav_btn.clicked.connect(self._on_fav_clicked)
        right_btns.addWidget(self.fav_btn)

        self.open_folder_btn = QPushButton("📁 打开文件夹")
        self.open_folder_btn.setFixedHeight(36)
        self.open_folder_btn.clicked.connect(self._open_folder)
        right_btns.addWidget(self.open_folder_btn)

        right_btns.addStretch()
        info_layout.addLayout(right_btns)

        layout.addLayout(info_layout)

    def _setup_video_player(self):
        """初始化视频播放组件"""
        if not HAS_MULTIMEDIA:
            # 无多媒体模块时显示占位
            self.video_label = QLabel("🎬 视频预览需要 PySide6-Multimedia\npip install PySide6-Multimedia")
            self.video_label.setAlignment(Qt.AlignCenter)
            self.video_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
            self.stack.addWidget(self.video_label)  # index 1
            return

        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._player.setVideoOutput(self.video_widget)

        # 信号连接
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)

        self.stack.addWidget(self.video_widget)  # index 1

    def _load_content(self):
        """加载内容（图片或视频）"""
        is_video = self.wallpaper.wp_type == "video" and self.wallpaper.file
        wallpaper_path = self.wallpaper.wallpaper_file_path

        if is_video and Path(wallpaper_path).exists():
            # 视频壁纸：先显示预览图，再加载视频
            self.stack.setCurrentIndex(1)
            self.video_controls.setVisible(True)
            if self._player:
                self._player.setSource(QUrl.fromLocalFile(wallpaper_path))
                self._player.play()
            # 预览图会由视频帧覆盖，无需额外加载
        else:
            # 图片壁纸
            self.stack.setCurrentIndex(0)
            self.video_controls.setVisible(False)
            self._load_preview_image()

    def _load_preview_image(self):
        """加载预览图"""
        preview_path = self.wallpaper.preview_path
        if preview_path and Path(preview_path).exists():
            pixmap = QPixmap(preview_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.scroll_area.size() - QSize(20, 20),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled)
                return

        self.image_label.setText("无法加载预览图")
        self.image_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 16px;")

    def _toggle_play(self):
        """播放/暂停切换"""
        if not self._player:
            return
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _seek_video(self, position):
        """跳转到指定位置"""
        if self._player:
            self._player.setPosition(position)

    def _on_position_changed(self, position):
        """视频播放位置变化"""
        self.position_slider.setValue(position)
        self.time_label.setText(f"{self._format_time(position)} / {self._format_time(self._player.duration())}")

    def _on_duration_changed(self, duration):
        """视频总时长变化"""
        self.position_slider.setRange(0, duration)
        self.time_label.setText(f"0:00 / {self._format_time(duration)}")

    def _on_state_changed(self, state):
        """播放状态变化"""
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setText("⏸ 暂停")
        else:
            self.play_btn.setText("▶ 播放")

    @staticmethod
    def _format_time(ms: int) -> str:
        """毫秒转 mm:ss 格式"""
        s = ms // 1000
        m, s = divmod(s, 60)
        return f"{m}:{s:02d}"

    def _on_fav_clicked(self):
        """切换收藏状态"""
        from core import db
        new_state = db.toggle_favorite(self.wallpaper.id)
        self.wallpaper.is_favorite = new_state
        self.fav_btn.setText("❤️ 已收藏" if new_state else "🤍 收藏")
        self.favorite_toggled.emit(self.wallpaper.id)

    def _open_folder(self):
        """在资源管理器中打开文件夹"""
        import subprocess
        path = self.wallpaper.folder_path
        if Path(path).exists():
            subprocess.Popen(["explorer", path])

    def resizeEvent(self, event):
        """窗口大小变化时重新缩放图片（带防抖）"""
        super().resizeEvent(event)
        if self.stack.currentIndex() == 0:
            if not hasattr(self, "_resize_timer"):
                self._resize_timer = QTimer()
                self._resize_timer.setSingleShot(True)
                self._resize_timer.timeout.connect(self._load_preview_image)
            self._resize_timer.start(100)

    def closeEvent(self, event):
        """关闭时停止视频播放"""
        if self._player:
            self._player.stop()
        super().closeEvent(event)
