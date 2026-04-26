"""core.rotation_worker 单元测试"""
from unittest.mock import MagicMock, patch

import pytest

# Skip if PySide6 not available (e.g., headless CI)
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QCoreApplication
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

# Ensure QApplication exists for Qt tests
_app = None


def get_qapp():
    global _app
    if _app is None and HAS_PYSIDE6:
        _app = QApplication.instance() or QApplication([])
    return _app


@pytest.fixture(autouse=True)
def ensure_qapp():
    """确保 QApplication 存在"""
    if HAS_PYSIDE6:
        get_qapp()
    yield


@pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 not available")
class TestRotationWorkerInit:
    """初始化测试"""

    def test_default_init(self):
        from core.rotation_worker import RotationWorker

        mock_db = MagicMock(return_value=[])
        mock_set = MagicMock()
        worker = RotationWorker(mock_db, mock_set)

        assert worker.interval_minutes == 30
        assert worker.mode == "random"
        assert worker.is_rotating is False

    def test_custom_init(self):
        from core.rotation_worker import RotationWorker

        mock_db = MagicMock(return_value=[])
        mock_set = MagicMock()
        worker = RotationWorker(mock_db, mock_set, interval_minutes=15, mode="favorite")

        assert worker.interval_minutes == 15
        assert worker.mode == "favorite"
        assert worker.is_rotating is False


@pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 not available")
class TestRotationWorkerPickNext:
    """_pick_next 测试"""

    def test_pick_from_empty_list(self):
        from core.rotation_worker import RotationWorker

        mock_db = MagicMock(return_value=[])
        mock_set = MagicMock()
        worker = RotationWorker(mock_db, mock_set)

        worker._wallpaper_list = []
        result = worker._pick_next()
        assert result is None

    def test_pick_random(self):
        from core.rotation_worker import RotationWorker

        mock_db = MagicMock(return_value=[])
        mock_set = MagicMock()
        worker = RotationWorker(mock_db, mock_set, mode="random")

        mock_wp = MagicMock()
        worker._wallpaper_list = [mock_wp]
        result = worker._pick_next()
        assert result == mock_wp

    def test_pick_sequential(self):
        from core.rotation_worker import RotationWorker

        mock_db = MagicMock(return_value=[])
        mock_set = MagicMock()
        worker = RotationWorker(mock_db, mock_set, mode="sequential")

        wp1 = MagicMock()
        wp2 = MagicMock()
        wp3 = MagicMock()
        worker._wallpaper_list = [wp1, wp2, wp3]

        assert worker._pick_next() == wp1
        assert worker._pick_next() == wp2
        assert worker._pick_next() == wp3
        # Wraps around
        assert worker._pick_next() == wp1

    def test_pick_favorite(self):
        from core.rotation_worker import RotationWorker

        mock_db = MagicMock(return_value=[])
        mock_set = MagicMock()
        worker = RotationWorker(mock_db, mock_set, mode="favorite")

        wp1 = MagicMock()
        wp2 = MagicMock()
        worker._wallpaper_list = [wp1, wp2]

        assert worker._pick_next() == wp1
        assert worker._pick_next() == wp2
        assert worker._pick_next() == wp1


@pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 not available")
class TestRotationWorkerRefresh:
    """_refresh_wallpaper_list 测试"""

    def test_refresh_all_mode(self):
        from core.rotation_worker import RotationWorker

        wp1 = MagicMock()
        wp1.is_favorite = False
        wp2 = MagicMock()
        wp2.is_favorite = True
        mock_db = MagicMock(return_value=[wp1, wp2])
        mock_set = MagicMock()

        worker = RotationWorker(mock_db, mock_set, mode="random")
        worker._refresh_wallpaper_list()

        assert len(worker._wallpaper_list) == 2

    def test_refresh_favorite_mode(self):
        from core.rotation_worker import RotationWorker

        wp1 = MagicMock()
        wp1.is_favorite = False
        wp2 = MagicMock()
        wp2.is_favorite = True
        mock_db = MagicMock(return_value=[wp1, wp2])
        mock_set = MagicMock()

        worker = RotationWorker(mock_db, mock_set, mode="favorite")
        worker._refresh_wallpaper_list()

        assert len(worker._wallpaper_list) == 1
        assert worker._wallpaper_list[0] == wp2

    def test_refresh_with_db_error(self):
        from core.rotation_worker import RotationWorker

        mock_db = MagicMock(side_effect=Exception("DB error"))
        mock_set = MagicMock()

        worker = RotationWorker(mock_db, mock_set)
        worker._refresh_wallpaper_list()

        assert worker._wallpaper_list == []


@pytest.mark.skipif(not HAS_PYSIDE6, reason="PySide6 not available")
class TestRotationWorkerLifecycle:
    """生命周期测试"""

    def test_stop_without_start(self):
        """未启动时停止不应崩溃"""
        from core.rotation_worker import RotationWorker

        mock_db = MagicMock(return_value=[])
        mock_set = MagicMock()
        worker = RotationWorker(mock_db, mock_set)

        worker.stop_rotation()
        assert worker.is_rotating is False

    def test_cleanup(self):
        """cleanup 应停止轮换并清理资源"""
        from core.rotation_worker import RotationWorker

        mock_db = MagicMock(return_value=[])
        mock_set = MagicMock()
        worker = RotationWorker(mock_db, mock_set)

        worker.cleanup()
        assert worker.is_rotating is False

    def test_next_wallpaper_without_list(self):
        """没有壁纸列表时 next_wallpaper 应尝试刷新"""
        from core.rotation_worker import RotationWorker

        mock_wp = MagicMock()
        mock_wp.title = "Test"
        mock_wp.id = 1
        mock_db = MagicMock(return_value=[mock_wp])
        mock_set = MagicMock()

        worker = RotationWorker(mock_db, mock_set)
        worker._wallpaper_list = []
        worker.next_wallpaper()

        # 应该从 db 刷新了列表并调用了 set_wallpaper
        mock_set.assert_called_once_with(mock_wp)
