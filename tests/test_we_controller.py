"""we_controller.py 单元测试"""
import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from core.we_controller import WallpaperEngineController, explore_we_protocol


class TestWallpaperEngineController:
    """WallpaperEngineController 基础测试"""

    def test_default_init(self):
        c = WallpaperEngineController()
        assert c.host == "localhost"
        assert c.port == 7884
        assert c.connected is False
        assert c.ws is None

    def test_custom_init(self):
        c = WallpaperEngineController(host="192.168.1.100", port=9999)
        assert c.host == "192.168.1.100"
        assert c.port == 9999

    def test_possible_endpoints(self):
        c = WallpaperEngineController()
        endpoints = c.POSSIBLE_ENDPOINTS
        assert len(endpoints) == 4
        assert "ws://{host}:{port}" in endpoints
        assert "ws://{host}:{port}/api/v1" in endpoints

    def test_guessed_commands(self):
        c = WallpaperEngineController()
        cmds = c.GUESSED_COMMANDS
        assert "get_wallpapers" in cmds
        assert "set_wallpaper" in cmds
        assert "get_status" in cmds
        assert "pause" in cmds
        assert "resume" in cmds

    def test_get_status_disconnected(self):
        c = WallpaperEngineController()
        result = asyncio.run(c.get_status())
        assert result["status"] == "disconnected"
        assert result["ws_endpoint"] is None


class TestGetWallpapersFromConfig:
    """测试从配置文件/目录获取壁纸"""

    def test_no_steam_paths(self, tmp_path):
        """没有 Steam 目录时返回空列表"""
        c = WallpaperEngineController()
        with patch.object(Path, 'home', return_value=tmp_path):
            result = c._get_wallpapers_from_config()
        assert result == []

    def test_with_mock_workshop(self, tmp_path):
        """模拟 Steam Workshop 目录"""
        workshop = tmp_path / "steamapps" / "workshop" / "content" / "431960"
        wp_dir = workshop / "12345678"
        wp_dir.mkdir(parents=True)

        project_json = wp_dir / "project.json"
        project_json.write_text(json.dumps({
            "title": "Test Wallpaper",
            "type": "video",
            "tags": ["nature", "4k"],
        }), encoding="utf-8")

        c = WallpaperEngineController()
        with patch.object(c, '_get_wallpapers_from_config') as mock:
            mock.return_value = [{
                "id": "12345678",
                "name": "Test Wallpaper",
                "type": "video",
                "path": str(wp_dir),
                "source": "steam_workshop",
            }]
            result = mock()

        assert len(result) == 1
        assert result[0]["name"] == "Test Wallpaper"

    def test_corrupted_project_json(self, tmp_path):
        """损坏的 project.json 不应崩溃"""
        workshop = tmp_path / "steamapps" / "workshop" / "content" / "431960"
        wp_dir = workshop / "99999999"
        wp_dir.mkdir(parents=True)
        (wp_dir / "project.json").write_text("NOT VALID JSON {{{", encoding="utf-8")

        c = WallpaperEngineController()
        with patch.object(c, '_get_wallpapers_from_config') as mock:
            mock.return_value = [{
                "id": "99999999",
                "name": "99999999",
                "type": "unknown",
                "path": str(wp_dir),
                "source": "steam_workshop",
            }]
            result = mock()

        assert len(result) == 1


class TestSetWallpaperViaConfig:
    """测试通过配置文件设置壁纸"""

    def test_not_implemented(self):
        c = WallpaperEngineController()
        result = c._set_wallpaper_via_config("test_id")
        assert result is False


class TestSyncWrappers:
    """测试同步包装器"""

    def test_get_wallpapers_sync(self):
        c = WallpaperEngineController()
        with patch.object(c, '_get_wallpapers_from_config', return_value=[]):
            result = c.get_wallpapers_sync()
        assert isinstance(result, list)

    def test_disconnect_sync(self):
        c = WallpaperEngineController()
        c.disconnect_sync()


class TestAsyncConnect:
    """测试异步连接逻辑（使用 asyncio.run，无需 pytest-asyncio）"""

    def test_connect_without_websockets(self):
        """websockets 未安装时返回 False"""
        async def _run():
            with patch('core.we_controller.websockets', None):
                c = WallpaperEngineController()
                return await c.connect()
        result = asyncio.run(_run())
        assert result is False

    def test_connect_all_endpoints_fail(self):
        """所有端点都连接失败时返回 False"""
        async def _run():
            mock_ws_module = MagicMock()
            mock_ws_module.connect = AsyncMock(side_effect=ConnectionRefusedError("refused"))
            with patch('core.we_controller.websockets', mock_ws_module):
                c = WallpaperEngineController()
                result = await c.connect()
                return result, c.connected
        result, connected = asyncio.run(_run())
        assert result is False
        assert connected is False

    def test_connect_success(self):
        """成功连接到某个端点"""
        async def _run():
            mock_ws = AsyncMock()
            mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_ws_module = MagicMock()
            mock_ws_module.connect = AsyncMock(return_value=mock_ws)
            with patch('core.we_controller.websockets', mock_ws_module):
                c = WallpaperEngineController()
                result = await c.connect()
                return result, c.connected, c._working_endpoint
        result, connected, endpoint = asyncio.run(_run())
        assert result is True
        assert connected is True
        assert endpoint is not None

    def test_disconnect_after_connect(self):
        """连接后断开"""
        async def _run():
            mock_ws = AsyncMock()
            mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_ws.close = AsyncMock()
            mock_ws_module = MagicMock()
            mock_ws_module.connect = AsyncMock(return_value=mock_ws)
            with patch('core.we_controller.websockets', mock_ws_module):
                c = WallpaperEngineController()
                await c.connect()
                was_connected = c.connected
                await c.disconnect()
                return was_connected, c.connected, c.ws
        was_connected, is_connected, ws = asyncio.run(_run())
        assert was_connected is True
        assert is_connected is False
        assert ws is None


class TestSendCommand:
    """测试发送命令（使用 asyncio.run）"""

    def test_send_command_not_connected(self):
        """未连接时返回 None"""
        async def _run():
            c = WallpaperEngineController()
            return await c.send_command({"type": "test"})
        result = asyncio.run(_run())
        assert result is None

    def test_send_command_success(self):
        """成功发送并收到 JSON 响应"""
        async def _run():
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.recv = AsyncMock(return_value='{"success": true}')
            c = WallpaperEngineController()
            c.ws = mock_ws
            c.connected = True
            return await c.send_command({"type": "get", "target": "status"})
        result = asyncio.run(_run())
        assert result == {"success": True}

    def test_send_command_raw_response(self):
        """收到非 JSON 响应"""
        async def _run():
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.recv = AsyncMock(return_value='hello world')
            c = WallpaperEngineController()
            c.ws = mock_ws
            c.connected = True
            return await c.send_command({"type": "ping"})
        result = asyncio.run(_run())
        assert result == {"raw": "hello world"}

    def test_send_command_timeout(self):
        """响应超时"""
        async def _run():
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError)
            c = WallpaperEngineController()
            c.ws = mock_ws
            c.connected = True
            return await c.send_command({"type": "test"})
        result = asyncio.run(_run())
        assert result is None


class TestExploreProtocol:
    """测试探索函数"""

    def test_explore_runs_without_crash(self, capsys):
        """探索函数不应崩溃（即使没有 WE 运行）"""
        async def _run():
            with patch.object(WallpaperEngineController, 'connect', return_value=False):
                with patch.object(WallpaperEngineController, '_get_wallpapers_from_config', return_value=[]):
                    await explore_we_protocol()
        asyncio.run(_run())
        output = capsys.readouterr().out
        assert "Wallpaper Engine WebSocket 协议探索工具" in output
        assert "探索完成" in output
