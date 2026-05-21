"""
APIAgent 单元测试（纯逻辑，不调 API）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.api_agent import APIAgent
from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus

# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────


@pytest.fixture
def api_agent():
    """Create an APIAgent instance without model_router."""
    return APIAgent()


@pytest.fixture
def mock_context(tmp_path):
    """Create a basic AgentContext for testing."""
    return AgentContext(
        project_path=tmp_path,
        task_description="Design a REST API for user management",
    )


@pytest.fixture
def mock_context_with_architect(tmp_path):
    """Create an AgentContext with previous architect output."""
    return AgentContext(
        project_path=tmp_path,
        task_description="Design a REST API",
        previous_outputs={
            "architect": AgentOutput(
                agent_name="architect",
                status=AgentStatus.COMPLETED,
                result="System architecture: microservices with FastAPI",
            )
        },
    )


# ─────────────────────────────────────────────────────────────────
# APIAgent Properties
# ─────────────────────────────────────────────────────────────────


class TestAPIAgentProperties:
    """Test APIAgent class properties."""

    def test_name(self, api_agent):
        assert api_agent.name == "api"

    def test_description(self, api_agent):
        assert "REST API" in api_agent.description

    def test_lane(self, api_agent):
        assert api_agent.lane == AgentLane.DOMAIN

    def test_default_tier(self, api_agent):
        assert api_agent.default_tier == "medium"

    def test_icon(self, api_agent):
        assert api_agent.icon == "🔌"

    def test_tools(self, api_agent):
        assert "file_read" in api_agent.tools
        assert "file_write" in api_agent.tools


class TestAPIAgentSystemPrompt:
    """Test APIAgent system_prompt property."""

    def test_system_prompt_is_string(self, api_agent):
        assert isinstance(api_agent.system_prompt, str)

    def test_system_prompt_contains_restful(self, api_agent):
        assert "RESTful" in api_agent.system_prompt

    def test_system_prompt_contains_http_methods(self, api_agent):
        prompt = api_agent.system_prompt
        assert "GET" in prompt
        assert "POST" in prompt
        assert "PUT" in prompt
        assert "DELETE" in prompt

    def test_system_prompt_contains_fastapi(self, api_agent):
        assert "FastAPI" in api_agent.system_prompt

    def test_system_prompt_contains_authentication(self, api_agent):
        prompt = api_agent.system_prompt
        assert "JWT" in prompt or "认证" in prompt


# ─────────────────────────────────────────────────────────────────
# APIAgent._run()
# ─────────────────────────────────────────────────────────────────


class TestAPIAgentRun:
    """Test APIAgent._run() method."""

    @pytest.mark.asyncio
    async def test_run_without_architect(self, api_agent, mock_context):
        """Test _run without previous architect output."""
        mock_response = MagicMock()
        mock_response.content = "API design result"

        with patch.object(
            api_agent, "call_model", new_callable=AsyncMock, return_value=mock_response
        ) as mock_call:
            prompt = [{"role": "system", "content": "test"}]
            result = await api_agent._run(mock_context, prompt)

            assert result == "API design result"
            mock_call.assert_called_once()

            # Verify the API hint was added
            call_args = mock_call.call_args
            messages = call_args.kwargs.get("messages", call_args[0][0] if call_args[0] else [])
            last_message = messages[-1]
            assert "RESTful API" in last_message.content

    @pytest.mark.asyncio
    async def test_run_with_architect(self, api_agent, mock_context_with_architect):
        """Test _run with previous architect output."""
        mock_response = MagicMock()
        mock_response.content = "API design with architecture context"

        with patch.object(
            api_agent, "call_model", new_callable=AsyncMock, return_value=mock_response
        ) as mock_call:
            prompt = [{"role": "system", "content": "test"}]
            result = await api_agent._run(mock_context_with_architect, prompt)

            assert result == "API design with architecture context"
            mock_call.assert_called_once()

            # Verify architect output was added to prompt
            call_args = mock_call.call_args
            messages = call_args.kwargs.get("messages", call_args[0][0] if call_args[0] else [])
            # Find the message with architect content (Message objects have .content attribute)
            architect_msg = next(
                (m for m in messages if "架构设计" in getattr(m, "content", "")), None
            )
            assert architect_msg is not None
            assert "microservices" in architect_msg.content

    @pytest.mark.asyncio
    async def test_run_uses_task_type_code_generation(self, api_agent, mock_context):
        """Test that _run uses TaskType.CODE_GENERATION."""
        from src.core.router import TaskType

        mock_response = MagicMock()
        mock_response.content = "result"

        with patch.object(
            api_agent, "call_model", new_callable=AsyncMock, return_value=mock_response
        ) as mock_call:
            prompt = [{"role": "system", "content": "test"}]
            await api_agent._run(mock_context, prompt)

            call_args = mock_call.call_args
            task_type = call_args.kwargs.get("task_type")
            assert task_type == TaskType.CODE_GENERATION


# ─────────────────────────────────────────────────────────────────
# APIAgent._post_process()
# ─────────────────────────────────────────────────────────────────


class TestAPIAgentPostProcess:
    """Test APIAgent._post_process() method."""

    def test_post_process_returns_agent_output(self, api_agent, mock_context):
        """Test that _post_process returns an AgentOutput."""
        result = "API endpoints designed"
        output = api_agent._post_process(result, mock_context)

        assert isinstance(output, AgentOutput)
        assert output.agent_name == "api"
        assert output.status == AgentStatus.COMPLETED
        assert output.result == result

    def test_post_process_includes_recommendations(self, api_agent, mock_context):
        """Test that _post_process includes recommendations."""
        output = api_agent._post_process("result", mock_context)

        assert len(output.recommendations) == 3
        assert any("app.py" in r for r in output.recommendations)
        assert any("单元测试" in r for r in output.recommendations)

    def test_post_process_sets_next_agent(self, api_agent, mock_context):
        """Test that _post_process sets next_agent to executor."""
        output = api_agent._post_process("result", mock_context)

        assert output.next_agent == "executor"
