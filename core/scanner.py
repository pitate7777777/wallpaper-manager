"""扫描 Wallpaper Engine 本地目录，解析 project.json 入库

使用线程池并行解析 project.json（I/O 密集），数据库写入在主线程完成。
"""
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional

from .db import upsert_wallpaper, remove_wallpaper, get_connection
from .models import Wallpaper

logger = logging.getLogger(__name__)

# 并行解析线程数（I/O 密集，取 CPU 核数×2，但不超过 8）
_PARSE_WORKERS = min(8, (os.cpu_count() or 1) * 2)

# project.json 中已知并解析的字段（其余归入 extra_data）
_PARSED_KEYS = frozenset({
    "workshopid", "title", "type", "file", "preview",
    "tags", "contentrating", "description", "general",
})


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

    if not isinstance(data, dict):
        logger.warning(f"project.json 顶层非对象: {project_file}")
        return None

    # ── 提取主题色 ────────────────────────────────────────────
    scheme_color = ""
    try:
        scheme_color = data["general"]["properties"]["schemecolor"]["value"]
        if not isinstance(scheme_color, str):
            scheme_color = ""
    except (KeyError, TypeError):
        pass

    # ── 标签类型校验 ──────────────────────────────────────────
    raw_tags = data.get("tags", [])
    if isinstance(raw_tags, list):
        # 过滤非字符串元素（某些壁纸可能混入整数或对象）
        tags = [str(t) for t in raw_tags if isinstance(t, (str, int, float))]
    else:
        tags = []

    # ── 保留未解析字段（extra_data）──────────────────────────
    extra = {k: v for k, v in data.items() if k not in _PARSED_KEYS}
    extra_data = json.dumps(extra, ensure_ascii=False) if extra else ""

    # 注: version 字段（部分壁纸包含）会自动归入 extra_data，当前不做独立逻辑判断

    return Wallpaper(
        folder_path=str(folder_path),
        workshop_id=str(data.get("workshopid", "")),
        title=data.get("title", folder_path.name),
        wp_type=data.get("type", ""),
        file=data.get("file", ""),
        preview=data.get("preview", ""),
        tags=tags,
        content_rating=data.get("contentrating", ""),
        description=data.get("description", ""),
        scheme_color=scheme_color,
        extra_data=extra_data,
    )


def scan_directory(
    root_dir: str,
    progress_callback: Callable[[int, int, str], None] = None,
) -> dict:
    """扫描目录下所有壁纸文件夹（并行解析 project.json）

    Args:
        root_dir: Wallpaper Engine 的 workshop 目录
        progress_callback: 进度回调 (current, total, folder_name)

    Returns:
        扫描结果统计 {"added": int, "updated": int, "removed": int, "errors": int,
                      "error_details": list[dict]}
    """
    root = Path(root_dir)
    if not root.is_dir():
        raise ValueError(f"目录不存在: {root_dir}")

    # 找到所有含 project.json 的子文件夹
    folders = [d for d in root.iterdir() if d.is_dir() and (d / "project.json").exists()]
    total = len(folders)
    stats = {"added": 0, "updated": 0, "removed": 0, "errors": 0, "error_details": []}

    if total == 0:
        # 无壁纸目录，仅做清理
        with get_connection() as conn:
            existing = {r["folder_path"] for r in conn.execute(
                "SELECT folder_path FROM wallpapers"
            ).fetchall()}
        for path in existing:
            remove_wallpaper(path)
            stats["removed"] += 1
        return stats

    # 记录当前数据库中的路径，用于检测已删除的
    with get_connection() as conn:
        existing = {r["folder_path"] for r in conn.execute(
            "SELECT folder_path FROM wallpapers"
        ).fetchall()}

    # ── 并行解析 project.json ────────────────────────────────
    parsed: dict[str, Optional[Wallpaper]] = {}  # folder_path → Wallpaper | None
    completed = 0

    with ThreadPoolExecutor(max_workers=_PARSE_WORKERS) as pool:
        future_to_folder = {
            pool.submit(parse_project_json, folder): folder
            for folder in folders
        }
        for future in as_completed(future_to_folder):
            folder = future_to_folder[future]
            completed += 1
            if progress_callback:
                progress_callback(completed, total, folder.name)

            try:
                wp = future.result()
                parsed[str(folder)] = wp
            except Exception as e:
                logger.error(f"解析异常: {folder} - {e}")
                parsed[str(folder)] = None
                stats["error_details"].append({
                    "folder": folder.name,
                    "reason": str(e),
                })

    # ── 批量写入数据库（单事务）────────────────────────────────
    found_paths = set(parsed.keys())

    with get_connection() as conn:
        try:
            for folder_path_str, wp in parsed.items():
                if wp is None:
                    stats["errors"] += 1
                    continue
                try:
                    conn.execute("""
                        INSERT INTO wallpapers (folder_path, workshop_id, title, wp_type, file,
                                                preview, tags, content_rating, description,
                                                scheme_color, extra_data, is_favorite)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(folder_path) DO UPDATE SET
                            workshop_id=excluded.workshop_id,
                            title=excluded.title,
                            wp_type=excluded.wp_type,
                            file=excluded.file,
                            preview=excluded.preview,
                            tags=excluded.tags,
                            content_rating=excluded.content_rating,
                            description=excluded.description,
                            scheme_color=excluded.scheme_color,
                            extra_data=excluded.extra_data
                    """, (
                        wp.folder_path, wp.workshop_id, wp.title, wp.wp_type,
                        wp.file, wp.preview, json.dumps(wp.tags, ensure_ascii=False),
                        wp.content_rating, wp.description, wp.scheme_color,
                        wp.extra_data, int(wp.is_favorite),
                    ))
                    if folder_path_str in existing:
                        stats["updated"] += 1
                    else:
                        stats["added"] += 1
                except Exception as e:
                    logger.error(f"入库失败: {folder_path_str} - {e}")
                    stats["errors"] += 1
                    stats["error_details"].append({
                        "folder": Path(folder_path_str).name,
                        "reason": f"数据库写入失败: {e}",
                    })

            # 清理已不存在的记录
            removed_paths = existing - found_paths
            for path in removed_paths:
                conn.execute("DELETE FROM wallpapers WHERE folder_path = ?", (path,))
                stats["removed"] += 1

            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return stats
