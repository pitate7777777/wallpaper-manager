"""壁纸定时轮换模块

支持三种轮换模式:
- random: 随机轮换
- sequential: 顺序轮换
- favorite: 仅收藏壁纸轮换
"""

import logging
import random
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal, QTimer

logger = logging.getLogger(__name__)


class RotationWorker(QObject):
    """壁纸轮换控制器

    使用 QTimer 在主线程中定时触发轮换，通过信号通知 UI 更新。
    继承 QObject（而非 QThread），因为轮换逻辑不需要独立线程。
    """

    wallpaper_changed = Signal(str, str)  # wallpaper_id, title
    rotation_started = Signal(int, str)   # interval_minutes, mode
    rotation_stopped = Signal()
    error_occurred = Signal(str)          # error message

    def __init__(
        self,
        db_query_func: Callable,
        set_wallpaper_func: Callable,
        interval_minutes: int = 30,
        mode: str = "random",
        parent=None,
    ):
        """
        Args:
            db_query_func: 获取壁纸列表的函数，返回 Wallpaper 列表
            set_wallpaper_func: 设置壁纸的函数，接收 Wallpaper 对象
            interval_minutes: 轮换间隔（分钟）
            mode: 轮换模式 - "random" / "sequential" / "favorite"
            parent: 父对象
        """
        super().__init__(parent)
        self._db_query_func = db_query_func
        self._set_wallpaper_func = set_wallpaper_func
        self._interval_minutes = interval_minutes
        self._mode = mode
        self._running = False
        self._current_index = 0
        self._wallpaper_list = []
        self._timer: Optional[QTimer] = None

    @property
    def is_rotating(self) -> bool:
        """是否正在轮换"""
        return self._running

    @property
    def interval_minutes(self) -> int:
        """当前轮换间隔（分钟）"""
        return self._interval_minutes

    @property
    def mode(self) -> str:
        """当前轮换模式"""
        return self._mode

    def start_rotation(self, interval_minutes: int = None, mode: str = None):
        """开始轮换

        Args:
            interval_minutes: 轮换间隔（分钟），None 则使用当前值
            mode: 轮换模式，None 则使用当前值
        """
        if interval_minutes is not None:
            self._interval_minutes = max(1, interval_minutes)
        if mode is not None:
            self._mode = mode

        # 刷新壁纸列表
        self._refresh_wallpaper_list()

        if not self._wallpaper_list:
            self.error_occurred.emit("没有可用的壁纸进行轮换")
            return

        self._running = True
        self._current_index = 0

        # 使用 QTimer 而不是 QThread.sleep，这样不会阻塞 UI
        if self._timer is None:
            self._timer = QTimer()
            self._timer.timeout.connect(self._on_timer_tick)

        interval_ms = self._interval_minutes * 60 * 1000
        self._timer.start(interval_ms)

        logger.info(
            f"壁纸轮换已启动: 间隔={self._interval_minutes}分钟, "
            f"模式={self._mode}, 壁纸数={len(self._wallpaper_list)}"
        )
        self.rotation_started.emit(self._interval_minutes, self._mode)

        # 立即切换一次
        self.next_wallpaper()

    def stop_rotation(self):
        """停止轮换"""
        if self._timer:
            self._timer.stop()
        self._running = False
        logger.info("壁纸轮换已停止")
        self.rotation_stopped.emit()

    def next_wallpaper(self):
        """手动切换到下一张壁纸"""
        if not self._wallpaper_list:
            self._refresh_wallpaper_list()
        if not self._wallpaper_list:
            self.error_occurred.emit("没有可用的壁纸")
            return

        wallpaper = self._pick_next()
        if wallpaper is None:
            return

        try:
            self._set_wallpaper_func(wallpaper)
            title = getattr(wallpaper, "title", str(wallpaper))
            wp_id = str(getattr(wallpaper, "id", ""))
            logger.info(f"轮换壁纸: {title}")
            self.wallpaper_changed.emit(wp_id, title)
        except Exception as e:
            error_msg = f"设置壁纸失败: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

    def _on_timer_tick(self):
        """定时器回调"""
        if self._running:
            self.next_wallpaper()

    def _refresh_wallpaper_list(self):
        """刷新壁纸列表"""
        try:
            all_wallpapers = self._db_query_func()

            if self._mode == "favorite":
                self._wallpaper_list = [
                    wp for wp in all_wallpapers
                    if getattr(wp, "is_favorite", False)
                ]
            else:
                self._wallpaper_list = list(all_wallpapers)

            # 随机模式打乱顺序
            if self._mode == "random":
                random.shuffle(self._wallpaper_list)

            self._current_index = 0
            logger.debug(f"刷新壁纸列表: {len(self._wallpaper_list)} 张 (模式: {self._mode})")

        except Exception as e:
            logger.error(f"刷新壁纸列表失败: {e}")
            self._wallpaper_list = []

    def _pick_next(self):
        """选择下一张壁纸

        Returns:
            下一张壁纸对象，失败返回 None
        """
        if not self._wallpaper_list:
            return None

        if self._mode == "random":
            # 随机选择
            wallpaper = random.choice(self._wallpaper_list)
        elif self._mode == "sequential":
            # 顺序选择
            wallpaper = self._wallpaper_list[self._current_index % len(self._wallpaper_list)]
            self._current_index += 1
        elif self._mode == "favorite":
            # 收藏壁纸顺序轮换
            wallpaper = self._wallpaper_list[self._current_index % len(self._wallpaper_list)]
            self._current_index += 1
        else:
            # 默认随机
            wallpaper = random.choice(self._wallpaper_list)

        return wallpaper

    def cleanup(self):
        """清理资源"""
        self.stop_rotation()
        if self._timer:
            self._timer.deleteLater()
            self._timer = None
