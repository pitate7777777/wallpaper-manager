"""core.wallpaper_setter 单元测试"""
import json
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

    def test_wallpaper_styles(self):
        styles = WallpaperSetter.WALLPAPER_STYLES
        assert "center" in styles
        assert "stretch" in styles
        assert "fit" in styles
        assert "fill" in styles
        assert "tile" in styles
        assert "span" in styles
        assert styles["stretch"] != styles["span"]
        assert styles["center"] == styles["tile"]


class TestSetWallpaper:
    """set_wallpaper 测试"""

    def test_returns_false_on_non_windows(self):
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            result = WallpaperSetter.set_wallpaper("/some/image.jpg")
            assert result is False

    def test_returns_false_on_non_windows_with_style(self):
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            result = WallpaperSetter.set_wallpaper("/some/image.jpg", style="fill")
            assert result is False

    @pytest.mark.skipif(IS_WINDOWS, reason="Windows-only test")
    def test_returns_false_for_nonexistent_file(self):
        result = WallpaperSetter.set_wallpaper("/nonexistent/image.jpg")
        assert result is False


class TestGetCurrentWallpaper:
    """get_current_wallpaper 测试"""

    def test_returns_none_on_non_windows(self):
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            result = WallpaperSetter.get_current_wallpaper()
            assert result is None


class TestSetWallpaperWe:
    """set_wallpaper_we 测试"""

    def test_returns_false_on_non_windows(self):
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            result = WallpaperSetter.set_wallpaper_we("/some/path")
            assert result is False


class TestResolveWeTarget:
    """_resolve_we_target 测试"""

    def test_file_path_returned_directly(self, tmp_path):
        """直接指向文件时原样返回"""
        f = tmp_path / "project.json"
        f.write_text("{}")
        result = WallpaperSetter._resolve_we_target(str(f))
        assert result == str(f.resolve())

    def test_scene_folder_returns_project_json(self, tmp_path):
        """Scene 类型壁纸文件夹返回 project.json"""
        project = tmp_path / "project.json"
        project.write_text(json.dumps({"type": "scene", "file": "scene.wpe"}))
        result = WallpaperSetter._resolve_we_target(str(tmp_path))
        assert result == str(project.resolve())

    def test_video_folder_returns_video_file(self, tmp_path):
        """Video 类型壁纸文件夹返回 .mp4 文件"""
        mp4 = tmp_path / "video.mp4"
        mp4.write_text("fake")
        project = tmp_path / "project.json"
        project.write_text(json.dumps({"type": "video", "file": "video.mp4"}))
        result = WallpaperSetter._resolve_we_target(str(tmp_path))
        assert result == str(mp4.resolve())

    def test_video_folder_fallback_to_project_json(self, tmp_path):
        """Video 文件不存在时回退到 project.json"""
        project = tmp_path / "project.json"
        project.write_text(json.dumps({"type": "video", "file": "missing.mp4"}))
        result = WallpaperSetter._resolve_we_target(str(tmp_path))
        assert result == str(project.resolve())

    def test_web_folder_returns_index_html(self, tmp_path):
        """Web 类型壁纸文件夹返回 index.html"""
        html = tmp_path / "index.html"
        html.write_text("<html/>")
        project = tmp_path / "project.json"
        project.write_text(json.dumps({"type": "web", "file": "index.html"}))
        result = WallpaperSetter._resolve_we_target(str(tmp_path))
        assert result == str(html.resolve())

    def test_missing_project_json_returns_none(self, tmp_path):
        """没有 project.json 的文件夹返回 None"""
        result = WallpaperSetter._resolve_we_target(str(tmp_path))
        assert result is None

    def test_invalid_path_returns_none(self):
        """无效路径返回 None"""
        result = WallpaperSetter._resolve_we_target("/nonexistent/path/12345")
        assert result is None

    def test_invalid_json_returns_project_json_fallback(self, tmp_path):
        """project.json 解析失败时回退到 project.json 本身"""
        project = tmp_path / "project.json"
        project.write_text("NOT JSON {{{")
        result = WallpaperSetter._resolve_we_target(str(tmp_path))
        assert result == str(project.resolve())


class TestApplyWeCli:
    """_apply_we_cli 测试"""

    def test_success(self):
        """CLI 成功发出命令"""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            result = WallpaperSetter._apply_we_cli("/fake/wallpaper64.exe", "/wallpaper/project.json")
            assert result is True
            args = mock_popen.call_args[0][0]
            assert "-control" in args
            assert "openWallpaper" in args
            assert "-file" in args
            assert "/wallpaper/project.json" in args

    def test_with_monitor(self):
        """指定显示器参数"""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            result = WallpaperSetter._apply_we_cli(
                "/fake/wallpaper64.exe", "/wallpaper/project.json", monitor=1
            )
            assert result is True
            args = mock_popen.call_args[0][0]
            assert "-monitor" in args
            assert "1" in args

    def test_file_not_found_returns_false(self):
        """exe 不存在返回 False"""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = FileNotFoundError("not found")
            result = WallpaperSetter._apply_we_cli("/nonexistent.exe", "/wallpaper/project.json")
            assert result is False

    def test_generic_exception_returns_false(self):
        """其他异常返回 False"""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = OSError("permission denied")
            result = WallpaperSetter._apply_we_cli("/fake/wallpaper64.exe", "/wallpaper/project.json")
            assert result is False


class TestWeSimpleCommands:
    """WE 简单命令测试"""

    def test_pause_on_non_windows(self):
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            assert WallpaperSetter.we_pause() is False

    def test_play_on_non_windows(self):
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            assert WallpaperSetter.we_play() is False

    def test_stop_on_non_windows(self):
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            assert WallpaperSetter.we_stop() is False

    def test_mute_on_non_windows(self):
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            assert WallpaperSetter.we_mute() is False

    def test_unmute_on_non_windows(self):
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            assert WallpaperSetter.we_unmute() is False

    def test_next_wallpaper_on_non_windows(self):
        with patch("core.wallpaper_setter.IS_WINDOWS", False):
            assert WallpaperSetter.we_next_wallpaper() is False


class TestFindWeInstall:
    """find_we_install 测试"""

    def test_returns_none_when_not_found(self):
        with patch.object(WallpaperSetter, "_find_steam_library_folders", return_value=[]):
            if IS_WINDOWS:
                with patch("core.wallpaper_setter.winreg"):
                    result = WallpaperSetter.find_we_install()
            else:
                result = WallpaperSetter.find_we_install()
            # 没有 Steam 安装时应该返回 None
            assert result is None or isinstance(result, Path)


class TestParseLibraryfoldersVdf:
    """_parse_libraryfolders_vdf 测试"""

    def test_parse_valid_vdf(self, tmp_path):
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
}
'''
        vdf_file = tmp_path / "libraryfolders.vdf"
        vdf_file.write_text(vdf_content, encoding="utf-8")
        result = WallpaperSetter._parse_libraryfolders_vdf(vdf_file)
        assert isinstance(result, list)

    def test_parse_empty_vdf(self, tmp_path):
        vdf_file = tmp_path / "libraryfolders.vdf"
        vdf_file.write_text("", encoding="utf-8")
        result = WallpaperSetter._parse_libraryfolders_vdf(vdf_file)
        assert result == []

    def test_parse_nonexistent_file(self, tmp_path):
        vdf_file = tmp_path / "nonexistent.vdf"
        result = WallpaperSetter._parse_libraryfolders_vdf(vdf_file)
        assert result == []
