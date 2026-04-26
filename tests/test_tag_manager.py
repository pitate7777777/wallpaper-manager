"""core.tag_manager / core.db 标签管理功能测试"""
import json
from pathlib import Path

import pytest

from core.models import Wallpaper


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch, tmp_path):
    """将 DB_PATH 重定向到临时文件，并初始化表结构"""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("core.db.DB_PATH", db_file)
    monkeypatch.setattr("core.db.DB_DIR", tmp_path)
    from core.db import init_db
    init_db()
    yield db_file


def _insert_wallpaper(**kwargs) -> int:
    """快捷插入壁纸并返回 id"""
    from core.db import upsert_wallpaper
    wp = Wallpaper(**kwargs)
    return upsert_wallpaper(wp)


def _get_tags(wallpaper_id: int) -> list[str]:
    """读取指定壁纸的标签"""
    from core.db import get_connection
    with get_connection() as conn:
        row = conn.execute("SELECT tags FROM wallpapers WHERE id = ?", (wallpaper_id,)).fetchone()
    return json.loads(row["tags"]) if row else []


# ─── rename_tag ──────────────────────────────────────────────


class TestRenameTag:
    """rename_tag 测试"""

    def test_rename_single(self):
        from core.db import rename_tag
        _insert_wallpaper(folder_path="/tmp/r1", tags=["anime", "nature"])
        count = rename_tag("anime", "animation")
        assert count == 1
        assert _get_tags(1) == ["animation", "nature"]

    def test_rename_multiple_wallpapers(self):
        from core.db import rename_tag
        _insert_wallpaper(folder_path="/tmp/r2a", tags=["anime", "nature"])
        _insert_wallpaper(folder_path="/tmp/r2b", tags=["anime", "dark"])
        count = rename_tag("anime", "animation")
        assert count == 2
        assert _get_tags(1) == ["animation", "nature"]
        assert _get_tags(2) == ["animation", "dark"]

    def test_rename_no_match(self):
        from core.db import rename_tag
        _insert_wallpaper(folder_path="/tmp/r3", tags=["nature"])
        count = rename_tag("anime", "animation")
        assert count == 0
        assert _get_tags(1) == ["nature"]

    def test_rename_empty_args(self):
        from core.db import rename_tag
        assert rename_tag("", "new") == 0
        assert rename_tag("old", "") == 0
        assert rename_tag("same", "same") == 0

    def test_rename_dedup(self):
        """重命名后如果目标标签已存在，应去重"""
        from core.db import rename_tag
        _insert_wallpaper(folder_path="/tmp/r5", tags=["anime", "animation"])
        count = rename_tag("anime", "animation")
        assert count == 1
        tags = _get_tags(1)
        assert tags.count("animation") == 1

    def test_rename_preserves_order(self):
        from core.db import rename_tag
        _insert_wallpaper(folder_path="/tmp/r6", tags=["a", "anime", "z"])
        rename_tag("anime", "ANIME")
        assert _get_tags(1) == ["a", "ANIME", "z"]


# ─── merge_tags ──────────────────────────────────────────────


class TestMergeTags:
    """merge_tags 测试"""

    def test_merge_two_tags(self):
        from core.db import merge_tags
        # wp1 has "anime" (target stays after merge), wp2 has "animation" (source → target)
        _insert_wallpaper(folder_path="/tmp/m1", tags=["anime", "nature"])
        _insert_wallpaper(folder_path="/tmp/m2", tags=["animation", "dark"])
        # merge_tags removes target from sources: source_set={"animation"}
        # Only wp2 matches the query
        count = merge_tags(["anime", "animation"], "anime")
        assert count == 1
        assert _get_tags(1) == ["anime", "nature"]  # wp1 unchanged
        assert "anime" in _get_tags(2)
        assert "animation" not in _get_tags(2)

    def test_merge_with_target_in_sources(self):
        """目标标签在源标签列表中"""
        from core.db import merge_tags
        _insert_wallpaper(folder_path="/tmp/m3", tags=["a", "b", "c"])
        count = merge_tags(["a", "b"], "a")
        assert count == 1
        tags = _get_tags(1)
        assert "a" in tags
        assert "b" not in tags

    def test_merge_no_match(self):
        from core.db import merge_tags
        _insert_wallpaper(folder_path="/tmp/m4", tags=["nature"])
        count = merge_tags(["anime", "animation"], "cartoon")
        assert count == 0
        assert _get_tags(1) == ["nature"]

    def test_merge_empty_args(self):
        from core.db import merge_tags
        assert merge_tags([], "target") == 0
        assert merge_tags(["a"], "") == 0

    def test_merge_single_source(self):
        """单个源标签也应正常工作"""
        from core.db import merge_tags
        _insert_wallpaper(folder_path="/tmp/m6", tags=["anime"])
        count = merge_tags(["anime"], "animation")
        assert count == 1
        assert _get_tags(1) == ["animation"]

    def test_merge_same_wallpaper_multiple_sources(self):
        """同一壁纸包含多个源标签，合并后只保留一个目标"""
        from core.db import merge_tags
        _insert_wallpaper(folder_path="/tmp/m7", tags=["anime", "animation", "nature"])
        count = merge_tags(["anime", "animation"], "anime")
        assert count == 1
        tags = _get_tags(1)
        assert tags.count("anime") == 1
        assert "animation" not in tags
        assert "nature" in tags


# ─── delete_tag ──────────────────────────────────────────────


class TestDeleteTag:
    """delete_tag 测试"""

    def test_delete_single(self):
        from core.db import delete_tag
        _insert_wallpaper(folder_path="/tmp/d1", tags=["anime", "nature"])
        count = delete_tag("anime")
        assert count == 1
        assert _get_tags(1) == ["nature"]

    def test_delete_multiple_wallpapers(self):
        from core.db import delete_tag
        _insert_wallpaper(folder_path="/tmp/d2a", tags=["anime", "nature"])
        _insert_wallpaper(folder_path="/tmp/d2b", tags=["anime", "dark"])
        count = delete_tag("anime")
        assert count == 2
        assert _get_tags(1) == ["nature"]
        assert _get_tags(2) == ["dark"]

    def test_delete_no_match(self):
        from core.db import delete_tag
        _insert_wallpaper(folder_path="/tmp/d3", tags=["nature"])
        count = delete_tag("anime")
        assert count == 0
        assert _get_tags(1) == ["nature"]

    def test_delete_empty_args(self):
        from core.db import delete_tag
        assert delete_tag("") == 0

    def test_delete_all_tags(self):
        """删除壁纸上唯一的标签"""
        from core.db import delete_tag
        _insert_wallpaper(folder_path="/tmp/d5", tags=["anime"])
        count = delete_tag("anime")
        assert count == 1
        assert _get_tags(1) == []

    def test_delete_preserves_other_tags(self):
        from core.db import delete_tag
        _insert_wallpaper(folder_path="/tmp/d6", tags=["a", "b", "c"])
        delete_tag("b")
        assert _get_tags(1) == ["a", "c"]


# ─── update_wallpaper_tags ──────────────────────────────────


class TestUpdateWallpaperTags:
    """update_wallpaper_tags 测试"""

    def test_update_tags(self):
        from core.db import update_wallpaper_tags
        wp_id = _insert_wallpaper(folder_path="/tmp/u1", tags=["old"])
        update_wallpaper_tags(wp_id, ["new1", "new2"])
        assert _get_tags(wp_id) == ["new1", "new2"]

    def test_update_to_empty(self):
        from core.db import update_wallpaper_tags
        wp_id = _insert_wallpaper(folder_path="/tmp/u2", tags=["tag"])
        update_wallpaper_tags(wp_id, [])
        assert _get_tags(wp_id) == []

    def test_update_unicode_tags(self):
        from core.db import update_wallpaper_tags
        wp_id = _insert_wallpaper(folder_path="/tmp/u3", tags=[])
        update_wallpaper_tags(wp_id, ["动漫", "风景", "4K"])
        assert _get_tags(wp_id) == ["动漫", "风景", "4K"]


# ─── get_tag_stats ───────────────────────────────────────────


class TestGetTagStats:
    """get_tag_stats 测试"""

    def test_empty(self):
        from core.db import get_tag_stats
        assert get_tag_stats() == []

    def test_single_tag(self):
        from core.db import get_tag_stats
        _insert_wallpaper(folder_path="/tmp/s1", tags=["anime"])
        stats = get_tag_stats()
        assert len(stats) == 1
        assert stats[0]["name"] == "anime"
        assert stats[0]["count"] == 1

    def test_count_multiple(self):
        from core.db import get_tag_stats
        _insert_wallpaper(folder_path="/tmp/s2a", tags=["anime", "nature"])
        _insert_wallpaper(folder_path="/tmp/s2b", tags=["anime", "dark"])
        _insert_wallpaper(folder_path="/tmp/s2c", tags=["nature"])
        stats = get_tag_stats()
        by_name = {s["name"]: s["count"] for s in stats}
        assert by_name["anime"] == 2
        assert by_name["nature"] == 2
        assert by_name["dark"] == 1

    def test_sorted_by_count_desc(self):
        from core.db import get_tag_stats
        _insert_wallpaper(folder_path="/tmp/s3a", tags=["a", "b", "c"])
        _insert_wallpaper(folder_path="/tmp/s3b", tags=["b", "c"])
        _insert_wallpaper(folder_path="/tmp/s3c", tags=["c"])
        stats = get_tag_stats()
        counts = [s["count"] for s in stats]
        assert counts == sorted(counts, reverse=True)

    def test_skip_empty_tags(self):
        """tags='[]' 的壁纸不应计入统计"""
        from core.db import get_tag_stats
        _insert_wallpaper(folder_path="/tmp/s4", tags=[])
        assert get_tag_stats() == []


# ─── tag_manager facade ─────────────────────────────────────


class TestTagManagerFacade:
    """core.tag_manager facade 测试"""

    def test_rename(self):
        from core.tag_manager import rename_tag
        _insert_wallpaper(folder_path="/tmp/f1", tags=["old"])
        count = rename_tag("old", "new")
        assert count == 1
        assert _get_tags(1) == ["new"]

    def test_merge(self):
        from core.tag_manager import merge_tags
        _insert_wallpaper(folder_path="/tmp/f2", tags=["a", "b"])
        count = merge_tags(["a", "b"], "c")
        assert count == 1
        assert _get_tags(1) == ["c"]

    def test_delete(self):
        from core.tag_manager import delete_tag
        _insert_wallpaper(folder_path="/tmp/f3", tags=["x", "y"])
        count = delete_tag("x")
        assert count == 1
        assert _get_tags(1) == ["y"]

    def test_stats(self):
        from core.tag_manager import get_tag_stats
        _insert_wallpaper(folder_path="/tmp/f4", tags=["a"])
        stats = get_tag_stats()
        assert len(stats) == 1
        assert stats[0]["name"] == "a"


# ─── 集成场景 ───────────────────────────────────────────────


class TestIntegration:
    """组合操作的集成测试"""

    def test_rename_then_delete(self):
        from core.db import rename_tag, delete_tag
        _insert_wallpaper(folder_path="/tmp/i1", tags=["anime", "nature"])
        rename_tag("anime", "animation")
        assert _get_tags(1) == ["animation", "nature"]
        delete_tag("animation")
        assert _get_tags(1) == ["nature"]

    def test_merge_then_rename(self):
        from core.db import merge_tags, rename_tag
        _insert_wallpaper(folder_path="/tmp/i2", tags=["a", "b"])
        _insert_wallpaper(folder_path="/tmp/i3", tags=["c"])
        merge_tags(["a", "b"], "ab")
        assert _get_tags(1) == ["ab"]
        rename_tag("ab", "merged")
        assert _get_tags(1) == ["merged"]
        assert _get_tags(2) == ["c"]

    def test_operations_on_empty_tags(self):
        """对没有标签的壁纸执行操作不应出错"""
        from core.db import rename_tag, merge_tags, delete_tag
        _insert_wallpaper(folder_path="/tmp/i4", tags=[])
        assert rename_tag("x", "y") == 0
        assert merge_tags(["x", "y"], "z") == 0
        assert delete_tag("x") == 0
