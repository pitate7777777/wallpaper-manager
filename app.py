"""壁纸管理器 - 入口"""
import logging
import re
import sys
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
from config import load_config, save_config


def _setup_logging():
    """配置日志：控制台 + 文件（~/.wallpaper-manager/logs/）"""
    log_dir = Path.home() / ".wallpaper-manager" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(
            log_dir / "wallpaper-manager.log",
            encoding="utf-8",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
        ),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def main():
    _setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"Wallpaper Manager v{__version__} 启动")

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

    # 启动后台版本检查
    from core.version_check import VersionCheckWorker
    version_checker = VersionCheckWorker(__version__, parent=window)
    version_checker.result.connect(
        lambda info: _handle_version_result(info, window),
    )
    # 防止 GC 回收
    window._version_checker = version_checker
    version_checker.start()

    sys.exit(app.exec())


def _handle_version_result(info: dict, window):
    """处理版本检查结果"""
    if info.get("has_update"):
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        latest = info["latest"]
        url = info["url"]
        current = info["current"]

        reply = QMessageBox.information(
            window,
            "发现新版本",
            f"当前版本: v{current}\n最新版本: {latest}\n\n"
            f"是否前往下载？",
            QMessageBox.Open | QMessageBox.Ignore,
            QMessageBox.Open,
        )
        if reply == QMessageBox.Open:
            QDesktopServices.openUrl(QUrl(url))
