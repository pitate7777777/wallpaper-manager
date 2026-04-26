"""
Wallpaper Engine WebSocket 控制器 (PoC Spike)
==============================================

调研发现 (Research Findings)
----------------------------

1. **官方 WebSocket 控制 API 不存在**
   经过大量搜索（包括官方文档 docs.wallpaperengine.io、GitHub、CSDN、知乎等），
   Wallpaper Engine **没有公开的 WebSocket API** 用于外部控制（切换壁纸、列出壁纸等）。
   官方文档仅覆盖：
   - Web Wallpaper API (JavaScript): wallpaperPropertyListener, wallpaperRegisterAudioListener
     等 —— 这些是给壁纸开发者用的，用于壁纸内部与 WE 运行时交互
   - Scene Scripting API (SceneScript): 类似 JavaScript，用于场景壁纸

2. **Android 配套 App 使用私有协议**
   Wallpaper Engine Android 版通过私有协议与 PC 端通信（传输壁纸），
   使用 4 位 PIN 码配对，协议未公开文档化。

3. **端口 7884 是社区猜测**
   在一些社区讨论中提到 WE 可能使用 WebSocket 端口 7884 进行内部通信，
   但没有官方确认。这可能是 Android companion app 使用的端口。

4. **替代控制方式**
   - **命令行参数**: WE 支持一些命令行参数（如 -control play/pause）
   - **配置文件**: 可以直接修改 WE 的配置文件来切换壁纸
   - **Windows API**: 通过 SystemParametersInfo 等 Windows API 设置壁纸
   - **Steam Workshop**: 可以通过 Steam 命令行下载壁纸

5. **PoC 策略**
   由于没有官方 WebSocket API，本 PoC 采用以下策略：
   a. 尝试连接 ws://localhost:7884（社区猜测的端口）
   b. 尝试连接 ws://localhost:7884/api/v1（可能的 API 路径）
   c. 探索可能的消息格式（JSON）
   d. 作为备用方案，提供通过配置文件控制壁纸的能力

参考资源:
- 官方文档: https://docs.wallpaperengine.io/en/web/overview.html
- Web Wallpaper API: wallpaperPropertyListener, wallpaperRegisterAudioListener
- Steam App ID: 431960
- Workshop 路径: steamapps/workshop/content/431960/
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

# PoC: 尝试导入 websockets，如果不存在则提供安装提示
try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    print("请安装 websockets 库: pip install websockets")
    websockets = None
    WebSocketClientProtocol = None

logger = logging.getLogger(__name__)


class WallpaperEngineController:
    """
    Wallpaper Engine WebSocket 控制器 (PoC)
    
    这是一个概念验证模块，用于探索与 Wallpaper Engine 的通信方式。
    
    已知信息:
    - Wallpaper Engine 没有公开的 WebSocket 控制 API
    - Android companion app 使用私有协议与 PC 通信
    - 社区猜测 WE 内部使用 WebSocket，端口可能是 7884
    
    此 PoC 尝试:
    1. 连接到可能的 WebSocket 端点
    2. 探索可用的命令和消息格式
    3. 提供备用控制方案（配置文件方式）
    """
    
    # 默认连接参数（基于社区猜测）
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 7884
    
    # 可能的 WebSocket 端点（需要实际测试验证）
    POSSIBLE_ENDPOINTS = [
        "ws://{host}:{port}",
        "ws://{host}:{port}/api/v1",
        "ws://{host}:{port}/ws",
        "ws://{host}:{port}/control",
    ]
    
    # 可能的消息格式（基于逆向工程猜测）
    # 注意: 这些都是猜测，需要实际测试验证
    GUESSED_COMMANDS = {
        "get_wallpapers": {
            "type": "get",
            "target": "wallpapers"
        },
        "set_wallpaper": {
            "type": "set",
            "target": "wallpaper",
            "data": {"id": None}
        },
        "get_status": {
            "type": "get",
            "target": "status"
        },
        "pause": {
            "type": "control",
            "action": "pause"
        },
        "resume": {
            "type": "control",
            "action": "resume"
        },
    }
    
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        we_install_path: Optional[str] = None
    ):
        """
        初始化控制器
        
        Args:
            host: Wallpaper Engine 主机地址
            port: WebSocket 端口（社区猜测 7884）
            we_install_path: Wallpaper Engine 安装路径（用于配置文件方式）
        """
        self.host = host
        self.port = port
        self.we_install_path = we_install_path
        self.ws: Optional[WebSocketClientProtocol] = None
        self.connected = False
        self._working_endpoint: Optional[str] = None
        
        # Wallpaper Engine 配置文件路径（Windows）
        # 通常在: %USERPROFILE%/Documents/my games/wallpaper_engine/
        self.config_dir = Path.home() / "Documents" / "my games" / "wallpaper_engine"
        if we_install_path:
            self.config_dir = Path(we_install_path)
    
    async def connect(self) -> bool:
        """
        尝试建立 WebSocket 连接
        
        会尝试多个可能的端点，直到找到一个可用的。
        
        Returns:
            bool: 是否成功连接
        """
        if websockets is None:
            logger.error("websockets 库未安装，请运行: pip install websockets")
            return False
        
        for endpoint_template in self.POSSIBLE_ENDPOINTS:
            endpoint = endpoint_template.format(host=self.host, port=self.port)
            try:
                logger.info(f"尝试连接: {endpoint}")
                self.ws = await websockets.connect(
                    endpoint,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5
                )
                self.connected = True
                self._working_endpoint = endpoint
                logger.info(f"✓ 成功连接到: {endpoint}")
                
                # 尝试读取欢迎消息
                try:
                    welcome = await asyncio.wait_for(self.ws.recv(), timeout=2.0)
                    logger.info(f"收到欢迎消息: {welcome}")
                except asyncio.TimeoutError:
                    logger.debug("无欢迎消息")
                
                return True
                
            except Exception as e:
                logger.debug(f"连接失败 {endpoint}: {e}")
                continue
        
        logger.warning("✗ 所有 WebSocket 端点均连接失败")
        logger.info("这可能是正常的 - Wallpaper Engine 没有公开的 WebSocket 控制 API")
        logger.info("建议使用备用方案（配置文件方式）")
        return False
    
    async def disconnect(self):
        """断开 WebSocket 连接"""
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
            self.connected = False
            self._working_endpoint = None
            logger.info("已断开连接")
    
    async def send_command(self, command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        发送命令并等待响应
        
        Args:
            command: 命令字典
            
        Returns:
            响应字典，如果失败则返回 None
        """
        if not self.connected or not self.ws:
            logger.error("未连接到 Wallpaper Engine")
            return None
        
        try:
            message = json.dumps(command)
            logger.info(f"发送: {message}")
            await self.ws.send(message)
            
            response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
            logger.info(f"收到: {response}")
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"raw": response}
                
        except asyncio.TimeoutError:
            logger.warning("命令响应超时")
            return None
        except Exception as e:
            logger.error(f"发送命令失败: {e}")
            return None
    
    async def get_wallpapers(self) -> List[Dict[str, Any]]:
        """
        获取当前壁纸列表
        
        注意: 这是基于猜测的命令格式，可能不工作。
        
        Returns:
            壁纸列表
        """
        if not self.connected:
            logger.warning("未连接，尝试连接...")
            if not await self.connect():
                return self._get_wallpapers_from_config()
        
        # 尝试猜测的命令
        result = await self.send_command(self.GUESSED_COMMANDS["get_wallpapers"])
        if result and "wallpapers" in result:
            return result["wallpapers"]
        
        logger.info("WebSocket 命令失败，尝试从配置文件获取...")
        return self._get_wallpapers_from_config()
    
    async def set_wallpaper(self, wallpaper_id: str) -> bool:
        """
        设置壁纸
        
        注意: 这是基于猜测的命令格式，可能不工作。
        
        Args:
            wallpaper_id: 壁纸 ID（可以是 Workshop ID 或本地路径）
            
        Returns:
            bool: 是否成功
        """
        if not self.connected:
            logger.warning("未连接，尝试连接...")
            if not await self.connect():
                return self._set_wallpaper_via_config(wallpaper_id)
        
        # 尝试猜测的命令
        command = dict(self.GUESSED_COMMANDS["set_wallpaper"])
        command["data"]["id"] = wallpaper_id
        result = await self.send_command(command)
        
        if result and result.get("success"):
            return True
        
        logger.info("WebSocket 命令失败，尝试通过配置文件设置...")
        return self._set_wallpaper_via_config(wallpaper_id)
    
    async def get_status(self) -> Optional[Dict[str, Any]]:
        """获取 Wallpaper Engine 状态"""
        if not self.connected:
            return {"status": "disconnected", "ws_endpoint": None}
        
        result = await self.send_command(self.GUESSED_COMMANDS["get_status"])
        return result or {"status": "connected", "endpoint": self._working_endpoint}
    
    # === 备用方案：通过配置文件控制 ===
    
    def _get_wallpapers_from_config(self) -> List[Dict[str, Any]]:
        """
        从 Wallpaper Engine 配置文件/目录获取壁纸列表
        
        Wallpaper Engine 的壁纸存储在:
        - Steam Workshop: steamapps/workshop/content/431960/
        - 本地项目: wallpaper_engine/projects/myprojects/
        
        Returns:
            壁纸列表
        """
        wallpapers = []
        
        # 尝试从 Steam Workshop 目录获取
        steam_paths = [
            Path.home() / "steamapps" / "workshop" / "content" / "431960",
            Path("C:/Program Files (x86)/Steam/steamapps/workshop/content/431960"),
            Path("D:/Steam/steamapps/workshop/content/431960"),
        ]
        
        for steam_path in steam_paths:
            if steam_path.exists():
                for item in steam_path.iterdir():
                    if item.is_dir():
                        # 检查是否有 project.json
                        project_json = item / "project.json"
                        if project_json.exists():
                            try:
                                with open(project_json, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                wallpapers.append({
                                    "id": item.name,
                                    "name": data.get("title", item.name),
                                    "type": data.get("type", "unknown"),
                                    "path": str(item),
                                    "source": "steam_workshop"
                                })
                            except Exception:
                                wallpapers.append({
                                    "id": item.name,
                                    "name": item.name,
                                    "type": "unknown",
                                    "path": str(item),
                                    "source": "steam_workshop"
                                })
        
        if wallpapers:
            logger.info(f"从 Steam Workshop 找到 {len(wallpapers)} 个壁纸")
        else:
            logger.info("未找到 Steam Workshop 壁纸目录")
        
        return wallpapers
    
    def _set_wallpaper_via_config(self, wallpaper_id: str) -> bool:
        """
        通过修改配置文件设置壁纸
        
        注意: 这种方式需要重启 Wallpaper Engine 才能生效。
        
        Args:
            wallpaper_id: 壁纸 ID
            
        Returns:
            bool: 是否成功
        """
        logger.warning("通过配置文件设置壁纸尚未实现")
        logger.info("建议手动在 Wallpaper Engine 中切换壁纸")
        logger.info(f"目标壁纸 ID: {wallpaper_id}")
        return False
    
    # === 同步包装器（方便测试）===
    
    def connect_sync(self) -> bool:
        """同步版本的 connect()"""
        return asyncio.run(self.connect())
    
    def get_wallpapers_sync(self) -> List[Dict[str, Any]]:
        """同步版本的 get_wallpapers()"""
        return asyncio.run(self.get_wallpapers())
    
    def set_wallpaper_sync(self, wallpaper_id: str) -> bool:
        """同步版本的 set_wallpaper()"""
        return asyncio.run(self.set_wallpaper(wallpaper_id))
    
    def disconnect_sync(self):
        """同步版本的 disconnect()"""
        if self.ws:
            asyncio.run(self.disconnect())


async def explore_we_protocol(host: str = "localhost", port: int = 7884):
    """
    探索 Wallpaper Engine 的 WebSocket 协议
    
    这个函数会尝试连接到多个可能的端点，
    并发送各种猜测的命令，记录响应。
    
    Args:
        host: 主机地址
        port: 端口
    """
    print("=" * 60)
    print("Wallpaper Engine WebSocket 协议探索工具")
    print("=" * 60)
    print(f"目标: {host}:{port}")
    print()
    
    controller = WallpaperEngineController(host=host, port=port)
    
    # 步骤 1: 尝试连接
    print("[步骤 1] 尝试连接到各种端点...")
    connected = await controller.connect()
    
    if connected:
        print(f"✓ 成功连接到: {controller._working_endpoint}")
        
        # 步骤 2: 尝试各种命令
        print("\n[步骤 2] 尝试发送命令...")
        
        test_commands = [
            ("获取壁纸列表", controller.GUESSED_COMMANDS["get_wallpapers"]),
            ("获取状态", controller.GUESSED_COMMANDS["get_status"]),
            ("暂停", controller.GUESSED_COMMANDS["pause"]),
        ]
        
        for name, cmd in test_commands:
            print(f"\n  尝试: {name}")
            result = await controller.send_command(cmd)
            if result:
                print(f"  响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"  无响应")
        
        await controller.disconnect()
    else:
        print("✗ 无法通过 WebSocket 连接")
        print()
        print("可能的原因:")
        print("  1. Wallpaper Engine 未运行")
        print("  2. WE 没有启用 WebSocket 控制接口")
        print("  3. 端口 7884 不正确")
        print("  4. WE 确实没有公开的 WebSocket API")
    
    # 步骤 3: 尝试配置文件方式
    print("\n[步骤 3] 尝试配置文件方式...")
    wallpapers = controller._get_wallpapers_from_config()
    if wallpapers:
        print(f"找到 {len(wallpapers)} 个壁纸:")
        for wp in wallpapers[:5]:  # 只显示前 5 个
            print(f"  - {wp['name']} (ID: {wp['id']}, 类型: {wp['type']})")
        if len(wallpapers) > 5:
            print(f"  ... 还有 {len(wallpapers) - 5} 个")
    else:
        print("未找到本地壁纸（可能需要安装 Steam 或 Wallpaper Engine）")
    
    print("\n" + "=" * 60)
    print("探索完成")
    print("=" * 60)


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    # 运行探索
    asyncio.run(explore_we_protocol())
