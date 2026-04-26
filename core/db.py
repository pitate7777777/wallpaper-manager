"""SQLite 数据库层"""
import json
import logging
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .models import Wallpaper

logger = logging.getLogger(__name__)

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

SCHEMA_VERSION: int = 2


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """v1: 初始 schema — wallpapers 表及索引。

    全新安装时，init_db() 中的 CREATE TABLE IF NOT EXISTS 语句已直接建好表结构，
    此函数有意留空，仅作为迁移链的起点占位符（version 0 → 1）。

    【全新安装行为说明】
    全新安装时 _get_current_version 返回 0，_run_migrations 会依次执行
    v1（空操作）→ v2 → ... → 最新版本，最终将 schema_version 写为
    SCHEMA_VERSION，确保迁移链从第一个版本起始，与升级路径保持一致。
    后续维护者勿将此函数改为非幂等操作，因为全新安装时它总会被调用。
    """
    pass


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """v2: 新增 extra_data 列（存储 project.json 中未解析的字段）。"""
    # 幂等：先检查列是否已存在（CREATE TABLE IF NOT EXISTS 可能已包含该列）
    cursor = conn.execute("PRAGMA table_info(wallpapers)")
    columns = {row["name"] for row in cursor.fetchall()}
    if "extra_data" not in columns:
        conn.execute("ALTER TABLE wallpapers ADD COLUMN extra_data TEXT DEFAULT ''")


# 迁移注册表: 版本号 → 迁移函数
# 新增迁移时在此追加，例如: 3: _migrate_v3
_MIGRATIONS: dict[int, callable] = {
    1: _migrate_v1,
    2: _migrate_v2,
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


def _sqlite_regexp(pattern: str, value: str) -> bool:
    """SQLite 自定义 REGEXP 函数，支持在 SQL 中直接做正则匹配。

    匹配失败（无效正则或无匹配）返回 0，成功返回 1。
    """
    if value is None:
        return False
    try:
        return bool(re.search(pattern, value, re.IGNORECASE))
    except re.error:
        return False


@contextmanager
def get_connection():
    """获取数据库连接（自动关闭）"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.create_function("REGEXP", 2, _sqlite_regexp)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """创建表结构并执行 schema 迁移。

    全新安装: 创建所有表 → 设 schema_version = SCHEMA_VERSION
    已有数据库: 仅执行版本差距所需的迁移（迁移前自动备份）
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
                extra_data      TEXT DEFAULT '',
                is_favorite     INTEGER DEFAULT 0,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_workshop_id ON wallpapers(workshop_id);
            CREATE INDEX IF NOT EXISTS idx_title ON wallpapers(title);
            CREATE INDEX IF NOT EXISTS idx_type ON wallpapers(wp_type);
            CREATE INDEX IF NOT EXISTS idx_favorite ON wallpapers(is_favorite);
        """)

        # 3. 迁移前自动备份（仅在需要迁移时）
        current = _get_current_version(conn)
        if current > 0 and current < SCHEMA_VERSION:
            backup_database()

        # 4. 执行迁移（全新安装时 current=0，会跑全部迁移并设版本号）
        _run_migrations(conn)
        conn.commit()


def backup_database(max_backups: int = 3) -> Optional[Path]:
    """备份数据库文件，保留最近 max_backups 份。

    Returns:
        备份文件路径；数据库不存在或备份失败返回 None
    """
    import shutil

    if not DB_PATH.exists():
        return None

    backup_dir = DB_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"wallpapers_{timestamp}.db"

    try:
        shutil.copy2(str(DB_PATH), str(backup_path))
        logger.info(f"数据库已备份: {backup_path}")

        # 清理旧备份，保留最近 max_backups 份
        backups = sorted(backup_dir.glob("wallpapers_*.db"), key=lambda p: p.stat().st_mtime)
        while len(backups) > max_backups:
            oldest = backups.pop(0)
            oldest.unlink()
            logger.info(f"清理旧备份: {oldest}")

        return backup_path
    except Exception as e:
        logger.error(f"数据库备份失败: {e}")
        return None


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
        extra_data=row["extra_data"] if "extra_data" in row.keys() else "",
        is_favorite=bool(row["is_favorite"]),
    )


def upsert_wallpaper(wp: Wallpaper) -> int:
    """插入或更新壁纸记录

    ON CONFLICT 策略：仅更新元数据字段（标题、类型、标签等），
    有意**不覆盖 is_favorite**，确保用户手动收藏的状态在重新扫描后不会丢失。
    """
    with get_connection() as conn:
        cursor = conn.execute("""
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
                -- is_favorite 有意不更新，保留用户收藏状态
        """, (
            wp.folder_path, wp.workshop_id, wp.title, wp.wp_type,
            wp.file, wp.preview, json.dumps(wp.tags, ensure_ascii=False),
            wp.content_rating, wp.description, wp.scheme_color,
            wp.extra_data, int(wp.is_favorite),
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


def batch_set_favorite(wallpaper_ids: list[int], favorite: bool) -> int:
    """批量设置收藏状态（单次 SQL，避免 N+1）

    Args:
        wallpaper_ids: 壁纸 ID 列表
        favorite: 目标收藏状态

    Returns:
        受影响的行数
    """
    if not wallpaper_ids:
        return 0
    placeholders = ",".join(["?"] * len(wallpaper_ids))
    with get_connection() as conn:
        cursor = conn.execute(
            f"UPDATE wallpapers SET is_favorite = ? WHERE id IN ({placeholders})",
            [int(favorite)] + wallpaper_ids,
        )
        conn.commit()
        return cursor.rowcount


def _escape_like(pattern: str) -> str:
    """转义 LIKE 模式中的通配符 % 和 _"""
    return re.sub(r'([%_])', r'\\\1', pattern)


def query_wallpapers(
    search: str = "",
    wp_type: str = "",
    tags: list[str] | None = None,
    favorites_only: bool = False,
    order_by: str = "title",
    search_mode: str = "simple",
    tags_mode: str = "any",
    exclude_tags: list[str] | None = None,
    content_rating: str = "",
) -> list[Wallpaper]:
    """查询壁纸列表

    Args:
        search: 搜索关键词
        wp_type: 壁纸类型过滤
        tags: 标签列表过滤
        favorites_only: 仅收藏
        order_by: 排序方式
        search_mode: 搜索模式 - "simple"(LIKE), "regex", "exact"
        tags_mode: 标签匹配模式 - "any"(匹配任一) / "all"(匹配全部)
        exclude_tags: 要排除的标签列表
        content_rating: 内容分级过滤
    """
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
            if search_mode == "exact":
                # 精确匹配：title 完全相等；tags 匹配 JSON 数组中的精确元素
                # 用 %"<term>"% 确保匹配 JSON 字符串中的完整词，不会误匹配子串
                escaped = _escape_like(search)
                conditions.append('(title = ? OR tags LIKE ?)')
                params.extend([search, f'%"{escaped}%'])
            elif search_mode == "regex":
                # 正则搜索：通过 SQLite REGEXP 函数在数据库侧过滤
                # 避免将全部记录加载到 Python 内存中
                try:
                    re.compile(search, re.IGNORECASE)
                except re.error:
                    # 无效正则，直接返回空结果
                    return []
                conditions.append("(title REGEXP ? OR tags REGEXP ?)")
                params.extend([search, search])
            else:
                # simple (默认，LIKE 匹配)
                escaped = _escape_like(search)
                conditions.append("(title LIKE ? OR tags LIKE ?)")
                params.extend([f"%{escaped}%", f"%{escaped}%"])

        if wp_type:
            conditions.append("wp_type = ?")
            params.append(wp_type)

        if tags:
            if tags_mode == "all":
                # 所有标签都必须匹配
                for tag in tags:
                    conditions.append("tags LIKE ?")
                    params.append(f"%{tag}%")
            else:
                # 匹配任一标签
                tag_conds = ["tags LIKE ?" for _ in tags]
                conditions.append(f"({' OR '.join(tag_conds)})")
                params.extend([f"%{t}%" for t in tags])

        if favorites_only:
            conditions.append("is_favorite = 1")

        if content_rating:
            conditions.append("content_rating = ?")
            params.append(content_rating)

        where = " AND ".join(conditions) if conditions else "1=1"

        rows = conn.execute(
            f"SELECT * FROM wallpapers WHERE {where} ORDER BY {order}",
            params
        ).fetchall()

        results = [_row_to_wallpaper(r) for r in rows]

        # 排除标签后处理
        if exclude_tags:
            results = [
                wp for wp in results
                if not any(t in wp.tags for t in exclude_tags)
            ]

        return results


def get_all_tags() -> list[str]:
    """获取所有去重标签"""
    with get_connection() as conn:
        rows = conn.execute("SELECT tags FROM wallpapers WHERE tags != '[]'").fetchall()
    tag_set = set()
    for row in rows:
        for tag in json.loads(row["tags"]):
            tag_set.add(tag)
    return sorted(tag_set)


def get_all_ratings() -> list[str]:
    """获取所有去重的内容分级（按出现频次降序）"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT content_rating, COUNT(*) as c FROM wallpapers "
            "WHERE content_rating != '' GROUP BY content_rating ORDER BY c DESC"
        ).fetchall()
    return [r["content_rating"] for r in rows]


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


# ---------------------------------------------------------------------------
# 标签管理
# ---------------------------------------------------------------------------

def rename_tag(old_name: str, new_name: str) -> int:
    """重命名标签：将所有壁纸中的 old_name 替换为 new_name。

    Args:
        old_name: 旧标签名
        new_name: 新标签名

    Returns:
        受影响的壁纸数量
    """
    if not old_name or not new_name or old_name == new_name:
        return 0

    count = 0
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, tags FROM wallpapers WHERE tags LIKE ?", (f'%"{old_name}"%',)
        ).fetchall()
        for row in rows:
            tags = json.loads(row["tags"])
            if old_name in tags:
                tags = [new_name if t == old_name else t for t in tags]
                # 去重（保持顺序）
                tags = list(dict.fromkeys(tags))
                conn.execute(
                    "UPDATE wallpapers SET tags = ? WHERE id = ?",
                    (json.dumps(tags, ensure_ascii=False), row["id"]),
                )
                count += 1
        conn.commit()
    return count


def merge_tags(source_names: list[str], target_name: str) -> int:
    """合并多个标签为一个。

    将 source_names 中的所有标签替换为 target_name。
    同一张壁纸中如果存在多个源标签，合并后只保留一个 target_name。

    Args:
        source_names: 要合并的源标签列表
        target_name: 合并后的目标标签名

    Returns:
        受影响的壁纸数量
    """
    if not source_names or not target_name:
        return 0
    source_set = set(source_names)
    if target_name in source_set:
        source_set.discard(target_name)
        if not source_set:
            return 0

    count = 0
    with get_connection() as conn:
        # 查找包含任一源标签的壁纸
        like_conditions = " OR ".join(["tags LIKE ?" for _ in source_set])
        like_params = [f'%"{s}"%' for s in source_set]
        rows = conn.execute(
            f"SELECT id, tags FROM wallpapers WHERE {like_conditions}",
            like_params,
        ).fetchall()

        for row in rows:
            tags = json.loads(row["tags"])
            if any(t in source_set for t in tags):
                target_already = target_name in tags
                new_tags = []
                merged = False
                for t in tags:
                    if t in source_set:
                        if not merged and not target_already:
                            new_tags.append(target_name)
                            merged = True
                        # 跳过其他源标签
                    else:
                        new_tags.append(t)
                if not merged and not target_already:
                    new_tags.append(target_name)
                # 去重：保留顺序
                new_tags = list(dict.fromkeys(new_tags))
                conn.execute(
                    "UPDATE wallpapers SET tags = ? WHERE id = ?",
                    (json.dumps(new_tags, ensure_ascii=False), row["id"]),
                )
                count += 1
        conn.commit()
    return count


def update_wallpaper_tags(wallpaper_id: int, tags: list[str]):
    """更新指定壁纸的标签"""
    with get_connection() as conn:
        conn.execute(
            "UPDATE wallpapers SET tags = ? WHERE id = ?",
            (json.dumps(tags, ensure_ascii=False), wallpaper_id),
        )
        conn.commit()


def get_tag_stats() -> list[dict]:
    """获取标签统计信息（使用次数）

    Returns:
        [{"name": "anime", "count": 42}, ...] 按使用次数降序排列
    """
    with get_connection() as conn:
        rows = conn.execute("SELECT tags FROM wallpapers WHERE tags != '[]'").fetchall()
    tag_counts: dict[str, int] = {}
    for row in rows:
        for tag in json.loads(row["tags"]):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    stats = [{"name": k, "count": v} for k, v in tag_counts.items()]
    stats.sort(key=lambda x: (-x["count"], x["name"]))
    return stats


def delete_tag(tag_name: str) -> int:
    """从所有壁纸中删除指定标签。

    Args:
        tag_name: 要删除的标签名

    Returns:
        受影响的壁纸数量
    """
    if not tag_name:
        return 0

    count = 0
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, tags FROM wallpapers WHERE tags LIKE ?", (f'%"{tag_name}"%',)
        ).fetchall()
        for row in rows:
            tags = json.loads(row["tags"])
            if tag_name in tags:
                tags = [t for t in tags if t != tag_name]
                conn.execute(
                    "UPDATE wallpapers SET tags = ? WHERE id = ?",
                    (json.dumps(tags, ensure_ascii=False), row["id"]),
                )
                count += 1
        conn.commit()
    return count
