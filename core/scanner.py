"""扫描 Wallpaper Engine 本地目录，解析 project.json 入库"""
import json
import logging
from pathlib import Path
from typing import Callable, Optional

from .db import upsert_wallpaper, remove_wallpaper, get_connection
from .models import Wallpaper

logger = logging.getLogger(__name__)


def parse_project_json(folder_path: Path) -> Optional[Wallpaper]:
    """解析单个壁纸文件夹的 project.json"""
    project_file = folder_path / "project.json"
    if not project_file.exists():
        return None

    try:
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"解析失败: {project_file} - {e}")
        return None

    # 提取主题色
    scheme_color = ""
    try:
        scheme_color = data["general"]["properties"]["schemecolor"]["value"]
    except (KeyError, TypeError):
        pass

    return Wallpaper(
        folder_path=str(folder_path),
        workshop_id=str(data.get("workshopid", "")),
        title=data.get("title", folder_path.name),
        wp_type=data.get("type", ""),
        file=data.get("file", ""),
        preview=data.get("preview", ""),
        tags=data.get("tags", []),
        content_rating=data.get("contentrating", ""),
        description=data.get("description", ""),
        scheme_color=scheme_color,
    )


def scan_directory(
    root_dir: str,
    progress_callback: Callable[[int, int, str], None] = None,
) -> dict:
    """
    扫描目录下所有壁纸文件夹

    Args:
        root_dir: Wallpaper Engine 的 workshop 目录
        progress_callback: 进度回调 (current, total, folder_name)

    Returns:
        扫描结果统计 {"added": int, "updated": int, "removed": int, "errors": int}
    """
    root = Path(root_dir)
    if not root.is_dir():
        raise ValueError(f"目录不存在: {root_dir}")

    # 找到所有含 project.json 的子文件夹
    folders = [d for d in root.iterdir() if d.is_dir() and (d / "project.json").exists()]
    total = len(folders)
    stats = {"added": 0, "updated": 0, "removed": 0, "errors": 0}

    # 记录当前数据库中的路径，用于检测已删除的
    conn = get_connection()
    existing = {r["folder_path"] for r in conn.execute("SELECT folder_path FROM wallpapers").fetchall()}
    conn.close()

    found_paths = set()

    for i, folder in enumerate(folders):
        if progress_callback:
            progress_callback(i + 1, total, folder.name)

        found_paths.add(str(folder))
        wp = parse_project_json(folder)
        if wp:
            try:
                if str(folder) in existing:
                    stats["updated"] += 1
                else:
                    stats["added"] += 1
                upsert_wallpaper(wp)
            except Exception as e:
                logger.error(f"入库失败: {folder} - {e}")
                stats["errors"] += 1
        else:
            stats["errors"] += 1

    # 清理已不存在的记录
    removed_paths = existing - found_paths
    for path in removed_paths:
        remove_wallpaper(path)
        stats["removed"] += 1

    return stats
