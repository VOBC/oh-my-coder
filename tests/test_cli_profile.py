"""
测试 cli_profile.py — Profile 管理命令

使用 CliRunner + mock 隔离外部依赖（文件系统）。
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.commands.cli_profile import app
from src.core.profile_manager import (
    PREDEFINED_PROFILES,
    AgentProfile,
)

runner = CliRunner()


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def mock_profile():
    """返回一个标准的 AgentProfile 供复用"""
    return AgentProfile(
        agent_id="agent-001",
        agent_name="TestAgent",
        created_at="2024-01-01T00:00:00",
        memories=["记忆1", "记忆2"],
        skills=["skill_a", "skill_b"],
        preferences={"theme": "dark"},
        task_history=[
            {"task": "任务A", "status": "completed", "timestamp": "2024-01-01T01:00:00"},
            {"task": "任务B", "status": "failed", "timestamp": "2024-01-01T02:00:00"},
        ],
    )


@pytest.fixture
def mock_context(mock_profile):
    """返回 get_context_for_agent 的典型输出"""
    return {
        "agent_name": mock_profile.agent_name,
        "memories": mock_profile.memories[-20:],
        "skills": mock_profile.skills,
        "preferences": mock_profile.preferences,
        "recent_tasks": mock_profile.task_history[-10:],
    }


# ===========================================================================
# create 命令
# ===========================================================================

class TestCreateProfile:
    def test_create_profile_success(self):
        """无模板，正常创建新 profile"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.get_profile.return_value = None  # 不存在

            created = AgentProfile(
                agent_id="new-agent",
                agent_name="NewAgent",
                created_at="2024-01-01T00:00:00",
            )
            instance.create_profile.return_value = created

            result = runner.invoke(app, ["create", "new-agent", "-n", "NewAgent"])

            assert result.exit_code == 0
            assert "Profile 创建成功" in result.output
            instance.create_profile.assert_called_once_with("new-agent", "NewAgent")

    def test_create_profile_already_exists(self):
        """profile 已存在时返回错误"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.get_profile.return_value = MagicMock()  # 已存在

            result = runner.invoke(app, ["create", "existing-agent", "-n", "Existing"])

            assert result.exit_code == 1
            assert "Profile 已存在" in result.output

    def test_create_profile_with_unknown_template(self):
        """指定不存在的模板时报错"""
        result = runner.invoke(
            app, ["create", "agent-x", "-n", "X", "-t", "nonexistent_template"]
        )
        assert result.exit_code == 1
        assert "未知模板" in result.output

    def test_create_profile_with_valid_template(self):
        """使用有效预定义模板创建 profile"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr, \
             patch("src.commands.cli_profile.create_predefined_profile") as mock_create:
            instance = MockMgr.return_value

            tmpl_profile = AgentProfile(
                agent_id="daikexing-20240101000000",
                agent_name="代可行",
                created_at="2024-01-01T00:00:00",
                skills=["simple_research"],
                preferences={"max_steps_per_task": 5},
            )
            mock_create.return_value = tmpl_profile

            result = runner.invoke(
                app, ["create", "my-agent", "-n", "MyAgent", "-t", "daikexing"]
            )

            assert result.exit_code == 0
            assert "Profile 创建成功" in result.output
            mock_create.assert_called_once_with("daikexing")
            # 验证 ID 和名称被覆盖
            assert tmpl_profile.agent_id == "my-agent"
            assert tmpl_profile.agent_name == "MyAgent"
            instance.update_profile.assert_called_once_with(tmpl_profile)


# ===========================================================================
# list 命令
# ===========================================================================

class TestListProfiles:
    def test_list_profiles_empty(self):
        """没有 profile 时提示无内容"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.list_profiles.return_value = []

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "没有 Profile" in result.output

    def test_list_profiles_with_data(self, mock_profile):
        """有 profile 时渲染表格"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.list_profiles.return_value = [mock_profile]

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "Agent Profiles" in result.output
            assert "TestAgent" in result.output


# ===========================================================================
# show 命令
# ===========================================================================

class TestShowProfile:
    def test_show_profile_exists(self):
        """profile 存在时显示摘要"""
        with patch("src.commands.cli_profile.get_profile_summary") as mock_summary:
            mock_summary.return_value = "Agent: TestAgent (agent-001)\nCreated: 2024-01-01T00:00:00\nMemories: 2\nTasks: 2\nSkills: skill_a, skill_b"

            result = runner.invoke(app, ["show", "agent-001"])

            assert result.exit_code == 0
            mock_summary.assert_called_once_with("agent-001")

    def test_show_profile_not_found(self):
        """profile 不存在时 get_profile_summary 返回提示文本"""
        with patch("src.commands.cli_profile.get_profile_summary") as mock_summary:
            mock_summary.return_value = "Profile not found: nonexistent"

            result = runner.invoke(app, ["show", "nonexistent"])

            assert result.exit_code == 0
            assert "not found" in result.output.lower()


# ===========================================================================
# context 命令
# ===========================================================================

class TestShowContext:
    def test_context_exists(self, mock_context):
        """context 存在时渲染隔离上下文"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.get_context_for_agent.return_value = mock_context

            result = runner.invoke(app, ["context", "agent-001"])

            assert result.exit_code == 0
            assert "Agent Context" in result.output or "TestAgent" in result.output

    def test_context_not_found(self):
        """profile 不存在时返回错误"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.get_context_for_agent.return_value = {}

            result = runner.invoke(app, ["context", "ghost-agent"])

            assert result.exit_code == 1
            assert "Profile 不存在" in result.output


# ===========================================================================
# add-memory 命令
# ===========================================================================

class TestAddMemory:
    def test_add_memory_success(self):
        """成功添加记忆"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.add_memory.return_value = True

            result = runner.invoke(app, ["add-memory", "agent-001", "这是一条新记忆"])

            assert result.exit_code == 0
            assert "记忆已添加" in result.output
            instance.add_memory.assert_called_once_with("agent-001", "这是一条新记忆")

    def test_add_memory_profile_not_found(self):
        """profile 不存在时返回错误"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.add_memory.return_value = False

            result = runner.invoke(app, ["add-memory", "ghost-agent", "记忆"])

            assert result.exit_code == 1
            assert "Profile 不存在" in result.output


# ===========================================================================
# add-task 命令
# ===========================================================================

class TestAddTask:
    def test_add_task_success(self):
        """成功记录任务"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.add_task.return_value = True

            result = runner.invoke(app, ["add-task", "agent-001", "完成代码审查", "-s", "completed"])

            assert result.exit_code == 0
            assert "任务已记录" in result.output
            instance.add_task.assert_called_once_with("agent-001", "完成代码审查", "completed")

    def test_add_task_with_different_status(self):
        """使用非默认状态值"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.add_task.return_value = True

            result = runner.invoke(app, ["add-task", "agent-001", "任务B", "-s", "failed"])

            assert result.exit_code == 0
            instance.add_task.assert_called_once_with("agent-001", "任务B", "failed")

    def test_add_task_profile_not_found(self):
        """profile 不存在时返回错误"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.add_task.return_value = False

            result = runner.invoke(app, ["add-task", "ghost", "任务"])

            assert result.exit_code == 1
            assert "Profile 不存在" in result.output


# ===========================================================================
# delete 命令
# ===========================================================================

class TestDeleteProfile:
    def test_delete_success(self):
        """成功删除 profile"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.delete_profile.return_value = True

            result = runner.invoke(app, ["delete", "agent-001"])

            assert result.exit_code == 0
            assert "已删除" in result.output
            instance.delete_profile.assert_called_once_with("agent-001")

    def test_delete_not_found(self):
        """profile 不存在时返回错误"""
        with patch("src.commands.cli_profile.ProfileManager") as MockMgr:
            instance = MockMgr.return_value
            instance.delete_profile.return_value = False

            result = runner.invoke(app, ["delete", "ghost-agent"])

            assert result.exit_code == 1
            assert "Profile 不存在" in result.output


# ===========================================================================
# templates 命令
# ===========================================================================

class TestListTemplates:
    def test_list_templates(self):
        """列出所有预定义模板"""
        with patch("src.commands.cli_profile.console"):
            # 直接运行命令，检查它访问了 PREDEFINED_PROFILES
            result = runner.invoke(app, ["templates"])

            assert result.exit_code == 0
            # 至少包含预定义模板的 key
            assert "daikexing" in PREDEFINED_PROFILES
            assert result.exit_code == 0
