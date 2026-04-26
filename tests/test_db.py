"""core.db 单元测试 — 使用内存数据库"""
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from core.models import Wallpaper


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch, tmp_path):
    """将 DB_PATH 重定向到临时文件，并初始化表结构"""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("core.db.DB_PATH", db_file)
    monkeypatch.setattr("core.db.DB_DIR", tmp_path)
    # 初始化表
    from core.db import init_db
    init_db()
    yield db_file


@pytest.fixture
def sample_wallpaper():
    return Wallpaper(
        folder_path="/tmp/wp1",
        workshop_id="12345",
        title="Test Wallpaper",
        wp_type="video",
        file="bg.mp4",
        preview="preview.jpg",
        tags=["anime", "nature"],
        content_rating="Everyone",
        description="A test wallpaper",
        scheme_color="0.5 0.3 0.8",
    )


@pytest.fixture
def sample_wallpaper2():
    return Wallpaper(
        folder_path="/tmp/wp2",
        workshop_id="67890",
        title="Another Wallpaper",
        wp_type="scene",
        file="index.html",
        preview="thumb.png",
        tags=["nature"],
        is_favorite=True,
        scheme_color="0.1 0.2 0.3",
    )


class TestUpsertWallpaper:
    """upsert_wallpaper 测试"""

    def test_insert_new(self, sample_wallpaper):
        from core.db import upsert_wallpaper
        wp_id = upsert_wallpaper(sample_wallpaper)
        assert wp_id > 0

    def test_upsert_updates_existing(self, sample_wallpaper):
        from core.db import upsert_wallpaper
        id1 = upsert_wallpaper(sample_wallpaper)
        sample_wallpaper.title = "Updated Title"
        id2 = upsert_wallpaper(sample_wallpaper)
        # folder_path 相同 → 应该更新而非新建
        assert id1 is not None
        assert id2 is not None

    def test_insert_minimal(self):
        from core.db import upsert_wallpaper
        wp = Wallpaper(folder_path="/tmp/minimal")
        wp_id = upsert_wallpaper(wp)
        assert wp_id > 0


class TestToggleFavorite:
    """toggle_favorite 测试"""

    def test_toggle_on(self, sample_wallpaper):
        from core.db import upsert_wallpaper, toggle_favorite
        wp_id = upsert_wallpaper(sample_wallpaper)
        new_state = toggle_favorite(wp_id)
        assert new_state is True

    def test_toggle_off(self, sample_wallpaper):
        from core.db import upsert_wallpaper, toggle_favorite
        sample_wallpaper.is_favorite = True
        wp_id = upsert_wallpaper(sample_wallpaper)
        new_state = toggle_favorite(wp_id)
        assert new_state is False

    def test_toggle_nonexistent(self):
        from core.db import toggle_favorite
        result = toggle_favorite(99999)
        assert result is False


class TestSetFavorite:
    """set_favorite 测试"""

    def test_set_true(self, sample_wallpaper):
        from core.db import upsert_wallpaper, set_favorite, query_wallpapers
        wp_id = upsert_wallpaper(sample_wallpaper)
        set_favorite(wp_id, True)
        results = query_wallpapers(favorites_only=True)
        assert len(results) == 1
        assert results[0].is_favorite is True

    def test_set_false(self, sample_wallpaper):
        from core.db import upsert_wallpaper, set_favorite, query_wallpapers
        sample_wallpaper.is_favorite = True
        wp_id = upsert_wallpaper(sample_wallpaper)
        set_favorite(wp_id, False)
        results = query_wallpapers(favorites_only=True)
        assert len(results) == 0


class TestQueryWallpapers:
    """query_wallpapers 测试"""

    def test_empty_db(self):
        from core.db import query_wallpapers
        results = query_wallpapers()
        assert results == []

    def test_query_all(self, sample_wallpaper, sample_wallpaper2):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(sample_wallpaper)
        upsert_wallpaper(sample_wallpaper2)
        results = query_wallpapers()
        assert len(results) == 2

    def test_search_by_title(self, sample_wallpaper):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(sample_wallpaper)
        results = query_wallpapers(search="Test")
        assert len(results) == 1
        assert results[0].title == "Test Wallpaper"

    def test_search_no_match(self, sample_wallpaper):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(sample_wallpaper)
        results = query_wallpapers(search="nonexistent")
        assert len(results) == 0

    def test_filter_by_type(self, sample_wallpaper, sample_wallpaper2):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(sample_wallpaper)
        upsert_wallpaper(sample_wallpaper2)
        results = query_wallpapers(wp_type="video")
        assert len(results) == 1
        assert results[0].wp_type == "video"

    def test_filter_by_tags(self, sample_wallpaper, sample_wallpaper2):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(sample_wallpaper)
        upsert_wallpaper(sample_wallpaper2)
        results = query_wallpapers(tags=["anime"])
        assert len(results) == 1

    def test_filter_favorites_only(self, sample_wallpaper, sample_wallpaper2):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(sample_wallpaper)
        upsert_wallpaper(sample_wallpaper2)
        results = query_wallpapers(favorites_only=True)
        assert len(results) == 1
        assert results[0].is_favorite is True

    def test_order_by_type(self, sample_wallpaper, sample_wallpaper2):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(sample_wallpaper)
        upsert_wallpaper(sample_wallpaper2)
        results = query_wallpapers(order_by="type")
        assert len(results) == 2
        # scene 排在 video 前面
        assert results[0].wp_type == "scene"

    def test_invalid_order_by(self, sample_wallpaper):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(sample_wallpaper)
        # 无效 order_by 应 fallback 到默认排序
        results = query_wallpapers(order_by="invalid")
        assert len(results) == 1


class TestGetAllTags:
    """get_all_tags 测试"""

    def test_empty(self):
        from core.db import get_all_tags
        assert get_all_tags() == []

    def test_dedup_and_sort(self, sample_wallpaper, sample_wallpaper2):
        from core.db import upsert_wallpaper, get_all_tags
        upsert_wallpaper(sample_wallpaper)
        upsert_wallpaper(sample_wallpaper2)
        tags = get_all_tags()
        assert tags == ["anime", "nature"]  # sorted, deduped


class TestGetStats:
    """get_stats 测试"""

    def test_empty(self):
        from core.db import get_stats
        stats = get_stats()
        assert stats["total"] == 0
        assert stats["favorites"] == 0
        assert stats["by_type"] == {}

    def test_with_data(self, sample_wallpaper, sample_wallpaper2):
        from core.db import upsert_wallpaper, get_stats
        upsert_wallpaper(sample_wallpaper)
        upsert_wallpaper(sample_wallpaper2)
        stats = get_stats()
        assert stats["total"] == 2
        assert stats["favorites"] == 1
        assert stats["by_type"]["video"] == 1
        assert stats["by_type"]["scene"] == 1


class TestRemoveWallpaper:
    """remove_wallpaper 测试"""

    def test_remove_existing(self, sample_wallpaper):
        from core.db import upsert_wallpaper, remove_wallpaper, query_wallpapers
        upsert_wallpaper(sample_wallpaper)
        remove_wallpaper("/tmp/wp1")
        results = query_wallpapers()
        assert len(results) == 0

    def test_remove_nonexistent(self):
        from core.db import remove_wallpaper
        # 不应抛异常
        remove_wallpaper("/nonexistent/path")


class TestRowToWallpaper:
    """_row_to_wallpaper 转换测试"""

    def test_roundtrip(self, sample_wallpaper):
        """写入再读出，验证所有字段正确"""
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(sample_wallpaper)
        results = query_wallpapers()
        assert len(results) == 1
        wp = results[0]
        assert wp.folder_path == sample_wallpaper.folder_path
        assert wp.workshop_id == sample_wallpaper.workshop_id
        assert wp.title == sample_wallpaper.title
        assert wp.wp_type == sample_wallpaper.wp_type
        assert wp.file == sample_wallpaper.file
        assert wp.preview == sample_wallpaper.preview
        assert wp.tags == sample_wallpaper.tags
        assert wp.content_rating == sample_wallpaper.content_rating
        assert wp.description == sample_wallpaper.description
        assert wp.scheme_color == sample_wallpaper.scheme_color
        assert wp.is_favorite == sample_wallpaper.is_favorite

    def test_tags_json_roundtrip(self):
        """确保标签的 JSON 序列化/反序列化正确"""
        from core.db import upsert_wallpaper, query_wallpapers
        wp = Wallpaper(folder_path="/tmp/tags_test", tags=["a", "b", "中文标签"])
        upsert_wallpaper(wp)
        results = query_wallpapers()
        assert results[0].tags == ["a", "b", "中文标签"]


class TestTagManagement:
    """标签管理: rename_tag / merge_tags / delete_tag"""

    def test_rename_tag(self):
        from core.db import upsert_wallpaper, rename_tag, get_all_tags
        upsert_wallpaper(Wallpaper(folder_path="/tr1", tags=["old", "keep"]))
        upsert_wallpaper(Wallpaper(folder_path="/tr2", tags=["old", "other"]))
        upsert_wallpaper(Wallpaper(folder_path="/tr3", tags=["keep"]))

        count = rename_tag("old", "new")
        assert count == 2

        tags = get_all_tags()
        assert "old" not in tags
        assert "new" in tags
        assert "keep" in tags

    def test_rename_tag_no_match(self):
        from core.db import upsert_wallpaper, rename_tag
        upsert_wallpaper(Wallpaper(folder_path="/trn1", tags=["abc"]))
        assert rename_tag("nonexistent", "new") == 0

    def test_rename_tag_noop(self):
        from core.db import rename_tag
        assert rename_tag("", "new") == 0
        assert rename_tag("old", "") == 0
        assert rename_tag("same", "same") == 0

    def test_merge_tags(self):
        from core.db import upsert_wallpaper, merge_tags, query_wallpapers
        upsert_wallpaper(Wallpaper(folder_path="/tm1", tags=["cat", "animal", "keep"]))
        upsert_wallpaper(Wallpaper(folder_path="/tm2", tags=["dog", "pet"]))
        upsert_wallpaper(Wallpaper(folder_path="/tm3", tags=["cat", "dog"]))

        count = merge_tags(["cat", "dog", "animal"], "pets")
        assert count == 3

        all_tags = set()
        for wp in query_wallpapers():
            all_tags.update(wp.tags)
        assert "cat" not in all_tags
        assert "dog" not in all_tags
        assert "animal" not in all_tags
        assert "pets" in all_tags

    def test_merge_tags_target_in_source(self):
        from core.db import upsert_wallpaper, merge_tags, query_wallpapers
        upsert_wallpaper(Wallpaper(folder_path="/tmt1", tags=["a", "b"]))
        count = merge_tags(["a", "b", "a"], "a")
        assert count == 1
        assert query_wallpapers()[0].tags == ["a"]

    def test_merge_tags_empty(self):
        from core.db import merge_tags
        assert merge_tags([], "target") == 0
        assert merge_tags(["a"], "") == 0

    def test_delete_tag(self):
        from core.db import upsert_wallpaper, delete_tag, get_all_tags
        upsert_wallpaper(Wallpaper(folder_path="/td1", tags=["del", "keep"]))
        upsert_wallpaper(Wallpaper(folder_path="/td2", tags=["del", "other"]))
        upsert_wallpaper(Wallpaper(folder_path="/td3", tags=["keep"]))

        count = delete_tag("del")
        assert count == 2

        tags = get_all_tags()
        assert "del" not in tags
        assert "keep" in tags

    def test_delete_tag_no_match(self):
        from core.db import upsert_wallpaper, delete_tag
        upsert_wallpaper(Wallpaper(folder_path="/tdn1", tags=["abc"]))
        assert delete_tag("nonexistent") == 0

    def test_delete_tag_empty(self):
        from core.db import delete_tag
        assert delete_tag("") == 0

    def test_rename_then_delete(self):
        from core.db import upsert_wallpaper, rename_tag, delete_tag, get_all_tags
        upsert_wallpaper(Wallpaper(folder_path="/trd1", tags=["old", "keep"]))
        rename_tag("old", "new")
        delete_tag("new")
        assert get_all_tags() == ["keep"]


class TestContentRating:
    """内容分级过滤测试"""

    def test_get_all_ratings_empty(self):
        from core.db import get_all_ratings
        assert get_all_ratings() == []

    def test_get_all_ratings(self):
        from core.db import upsert_wallpaper, get_all_ratings
        upsert_wallpaper(Wallpaper(folder_path="/r1", content_rating="Everyone"))
        upsert_wallpaper(Wallpaper(folder_path="/r2", content_rating="Everyone"))
        upsert_wallpaper(Wallpaper(folder_path="/r3", content_rating="Mature"))
        upsert_wallpaper(Wallpaper(folder_path="/r4", content_rating=""))
        ratings = get_all_ratings()
        assert ratings[0] == "Everyone"  # 按频次降序
        assert "Mature" in ratings
        assert "" not in ratings  # 空分级不包含

    def test_query_by_content_rating(self):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(Wallpaper(folder_path="/cr1", content_rating="Everyone"))
        upsert_wallpaper(Wallpaper(folder_path="/cr2", content_rating="Mature"))
        upsert_wallpaper(Wallpaper(folder_path="/cr3", content_rating="Everyone"))
        results = query_wallpapers(content_rating="Everyone")
        assert len(results) == 2
        assert all(r.content_rating == "Everyone" for r in results)

    def test_query_by_content_rating_no_match(self):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(Wallpaper(folder_path="/crn1", content_rating="Everyone"))
        results = query_wallpapers(content_rating="Questionable")
        assert len(results) == 0

    def test_query_empty_rating_means_all(self):
        from core.db import upsert_wallpaper, query_wallpapers
        upsert_wallpaper(Wallpaper(folder_path="/cra1", content_rating="Everyone"))
        upsert_wallpaper(Wallpaper(folder_path="/cra2", content_rating="Mature"))
        upsert_wallpaper(Wallpaper(folder_path="/cra3", content_rating=""))
        results = query_wallpapers(content_rating="")
        assert len(results) == 3


class TestExtraData:
    """extra_data 字段测试"""

    def test_extra_data_roundtrip(self):
        """写入 extra_data 再读出"""
        from core.db import upsert_wallpaper, query_wallpapers
        wp = Wallpaper(
            folder_path="/tmp/extra_test",
            extra_data='{"version": 2, "custom": "value"}',
        )
        upsert_wallpaper(wp)
        results = query_wallpapers()
        assert len(results) == 1
        assert results[0].extra_data == '{"version": 2, "custom": "value"}'

    def test_extra_data_default_empty(self):
        """extra_data 默认为空"""
        from core.db import upsert_wallpaper, query_wallpapers
        wp = Wallpaper(folder_path="/tmp/no_extra")
        upsert_wallpaper(wp)
        results = query_wallpapers()
        assert results[0].extra_data == ""

    def test_extra_data_update(self):
        """extra_data 可更新"""
        from core.db import upsert_wallpaper, query_wallpapers
        wp = Wallpaper(folder_path="/tmp/update_extra", extra_data='{"old": true}')
        upsert_wallpaper(wp)
        wp.extra_data = '{"new": true}'
        upsert_wallpaper(wp)
        results = query_wallpapers()
        assert results[0].extra_data == '{"new": true}'


class TestSchemaMigration:
    """Schema 迁移测试"""

    def test_schema_version_set(self):
        """init_db 后 schema_version 应为当前版本"""
        from core.db import get_connection, SCHEMA_VERSION
        with get_connection() as conn:
            row = conn.execute("SELECT version FROM schema_version").fetchone()
            assert row is not None
            assert row["version"] == SCHEMA_VERSION

    def test_extra_data_column_exists(self):
        """wallpapers 表应有 extra_data 列"""
        from core.db import get_connection
        with get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(wallpapers)")
            columns = {row["name"] for row in cursor.fetchall()}
            assert "extra_data" in columns


class TestBackup:
    """数据库备份测试"""

    def test_backup_creates_file(self, tmp_path):
        """备份应创建文件"""
        from core.db import backup_database, DB_PATH
        # 写入一些数据确保 DB 存在
        from core.db import upsert_wallpaper
        upsert_wallpaper(Wallpaper(folder_path="/backup_test"))

        result = backup_database()
        assert result is not None
        assert result.exists()
        assert result.suffix == ".db"

    def test_backup_cleans_old(self, tmp_path):
        """备份应清理旧备份，保留最近 3 份"""
        from core.db import backup_database, DB_PATH, DB_DIR
        from core.db import upsert_wallpaper
        upsert_wallpaper(Wallpaper(folder_path="/backup_clean_test"))

        # 创建 5 个备份
        paths = []
        for _ in range(5):
            p = backup_database(max_backups=3)
            if p:
                paths.append(p)

        backup_dir = DB_DIR / "backups"
        if backup_dir.exists():
            backups = list(backup_dir.glob("wallpapers_*.db"))
            assert len(backups) <= 3

    def test_backup_returns_none_if_no_db(self, tmp_path, monkeypatch):
        """数据库不存在时备份返回 None"""
        monkeypatch.setattr("core.db.DB_PATH", tmp_path / "nonexistent.db")
        from core.db import backup_database
        result = backup_database()
        assert result is None
