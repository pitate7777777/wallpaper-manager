"""数据模型"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Wallpaper:
    id: Optional[int] = None
    folder_path: str = ""
    workshop_id: str = ""
    title: str = ""
    wp_type: str = ""            # video / scene / web / application
    file: str = ""               # 实际壁纸文件名
    preview: str = ""            # preview.jpg 相对路径
    tags: list[str] = field(default_factory=list)
    content_rating: str = ""
    description: str = ""
    is_favorite: bool = False
    scheme_color: str = ""       # 主题色，如 "0.51373 0.54510 0.70588"
    extra_data: str = ""         # 未解析的原始字段（JSON 序列化），防止信息丢失

    @property
    def preview_path(self) -> str:
        """预览图的绝对路径"""
        import os
        if self.preview:
            return os.path.join(self.folder_path, self.preview)
        return ""

    @property
    def wallpaper_file_path(self) -> str:
        """壁纸文件的绝对路径"""
        import os
        if self.file:
            return os.path.join(self.folder_path, self.file)
        return ""

    @property
    def tags_display(self) -> str:
        return ", ".join(self.tags) if self.tags else ""

    @property
    def type_emoji(self) -> str:
        return {"video": "🎬", "scene": "🖼️", "web": "🌐"}.get(self.wp_type, "📄")

    @property
    def scheme_color_hex(self) -> str:
        """将 "0.51373 0.54510 0.70588" 转为 #838BB4"""
        if not self.scheme_color:
            return ""
        try:
            parts = self.scheme_color.split()
            r, g, b = [int(float(v) * 255) for v in parts[:3]]
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return ""
