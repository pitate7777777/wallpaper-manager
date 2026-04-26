"""导入/导出功能"""
import json
import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core import db
from core.models import Wallpaper

logger = logging.getLogger(__name__)


class ExportWorker(QThread):
    """后台导出收藏列表"""
    finished = Signal(bool, str)  # success, message

    def __init__(self, output_path: str, favorites_only: bool = True,
                 wallpaper_ids: set[int] = None):
        super().__init__()
        self.output_path = output_path
        self.favorites_only = favorites_only
        self.wallpaper_ids = wallpaper_ids  # 指定 ID 集合时仅导出这些
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            wallpapers = db.query_wallpapers(
                favorites_only=self.favorites_only,
                order_by="title",
            )

            # 如果指定了 ID，过滤到仅这些
            if self.wallpaper_ids is not None:
                wallpapers = [wp for wp in wallpapers if wp.id in self.wallpaper_ids]

            export_data = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "count": len(wallpapers),
                "wallpapers": [
                    {
                        "folder_path": wp.folder_path,
                        "workshop_id": wp.workshop_id,
                        "title": wp.title,
                        "wp_type": wp.wp_type,
                        "file": wp.file,
                        "preview": wp.preview,
                        "tags": wp.tags,
                        "content_rating": wp.content_rating,
                        "description": wp.description,
                        "scheme_color": wp.scheme_color,
                        "is_favorite": wp.is_favorite,
                    }
                    for wp in wallpapers
                ],
            }

            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.finished.emit(True, f"已导出 {len(wallpapers)} 条记录到 {self.output_path}")
        except Exception as e:
            self.finished.emit(False, f"导出失败: {e}")


class ImportWorker(QThread):
    """后台导入收藏列表"""
    progress = Signal(int, int)   # current, total
    finished = Signal(dict)       # stats

    def __init__(self, input_path: str):
        super().__init__()
        self.input_path = input_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            with open(self.input_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            wallpapers = data.get("wallpapers", [])
            total = len(wallpapers)
            stats = {"imported": 0, "skipped": 0, "errors": 0}

            for i, item in enumerate(wallpapers):
                if self._cancelled:
                    break
                self.progress.emit(i + 1, total)

                # 检查文件夹是否还存在
                folder = item.get("folder_path", "")
                if not folder or not Path(folder).is_dir():
                    stats["skipped"] += 1
                    continue

                try:
                    wp = Wallpaper(
                        folder_path=item["folder_path"],
                        workshop_id=item.get("workshop_id", ""),
                        title=item.get("title", ""),
                        wp_type=item.get("wp_type", ""),
                        file=item.get("file", ""),
                        preview=item.get("preview", ""),
                        tags=item.get("tags", []),
                        content_rating=item.get("content_rating", ""),
                        description=item.get("description", ""),
                        scheme_color=item.get("scheme_color", ""),
                        is_favorite=item.get("is_favorite", False),
                    )
                    db.upsert_wallpaper(wp)
                    stats["imported"] += 1
                except Exception as e:
                    logger.warning(f"导入失败: {item.get('title', '?')} - {e}")
                    stats["errors"] += 1

            self.finished.emit(stats)
        except Exception as e:
            self.finished.emit({"error": str(e)})
