"""主窗口 - 多选/右键菜单/多目录/缩略图/导入导出"""
import logging
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QLabel, QStatusBar, QFileDialog, QMessageBox,
    QProgressBar, QApplication, QPushButton,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont

from core import db
from core.scanner import scan_directory
from core.models import Wallpaper, TYPE_EMOJI
from core.thumbnail_worker import ThumbnailWorker, cleanup_thumbs
from core.export_worker import ExportWorker, ImportWorker
from core.wallpaper_setter import WallpaperSetter
from core.rotation_worker import RotationWorker
from config import load_config, save_config, add_wallpaper_dir
from ui.wallpaper_card import WallpaperCard, get_card_dimensions
from ui.filter_bar import FilterBar
from ui.preview_dialog import PreviewDialog
from ui.dir_manager_dialog import DirManagerDialog
from ui.tag_manager_dialog import TagManagerDialog
from ui.context_menu import WallpaperContextMenu
from ui.theme import COLORS, set_theme, generate_stylesheet

logger = logging.getLogger(__name__)

CARD_SPACING = 8


# ─── 后台工作线程 ───────────────────────────────────────────────

class ScanWorker(QThread):
    """后台扫描线程（多目录并行）"""
    progress = Signal(int, int, str)
    finished = Signal(dict)

    def __init__(self, directories: list[str]):
        super().__init__()
        self.directories = directories

    def run(self):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        try:
            combined = {"added": 0, "updated": 0, "removed": 0, "errors": 0, "error_details": []}

            if len(self.directories) == 1:
                # 单目录：直接扫描
                self.progress.emit(1, 1, Path(self.directories[0]).name)
                stats = scan_directory(self.directories[0])
                for k in ("added", "updated", "removed", "errors"):
                    combined[k] += stats.get(k, 0)
                combined["error_details"].extend(stats.get("error_details", []))
            else:
                # 多目录：并行扫描
                with ThreadPoolExecutor(max_workers=min(len(self.directories), 4)) as pool:
                    future_to_dir = {
                        pool.submit(scan_directory, d): d
                        for d in self.directories
                    }
                    for i, future in enumerate(as_completed(future_to_dir)):
                        d = future_to_dir[future]
                        self.progress.emit(i + 1, len(self.directories), Path(d).name)
                        try:
                            stats = future.result()
                            for k in ("added", "updated", "removed", "errors"):
                                combined[k] += stats.get(k, 0)
                            combined["error_details"].extend(stats.get("error_details", []))
                        except Exception as e:
                            combined["errors"] += 1
                            combined["error_details"].append({
                                "folder": Path(d).name,
                                "reason": str(e),
                            })

            self.finished.emit(combined)
        except Exception as e:
            self.finished.emit({"error": str(e)})


# ─── 主窗口 ────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎨 Wallpaper Manager")
        self.setMinimumSize(900, 600)
        self.resize(1200, 800)

        # 过滤状态
        self._search_text = ""
        self._type_filter = ""
        self._tag_filter = ""
        self._selected_tags: list[str] = []
        self._favorites_only = False
        self._order_by = "title"
        self._search_mode = "simple"
        self._excluded_tags: list[str] = []
        self._content_rating = ""

        # 显示设置
        cfg = load_config()
        self._card_size = cfg.get("card_size", "medium")
        self._current_theme = cfg.get("theme", "dark")

        # 多选状态
        self._selected_ids: set[int] = set()
        self._last_clicked_id: int | None = None

        # 壁纸 ID → 卡片映射
        self._cards: dict[int, WallpaperCard] = {}
        # 当前查询结果
        self._current_wallpapers: list[Wallpaper] = []

        # 后台线程引用（防止 GC）
        self._scan_worker = None
        self._thumb_worker = None
        self._export_worker = None
        self._import_worker = None

        # 右键菜单
        self._context_menu = WallpaperContextMenu(self)
        self._context_menu.batch_favorite.connect(self._batch_favorite)
        self._context_menu.batch_unfavorite.connect(self._batch_unfavorite)
        self._context_menu.batch_export.connect(self._on_export_selected)
        self._context_menu.open_preview.connect(self._open_preview_from_context)
        self._context_menu.open_folder.connect(self._open_folder_from_context)
        self._context_menu.copy_path.connect(self._copy_path_from_context)
        self._context_menu.set_as_wallpaper.connect(self._on_set_wallpaper)
        self._context_menu.set_as_we_wallpaper.connect(self._on_set_wallpaper_we)
        self._context_menu_wallpaper_id = None

        # 壁纸轮换
        self._rotation_worker = None

        self._setup_ui()
        self._apply_theme(self._current_theme)
        self.filter_bar.set_theme_display(self._current_theme)
        self.filter_bar.set_card_size(self._card_size)
        self._load_data()
        self._start_thumbnail_generation()

    # ─── UI 构建 ──────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 过滤栏
        self.filter_bar = FilterBar()
        self.filter_bar.search_changed.connect(self._on_search)
        self.filter_bar.type_changed.connect(self._on_type_filter)
        self.filter_bar.tag_changed.connect(self._on_tag_filter)
        self.filter_bar.tags_changed.connect(self._on_tags_filter)
        self.filter_bar.favorites_toggled.connect(self._on_favorites)
        self.filter_bar.order_changed.connect(self._on_order)
        self.filter_bar.scan_clicked.connect(self._on_scan)
        self.filter_bar.dir_manager_clicked.connect(self._on_dir_manager)
        self.filter_bar.export_clicked.connect(self._on_export_all)
        self.filter_bar.import_clicked.connect(self._on_import)
        self.filter_bar.rotation_toggled.connect(self._on_rotation_toggle)
        self.filter_bar.search_mode_changed.connect(self._on_search_mode)
        self.filter_bar.exclude_tags_changed.connect(self._on_exclude_tags)
        self.filter_bar.theme_changed.connect(self._on_theme_change)
        self.filter_bar.card_size_changed.connect(self._on_card_size_change)
        self.filter_bar.tag_manager_clicked.connect(self._on_tag_manager)
        self.filter_bar.rating_changed.connect(self._on_rating_filter)
        main_layout.addWidget(self.filter_bar)

        # 统计 + 选择状态栏
        info_bar = QWidget()
        info_bar.setObjectName("infoBar")
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(12, 4, 12, 4)

        self.stats_label = QLabel()
        self.stats_label.setObjectName("statsLabel")
        self.stats_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        info_layout.addWidget(self.stats_label)

        info_layout.addStretch()

        self.selection_label = QLabel()
        self.selection_label.setObjectName("selectionLabel")
        self.selection_label.setStyleSheet(f"color: {COLORS['selection_text']}; font-size: 12px;")
        self.selection_label.setVisible(False)
        info_layout.addWidget(self.selection_label)

        clear_sel_btn = QPushButton("✕ 取消选择")
        clear_sel_btn.setObjectName("clearSelBtn")
        clear_sel_btn.setFixedHeight(22)
        clear_sel_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        clear_sel_btn.clicked.connect(self._clear_selection)
        clear_sel_btn.setVisible(False)
        self._clear_sel_btn = clear_sel_btn
        info_layout.addWidget(clear_sel_btn)

        main_layout.addWidget(info_bar)

        # 滚动区域 + 网格
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setObjectName("scrollArea")

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(CARD_SPACING)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_area.setWidget(self.grid_widget)
        main_layout.addWidget(self.scroll_area, 1)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMaximumHeight(20)
        self.status_bar.addPermanentWidget(self.progress_bar)

    # ─── 数据加载 ─────────────────────────────────────────────

    def _load_data(self):
        db.init_db()
        # 确定标签过滤：多选优先，单选回退
        tags_filter = self._selected_tags if self._selected_tags else (
            [self._tag_filter] if self._tag_filter else None
        )
        wallpapers = db.query_wallpapers(
            search=self._search_text,
            wp_type=self._type_filter,
            tags=tags_filter,
            favorites_only=self._favorites_only,
            order_by=self._order_by,
            search_mode=self._search_mode,
            tags_mode="any",
            exclude_tags=self._excluded_tags if self._excluded_tags else None,
            content_rating=self._content_rating,
        )
        self._current_wallpapers = wallpapers
        self._populate_grid(wallpapers)
        self._update_stats()
        self._update_tags()
        self._update_ratings()

    def _populate_grid(self, wallpapers: list[Wallpaper]):
        # 清空旧卡片
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        if not wallpapers:
            empty = QLabel("📭 没有找到壁纸\n\n点击「扫描」导入 Wallpaper Engine 壁纸\n或通过「目录」管理多个壁纸库")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px; padding: 60px;")
            self.grid_layout.addWidget(empty, 0, 0, 1, -1)
            return

        preview_w, preview_h = get_card_dimensions(self._card_size)
        area_width = self.scroll_area.viewport().width() - 20
        card_full_width = preview_w + 16 + CARD_SPACING
        cols = max(1, area_width // card_full_width)

        for i, wp in enumerate(wallpapers):
            row, col = divmod(i, cols)
            card = WallpaperCard(wp, size=self._card_size)
            card.clicked.connect(self._on_card_clicked)
            card.ctrl_clicked.connect(self._on_card_ctrl_clicked)
            card.shift_clicked.connect(self._on_card_shift_clicked)
            card.favorite_toggled.connect(self._on_favorite_toggled)
            card.context_menu_requested.connect(self._on_context_menu)

            # 恢复选中状态
            if wp.id in self._selected_ids:
                card.set_selected(True)

            self._cards[wp.id] = card
            self.grid_layout.addWidget(card, row, col)

    def _update_stats(self):
        stats = db.get_stats()
        parts = [f"共 {stats['total']} 张壁纸"]
        if stats['favorites']:
            parts.append(f"❤️ {stats['favorites']} 收藏")
        for t, c in stats['by_type'].items():
            emoji = TYPE_EMOJI.get(t, "📄")
            parts.append(f"{emoji} {t}: {c}")
        self.stats_label.setText("  ·  ".join(parts))

    def _update_tags(self):
        tags = db.get_all_tags()
        self.filter_bar.update_tags(tags)

    def _update_selection_ui(self):
        """更新多选状态栏"""
        count = len(self._selected_ids)
        if count > 0:
            self.selection_label.setText(f"已选择 {count} 项")
            self.selection_label.setVisible(True)
            self._clear_sel_btn.setVisible(True)
        else:
            self.selection_label.setVisible(False)
            self._clear_sel_btn.setVisible(False)

    # ─── 过滤事件 ─────────────────────────────────────────────

    def _on_search(self, text: str):
        self._search_text = text
        self._reload_with_delay()

    def _on_type_filter(self, wp_type: str):
        self._type_filter = wp_type
        self._load_data()

    def _on_tag_filter(self, tag: str):
        self._tag_filter = tag
        self._selected_tags = []  # 清除多选
        self._load_data()

    def _on_tags_filter(self, tags: list[str]):
        """多选标签过滤"""
        self._selected_tags = tags
        self._tag_filter = ""  # 清除单选
        self._load_data()

    def _on_favorites(self, checked: bool):
        self._favorites_only = checked
        self._load_data()

    def _on_order(self, order: str):
        self._order_by = order
        self._load_data()

    def _on_search_mode(self, mode: str):
        """搜索模式变更"""
        self._search_mode = mode
        self._load_data()

    def _on_exclude_tags(self, tags: list[str]):
        """排除标签变更"""
        self._excluded_tags = tags
        self._load_data()

    def _on_rating_filter(self, rating: str):
        """内容分级过滤"""
        self._content_rating = rating
        self._load_data()

    def _update_ratings(self):
        """更新内容分级下拉框选项"""
        ratings = db.get_all_ratings()
        self.filter_bar.update_ratings(ratings)

    def _reload_with_delay(self):
        if not hasattr(self, "_search_timer"):
            self._search_timer = QTimer()
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self._load_data)
        self._search_timer.start(300)

    # ─── 多选逻辑 ─────────────────────────────────────────────

    def _on_card_clicked(self, wallpaper_id: int):
        """普通点击：清除其他选中，打开预览"""
        self._clear_selection()
        self._last_clicked_id = wallpaper_id
        self._open_preview(wallpaper_id)

    def _on_card_ctrl_clicked(self, wallpaper_id: int):
        """Ctrl+点击：切换选中"""
        if wallpaper_id in self._selected_ids:
            self._selected_ids.discard(wallpaper_id)
            if wallpaper_id in self._cards:
                self._cards[wallpaper_id].set_selected(False)
        else:
            self._selected_ids.add(wallpaper_id)
            if wallpaper_id in self._cards:
                self._cards[wallpaper_id].set_selected(True)
        self._last_clicked_id = wallpaper_id
        self._update_selection_ui()

    def _on_card_shift_clicked(self, wallpaper_id: int):
        """Shift+点击：范围选中"""
        if self._last_clicked_id is None:
            self._on_card_ctrl_clicked(wallpaper_id)
            return

        # 在当前列表中找到范围
        ids = [wp.id for wp in self._current_wallpapers]
        try:
            start = ids.index(self._last_clicked_id)
            end = ids.index(wallpaper_id)
        except ValueError:
            return

        if start > end:
            start, end = end, start

        for i in range(start, end + 1):
            wp_id = ids[i]
            self._selected_ids.add(wp_id)
            if wp_id in self._cards:
                self._cards[wp_id].set_selected(True)

        self._last_clicked_id = wallpaper_id
        self._update_selection_ui()

    def _clear_selection(self):
        self._selected_ids.clear()
        for card in self._cards.values():
            card.set_selected(False)
        self._update_selection_ui()

    # ─── 右键菜单 ─────────────────────────────────────────────

    def _on_context_menu(self, wallpaper_id: int, global_pos):
        self._context_menu_wallpaper_id = wallpaper_id
        wp = next((w for w in self._current_wallpapers if w.id == wallpaper_id), None)
        # 如果壁纸在选中集合中，显示选中数量；否则显示单个
        count = len(self._selected_ids) if wallpaper_id in self._selected_ids else (1 if wp else 0)
        self._context_menu.show(global_pos, wp, count)

    def _open_preview_from_context(self):
        if self._context_menu_wallpaper_id:
            self._open_preview(self._context_menu_wallpaper_id)

    def _open_folder_from_context(self):
        if self._context_menu_wallpaper_id:
            wp = next((w for w in self._current_wallpapers if w.id == self._context_menu_wallpaper_id), None)
            if wp:
                if Path(wp.folder_path).exists():
                    subprocess.Popen(["explorer", wp.folder_path])

    def _copy_path_from_context(self):
        if self._context_menu_wallpaper_id:
            wp = next((w for w in self._current_wallpapers if w.id == self._context_menu_wallpaper_id), None)
            if wp:
                QApplication.clipboard().setText(wp.folder_path)
                self.status_bar.showMessage("📋 路径已复制到剪贴板", 2000)

    # ─── 批量操作 ─────────────────────────────────────────────

    def _batch_favorite(self):
        """批量收藏（强制设为收藏状态）"""
        targets = self._selected_ids if self._selected_ids else (
            {self._context_menu_wallpaper_id} if self._context_menu_wallpaper_id else set()
        )
        targets = [wp_id for wp_id in targets if wp_id]
        if not targets:
            return
        count = db.batch_set_favorite(targets, True)
        self.status_bar.showMessage(f"❤️ 已收藏 {count} 项", 2000)
        self._clear_selection()
        self._load_data()

    def _batch_unfavorite(self):
        """批量取消收藏（强制取消收藏状态）"""
        targets = self._selected_ids if self._selected_ids else (
            {self._context_menu_wallpaper_id} if self._context_menu_wallpaper_id else set()
        )
        targets = [wp_id for wp_id in targets if wp_id]
        if not targets:
            return
        count = db.batch_set_favorite(targets, False)
        self.status_bar.showMessage(f"🤍 已取消收藏 {count} 项", 2000)
        self._clear_selection()
        self._load_data()

    # ─── 扫描（支持多目录）────────────────────────────────────

    def _on_scan(self):
        cfg = load_config()
        dirs = cfg.get("wallpaper_dirs", [])

        if not dirs:
            # 无已配置目录，走单目录选择
            directory = QFileDialog.getExistingDirectory(
                self, "选择壁纸目录", str(Path.home()),
            )
            if not directory:
                return
            dirs = [directory]
            add_wallpaper_dir(directory)

        self._start_scan(dirs)

    def _start_scan(self, directories: list[str]):
        self._scan_worker = ScanWorker(directories)
        self._scan_worker.finished.connect(self._on_scan_finished)

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # 不确定进度
        self.filter_bar.scan_btn.setEnabled(False)
        self.status_bar.showMessage(f"正在扫描 {len(directories)} 个目录...")
        self._scan_worker.start()

    def _on_scan_finished(self, stats: dict):
        self.progress_bar.setVisible(False)
        self.filter_bar.scan_btn.setEnabled(True)

        if "error" in stats:
            QMessageBox.critical(self, "扫描失败", stats["error"])
            self.status_bar.showMessage("扫描失败")
            return

        msg = f"✅ 扫描完成 — 新增: {stats['added']}, 更新: {stats['updated']}, 移除: {stats['removed']}"
        if stats['errors']:
            msg += f", 错误: {stats['errors']}"

        # 清理过期缩略图缓存
        all_wallpapers = db.query_wallpapers()
        valid_paths = {wp.preview_path for wp in all_wallpapers if wp.preview_path}
        cleaned = cleanup_thumbs(valid_paths)
        if cleaned:
            msg += f", 清理缓存: {cleaned}"

        self.status_bar.showMessage(msg)

        # 显示扫描错误详情（最多 5 条）
        error_details = stats.get("error_details", [])
        if error_details:
            detail_lines = [f"• {e['folder']}: {e['reason']}" for e in error_details[:5]]
            if len(error_details) > 5:
                detail_lines.append(f"... 还有 {len(error_details) - 5} 个错误")
            QMessageBox.warning(
                self,
                f"扫描完成（{stats['errors']} 个错误）",
                "以下文件解析失败（非壁纸文件或格式异常）：\n\n"
                + "\n".join(detail_lines)
                + "\n\n这些文件已被跳过，不影响其他壁纸。",
            )

        self._load_data()
        self._start_thumbnail_generation()

    # ─── 目录管理 ─────────────────────────────────────────────

    def _on_dir_manager(self):
        dlg = DirManagerDialog(self)
        dlg.dirs_changed.connect(self._on_dirs_changed)
        if dlg.exec() and dlg.should_scan_all():
            cfg = load_config()
            dirs = cfg.get("wallpaper_dirs", [])
            if dirs:
                self._start_scan(dirs)

    def _on_dirs_changed(self):
        self.status_bar.showMessage("📂 目录列表已更新", 2000)

    # ─── 缩略图生成 ───────────────────────────────────────────

    def _start_thumbnail_generation(self):
        """启动后台缩略图生成"""
        if self._thumb_worker and self._thumb_worker.isRunning():
            return

        wallpapers = db.query_wallpapers()
        # 过滤掉已有缓存的
        from core.thumbnail_worker import get_thumb_path
        needs_gen = [
            wp for wp in wallpapers
            if wp.preview_path and Path(wp.preview_path).exists()
            and not get_thumb_path(wp.preview_path).exists()
        ]

        if not needs_gen:
            return

        self._thumb_worker = ThumbnailWorker(needs_gen)
        self._thumb_worker.progress.connect(self._on_thumb_progress)
        self._thumb_worker.finished.connect(self._on_thumb_finished)
        self._thumb_worker.start()

    def _on_thumb_progress(self, current, total, title):
        self.status_bar.showMessage(f"🖼️ 生成缩略图: {title} ({current}/{total})")

    def _on_thumb_finished(self, count):
        if count > 0:
            self.status_bar.showMessage(f"✅ 缩略图生成完成，共 {count} 张", 3000)
            # 复用现有壁纸数据重建卡片（缩略图已落盘，WallpaperCard 会自动加载缓存）
            # 不重新查询数据库，避免不必要的 IO
            self._populate_grid(self._current_wallpapers)
        else:
            self.status_bar.showMessage("缩略图已是最新", 2000)

    # ─── 导入/导出 ────────────────────────────────────────────

    def _on_export_all(self):
        """导出全部收藏"""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出收藏列表",
            str(Path.home() / "wallpaper_favorites.json"),
            "JSON 文件 (*.json)",
        )
        if not path:
            return

        self._export_worker = ExportWorker(path, favorites_only=True)
        self._export_worker.finished.connect(self._on_export_finished)
        self.status_bar.showMessage("📤 正在导出...")
        self._export_worker.start()

    def _on_export_selected(self):
        """导出选中的壁纸"""
        if not self._selected_ids:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "导出选中壁纸",
            str(Path.home() / "wallpaper_selection.json"),
            "JSON 文件 (*.json)",
        )
        if not path:
            return

        self._export_worker = ExportWorker(path, favorites_only=False,
                                           wallpaper_ids=self._selected_ids)
        self._export_worker.finished.connect(self._on_export_finished)
        self.status_bar.showMessage("📤 正在导出选中项...")
        self._export_worker.start()

    def _on_export_finished(self, success, message):
        self.status_bar.showMessage(message, 5000)

    def _on_import(self):
        """导入壁纸列表"""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入壁纸列表",
            str(Path.home()),
            "JSON 文件 (*.json)",
        )
        if not path:
            return

        self._import_worker = ImportWorker(path)
        self._import_worker.progress.connect(self._on_import_progress)
        self._import_worker.finished.connect(self._on_import_finished)

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)
        self.filter_bar.import_btn.setEnabled(False)
        self.status_bar.showMessage("📥 正在导入...")
        self._import_worker.start()

    def _on_import_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def _on_import_finished(self, stats):
        self.progress_bar.setVisible(False)
        self.filter_bar.import_btn.setEnabled(True)

        if "error" in stats:
            QMessageBox.critical(self, "导入失败", stats["error"])
            self.status_bar.showMessage("导入失败")
            return

        msg = f"✅ 导入完成 — 新增: {stats['imported']}, 跳过: {stats['skipped']}, 错误: {stats['errors']}"
        self.status_bar.showMessage(msg, 5000)
        self._load_data()
        self._start_thumbnail_generation()

    # ─── 预览 ─────────────────────────────────────────────────

    def _open_preview(self, wallpaper_id: int):
        wp = next((w for w in self._current_wallpapers if w.id == wallpaper_id), None)
        if wp:
            # 计算当前壁纸在列表中的索引
            ids = [w.id for w in self._current_wallpapers]
            idx = ids.index(wallpaper_id) if wallpaper_id in ids else 0
            dlg = PreviewDialog(wp, self._current_wallpapers, idx, self)
            dlg.favorite_toggled.connect(self._on_favorite_toggled)
            dlg.exec()

    # ─── 单卡交互 ─────────────────────────────────────────────

    def _on_favorite_toggled(self, wallpaper_id: int):
        new_state = db.toggle_favorite(wallpaper_id)
        emoji = "❤️" if new_state else "🤍"
        self.status_bar.showMessage(f"{emoji} 收藏{'已添加' if new_state else '已取消'}", 2000)
        # 更新卡片按钮文本
        if wallpaper_id in self._cards:
            self._cards[wallpaper_id].fav_btn.setText(emoji)
        self._update_stats()

    # ─── 标签管理 ─────────────────────────────────────────────

    def _on_tag_manager(self):
        """打开标签管理对话框"""
        dlg = TagManagerDialog(self)
        dlg.tags_changed.connect(self._on_tags_changed)
        dlg.exec()

    def _on_tags_changed(self):
        """标签变化后刷新"""
        self._update_tags()
        self.status_bar.showMessage("🏷️ 标签已更新", 2000)

    # ─── 主题切换 ─────────────────────────────────────────────

    def _on_theme_change(self, theme_name: str):
        """切换主题"""
        self._apply_theme(theme_name)
        self._current_theme = theme_name
        # 刷新所有卡片的 inline 样式（卡片用 COLORS 值硬编码了边框/背景色）
        for card in self._cards.values():
            card._update_style()
        # 刷新 stats_label / selection_label 等 inline 样式
        self.stats_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px;"
        )
        self.selection_label.setStyleSheet(
            f"color: {COLORS['selection_text']}; font-size: 12px;"
        )
        # 刷新 filter_bar 分隔线等 inline 样式
        self.filter_bar.refresh_theme()
        # 保存到配置
        cfg = load_config()
        cfg["theme"] = theme_name
        save_config(cfg)
        self.status_bar.showMessage(
            f"🎨 已切换到{'亮色' if theme_name == 'light' else '暗色'}主题", 2000
        )

    def _apply_theme(self, theme_name: str):
        """应用主题样式表"""
        try:
            set_theme(theme_name)
        except KeyError:
            return
        stylesheet = generate_stylesheet()
        QApplication.instance().setStyleSheet(stylesheet)

    # ─── 卡片尺寸 ─────────────────────────────────────────────

    def _on_card_size_change(self, size: str):
        """切换卡片尺寸"""
        self._card_size = size
        # 保存到配置
        cfg = load_config()
        cfg["card_size"] = size
        save_config(cfg)
        # 复用已有数据重建网格（避免重新查询数据库）
        self._populate_grid(self._current_wallpapers)
        self.status_bar.showMessage(f"📐 卡片尺寸: {size}", 2000)

    # ─── 壁纸设置 ─────────────────────────────────────────────

    def _on_set_wallpaper(self):
        """设为桌面壁纸（静态图片）"""
        if not self._context_menu_wallpaper_id:
            return
        wp = next(
            (w for w in self._current_wallpapers if w.id == self._context_menu_wallpaper_id),
            None,
        )
        if not wp:
            return

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "设置壁纸",
            f"确定要将「{wp.title}」设为桌面壁纸吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        image_path = wp.preview_path or wp.wallpaper_file_path
        if not image_path or not Path(image_path).exists():
            self.status_bar.showMessage("❌ 壁纸文件不存在", 3000)
            return

        success = WallpaperSetter.set_wallpaper(image_path)
        if success:
            self.status_bar.showMessage(f"✅ 桌面壁纸已设置为「{wp.title}」", 3000)
        else:
            self.status_bar.showMessage(f"❌ 设置壁纸失败，请检查文件格式", 5000)

    def _on_set_wallpaper_we(self):
        """设为 WE 动态壁纸"""
        if not self._context_menu_wallpaper_id:
            return
        wp = next(
            (w for w in self._current_wallpapers if w.id == self._context_menu_wallpaper_id),
            None,
        )
        if not wp:
            return

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "设置 WE 壁纸",
            f"确定要将「{wp.title}」设为 Wallpaper Engine 壁纸吗？\n\n"
            "注意：需要 Wallpaper Engine 正在运行。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        success = WallpaperSetter.set_wallpaper_we(wp.folder_path)
        if success:
            self.status_bar.showMessage(f"✅ WE 壁纸已设置为「{wp.title}」", 3000)
        else:
            self.status_bar.showMessage(
                f"❌ 设置 WE 壁纸失败，请确认 Wallpaper Engine 已安装且正在运行", 5000
            )

    # ─── 壁纸轮换 ─────────────────────────────────────────────

    def _on_rotation_toggle(self, enabled: bool, interval_minutes: int, mode: str):
        """切换壁纸轮换状态"""
        if enabled:
            self._start_rotation(interval_minutes, mode)
        else:
            self._stop_rotation()

    def _start_rotation(self, interval_minutes: int, mode: str):
        """启动壁纸轮换

        db_query_func 始终查全部壁纸；"收藏模式"过滤在 RotationWorker
        内部的 _refresh_wallpaper_list 中执行，避免与 db_query_func 双重叠加
        导致 random/sequential 模式也只轮换收藏壁纸。
        """
        if self._rotation_worker is None:
            self._rotation_worker = RotationWorker(
                db_query_func=lambda: db.query_wallpapers(),
                set_wallpaper_func=self._apply_rotation_wallpaper,
                interval_minutes=interval_minutes,
                mode=mode,
                parent=self,
            )
            self._rotation_worker.wallpaper_changed.connect(self._on_rotation_wallpaper_changed)
            self._rotation_worker.rotation_started.connect(self._on_rotation_started)
            self._rotation_worker.rotation_stopped.connect(self._on_rotation_stopped)
            self._rotation_worker.error_occurred.connect(self._on_rotation_error)

        self._rotation_worker.start_rotation(interval_minutes, mode)

    def _stop_rotation(self):
        """停止壁纸轮换"""
        if self._rotation_worker:
            self._rotation_worker.cleanup()
            self._rotation_worker = None

    def _apply_rotation_wallpaper(self, wallpaper):
        """轮换时应用壁纸（内部方法）"""
        if sys.platform != "win32":
            logger.warning("壁纸轮换仅支持 Windows")
            return

        image_path = wallpaper.preview_path or wallpaper.wallpaper_file_path
        if image_path and Path(image_path).exists():
            WallpaperSetter.set_wallpaper(image_path)
        else:
            # 尝试 WE 方式
            WallpaperSetter.set_wallpaper_we(wallpaper.folder_path)

    def _on_rotation_wallpaper_changed(self, wp_id: str, title: str):
        """轮换壁纸变化通知"""
        self.status_bar.showMessage(f"🔄 壁纸轮换: {title}", 3000)

    def _on_rotation_started(self, interval_minutes: int, mode: str):
        """轮换启动通知"""
        mode_names = {"random": "随机", "sequential": "顺序", "favorite": "收藏"}
        mode_name = mode_names.get(mode, mode)
        self.status_bar.showMessage(
            f"🔄 壁纸轮换已启动: 每 {interval_minutes} 分钟 ({mode_name})", 3000
        )

    def _on_rotation_stopped(self):
        """轮换停止通知"""
        self.status_bar.showMessage("🔄 壁纸轮换已停止", 3000)

    def _on_rotation_error(self, message: str):
        """轮换错误通知"""
        self.status_bar.showMessage(f"❌ 轮换错误: {message}", 5000)

    # ─── 窗口事件 ─────────────────────────────────────────────

    def resizeEvent(self, event):
        """窗口大小变化时重新排列卡片（轻量级，不重新查询数据库）"""
        super().resizeEvent(event)
        if not hasattr(self, "_resize_timer"):
            self._resize_timer = QTimer()
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._relayout_grid)
        self._resize_timer.start(100)

    def _relayout_grid(self):
        """仅重新计算网格位置，不重建卡片、不查询数据库"""
        if not self._current_wallpapers:
            return

        preview_w, preview_h = get_card_dimensions(self._card_size)
        area_width = self.scroll_area.viewport().width() - 20
        card_full_width = preview_w + 16 + CARD_SPACING
        cols = max(1, area_width // card_full_width)

        # 收集当前所有卡片（保持顺序）
        cards_in_order = []
        for wp in self._current_wallpapers:
            if wp.id in self._cards:
                cards_in_order.append(self._cards[wp.id])

        # 先从 grid 中移除所有卡片（不 deleteLater）
        for card in cards_in_order:
            self.grid_layout.removeWidget(card)

        # 重新放入 grid
        for i, card in enumerate(cards_in_order):
            row, col = divmod(i, cols)
            self.grid_layout.addWidget(card, row, col)

    def closeEvent(self, event):
        """关闭时清理后台线程"""
        # 停止壁纸轮换
        if self._rotation_worker:
            self._rotation_worker.cleanup()
            self._rotation_worker = None

        workers = [
            (self._thumb_worker, True),   # has cancel()
            (self._scan_worker, False),
            (self._export_worker, True),   # has cancel()
            (self._import_worker, True),   # has cancel()
        ]
        for worker, has_cancel in workers:
            if worker and worker.isRunning():
                if has_cancel:
                    worker.cancel()
                worker.wait(2000)
        super().closeEvent(event)

    def keyPressEvent(self, event):
        """全局快捷键处理"""
        key = event.key()
        mods = event.modifiers()

        # Ctrl+F — 聚焦搜索框
        if key == Qt.Key_F and mods == Qt.ControlModifier:
            self.filter_bar.focus_search()
            event.accept()
            return

        # F5 — 刷新/扫描
        if key == Qt.Key_F5:
            self._on_scan()
            event.accept()
            return

        # Ctrl+A — 全选当前过滤结果
        if key == Qt.Key_A and mods == Qt.ControlModifier:
            self._select_all()
            event.accept()
            return

        # Delete — 删除选中项（需确认）
        if key == Qt.Key_Delete and self._selected_ids:
            self._delete_selected()
            event.accept()
            return

        super().keyPressEvent(event)

    def _select_all(self):
        """全选当前过滤结果"""
        for wp in self._current_wallpapers:
            self._selected_ids.add(wp.id)
            if wp.id in self._cards:
                self._cards[wp.id].set_selected(True)
        self._update_selection_ui()

    def _delete_selected(self):
        """删除选中的壁纸记录（需确认）"""
        if not self._selected_ids:
            return
        count = len(self._selected_ids)
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {count} 项壁纸记录吗？\n\n注意：此操作不会删除磁盘上的文件。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        removed = 0
        for wp_id in list(self._selected_ids):
            wp = next((w for w in self._current_wallpapers if w.id == wp_id), None)
            if wp:
                db.remove_wallpaper(wp.folder_path)
                removed += 1
        self.status_bar.showMessage(f"🗑️ 已删除 {removed} 项记录", 3000)
        self._clear_selection()
        self._load_data()
        self._start_thumbnail_generation()
