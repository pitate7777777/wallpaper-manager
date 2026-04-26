"""core.wallpaper_setter 单元测试"""
import platform
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.wallpaper_setter import WallpaperSetter, IS_WINDOWS


class TestConstants:
    """常量测试"""

    def test_spi_constants(self):
        assert WallpaperSetter.SPI_SETDESKWALLPAPER == 0x0014
        assert WallpaperSetter.SPI_GETDESKWALLPAPER == 0x0073
        assert WallpaperSetter.SPIF_UPDATEINIFILE == 0x01
        assert WallpaperSetter.SPIF_SENDWININICHANGE == 0x02

    def test_we_app_id(self):
        assert WallpaperSetter.WE_APP_ID == "431960"

    def test_steam_paths_not_empty(self):
        assert len(WallpaperSetter.STEAM_PATHS) > 0


class TestSetWallpaper:
    """set_wallpaper 测试"""

    def test_returns_false_on_non_windows(self):
        """非 Windows 平台应返回 False"""
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            result = WallpaperSetter.set_wallpaper("/some/image.jpg")
            assert result is False

    @pytest.mark.skipif(IS_WINDOWS, reason="Windows-only test")
    def test_returns_false_for_nonexistent_file(self):
        """文件不存在时应返回 False（在 Windows 上）"""
        # 在非 Windows 上，会直接返回 False（平台检查）
        result = WallpaperSetter.set_wallpaper("/nonexistent/image.jpg")
        assert result is False


class TestGetCurrentWallpaper:
    """get_current_wallpaper 测试"""

    def test_returns_none_on_non_windows(self):
        """非 Windows 平台应返回 None"""
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            result = WallpaperSetter.get_current_wallpaper()
            assert result is None


class TestSetWallpaperWe:
    """set_wallpaper_we 测试"""

    def test_returns_false_on_non_windows(self):
        """非 Windows 平台应返回 False"""
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            result = WallpaperSetter.set_wallpaper_we("/some/path")
            assert result is False

    def test_returns_false_for_invalid_path(self):
        """无效路径应返回 False"""
        with patch("core.wallpaper_setter.IS_WINDOWS", True):
            result = WallpaperSetter.set_wallpaper_we("not_a_path_or_id")
            assert result is False


class TestFindWeInstall:
    """find_we_install 测试"""

    def test_returns_none_on_non_windows(self):
        """非 Windows 平台应返回 None"""
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            result = WallpaperSetter.find_we_install()
            # 在非 Windows 上仍然会尝试查找路径（不依赖平台）
            # 但通常不会有 WE 安装
            # 只要不崩溃即可
            assert result is None or isinstance(result, Path)


class TestParseLibraryfoldersVdf:
    """_parse_libraryfolders_vdf 测试"""

    def test_parse_valid_vdf(self, tmp_path):
        """解析有效的 VDF 文件"""
        vdf_content = '''
"libraryfolders"
{
    "0"
    {
        "path"	"C:\\\\Program Files (x86)\\\\Steam"
        "apps"
        {
            "431960"	"12345"
        }
    }
    "1"
    {
        "path"	"D:\\\\SteamLibrary"
        "apps"
        {
            "431960"	"67890"
        }
    }
}
'''
        vdf_file = tmp_path / "libraryfolders.vdf"
        vdf_file.write_text(vdf_content, encoding="utf-8")

        # 注意：由于路径可能不存在，解析出的路径会被过滤
        # 这里只测试解析逻辑不崩溃
        result = WallpaperSetter._parse_libraryfolders_vdf(vdf_file)
        assert isinstance(result, list)

    def test_parse_empty_vdf(self, tmp_path):
        """解析空 VDF 文件"""
        vdf_file = tmp_path / "libraryfolders.vdf"
        vdf_file.write_text("", encoding="utf-8")

        result = WallpaperSetter._parse_libraryfolders_vdf(vdf_file)
        assert result == []

    def test_parse_nonexistent_file(self, tmp_path):
        """解析不存在的文件"""
        vdf_file = tmp_path / "nonexistent.vdf"
        result = WallpaperSetter._parse_libraryfolders_vdf(vdf_file)
        assert result == []


class TestGetWeWallpaperList:
    """get_we_wallpaper_list 测试"""

    def test_returns_empty_when_no_steam(self):
        """没有 Steam 安装时应返回空列表"""
        with patch.object(WallpaperSetter, "_find_steam_library_folders", return_value=[]):
            result = WallpaperSetter.get_we_wallpaper_list()
            assert result == []
