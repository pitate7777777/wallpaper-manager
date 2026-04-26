"""GitHub Release 版本检查

启动时后台检查是否有新版本，通过信号通知 UI 层。
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Optional

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

GITHUB_REPO = "pitate7777777/wallpaper-manager"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(v: str) -> tuple[int, ...]:
    """将版本字符串 'v0.4.1' 或 '0.4.1' 解析为可比较的元组。"""
    v = v.strip().lstrip("v")
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts) if parts else (0,)


def fetch_latest_release() -> Optional[dict]:
    """同步请求 GitHub API 获取最新 Release 信息。

    Returns:
        {"tag_name": "v0.5.0", "body": "...", "html_url": "..."} 或 None
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "wallpaper-manager",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "tag_name": data.get("tag_name", ""),
                "body": data.get("body", ""),
                "html_url": data.get("html_url", ""),
                "name": data.get("name", ""),
            }
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        logger.debug(f"版本检查请求失败（可忽略）: {e}")
        return None


class VersionCheckWorker(QThread):
    """后台检查 GitHub Release 新版本"""
    result = Signal(dict)  # {"has_update": bool, "current": str, "latest": str, "url": str}

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        release = fetch_latest_release()
        if not release:
            return

        latest_tag = release["tag_name"]
        current_ver = _parse_version(self.current_version)
        latest_ver = _parse_version(latest_tag)

        if latest_ver > current_ver:
            self.result.emit({
                "has_update": True,
                "current": self.current_version,
                "latest": latest_tag,
                "url": release["html_url"],
                "body": release.get("body", ""),
            })
        else:
            self.result.emit({
                "has_update": False,
                "current": self.current_version,
                "latest": latest_tag,
            })
