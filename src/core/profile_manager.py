"""
Profile 隔离 — 子 Agent 上下文隔离管理

解决代可行等子 agent 的上下文污染问题：
- 每个子 agent 有独立的 profile（记忆/技能/偏好）
- 主 session 和子 session 上下文隔离
- 子 agent 只能访问自己的 profile，不能读写主 session 记忆
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

PROFILES_DIR = Path.home() / ".omc" / "profiles"


@dataclass
class AgentProfile:
    """Agent Profile — 隔离的上下文容器"""

    agent_id: str
    agent_name: str
    created_at: str
    # 隔离的记忆（只包含该 agent 相关的）
    memories: list[str] = field(default_factory=list)
    # 该 agent 可用的技能
    skills: list[str] = field(default_factory=list)
    # 该 agent 的偏好设置
    preferences: dict = field(default_factory=dict)
    # 执行历史（只记录该 agent 的任务）
    task_history: list[dict] = field(default_factory=list)
    # 父级 profile（用于继承）
    parent_profile: Optional[str] = None


class ProfileManager:
    """Profile 管理器"""

    def __init__(self):
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    def create_profile(
        self,
        agent_id: str,
        agent_name: str,
        parent_profile: Optional[str] = None,
    ) -> AgentProfile:
        """创建新的 agent profile"""
        profile = AgentProfile(
            agent_id=agent_id,
            agent_name=agent_name,
            created_at=datetime.now().isoformat(),
            parent_profile=parent_profile,
        )
        self._save_profile(profile)
        return profile

    def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """获取 agent profile"""
        filepath = PROFILES_DIR / f"{agent_id}.json"
        if not filepath.exists():
            return None

        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return AgentProfile(**data)
        except Exception:
            return None

    def update_profile(self, profile: AgentProfile) -> None:
        """更新 profile"""
        self._save_profile(profile)

    def add_memory(self, agent_id: str, memory: str) -> bool:
        """向 profile 添加记忆（隔离存储）"""
        profile = self.get_profile(agent_id)
        if not profile:
            return False

        profile.memories.append(f"[{datetime.now().isoformat()}] {memory}")
        # 限制记忆数量，防止膨胀
        if len(profile.memories) > 100:
            profile.memories = profile.memories[-100:]

        self._save_profile(profile)
        return True

    def add_task(self, agent_id: str, task: str, status: str) -> bool:
        """记录任务执行历史"""
        profile = self.get_profile(agent_id)
        if not profile:
            return False

        profile.task_history.append(
            {
                "task": task[:200],
                "status": status,
                "timestamp": datetime.now().isoformat(),
            }
        )
        # 限制历史数量
        if len(profile.task_history) > 50:
            profile.task_history = profile.task_history[-50:]

        self._save_profile(profile)
        return True

    def get_context_for_agent(self, agent_id: str) -> dict:
        """
        获取 agent 的隔离上下文（用于传递给子 agent）

        只包含：
        - 该 agent 的记忆
        - 该 agent 的技能
        - 该 agent 的偏好
        - 最近的任务历史

        不包含：
        - 主 session 的记忆
        - 其他 agent 的上下文
        """
        profile = self.get_profile(agent_id)
        if not profile:
            return {}

        return {
            "agent_name": profile.agent_name,
            "memories": profile.memories[-20:],  # 最近 20 条记忆
            "skills": profile.skills,
            "preferences": profile.preferences,
            "recent_tasks": profile.task_history[-10:],  # 最近 10 个任务
        }

    def list_profiles(self) -> list[AgentProfile]:
        """列出所有 profiles"""
        profiles = []
        for filepath in sorted(PROFILES_DIR.glob("*.json")):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                profiles.append(AgentProfile(**data))
            except Exception:
                continue
        return profiles

    def delete_profile(self, agent_id: str) -> bool:
        """删除 profile"""
        filepath = PROFILES_DIR / f"{agent_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def _save_profile(self, profile: AgentProfile) -> None:
        """保存 profile 到文件"""
        filepath = PROFILES_DIR / f"{profile.agent_id}.json"
        filepath.write_text(
            json.dumps(asdict(profile), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ===== 预定义 Profile =====

PREDEFINED_PROFILES = {
    "daikexing": {
        "name": "代可行",
        "skills": ["simple_research", "single_file_edit", "doc_generation"],
        "preferences": {
            "max_steps_per_task": 5,
            "max_files_per_batch": 2,
            "build_after_edit": True,
            "timeout_minutes": 15,
            "suitable_for": [
                "文档调研",
                "单文件简单修改",
                "代码格式化",
            ],
            "not_suitable_for": [
                "多文件重构",
                "复杂逻辑实现",
                "架构设计",
            ],
        },
    },
    "code_reviewer": {
        "name": "代码审查员",
        "skills": ["security_audit", "style_check", "best_practices"],
        "preferences": {
            "focus_areas": ["security", "performance", "readability"],
            "severity_levels": ["critical", "warning", "suggestion"],
        },
    },
    "test_writer": {
        "name": "测试工程师",
        "skills": ["unit_test", "integration_test", "coverage_analysis"],
        "preferences": {
            "test_framework": "pytest",
            "min_coverage": 80,
        },
    },
}


def create_predefined_profile(agent_type: str) -> Optional[AgentProfile]:
    """创建预定义 profile"""
    if agent_type not in PREDEFINED_PROFILES:
        return None

    config = cast(dict[str, Any], PREDEFINED_PROFILES[agent_type])
    manager = ProfileManager()

    profile = manager.create_profile(
        agent_id=f"{agent_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        agent_name=config["name"],
    )
    profile.skills = cast(list[str], config["skills"])
    profile.preferences = cast(dict[str, Any], config["preferences"])
    manager.update_profile(profile)

    return profile


def get_profile_summary(agent_id: str) -> str:
    """获取 profile 摘要（用于调试）"""
    manager = ProfileManager()
    profile = manager.get_profile(agent_id)

    if not profile:
        return f"Profile not found: {agent_id}"

    return (
        f"Agent: {profile.agent_name} ({profile.agent_id})\n"
        f"Created: {profile.created_at}\n"
        f"Memories: {len(profile.memories)}\n"
        f"Tasks: {len(profile.task_history)}\n"
        f"Skills: {', '.join(profile.skills) or 'None'}\n"
    )
