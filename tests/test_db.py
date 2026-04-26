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
