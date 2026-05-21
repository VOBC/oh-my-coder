"""Tests for devops.py"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.devops import DevOpsAgent

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def mock_model_router():
    """Create a mock model router."""
    router = MagicMock()
    router.route_and_call = AsyncMock()
    return router


@pytest.fixture
def devops_agent(mock_model_router):
    """Create a DevOpsAgent instance."""
    return DevOpsAgent(model_router=mock_model_router)


@pytest.fixture
def agent_context(tmp_path):
    """Create an AgentContext for testing."""
    return AgentContext(
        project_path=tmp_path,
        task_description="Setup CI/CD pipeline",
    )


# ── DevOpsAgent Class Attributes ───────────────────────────────────


class TestDevOpsAgentAttributes:
    def test_name(self, devops_agent):
        assert devops_agent.name == "devops"

    def test_description(self, devops_agent):
        assert "CI/CD" in devops_agent.description

    def test_lane(self, devops_agent):
        assert devops_agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, devops_agent):
        assert devops_agent.default_tier == "medium"

    def test_icon(self, devops_agent):
        assert devops_agent.icon == "🚀"

    def test_tools(self, devops_agent):
        assert "file_read" in devops_agent.tools
        assert "file_write" in devops_agent.tools


# ── system_prompt Property ─────────────────────────────────────────


class TestDevOpsAgentSystemPrompt:
    def test_system_prompt_not_empty(self, devops_agent):
        prompt = devops_agent.system_prompt
        assert len(prompt) > 0

    def test_system_prompt_contains_role(self, devops_agent):
        prompt = devops_agent.system_prompt
        assert "DevOps 工程师" in prompt

    def test_system_prompt_contains_capabilities(self, devops_agent):
        prompt = devops_agent.system_prompt
        assert "CI/CD" in prompt
        assert "容器化" in prompt
        assert "部署" in prompt

    def test_system_prompt_contains_best_practices(self, devops_agent):
        prompt = devops_agent.system_prompt
        assert "GitHub Actions" in prompt
        assert "Dockerfile" in prompt


# ── _run Method ────────────────────────────────────────────────────


class TestDevOpsAgentRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, devops_agent, agent_context):
        """Test basic _run execution."""
        mock_response = MagicMock()
        mock_response.content = "name: CI Pipeline\non: push"

        devops_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a DevOps engineer."}]

        result = await devops_agent._run(agent_context, prompt)

        assert "name: CI Pipeline" in result
        devops_agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_architect_output(self, devops_agent, tmp_path):
        """Test _run with architect output in previous_outputs."""
        mock_response = MagicMock()
        mock_response.content = "CI/CD configuration based on architecture."

        devops_agent.call_model = AsyncMock(return_value=mock_response)

        context = AgentContext(
            project_path=tmp_path,
            task_description="Setup CI/CD",
            previous_outputs={
                "architect": MagicMock(result="Architecture: Python FastAPI")
            },
        )

        prompt = [{"role": "system", "content": "You are a DevOps engineer."}]

        await devops_agent._run(context, prompt)

        # Check that architect output was added to prompt
        call_args = devops_agent.call_model.call_args
        messages = call_args.kwargs["messages"]
        assert any("架构设计" in str(m) for m in messages)

    @pytest.mark.asyncio
    async def test_run_adds_devops_hint(self, devops_agent, agent_context):
        """Test that _run adds DevOps-specific hint to prompt."""
        mock_response = MagicMock()
        mock_response.content = "DevOps setup complete."

        devops_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a DevOps engineer."}]

        await devops_agent._run(agent_context, prompt)

        call_args = devops_agent.call_model.call_args
        messages = call_args.kwargs["messages"]
        assert any("DevOps" in str(m.content) for m in messages)

    @pytest.mark.asyncio
    async def test_run_uses_simple_qa_task_type(self, devops_agent, agent_context):
        """Test that _run uses SIMPLE_QA task type."""
        mock_response = MagicMock()
        mock_response.content = "Pipeline configured."

        devops_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a DevOps engineer."}]

        await devops_agent._run(agent_context, prompt)

        call_args = devops_agent.call_model.call_args
        assert "task_type" in call_args.kwargs


# ── _post_process Method ───────────────────────────────────────────


class TestDevOpsAgentPostProcess:
    def test_post_process_returns_output(self, devops_agent, agent_context):
        """Test that _post_process returns AgentOutput."""
        result = "name: CI Pipeline\non: push"

        output = devops_agent._post_process(result, agent_context)

        assert isinstance(output, AgentOutput)
        assert output.agent_name == "devops"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == result

    def test_post_process_recommendations(self, devops_agent, agent_context):
        """Test that _post_process includes recommendations."""
        result = "name: CI Pipeline"

        output = devops_agent._post_process(result, agent_context)

        assert len(output.recommendations) == 3
        assert any(".github/workflows/" in r for r in output.recommendations)
        assert any("Docker" in r for r in output.recommendations)
        assert any("Secrets" in r for r in output.recommendations)

    def test_post_process_next_agent(self, devops_agent, agent_context):
        """Test that _post_process sets next_agent."""
        result = "name: CI Pipeline"

        output = devops_agent._post_process(result, agent_context)

        assert output.next_agent == "executor"
