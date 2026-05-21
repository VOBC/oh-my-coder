"""DebuggerAgent 单元测试"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.debugger import DebuggerAgent
from src.core.router import TaskType


def _make_context(metadata=None, relevant_files=None):
    return AgentContext(
        project_path=Path("."),
        task_description="fix bug",
        metadata=metadata or {},
        relevant_files=relevant_files or [],
    )


@pytest.fixture
def agent():
    return DebuggerAgent()


# ── class attributes ──────────────────────────────────────────
class TestAttributes:
    def test_class_attrs(self, agent):
        assert agent.name == "debugger"
        assert agent.lane == AgentLane.BUILD_ANALYSIS
        assert agent.default_tier == "medium"
        assert agent.icon == "🐛"
        assert "bash" in agent.tools


# ── system_prompt ─────────────────────────────────────────────
class TestSystemPrompt:
    def test_prompt_content(self, agent):
        prompt = agent.system_prompt
        assert "调试专家" in prompt
        assert "根因" in prompt


# ── _post_process ─────────────────────────────────────────────
class TestPostProcess:
    def test_post_process(self, agent):
        ctx = _make_context()
        out = agent._post_process("fixed result", ctx)
        assert isinstance(out, AgentOutput)
        assert out.status == AgentStatus.COMPLETED
        assert out.result == "fixed result"
        assert out.agent_name == "debugger"
        assert out.next_agent == "verifier"
        assert len(out.recommendations) == 2


# ── _run ──────────────────────────────────────────────────────
class TestRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, agent):
        """Basic run with no error info, no relevant files."""
        mock_response = MagicMock()
        mock_response.content = "debug result"
        agent.call_model = AsyncMock(return_value=mock_response)

        ctx = _make_context()
        prompt = [{"role": "user", "content": "bug report"}]
        result = await agent._run(ctx, prompt)

        assert result == "debug result"
        agent.call_model.assert_called_once()
        call_kwargs = agent.call_model.call_args
        assert call_kwargs.kwargs["task_type"] == TaskType.DEBUGGING

    @pytest.mark.asyncio
    async def test_run_with_error_info(self, agent):
        """Run with error info in metadata."""
        mock_response = MagicMock()
        mock_response.content = "analysis"
        agent.call_model = AsyncMock(return_value=mock_response)

        ctx = _make_context(metadata={"error": "TypeError: invalid"})
        prompt = []
        await agent._run(ctx, prompt)

        # Verify error info was appended
        call_args = agent.call_model.call_args
        messages = call_args.kwargs["messages"]
        # Should have error info + debug hint + relevant-code-none-skipped
        error_msgs = [m for m in messages if "TypeError" in m.content]
        assert len(error_msgs) >= 1

    @pytest.mark.asyncio
    async def test_run_with_relevant_files(self, agent, tmp_path):
        """Run with relevant files that exist."""
        test_file = tmp_path / "bug.py"
        test_file.write_text("def broken(): pass", encoding="utf-8")

        mock_response = MagicMock()
        mock_response.content = "found bug"
        agent.call_model = AsyncMock(return_value=mock_response)

        ctx = _make_context(relevant_files=[test_file])
        prompt = []
        await agent._run(ctx, prompt)

        call_args = agent.call_model.call_args
        messages = call_args.kwargs["messages"]
        code_msgs = [m for m in messages if "bug.py" in m.content]
        assert len(code_msgs) >= 1

    @pytest.mark.asyncio
    async def test_run_with_nonexistent_file(self, agent):
        """Run with relevant files that don't exist (should skip gracefully)."""
        mock_response = MagicMock()
        mock_response.content = "ok"
        agent.call_model = AsyncMock(return_value=mock_response)

        fake_path = Path("/nonexistent/file.py")
        ctx = _make_context(relevant_files=[fake_path])
        prompt = []
        result = await agent._run(ctx, prompt)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_run_debug_hint_appended(self, agent):
        """Verify debug hint is always appended."""
        mock_response = MagicMock()
        mock_response.content = "done"
        agent.call_model = AsyncMock(return_value=mock_response)

        ctx = _make_context()
        prompt = []
        await agent._run(ctx, prompt)

        call_args = agent.call_model.call_args
        messages = call_args.kwargs["messages"]
        hint_msgs = [m for m in messages if "根因" in m.content]
        assert len(hint_msgs) >= 1
