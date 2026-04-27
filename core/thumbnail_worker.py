"""缩略图缓存 - 后台生成 + 大小限制 + LRU 淘汰"""
import hashlib
import logging
import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PIL import Image

logger = logging.getLogger(__name__)

THUMB_DIR = Path.home() / ".wallpaper-manager" / "thumbs"
# 缩略图统一尺寸（16:9）
# 注意：config.py DEFAULT_CONFIG["thumb_size"] 也维护了相同的默认值 [320, 180]，
# 如需修改请同步两处（当前版本生成逻辑不读取 config，以此常量为准）。
THUMB_SIZE = (320, 180)  # 16:9 统一尺寸

# 缓存上限（默认 500MB），超出时按最久未访问淘汰
MAX_CACHE_BYTES = 500 * 1024 * 1024

# ─── 内存中的缓存大小追踪（增量更新，避免重复扫描磁盘）─────────────
_current_cache_bytes: int | None = None  # None = 未初始化


def get_thumb_path(preview_path: str) -> Path:
    """根据原图路径生成缓存路径（MD5 hash）"""
    h = hashlib.md5(preview_path.encode()).hexdigest()
    return THUMB_DIR / f"{h}.jpg"


def _get_cache_size() -> int:
    """获取当前缓存目录总大小（字节）。仅在首次调用或需要精确值时扫描。"""
    global _current_cache_bytes
    if _current_cache_bytes is not None:
        return _current_cache_bytes

    # 首次调用：扫描整个目录
    if not THUMB_DIR.exists():
        _current_cache_bytes = 0
        return 0
    total = 0
    for f in THUMB_DIR.glob("*.jpg"):
        try:
            total += f.stat().st_size
        except OSError:
            pass
    _current_cache_bytes = total
    return total


def _touch_thumb(path: Path) -> None:
    """更新缩略图访问时间（供 LRU 排序），不改变内存计数器。"""
    try:
        os.utime(path)
    except OSError:
        pass


def _evict_lru(max_bytes: int = MAX_CACHE_BYTES) -> int:
    """LRU 淘汰：按文件最后访问时间排序，删除最久未访问的文件直到低于上限。

    使用内存中维护的缓存大小，避免重复扫描磁盘。

    Returns:
        删除的文件数量。
    """
    global _current_cache_bytes

    if not THUMB_DIR.exists():
        return 0

    current_size = _get_cache_size()
    if current_size <= max_bytes:
        return 0

    # 收集所有缩略图及其最后访问时间
    files: list[tuple[float, Path, int]] = []
    for f in THUMB_DIR.glob("*.jpg"):
        try:
            stat = f.stat()
            files.append((stat.st_atime, f, stat.st_size))
        except OSError:
            pass

    # 按访问时间升序（最久未访问的排前面）
    files.sort(key=lambda x: x[0])

    original_size = current_size
    removed = 0
    for atime, path, size in files:
        if current_size <= max_bytes:
            break
        try:
            path.unlink()
            current_size -= size
            removed += 1
        except OSError as e:
            logger.warning(f"淘汰缩略图失败: {path} - {e}")

    _current_cache_bytes = current_size

    if removed:
        freed_mb = (original_size - current_size) / 1024 / 1024
        remaining_mb = current_size / 1024 / 1024
        logger.info(
            f"缩略图缓存淘汰: 删除 {removed} 个文件, "
            f"释放 {freed_mb:.1f}MB, 剩余 {remaining_mb:.1f}MB"
        )
    return removed


def cleanup_thumbs(valid_preview_paths: set[str]) -> int:
    """清理缩略图缓存：删除无效文件 + LRU 淘汰超限文件。

    Args:
        valid_preview_paths: 当前数据库中所有有效壁纸的 preview_path 集合。

    Returns:
        删除的文件数量。
    """
    global _current_cache_bytes

    if not THUMB_DIR.exists():
        return 0

    valid_thumb_paths = {get_thumb_path(p) for p in valid_preview_paths if p}
    removed = 0

    for f in THUMB_DIR.glob("*.jpg"):
        if f not in valid_thumb_paths:
            try:
                f.unlink()
                if _current_cache_bytes is not None:
                    _current_cache_bytes -= f.stat().st_size
                removed += 1
            except OSError as e:
                logger.warning(f"清理缩略图失败: {f} - {e}")

    if removed:
        logger.info(f"清理缩略图缓存: 删除 {removed} 个过期文件")

    # 清理无效文件后再做 LRU 淘汰
    removed += _evict_lru()
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

        # 确保缓存大小已初始化
        _get_cache_size()

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
                # 访问已有缓存文件，更新 atime（供 LRU 排序）
                _touch_thumb(thumb_path)
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

                # 增量更新内存中的缓存大小
                global _current_cache_bytes
                try:
                    _current_cache_bytes = (_current_cache_bytes or 0) + thumb_path.stat().st_size
                except OSError:
                    pass

                # 只有超过上限才触发淘汰（不再每 50 张检查）
                if _current_cache_bytes > MAX_CACHE_BYTES:
                    _evict_lru()

            except Exception as e:
                logger.warning(f"缩略图生成失败: {preview_path} - {e}")

        self.finished.emit(generated)
