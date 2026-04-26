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


def cleanup_thumbs(valid_preview_paths: set[str]) -> int:
    """清理缩略图缓存，删除不在 valid_preview_paths 中的文件。

    Args:
        valid_preview_paths: 当前数据库中所有有效壁纸的 preview_path 集合。

    Returns:
        删除的文件数量。
    """
    if not THUMB_DIR.exists():
        return 0

    valid_thumb_paths = {get_thumb_path(p) for p in valid_preview_paths if p}
    removed = 0

    for f in THUMB_DIR.glob("*.jpg"):
        if f not in valid_thumb_paths:
            try:
                f.unlink()
                removed += 1
            except OSError as e:
                logger.warning(f"清理缩略图失败: {f} - {e}")

    if removed:
        logger.info(f"清理缩略图缓存: 删除 {removed} 个过期文件")
    return removed


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
