"""
长期记忆系统

三层架构：
1. ShortTermMemory - 当前会话上下文（内存 + 临时文件）
2. LongTermMemory - 项目偏好、常用模式（JSON 持久化）
3. LearningsMemory - 踩坑记录、最佳实践（Markdown）

功能：
- 会话结束自动总结沉淀
- 新会话自动召回相关记忆
- 手动触发记忆召回（搜索）
"""

from .manager import MemoryConfig, MemoryManager

__all__ = [
    "LearningsMemory",
    "LongTermMemory",
    "MemoryConfig",
    "MemoryManager",
    "ShortTermMemory",
]
