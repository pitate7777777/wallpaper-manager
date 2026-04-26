"""配置管理"""
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".wallpaper-manager"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "wallpaper_dirs": [],       # Wallpaper Engine 壁纸目录列表
    "last_used_dir": "",        # 上次使用的目录
    "card_size": "medium",      # small / medium / large
    "theme": "dark",            # dark / light
    "thumb_quality": 85,        # 缩略图 JPEG 质量
    "thumb_size": [320, 180],   # 缩略图尺寸 [w, h]
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                merged = {**DEFAULT_CONFIG, **cfg}
                return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def add_wallpaper_dir(directory: str):
    cfg = load_config()
    if directory not in cfg["wallpaper_dirs"]:
        cfg["wallpaper_dirs"].append(directory)
    cfg["last_used_dir"] = directory
    save_config(cfg)
