"""
记忆管理器 - 统一入口

整合三层记忆：
- ShortTermMemory（短期会话）
- LongTermMemory（项目偏好）
- LearningsMemory（学习记录）

分层有限记忆设计（借鉴 Hermes Agent）：
- Tier 0（Tiny）：< 500 token，最重要的核心记忆
- Tier 1（精选）：< 2000 token，高价值条目
- Tier 2（Archive）：完整存档，无限存储
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .short_term import ShortTermMemory, SessionContext
from .long_term import LongTermMemory, UserPreference, ProjectPreference
from .learnings import LearningsMemory, LearningEntry

# 可选：tiktoken 用于精确 token 计算
try:
    import tiktoken

    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False


@dataclass
class MemoryConfig:
    """记忆配置"""

    storage_dir: Path
    short_term_max_messages: int = 100
    short_term_max_age_hours: int = 24
    auto_save_interval: int = 300  # 5 分钟
    # 分层记忆限制（token 数）
    tier0_max_tokens: int = 500
    tier1_max_tokens: int = 2000


class MemoryManager:
    """统一记忆管理器"""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self.short_term = ShortTermMemory(
            config.storage_dir, config.short_term_max_messages
        )
        self.long_term = LongTermMemory(config.storage_dir)
        self.learnings = LearningsMemory(config.storage_dir)
        self._enc = self._get_encoder()

    @staticmethod
    def _get_encoder():
        """获取 tokenizer，失败返回 None"""
        if not _HAS_TIKTOKEN:
            return None
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None

    def count_tokens(self, text: str) -> int:
        """计算 token 数"""
        if self._enc:
            return len(self._enc.encode(text))
        return len(text) // 4  # 回退估算

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

    # ========== 分层有限记忆（借鉴 Hermes Agent）==========

    def get_tier0_summary(self) -> str:
        """
        获取 Tier 0 记忆（< 500 token）。

        核心记忆：当前项目、最近任务、关键偏好。
        用于系统 Prompt 注入。
        """
        lines = []

        # 项目信息
        projects = self.long_term.get_recent_projects(limit=3)
        if projects:
            lines.append("## 最近项目")
            for p in projects:
                prefs = self.long_term.get_project_prefs(p)
                lines.append(
                    f"- {prefs.name or p.name}: {prefs.framework or prefs.language}"
                )

        # 用户偏好
        prefs = self.long_term.get_user_prefs()
        lines.append("\n## 用户偏好")
        lines.append(f"- 模型: {prefs.default_model}")
        lines.append(f"- 工作流: {prefs.default_workflow}")

        # 最近学习
        recent = self.learnings.get_recent(limit=3)
        if recent:
            lines.append("\n## 最近经验")
            for entry in recent:
                lines.append(f"- {entry.title}: {entry.content[:80]}")

        # 拼接并截断
        summary = "\n".join(lines)
        tokens = self.count_tokens(summary)
        if tokens > self.config.tier0_max_tokens:
            # 截断到 token 限制
            if self._enc:
                truncated = self._enc.decode(
                    self._enc.encode(summary)[: self.config.tier0_max_tokens]
                )
                return truncated
            return summary[: self.config.tier0_max_tokens * 4]
        return summary

    def get_tier1_summary(self, max_tokens: int = 2000) -> str:
        """
        获取 Tier 1 记忆（< 2000 token）。

        精选记忆：项目特定知识、常用命令、重要经验。
        用于上下文补充。
        """
        lines = []

        # 项目详情
        projects = self.long_term.get_recent_projects(limit=5)
        for p in projects:
            prefs = self.long_term.get_project_prefs(p)
            if prefs.notes:
                lines.append(f"## {prefs.name or p.name}")
                lines.append(prefs.notes[:200])

            if prefs.custom_commands:
                lines.append("### 常用命令")
                for alias, cmd in prefs.custom_commands.items():
                    lines.append(f"- {alias}: {cmd}")

        # 更多学习记录
        recent = self.learnings.get_recent(limit=10)
        for entry in recent:
            lines.append(f"## {entry.title}")
            lines.append(entry.content[:300])

        summary = "\n".join(lines)
        tokens = self.count_tokens(summary)
        if tokens > max_tokens:
            if self._enc:
                truncated = self._enc.decode(self._enc.encode(summary)[:max_tokens])
                return truncated
            return summary[: max_tokens * 4]
        return summary
