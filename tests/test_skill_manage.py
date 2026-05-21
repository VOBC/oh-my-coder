"""Tests for SkillManageAgent."""
from unittest.mock import MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.skill_manage import SkillManageAgent


@pytest.fixture
def agent():
    router = MagicMock()
    return SkillManageAgent(router)


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Test skill management"
    ctx.previous_outputs = {}
    ctx.metadata = {}
    return ctx


class TestSkillManageAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "skill-manage"

    def test_description(self, agent):
        assert "Skill" in agent.description

    def test_lane(self, agent):
        assert agent.lane == AgentLane.COORDINATION

    def test_default_tier(self, agent):
        assert agent.default_tier == "low"

    def test_icon(self, agent):
        assert agent.icon == "🧩"

    def test_tools_empty(self, agent):
        assert agent.tools == []


class TestInit:
    def test_init_without_config(self, agent):
        assert agent.sm is not None

    def test_init_with_config(self):
        router = MagicMock()
        agent = SkillManageAgent(router, config={"skills_dir": "/tmp/test"})
        assert agent.sm is not None


class TestSystemPrompt:
    def test_system_prompt_contains_skill_role(self, agent):
        prompt = agent.system_prompt
        assert "Skill" in prompt

    def test_system_prompt_contains_tools(self, agent):
        prompt = agent.system_prompt
        assert "list" in prompt
        assert "create" in prompt
        assert "patch" in prompt

    def test_system_prompt_contains_crud(self, agent):
        prompt = agent.system_prompt
        assert "patch 优先" in prompt or "优先" in prompt


class TestPostProcess:
    def test_post_process_returns_completed(self, agent, mock_context):
        result = agent._post_process("Skill updated", mock_context)
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED
        assert result.agent_name == "skill-manage"
        assert len(result.recommendations) == 1


class TestSkillManager:
    def test_sm_is_skill_manager_instance(self, agent):
        from src.memory.skill_manager import SkillManager

        assert isinstance(agent.sm, SkillManager)


class TestToolMethods:
    """Test tool methods directly."""

    def test_tool_list_empty(self, agent):
        with patch.object(agent.sm, "list_skills", return_value=[]):
            result = agent.tool_list()
        assert result == "（无结果）"

    def test_tool_list_with_skills(self, agent):
        skills = [
            {
                "skill_id": "test-skill",
                "category": "workflow",
                "description": "A test skill",
                "tags": ["python", "test"],
            }
        ]
        with patch.object(agent.sm, "list_skills", return_value=skills):
            result = agent.tool_list()
        assert "test-skill" in result
        assert "workflow" in result

    def test_tool_list_with_limit(self, agent):
        with patch.object(agent.sm, "list_skills") as mock_list:
            agent.tool_list(limit=5)
            mock_list.assert_called_once_with(category=None, tag=None, limit=5)

    def test_tool_list_with_category(self, agent):
        with patch.object(agent.sm, "list_skills") as mock_list:
            mock_list.return_value = []
            agent.tool_list(category="debugging")
            mock_list.assert_called_once_with(category="debugging", tag=None, limit=20)

    def test_tool_list_with_tag(self, agent):
        with patch.object(agent.sm, "list_skills") as mock_list:
            mock_list.return_value = []
            agent.tool_list(tag="python")
            mock_list.assert_called_once_with(category=None, tag="python", limit=20)

    def test_tool_view_not_found(self, agent):
        with patch.object(agent.sm, "get_skill", return_value=None):
            result = agent.tool_view("nonexistent")
        assert "不存在" in result

    def test_tool_view_found(self, agent):
        skill = {
            "name": "Test Skill",
            "skill_id": "test-skill",
            "category": "workflow",
            "description": "A test",
            "tags": ["python"],
            "triggers": ["test"],
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        with patch.object(agent.sm, "get_skill", return_value=skill):
            result = agent.tool_view("test-skill")
        assert "Test Skill" in result
        assert "workflow" in result
        assert "python" in result

    def test_tool_view_with_body(self, agent):
        skill = {
            "name": "Test",
            "skill_id": "test",
            "category": "workflow",
            "description": "Desc",
            "tags": [],
            "triggers": [],
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
            "body": "Skill body content",
        }
        with patch.object(agent.sm, "get_skill", return_value=skill):
            result = agent.tool_view("test", include_body=True)
        assert "body" in result.lower() or "Skill body content" in result

    def test_tool_delete_success(self, agent):
        with patch.object(agent.sm, "delete", return_value=True):
            result = agent.tool_delete("test-skill")
        assert "✅" in result

    def test_tool_delete_not_found(self, agent):
        with patch.object(agent.sm, "delete", return_value=False):
            result = agent.tool_delete("nonexistent")
        assert "不存在" in result or "⚠️" in result

    def test_tool_search_no_results(self, agent):
        with patch.object(agent.sm, "search", return_value=[]):
            result = agent.tool_search("nonexistent query")
        assert "无匹配" in result or "nonexistent" in result.lower()

    def test_tool_search_with_results(self, agent):
        skills = [
            {
                "skill_id": "match-skill",
                "category": "debugging",
                "description": "Matches query",
            }
        ]
        with patch.object(agent.sm, "search", return_value=skills):
            result = agent.tool_search("query")
        assert "match-skill" in result
        assert "1 个结果" in result


class TestParseAction:
    def test_parse_search(self, agent):
        assert agent._parse_action("搜索 python") == "search"
        assert agent._parse_action("SEARCH python") == "search"

    def test_parse_list(self, agent):
        assert agent._parse_action("列出所有技能") == "list"
        assert agent._parse_action("list skills") == "list"

    def test_parse_view(self, agent):
        assert agent._parse_action("查看 skill") == "view"
        assert agent._parse_action("VIEW `skill-id`") == "view"

    def test_parse_patch(self, agent):
        assert agent._parse_action("更新 skill") == "patch"
        assert agent._parse_action("PATCH skill") == "patch"

    def test_parse_create(self, agent):
        assert agent._parse_action("创建新技能") == "create"
        assert agent._parse_action("CREATE skill") == "create"

    def test_parse_delete(self, agent):
        assert agent._parse_action("删除 skill") == "delete"
        assert agent._parse_action("DELETE skill") == "delete"

    def test_parse_default(self, agent):
        assert agent._parse_action("do something") == ""


class TestParseParams:
    def test_parse_category(self, agent):
        params = agent._parse_params("列出 debugging 分类")
        assert params.get("category") == "debugging"

    def test_parse_skill_id(self, agent):
        params = agent._parse_params("查看 `test-skill` 详情")
        assert params.get("skill_id") == "test-skill"


class TestRun:
    @pytest.mark.asyncio
    async def test_run_list(self, agent, mock_context):
        with patch.object(agent.sm, "list_skills", return_value=[]):
            result = await agent._run(mock_context, [{"role": "user", "content": "列出所有技能"}])
        assert result == "（无结果）"


    @pytest.mark.asyncio
    async def test_run_default(self, agent, mock_context):
        with patch.object(agent.sm, "list_skills", return_value=[]):
            result = await agent._run(mock_context, [{"role": "user", "content": "do something"}])
        # Default action: list all
        assert "（无结果）" in result or "💡" in result

    @pytest.mark.asyncio
    async def test_run_extracts_last_user_message(self, agent, mock_context):
        prompt = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "response"},
            {"role": "user", "content": "last message"},
        ]
        with patch.object(agent.sm, "list_skills", return_value=[]) as mock_list:
            await agent._run(mock_context, prompt)
            # Should have extracted "last message" and matched list action
            # Since "last message" doesn't match any action, default to list
            mock_list.assert_called()


class TestToolCreate:
    def test_tool_create_new_skill(self, agent):
        with patch.object(agent.sm, "get_skill", return_value=None):
            with patch.object(agent.sm, "create") as mock_create:
                mock_create.return_value = {"skill_id": "new-skill", "description": "Test"}
                result = agent.tool_create(name="New Skill", body="Content")
        assert "成功" in result or "✅" in result
        assert "new-skill" in result

    def test_tool_create_existing_auto_patch(self, agent):
        existing = {"skill_id": "existing-skill", "description": "Old desc"}
        with patch.object(agent.sm, "get_skill", return_value=existing):
            with patch.object(agent.sm, "patch") as mock_patch:
                mock_patch.return_value = {"skill_id": "existing-skill", "description": "New desc"}
                result = agent.tool_create(name="Existing Skill", body="New content")
        assert "patch" in result.lower() or "✅" in result

    def test_tool_create_failure(self, agent):
        with patch.object(agent.sm, "get_skill", return_value=None):
            with patch.object(agent.sm, "create", side_effect=Exception("DB error")):
                result = agent.tool_create(name="Fail Skill", body="Content")
        assert "失败" in result or "❌" in result


class TestToolPatch:
    def test_tool_patch_update_existing(self, agent):
        existing = {"skill_id": "test", "description": "Old"}
        with patch.object(agent.sm, "get_skill", return_value=existing):
            with patch.object(agent.sm, "patch") as mock_patch:
                mock_patch.return_value = {"skill_id": "test", "description": "New"}
                result = agent.tool_patch(skill_id="test", description="New")
        assert "更新" in result

    def test_tool_patch_create_new(self, agent):
        with patch.object(agent.sm, "get_skill", return_value=None):
            with patch.object(agent.sm, "patch") as mock_patch:
                mock_patch.return_value = {"skill_id": "new", "description": "Desc"}
                result = agent.tool_patch(skill_id="new")
        assert "创建" in result

    def test_tool_patch_failure(self, agent):
        with patch.object(agent.sm, "get_skill", return_value={}):
            with patch.object(agent.sm, "patch", side_effect=Exception("Error")):
                result = agent.tool_patch(skill_id="test")
        assert "失败" in result or "❌" in result
