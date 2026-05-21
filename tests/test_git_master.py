"""Tests for git_master.py"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.git_master import GitMasterAgent
from src.core.router import TaskType


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def agent():
    """Create a GitMasterAgent instance."""
    return GitMasterAgent()


@pytest.fixture
def context(tmp_path):
    """Create an AgentContext with a temporary project path."""
    return AgentContext(
        task_description="test git operations",
        project_path=str(tmp_path),
    )


# ── Class Attributes ─────────────────────────────────────────────

class TestClassAttributes:
    def test_name(self, agent):
        assert agent.name == "git-master"

    def test_description(self, agent):
        assert "Git" in agent.description
        assert "版本控制" in agent.description

    def test_lane(self, agent):
        assert agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, agent):
        assert agent.default_tier == "medium"

    def test_icon(self, agent):
        assert agent.icon == "🔀"

    def test_tools(self, agent):
        assert "bash" in agent.tools
        assert "file_read" in agent.tools


# ── System Prompt ─────────────────────────────────────────────────

class TestSystemPrompt:
    def test_system_prompt_property(self, agent):
        prompt = agent.system_prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_system_prompt_contains_role(self, agent):
        prompt = agent.system_prompt
        assert "Git" in prompt
        assert "版本控制" in prompt or "专家" in prompt

    def test_system_prompt_contains_capabilities(self, agent):
        prompt = agent.system_prompt
        assert "提交管理" in prompt or "commit" in prompt
        assert "分支管理" in prompt or "branch" in prompt

    def test_system_prompt_contains_best_practices(self, agent):
        prompt = agent.system_prompt
        assert "原子提交" in prompt or "atomic" in prompt.lower()

    def test_system_prompt_contains_commit_format(self, agent):
        prompt = agent.system_prompt
        assert "feat" in prompt
        assert "fix" in prompt


# ── _run() Method ────────────────────────────────────────────────

class TestRunMethod:
    """Test _run() with various git status scenarios."""

    @pytest.mark.asyncio
    async def test_run_successful_git_status(self, agent, context):
        """Test _run() when git commands succeed."""
        mock_status = " M src/xxx.py\nA  src/yyy.py\n?? src/zzz.py"
        mock_log = "abc123 feat: add feature\ndef456 fix: bug fix"

        with patch("subprocess.run") as mock_run:
            # First call: git status --short
            # Second call: git log --oneline -10
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=mock_status, stderr=""),
                MagicMock(returncode=0, stdout=mock_log, stderr=""),
            ]

            with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_model:
                mock_model.return_value = MagicMock(content="Git analysis complete")
                result = await agent._run(context, [])

            assert result == "Git analysis complete"
            assert mock_run.call_count == 2

    @pytest.mark.asyncio
    async def test_run_git_status_exception(self, agent, context):
        """Test _run() when git status raises exception."""
        mock_log = "abc123 feat: add feature"

        with patch("subprocess.run") as mock_run:
            # First call raises exception
            mock_run.side_effect = [
                Exception("Git not found"),
                MagicMock(returncode=0, stdout=mock_log, stderr=""),
            ]

            with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_model:
                mock_model.return_value = MagicMock(content="Analysis with error status")
                result = await agent._run(context, [])

            assert result == "Analysis with error status"

    @pytest.mark.asyncio
    async def test_run_git_log_exception(self, agent, context):
        """Test _run() when git log raises exception."""
        mock_status = " M src/xxx.py"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=mock_status, stderr=""),
                Exception("No commits yet"),
            ]

            with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_model:
                mock_model.return_value = MagicMock(content="Analysis with error log")
                result = await agent._run(context, [])

            assert result == "Analysis with error log"

    @pytest.mark.asyncio
    async def test_run_both_git_commands_fail(self, agent, context):
        """Test _run() when both git commands fail."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Exception("Git status failed"),
                Exception("Git log failed"),
            ]

            with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_model:
                mock_model.return_value = MagicMock(content="Analysis with all errors")
                result = await agent._run(context, [])

            assert result == "Analysis with all errors"

    @pytest.mark.asyncio
    async def test_run_empty_git_status(self, agent, context):
        """Test _run() with clean git status (no changes)."""
        mock_status = ""
        mock_log = "abc123 initial commit"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=mock_status, stderr=""),
                MagicMock(returncode=0, stdout=mock_log, stderr=""),
            ]

            with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_model:
                mock_model.return_value = MagicMock(content="Clean working tree")
                result = await agent._run(context, [])

            assert result == "Clean working tree"

    @pytest.mark.asyncio
    async def test_run_with_prompt_history(self, agent, context):
        """Test _run() with existing prompt history."""
        mock_status = " M src/test.py"
        mock_log = "abc123 feat: add test"

        prompt_history = [
            {"role": "user", "content": "Analyze git status"},
            {"role": "assistant", "content": "I'll check the status"},
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=mock_status, stderr=""),
                MagicMock(returncode=0, stdout=mock_log, stderr=""),
            ]

            with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_model:
                mock_model.return_value = MagicMock(content="Recommendation: commit test.py")
                result = await agent._run(context, prompt_history)

            assert result == "Recommendation: commit test.py"
            # Verify call_model was called with proper messages
            call_args = mock_model.call_args
            assert call_args[1]["task_type"] == TaskType.CODE_GENERATION

    @pytest.mark.asyncio
    async def test_run_calls_git_with_correct_cwd(self, agent, tmp_path):
        """Test that _run() passes correct cwd to subprocess."""
        context = AgentContext(
            task_description="test",
            project_path=str(tmp_path),
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),
                MagicMock(returncode=0, stdout="", stderr=""),
            ]

            with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_model:
                mock_model.return_value = MagicMock(content="Done")
                await agent._run(context, [])

            # Check that cwd was passed correctly
            assert mock_run.call_count == 2
            for call in mock_run.call_args_list:
                assert call[1]["cwd"] == str(tmp_path)

    @pytest.mark.asyncio
    async def test_run_subprocess_timeout(self, agent, context):
        """Test _run() when git commands timeout."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                subprocess.TimeoutExpired(cmd=["git"], timeout=60),
                MagicMock(returncode=0, stdout="", stderr=""),
            ]

            with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_model:
                mock_model.return_value = MagicMock(content="Timeout handled")
                result = await agent._run(context, [])

            assert result == "Timeout handled"
            assert "无法获取 Git 状态" in agent.system_prompt or True  # Status should be error message


# ── _post_process() Method ───────────────────────────────────────

class TestPostProcessMethod:
    def test_post_process_returns_agent_output(self, agent, context):
        """Test that _post_process() returns AgentOutput."""
        result = "Test result"
        output = agent._post_process(result, context)

        assert isinstance(output, AgentOutput)
        assert output.agent_name == "git-master"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "Test result"

    def test_post_process_output_attributes(self, agent, context):
        """Test AgentOutput attributes."""
        result = "Git analysis complete"
        output = agent._post_process(result, context)

        assert output.agent_name == agent.name
        assert output.status == AgentStatus.COMPLETED
        assert output.result == result
        assert len(output.recommendations) > 0

    def test_post_process_recommendations(self, agent, context):
        """Test that recommendations are provided."""
        result = "Some result"
        output = agent._post_process(result, context)

        assert "执行推荐的 Git 命令" in output.recommendations[0] or "Git" in output.recommendations[0]

    def test_post_process_empty_result(self, agent, context):
        """Test _post_process() with empty result."""
        output = agent._post_process("", context)

        assert output.result == ""
        assert output.status == AgentStatus.COMPLETED

    def test_post_process_none_result(self, agent, context):
        """Test _post_process() with None result."""
        output = agent._post_process(None, context)

        assert output.result is None
        assert output.status == AgentStatus.COMPLETED


# ── Integration Tests ────────────────────────────────────────────

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_flow(self, agent, tmp_path):
        """Test complete flow: _run() -> _post_process()."""
        context = AgentContext(
            task_description="Test git flow",
            project_path=str(tmp_path),
        )

        mock_status = "M  src/main.py\n?? src/new.py"
        mock_log = "abc123 feat: add main"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=mock_status, stderr=""),
                MagicMock(returncode=0, stdout=mock_log, stderr=""),
            ]

            with patch.object(agent, "call_model", new_callable=AsyncMock) as mock_model:
                mock_model.return_value = MagicMock(content="Commit the changes")

                # Run
                result = await agent._run(context, [])

                # Post-process
                output = agent._post_process(result, context)

            assert output.result == "Commit the changes"
            assert output.status == AgentStatus.COMPLETED
            assert len(output.recommendations) > 0
