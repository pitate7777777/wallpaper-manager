"""壁纸设置模块 - 通过 Windows API 或 WE 配置设置壁纸

支持:
1. 静态图片壁纸: 通过 SystemParametersInfoW (支持 JPG/PNG/BMP)
2. WE 动态壁纸: 通过命令行或配置文件
3. 获取当前壁纸路径
4. 自动检测 Wallpaper Engine 安装路径
"""

import json
import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 平台检测
IS_WINDOWS = platform.system() == "Windows"

# Windows-only imports
if IS_WINDOWS:
    import ctypes
    import ctypes.wintypes
    import winreg


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

    @staticmethod
    def set_wallpaper(image_path: str) -> bool:
        """通过 Windows API 设置桌面壁纸

        支持 JPG、PNG、BMP 等格式。
        通过注册表设置壁纸路径，再调用 SystemParametersInfoW 生效。

        Args:
            image_path: 图片文件的绝对路径

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

        # 检查文件扩展名
        valid_ext = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
        if path.suffix.lower() not in valid_ext:
            logger.warning(f"不支持的图片格式: {path.suffix}")
            return False

        try:
            abs_path = str(path.resolve())

            # 通过注册表设置壁纸路径（支持 JPG/PNG 等非 BMP 格式）
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Control Panel\Desktop",
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, "Wallpaper", 0, winreg.REG_SZ, abs_path)
            # 设置壁纸样式：2 = 拉伸, 0 = 居中, 6 = 适应, 10 = 填充
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "2")
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
            winreg.CloseKey(key)

            # 调用 SystemParametersInfoW 使设置生效
            result = ctypes.windll.user32.SystemParametersInfoW(
                WallpaperSetter.SPI_SETDESKWALLPAPER,
                0,
                abs_path,
                WallpaperSetter.SPIF_UPDATEINIFILE | WallpaperSetter.SPIF_SENDWININICHANGE,
            )

            if result:
                logger.info(f"壁纸设置成功: {abs_path}")
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
        """获取当前桌面壁纸路径

        Returns:
            当前壁纸的绝对路径，失败返回 None
        """
        if not IS_WINDOWS:
            logger.warning("get_current_wallpaper 仅支持 Windows 平台")
            return None

        try:
            # 方式 1: 通过注册表读取
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Control Panel\Desktop",
                0,
                winreg.KEY_READ,
            )
            value, _ = winreg.QueryValueEx(key, "Wallpaper")
            winreg.CloseKey(key)

            if value and Path(value).exists():
                logger.debug(f"当前壁纸: {value}")
                return value

            # 方式 2: 通过 SystemParametersInfoW 读取
            buf = ctypes.create_unicode_buffer(512)
            result = ctypes.windll.user32.SystemParametersInfoW(
                WallpaperSetter.SPI_GETDESKWALLPAPER,
                512,
                buf,
                0,
            )
            if result and buf.value:
                logger.debug(f"当前壁纸 (API): {buf.value}")
                return buf.value

            return None

        except Exception as e:
            logger.error(f"获取当前壁纸失败: {e}")
            return None

    @staticmethod
    def set_wallpaper_we(
        wallpaper_path: str, we_exe_path: Optional[str] = None
    ) -> bool:
        """通过 Wallpaper Engine 设置动态壁纸

        尝试方式:
        1. 命令行参数 (-control openWallpaper)
        2. 修改配置文件

        Args:
            wallpaper_path: 壁纸文件夹路径或 workshop ID
            we_exe_path: WE 可执行文件路径（可选，自动检测）

        Returns:
            是否设置成功
        """
        if not IS_WINDOWS:
            logger.warning("set_wallpaper_we 仅支持 Windows 平台")
            return False

        # 查找 WE 可执行文件
        if not we_exe_path:
            we_path = WallpaperSetter.find_we_install()
            if not we_path:
                logger.error("未找到 Wallpaper Engine 安装路径")
                return False
            we_exe_path = str(we_path / "wallpaper64.exe")
            if not Path(we_exe_path).exists():
                we_exe_path = str(we_path / "wallpaper32.exe")

        if not Path(we_exe_path).exists():
            logger.error(f"WE 可执行文件不存在: {we_exe_path}")
            return False

        # 判断 wallpaper_path 是文件夹还是 workshop ID
        wp_path = Path(wallpaper_path)
        if wp_path.exists() and wp_path.is_dir():
            # 本地壁纸文件夹
            project_json = wp_path / "project.json"
            if project_json.exists():
                return WallpaperSetter._apply_we_local(we_exe_path, str(wp_path))
            else:
                logger.warning(f"壁纸文件夹中没有 project.json: {wp_path}")
                return False
        elif wallpaper_path.isdigit():
            # Workshop ID
            return WallpaperSetter._apply_we_workshop(we_exe_path, wallpaper_path)
        else:
            logger.error(f"无效的壁纸路径或 ID: {wallpaper_path}")
            return False

    @staticmethod
    def _apply_we_local(we_exe: str, folder_path: str) -> bool:
        """通过 WE 应用本地壁纸

        Wallpaper Engine 支持的命令行格式:
        wallpaper64.exe -control openWallpaper -path <folder_path>

        注意: WE 的命令行 API 未正式文档化，以下命令基于社区逆向。
        如果命令行方式失败，回退到配置文件方式。
        """
        try:
            # 方式 1: 命令行方式
            cmd = [we_exe, "-control", "openWallpaper", "-path", folder_path]
            logger.info(f"尝试命令行方式: {' '.join(cmd)}")
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            result = subprocess.run(
                cmd, capture_output=True, timeout=10, creationflags=creation_flags
            )
            if result.returncode == 0:
                logger.info(f"WE 命令行方式成功: {folder_path}")
                return True
            else:
                logger.warning(
                    f"WE 命令行方式失败 (code={result.returncode}): "
                    f"{result.stderr.decode('utf-8', errors='replace')}"
                )

            # 方式 2: 配置文件方式
            return WallpaperSetter._apply_we_config(folder_path)

        except subprocess.TimeoutExpired:
            logger.warning("WE 命令行超时，尝试配置文件方式")
            return WallpaperSetter._apply_we_config(folder_path)
        except Exception as e:
            logger.error(f"应用 WE 壁纸失败: {e}")
            return WallpaperSetter._apply_we_config(folder_path)

    @staticmethod
    def _apply_we_workshop(we_exe: str, workshop_id: str) -> bool:
        """通过 Workshop ID 应用壁纸"""
        # 先在 Steam Workshop 目录中查找对应文件夹
        steam_libs = WallpaperSetter._find_steam_library_folders()
        for lib in steam_libs:
            wp_folder = lib / "steamapps" / "workshop" / "content" / WallpaperSetter.WE_APP_ID / workshop_id
            if wp_folder.exists():
                return WallpaperSetter._apply_we_local(we_exe, str(wp_folder))

        logger.error(f"未找到 Workshop 壁纸: {workshop_id}")
        return False

    @staticmethod
    def _apply_we_config(folder_path: str) -> bool:
        """通过修改 WE 配置文件设置壁纸

        WE 的配置文件位于:
        %USERPROFILE%/Documents/my games/wallpaper_engine/

        修改 general.conf 或类似配置文件，需要重启 WE 生效。
        """
        config_dir = Path.home() / "Documents" / "my games" / "wallpaper_engine"
        if not config_dir.exists():
            logger.warning(f"WE 配置目录不存在: {config_dir}")
            return False

        # 查找配置文件
        config_file = config_dir / "general.conf"
        if not config_file.exists():
            # 尝试其他可能的配置文件名
            for name in ["settings.json", "config.json", "general.json"]:
                alt = config_dir / name
                if alt.exists():
                    config_file = alt
                    break
            else:
                logger.warning("未找到 WE 配置文件")
                return False

        try:
            # 读取现有配置
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()

            # WE 的配置格式是 key=value（不是标准 JSON）
            # 尝试解析并修改
            if config_file.suffix == ".json":
                config = json.loads(content)
                # JSON 格式配置
                logger.info(f"WE JSON 配置文件: {config_file}")
                # 具体字段需要根据 WE 版本确定
                return False  # 需要实际 WE 环境测试
            else:
                # key=value 格式
                lines = content.split("\n")
                new_lines = []
                found = False
                for line in lines:
                    if line.strip().startswith("wallpaper=") or line.strip().startswith("lastwallpaper="):
                        new_lines.append(f"wallpaper={folder_path}")
                        found = True
                    else:
                        new_lines.append(line)

                if not found:
                    new_lines.append(f"wallpaper={folder_path}")

                with open(config_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(new_lines))

                logger.info(f"WE 配置已更新，需要重启 Wallpaper Engine 生效")
                return True

        except Exception as e:
            logger.error(f"修改 WE 配置失败: {e}")
            return False

    @staticmethod
    def find_we_install() -> Optional[Path]:
        """自动检测 Wallpaper Engine 安装路径

        检查顺序:
        1. Steam 默认路径
        2. Windows 注册表
        3. 常见安装目录

        Returns:
            WE 安装目录路径，未找到返回 None
        """
        # 方式 1: 从 Steam 库路径查找
        steam_libs = WallpaperSetter._find_steam_library_folders()
        for lib in steam_libs:
            we_path = lib / "steamapps" / "common" / "wallpaper_engine"
            if we_path.exists() and (we_path / "wallpaper64.exe").exists():
                logger.info(f"找到 WE 安装路径: {we_path}")
                return we_path

        # 方式 2: 从注册表查找 Steam 路径
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

        # 方式 3: 常见路径暴力搜索
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
        """查找所有 Steam 库文件夹

        从 Steam 的 libraryfolders.vdf 文件解析。

        Returns:
            Steam 库路径列表
        """
        libraries = []

        # 默认 Steam 路径
        for steam_path in WallpaperSetter.STEAM_PATHS:
            if steam_path.exists():
                libraries.append(steam_path)
                break

        # 从 libraryfolders.vdf 解析额外库
        for steam_path in WallpaperSetter.STEAM_PATHS:
            vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
            if vdf_path.exists():
                try:
                    libraries.extend(WallpaperSetter._parse_libraryfolders_vdf(vdf_path))
                except Exception as e:
                    logger.debug(f"解析 libraryfolders.vdf 失败: {e}")
                break

        # 去重
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
        """解析 Steam 的 libraryfolders.vdf 文件

        这是一个 Valve Data Format 文件，包含额外的 Steam 库路径。
        简化解析：提取所有 "path" 字段的值。

        Args:
            vdf_path: libraryfolders.vdf 文件路径

        Returns:
            解析出的库路径列表
        """
        libraries = []
        try:
            with open(vdf_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 简单的正则提取 "path"  "X:\\..."
            import re
            paths = re.findall(r'"path"\s+"([^"]+)"', content)
            for p in paths:
                # VDF 中的路径使用 \\\\ 双转义
                clean_path = p.replace("\\\\", "\\")
                lib_path = Path(clean_path)
                if lib_path.exists():
                    libraries.append(lib_path)
        except Exception as e:
            logger.debug(f"解析 VDF 失败: {e}")

        return libraries

    @staticmethod
    def get_we_wallpaper_list() -> list[dict]:
        """获取 Wallpaper Engine 壁纸列表

        从 Steam Workshop 目录和本地项目目录中扫描。

        Returns:
            壁纸信息列表，每项包含 id, name, type, path
        """
        wallpapers = []

        # Steam Workshop 目录
        steam_libs = WallpaperSetter._find_steam_library_folders()
        for lib in steam_libs:
            workshop_dir = lib / "steamapps" / "workshop" / "content" / WallpaperSetter.WE_APP_ID
            if workshop_dir.exists():
                for item in workshop_dir.iterdir():
                    if item.is_dir():
                        project_json = item / "project.json"
                        if project_json.exists():
                            try:
                                with open(project_json, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                wallpapers.append({
                                    "id": item.name,
                                    "name": data.get("title", item.name),
                                    "type": data.get("type", "unknown"),
                                    "path": str(item),
                                    "source": "steam_workshop",
                                })
                            except Exception:
                                wallpapers.append({
                                    "id": item.name,
                                    "name": item.name,
                                    "type": "unknown",
                                    "path": str(item),
                                    "source": "steam_workshop",
                                })

        # 本地项目目录
        local_projects = Path.home() / "Documents" / "my games" / "wallpaper_engine" / "projects" / "myprojects"
        if local_projects.exists():
            for item in local_projects.iterdir():
                if item.is_dir():
                    project_json = item / "project.json"
                    if project_json.exists():
                        try:
                            with open(project_json, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            wallpapers.append({
                                "id": f"local_{item.name}",
                                "name": data.get("title", item.name),
                                "type": data.get("type", "unknown"),
                                "path": str(item),
                                "source": "local",
                            })
                        except Exception:
                            pass

        logger.info(f"找到 {len(wallpapers)} 个 WE 壁纸")
        return wallpapers
