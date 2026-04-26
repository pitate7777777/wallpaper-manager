"""壁纸管理器 - 入口"""
import re
import sys
import logging
from pathlib import Path
from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    __version__ = _pkg_version("wallpaper-manager")
except PackageNotFoundError:
    # 开发模式下未安装包，从 pyproject.toml 读取
    # 兼容 Python 3.10（无 tomllib）和 3.11+（有 tomllib）
    _pyproject = Path(__file__).parent / "pyproject.toml"
    __version__ = "0.0.0"
    if _pyproject.exists():
        try:
            import tomllib
            with open(_pyproject, "rb") as _f:
                __version__ = tomllib.load(_f).get("project", {}).get("version", "0.0.0")
        except ImportError:
            # Python 3.10: 用正则从 pyproject.toml 提取 version
            _match = re.search(
                r'^version\s*=\s*"([^"]+)"',
                _pyproject.read_text(encoding="utf-8"),
                re.MULTILINE,
            )
            if _match:
                __version__ = _match.group(1)

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
