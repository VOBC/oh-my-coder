"""Tests for DataAgent."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.data_agent import DataAgent


@pytest.fixture
def agent():
    router = MagicMock()
    return DataAgent(router)


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Test data task"
    ctx.previous_outputs = {}
    ctx.metadata = {}
    return ctx


class TestDataAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "data"

    def test_description(self, agent):
        assert "数据" in agent.description

    def test_lane(self, agent):
        assert agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, agent):
        assert agent.default_tier == "medium"

    def test_icon(self, agent):
        assert agent.icon == "📥"

    def test_tools(self, agent):
        assert agent.tools == ["file_read", "file_write"]


class TestSystemPrompt:
    def test_system_prompt_contains_data_role(self, agent):
        prompt = agent.system_prompt
        assert "数据工程" in prompt

    def test_system_prompt_contains_etl(self, agent):
        prompt = agent.system_prompt
        assert "ETL" in prompt
        assert "Pandas" in prompt or "pandas" in prompt.lower()


class TestPostProcess:
    def test_post_process_returns_completed(self, agent, mock_context):
        result = agent._post_process("Data pipeline", mock_context)
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED
        assert result.agent_name == "data"
        assert len(result.recommendations) == 3


class TestRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Data analysis result"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        result = await agent._run(mock_context, [{"role": "user", "content": "test"}])
        assert result == "Data analysis result"
        agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_prompt_modified(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Data result"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        # data hint was appended
        assert len(prompt) > 1
        assert any("数据" in str(p) or "data" in str(p).lower() for p in prompt)
