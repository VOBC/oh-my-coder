"""Tests for migration.py"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentOutput, AgentStatus
from src.agents.migration import MigrationAgent


@pytest.fixture
def agent():
    return MigrationAgent()


@pytest.fixture
def mock_context(tmp_path):
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Design migration"
    ctx.project_path = tmp_path
    ctx.previous_outputs = {}
    return ctx


@pytest.fixture
def mock_context_with_db(tmp_path):
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Design migration"
    ctx.project_path = tmp_path
    prev = MagicMock()
    prev.result = "CREATE TABLE users (id INT)"
    ctx.previous_outputs = {"database": prev}
    return ctx


@pytest.fixture
def mock_prompt():
    return [{"role": "user", "content": "Migrate data"}]


class TestMigrationAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "migration"

    def test_lane(self, agent):
        from src.agents.base import AgentLane
        assert agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, agent):
        assert agent.default_tier == "medium"

    def test_icon(self, agent):
        assert agent.icon == "🔄"


class TestSystemPrompt:
    def test_not_empty(self, agent):
        assert isinstance(agent.system_prompt, str) and len(agent.system_prompt) > 0

    def test_contains_keywords(self, agent):
        p = agent.system_prompt
        assert "迁移" in p
        assert "回滚" in p


class TestRunMethod:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context, mock_prompt):
        mock_resp = MagicMock()
        mock_resp.content = "Migration plan"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            result = await agent._run(mock_context, mock_prompt)
        assert result == "Migration plan"

    @pytest.mark.asyncio
    async def test_run_with_database_output(self, agent, mock_context_with_db, mock_prompt):
        mock_resp = MagicMock()
        mock_resp.content = "Migration script"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            result = await agent._run(mock_context_with_db, mock_prompt)
        assert any("数据库设计" in m.get("content", "") for m in mock_prompt)


class TestPostProcess:
    def test_basic(self, agent, mock_context):
        output = agent._post_process("migration", mock_context)
        assert isinstance(output, AgentOutput)
        assert output.agent_name == "migration"
        assert output.status == AgentStatus.COMPLETED
        assert output.next_agent == "executor"

    def test_recommendations(self, agent, mock_context):
        output = agent._post_process("migration", mock_context)
        assert len(output.recommendations) == 3
