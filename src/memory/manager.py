"""
记忆管理器 - 统一入口

整合三层记忆：
- ShortTermMemory（短期会话）
- LongTermMemory（项目偏好）
- LearningsMemory（学习记录）
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .short_term import ShortTermMemory, SessionContext
from .long_term import LongTermMemory, UserPreference, ProjectPreference
from .learnings import LearningsMemory, LearningEntry


@dataclass
class MemoryConfig:
    """记忆配置"""

    storage_dir: Path
    short_term_max_messages: int = 100
    short_term_max_age_hours: int = 24
    auto_save_interval: int = 300  # 5 分钟


class MemoryManager:
    """统一记忆管理器"""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self.short_term = ShortTermMemory(
            config.storage_dir, config.short_term_max_messages
        )
        self.long_term = LongTermMemory(config.storage_dir)
        self.learnings = LearningsMemory(config.storage_dir)

    @classmethod
    def from_project(cls, project_path: Path) -> "MemoryManager":
        """从项目路径创建"""
        storage_dir = project_path / ".omc" / "memory"
        return cls(MemoryConfig(storage_dir=storage_dir))

    @classmethod
    def from_home(cls) -> "MemoryManager":
        """从用户 home 目录创建（全局记忆）"""
        storage_dir = Path.home() / ".oh-my-coder" / "memory"
        return cls(MemoryConfig(storage_dir=storage_dir))

    # ========== Short Term ==========

    def create_session(
        self, project_path: Optional[Path] = None, task: Optional[str] = None
    ) -> SessionContext:
        """创建新会话"""
        return self.short_term.create_session(project_path, task)

    def get_current_session(self) -> Optional[SessionContext]:
        """获取当前会话"""
        return self.short_term.get_current_session()

    def save_current_session(self):
        """保存当前会话"""
        session = self.short_term.get_current_session()
        if session:
            self.short_term.save_session(session)

    # ========== Long Term ==========

    def get_user_prefs(self) -> UserPreference:
        """获取用户偏好"""
        return self.long_term.get_user_prefs()

    def update_user_prefs(self, **kwargs):
        """更新用户偏好"""
        self.long_term.update_user_prefs(**kwargs)

    def get_project_prefs(self, project_path: Path) -> ProjectPreference:
        """获取项目偏好"""
        return self.long_term.get_project_prefs(project_path)

    def update_project_prefs(self, project_path: Path, **kwargs):
        """更新项目偏好"""
        self.long_term.update_project_prefs(project_path, **kwargs)

    def add_recent_project(self, project_path: Path):
        """添加最近项目"""
        self.long_term.add_recent_project(project_path)

    def get_recent_projects(self, limit: int = 5) -> List[Path]:
        """获取最近项目"""
        return self.long_term.get_recent_projects(limit)

    # ========== Learnings ==========

    def add_learning(
        self,
        title: str,
        content: str,
        category: str = "note",
        tags: Optional[List[str]] = None,
        context: str = "",
    ) -> LearningEntry:
        """添加学习条目"""
        return self.learnings.add(title, content, category, tags, context)

    def search_learnings(
        self, query: str, category: Optional[str] = None
    ) -> List[LearningEntry]:
        """搜索学习记录"""
        return self.learnings.search(query, category)

    def get_learnings_by_category(self, category: str) -> List[LearningEntry]:
        """按类别获取学习记录"""
        return self.learnings.get_by_category(category)

    def get_recent_learnings(self, limit: int = 10) -> List[LearningEntry]:
        """获取最近学习记录"""
        return self.learnings.get_recent(limit)

    # ========== 综合 ==========

    def recall(self, query: str) -> Dict[str, Any]:
        """综合召回：搜索所有记忆层"""
        results = {
            "short_term": [],
            "long_term": [],
            "learnings": self.search_learnings(query),
        }

        # 搜索项目偏好
        project_prefs = list(self.long_term._projects.values())
        for prefs in project_prefs:
            if (
                query.lower() in prefs.name.lower()
                or query.lower() in prefs.notes.lower()
            ):
                results["long_term"].append(prefs.to_dict())

        return results
