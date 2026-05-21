"""Tests for code_simplifier.py"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentLane, AgentStatus
from src.agents.code_simplifier import CodeSimplifierAgent

# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def make_context(tmp_path):
    """Factory: create AgentContext with optional relevant_files."""
    def _make(relevant_files: list[Path] | None = None) -> AgentContext:
        return AgentContext(
            project_path=tmp_path,
            task_description="简化这段代码",
            relevant_files=relevant_files or [],
        )
    return _make


@pytest.fixture
def make_agent():
    """Factory: create CodeSimplifierAgent with a mocked model router."""
    def _make() -> CodeSimplifierAgent:
        mock_router = MagicMock()
        return CodeSimplifierAgent(model_router=mock_router, config={})
    return _make


# ── Class attributes ───────────────────────────────────────────────

class TestClassAttributes:
    def test_name(self):
        assert CodeSimplifierAgent.name == "code-simplifier"

    def test_lane(self):
        assert CodeSimplifierAgent.lane == AgentLane.DOMAIN

    def test_default_tier(self):
        assert CodeSimplifierAgent.default_tier == "high"

    def test_tools(self):
        assert "file_read" in CodeSimplifierAgent.tools
        assert "file_write" in CodeSimplifierAgent.tools
        assert "bash" in CodeSimplifierAgent.tools

    def test_icon(self):
        assert CodeSimplifierAgent.icon == "🧹"

    def test_system_prompt_not_empty(self):
        agent = CodeSimplifierAgent(model_router=MagicMock(), config={})
        assert len(agent.system_prompt) > 0
        assert "代码重构专家" in agent.system_prompt
        assert "单一职责" in agent.system_prompt


# ── _run ──────────────────────────────────────────────────────────

class TestRun:
    @pytest.mark.asyncio
    async def test_run_with_no_relevant_files(self, make_agent, make_context):
        """No relevant files → prompt is built but no file content appended."""
        agent = make_agent()
        ctx = make_context([])

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = MagicMock(content="简化建议：...")
            prompt = [{"role": "system", "content": agent.system_prompt}]
            result = await agent._run(ctx, prompt)

        assert result == "简化建议：..."
        mock_call.assert_called_once()
        call_kwargs = mock_call.call_args.kwargs
        assert call_kwargs["task_type"] == "code_review"
        assert call_kwargs["complexity"] == "high"

    @pytest.mark.asyncio
    async def test_run_with_relevant_files(self, make_agent, make_context, tmp_path):
        """With relevant files, file content is prepended before simplify hint."""
        (tmp_path / "foo.py").write_text("def foo():\n    pass\n", encoding="utf-8")
        agent = make_agent()
        ctx = make_context([tmp_path / "foo.py"])

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = MagicMock(content="分析完成")
            prompt = [{"role": "system", "content": agent.system_prompt}]
            await agent._run(ctx, prompt)


        call_kwargs = mock_call.call_args.kwargs
        messages = call_kwargs["messages"]
        user_msgs = [m.content for m in messages if m.role == "user"]
        combined = "\n".join(user_msgs)
        assert "foo.py" in combined
        assert "简化建议" in combined or "分析" in combined

    @pytest.mark.asyncio
    async def test_run_with_file_read_error(self, make_agent, make_context, tmp_path):
        """A file that raises an exception on read is skipped gracefully."""
        (tmp_path / "good.py").write_text("def good():\n    return 1\n", encoding="utf-8")
        agent = make_agent()
        ctx = make_context([tmp_path / "good.py"])


        def raise_on_good(path, *args, **kwargs):
            if "good.py" in str(path):
                raise OSError("read error")
            return MagicMock(__enter__=lambda s: MagicMock(read=lambda: "code"), __exit__=lambda *a: None)

        with patch("builtins.open", side_effect=raise_on_good):
            with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = MagicMock(content="ok")
                prompt = [{"role": "system", "content": agent.system_prompt}]
                await agent._run(ctx, prompt)


        # Should not raise; call_model should still have been called
        mock_call.assert_called_once()


    @pytest.mark.asyncio
    async def test_run_call_model_receives_messages(self, make_agent, make_context):
        """The prompt list is converted to Message objects before calling the model."""
        agent = make_agent()
        ctx = make_context([])

        with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = MagicMock(content="done")
            prompt = [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
            ]
            await agent._run(ctx, prompt)


        call_kwargs = mock_call.call_args.kwargs
        messages = call_kwargs["messages"]
        roles = [m.role for m in messages]
        assert "system" in roles
        assert "user" in roles
        assert mock_call.call_args.kwargs["task_type"] == "code_review"


# ── _post_process ─────────────────────────────────────────────────

class TestPostProcess:
    def test_post_process_returns_completed_output(self, make_agent):
        agent = make_agent()
        ctx = MagicMock(spec=AgentContext)
        output = agent._post_process("简化结果：xxx", ctx)

        assert output.agent_name == "code-simplifier"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "简化结果：xxx"
        assert "应用简化建议" in output.recommendations
        assert "运行测试验证" in output.recommendations

    def test_post_process_empty_result(self, make_agent):
        agent = make_agent()
        ctx = MagicMock(spec=AgentContext)
        output = agent._post_process("", ctx)
        assert output.status == AgentStatus.COMPLETED
        assert output.result == ""
