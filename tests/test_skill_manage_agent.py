"""
SkillManageAgent 单元测试
"""

import tempfile
from pathlib import Path

import pytest

from src.agents.base import AgentLane
from src.agents.skill_manage import SkillManageAgent


@pytest.fixture
def tmp_sm():
    """独立临时 SkillManager"""
    td = Path(tempfile.mkdtemp())
    return SkillManageAgent(
        model_router=None,
        config={"skills_dir": td / ".omc" / "skills"},
    )


class TestSkillManageAgentMetadata:
    def test_registered_name(self, tmp_sm):
        assert tmp_sm.name == "skill-manage"

    def test_lane(self, tmp_sm):
        assert tmp_sm.lane == AgentLane.COORDINATION

    def test_icon(self, tmp_sm):
        assert tmp_sm.icon == "🧩"

    def test_default_tier_low(self, tmp_sm):
        assert tmp_sm.default_tier == "low"

    def test_tools_empty(self, tmp_sm):
        assert tmp_sm.tools == []

    def test_system_prompt_has_tools(self, tmp_sm):
        prompt = tmp_sm.system_prompt
        assert "create" in prompt
        assert "patch" in prompt
        assert "delete" in prompt
        assert "list" in prompt
        assert "search" in prompt
        assert "patch 优先" in prompt

    def test_post_process(self, tmp_sm):
        output = tmp_sm._post_process("test result", None)
        assert output.agent_name == "skill-manage"
        assert output.result == "test result"


class TestToolList:
    def test_list_empty(self, tmp_sm):
        result = tmp_sm.tool_list()
        assert "（无结果）" in result

    def test_list_with_skills(self, tmp_sm):
        tmp_sm.tool_create(name="Test Skill", body="# Test", category="workflow")
        result = tmp_sm.tool_list()
        assert "test-skill" in result
        assert "workflow" in result

    def test_list_filter_category(self, tmp_sm):
        tmp_sm.tool_create(name="D", body="# D", category="debugging")
        tmp_sm.tool_create(name="W", body="# W", category="workflow")
        result = tmp_sm.tool_list(category="debugging")
        assert "d" in result.lower()
        assert "workflow" not in result.lower()


class TestToolCreate:
    def test_create_basic(self, tmp_sm):
        result = tmp_sm.tool_create(
            name="Create Test",
            body="# Create Test\n\nbody content",
            category="debugging",
            description="测试创建",
            tags=["test"],
        )
        assert "✅" in result
        assert "create-test" in result

    def test_create_duplicate(self, tmp_sm):
        tmp_sm.tool_create(name="Dup", body="# Dup", category="workflow")
        result = tmp_sm.tool_create(name="Dup", body="# Dup", category="workflow")
        # 重复创建自动转为 patch，返回成功
        assert "✅" in result
        assert "patch" in result


class TestToolPatch:
    def test_patch_body_only(self, tmp_sm):
        tmp_sm.tool_create(name="Patch Target", body="# Old", category="workflow")
        skill_id = tmp_sm.sm._slugify("Patch Target")
        result = tmp_sm.tool_patch(skill_id=skill_id, body="# New Body\n\nupdated")
        assert "✅" in result
        assert "更新" in result

    def test_patch_creates_if_missing(self, tmp_sm):
        result = tmp_sm.tool_patch(
            skill_id="auto-new",
            body="# Auto New\n\nauto",
            category="debugging",
        )
        assert "✅" in result
        assert "create" in result.lower() or "创建" in result


class TestToolView:
    def test_view_with_body(self, tmp_sm):
        tmp_sm.tool_create(
            name="View Test",
            body="# View Test\n\n## Section\n\ncontent",
            category="workflow",
            description="测试查看",
        )
        skill_id = tmp_sm.sm._slugify("View Test")
        result = tmp_sm.tool_view(skill_id=skill_id, include_body=True)
        assert "View Test" in result
        assert "Section" in result

    def test_view_not_exists(self, tmp_sm):
        result = tmp_sm.tool_view(skill_id="no-such-skill")
        assert "不存在" in result


class TestToolDelete:
    def test_delete_exists(self, tmp_sm):
        tmp_sm.tool_create(name="Del", body="# Del", category="workflow")
        skill_id = tmp_sm.sm._slugify("Del")
        result = tmp_sm.tool_delete(skill_id=skill_id)
        assert "✅" in result
        assert tmp_sm.sm.get_skill(skill_id) is None

    def test_delete_not_exists(self, tmp_sm):
        result = tmp_sm.tool_delete(skill_id="nonexistent")
        assert "⚠️" in result


class TestToolSearch:
    def test_search(self, tmp_sm):
        tmp_sm.tool_create(
            name="SQL 慢查询",
            body="# SQL 慢查询",
            category="debugging",
            description="SQL 查询优化",
            tags=["sql"],
        )
        result = tmp_sm.tool_search("sql")
        assert "sql" in result.lower()

    def test_search_no_match(self, tmp_sm):
        result = tmp_sm.tool_search("zzzzz")
        assert "无匹配" in result


class TestParseAction:
    def test_parse_list(self, tmp_sm):
        assert tmp_sm._parse_action("列出所有 Skills") == "list"
        assert tmp_sm._parse_action("list skills") == "list"

    def test_parse_search(self, tmp_sm):
        assert tmp_sm._parse_action("搜索 sql 优化") == "search"

    def test_parse_create(self, tmp_sm):
        assert tmp_sm._parse_action("创建一个 Skill") == "create"

    def test_parse_update(self, tmp_sm):
        assert tmp_sm._parse_action("更新 skill 内容") == "patch"

    def test_parse_delete(self, tmp_sm):
        assert tmp_sm._parse_action("删除这个 skill") == "delete"
