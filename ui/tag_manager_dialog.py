"""标签管理对话框 - 重命名、合并、删除标签"""
import logging

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QInputDialog, QMessageBox, QLineEdit,
    QWidget, QGroupBox,
)
from PySide6.QtCore import Qt, Signal

from core import db
from ui.theme import COLORS

logger = logging.getLogger(__name__)


class TagManagerDialog(QDialog):
    """标签管理对话框

    支持:
    - 重命名标签
    - 合并多个标签为一个
    - 删除标签
    """

    tags_changed = Signal()  # 标签发生变化时发出

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏷️ 标签管理")
        self.setMinimumSize(500, 400)
        self.resize(550, 450)

        self._setup_ui()
        self._load_tags()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 说明
        desc = QLabel("管理壁纸标签：重命名、合并或删除。")
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(desc)

        # 标签列表
        self.tag_list = QListWidget()
        self.tag_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.tag_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['selection_bg']};
                color: {COLORS['text_primary']};
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['bg_dropdown']};
            }}
        """)
        layout.addWidget(self.tag_list, 1)

        # 统计
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self.stats_label)

        # 按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.rename_btn = QPushButton("✏️ 重命名")
        self.rename_btn.setToolTip("重命名选中的标签")
        self.rename_btn.clicked.connect(self._on_rename)
        btn_layout.addWidget(self.rename_btn)

        self.merge_btn = QPushButton("🔗 合并")
        self.merge_btn.setToolTip("将选中的多个标签合并为一个")
        self.merge_btn.clicked.connect(self._on_merge)
        btn_layout.addWidget(self.merge_btn)

        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.setToolTip("从所有壁纸中删除选中的标签")
        self.delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _load_tags(self):
        """加载所有标签"""
        self.tag_list.clear()
        stats = db.get_tag_stats()
        for s in stats:
            item = QListWidgetItem(f"{s['name']}  ({s['count']} 张)")
            item.setData(Qt.UserRole, s["name"])
            self.tag_list.addItem(item)
        self.stats_label.setText(f"共 {len(stats)} 个标签")

    def _get_selected_tags(self) -> list[str]:
        """获取选中的标签名列表"""
        return [
            item.data(Qt.UserRole)
            for item in self.tag_list.selectedItems()
        ]

    def _on_rename(self):
        """重命名单个标签"""
        selected = self._get_selected_tags()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择一个标签")
            return
        if len(selected) > 1:
            QMessageBox.information(self, "提示", "重命名只能选择一个标签")
            return

        old_name = selected[0]
        new_name, ok = QInputDialog.getText(
            self, "重命名标签", f"将「{old_name}」重命名为：",
            QLineEdit.Normal, old_name,
        )
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return

        new_name = new_name.strip()
        count = db.rename_tag(old_name, new_name)
        QMessageBox.information(self, "完成", f"已重命名标签，影响 {count} 张壁纸")
        self._load_tags()
        self.tags_changed.emit()

    def _on_merge(self):
        """合并多个标签"""
        selected = self._get_selected_tags()
        if len(selected) < 2:
            QMessageBox.information(self, "提示", "请至少选择两个标签进行合并")
            return

        target_name, ok = QInputDialog.getText(
            self,
            "合并标签",
            f"将 {len(selected)} 个标签合并为：\n"
            f"（{', '.join(selected)}）",
            QLineEdit.Normal,
            selected[0],  # 默认使用第一个
        )
        if not ok or not target_name.strip():
            return

        target_name = target_name.strip()
        reply = QMessageBox.question(
            self,
            "确认合并",
            f"将以下标签合并为「{target_name}」：\n\n"
            f"{', '.join(selected)}\n\n"
            f"此操作不可撤销，确定吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        count = db.merge_tags(selected, target_name)
        QMessageBox.information(self, "完成", f"已合并标签，影响 {count} 张壁纸")
        self._load_tags()
        self.tags_changed.emit()

    def _on_delete(self):
        """删除标签"""
        selected = self._get_selected_tags()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要删除的标签")
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"将从所有壁纸中删除以下标签：\n\n"
            f"{', '.join(selected)}\n\n"
            f"此操作不可撤销，确定吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        total = 0
        for tag in selected:
            total += db.delete_tag(tag)

        QMessageBox.information(self, "完成", f"已删除 {len(selected)} 个标签，影响 {total} 张壁纸")
        self._load_tags()
        self.tags_changed.emit()
