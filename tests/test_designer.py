"""Tests for designer.py"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.designer import DesignerAgent

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def mock_model_router():
    """Create a mock model router."""
    router = MagicMock()
    router.route_and_call = AsyncMock()
    return router


@pytest.fixture
def designer_agent(mock_model_router):
    """Create a DesignerAgent instance."""
    return DesignerAgent(model_router=mock_model_router)


@pytest.fixture
def agent_context(tmp_path):
    """Create an AgentContext for testing."""
    return AgentContext(
        project_path=tmp_path,
        task_description="Design UI for user dashboard",
    )


# ── DesignerAgent Class Attributes ────────────────────────────────


class TestDesignerAgentAttributes:
    def test_name(self, designer_agent):
        assert designer_agent.name == "designer"

    def test_description(self, designer_agent):
        assert "UI/UX" in designer_agent.description

    def test_lane(self, designer_agent):
        assert designer_agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, designer_agent):
        assert designer_agent.default_tier == "medium"

    def test_icon(self, designer_agent):
        assert designer_agent.icon == "🎨"

    def test_tools(self, designer_agent):
        assert "file_read" in designer_agent.tools
        assert "file_write" in designer_agent.tools


# ── system_prompt Property ─────────────────────────────────────────


class TestDesignerAgentSystemPrompt:
    def test_system_prompt_not_empty(self, designer_agent):
        prompt = designer_agent.system_prompt
        assert len(prompt) > 0

    def test_system_prompt_contains_role(self, designer_agent):
        prompt = designer_agent.system_prompt
        assert "UI/UX 设计师" in prompt

    def test_system_prompt_contains_capabilities(self, designer_agent):
        prompt = designer_agent.system_prompt
        assert "UI 设计" in prompt
        assert "UX 设计" in prompt
        assert "组件设计" in prompt

    def test_system_prompt_contains_principles(self, designer_agent):
        prompt = designer_agent.system_prompt
        assert "用户优先" in prompt
        assert "一致性" in prompt


# ── _run Method ────────────────────────────────────────────────────


class TestDesignerAgentRun:
    @pytest.mark.asyncio
    async def test_run_basic(self, designer_agent, agent_context):
        """Test basic _run execution."""
        mock_response = MagicMock()
        mock_response.content = "## UI Design\n\n### Layout\n- Header\n- Content"

        designer_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a designer."}]

        result = await designer_agent._run(agent_context, prompt)

        assert "## UI Design" in result
        designer_agent.call_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_architect_output(self, designer_agent, tmp_path):
        """Test _run with architect output in previous_outputs."""
        mock_response = MagicMock()
        mock_response.content = "Design based on architecture."

        designer_agent.call_model = AsyncMock(return_value=mock_response)

        context = AgentContext(
            project_path=tmp_path,
            task_description="Design UI",
            previous_outputs={
                "architect": MagicMock(result="Architecture: React + Tailwind")
            },
        )

        prompt = [{"role": "system", "content": "You are a designer."}]

        await designer_agent._run(context, prompt)

        # Check that architect output was added to prompt
        call_args = designer_agent.call_model.call_args
        messages = call_args.kwargs["messages"]
        assert any("架构设计" in str(m) for m in messages)

    @pytest.mark.asyncio
    async def test_run_adds_design_hint(self, designer_agent, agent_context):
        """Test that _run adds design-specific hint to prompt."""
        mock_response = MagicMock()
        mock_response.content = "Design complete."

        designer_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a designer."}]

        await designer_agent._run(agent_context, prompt)

        call_args = designer_agent.call_model.call_args
        messages = call_args.kwargs["messages"]
        assert any("UI/UX" in str(m.content) for m in messages)

    @pytest.mark.asyncio
    async def test_run_uses_code_generation_task_type(self, designer_agent, agent_context):
        """Test that _run uses CODE_GENERATION task type."""
        mock_response = MagicMock()
        mock_response.content = "Design output."

        designer_agent.call_model = AsyncMock(return_value=mock_response)

        prompt = [{"role": "system", "content": "You are a designer."}]

        await designer_agent._run(agent_context, prompt)

        call_args = designer_agent.call_model.call_args
        # Check task_type was passed
        assert "task_type" in call_args.kwargs


# ── _post_process Method ───────────────────────────────────────────


class TestDesignerAgentPostProcess:
    def test_post_process_returns_output(self, designer_agent, agent_context):
        """Test that _post_process returns AgentOutput."""
        result = "## UI Design\n\n### Layout\n- Header\n- Content"

        output = designer_agent._post_process(result, agent_context)

        assert isinstance(output, AgentOutput)
        assert output.agent_name == "designer"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == result

    def test_post_process_recommendations(self, designer_agent, agent_context):
        """Test that _post_process includes recommendations."""
        result = "## UI Design"

        output = designer_agent._post_process(result, agent_context)

        assert len(output.recommendations) == 2
        assert any("组件" in r for r in output.recommendations)
        assert any("测试" in r for r in output.recommendations)

    def test_post_process_next_agent(self, designer_agent, agent_context):
        """Test that _post_process sets next_agent."""
        result = "## UI Design"

        output = designer_agent._post_process(result, agent_context)

        assert output.next_agent == "executor"
