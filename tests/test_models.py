"""core.models 单元测试"""
import os
from pathlib import Path

import pytest

from core.models import Wallpaper


class TestPreviewPath:
    """preview_path 属性测试"""

    def test_with_preview(self):
        wp = Wallpaper(folder_path="/home/user/wallpapers/wp1", preview="preview.jpg")
        assert wp.preview_path == str(Path("/home/user/wallpapers/wp1") / "preview.jpg")

    def test_empty_preview(self):
        wp = Wallpaper(folder_path="/home/user/wallpapers/wp1", preview="")
        assert wp.preview_path == ""

    def test_nested_preview(self):
        wp = Wallpaper(folder_path="/data/wps", preview="subdir/preview.png")
        assert wp.preview_path == str(Path("/data/wps") / "subdir/preview.png")

    def test_default_preview(self):
        wp = Wallpaper()
        assert wp.preview_path == ""


class TestWallpaperFilePath:
    """wallpaper_file_path 属性测试"""

    def test_with_file(self):
        wp = Wallpaper(folder_path="/home/user/wallpapers/wp1", file="video.mp4")
        assert wp.wallpaper_file_path == str(Path("/home/user/wallpapers/wp1") / "video.mp4")

    def test_empty_file(self):
        wp = Wallpaper(folder_path="/home/user/wallpapers/wp1", file="")
        assert wp.wallpaper_file_path == ""

    def test_default_file(self):
        wp = Wallpaper()
        assert wp.wallpaper_file_path == ""

    def test_scene_file(self):
        wp = Wallpaper(folder_path="/data/wps", file="index.html")
        assert wp.wallpaper_file_path == str(Path("/data/wps") / "index.html")


class TestTagsDisplay:
    """tags_display 属性测试"""

    def test_multiple_tags(self):
        wp = Wallpaper(tags=["anime", "nature", "4k"])
        assert wp.tags_display == "anime, nature, 4k"

    def test_single_tag(self):
        wp = Wallpaper(tags=["minimal"])
        assert wp.tags_display == "minimal"

    def test_empty_tags(self):
        wp = Wallpaper(tags=[])
        assert wp.tags_display == ""

    def test_default_tags(self):
        wp = Wallpaper()
        assert wp.tags_display == ""


class TestTypeEmoji:
    """type_emoji 属性测试"""

    def test_video(self):
        assert Wallpaper(wp_type="video").type_emoji == "🎬"

    def test_scene(self):
        assert Wallpaper(wp_type="scene").type_emoji == "🖼️"

    def test_web(self):
        assert Wallpaper(wp_type="web").type_emoji == "🌐"

    def test_application(self):
        assert Wallpaper(wp_type="application").type_emoji == "📄"

    def test_unknown_type(self):
        assert Wallpaper(wp_type="other").type_emoji == "📄"

    def test_empty_type(self):
        assert Wallpaper(wp_type="").type_emoji == "📄"


class TestSchemeColorHex:
    """scheme_color_hex 属性测试"""

    def test_normal_color(self):
        wp = Wallpaper(scheme_color="0.51373 0.54510 0.70588")
        result = wp.scheme_color_hex
        assert result.startswith("#")
        assert len(result) == 7
        # int(0.51373*255)=131→0x83, int(0.54510*255)=139→0x8b, int(0.70588*255)=179→0xb3
        assert result == "#838bb3"

    def test_black(self):
        wp = Wallpaper(scheme_color="0 0 0")
        assert wp.scheme_color_hex == "#000000"

    def test_white(self):
        wp = Wallpaper(scheme_color="1 1 1")
        assert wp.scheme_color_hex == "#ffffff"

    def test_empty(self):
        wp = Wallpaper(scheme_color="")
        assert wp.scheme_color_hex == ""

    def test_malformed_color(self):
        wp = Wallpaper(scheme_color="not-a-color")
        assert wp.scheme_color_hex == ""

    def test_partial_values(self):
        wp = Wallpaper(scheme_color="0.5 0.3")
        assert wp.scheme_color_hex == ""

    def test_extra_values(self):
        # 只取前三个
        wp = Wallpaper(scheme_color="0.5 0.5 0.5 0.9")
        # int(0.5*255)=127→0x7f (Python int() truncates)
        assert wp.scheme_color_hex == "#7f7f7f"


class TestWallpaperDefaults:
    """默认值测试"""

    def test_all_defaults(self):
        wp = Wallpaper()
        assert wp.id is None
        assert wp.folder_path == ""
        assert wp.workshop_id == ""
        assert wp.title == ""
        assert wp.wp_type == ""
        assert wp.file == ""
        assert wp.preview == ""
        assert wp.tags == []
        assert wp.content_rating == ""
        assert wp.description == ""
        assert wp.is_favorite is False
        assert wp.scheme_color == ""
        assert wp.extra_data == ""

    def test_partial_init(self):
        wp = Wallpaper(title="My Wallpaper", wp_type="video", is_favorite=True)
        assert wp.title == "My Wallpaper"
        assert wp.wp_type == "video"
        assert wp.is_favorite is True
        assert wp.folder_path == ""
