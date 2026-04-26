"""标签管理模块

提供标签重命名、合并、删除和统计的高级接口。
底层操作委托给 core.db 执行。
"""
import logging

from core import db

logger = logging.getLogger(__name__)


def rename_tag(old_name: str, new_name: str) -> int:
    """重命名标签，返回受影响的壁纸数量"""
    count = db.rename_tag(old_name, new_name)
    logger.info("重命名标签: %s → %s, 影响 %d 张壁纸", old_name, new_name, count)
    return count


def merge_tags(source_tags: list[str], target_tag: str) -> int:
    """合并多个标签到目标标签，返回受影响的壁纸数量"""
    count = db.merge_tags(source_tags, target_tag)
    logger.info("合并标签: %s → %s, 影响 %d 张壁纸", source_tags, target_tag, count)
    return count


def delete_tag(tag_name: str) -> int:
    """删除标签，返回受影响的壁纸数量"""
    count = db.delete_tag(tag_name)
    logger.info("删除标签: %s, 影响 %d 张壁纸", tag_name, count)
    return count


def get_tag_stats() -> list[dict]:
    """获取标签统计信息（使用次数）

    Returns:
        [{"name": "anime", "count": 42}, ...]
    """
    return db.get_tag_stats()
