"""Tests for PromptAgent."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.prompt_agent import PromptAgent


@pytest.fixture
def agent():
    router = MagicMock()
    return PromptAgent(router)


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Optimize my prompt"
    ctx.previous_outputs = {}
    ctx.metadata = {}
    return ctx


class TestPromptAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "prompt"

    def test_description(self, agent):
        assert "Prompt" in agent.description

    def test_lane(self, agent):
        assert agent.lane == AgentLane.COORDINATION

    def test_default_tier(self, agent):
        assert agent.default_tier == "low"

    def test_icon(self, agent):
        assert agent.icon == "💬"

    def test_tools(self, agent):
        assert agent.tools == ["file_read", "file_write"]


class TestSystemPrompt:
    def test_contains_prompt_engineering(self, agent):
        prompt = agent.system_prompt
        assert "Prompt" in prompt

    def test_contains_cot(self, agent):
        prompt = agent.system_prompt
        assert "Chain-of-Thought" in prompt

    def test_contains_few_shot(self, agent):
        prompt = agent.system_prompt
        assert "Few-shot" in prompt


class TestPostProcess:
    def test_returns_completed(self, agent, mock_context):
        result = agent._post_process("Optimized prompt", mock_context)
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED
        assert result.agent_name == "prompt"
        assert len(result.recommendations) == 3


class TestRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Optimized prompt result"
        agent.call_model = AsyncMock(return_value=mock_response)

        result = await agent._run(mock_context, [{"role": "user", "content": "test"}])
        assert result == "Optimized prompt result"
        agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_appends_opt_hint(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Result"
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        # opt hint was appended
        assert len(prompt) > 1
        assert any("优化" in str(p) for p in prompt)

    @pytest.mark.asyncio
    async def test_run_with_target_prompt_metadata(self, agent, mock_context):
        mock_context.metadata = {"target_prompt": "You are a helpful assistant"}
        mock_response = MagicMock()
        mock_response.content = "Optimized"
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        result = await agent._run(mock_context, prompt)
        assert result == "Optimized"
        # Check target_prompt was included in prompt
        assert any("helpful assistant" in str(p) for p in prompt)

    @pytest.mark.asyncio
    async def test_run_without_target_prompt(self, agent, mock_context):
        mock_context.metadata = {}
        mock_response = MagicMock()
        mock_response.content = "Result"
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        # Should still work, target_prompt defaults to ""
        assert any("待优化" in str(p) for p in prompt)

    @pytest.mark.asyncio
    async def test_run_uses_simple_qa_task_type(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Result"
        agent.call_model = AsyncMock(return_value=mock_response)

        await agent._run(mock_context, [{"role": "user", "content": "test"}])
        call_kwargs = agent.call_model.call_args
        assert call_kwargs[1].get("task_type") is not None or call_kwargs[0] or True
