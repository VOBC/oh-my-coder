"""Tests for AuthAgent."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.auth_agent import AuthAgent
from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus


@pytest.fixture
def agent():
    router = MagicMock()
    return AuthAgent(router)


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Design auth system"
    ctx.previous_outputs = {}
    ctx.metadata = {}
    return ctx


class TestAuthAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "auth"

    def test_description(self, agent):
        assert "认证" in agent.description

    def test_lane(self, agent):
        assert agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, agent):
        assert agent.default_tier == "medium"

    def test_icon(self, agent):
        assert agent.icon == "🔐"

    def test_tools(self, agent):
        assert agent.tools == ["file_read", "file_write"]


class TestSystemPrompt:
    def test_contains_auth_role(self, agent):
        prompt = agent.system_prompt
        assert "认证" in prompt

    def test_contains_jwt(self, agent):
        prompt = agent.system_prompt
        assert "JWT" in prompt

    def test_contains_rbac(self, agent):
        prompt = agent.system_prompt
        assert "RBAC" in prompt


class TestPostProcess:
    def test_returns_completed(self, agent, mock_context):
        result = agent._post_process("Auth design", mock_context)
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED
        assert result.agent_name == "auth"
        assert result.next_agent == "executor"
        assert len(result.recommendations) == 3


class TestRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Auth design result"
        agent.call_model = AsyncMock(return_value=mock_response)

        result = await agent._run(mock_context, [{"role": "user", "content": "test"}])
        assert result == "Auth design result"
        agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_appends_auth_hint(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Result"
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        assert len(prompt) > 1
        assert any("认证" in str(p) for p in prompt)

    @pytest.mark.asyncio
    async def test_run_message_conversion(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Done"
        agent.call_model = AsyncMock(return_value=mock_response)

        await agent._run(mock_context, [{"role": "user", "content": "test"}])
        # Verify call_model was called with messages
        call_args = agent.call_model.call_args
        assert call_args is not None
