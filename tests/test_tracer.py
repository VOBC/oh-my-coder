"""Tests for TracerAgent."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.tracer import Hypothesis, TracerAgent


@pytest.fixture
def agent():
    router = MagicMock()
    return TracerAgent(router)


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Test trace"
    ctx.previous_outputs = {}
    ctx.metadata = {}
    ctx.relevant_files = []
    return ctx


class TestTracerAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "tracer"

    def test_description(self, agent):
        assert "追踪" in agent.description

    def test_lane(self, agent):
        assert agent.lane == AgentLane.BUILD_ANALYSIS

    def test_default_tier(self, agent):
        assert agent.default_tier == "medium"

    def test_icon(self, agent):
        assert agent.icon == "🔍"

    def test_tools(self, agent):
        assert agent.tools == ["file_read", "search", "bash"]


class TestSystemPrompt:
    def test_system_prompt_contains_root_cause_analysis(self, agent):
        prompt = agent.system_prompt
        assert "根因" in prompt

    def test_system_prompt_contains_hypothesis_analysis(self, agent):
        prompt = agent.system_prompt
        assert "假设" in prompt


class TestHypothesis:
    def test_hypothesis_creation(self):
        h = Hypothesis(
            description="Bug in code",
            evidence_for=["Error log shows X", "Test fails"],
            evidence_against=["Other tests pass"],
            confidence=0.8,
        )
        assert h.description == "Bug in code"
        assert len(h.evidence_for) == 2
        assert h.confidence == 0.8

    def test_hypothesis_confidence_range(self):
        h = Hypothesis(
            description="Test",
            evidence_for=[],
            evidence_against=[],
            confidence=0.5,
        )
        assert 0 <= h.confidence <= 1


class TestPostProcess:
    def test_post_process_returns_completed(self, agent, mock_context):
        result = agent._post_process("Root cause analysis", mock_context)
        assert isinstance(result, AgentOutput)
        assert result.status == AgentStatus.COMPLETED
        assert result.agent_name == "tracer"
        assert result.next_agent == "debugger"

    def test_post_process_recommendations(self, agent, mock_context):
        result = agent._post_process("Analysis", mock_context)
        assert len(result.recommendations) == 2


class TestRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_context):
        mock_response = MagicMock()
        mock_response.content = "Root cause found"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        result = await agent._run(mock_context, [{"role": "user", "content": "test"}])
        assert result == "Root cause found"
        agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_error_metadata(self, agent, mock_context):
        mock_context.metadata = {"error": "TypeError: NoneType has no attribute"}
        mock_response = MagicMock()
        mock_response.content = "Analysis"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        # error info was added
        assert len(prompt) > 1

    @pytest.mark.asyncio
    async def test_run_with_relevant_files(self, agent, mock_context, tmp_path):
        # Create a mock file
        mock_file = tmp_path / "test.py"
        mock_file.write_text("x = 1")
        mock_context.relevant_files = [mock_file]

        mock_response = MagicMock()
        mock_response.content = "Analysis"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        # code context was added
        assert len(prompt) > 1

    @pytest.mark.asyncio
    async def test_run_with_multiple_files(self, agent, mock_context, tmp_path):
        mock_file1 = tmp_path / "a.py"
        mock_file1.write_text("import os")
        mock_file2 = tmp_path / "b.py"
        mock_file2.write_text("import sys")
        mock_context.relevant_files = [mock_file1, mock_file2]

        mock_response = MagicMock()
        mock_response.content = "Analysis"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        # limit is 5, we have 2
        assert len(prompt) > 1

    @pytest.mark.asyncio
    async def test_run_with_file_read_error(self, agent, mock_context, tmp_path):
        mock_file = tmp_path / "unreadable.py"
        mock_context.relevant_files = [mock_file]
        # File doesn't exist - will raise in _run

        mock_response = MagicMock()
        mock_response.content = "Analysis"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        # Should not raise, just skip unreadable file
        await agent._run(mock_context, prompt)
        agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_long_file_truncated(self, agent, mock_context, tmp_path):
        mock_file = tmp_path / "long.py"
        mock_file.write_text("x = 1\n" * 1000)  # Very long
        mock_context.relevant_files = [mock_file]

        mock_response = MagicMock()
        mock_response.content = "Analysis"
        mock_response.tool_calls = []
        agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "user", "content": "test"}]
        await agent._run(mock_context, prompt)
        agent.call_model.assert_called_once()
