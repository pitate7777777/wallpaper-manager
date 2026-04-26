"""右键上下文菜单"""
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal, QObject


class WallpaperContextMenu(QObject):
    """壁纸卡片右键菜单"""

    batch_favorite = Signal()       # 批量收藏
    batch_unfavorite = Signal()     # 批量取消收藏
    batch_export = Signal()         # 批量导出
    open_preview = Signal()         # 打开预览
    open_folder = Signal()          # 打开文件夹
    copy_path = Signal()            # 复制路径
    apply_wallpaper = Signal()      # 应用壁纸（在 WE 中打开）
    set_as_wallpaper = Signal()     # 设为桌面壁纸（静态图片）
    set_as_we_wallpaper = Signal()  # 设为 WE 动态壁纸

    def __init__(self, parent=None):
        super().__init__(parent)

    def show(self, pos, wallpaper=None, selected_count=0):
        """显示右键菜单"""
        menu = QMenu()

        # 单个壁纸操作
        if wallpaper and selected_count <= 1:
            preview_action = QAction(f"🔍 预览 - {wallpaper.title}", menu)
            preview_action.triggered.connect(self.open_preview.emit)
            menu.addAction(preview_action)

            # 设为桌面壁纸（静态图片类型时显示）
            if wallpaper.wp_type == "scene":
                set_wp_action = QAction("🖼️ 设为桌面壁纸", menu)
                set_wp_action.triggered.connect(self.set_as_wallpaper.emit)
                menu.addAction(set_wp_action)

            # 设为 WE 动态壁纸
            set_we_action = QAction("🎬 设为 WE 壁纸", menu)
            set_we_action.triggered.connect(self.set_as_we_wallpaper.emit)
            menu.addAction(set_we_action)

            apply_action = QAction("🎨 在 Wallpaper Engine 中应用", menu)
            apply_action.triggered.connect(self.apply_wallpaper.emit)
            menu.addAction(apply_action)

            folder_action = QAction("📁 打开文件夹", menu)
            folder_action.triggered.connect(self.open_folder.emit)
            menu.addAction(folder_action)

            copy_action = QAction("📋 复制路径", menu)
            copy_action.triggered.connect(self.copy_path.emit)
            menu.addAction(copy_action)

            menu.addSeparator()

        # 批量操作
        if selected_count > 1:
            fav_action = QAction(f"❤️ 收藏选中的 {selected_count} 项", menu)
            fav_action.triggered.connect(self.batch_favorite.emit)
            menu.addAction(fav_action)

            unfav_action = QAction(f"🤍 取消收藏选中的 {selected_count} 项", menu)
            unfav_action.triggered.connect(self.batch_unfavorite.emit)
            menu.addAction(unfav_action)

            menu.addSeparator()

            export_action = QAction(f"📤 导出选中的 {selected_count} 项", menu)
            export_action.triggered.connect(self.batch_export.emit)
            menu.addAction(export_action)
        elif wallpaper:
            fav_text = "🤍 取消收藏" if wallpaper.is_favorite else "❤️ 收藏"
            fav_action = QAction(fav_text, menu)
            if wallpaper.is_favorite:
                fav_action.triggered.connect(self.batch_unfavorite.emit)
            else:
                fav_action.triggered.connect(self.batch_favorite.emit)
            menu.addAction(fav_action)

        menu.exec(pos)
