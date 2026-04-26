"""壁纸管理器 - 入口"""
import sys
import logging

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from ui.main_window import MainWindow
from ui.theme import generate_stylesheet, set_theme
from config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 从配置读取主题
    cfg = load_config()
    theme_name = cfg.get("theme", "dark")
    try:
        set_theme(theme_name)
    except KeyError:
        theme_name = "dark"
        set_theme(theme_name)

    app = QApplication(sys.argv)
    app.setApplicationName("Wallpaper Manager")
    app.setStyleSheet(generate_stylesheet(theme_name))

    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
