"""高级搜索功能测试"""
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


@pytest.fixture
def sample_wallpapers():
    """创建一组测试壁纸"""
    from core.db import upsert_wallpaper
    wallpapers = [
        Wallpaper(
            folder_path="/tmp/wp1",
            title="Sunset Beach",
            wp_type="video",
            tags=["nature", "beach", "sunset"],
        ),
        Wallpaper(
            folder_path="/tmp/wp2",
            title="Mountain Lake",
            wp_type="scene",
            tags=["nature", "mountain", "lake"],
        ),
        Wallpaper(
            folder_path="/tmp/wp3",
            title="Anime Girl",
            wp_type="video",
            tags=["anime", "character", "sunset"],
        ),
        Wallpaper(
            folder_path="/tmp/wp4",
            title="City Night",
            wp_type="scene",
            tags=["city", "night", "neon"],
        ),
        Wallpaper(
            folder_path="/tmp/wp5",
            title="Regex Test (Special) [Chars]",
            wp_type="web",
            tags=["test", "special"],
        ),
    ]
    for wp in wallpapers:
        upsert_wallpaper(wp)
    return wallpapers


class TestSearchMode:
    """搜索模式测试"""

    def test_simple_search_default(self, sample_wallpapers):
        """默认简单搜索（LIKE 匹配）"""
        from core.db import query_wallpapers
        results = query_wallpapers(search="Sunset")
        titles = [r.title for r in results]
        assert "Sunset Beach" in titles
        assert "Anime Girl" in titles  # tags 包含 sunset

    def test_simple_search_case_insensitive(self, sample_wallpapers):
        """简单搜索不区分大小写"""
        from core.db import query_wallpapers
        results = query_wallpapers(search="sunset")
        assert len(results) >= 2

    def test_simple_search_partial(self, sample_wallpapers):
        """简单搜索支持部分匹配"""
        from core.db import query_wallpapers
        results = query_wallpapers(search="Mount")
        assert len(results) == 1
        assert results[0].title == "Mountain Lake"

    def test_exact_search_title(self, sample_wallpapers):
        """精确搜索 - 标题完全匹配"""
        from core.db import query_wallpapers
        results = query_wallpapers(search="Sunset Beach", search_mode="exact")
        assert len(results) == 1
        assert results[0].title == "Sunset Beach"

    def test_exact_search_no_partial(self, sample_wallpapers):
        """精确搜索 - 部分匹配不命中标题；但会匹配 tags 中的精确元素"""
        from core.db import query_wallpapers
        # "Sune" 不是任何标题的精确值，也不是任何标签的精确元素
        results = query_wallpapers(search="Sune", search_mode="exact")
        assert len(results) == 0

    def test_exact_search_tags(self, sample_wallpapers):
        """精确搜索 - 匹配标签字段中的精确元素（JSON LIKE %\"term\"%）"""
        from core.db import query_wallpapers
        # "nature" 是 wp1 和 wp2 标签中的精确元素
        results = query_wallpapers(search="nature", search_mode="exact")
        # title 中没有精确等于 "nature" 的，但 tags JSON 含 "nature" 元素
        assert len(results) == 2
        titles = [r.title for r in results]
        assert "Sunset Beach" in titles
        assert "Mountain Lake" in titles

    def test_regex_search_basic(self, sample_wallpapers):
        """正则搜索 - 基本匹配"""
        from core.db import query_wallpapers
        results = query_wallpapers(search="Sunset|Mountain", search_mode="regex")
        titles = [r.title for r in results]
        assert "Sunset Beach" in titles
        assert "Mountain Lake" in titles

    def test_regex_search_pattern(self, sample_wallpapers):
        """正则搜索 - 模式匹配"""
        from core.db import query_wallpapers
        results = query_wallpapers(search="^City.*Night$", search_mode="regex")
        assert len(results) == 1
        assert results[0].title == "City Night"

    def test_regex_search_invalid(self, sample_wallpapers):
        """正则搜索 - 无效正则返回空结果"""
        from core.db import query_wallpapers
        results = query_wallpapers(search="[invalid", search_mode="regex")
        assert results == []

    def test_regex_search_special_chars(self, sample_wallpapers):
        """正则搜索 - 特殊字符标题"""
        from core.db import query_wallpapers
        results = query_wallpapers(search=r"Regex Test.*Special", search_mode="regex")
        assert len(results) == 1

    def test_regex_case_insensitive(self, sample_wallpapers):
        """正则搜索 - 默认不区分大小写"""
        from core.db import query_wallpapers
        results = query_wallpapers(search="sunset beach", search_mode="regex")
        assert len(results) >= 1


class TestTagsMode:
    """标签组合模式测试"""

    def test_tags_any_default(self, sample_wallpapers):
        """默认 any 模式 - 匹配任一标签"""
        from core.db import query_wallpapers
        results = query_wallpapers(tags=["beach", "mountain"], tags_mode="any")
        titles = [r.title for r in results]
        assert "Sunset Beach" in titles
        assert "Mountain Lake" in titles
        assert len(results) == 2

    def test_tags_all_mode(self, sample_wallpapers):
        """all 模式 - 必须匹配所有标签"""
        from core.db import query_wallpapers
        results = query_wallpapers(tags=["nature", "beach"], tags_mode="all")
        assert len(results) == 1
        assert results[0].title == "Sunset Beach"

    def test_tags_all_no_match(self, sample_wallpapers):
        """all 模式 - 无壁纸同时包含所有标签"""
        from core.db import query_wallpapers
        results = query_wallpapers(tags=["beach", "mountain"], tags_mode="all")
        assert len(results) == 0

    def test_tags_all_single(self, sample_wallpapers):
        """all 模式 - 单个标签"""
        from core.db import query_wallpapers
        results = query_wallpapers(tags=["nature"], tags_mode="all")
        assert len(results) == 2

    def test_tags_any_empty(self, sample_wallpapers):
        """any 模式 - 空标签列表"""
        from core.db import query_wallpapers
        results = query_wallpapers(tags=[], tags_mode="any")
        assert len(results) == 5


class TestExcludeTags:
    """排除标签测试"""

    def test_exclude_single(self, sample_wallpapers):
        """排除单个标签"""
        from core.db import query_wallpapers
        results = query_wallpapers(exclude_tags=["anime"])
        titles = [r.title for r in results]
        assert "Anime Girl" not in titles
        assert len(results) == 4

    def test_exclude_multiple(self, sample_wallpapers):
        """排除多个标签"""
        from core.db import query_wallpapers
        results = query_wallpapers(exclude_tags=["anime", "city"])
        titles = [r.title for r in results]
        assert "Anime Girl" not in titles
        assert "City Night" not in titles
        assert len(results) == 3

    def test_exclude_no_match(self, sample_wallpapers):
        """排除标签 - 没有匹配的排除"""
        from core.db import query_wallpapers
        results = query_wallpapers(exclude_tags=["nonexistent_tag"])
        assert len(results) == 5

    def test_exclude_empty_list(self, sample_wallpapers):
        """排除空列表 - 不影响结果"""
        from core.db import query_wallpapers
        results = query_wallpapers(exclude_tags=[])
        assert len(results) == 5

    def test_exclude_with_search(self, sample_wallpapers):
        """排除标签 + 搜索组合"""
        from core.db import query_wallpapers
        results = query_wallpapers(search="sunset", exclude_tags=["anime"])
        titles = [r.title for r in results]
        assert "Sunset Beach" in titles
        assert "Anime Girl" not in titles

    def test_exclude_with_type(self, sample_wallpapers):
        """排除标签 + 类型过滤"""
        from core.db import query_wallpapers
        results = query_wallpapers(wp_type="video", exclude_tags=["anime"])
        titles = [r.title for r in results]
        assert "Sunset Beach" in titles
        assert "Anime Girl" not in titles


class TestCombinedSearch:
    """组合搜索测试"""

    def test_search_and_tags(self, sample_wallpapers):
        """搜索 + 标签过滤"""
        from core.db import query_wallpapers
        results = query_wallpapers(search="Sunset", tags=["nature"])
        assert len(results) == 1
        assert results[0].title == "Sunset Beach"

    def test_search_and_type_and_exclude(self, sample_wallpapers):
        """搜索 + 类型 + 排除"""
        from core.db import query_wallpapers
        results = query_wallpapers(
            search="sunset",
            wp_type="video",
            exclude_tags=["anime"],
        )
        assert len(results) == 1
        assert results[0].title == "Sunset Beach"

    def test_all_tags_and_exclude(self, sample_wallpapers):
        """all 标签 + 排除"""
        from core.db import query_wallpapers
        results = query_wallpapers(
            tags=["nature", "sunset"],
            tags_mode="all",
            exclude_tags=["beach"],
        )
        # Anime Girl 有 nature 和 sunset 但没有 beach
        # 但 exclude_tags=["beach"] 排除的是包含 "beach" 标签的壁纸
        # Sunset Beach 有 beach 标签，会被排除
        # Anime Girl 没有 beach 标签，但也没有 nature 标签
        # 实际上 Anime Girl 有 nature 标签... 让我检查
        # sample_wallpapers[2] tags=["anime", "character", "sunset"]
        # 所以 Anime Girl 没有 nature 标签
        # 只有 Sunset Beach 和 Mountain Lake 有 nature
        # Sunset Beach 有 nature + sunset，但也有 beach → 被排除
        # Mountain Lake 有 nature 但没有 sunset → 不匹配 all
        assert len(results) == 0

    def test_regex_and_exclude(self, sample_wallpapers):
        """正则 + 排除"""
        from core.db import query_wallpapers
        results = query_wallpapers(
            search="Sunset|Mountain",
            search_mode="regex",
            exclude_tags=["beach"],
        )
        titles = [r.title for r in results]
        assert "Mountain Lake" in titles
        assert "Sunset Beach" not in titles

    def test_exact_and_favorites(self, sample_wallpapers):
        """精确搜索 + 收藏"""
        from core.db import upsert_wallpaper, set_favorite, query_wallpapers
        # 将 Sunset Beach 设为收藏
        from core.db import get_connection
        with get_connection() as conn:
            row = conn.execute("SELECT id FROM wallpapers WHERE folder_path = ?", ("/tmp/wp1",)).fetchone()
            set_favorite(row["id"], True)

        results = query_wallpapers(
            search="Sunset Beach",
            search_mode="exact",
            favorites_only=True,
        )
        assert len(results) == 1
        assert results[0].title == "Sunset Beach"
