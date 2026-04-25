"""缩略图缓存 - 后台生成"""
import hashlib
import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PIL import Image

logger = logging.getLogger(__name__)

THUMB_DIR = Path.home() / ".wallpaper-manager" / "thumbs"
THUMB_SIZE = (320, 180)  # 16:9 统一尺寸


def get_thumb_path(preview_path: str) -> Path:
    """根据原图路径生成缓存路径"""
    h = hashlib.md5(preview_path.encode()).hexdigest()
    return THUMB_DIR / f"{h}.jpg"


class ThumbnailWorker(QThread):
    """后台缩略图生成线程"""
    progress = Signal(int, int, str)   # current, total, title
    finished = Signal(int)             # generated count

    def __init__(self, wallpapers, force=False):
        super().__init__()
        self.wallpapers = wallpapers
        self.force = force
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        THUMB_DIR.mkdir(parents=True, exist_ok=True)
        generated = 0
        total = len(self.wallpapers)

        for i, wp in enumerate(self.wallpapers):
            if self._cancelled:
                break

            self.progress.emit(i + 1, total, wp.title)

            preview_path = wp.preview_path
            if not preview_path or not Path(preview_path).exists():
                continue

            thumb_path = get_thumb_path(preview_path)
            if not self.force and thumb_path.exists():
                continue

            try:
                img = Image.open(preview_path)
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                # 转为 RGB 保存为 JPEG（处理 PNG 的 alpha 通道）
                if img.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", img.size, (15, 15, 26))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    bg.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(str(thumb_path), "JPEG", quality=85)
                generated += 1
            except Exception as e:
                logger.warning(f"缩略图生成失败: {preview_path} - {e}")

        self.finished.emit(generated)
