"""Tests for CriticAgent."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.critic import CriticAgent


@pytest.fixture
def agent():
    router = MagicMock()
    return CriticAgent(router)


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Test task"
    ctx.previous_outputs = {}
    ctx.metadata = {}
    return ctx


class TestCriticAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "critic"

    def test_description(self, agent):
        assert "批评家" in agent.description

    def test_lane(self, agent):
        assert agent.lane == AgentLane.COORDINATION

    def test_default_tier(self, agent):
        assert agent.default_tier == "high"

    def test_icon(self, agent):
        assert agent.icon == "🎯"

    def test_tools(self, agent):
        assert agent.tools == ["file_read", "search"]


class TestSystemPrompt:
    def test_system_prompt_contains_critic_role(self, agent):
        prompt = agent.system_prompt
        assert "批评家" in prompt
        assert "建设性" in prompt

    def test_system_prompt_contains_review_dimensions(self, agent):
        prompt = agent.system_prompt
        assert "完整性" in prompt
        assert "可行性" in prompt
        assert "一致性" in prompt
        assert "可维护性" in prompt
        assert "可扩展性" in prompt


class TestPostProcess:
    def test_post_process_returns_completed(self, agent, mock_context):
        result = agent._post_process("Some review", mock_context)
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED
        assert result.agent_name == "critic"
        assert result.result == "Some review"
        assert len(result.recommendations) == 2


class TestRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Review result"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        result = await agent._run(mock_context, [{"role": "user", "content": "test"}])
        assert result == "Review result"
        agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_planner_output(self, agent, mock_context):
        mock_context.previous_outputs = {
            "planner": MagicMock(result="Plan: do X")
        }
        mock_response = MagicMock()
        mock_response.content = "Review of plan"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        result = await agent._run(mock_context, prompt)
        assert result == "Review of plan"
        # context was appended
        assert len(prompt) > 1

    @pytest.mark.asyncio
    async def test_run_with_architect_output(self, agent, mock_context):
        mock_context.previous_outputs = {
            "architect": MagicMock(result="Architecture: use microservices")
        }
        mock_response = MagicMock()
        mock_response.content = "Review of architecture"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        result = await agent._run(mock_context, prompt)
        assert result == "Review of architecture"

    @pytest.mark.asyncio
    async def test_run_with_both_outputs(self, agent, mock_context):
        mock_context.previous_outputs = {
            "planner": MagicMock(result="Plan: do X"),
            "architect": MagicMock(result="Architecture: use Y"),
        }
        mock_response = MagicMock()
        mock_response.content = "Review"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        result = await agent._run(mock_context, prompt)
        assert result == "Review"
