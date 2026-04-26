"""SQLite 数据库层"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .models import Wallpaper

DB_DIR = Path.home() / ".wallpaper-manager"
DB_PATH = DB_DIR / "wallpapers.db"

# ---------------------------------------------------------------------------
# Schema Migration
# ---------------------------------------------------------------------------
# 当前数据库 schema 版本。每次修改表结构时递增，并添加对应的 _migrate_vN 函数。
#
# 如何添加新迁移:
#   1. 将 SCHEMA_VERSION 递增（例如改为 3）
#   2. 编写 _migrate_v3(conn) 函数，执行 ALTER TABLE / CREATE INDEX 等
#   3. init_db() 会自动检测版本差距并按顺序调用迁移函数
#
# 注意: 迁移函数按版本号升序依次执行，每个函数只负责从 v(N-1) → vN 的变更。

SCHEMA_VERSION: int = 1


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """v1: 初始 schema — wallpapers 表及索引。

    全新安装时由 init_db() 中的 CREATE TABLE 语句直接创建，
    此函数留空，仅作为迁移链的起点占位。
    """
    pass


# 迁移注册表: 版本号 → 迁移函数
# 新增迁移时在此追加，例如: 3: _migrate_v3
_MIGRATIONS: dict[int, callable] = {
    1: _migrate_v1,
}


def _get_current_version(conn: sqlite3.Connection) -> int:
    """读取当前 schema 版本，无记录则返回 0。"""
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    return row[0] if row else 0


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    """写入（或更新）schema 版本。"""
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


def _run_migrations(conn: sqlite3.Connection) -> None:
    """检测版本差距，按顺序执行所需迁移，最后更新版本号。"""
    current = _get_current_version(conn)
    if current >= SCHEMA_VERSION:
        return

    # 按版本号升序执行缺失的迁移
    for v in sorted(_MIGRATIONS.keys()):
        if v > current:
            _MIGRATIONS[v](conn)

    _set_version(conn, SCHEMA_VERSION)


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
    """创建表结构并执行 schema 迁移。

    全新安装: 创建所有表 → 设 schema_version = SCHEMA_VERSION
    已有数据库: 仅执行版本差距所需的迁移
    """
    with get_connection() as conn:
        # 1. 确保 schema_version 表存在
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            )
        """)

        # 2. 确保 wallpapers 表和索引存在（全新安装时创建，已有则跳过）
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

        # 3. 执行迁移（全新安装时 current=0，会跑全部迁移并设版本号）
        _run_migrations(conn)
        conn.commit()


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
