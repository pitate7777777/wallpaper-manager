"""搜索和过滤栏 - 增加目录管理、导入导出"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QComboBox,
    QPushButton, QCheckBox,
)
from PySide6.QtCore import Signal

from ui.theme import COLORS


class FilterBar(QWidget):
    """顶部过滤/搜索栏"""

    search_changed = Signal(str)
    type_changed = Signal(str)
    tag_changed = Signal(str)
    favorites_toggled = Signal(bool)
    order_changed = Signal(str)
    scan_clicked = Signal()
    dir_manager_clicked = Signal()
    export_clicked = Signal()
    import_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("filterBar")
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索壁纸标题或标签...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_input, 1)

        # 类型过滤
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部类型", "")
        self.type_combo.addItem("🎬 视频", "video")
        self.type_combo.addItem("🖼️ 场景", "scene")
        self.type_combo.addItem("🌐 网页", "web")
        self.type_combo.currentIndexChanged.connect(
            lambda _: self.type_changed.emit(self.type_combo.currentData())
        )
        layout.addWidget(self.type_combo)

        # 标签过滤
        self.tag_combo = QComboBox()
        self.tag_combo.addItem("全部标签", "")
        self.tag_combo.setMinimumWidth(100)
        self.tag_combo.currentIndexChanged.connect(
            lambda _: self.tag_changed.emit(self.tag_combo.currentData())
        )
        layout.addWidget(self.tag_combo)

        # 排序
        self.order_combo = QComboBox()
        self.order_combo.addItem("按标题", "title")
        self.order_combo.addItem("按类型", "type")
        self.order_combo.addItem("最近添加", "newest")
        self.order_combo.addItem("收藏优先", "favorite")
        self.order_combo.currentIndexChanged.connect(
            lambda _: self.order_changed.emit(self.order_combo.currentData())
        )
        layout.addWidget(self.order_combo)

        # 收藏过滤
        self.fav_check = QCheckBox("❤️ 仅收藏")
        self.fav_check.toggled.connect(self.favorites_toggled.emit)
        layout.addWidget(self.fav_check)

        # 分隔
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {COLORS['separator']};")
        sep.setFixedHeight(20)
        layout.addWidget(sep)

        # 导入导出
        self.export_btn = QPushButton("📤 导出")
        self.export_btn.setToolTip("导出收藏列表为 JSON")
        self.export_btn.clicked.connect(self.export_clicked.emit)
        layout.addWidget(self.export_btn)

        self.import_btn = QPushButton("📥 导入")
        self.import_btn.setToolTip("从 JSON 导入壁纸列表")
        self.import_btn.clicked.connect(self.import_clicked.emit)
        layout.addWidget(self.import_btn)

        # 目录管理
        self.dir_btn = QPushButton("📂 目录")
        self.dir_btn.setToolTip("管理多个壁纸目录")
        self.dir_btn.clicked.connect(self.dir_manager_clicked.emit)
        layout.addWidget(self.dir_btn)

        # 扫描按钮
        self.scan_btn = QPushButton("🔄 扫描")
        self.scan_btn.setObjectName("scanBtn")
        self.scan_btn.clicked.connect(self.scan_clicked.emit)
        layout.addWidget(self.scan_btn)

    def update_tags(self, tags: list[str]):
        """更新标签下拉列表"""
        current = self.tag_combo.currentData()
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("全部标签", "")
        for tag in tags:
            self.tag_combo.addItem(tag, tag)
        if current:
            idx = self.tag_combo.findData(current)
            if idx >= 0:
                self.tag_combo.setCurrentIndex(idx)
        self.tag_combo.blockSignals(False)
