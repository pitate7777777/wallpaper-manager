"""壁纸设置模块 - 通过 Windows API 或 Wallpaper Engine CLI 设置壁纸

支持:
1. 静态图片壁纸: 通过 SystemParametersInfoW (支持 JPG/PNG/BMP)
2. WE 动态壁纸: 通过官方 CLI (-control openWallpaper)
3. 获取当前壁纸路径
4. 自动检测 Wallpaper Engine 安装路径

参考: https://help.wallpaperengine.io/en/functionality/cli.html
"""

import json
import logging
import platform
import re
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 平台检测
IS_WINDOWS = platform.system() == "Windows"

# Windows-only imports
if IS_WINDOWS:
    import ctypes
    import winreg

# WE exe 路径缓存（首次查找后记住，避免重复扫描文件系统）
_we_exe_cache: Optional[str] = None


class WallpaperSetter:
    """壁纸设置器"""

    # Windows API 常量
    SPI_SETDESKWALLPAPER = 0x0014
    SPI_GETDESKWALLPAPER = 0x0073
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDWININICHANGE = 0x02

    # Wallpaper Engine Steam App ID
    WE_APP_ID = "431960"

    # 常见 Steam 安装路径
    STEAM_PATHS = [
        Path("C:/Program Files (x86)/Steam"),
        Path("C:/Program Files/Steam"),
        Path("D:/Steam"),
        Path("D:/SteamLibrary"),
        Path("E:/Steam"),
        Path("E:/SteamLibrary"),
    ]

    # 壁纸样式映射 (名称 → WallpaperStyle 注册表值)
    WALLPAPER_STYLES = {
        "center": "0",
        "tile": "0",
        "stretch": "2",
        "fit": "6",
        "fill": "10",
        "span": "22",
    }

    # ── 静态图片壁纸 (Windows API) ───────────────────────────

    @staticmethod
    def set_wallpaper(image_path: str, style: str = "stretch") -> bool:
        """通过 Windows API 设置桌面壁纸

        Args:
            image_path: 图片文件的绝对路径
            style: 壁纸样式 - "center" / "tile" / "stretch" / "fit" / "fill" / "span"

        Returns:
            是否设置成功
        """
        if not IS_WINDOWS:
            logger.warning("set_wallpaper 仅支持 Windows 平台")
            return False

        path = Path(image_path)
        if not path.exists():
            logger.error(f"图片文件不存在: {image_path}")
            return False

        valid_ext = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
        if path.suffix.lower() not in valid_ext:
            logger.warning(f"不支持的图片格式: {path.suffix}")
            return False

        style_val = WallpaperSetter.WALLPAPER_STYLES.get(style, "2")
        is_tile = "1" if style == "tile" else "0"

        try:
            abs_path = str(path.resolve())

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Control Panel\Desktop",
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, "Wallpaper", 0, winreg.REG_SZ, abs_path)
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, style_val)
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, is_tile)
            winreg.CloseKey(key)

            result = ctypes.windll.user32.SystemParametersInfoW(
                WallpaperSetter.SPI_SETDESKWALLPAPER,
                0,
                abs_path,
                WallpaperSetter.SPIF_UPDATEINIFILE | WallpaperSetter.SPIF_SENDWININICHANGE,
            )

            if result:
                logger.info(f"壁纸设置成功: {abs_path} (style={style})")
                return True
            else:
                error = ctypes.get_last_error()
                logger.error(f"SystemParametersInfoW 调用失败, error={error}")
                return False

        except Exception as e:
            logger.error(f"设置壁纸失败: {e}")
            return False

    @staticmethod
    def get_current_wallpaper() -> Optional[str]:
        """获取当前桌面壁纸路径"""
        if not IS_WINDOWS:
            logger.warning("get_current_wallpaper 仅支持 Windows 平台")
            return None

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Control Panel\Desktop",
                0,
                winreg.KEY_READ,
            )
            value, _ = winreg.QueryValueEx(key, "Wallpaper")
            winreg.CloseKey(key)

            if value and Path(value).exists():
                return value

            buf = ctypes.create_unicode_buffer(512)
            result = ctypes.windll.user32.SystemParametersInfoW(
                WallpaperSetter.SPI_GETDESKWALLPAPER, 512, buf, 0,
            )
            if result and buf.value:
                return buf.value

            return None

        except Exception as e:
            logger.error(f"获取当前壁纸失败: {e}")
            return None

    # ── WE 内部工具 ───────────────────────────────────────────

    @staticmethod
    def _find_we_exe(we_exe_path: Optional[str] = None) -> Optional[str]:
        """查找 WE 可执行文件路径（结果会缓存）

        Args:
            we_exe_path: 已知的路径，None 则自动检测

        Returns:
            可执行文件路径，未找到返回 None
        """
        global _we_exe_cache

        # 调用方指定了路径，直接验证
        if we_exe_path and Path(we_exe_path).exists():
            _we_exe_cache = we_exe_path
            return we_exe_path

        # 使用缓存
        if _we_exe_cache and Path(_we_exe_cache).exists():
            return _we_exe_cache

        we_path = WallpaperSetter.find_we_install()
        if not we_path:
            logger.error("未找到 Wallpaper Engine 安装路径")
            return None

        for name in ("wallpaper64.exe", "wallpaper32.exe"):
            candidate = we_path / name
            if candidate.exists():
                _we_exe_cache = str(candidate)
                logger.info(f"WE 可执行文件已缓存: {_we_exe_cache}")
                return _we_exe_cache

        logger.error(f"WE 目录中未找到可执行文件: {we_path}")
        return None

    # ── WE 动态壁纸 (官方 CLI) ────────────────────────────────

    @staticmethod
    def set_wallpaper_we(
        wallpaper_path: str,
        we_exe_path: Optional[str] = None,
        monitor: Optional[int] = None,
    ) -> bool:
        """通过 Wallpaper Engine CLI 设置动态壁纸

        官方 CLI 格式:
            wallpaper64.exe -control openWallpaper -file <path> [-monitor N]

        Args:
            wallpaper_path: 壁纸文件夹路径、project.json 路径或实际壁纸文件路径
            we_exe_path: WE 可执行文件路径（可选，自动检测）
            monitor: 显示器索引（0-based），None 则使用默认显示器

        Returns:
            是否设置成功
        """
        if not IS_WINDOWS:
            logger.warning("set_wallpaper_we 仅支持 Windows 平台")
            return False

        # 查找 WE 可执行文件
        if not we_exe_path:
            we_exe_path = WallpaperSetter._find_we_exe()
            if not we_exe_path:
                return False

        if not Path(we_exe_path).exists():
            logger.error(f"WE 可执行文件不存在: {we_exe_path}")
            return False

        # 解析目标文件路径
        target_file = WallpaperSetter._resolve_we_target(wallpaper_path)
        if not target_file:
            return False

        return WallpaperSetter._apply_we_cli(we_exe_path, target_file, monitor)

    @staticmethod
    def _resolve_we_target(wallpaper_path: str) -> Optional[str]:
        """解析壁纸路径，定位到 WE CLI 需要的 -file 参数值

        根据官方文档:
        - Scene 壁纸: 指向 project.json
        - Video 壁纸: 指向 .mp4 文件
        - Web 壁纸: 指向 index.html

        Args:
            wallpaper_path: 壁纸文件夹路径、project.json 路径或实际文件路径

        Returns:
            解析后的目标文件路径，失败返回 None
        """
        p = Path(wallpaper_path)

        # 情况 1: 直接指向 project.json 或具体文件
        if p.is_file():
            return str(p.resolve())

        # 情况 2: 指向壁纸文件夹
        if p.is_dir():
            # 读取 project.json 确定壁纸类型和文件
            project_json = p / "project.json"
            if not project_json.exists():
                logger.warning(f"壁纸文件夹中没有 project.json: {p}")
                return None

            try:
                with open(project_json, "r", encoding="utf-8") as f:
                    data = json.load(f)

                wp_type = data.get("type", "")
                wp_file = data.get("file", "")

                if wp_type == "scene":
                    # Scene 壁纸: 指向 project.json
                    return str(project_json.resolve())
                elif wp_type == "video" and wp_file:
                    # Video 壁纸: 指向视频文件
                    video_path = p / wp_file
                    if video_path.exists():
                        return str(video_path.resolve())
                    else:
                        logger.warning(f"视频文件不存在: {video_path}")
                        return str(project_json.resolve())
                elif wp_type == "web" and wp_file:
                    # Web 壁纸: 指向 index.html
                    web_path = p / wp_file
                    if web_path.exists():
                        return str(web_path.resolve())
                    else:
                        logger.warning(f"Web 文件不存在: {web_path}")
                        return str(project_json.resolve())
                else:
                    # 其他类型: 回退到 project.json
                    return str(project_json.resolve())

            except Exception as e:
                logger.warning(f"解析 project.json 失败: {e}")
                # 回退: 尝试直接用 project.json
                return str(project_json.resolve())

        # 情况 3: 可能是 Workshop ID（纯数字）
        if str(wallpaper_path).isdigit():
            # 在 Steam Workshop 目录中查找
            steam_libs = WallpaperSetter._find_steam_library_folders()
            for lib in steam_libs:
                wp_folder = (
                    lib / "steamapps" / "workshop" / "content"
                    / WallpaperSetter.WE_APP_ID / str(wallpaper_path)
                )
                if wp_folder.exists():
                    return WallpaperSetter._resolve_we_target(str(wp_folder))

            logger.error(f"未找到 Workshop 壁纸: {wallpaper_path}")
            return None

        logger.error(f"无效的壁纸路径: {wallpaper_path}")
        return None

    @staticmethod
    def _apply_we_cli(we_exe: str, target_file: str, monitor: Optional[int] = None) -> bool:
        """通过官方 CLI 设置壁纸（非阻塞，带重试）

        格式: wallpaper64.exe -control openWallpaper -file <path> [-monitor N]

        使用 Popen 异步启动进程后立即返回，不阻塞调用线程。
        Wallpaper Engine 接收到命令后会自行处理壁纸加载。

        参考: https://help.wallpaperengine.io/en/functionality/cli.html

        Args:
            we_exe: WE 可执行文件路径
            target_file: 壁纸目标文件路径（project.json / .mp4 / index.html）
            monitor: 显示器索引（0-based），None 则使用默认

        Returns:
            命令是否已成功发出
        """
        cmd = [we_exe, "-control", "openWallpaper", "-file", target_file]
        if monitor is not None:
            cmd.extend(["-monitor", str(monitor)])

        logger.info(f"执行 WE CLI: {' '.join(cmd)}")

        creation_flags = 0
        if IS_WINDOWS:
            creation_flags = subprocess.CREATE_NO_WINDOW

        try:
            # Popen 不阻塞 —— 命令发出后立即返回
            # Wallpaper Engine 会在后台处理壁纸加载
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            logger.info(f"WE 壁纸命令已发出: {target_file}")
            return True

        except FileNotFoundError:
            logger.error(f"WE 可执行文件不存在: {we_exe}")
            return False
        except Exception as e:
            logger.error(f"WE CLI 执行异常: {e}")
            return False

    # ── WE CLI 辅助命令 ───────────────────────────────────────

    @staticmethod
    def we_pause(we_exe_path: Optional[str] = None) -> bool:
        """暂停所有壁纸"""
        return WallpaperSetter._we_simple_command("pause", we_exe_path)

    @staticmethod
    def we_play(we_exe_path: Optional[str] = None) -> bool:
        """恢复播放"""
        return WallpaperSetter._we_simple_command("play", we_exe_path)

    @staticmethod
    def we_stop(we_exe_path: Optional[str] = None) -> bool:
        """停止所有壁纸"""
        return WallpaperSetter._we_simple_command("stop", we_exe_path)

    @staticmethod
    def we_mute(we_exe_path: Optional[str] = None) -> bool:
        """静音"""
        return WallpaperSetter._we_simple_command("mute", we_exe_path)

    @staticmethod
    def we_unmute(we_exe_path: Optional[str] = None) -> bool:
        """取消静音"""
        return WallpaperSetter._we_simple_command("unmute", we_exe_path)

    @staticmethod
    def we_next_wallpaper(we_exe_path: Optional[str] = None) -> bool:
        """切换到下一张壁纸"""
        return WallpaperSetter._we_simple_command("nextWallpaper", we_exe_path)

    @staticmethod
    def we_get_current_wallpaper(monitor: Optional[int] = None) -> Optional[str]:
        """获取当前 WE 壁纸路径

        Args:
            monitor: 显示器索引（0-based）

        Returns:
            当前壁纸路径字符串，失败返回 None
        """
        if not IS_WINDOWS:
            return None

        we_exe = WallpaperSetter._find_we_exe()
        if not we_exe:
            return None

        cmd = [we_exe, "-control", "getCurrentWallpaper"]
        if monitor is not None:
            cmd.extend(["-monitor", str(monitor)])

        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                output = result.stdout.decode("utf-8", errors="replace").strip()
                return output if output else None
        except Exception:
            pass
        return None

    @staticmethod
    def _we_simple_command(command: str, we_exe_path: Optional[str] = None) -> bool:
        """执行简单的 WE CLI 命令（非阻塞）

        Args:
            command: 命令名（pause/play/stop/mute/unmute/nextWallpaper）
            we_exe_path: WE 可执行文件路径

        Returns:
            是否成功发出命令
        """
        if not IS_WINDOWS:
            logger.warning(f"WE {command} 仅支持 Windows 平台")
            return False

        we_exe_path = WallpaperSetter._find_we_exe(we_exe_path)
        if not we_exe_path:
            return False

        cmd = [we_exe_path, "-control", command]
        logger.info(f"执行 WE CLI: {' '.join(cmd)}")

        try:
            # fire-and-forget: 命令发出后立即返回，不阻塞调用线程
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            logger.info(f"WE {command} 命令已发出")
            return True
        except FileNotFoundError:
            logger.error(f"WE 可执行文件不存在: {we_exe_path}")
            return False
        except Exception as e:
            logger.error(f"WE {command} 异常: {e}")
            return False

    # ── WE 安装路径检测 ───────────────────────────────────────

    @staticmethod
    def find_we_install() -> Optional[Path]:
        """自动检测 Wallpaper Engine 安装路径

        检查顺序:
        1. Steam 库路径（解析 libraryfolders.vdf）
        2. Windows 注册表
        3. 常见安装目录

        Returns:
            WE 安装目录路径，未找到返回 None
        """
        steam_libs = WallpaperSetter._find_steam_library_folders()
        for lib in steam_libs:
            we_path = lib / "steamapps" / "common" / "wallpaper_engine"
            if we_path.exists() and (we_path / "wallpaper64.exe").exists():
                logger.info(f"找到 WE 安装路径: {we_path}")
                return we_path

        if IS_WINDOWS:
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Valve\Steam",
                    0,
                    winreg.KEY_READ,
                )
                steam_path_str, _ = winreg.QueryValueEx(key, "SteamPath")
                winreg.CloseKey(key)

                if steam_path_str:
                    steam_path = Path(steam_path_str)
                    we_path = steam_path / "steamapps" / "common" / "wallpaper_engine"
                    if we_path.exists() and (we_path / "wallpaper64.exe").exists():
                        logger.info(f"从注册表找到 WE: {we_path}")
                        return we_path
            except Exception:
                pass

        common_we_paths = [
            Path("C:/Program Files (x86)/Steam/steamapps/common/wallpaper_engine"),
            Path("C:/Program Files/Steam/steamapps/common/wallpaper_engine"),
            Path("D:/SteamLibrary/steamapps/common/wallpaper_engine"),
            Path("D:/Steam/steamapps/common/wallpaper_engine"),
            Path("E:/SteamLibrary/steamapps/common/wallpaper_engine"),
            Path("E:/Steam/steamapps/common/wallpaper_engine"),
        ]
        for p in common_we_paths:
            if p.exists() and (p / "wallpaper64.exe").exists():
                logger.info(f"从常见路径找到 WE: {p}")
                return p

        logger.warning("未找到 Wallpaper Engine 安装路径")
        return None

    @staticmethod
    def _find_steam_library_folders() -> list[Path]:
        """查找所有 Steam 库文件夹"""
        libraries = []
        vdf_parsed = False

        for steam_path in WallpaperSetter.STEAM_PATHS:
            if steam_path.exists():
                if steam_path not in libraries:
                    libraries.append(steam_path)
                if not vdf_parsed:
                    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
                    if vdf_path.exists():
                        try:
                            libraries.extend(
                                WallpaperSetter._parse_libraryfolders_vdf(vdf_path)
                            )
                        except Exception as e:
                            logger.debug(f"解析 libraryfolders.vdf 失败: {e}")
                        vdf_parsed = True

        seen = set()
        unique = []
        for lib in libraries:
            resolved = str(lib.resolve()).lower()
            if resolved not in seen:
                seen.add(resolved)
                unique.append(lib)

        return unique

    @staticmethod
    def _parse_libraryfolders_vdf(vdf_path: Path) -> list[Path]:
        """解析 Steam 的 libraryfolders.vdf 文件"""
        libraries = []
        try:
            with open(vdf_path, "r", encoding="utf-8") as f:
                content = f.read()

            paths = re.findall(r'"path"\s+"([^"]+)"', content)
            for p in paths:
                clean_path = p.replace("\\\\", "\\")
                lib_path = Path(clean_path)
                if lib_path.exists():
                    libraries.append(lib_path)
        except Exception as e:
            logger.debug(f"解析 VDF 失败: {e}")

        return libraries
