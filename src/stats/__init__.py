"""
项目文件统计模块。

提供文件遍历、分类统计、排除规则等功能。
"""

from .counter import count_files
from .models import FileStats, StatsResult

__all__ = [
    "count_files",
    "FileStats",
    "StatsResult",
]