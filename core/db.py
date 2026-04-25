"""SQLite 数据库层"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .models import Wallpaper

DB_DIR = Path.home() / ".wallpaper-manager"
DB_PATH = DB_DIR / "wallpapers.db"


@contextmanager
def get_connection():
    """获取数据库连接（自动关闭）"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """创建表结构"""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS wallpapers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_path     TEXT UNIQUE NOT NULL,
                workshop_id     TEXT DEFAULT '',
                title           TEXT DEFAULT '',
                wp_type         TEXT DEFAULT '',
                file            TEXT DEFAULT '',
                preview         TEXT DEFAULT '',
                tags            TEXT DEFAULT '[]',
                content_rating  TEXT DEFAULT '',
                description     TEXT DEFAULT '',
                scheme_color    TEXT DEFAULT '',
                is_favorite     INTEGER DEFAULT 0,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_workshop_id ON wallpapers(workshop_id);
            CREATE INDEX IF NOT EXISTS idx_title ON wallpapers(title);
            CREATE INDEX IF NOT EXISTS idx_type ON wallpapers(wp_type);
            CREATE INDEX IF NOT EXISTS idx_favorite ON wallpapers(is_favorite);
        """)


def _row_to_wallpaper(row: sqlite3.Row) -> Wallpaper:
    """将数据库行转为 Wallpaper 对象"""
    return Wallpaper(
        id=row["id"],
        folder_path=row["folder_path"],
        workshop_id=row["workshop_id"],
        title=row["title"],
        wp_type=row["wp_type"],
        file=row["file"],
        preview=row["preview"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        content_rating=row["content_rating"],
        description=row["description"],
        scheme_color=row["scheme_color"],
        is_favorite=bool(row["is_favorite"]),
    )


def upsert_wallpaper(wp: Wallpaper) -> int:
    """插入或更新壁纸记录"""
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO wallpapers (folder_path, workshop_id, title, wp_type, file,
                                    preview, tags, content_rating, description,
                                    scheme_color, is_favorite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(folder_path) DO UPDATE SET
                workshop_id=excluded.workshop_id,
                title=excluded.title,
                wp_type=excluded.wp_type,
                file=excluded.file,
                preview=excluded.preview,
                tags=excluded.tags,
                content_rating=excluded.content_rating,
                description=excluded.description,
                scheme_color=excluded.scheme_color
        """, (
            wp.folder_path, wp.workshop_id, wp.title, wp.wp_type,
            wp.file, wp.preview, json.dumps(wp.tags, ensure_ascii=False),
            wp.content_rating, wp.description, wp.scheme_color,
            int(wp.is_favorite),
        ))
        wp_id = cursor.lastrowid
        conn.commit()
        return wp_id


def toggle_favorite(wallpaper_id: int) -> bool:
    """切换收藏状态，返回新状态"""
    with get_connection() as conn:
        conn.execute("""
            UPDATE wallpapers SET is_favorite = 1 - is_favorite WHERE id = ?
        """, (wallpaper_id,))
        row = conn.execute("SELECT is_favorite FROM wallpapers WHERE id = ?", (wallpaper_id,)).fetchone()
        conn.commit()
        return bool(row["is_favorite"]) if row else False


def set_favorite(wallpaper_id: int, favorite: bool):
    """设置收藏状态（强制指定）"""
    with get_connection() as conn:
        conn.execute("UPDATE wallpapers SET is_favorite = ? WHERE id = ?", (int(favorite), wallpaper_id))
        conn.commit()


def query_wallpapers(
    search: str = "",
    wp_type: str = "",
    tags: list[str] = None,
    favorites_only: bool = False,
    order_by: str = "title",
) -> list[Wallpaper]:
    """查询壁纸列表"""
    # 白名单校验，防止 SQL 注入
    order_map = {
        "title": "title COLLATE NOCASE ASC",
        "type": "wp_type ASC",
        "newest": "created_at DESC",
        "favorite": "is_favorite DESC, title COLLATE NOCASE ASC",
    }
    order = order_map.get(order_by, "title COLLATE NOCASE ASC")

    with get_connection() as conn:
        conditions = []
        params = []

        if search:
            conditions.append("(title LIKE ? OR tags LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        if wp_type:
            conditions.append("wp_type = ?")
            params.append(wp_type)

        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")

        if favorites_only:
            conditions.append("is_favorite = 1")

        where = " AND ".join(conditions) if conditions else "1=1"

        rows = conn.execute(
            f"SELECT * FROM wallpapers WHERE {where} ORDER BY {order}",
            params
        ).fetchall()

        return [_row_to_wallpaper(r) for r in rows]


def get_all_tags() -> list[str]:
    """获取所有去重标签"""
    with get_connection() as conn:
        rows = conn.execute("SELECT tags FROM wallpapers WHERE tags != '[]'").fetchall()
    tag_set = set()
    for row in rows:
        for tag in json.loads(row["tags"]):
            tag_set.add(tag)
    return sorted(tag_set)


def get_stats() -> dict:
    """获取统计信息"""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM wallpapers").fetchone()["c"]
        by_type = conn.execute(
            "SELECT wp_type, COUNT(*) as c FROM wallpapers GROUP BY wp_type"
        ).fetchall()
        favorites = conn.execute("SELECT COUNT(*) as c FROM wallpapers WHERE is_favorite=1").fetchone()["c"]
    return {
        "total": total,
        "favorites": favorites,
        "by_type": {r["wp_type"]: r["c"] for r in by_type},
    }


def remove_wallpaper(folder_path: str):
    """删除壁纸记录（文件夹不再存在时调用）"""
    with get_connection() as conn:
        conn.execute("DELETE FROM wallpapers WHERE folder_path = ?", (folder_path,))
        conn.commit()
