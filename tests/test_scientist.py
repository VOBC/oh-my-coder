"""Tests for ScientistAgent."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.scientist import ScientistAgent


@pytest.fixture
def agent():
    router = MagicMock()
    return ScientistAgent(router)


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Test analysis"
    ctx.previous_outputs = {}
    ctx.metadata = {}
    return ctx


class TestScientistAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "scientist"

    def test_description(self, agent):
        assert "数据分析" in agent.description

    def test_lane(self, agent):
        assert agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, agent):
        assert agent.default_tier == "medium"

    def test_icon(self, agent):
        assert agent.icon == "🔬"

    def test_tools(self, agent):
        assert agent.tools == ["file_read", "file_write", "bash"]


class TestSystemPrompt:
    def test_system_prompt_contains_data_scientist_role(self, agent):
        prompt = agent.system_prompt
        assert "数据科学家" in prompt or "数据" in prompt

    def test_system_prompt_contains_analysis_methods(self, agent):
        prompt = agent.system_prompt
        assert "描述性统计" in prompt or "统计" in prompt


class TestPostProcess:
    def test_post_process_returns_completed(self, agent, mock_context):
        result = agent._post_process("Analysis findings", mock_context)
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED
        assert result.agent_name == "scientist"
        assert len(result.recommendations) == 1


class TestRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Statistical analysis"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        result = await agent._run(mock_context, [{"role": "user", "content": "test"}])
        assert result == "Statistical analysis"
        agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_prompt_has_analysis_hint(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Result"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        # analysis hint was appended
        assert len(prompt) > 1
