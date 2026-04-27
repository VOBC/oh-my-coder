from __future__ import annotations
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
from typing import Any

from .auto_compact import AutoCompact, CompactResult
from .learnings import LearningEntry, LearningsMemory
from .long_term import LongTermMemory, ProjectPreference, UserPreference
from .short_term import SessionContext, ShortTermMemory

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
    # 自动压缩配置
    compact_threshold: float = 0.85
    warning_threshold: float = 0.70


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
        self.auto_compact = AutoCompact(
            self,
            compact_threshold=config.compact_threshold,
            warning_threshold=config.warning_threshold,
        )

    @staticmethod
    def _get_encoder() -> str | None:
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
        return int(len(text) / 2.5)  # 回退估算：英文~0.4 token/词

    def auto_compact_check(
        self,
        session: SessionContext,
        provider: str = "",
        model: str = "",
    ) -> CompactResult:
        """检查并执行自动压缩

        Args:
            session: 当前会话上下文
            provider: 模型提供商
            model: 模型名称

        Returns:
            CompactResult: 压缩结果
        """
        return self.auto_compact.check_and_compact(session, provider, model)

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
        self, project_path: Path | None = None, task: str | None = None
    ) -> SessionContext:
        """创建新会话"""
        return self.short_term.create_session(project_path, task)

    def get_current_session(self) -> SessionContext | None:
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

    def get_recent_projects(self, limit: int = 5) -> list[Path]:
        """获取最近项目"""
        return self.long_term.get_recent_projects(limit)

    # ========== Learnings ==========

    def add_learning(
        self,
        title: str,
        content: str,
        category: str = "note",
        tags: list[str] | None = None,
        context: str = "",
    ) -> LearningEntry:
        """添加学习条目"""
        return self.learnings.add(title, content, category, tags, context)

    def search_learnings(
        self, query: str, category: str | None = None
    ) -> list[LearningEntry]:
        """搜索学习记录"""
        return self.learnings.search(query, category)

    def get_learnings_by_category(self, category: str) -> list[LearningEntry]:
        """按类别获取学习记录"""
        return self.learnings.get_by_category(category)

    def get_recent_learnings(self, limit: int = 10) -> list[LearningEntry]:
        """获取最近学习记录"""
        return self.learnings.get_recent(limit)

    # ========== 综合 ==========

    def recall(self, query: str) -> dict[str, Any]:
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
            lines.extend([f"- {entry.title}: {entry.content[:80]}" for entry in recent])

        # 拼接并截断
        summary = "\n".join(lines)
        tokens = self.count_tokens(summary)
        if tokens > self.config.tier0_max_tokens:
            # 截断到 token 限制
            if self._enc:
                return self._enc.decode(
                    self._enc.encode(summary)[: self.config.tier0_max_tokens]
                )
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
                return self._enc.decode(self._enc.encode(summary)[:max_tokens])
            return summary[: max_tokens * 4]
        return summary

    def get_tier2_archive(self) -> str:
        """
        获取 Tier 2 完整存档（无 token 限制）。

        完整记忆：所有项目、所有学习记录、所有偏好。
        用于导出、搜索、审计。
        """
        lines = []

        # 用户偏好
        prefs = self.long_term.get_user_prefs()
        lines.append("## 用户偏好")
        lines.append(f"- 模型: {prefs.default_model}")
        lines.append(f"- 工作流: {prefs.default_workflow}")
        lines.append(f"- 主题: {prefs.theme}")
        lines.append(f"- 编辑器: {prefs.editor}")
        lines.append(f"- Shell: {prefs.shell}")
        lines.append("")

        # 所有项目
        projects = self.long_term.get_recent_projects(limit=20)
        if projects:
            lines.append("## 项目列表")
            for p in projects:
                prefs_p = self.long_term.get_project_prefs(p)
                lines.append(f"### {prefs_p.name or p.name}")
                lines.append(f"- 路径: {p}")
                lines.append(f"- 框架: {prefs_p.framework or '—'}")
                lines.append(f"- 语言: {prefs_p.language or '—'}")
                if prefs_p.notes:
                    lines.append(f"- 备注: {prefs_p.notes[:300]}")
                if prefs_p.custom_commands:
                    lines.append("- 常用命令:")
                    for alias, cmd in prefs_p.custom_commands.items():
                        lines.append(f"  - {alias}: {cmd}")
                lines.append("")

        # 所有学习记录
        all_learnings = self.learnings.get_recent(limit=50)
        if all_learnings:
            lines.append("## 学习记录")
            for entry in all_learnings:
                lines.append(f"### {entry.title} [{entry.category}]")
                lines.append(entry.content[:500])
                if entry.tags:
                    lines.append(f"标签: {', '.join(entry.tags)}")
                lines.append("")

        return "\n".join(lines)

    def get_memory_stats(self) -> dict[str, Any]:
        """获取记忆统计信息"""
        projects = self.long_term.get_recent_projects(limit=100)
        all_learnings = self.learnings.get_recent(limit=1000)

        tier0 = self.get_tier0_summary()
        tier1 = self.get_tier1_summary()

        return {
            "projects_count": len(projects),
            "learnings_count": len(all_learnings),
            "tier0_tokens": self.count_tokens(tier0),
            "tier1_tokens": self.count_tokens(tier1),
            "categories": list(set(e.category for e in all_learnings)),
        }
