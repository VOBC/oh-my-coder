"""Tests for src/agents/performance.py"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentContext, AgentLane, AgentOutput, AgentStatus
from src.agents.performance import PerformanceAgent
from src.models.base import Message

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def agent() -> PerformanceAgent:
    return PerformanceAgent()


@pytest.fixture
def ctx_no_previous() -> AgentContext:
    return AgentContext(
        project_path=Path("/fake/project"),
        task_description="Analyze performance",
    )


@dataclass
class FakeAgentOutput:
    result: str


# ─────────────────────────────────────────────────────────────
# Test Agent Properties
# ─────────────────────────────────────────────────────────────


class TestPerformanceAgentProperties:
    def test_name(self, agent: PerformanceAgent) -> None:
        assert agent.name == "performance"

    def test_description(self, agent: PerformanceAgent) -> None:
        assert isinstance(agent.description, str)
        assert len(agent.description) > 0
        assert "性能" in agent.description

    def test_lane(self, agent: PerformanceAgent) -> None:
        assert agent.lane == AgentLane.BUILD_ANALYSIS

    def test_default_tier(self, agent: PerformanceAgent) -> None:
        assert agent.default_tier == "high"

    def test_icon(self, agent: PerformanceAgent) -> None:
        assert agent.icon == "⚡"
        assert isinstance(agent.icon, str)

    def test_tools(self, agent: PerformanceAgent) -> None:
        assert "file_read" in agent.tools
        assert "file_write" in agent.tools


# ─────────────────────────────────────────────────────────────
# Test system_prompt
# ─────────────────────────────────────────────────────────────


class TestSystemPrompt:
    def test_system_prompt_is_string(self, agent: PerformanceAgent) -> None:
        prompt = agent.system_prompt
        assert isinstance(prompt, str)

    def test_system_prompt_not_empty(self, agent: PerformanceAgent) -> None:
        prompt = agent.system_prompt
        assert len(prompt) > 100

    def test_system_prompt_contains_key_topics(self, agent: PerformanceAgent) -> None:
        prompt = agent.system_prompt
        # Check that key performance topics are covered
        assert "性能" in prompt
        assert "数据库" in prompt or "查询" in prompt or "慢查询" in prompt
        assert "缓存" in prompt
        assert "并发" in prompt or "异步" in prompt

    def test_system_prompt_contains_output_format(self, agent: PerformanceAgent) -> None:
        prompt = agent.system_prompt
        assert "性能报告" in prompt or "优化" in prompt

    def test_system_prompt_contains_role(self, agent: PerformanceAgent) -> None:
        prompt = agent.system_prompt
        assert "性能优化" in prompt or "专家" in prompt


# ─────────────────────────────────────────────────────────────
# Test _run (async)
# ─────────────────────────────────────────────────────────────


def _make_mock_response(content: str = "done") -> MagicMock:
    mock = MagicMock()
    mock.content = content
    return mock


class TestRunAsync:
    @pytest.mark.asyncio
    async def test_run_without_previous_outputs(
        self, agent: PerformanceAgent, ctx_no_previous: AgentContext
    ) -> None:
        """_run calls call_model and returns response.content when no previous_outputs."""
        mock_response = _make_mock_response("Performance analysis complete.")

        async def mock_call_model(**kwargs: Any) -> MagicMock:
            return mock_response

        agent.call_model = mock_call_model  # type: ignore[method-assign]

        result = await agent._run(ctx_no_previous, [{"role": "user", "content": "test"}])

        assert result == mock_response.content

    @pytest.mark.asyncio
    async def test_run_injects_previous_outputs_explore(
        self, agent: PerformanceAgent, ctx_no_previous: AgentContext
    ) -> None:
        """_run injects explore result into prompt when previous_outputs['explore'] exists."""
        ctx_no_previous.previous_outputs = {
            "explore": FakeAgentOutput(result="Project has 42 files, 3 modules.")
        }

        captured: list[Any] = []

        async def mock_call_model(**kwargs: Any) -> MagicMock:
            captured.extend(kwargs.get("messages", []))
            return _make_mock_response()

        agent.call_model = mock_call_model  # type: ignore[method-assign]

        await agent._run(ctx_no_previous, [{"role": "user", "content": "test"}])

        # Verify that the explore result was injected into prompt
        injected = [m.content for m in captured if "代码结构" in m.content]
        assert len(injected) == 1
        assert "42 files" in injected[0]

    @pytest.mark.asyncio
    async def test_run_truncates_long_explore_result(
        self, agent: PerformanceAgent, ctx_no_previous: AgentContext
    ) -> None:
        """_run truncates explore result to 3000 chars."""
        long_result = "x" * 5000
        ctx_no_previous.previous_outputs = {"explore": FakeAgentOutput(result=long_result)}

        captured: list[Any] = []

        async def mock_call_model(**kwargs: Any) -> MagicMock:
            captured.extend(kwargs.get("messages", []))
            return _make_mock_response()

        agent.call_model = mock_call_model  # type: ignore[method-assign]

        await agent._run(ctx_no_previous, [{"role": "user", "content": "test"}])

        injected = [m.content for m in captured if "代码结构" in m.content][0]
        # The explore result part should be truncated to 3000 chars
        # plus the "## 代码结构\n" prefix
        assert len(injected) <= 3010

    @pytest.mark.asyncio
    async def test_run_uses_code_generation_task_type(
        self, agent: PerformanceAgent, ctx_no_previous: AgentContext
    ) -> None:
        """_run calls call_model with task_type=CODE_GENERATION."""
        captured_task_types: list[str] = []

        async def mock_call_model(**kwargs: Any) -> MagicMock:
            captured_task_types.append(kwargs.get("task_type", ""))
            return _make_mock_response()

        agent.call_model = mock_call_model  # type: ignore[method-assign]

        await agent._run(ctx_no_previous, [{"role": "user", "content": "test"}])

        assert captured_task_types[0] == "code_generation"

    @pytest.mark.asyncio
    async def test_run_adds_performance_hint(
        self, agent: PerformanceAgent, ctx_no_previous: AgentContext
    ) -> None:
        """_run appends the performance analysis hint to prompt."""
        captured: list[Any] = []

        async def mock_call_model(**kwargs: Any) -> MagicMock:
            captured.extend(kwargs.get("messages", []))
            return _make_mock_response()

        agent.call_model = mock_call_model  # type: ignore[method-assign]

        await agent._run(ctx_no_previous, [{"role": "user", "content": "test"}])

        user_msgs = [m.content for m in captured if m.role == "user"]
        assert any("性能" in msg for msg in user_msgs)
        assert any("N+1" in msg or "慢查询" in msg for msg in user_msgs)

    @pytest.mark.asyncio
    async def test_run_converts_prompt_to_message_objects(
        self, agent: PerformanceAgent, ctx_no_previous: AgentContext
    ) -> None:
        """_run converts dict prompt items to Message objects before calling model."""
        captured: list[Any] = []

        async def mock_call_model(**kwargs: Any) -> MagicMock:
            captured.extend(kwargs.get("messages", []))
            return _make_mock_response()

        agent.call_model = mock_call_model  # type: ignore[method-assign]

        await agent._run(
            ctx_no_previous,
            [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Analyze this."},
            ],
        )

        # All items should be Message instances
        for msg in captured:
            assert isinstance(msg, Message)
        assert any(m.role == "system" for m in captured)
        assert any(m.role == "user" for m in captured)


# ─────────────────────────────────────────────────────────────
# Test _post_process
# ─────────────────────────────────────────────────────────────


class TestPostProcess:
    def test_returns_agent_output(self, agent: PerformanceAgent) -> None:
        result = agent._post_process("analysis result", None)
        assert isinstance(result, AgentOutput)

    def test_status_completed(self, agent: PerformanceAgent) -> None:
        result = agent._post_process("analysis result", None)
        assert result.status == AgentStatus.COMPLETED

    def test_result_equals_input(self, agent: PerformanceAgent) -> None:
        result_text = "Full performance analysis report."
        result = agent._post_process(result_text, None)
        assert result.result == result_text

    def test_agent_name(self, agent: PerformanceAgent) -> None:
        result = agent._post_process("done", None)
        assert result.agent_name == "performance"

    def test_recommendations_present(self, agent: PerformanceAgent) -> None:
        result = agent._post_process("done", None)
        assert len(result.recommendations) >= 3

    def test_recommendations_include_apm(self, agent: PerformanceAgent) -> None:
        result = agent._post_process("done", None)
        rec_texts = " ".join(result.recommendations)
        assert "APM" in rec_texts or "监控" in rec_texts

    def test_next_agent_executor(self, agent: PerformanceAgent) -> None:
        result = agent._post_process("done", None)
        assert result.next_agent == "executor"

    def test_timestamp_is_string(self, agent: PerformanceAgent) -> None:
        result = agent._post_process("done", None)
        assert isinstance(result.timestamp, str)
        assert len(result.timestamp) > 0


# ─────────────────────────────────────────────────────────────
# Test execute (inherited template method)
# ─────────────────────────────────────────────────────────────


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_agent_output(
        self, agent: PerformanceAgent, ctx_no_previous: AgentContext
    ) -> None:
        """execute() returns an AgentOutput with COMPLETED status."""
        mock_response = _make_mock_response("Performance report.")
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)

        # Patch route_and_call so call_model sets _last_model_response
        agent.model_router = MagicMock()
        agent.model_router.route_and_call = AsyncMock(return_value=mock_response)

        output = await agent.execute(ctx_no_previous)
        assert isinstance(output, AgentOutput)
        assert output.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_populates_usage(
        self, agent: PerformanceAgent, ctx_no_previous: AgentContext
    ) -> None:
        """execute() fills usage from cached ModelResponse."""
        mock_response = _make_mock_response("done")
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=200, total_tokens=300)

        # Patch route_and_call so call_model properly sets _last_model_response
        agent.model_router = MagicMock()
        agent.model_router.route_and_call = AsyncMock(return_value=mock_response)

        output = await agent.execute(ctx_no_previous)
        assert output.usage["prompt_tokens"] == 100
        assert output.usage["completion_tokens"] == 200

    @pytest.mark.asyncio
    async def test_execute_updates_status(
        self, agent: PerformanceAgent, ctx_no_previous: AgentContext
    ) -> None:
        """execute() transitions agent status to WORKING then COMPLETED."""
        mock_response = _make_mock_response("done")
        mock_response.usage = MagicMock(prompt_tokens=0, completion_tokens=0, total_tokens=0)

        agent.model_router = MagicMock()
        agent.model_router.route_and_call = AsyncMock(return_value=mock_response)
        agent.status = AgentStatus.IDLE

        await agent.execute(ctx_no_previous)
        assert agent.status == AgentStatus.COMPLETED


# ─────────────────────────────────────────────────────────────
# Test register_agent decorator
# ─────────────────────────────────────────────────────────────


class TestRegisterDecorator:
    def test_agent_registered_in_registry(self) -> None:
        """PerformanceAgent is registered in the global AGENT_REGISTRY."""
        from src.agents.base import AGENT_REGISTRY

        assert "performance" in AGENT_REGISTRY
        assert AGENT_REGISTRY["performance"] is PerformanceAgent

    def test_agent_instantiable(self) -> None:
        """PerformanceAgent() creates a proper instance."""
        agent = PerformanceAgent()
        assert isinstance(agent, PerformanceAgent)
