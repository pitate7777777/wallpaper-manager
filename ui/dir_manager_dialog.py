"""多目录管理对话框"""
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal

from config import load_config, save_config
from ui.theme import COLORS


class DirManagerDialog(QDialog):
    """管理多个壁纸目录"""

    dirs_changed = Signal()  # 目录列表变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📂 壁纸目录管理")
        self.setMinimumSize(500, 350)
        self.resize(550, 400)

        self._config = load_config()
        self._setup_ui()
        self._populate_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 说明
        info = QLabel("管理 Wallpaper Engine 壁纸库目录。可添加多个目录，扫描时会合并所有目录。")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(info)

        # 目录列表
        self.dir_list = QListWidget()
        self.dir_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.dir_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 6px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['selection_bg']};
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['bg_card_hover']};
            }}
        """)
        layout.addWidget(self.dir_list)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        add_btn = QPushButton("➕ 添加目录")
        add_btn.setObjectName("addDirBtn")
        add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton("➖ 移除选中")
        remove_btn.setObjectName("removeDirBtn")
        remove_btn.clicked.connect(self._on_remove)
        btn_layout.addWidget(remove_btn)

        btn_layout.addStretch()

        scan_all_btn = QPushButton("🔄 扫描全部")
        scan_all_btn.setObjectName("scanAllBtn")
        scan_all_btn.clicked.connect(self._on_scan_all)
        btn_layout.addWidget(scan_all_btn)

        layout.addLayout(btn_layout)

        # 底部状态
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _populate_list(self):
        """填充目录列表"""
        self.dir_list.clear()
        dirs = self._config.get("wallpaper_dirs", [])
        for d in dirs:
            exists = Path(d).is_dir()
            icon = "✅" if exists else "❌"
            item = QListWidgetItem(f"{icon} {d}")
            item.setData(Qt.UserRole, d)
            if not exists:
                item.setForeground(Qt.red)
            self.dir_list.addItem(item)
        self.status_label.setText(f"共 {len(dirs)} 个目录")

    def _on_add(self):
        """添加目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择壁纸目录",
            self._config.get("last_used_dir", "") or str(Path.home()),
        )
        if not directory:
            return

        dirs = self._config.get("wallpaper_dirs", [])
        if directory in dirs:
            QMessageBox.information(self, "提示", "该目录已在列表中")
            return

        dirs.append(directory)
        self._config["wallpaper_dirs"] = dirs
        self._config["last_used_dir"] = directory
        save_config(self._config)

        self._populate_list()
        self.dirs_changed.emit()

    def _on_remove(self):
        """移除选中目录"""
        item = self.dir_list.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选择要移除的目录")
            return

        directory = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "确认移除",
            f"确定从列表中移除？\n{directory}\n\n（不会删除实际文件）",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        dirs = self._config.get("wallpaper_dirs", [])
        if directory in dirs:
            dirs.remove(directory)
            self._config["wallpaper_dirs"] = dirs
            save_config(self._config)

        self._populate_list()
        self.dirs_changed.emit()

    def _on_scan_all(self):
        """扫描全部目录（关闭对话框，由主窗口执行）"""
        self._scan_all = True
        self.accept()

    def should_scan_all(self) -> bool:
        return getattr(self, "_scan_all", False)
