"""ui.theme 单元测试"""
import pytest

from ui.theme import (
    DARK_THEME, LIGHT_THEME, THEMES, COLORS,
    get_theme_names, get_current_theme_name, set_theme, register_theme,
    generate_stylesheet,
)


class TestThemeConstants:
    """主题常量测试"""

    def test_dark_theme_keys(self):
        """暗色主题应包含所有必要 key"""
        required = {"bg_main", "bg_panel", "bg_input", "text_primary", "border", "btn_bg"}
        assert required.issubset(DARK_THEME.keys())

    def test_light_theme_keys(self):
        """亮色主题应包含与暗色主题相同的 key"""
        assert set(LIGHT_THEME.keys()) == set(DARK_THEME.keys())

    def test_themes_registry(self):
        """主题注册表应包含 dark 和 light"""
        assert "dark" in THEMES
        assert "light" in THEMES

    def test_colors_is_dark_by_default(self):
        """COLORS 默认应等于 DARK_THEME"""
        assert COLORS == DARK_THEME


class TestThemeSwitching:
    """主题切换测试"""

    def setup_method(self):
        """每个测试前重置为暗色主题"""
        set_theme("dark")

    def test_set_theme_light(self):
        set_theme("light")
        assert get_current_theme_name() == "light"
        assert COLORS["bg_main"] == LIGHT_THEME["bg_main"]

    def test_set_theme_dark(self):
        set_theme("light")
        set_theme("dark")
        assert get_current_theme_name() == "dark"
        assert COLORS["bg_main"] == DARK_THEME["bg_main"]

    def test_set_theme_invalid(self):
        with pytest.raises(KeyError):
            set_theme("nonexistent")

    def test_get_theme_names(self):
        names = get_theme_names()
        assert "dark" in names
        assert "light" in names


class TestRegisterTheme:
    """自定义主题注册测试"""

    def setup_method(self):
        """清理可能注册的测试主题"""
        THEMES.pop("custom", None)

    def teardown_method(self):
        THEMES.pop("custom", None)

    def test_register_custom_theme(self):
        custom = dict(DARK_THEME)
        custom["bg_main"] = "#ff0000"
        register_theme("custom", custom)
        assert "custom" in THEMES
        assert THEMES["custom"]["bg_main"] == "#ff0000"

    def test_use_custom_theme(self):
        custom = dict(DARK_THEME)
        custom["bg_main"] = "#00ff00"
        register_theme("custom", custom)
        set_theme("custom")
        assert get_current_theme_name() == "custom"
        assert COLORS["bg_main"] == "#00ff00"


class TestGenerateStylesheet:
    """样式表生成测试"""

    def test_default_stylesheet(self):
        """默认样式表应包含基本选择器"""
        css = generate_stylesheet()
        assert "QMainWindow" in css
        assert "QPushButton" in css
        assert "QLineEdit" in css

    def test_custom_colors_stylesheet(self):
        """传入自定义颜色应生效"""
        custom = dict(DARK_THEME)
        custom["bg_main"] = "#123456"
        css = generate_stylesheet(colors=custom)
        assert "#123456" in css

    def test_stylesheet_uses_provided_colors(self):
        """样式表应使用传入的颜色而非全局 COLORS"""
        custom = dict(DARK_THEME)
        custom["bg_main"] = "#aabbcc"
        css = generate_stylesheet(colors=custom)
        assert "#aabbcc" in css
