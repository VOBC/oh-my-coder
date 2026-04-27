"""Skills 系统 - 插件化 Skill 框架

支持内置 Skill 和用户自定义 Skill（~/.omc/skills/）。
"""

from .registry import Skill, SkillRegistry, SkillResult, get_registry

__all__ = ["SkillRegistry", "Skill", "SkillResult", "get_registry"]
