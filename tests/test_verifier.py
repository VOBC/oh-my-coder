"""Tests for verifier.py"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentOutput, AgentStatus
from src.agents.verifier import VerifierAgent


@pytest.fixture
def agent():
    return VerifierAgent()


@pytest.fixture
def mock_context(tmp_path):
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Verify code"
    ctx.project_path = tmp_path
    ctx.previous_outputs = {}
    return ctx


@pytest.fixture
def mock_context_with_executor(tmp_path):
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Verify code"
    ctx.project_path = tmp_path
    prev = MagicMock()
    prev.result = "def hello(): return 'world'"
    ctx.previous_outputs = {"executor": prev}
    return ctx


@pytest.fixture
def mock_prompt():
    return [{"role": "user", "content": "Verify implementation"}]


class TestVerifierAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "verifier"

    def test_lane(self, agent):
        from src.agents.base import AgentLane
        assert agent.lane == AgentLane.BUILD_ANALYSIS

    def test_default_tier(self, agent):
        assert agent.default_tier == "medium"

    def test_icon(self, agent):
        assert agent.icon == "✅"

    def test_tools(self, agent):
        assert "bash" in agent.tools
        assert "test" in agent.tools


class TestSystemPrompt:
    def test_not_empty(self, agent):
        assert isinstance(agent.system_prompt, str) and len(agent.system_prompt) > 0

    def test_contains_keywords(self, agent):
        p = agent.system_prompt
        assert "验证" in p
        assert "覆盖率" in p


class TestRunMethod:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context, mock_prompt):
        mock_resp = MagicMock()
        mock_resp.content = "Verification result"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            result = await agent._run(mock_context, mock_prompt)
        assert result == "Verification result"

    @pytest.mark.asyncio
    async def test_run_with_executor_output(self, agent, mock_context_with_executor, mock_prompt):
        mock_resp = MagicMock()
        mock_resp.content = "Verified"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            result = await agent._run(mock_context_with_executor, mock_prompt)
        assert any("实现代码" in m.get("content", "") for m in mock_prompt)

    @pytest.mark.asyncio
    async def test_run_with_existing_tests(self, agent, tmp_path, mock_prompt):
        ctx = MagicMock(spec=AgentContext)
        ctx.task_description = "Verify code"
        ctx.project_path = tmp_path
        ctx.previous_outputs = {}
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_foo.py").write_text("def test_x(): pass")

        mock_resp = MagicMock()
        mock_resp.content = "Verified"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            result = await agent._run(ctx, mock_prompt)
        assert any("现有测试" in m.get("content", "") for m in mock_prompt)

    @pytest.mark.asyncio
    async def test_run_no_test_dir(self, agent, mock_context, mock_prompt):
        mock_resp = MagicMock()
        mock_resp.content = "No tests found"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            result = await agent._run(mock_context, mock_prompt)
        assert result == "No tests found"


class TestPostProcess:
    def test_basic(self, agent, mock_context):
        output = agent._post_process("result", mock_context)
        assert isinstance(output, AgentOutput)
        assert output.agent_name == "verifier"
        assert output.status == AgentStatus.COMPLETED

    def test_no_next_agent(self, agent, mock_context):
        output = agent._post_process("result", mock_context)
        assert output.next_agent is None
