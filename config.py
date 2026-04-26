"""配置管理"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".wallpaper-manager"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: dict = {
    "wallpaper_dirs": [],       # Wallpaper Engine 壁纸目录列表
    "last_used_dir": "",        # 上次使用的目录
    "card_size": "medium",      # small / medium / large
    "theme": "dark",            # dark / light
    "thumb_quality": 85,        # 缩略图 JPEG 质量
    "thumb_size": [320, 180],   # 缩略图尺寸 [w, h]
}


def load_config() -> dict:
    """加载配置文件，缺失字段用 DEFAULT_CONFIG 补齐。"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                merged = {**DEFAULT_CONFIG, **cfg}
                return merged
        except Exception as e:
            logger.warning(
                "配置文件读取失败，已回退到默认配置：%s（路径：%s）",
                e,
                CONFIG_PATH,
            )
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    """保存配置到文件。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def add_wallpaper_dir(directory: str) -> None:
    """添加壁纸目录到配置（去重）。"""
    cfg = load_config()
    if directory not in cfg["wallpaper_dirs"]:
        cfg["wallpaper_dirs"].append(directory)
    cfg["last_used_dir"] = directory
    save_config(cfg)
