"""Tests for database.py"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.database import DatabaseAgent

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def mock_model_router():
    """Create a mock model router."""
    router = MagicMock()
    router.route_and_call = AsyncMock()
    return router


@pytest.fixture
def database_agent(mock_model_router):
    """Create a DatabaseAgent instance."""
    return DatabaseAgent(model_router=mock_model_router)


@pytest.fixture
def agent_context(tmp_path):
    """Create an AgentContext for testing."""
    return AgentContext(
        project_path=tmp_path,
        task_description="Design database schema",
    )


# ── DatabaseAgent Class Attributes ──────────────────────────────────


class TestDatabaseAgentAttributes:
    def test_name(self, database_agent):
        assert database_agent.name == "database"

    def test_description(self, database_agent):
        assert "数据库" in database_agent.description

    def test_lane(self, database_agent):
        assert database_agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, database_agent):
        assert database_agent.default_tier == "medium"

    def test_icon(self, database_agent):
        assert database_agent.icon == "🗄️"

    def test_tools(self, database_agent):
        assert "file_read" in database_agent.tools
        assert "file_write" in database_agent.tools


# ── system_prompt Property ─────────────────────────────────────────


class TestDatabaseAgentSystemPrompt:
    def test_system_prompt_not_empty(self, database_agent):
        prompt = database_agent.system_prompt
        assert len(prompt) > 0

    def test_system_prompt_contains_role(self, database_agent):
        prompt = database_agent.system_prompt
        assert "数据库工程师" in prompt

    def test_system_prompt_contains_capabilities(self, database_agent):
        prompt = database_agent.system_prompt
        assert "表结构设计" in prompt
        assert "SQL 编写" in prompt
        assert "索引优化" in prompt


# ── _run Method ────────────────────────────────────────────────────


class TestDatabaseAgentRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, database_agent, agent_context):
        """Test basic _run execution."""
        mock_response = MagicMock()
        mock_response.content = "CREATE TABLE users (id INT);"

        database_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a database engineer."}]

        result = await database_agent._run(agent_context, prompt)

        assert result == "CREATE TABLE users (id INT);"
        database_agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_architect_output(self, database_agent, tmp_path):
        """Test _run with architect output in previous_outputs."""
        mock_response = MagicMock()
        mock_response.content = "CREATE TABLE orders (id INT);"

        database_agent.call_model = AsyncMock(return_value=mock_response)

        context = AgentContext(
            project_path=tmp_path,
            task_description="Design orders table",
            previous_outputs={
                "architect": MagicMock(result="Architecture: microservice")
            },
        )

        prompt = [{"role": "system", "content": "You are a database engineer."}]

        await database_agent._run(context, prompt)

        # Check that architect output was added to prompt
        call_args = database_agent.call_model.call_args
        messages = call_args.kwargs["messages"]
        assert any("架构设计参考" in str(m) for m in messages)

    @pytest.mark.asyncio
    async def test_run_adds_db_hint(self, database_agent, agent_context):
        """Test that _run adds database-specific hint to prompt."""
        mock_response = MagicMock()
        mock_response.content = "Database design complete."

        database_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a database engineer."}]

        await database_agent._run(agent_context, prompt)

        call_args = database_agent.call_model.call_args
        messages = call_args.kwargs["messages"]
        assert any("数据库设计" in str(m.content) for m in messages)


# ── _post_process Method ───────────────────────────────────────────


class TestDatabaseAgentPostProcess:
    def test_post_process_returns_output(self, database_agent, agent_context):
        """Test that _post_process returns AgentOutput."""
        result = "CREATE TABLE users (id INT);"

        output = database_agent._post_process(result, agent_context)

        assert isinstance(output, AgentOutput)
        assert output.agent_name == "database"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == result

    def test_post_process_recommendations(self, database_agent, agent_context):
        """Test that _post_process includes recommendations."""
        result = "CREATE TABLE users (id INT);"

        output = database_agent._post_process(result, agent_context)

        assert len(output.recommendations) == 3
        assert any("migrations/" in r for r in output.recommendations)
        assert any("索引" in r for r in output.recommendations)

    def test_post_process_next_agent(self, database_agent, agent_context):
        """Test that _post_process sets next_agent."""
        result = "CREATE TABLE users (id INT);"

        output = database_agent._post_process(result, agent_context)

        assert output.next_agent == "executor"
