"""搜索和过滤栏 - 增加目录管理、导入导出、壁纸轮换、主题切换、卡片尺寸、高级搜索"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QComboBox,
    QPushButton, QCheckBox, QMenu, QToolButton,
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal, QEvent, Qt

from ui.theme import COLORS


class FilterBar(QWidget):
    """顶部过滤/搜索栏"""

    search_changed = Signal(str)
    type_changed = Signal(str)
    tag_changed = Signal(str)
    tags_changed = Signal(list)          # 多选标签
    favorites_toggled = Signal(bool)
    order_changed = Signal(str)
    scan_clicked = Signal()
    dir_manager_clicked = Signal()
    export_clicked = Signal()
    import_clicked = Signal()
    rotation_toggled = Signal(bool, int, str)  # enabled, interval_minutes, mode
    theme_changed = Signal(str)                # theme_name
    card_size_changed = Signal(str)            # "small" / "medium" / "large"
    tag_manager_clicked = Signal()
    search_mode_changed = Signal(str)          # "simple" / "regex" / "exact"
    exclude_tags_changed = Signal(list)        # 排除标签列表

    # 搜索模式定义
    SEARCH_MODES = [
        ("simple", "🔤", "简单搜索（模糊匹配）"),
        ("regex",  "🔣", "正则搜索（支持正则表达式）"),
        ("exact",  "🎯", "精确搜索（完全匹配）"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("filterBar")
        self._rotation_enabled = False
        self._rotation_interval = 30  # 分钟
        self._rotation_mode = "random"
        self._search_mode_index = 0  # 0=simple, 1=regex, 2=exact
        self._selected_tags: list[str] = []
        self._excluded_tags: list[str] = []
        self._all_tags: list[str] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索壁纸标题或标签...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(180)
        self.search_input.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_input, 1)

        # 搜索模式切换按钮
        self.search_mode_btn = QToolButton()
        self.search_mode_btn.setObjectName("searchModeBtn")
        self._update_search_mode_btn()
        self.search_mode_btn.setCheckable(False)
        self.search_mode_btn.setAutoRaise(True)
        self.search_mode_btn.setFixedWidth(32)
        self.search_mode_btn.clicked.connect(self._cycle_search_mode)
        self.search_mode_btn.setToolTip(self.SEARCH_MODES[0][2])
        layout.addWidget(self.search_mode_btn)

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

        # 标签过滤（多选按钮 + 弹出面板）
        self.tag_btn = QPushButton("🏷️ 全部标签")
        self.tag_btn.setObjectName("tagBtn")
        self.tag_btn.setMinimumWidth(100)
        self.tag_btn.clicked.connect(self._show_tag_selector)
        self.tag_btn.setToolTip("点击选择标签（支持多选）")
        layout.addWidget(self.tag_btn)

        # 排除标签按钮
        self.exclude_tag_btn = QPushButton("🚫 排除标签")
        self.exclude_tag_btn.setObjectName("excludeTagBtn")
        self.exclude_tag_btn.setMinimumWidth(80)
        self.exclude_tag_btn.clicked.connect(self._show_exclude_tag_selector)
        self.exclude_tag_btn.setToolTip("点击选择要排除的标签")
        self.exclude_tag_btn.setVisible(False)  # 有选中标签时才显示
        layout.addWidget(self.exclude_tag_btn)

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

        # 分隔
        sep2 = QWidget()
        sep2.setFixedWidth(1)
        sep2.setStyleSheet(f"background: {COLORS['separator']};")
        sep2.setFixedHeight(20)
        layout.addWidget(sep2)

        # 壁纸轮换按钮
        self.rotation_btn = QPushButton("🔄 自动轮换")
        self.rotation_btn.setObjectName("rotationBtn")
        self.rotation_btn.setToolTip("点击开启/关闭壁纸自动轮换\n右键可设置轮换参数")
        self.rotation_btn.setCheckable(True)
        self.rotation_btn.setChecked(False)
        self.rotation_btn.clicked.connect(self._on_rotation_clicked)
        # 通过 eventFilter 拦截右键菜单
        self.rotation_btn.installEventFilter(self)
        layout.addWidget(self.rotation_btn)

        # 分隔
        sep3 = QWidget()
        sep3.setFixedWidth(1)
        sep3.setStyleSheet(f"background: {COLORS['separator']};")
        sep3.setFixedHeight(20)
        layout.addWidget(sep3)

        # 卡片尺寸
        self.size_combo = QComboBox()
        self.size_combo.addItem("📐 小", "small")
        self.size_combo.addItem("📐 中", "medium")
        self.size_combo.addItem("📐 大", "large")
        self.size_combo.setCurrentIndex(1)  # 默认 medium
        self.size_combo.setMinimumWidth(70)
        self.size_combo.currentIndexChanged.connect(
            lambda _: self.card_size_changed.emit(self.size_combo.currentData())
        )
        self.size_combo.setToolTip("缩略图卡片尺寸")
        layout.addWidget(self.size_combo)

        # 主题切换
        self.theme_btn = QPushButton("🌙 暗色")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setToolTip("点击切换亮/暗主题")
        self.theme_btn.clicked.connect(self._on_theme_toggle)
        layout.addWidget(self.theme_btn)

        # 标签管理
        self.tag_mgr_btn = QPushButton("🏷️ 标签")
        self.tag_mgr_btn.setObjectName("tagMgrBtn")
        self.tag_mgr_btn.setToolTip("管理标签：重命名、合并、删除")
        self.tag_mgr_btn.clicked.connect(self.tag_manager_clicked.emit)
        layout.addWidget(self.tag_mgr_btn)

    def _cycle_search_mode(self):
        """循环切换搜索模式"""
        self._search_mode_index = (self._search_mode_index + 1) % len(self.SEARCH_MODES)
        self._update_search_mode_btn()
        mode_key = self.SEARCH_MODES[self._search_mode_index][0]
        self.search_mode_changed.emit(mode_key)
        self.search_changed.emit(self.search_input.text())  # 触发重新搜索

    def _update_search_mode_btn(self):
        """更新搜索模式按钮显示"""
        mode = self.SEARCH_MODES[self._search_mode_index]
        self.search_mode_btn.setText(mode[1])
        self.search_mode_btn.setToolTip(mode[2])

    @property
    def search_mode(self) -> str:
        """当前搜索模式"""
        return self.SEARCH_MODES[self._search_mode_index][0]

    def _show_tag_selector(self):
        """显示标签多选弹出面板"""
        menu = QMenu(self)
        menu.setMinimumWidth(200)

        # 全部标签选项
        all_action = QAction("全部标签", menu)
        all_action.setCheckable(True)
        all_action.setChecked(not self._selected_tags)
        all_action.triggered.connect(lambda: self._set_selected_tags([]))
        menu.addAction(all_action)
        menu.addSeparator()

        # 标签列表
        for tag in self._all_tags:
            action = QAction(tag, menu)
            action.setCheckable(True)
            action.setChecked(tag in self._selected_tags)
            action.triggered.connect(lambda checked, t=tag: self._toggle_tag(t, checked))
            menu.addAction(action)

        if self._all_tags:
            menu.addSeparator()
            clear_action = QAction("清除选择", menu)
            clear_action.triggered.connect(lambda: self._set_selected_tags([]))
            menu.addAction(clear_action)

        menu.exec(self.tag_btn.mapToGlobal(self.tag_btn.rect().bottomLeft()))

    def _show_exclude_tag_selector(self):
        """显示排除标签多选弹出面板"""
        menu = QMenu(self)
        menu.setMinimumWidth(200)

        for tag in self._all_tags:
            action = QAction(tag, menu)
            action.setCheckable(True)
            action.setChecked(tag in self._excluded_tags)
            action.triggered.connect(lambda checked, t=tag: self._toggle_exclude_tag(t, checked))
            menu.addAction(action)

        if self._excluded_tags:
            menu.addSeparator()
            clear_action = QAction("清除排除", menu)
            clear_action.triggered.connect(lambda: self._set_excluded_tags([]))
            menu.addAction(clear_action)

        menu.exec(self.exclude_tag_btn.mapToGlobal(self.exclude_tag_btn.rect().bottomLeft()))

    def _toggle_tag(self, tag: str, checked: bool):
        """切换标签选中状态"""
        if checked:
            if tag not in self._selected_tags:
                self._selected_tags.append(tag)
        else:
            self._selected_tags = [t for t in self._selected_tags if t != tag]
        self._update_tag_btn_text()
        self.tags_changed.emit(self._selected_tags)

    def _toggle_exclude_tag(self, tag: str, checked: bool):
        """切换排除标签状态"""
        if checked:
            if tag not in self._excluded_tags:
                self._excluded_tags.append(tag)
        else:
            self._excluded_tags = [t for t in self._excluded_tags if t != tag]
        self._update_exclude_btn_text()
        self.exclude_tags_changed.emit(self._excluded_tags)

    def _set_selected_tags(self, tags: list[str]):
        """设置选中的标签"""
        self._selected_tags = tags
        self._update_tag_btn_text()
        self.tags_changed.emit(self._selected_tags)

    def _set_excluded_tags(self, tags: list[str]):
        """设置排除的标签"""
        self._excluded_tags = tags
        self._update_exclude_btn_text()
        self.exclude_tags_changed.emit(self._excluded_tags)

    def _update_tag_btn_text(self):
        """更新标签按钮文本"""
        if not self._selected_tags:
            self.tag_btn.setText("🏷️ 全部标签")
        elif len(self._selected_tags) == 1:
            self.tag_btn.setText(f"🏷️ {self._selected_tags[0]}")
        else:
            self.tag_btn.setText(f"🏷️ {len(self._selected_tags)} 个标签")
        # 有选中标签时显示排除按钮
        self.exclude_tag_btn.setVisible(bool(self._selected_tags))

    def _update_exclude_btn_text(self):
        """更新排除标签按钮文本"""
        if not self._excluded_tags:
            self.exclude_tag_btn.setText("🚫 排除标签")
        elif len(self._excluded_tags) == 1:
            self.exclude_tag_btn.setText(f"🚫 {self._excluded_tags[0]}")
        else:
            self.exclude_tag_btn.setText(f"🚫 排除 {len(self._excluded_tags)} 个")

    def get_selected_tags(self) -> list[str]:
        """获取当前选中的标签"""
        return self._selected_tags.copy()

    def get_excluded_tags(self) -> list[str]:
        """获取当前排除的标签"""
        return self._excluded_tags.copy()

    def eventFilter(self, obj, event):
        """处理轮换按钮的右键菜单"""
        if obj is self.rotation_btn and event.type() == QEvent.ContextMenu:
            self._show_rotation_menu(event.globalPos())
            return True
        return super().eventFilter(obj, event)

    def _on_rotation_clicked(self):
        """轮换按钮点击"""
        self._rotation_enabled = self.rotation_btn.isChecked()
        self.rotation_toggled.emit(
            self._rotation_enabled,
            self._rotation_interval,
            self._rotation_mode,
        )
        self._update_rotation_btn_text()

    def _show_rotation_menu(self, pos):
        """显示轮换设置菜单"""
        menu = QMenu(self)

        # 间隔时间
        interval_menu = menu.addMenu("⏱️ 轮换间隔")
        for minutes, label in [
            (5, "5 分钟"),
            (15, "15 分钟"),
            (30, "30 分钟"),
            (60, "1 小时"),
            (120, "2 小时"),
        ]:
            action = QAction(label, interval_menu)
            action.setCheckable(True)
            action.setChecked(self._rotation_interval == minutes)
            action.triggered.connect(lambda checked, m=minutes: self._set_rotation_interval(m))
            interval_menu.addAction(action)

        menu.addSeparator()

        # 轮换模式
        mode_menu = menu.addMenu("🎲 轮换模式")
        for mode, label in [
            ("random", "🔀 随机"),
            ("sequential", "📋 顺序"),
            ("favorite", "❤️ 仅收藏"),
        ]:
            action = QAction(label, mode_menu)
            action.setCheckable(True)
            action.setChecked(self._rotation_mode == mode)
            action.triggered.connect(lambda checked, m=mode: self._set_rotation_mode(m))
            mode_menu.addAction(action)

        menu.exec(pos)

    def _set_rotation_interval(self, minutes: int):
        """设置轮换间隔"""
        self._rotation_interval = minutes
        if self._rotation_enabled:
            self.rotation_toggled.emit(True, self._rotation_interval, self._rotation_mode)
        self._update_rotation_btn_text()

    def _set_rotation_mode(self, mode: str):
        """设置轮换模式"""
        self._rotation_mode = mode
        if self._rotation_enabled:
            self.rotation_toggled.emit(True, self._rotation_interval, self._rotation_mode)
        self._update_rotation_btn_text()

    def _update_rotation_btn_text(self):
        """更新轮换按钮文本"""
        if self._rotation_enabled:
            mode_names = {"random": "随机", "sequential": "顺序", "favorite": "收藏"}
            mode_name = mode_names.get(self._rotation_mode, self._rotation_mode)
            self.rotation_btn.setText(f"🔄 轮换中 ({self._rotation_interval}分/{mode_name})")
            self.rotation_btn.setChecked(True)
        else:
            self.rotation_btn.setText("🔄 自动轮换")
            self.rotation_btn.setChecked(False)

    def _on_theme_toggle(self):
        """切换亮/暗主题"""
        from ui.theme import get_current_theme_name
        current = get_current_theme_name()
        new_theme = "light" if current == "dark" else "dark"
        self.theme_btn.setText("☀️ 亮色" if new_theme == "light" else "🌙 暗色")
        self.theme_changed.emit(new_theme)

    def set_theme_display(self, theme_name: str):
        """设置主题按钮显示状态（外部调用）"""
        self.theme_btn.setText("☀️ 亮色" if theme_name == "light" else "🌙 暗色")

    def set_card_size(self, size: str):
        """设置卡片尺寸下拉框（外部调用）"""
        idx = self.size_combo.findData(size)
        if idx >= 0:
            self.size_combo.setCurrentIndex(idx)

    def update_tags(self, tags: list[str]):
        """更新标签列表（供多选弹出面板使用）"""
        self._all_tags = tags
