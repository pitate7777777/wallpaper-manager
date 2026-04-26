"""core.scanner 单元测试 — 使用 tmp_path 创建假壁纸目录"""
import json
from pathlib import Path

import pytest

from core.scanner import parse_project_json


def _make_wallpaper_dir(tmp_path, name, project_data):
    """创建假壁纸目录并写入 project.json"""
    wp_dir = tmp_path / name
    wp_dir.mkdir(parents=True, exist_ok=True)
    (wp_dir / "project.json").write_text(
        json.dumps(project_data, ensure_ascii=False), encoding="utf-8"
    )
    return wp_dir


class TestParseProjectJson:
    """parse_project_json 正常解析测试"""

    def test_full_project(self, tmp_path):
        """完整字段的 project.json"""
        data = {
            "workshopid": "123456789",
            "title": "Beautiful Sunset",
            "type": "video",
            "file": "bg.mp4",
            "preview": "preview.jpg",
            "tags": ["nature", "sunset", "4k"],
            "contentrating": "Everyone",
            "description": "A beautiful sunset wallpaper",
            "general": {
                "properties": {
                    "schemecolor": {
                        "value": "0.25 0.50 0.75"
                    }
                }
            },
        }
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_full", data)
        wp = parse_project_json(wp_dir)

        assert wp is not None
        assert wp.folder_path == str(wp_dir)
        assert wp.workshop_id == "123456789"
        assert wp.title == "Beautiful Sunset"
        assert wp.wp_type == "video"
        assert wp.file == "bg.mp4"
        assert wp.preview == "preview.jpg"
        assert wp.tags == ["nature", "sunset", "4k"]
        assert wp.content_rating == "Everyone"
        assert wp.description == "A beautiful sunset wallpaper"
        assert wp.scheme_color == "0.25 0.50 0.75"

    def test_minimal_project(self, tmp_path):
        """最少字段的 project.json"""
        data = {"type": "scene"}
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_minimal", data)
        wp = parse_project_json(wp_dir)

        assert wp is not None
        assert wp.wp_type == "scene"
        assert wp.title == "wp_minimal"  # fallback to folder name
        assert wp.workshop_id == ""
        assert wp.file == ""
        assert wp.tags == []
        assert wp.scheme_color == ""

    def test_empty_json(self, tmp_path):
        """空 JSON 对象 {}"""
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_empty", {})
        wp = parse_project_json(wp_dir)

        assert wp is not None
        assert wp.title == "wp_empty"  # fallback
        assert wp.wp_type == ""
        assert wp.tags == []

    def test_no_project_json(self, tmp_path):
        """目录存在但没有 project.json"""
        wp_dir = tmp_path / "no_project"
        wp_dir.mkdir()
        result = parse_project_json(wp_dir)
        assert result is None

    def test_malformed_json(self, tmp_path):
        """畸形 JSON 文件"""
        wp_dir = tmp_path / "wp_bad_json"
        wp_dir.mkdir()
        (wp_dir / "project.json").write_text("{invalid json!!!", encoding="utf-8")
        result = parse_project_json(wp_dir)
        assert result is None

    def test_empty_file(self, tmp_path):
        """空 project.json 文件"""
        wp_dir = tmp_path / "wp_empty_file"
        wp_dir.mkdir()
        (wp_dir / "project.json").write_text("", encoding="utf-8")
        result = parse_project_json(wp_dir)
        assert result is None

    def test_empty_tags(self, tmp_path):
        """tags 为空列表"""
        data = {"title": "No Tags", "tags": []}
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_no_tags", data)
        wp = parse_project_json(wp_dir)
        assert wp is not None
        assert wp.tags == []

    def test_missing_tags_field(self, tmp_path):
        """没有 tags 字段"""
        data = {"title": "Missing Tags"}
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_missing_tags", data)
        wp = parse_project_json(wp_dir)
        assert wp is not None
        assert wp.tags == []

    def test_scheme_color_missing_general(self, tmp_path):
        """没有 general 字段"""
        data = {"title": "No General", "type": "video"}
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_no_general", data)
        wp = parse_project_json(wp_dir)
        assert wp is not None
        assert wp.scheme_color == ""

    def test_scheme_color_missing_schemecolor(self, tmp_path):
        """general 存在但没有 schemecolor"""
        data = {
            "title": "Partial General",
            "general": {"properties": {}},
        }
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_partial_gen", data)
        wp = parse_project_json(wp_dir)
        assert wp is not None
        assert wp.scheme_color == ""

    def test_scheme_color_none_value(self, tmp_path):
        """schemecolor.value 为 None"""
        data = {
            "title": "Null Color",
            "general": {"properties": {"schemecolor": {"value": None}}},
        }
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_null_color", data)
        wp = parse_project_json(wp_dir)
        assert wp is not None
        # None 会被赋值给 scheme_color
        assert wp.scheme_color is None or wp.scheme_color == ""

    def test_unicode_title_and_tags(self, tmp_path):
        """Unicode 标题和标签"""
        data = {
            "title": "壁纸测试 🎨",
            "tags": ["动漫", "风景", "4K"],
            "description": "这是一个测试壁纸",
        }
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_unicode", data)
        wp = parse_project_json(wp_dir)
        assert wp is not None
        assert wp.title == "壁纸测试 🎨"
        assert wp.tags == ["动漫", "风景", "4K"]
        assert wp.description == "这是一个测试壁纸"

    def test_workshopid_as_int(self, tmp_path):
        """workshopid 可能是整数"""
        data = {"workshopid": 123456789, "title": "Int ID"}
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_int_id", data)
        wp = parse_project_json(wp_dir)
        assert wp is not None
        assert wp.workshop_id == "123456789"

    def test_web_type(self, tmp_path):
        """web 类型壁纸"""
        data = {
            "type": "web",
            "file": "index.html",
            "title": "Clock Widget",
        }
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_web", data)
        wp = parse_project_json(wp_dir)
        assert wp is not None
        assert wp.wp_type == "web"
        assert wp.file == "index.html"

    def test_application_type(self, tmp_path):
        """application 类型壁纸"""
        data = {
            "type": "application",
            "file": "app.exe",
            "title": "Interactive App",
        }
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_app", data)
        wp = parse_project_json(wp_dir)
        assert wp is not None
        assert wp.wp_type == "application"

    def test_nested_scheme_color(self, tmp_path):
        """general.properties 结构完整但有多余字段"""
        data = {
            "title": "Extra Props",
            "general": {
                "properties": {
                    "schemecolor": {"value": "0.9 0.1 0.1"},
                    "other": "ignored",
                },
                "extra_field": True,
            },
        }
        wp_dir = _make_wallpaper_dir(tmp_path, "wp_extra", data)
        wp = parse_project_json(wp_dir)
        assert wp is not None
        assert wp.scheme_color == "0.9 0.1 0.1"
