"""Tests for qa_tester.py"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.qa_tester import QATesterAgent

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def mock_model_router():
    """Create a mock model router."""
    router = MagicMock()
    router.route_and_call = AsyncMock()
    return router


@pytest.fixture
def qa_tester_agent(mock_model_router):
    """Create a QATesterAgent instance."""
    return QATesterAgent(model_router=mock_model_router)


@pytest.fixture
def agent_context(tmp_path):
    """Create an AgentContext for testing."""
    # Create some test files in the project path
    (tmp_path / "start.sh").write_text("#!/bin/bash\necho 'start'", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
    return AgentContext(
        project_path=tmp_path,
        task_description="Run end-to-end tests",
    )


# ── QATesterAgent Class Attributes ────────────────────────────────


class TestQATesterAgentAttributes:
    def test_name(self, qa_tester_agent):
        assert qa_tester_agent.name == "qa-tester"

    def test_description(self, qa_tester_agent):
        assert "QA" in qa_tester_agent.description

    def test_lane(self, qa_tester_agent):
        assert qa_tester_agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, qa_tester_agent):
        assert qa_tester_agent.default_tier == "medium"

    def test_icon(self, qa_tester_agent):
        assert qa_tester_agent.icon == "🛠️"

    def test_tools(self, qa_tester_agent):
        assert "bash" in qa_tester_agent.tools
        assert "file_read" in qa_tester_agent.tools


# ── system_prompt Property ─────────────────────────────────────────


class TestQATesterAgentSystemPrompt:
    def test_system_prompt_not_empty(self, qa_tester_agent):
        prompt = qa_tester_agent.system_prompt
        assert len(prompt) > 0

    def test_system_prompt_contains_role(self, qa_tester_agent):
        prompt = qa_tester_agent.system_prompt
        assert "QA 测试专家" in prompt

    def test_system_prompt_contains_capabilities(self, qa_tester_agent):
        prompt = qa_tester_agent.system_prompt
        assert "CLI 测试" in prompt
        assert "API 测试" in prompt
        assert "集成测试" in prompt

    def test_system_prompt_contains_principles(self, qa_tester_agent):
        prompt = qa_tester_agent.system_prompt
        assert "实际运行" in prompt
        assert "边界测试" in prompt


# ── _run Method ────────────────────────────────────────────────────


class TestQATesterAgentRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, qa_tester_agent, agent_context):
        """Test basic _run execution."""
        mock_response = MagicMock()
        mock_response.content = "## Test Results\n\n| 用例 | 状态 |\n| TC-01 | ✅ PASS |"

        qa_tester_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a QA tester."}]

        result = await qa_tester_agent._run(agent_context, prompt)

        assert "## Test Results" in result
        qa_tester_agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_detects_executables(self, qa_tester_agent, tmp_path):
        """Test that _run detects executable files in project."""
        # Create executable files
        (tmp_path / "run.sh").write_text("#!/bin/bash", encoding="utf-8")
        (tmp_path / "start_server.py").write_text("print('server')", encoding="utf-8")

        mock_response = MagicMock()
        mock_response.content = "Test plan generated."

        qa_tester_agent.call_model = AsyncMock(return_value=mock_response)

        context = AgentContext(
            project_path=tmp_path,
            task_description="Test the server",
        )

        prompt = [{"role": "system", "content": "You are a QA tester."}]

        await qa_tester_agent._run(context, prompt)

        # Check that call_model was called
        qa_tester_agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_detects_main_files(self, qa_tester_agent, tmp_path):
        """Test that _run detects main entry files."""
        # Create main files
        (tmp_path / "app.py").write_text("print('app')", encoding="utf-8")
        (tmp_path / "cli.py").write_text("print('cli')", encoding="utf-8")

        mock_response = MagicMock()
        mock_response.content = "Entry points identified."

        qa_tester_agent.call_model = AsyncMock(return_value=mock_response)

        context = AgentContext(
            project_path=tmp_path,
            task_description="Test CLI",
        )

        prompt = [{"role": "system", "content": "You are a QA tester."}]

        result = await qa_tester_agent._run(context, prompt)

        assert result == "Entry points identified."

    @pytest.mark.asyncio
    async def test_run_adds_test_info(self, qa_tester_agent, agent_context):
        """Test that _run adds test environment info to prompt."""
        mock_response = MagicMock()
        mock_response.content = "Test complete."

        qa_tester_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a QA tester."}]

        await qa_tester_agent._run(agent_context, prompt)

        call_args = qa_tester_agent.call_model.call_args
        messages = call_args.kwargs["messages"]
        # Check that test environment info was added
        assert any("测试环境" in str(m.content) for m in messages)

    @pytest.mark.asyncio
    async def test_run_uses_testing_task_type(self, qa_tester_agent, agent_context):
        """Test that _run uses TESTING task type."""
        mock_response = MagicMock()
        mock_response.content = "Test plan."

        qa_tester_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a QA tester."}]

        await qa_tester_agent._run(agent_context, prompt)

        call_args = qa_tester_agent.call_model.call_args
        assert "task_type" in call_args.kwargs


# ── _post_process Method ───────────────────────────────────────────


class TestQATesterAgentPostProcess:
    def test_post_process_returns_output(self, qa_tester_agent, agent_context):
        """Test that _post_process returns AgentOutput."""
        result = "## Test Results\n\n| 用例 | 状态 |\n| TC-01 | ✅ PASS |"

        output = qa_tester_agent._post_process(result, agent_context)

        assert isinstance(output, AgentOutput)
        assert output.agent_name == "qa-tester"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == result

    def test_post_process_recommendations(self, qa_tester_agent, agent_context):
        """Test that _post_process includes recommendations."""
        result = "## Test Results"

        output = qa_tester_agent._post_process(result, agent_context)

        assert len(output.recommendations) == 2
        assert any("修复" in r for r in output.recommendations)
        assert any("自动化测试" in r for r in output.recommendations)

    def test_post_process_no_next_agent(self, qa_tester_agent, agent_context):
        """Test that _post_process does not set next_agent for QA."""
        result = "## Test Results"

        output = qa_tester_agent._post_process(result, agent_context)

        # QA tester doesn't have a next_agent recommendation
        assert output.next_agent is None


# ── Integration Tests ──────────────────────────────────────────────


class TestQATesterAgentIntegration:
    @pytest.mark.asyncio
    async def test_full_workflow(self, qa_tester_agent, agent_context):
        """Test the full workflow from _run to _post_process."""
        mock_response = MagicMock()
        mock_response.content = "All tests passed."

        qa_tester_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a QA tester."}]

        # Run
        result = await qa_tester_agent._run(agent_context, prompt)
        assert result == "All tests passed."

        # Post-process
        output = qa_tester_agent._post_process(result, agent_context)
        assert output.status == AgentStatus.COMPLETED
        assert output.result == "All tests passed."

    @pytest.mark.asyncio
    async def test_run_with_no_executables(self, qa_tester_agent, tmp_path):
        """Test _run when no executable files are found."""
        mock_response = MagicMock()
        mock_response.content = "No entry points found, testing skipped."

        qa_tester_agent.call_model = AsyncMock(return_value=mock_response)

        context = AgentContext(
            project_path=tmp_path,  # Empty directory
            task_description="Test the project",
        )

        prompt = [{"role": "system", "content": "You are a QA tester."}]

        result = await qa_tester_agent._run(context, prompt)
        assert result == "No entry points found, testing skipped."
