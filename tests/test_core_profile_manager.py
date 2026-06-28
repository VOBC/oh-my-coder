"""
测试 Profile 隔离管理器 (src/core/profile_manager.py)

覆盖 AgentProfile 数据类和 ProfileManager 的所有方法。
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.core.profile_manager import (
    AgentProfile,
    PREDEFINED_PROFILES,
    ProfileManager,
    PROFILES_DIR,
    create_predefined_profile,
    get_profile_summary,
)


@pytest.fixture
def tmp_profile_dir(tmp_path: Path) -> ProfileManager:
    """使用临时目录的 ProfileManager，避免污染真实 ~/.omc/"""
    # 临时替换 PROFILES_DIR 效果：通过 monkeypatch 或实例化时覆盖
    manager = ProfileManager()
    # 让 manager 写入 tmp_path（需要 patch PROFILES_DIR）
    return manager


@pytest.fixture
def profile_manager(tmp_path: Path, monkeypatch) -> ProfileManager:
    """ProfileManager with temp PROFILES_DIR"""
    temp_dir = tmp_path / "profiles"
    temp_dir.mkdir()
    monkeypatch.setattr("src.core.profile_manager.PROFILES_DIR", temp_dir)
    return ProfileManager()


class TestAgentProfile:
    """AgentProfile 数据类测试"""

    def test_create_profile_basic(self):
        profile = AgentProfile(
            agent_id="test-001",
            agent_name="TestAgent",
            created_at="2026-01-01T00:00:00",
        )
        assert profile.agent_id == "test-001"
        assert profile.agent_name == "TestAgent"
        assert profile.memories == []
        assert profile.skills == []
        assert profile.preferences == {}
        assert profile.task_history == []
        assert profile.parent_profile is None

    def test_profile_with_parent(self):
        profile = AgentProfile(
            agent_id="child-001",
            agent_name="ChildAgent",
            created_at="2026-01-01T00:00:00",
            parent_profile="parent-001",
        )
        assert profile.parent_profile == "parent-001"


class TestProfileManagerCreate:
    """ProfileManager 创建 / 持久化测试"""

    def test_create_profile(self, profile_manager: ProfileManager):
        profile = profile_manager.create_profile(
            agent_id="agent-new",
            agent_name="New Agent",
        )
        assert profile.agent_id == "agent-new"
        assert profile.agent_name == "New Agent"
        assert profile.created_at != ""

    def test_create_profile_with_parent(self, profile_manager: ProfileManager):
        profile = profile_manager.create_profile(
            agent_id="child-agent",
            agent_name="Child",
            parent_profile="parent-agent",
        )
        assert profile.parent_profile == "parent-agent"

    def test_create_and_get_profile(self, profile_manager: ProfileManager):
        profile_manager.create_profile("fetch-test", "Fetch Test Agent")
        fetched = profile_manager.get_profile("fetch-test")
        assert fetched is not None
        assert fetched.agent_id == "fetch-test"
        assert fetched.agent_name == "Fetch Test Agent"

    def test_get_nonexistent_profile(self, profile_manager: ProfileManager):
        result = profile_manager.get_profile("no-such-agent")
        assert result is None

    def test_profile_persistence(self, tmp_path: Path, monkeypatch):
        """跨实例访问同一目录时数据保持"""
        temp_dir = tmp_path / "profiles"
        temp_dir.mkdir()
        monkeypatch.setattr("src.core.profile_manager.PROFILES_DIR", temp_dir)

        mgr1 = ProfileManager()
        mgr1.create_profile("persist", "Persistent Agent")

        mgr2 = ProfileManager()
        fetched = mgr2.get_profile("persist")
        assert fetched is not None
        assert fetched.agent_name == "Persistent Agent"


class TestProfileManagerUpdate:
    """ProfileManager 更新测试"""

    def test_update_profile(self, profile_manager: ProfileManager):
        profile_manager.create_profile("update-test", "Original Name")
        profile = profile_manager.get_profile("update-test")
        profile.preferences["theme"] = "dark"
        profile_manager.update_profile(profile)

        restored = profile_manager.get_profile("update-test")
        assert restored.preferences["theme"] == "dark"

    def test_add_memory(self, profile_manager: ProfileManager):
        profile_manager.create_profile("mem-agent", "Memory Agent")
        result = profile_manager.add_memory("mem-agent", "记住这个重要的决策")
        assert result is True

        profile = profile_manager.get_profile("mem-agent")
        assert len(profile.memories) >= 1
        assert "记住这个重要的决策" in profile.memories[-1]

    def test_add_memory_nonexistent_agent(self, profile_manager: ProfileManager):
        result = profile_manager.add_memory("no-such-id", "memory")
        assert result is False

    def test_add_memory_limit_100(self, profile_manager: ProfileManager):
        profile_manager.create_profile("limit-test", "Limit Test")
        for i in range(120):
            profile_manager.add_memory("limit-test", f"memory {i}")

        profile = profile_manager.get_profile("limit-test")
        # 应该保留最近 100 条
        assert len(profile.memories) <= 100

    def test_add_task(self, profile_manager: ProfileManager):
        profile_manager.create_profile("task-agent", "Task Agent")
        result = profile_manager.add_task("task-agent", "完成代码审查", "completed")
        assert result is True

        profile = profile_manager.get_profile("task-agent")
        assert len(profile.task_history) == 1
        assert profile.task_history[0]["task"] == "完成代码审查"
        assert profile.task_history[0]["status"] == "completed"
        assert "timestamp" in profile.task_history[0]

    def test_add_task_nonexistent(self, profile_manager: ProfileManager):
        result = profile_manager.add_task("no-such-id", "task", "pending")
        assert result is False

    def test_add_task_limit_50(self, profile_manager: ProfileManager):
        profile_manager.create_profile("task-limit", "Task Limit")
        for i in range(60):
            profile_manager.add_task("task-limit", f"task {i}", "done")

        profile = profile_manager.get_profile("task-limit")
        assert len(profile.task_history) <= 50


class TestProfileManagerContext:
    """get_context_for_agent 测试"""

    def test_get_context_for_agent(self, profile_manager: ProfileManager):
        profile_manager.create_profile("ctx-agent", "Context Agent")
        profile_manager.add_memory("ctx-agent", "记得用 pytest")
        profile_manager.add_task("ctx-agent", "review 代码", "done")

        profile = profile_manager.get_profile("ctx-agent")
        profile.skills = ["code-review", "security"]
        profile.preferences = {"max_tokens": 8000}
        profile_manager.update_profile(profile)

        ctx = profile_manager.get_context_for_agent("ctx-agent")
        assert ctx["agent_name"] == "Context Agent"
        assert "记得用 pytest" in ctx["memories"][-1]
        assert "code-review" in ctx["skills"]
        assert ctx["preferences"]["max_tokens"] == 8000
        assert len(ctx["recent_tasks"]) == 1

    def test_get_context_for_nonexistent(self, profile_manager: ProfileManager):
        ctx = profile_manager.get_context_for_agent("no-such")
        assert ctx == {}


class TestProfileManagerListDelete:
    """列表和删除测试"""

    def test_list_profiles_empty(self, profile_manager: ProfileManager):
        profiles = profile_manager.list_profiles()
        assert profiles == []

    def test_list_profiles(self, profile_manager: ProfileManager):
        profile_manager.create_profile("list-1", "Agent 1")
        profile_manager.create_profile("list-2", "Agent 2")
        profiles = profile_manager.list_profiles()
        assert len(profiles) == 2
        ids = {p.agent_id for p in profiles}
        assert ids == {"list-1", "list-2"}

    def test_delete_profile(self, profile_manager: ProfileManager):
        profile_manager.create_profile("delete-me", "Delete Me")
        assert profile_manager.get_profile("delete-me") is not None
        assert profile_manager.delete_profile("delete-me") is True
        assert profile_manager.get_profile("delete-me") is None

    def test_delete_nonexistent(self, profile_manager: ProfileManager):
        assert profile_manager.delete_profile("no-such") is False


class TestPredefinedProfiles:
    """预定义 Profile 测试"""

    def test_predefined_profiles_exist(self):
        assert "daikexing" in PREDEFINED_PROFILES
        assert "code_reviewer" in PREDEFINED_PROFILES
        assert "test_writer" in PREDEFINED_PROFILES

    def test_daikexing_structure(self):
        daikexing = PREDEFINED_PROFILES["daikexing"]
        assert daikexing["name"] == "代可行"
        assert "skills" in daikexing
        assert "preferences" in daikexing

    def test_create_predefined_profile(self, tmp_path: Path, monkeypatch):
        temp_dir = tmp_path / "profiles"
        temp_dir.mkdir()
        monkeypatch.setattr("src.core.profile_manager.PROFILES_DIR", temp_dir)

        profile = create_predefined_profile("daikexing")
        assert profile is not None
        assert profile.agent_name == "代可行"
        assert len(profile.skills) > 0
        assert profile.preferences.get("max_steps_per_task") == 5

    def test_create_predefined_unknown_type(self, tmp_path: Path, monkeypatch):
        temp_dir = tmp_path / "profiles"
        temp_dir.mkdir()
        monkeypatch.setattr("src.core.profile_manager.PROFILES_DIR", temp_dir)

        result = create_predefined_profile("nonexistent-agent-type")
        assert result is None


class TestGetProfileSummary:
    """get_profile_summary 测试"""

    def test_summary_nonexistent(self, tmp_path: Path, monkeypatch):
        temp_dir = tmp_path / "profiles"
        temp_dir.mkdir()
        monkeypatch.setattr("src.core.profile_manager.PROFILES_DIR", temp_dir)

        summary = get_profile_summary("no-such-agent")
        assert "not found" in summary.lower()

    def test_summary_existing(self, tmp_path: Path, monkeypatch):
        temp_dir = tmp_path / "profiles"
        temp_dir.mkdir()
        monkeypatch.setattr("src.core.profile_manager.PROFILES_DIR", temp_dir)

        ProfileManager().create_profile("summary-agent", "Summary Agent")
        summary = get_profile_summary("summary-agent")
        assert "summary-agent" in summary
        assert "Summary Agent" in summary
        assert "Memories:" in summary
        assert "Tasks:" in summary
