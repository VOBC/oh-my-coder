"""Tests for code_reviewer.py"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.code_reviewer import CodeReviewerAgent
from src.agents.base import AgentContext, AgentOutput, AgentStatus


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def agent():
    """Create a CodeReviewerAgent instance."""
    return CodeReviewerAgent()


@pytest.fixture
def mock_context(tmp_path):
    """Create a mock AgentContext with relevant_files."""
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Review code"
    ctx.project_path = tmp_path

    # Create some test files
    file1 = tmp_path / "module1.py"
    file1.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    file2 = tmp_path / "module2.py"
    file2.write_text("import os\n\ndef func():\n    pass\n", encoding="utf-8")

    ctx.relevant_files = [file1, file2]
    return ctx


@pytest.fixture
def mock_context_no_files():
    """Create a mock AgentContext with no relevant_files."""
    ctx = MagicMock(spec=AgentContext)
    ctx.task_description = "Review code"
    ctx.project_path = "/fake/path"
    ctx.relevant_files = []
    return ctx


@pytest.fixture
def mock_prompt():
    """Create a mock prompt list."""
    return [{"role": "user", "content": "Initial prompt"}]


# ── Test Class Attributes ────────────────────────────────────────

class TestCodeReviewerAgentAttributes:
    def test_name(self, agent):
        assert agent.name == "code-reviewer"

    def test_description(self, agent):
        assert "代码审查" in agent.description

    def test_lane(self, agent):
        from src.agents.base import AgentLane
        assert agent.lane == AgentLane.REVIEW

    def test_default_tier(self, agent):
        assert agent.default_tier == "high"

    def test_icon(self, agent):
        assert agent.icon == "👀"

    def test_tools(self, agent):
        assert "file_read" in agent.tools
        assert "search" in agent.tools


# ── Test system_prompt Property ──────────────────────────────────

class TestSystemPrompt:
    def test_system_prompt_not_empty(self, agent):
        prompt = agent.system_prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_system_prompt_contains_keywords(self, agent):
        prompt = agent.system_prompt
        assert "代码审查" in prompt
        assert "审查维度" in prompt
        assert "代码质量" in prompt
        assert "安全" in prompt

    def test_system_prompt_contains_output_format(self, agent):
        prompt = agent.system_prompt
        assert "总体评价" in prompt
        assert "必须修复" in prompt
        assert "建议改进" in prompt
        assert "安全检查" in prompt


# ── Test _run() Method ────────────────────────────────────────────

class TestRunMethod:
    @pytest.mark.asyncio
    async def test_run_no_relevant_files(self, agent, mock_context_no_files, mock_prompt):
        """Test _run when there are no relevant files."""
        with patch("src.models.base.Message"):
            mock_instance = MagicMock()
            mock_instance.content = "Review result"
            agent.call_model = AsyncMock(return_value=mock_instance)

            result = await agent._run(mock_context_no_files, mock_prompt)

            assert result == "Review result"
            agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_relevant_files(self, agent, mock_context, mock_prompt):
        """Test _run with relevant files."""
        with patch("src.models.base.Message") as mock_message_class:
            mock_instance = MagicMock()
            mock_instance.content = "Review result"
            agent.call_model = AsyncMock(return_value=mock_instance)

            result = await agent._run(mock_context, mock_prompt)

            assert result == "Review result"
            agent.call_model.assert_called_once()

            # Verify prompt was modified
            assert len(mock_prompt) > 1

    @pytest.mark.asyncio
    async def test_run_file_read_error(self, agent, tmp_path, mock_prompt):
        """Test _run when file read fails."""
        ctx = MagicMock(spec=AgentContext)
        ctx.task_description = "Review code"
        ctx.project_path = tmp_path

        # Create a file that will fail to read
        file1 = tmp_path / "bad_file.py"
        file1.write_text("content", encoding="utf-8")
        ctx.relevant_files = [file1]

        with patch("builtins.open", side_effect=Exception("Read error")):
            with patch("src.models.base.Message"):
                mock_instance = MagicMock()
                mock_instance.content = "Review result"
                agent.call_model = AsyncMock(return_value=mock_instance)

                result = await agent._run(ctx, mock_prompt)

                assert result == "Review result"

    @pytest.mark.asyncio
    async def test_run_multiple_files(self, agent, tmp_path, mock_prompt):
        """Test _run with multiple files."""
        ctx = MagicMock(spec=AgentContext)
        ctx.task_description = "Review code"
        ctx.project_path = tmp_path

        files = []
        for i in range(5):
            f = tmp_path / f"module{i}.py"
            f.write_text(f"def func{i}():\n    return {i}\n", encoding="utf-8")
            files.append(f)
        ctx.relevant_files = files

        with patch("src.models.base.Message"):
            mock_instance = MagicMock()
            mock_instance.content = "Review result"
            agent.call_model = AsyncMock(return_value=mock_instance)

            result = await agent._run(ctx, mock_prompt)

            assert result == "Review result"
            # Check that code_parts were added
            code_added = any("待审查代码" in msg.get("content", "") for msg in mock_prompt)
            assert code_added

    @pytest.mark.asyncio
    async def test_run_more_than_10_files(self, agent, tmp_path, mock_prompt):
        """Test _run with more than 10 files (should limit to 10)."""
        ctx = MagicMock(spec=AgentContext)
        ctx.task_description = "Review code"
        ctx.project_path = tmp_path

        files = []
        for i in range(15):
            f = tmp_path / f"module{i}.py"
            f.write_text(f"def func{i}():\n    pass\n", encoding="utf-8")
            files.append(f)
        ctx.relevant_files = files

        with patch("src.models.base.Message"):
            mock_instance = MagicMock()
            mock_instance.content = "Review result"
            agent.call_model = AsyncMock(return_value=mock_instance)

            result = await agent._run(ctx, mock_prompt)

            assert result == "Review result"
            # Should only process first 10 files
            call_args = mock_prompt[-2]  # The code review content
            assert "module9.py" in call_args.get("content", "")


# ── Test _post_process() Method ──────────────────────────────────

class TestPostProcessMethod:
    def test_post_process_basic(self, agent, mock_context):
        """Test _post_process returns correct AgentOutput."""
        result = "Review result content"
        output = agent._post_process(result, mock_context)

        assert isinstance(output, AgentOutput)
        assert output.agent_name == "code-reviewer"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == result
        assert len(output.recommendations) == 2

    def test_post_process_recommendations(self, agent, mock_context):
        """Test _post_process recommendations."""
        result = "Review result"
        output = agent._post_process(result, mock_context)

        assert "根据审查结果修复问题" in output.recommendations
        assert "使用 executor 改进代码" in output.recommendations

    def test_post_process_empty_result(self, agent, mock_context):
        """Test _post_process with empty result."""
        output = agent._post_process("", mock_context)

        assert output.status == AgentStatus.COMPLETED
        assert output.result == ""

    def test_post_process_none_result(self, agent, mock_context):
        """Test _post_process with None result."""
        output = agent._post_process(None, mock_context)

        assert output.status == AgentStatus.COMPLETED
        assert output.result is None


# ── Test Integration ─────────────────────────────────────────────

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_workflow(self, agent, mock_context, mock_prompt):
        """Test full workflow: _run + _post_process."""
        with patch("src.models.base.Message"):
            mock_instance = MagicMock()
            mock_instance.content = "## 总体评价\n⭐⭐⭐⭐☆\n\nGood code"
            agent.call_model = AsyncMock(return_value=mock_instance)

            # Run
            result = await agent._run(mock_context, mock_prompt)
            assert "总体评价" in result

            # Post-process
            output = agent._post_process(result, mock_context)
            assert output.status == AgentStatus.COMPLETED
            assert "总体评价" in output.result
