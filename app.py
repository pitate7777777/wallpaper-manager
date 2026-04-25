"""壁纸管理器 - 入口"""
import sys
import logging

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from ui.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

STYLESHEET = """
QMainWindow {
    background-color: #0f0f1a;
}

/* ── 过滤栏 ─────────────────────────── */
#filterBar {
    background-color: #1a1a2e;
    border-bottom: 1px solid #2a2a4a;
}

QLineEdit {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #4a4a8a;
}

QComboBox {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 5px 10px;
    min-width: 80px;
}
QComboBox:hover {
    border-color: #4a4a8a;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #16213e;
    color: #e0e0e0;
    selection-background-color: #2a2a6a;
}

QCheckBox {
    color: #c0c0c0;
    spacing: 4px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}

/* ── 按钮 ────────────────────────────── */
QPushButton {
    background-color: #2a2a5a;
    color: #e0e0e0;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #3a3a7a;
}
QPushButton:pressed {
    background-color: #1a1a4a;
}

#scanBtn {
    background-color: #4a4a8a;
    font-weight: bold;
}
#scanBtn:hover {
    background-color: #5a5aaa;
}

#favBtn {
    background: transparent;
    font-size: 14px;
    padding: 2px;
}
#favBtn:hover {
    background: rgba(255,255,255,0.1);
}

/* ── 壁纸卡片 ────────────────────────── */
#wallpaperCard {
    background-color: #1a1a2e;
    border: 2px solid #2a2a4a;
    border-bottom: 3px solid #2a2a4a;
    border-radius: 8px;
}
#wallpaperCard:hover {
    border-color: #4a4a8a;
    background-color: #1e1e35;
}

#previewLabel {
    background-color: #0a0a15;
    border-radius: 6px;
}

#titleLabel {
    color: #c0c0c0;
    font-size: 9px;
}

/* ── 信息栏 ──────────────────────────── */
#infoBar {
    background-color: #12122a;
    border-bottom: 1px solid #2a2a4a;
}

#clearSelBtn {
    background-color: #2a2a4a;
    color: #aaa;
    border: 1px solid #3a3a5a;
}
#clearSelBtn:hover {
    background-color: #3a3a6a;
    color: #e0e0e0;
}

/* ── 滚动区域 ────────────────────────── */
QScrollArea {
    border: none;
    background-color: #0f0f1a;
}

QScrollBar:vertical {
    background: #0f0f1a;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3a3a5a;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #4a4a8a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── 状态栏 ──────────────────────────── */
QStatusBar {
    background-color: #12122a;
    color: #888;
    border-top: 1px solid #2a2a4a;
}

QProgressBar {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    text-align: center;
    color: #e0e0e0;
    font-size: 10px;
}
QProgressBar::chunk {
    background-color: #4a4a8a;
    border-radius: 3px;
}

/* ── 对话框 ──────────────────────────── */
QMessageBox {
    background-color: #1a1a2e;
}

QDialog {
    background-color: #0f0f1a;
}

/* ── 视频控制栏 ──────────────────────── */
QSlider::groove:horizontal {
    background: #2a2a4a;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #4a4a8a;
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::handle:horizontal:hover {
    background: #5a5aaa;
}
QSlider::sub-page:horizontal {
    background: #4a4a8a;
    border-radius: 2px;
}
"""


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Wallpaper Manager")
    app.setStyleSheet(STYLESHEET)

    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
