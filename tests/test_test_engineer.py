"""Tests for test_engineer.py"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentOutput, AgentStatus
from src.agents.test_engineer import TestEngineerAgent


@pytest.fixture
def agent():
    return TestEngineerAgent()


@pytest.fixture
def mock_context(tmp_path):
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Design tests"
    ctx.project_path = tmp_path
    ctx.previous_outputs = {}
    return ctx


@pytest.fixture
def mock_context_with_prev(tmp_path):
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Design tests"
    ctx.project_path = tmp_path
    prev = MagicMock()
    prev.result = "def hello(): return 'world'"
    ctx.previous_outputs = {"executor": prev}
    return ctx


@pytest.fixture
def mock_prompt():
    return [{"role": "user", "content": "Write tests"}]


class TestTestEngineerAttributes:
    def test_name(self, agent):
        assert agent.name == "test-engineer"

    def test_description(self, agent):
        assert "测试" in agent.description

    def test_lane(self, agent):
        from src.agents.base import AgentLane
        assert agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, agent):
        assert agent.default_tier == "medium"

    def test_icon(self, agent):
        assert agent.icon == "🧪"

    def test_tools(self, agent):
        assert "bash" in agent.tools
        assert "test" in agent.tools


class TestSystemPrompt:
    def test_not_empty(self, agent):
        assert isinstance(agent.system_prompt, str) and len(agent.system_prompt) > 0

    def test_contains_keywords(self, agent):
        p = agent.system_prompt
        assert "测试工程师" in p
        assert "FAST" in p
        assert "ISOLATED" in p


class TestRunMethod:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context, mock_prompt):
        mock_resp = MagicMock()
        mock_resp.content = "Test plan"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            result = await agent._run(mock_context, mock_prompt)
        assert result == "Test plan"

    @pytest.mark.asyncio
    async def test_run_with_previous_output(self, agent, mock_context_with_prev, mock_prompt):
        mock_resp = MagicMock()
        mock_resp.content = "Test result"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            result = await agent._run(mock_context_with_prev, mock_prompt)
        assert result == "Test result"
        # Should have appended executor output
        assert any("实现代码" in m.get("content", "") for m in mock_prompt)

    @pytest.mark.asyncio
    async def test_run_with_existing_tests(self, agent, tmp_path, mock_prompt):
        ctx = MagicMock(spec=AgentContext)
        ctx.task_description = "Design tests"
        ctx.project_path = tmp_path
        ctx.previous_outputs = {}
        # Create test dir with files
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_foo.py").write_text("def test_x(): pass")
        (test_dir / "test_bar.py").write_text("def test_y(): pass")

        mock_resp = MagicMock()
        mock_resp.content = "Test plan"
        mock_resp.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_resp)

        with patch("src.models.base.Message"):
            result = await agent._run(ctx, mock_prompt)
        assert any("现有测试" in m.get("content", "") for m in mock_prompt)


class TestPostProcess:
    def test_basic(self, agent, mock_context):
        output = agent._post_process("result", mock_context)
        assert isinstance(output, AgentOutput)
        assert output.agent_name == "test-engineer"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "result"
        assert output.next_agent == "verifier"

    def test_recommendations(self, agent, mock_context):
        output = agent._post_process("result", mock_context)
        assert len(output.recommendations) == 2
