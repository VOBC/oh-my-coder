"""Tests for uml.py"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentOutput, AgentStatus
from src.agents.uml import UMLAgent


@pytest.fixture
def agent():
    return UMLAgent()


@pytest.fixture
def mock_context(tmp_path):
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Generate UML"
    ctx.project_path = tmp_path
    ctx.previous_outputs = {}
    return ctx


@pytest.fixture
def mock_context_with_prev(tmp_path):
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Generate UML"
    ctx.project_path = tmp_path
    arch = MagicMock()
    arch.result = "System uses microservices"
    explore = MagicMock()
    explore.result = "x" * 3000  # long result to test truncation
    ctx.previous_outputs = {"architect": arch, "explore": explore}
    return ctx


@pytest.fixture
def mock_prompt():
    return [{"role": "user", "content": "Draw UML"}]


class TestUMLAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "uml"

    def test_lane(self, agent):
        from src.agents.base import AgentLane
        assert agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, agent):
        assert agent.default_tier == "low"

    def test_icon(self, agent):
        assert agent.icon == "📊"


class TestSystemPrompt:
    def test_not_empty(self, agent):
        assert isinstance(agent.system_prompt, str) and len(agent.system_prompt) > 0

    def test_contains_mermaid(self, agent):
        assert "Mermaid" in agent.system_prompt


class TestRunMethod:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context, mock_prompt):
        mock_resp = MagicMock()
        mock_resp.content = "Mermaid diagram"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            result = await agent._run(mock_context, mock_prompt)
        assert result == "Mermaid diagram"

    @pytest.mark.asyncio
    async def test_run_with_architect_output(self, agent, mock_context_with_prev, mock_prompt):
        mock_resp = MagicMock()
        mock_resp.content = "UML result"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            await agent._run(mock_context_with_prev, mock_prompt)
        assert any("架构设计" in m.get("content", "") for m in mock_prompt)
        assert any("代码结构" in m.get("content", "") for m in mock_prompt)


class TestPostProcess:
    def test_basic(self, agent, mock_context):
        output = agent._post_process("diagram", mock_context)
        assert isinstance(output, AgentOutput)
        assert output.agent_name == "uml"
        assert output.status == AgentStatus.COMPLETED
        assert output.next_agent == "writer"

    def test_recommendations(self, agent, mock_context):
        output = agent._post_process("diagram", mock_context)
        assert len(output.recommendations) == 3
