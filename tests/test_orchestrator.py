"""Tests for src/core/orchestrator.py — rewritten with correct signatures."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, AgentOutput, AgentStatus
from src.core.orchestrator import (
    ExecutionMode,
    Orchestrator,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def orch(tmp_path: Path) -> Orchestrator:
    state_dir = tmp_path / ".omc" / "state"
    skills_dir = tmp_path / ".omc" / "skills"
    mock_router = MagicMock()
    mock_router.call_model = AsyncMock(return_value="ok")
    with patch("src.core.orchestrator.WorkflowLoader", return_value=None):
        o = Orchestrator(
            model_router=mock_router,
            state_dir=state_dir,
            skills_dir=skills_dir,
            project_path=tmp_path,
        )
    o._checkpoint_manager = MagicMock()
    o._health_checker = MagicMock()
    o._skill_manager = MagicMock()
    o._memory_manager = MagicMock()
    return o


@pytest.fixture
def wf_result() -> WorkflowResult:
    return WorkflowResult(
        workflow_id="wf-1",
        status=WorkflowStatus.RUNNING,
        steps_completed=[],
        steps_failed=[],
        outputs={},
        total_tokens=0,
        total_cost=0.0,
        execution_time=0.0,
        agent_names=[],
    )


# ---------------------------------------------------------------------------
# WorkflowStep
# ---------------------------------------------------------------------------

class TestWorkflowStep:
    def test_basic(self) -> None:
        s = WorkflowStep("a", "do a")
        assert s.agent_name == "a"
        assert s.description == "do a"
        assert s.dependencies == []
        assert s.retry_count == 0
        assert s.timeout == 300.0
        assert s.condition is None
        assert s.metadata == {}

    def test_with_condition(self) -> None:
        s = WorkflowStep("a", "do a", condition=lambda ctx: True)
        assert callable(s.condition)


# ---------------------------------------------------------------------------
# WorkflowResult
# ---------------------------------------------------------------------------

class TestWorkflowResult:
    def test_basic(self) -> None:
        r = WorkflowResult(
            workflow_id="wf-1",
            status=WorkflowStatus.RUNNING,
            steps_completed=[],
            steps_failed=[],
            outputs={},
            total_tokens=0,
            total_cost=0.0,
            execution_time=0.0,
            agent_names=[],
        )
        assert r.workflow_id == "wf-1"
        assert r.status == WorkflowStatus.RUNNING


# ---------------------------------------------------------------------------
# Orchestrator — init
# ---------------------------------------------------------------------------

class TestOrchestratorInit:
    def test_creates_dirs(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".omc" / "state"
        skills_dir = tmp_path / ".omc" / "skills"
        Orchestrator(
            model_router=MagicMock(),
            state_dir=state_dir,
            skills_dir=skills_dir,
            project_path=tmp_path,
        )
        assert state_dir.exists()
        # skills_dir is only stored, not created by __init__
        assert not skills_dir.exists()

    def test_lazy_properties(self, orch: Orchestrator) -> None:
        # pre-set in fixture, should not raise
        assert orch._health_checker is not None
        assert orch._checkpoint_manager is not None
        assert orch._skill_manager is not None


# ---------------------------------------------------------------------------
# get_agent
# ---------------------------------------------------------------------------

class TestGetAgent:
    def test_returns_none_for_unknown(self, orch: Orchestrator) -> None:
        with patch("src.agents.base.get_agent", return_value=None):
            with pytest.raises(ValueError, match="未知的 Agent"):
                orch.get_agent("nonexistent")

    def test_returns_cached(self, orch: Orchestrator) -> None:
        mock_agent = MagicMock()
        mock_agent.name = "cached"
        orch._agents["cached"] = mock_agent
        result = orch.get_agent("cached")
        assert result is mock_agent


# ---------------------------------------------------------------------------
# execute_single_agent
# ---------------------------------------------------------------------------

class TestExecuteSingleAgent:
    @pytest.mark.asyncio
    async def test_success(self, orch: Orchestrator) -> None:
        out = AgentOutput(
            agent_name="a", status=AgentStatus.COMPLETED,
            result="ok", artifacts={}, recommendations=[],
            next_agent=None, usage={}, execution_time=0.0,
            error=None, timestamp="",
        )
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value=out)

        with patch.object(orch, "get_agent", return_value=mock_agent):
            result = await orch.execute_single_agent("a", {"task": "hi"})

        assert result.status == AgentStatus.COMPLETED
        assert result.result == "ok"

    @pytest.mark.asyncio
    async def test_agent_raises(self, orch: Orchestrator) -> None:
        mock_agent = MagicMock()
        mock_agent.name = "bad"
        mock_agent.execute = AsyncMock(side_effect=RuntimeError("boom"))

        with patch.object(orch, "get_agent", return_value=mock_agent):
            with pytest.raises(RuntimeError, match="boom"):
                await orch.execute_single_agent("bad", {"task": "test"})


# ---------------------------------------------------------------------------
# _execute_sequential
# ---------------------------------------------------------------------------

class TestExecuteSequential:
    @pytest.mark.asyncio
    async def test_all_succeed(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        call_log: list[str] = []

        async def fake_exec(ctx: Any) -> AgentOutput:
            # ctx is AgentContext (dataclass), not dict — use task_description
            call_log.append(ctx.task_description or "?")
            return AgentOutput(
                agent_name="test-agent",
                status=AgentStatus.COMPLETED, result="ok",
                artifacts={}, recommendations=[],
                next_agent=None,
                usage={}, execution_time=0.0,
                error=None, timestamp="",
            )

        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=fake_exec)

        with patch.object(orch, "get_agent", return_value=mock_agent):
            steps = [WorkflowStep("a", "A"), WorkflowStep("b", "B")]
            await orch._execute_sequential(steps, {}, wf_result)

        assert len(wf_result.steps_completed) == 2
        # _execute_sequential does not set status; that is done by execute_workflow

    @pytest.mark.asyncio
    async def test_dep_not_met(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        with patch.object(orch, "get_agent", return_value=MagicMock()):
            steps = [WorkflowStep("b", "B", dependencies=["a"])]
            with pytest.raises(ValueError, match="依赖.*未完成"):
                await orch._execute_sequential(steps, {}, wf_result)


# ---------------------------------------------------------------------------
# _execute_parallel
# ---------------------------------------------------------------------------

class TestExecuteParallel:
    @pytest.mark.asyncio
    async def test_all_succeed(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value=AgentOutput(
            agent_name="x", status=AgentStatus.COMPLETED, result="ok",
            artifacts={}, recommendations=[], next_agent=None,
            usage={}, execution_time=0.0, error=None, timestamp="",
        ))

        with patch.object(orch, "get_agent", return_value=mock_agent):
            steps = [WorkflowStep("a", "A"), WorkflowStep("b", "B")]
            await orch._execute_parallel(steps, {}, wf_result)

        assert len(wf_result.steps_completed) == 2


# ---------------------------------------------------------------------------
# _execute_conditional
# ---------------------------------------------------------------------------

class TestExecuteConditional:
    @pytest.mark.asyncio
    async def test_condition_true(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value=AgentOutput(
            agent_name="x", status=AgentStatus.COMPLETED, result="ok",
            artifacts={}, recommendations=[], next_agent=None,
            usage={}, execution_time=0.0, error=None, timestamp="",
        ))
        step = WorkflowStep("a", "A", condition=lambda ctx: True)

        with patch.object(orch, "get_agent", return_value=mock_agent):
            await orch._execute_conditional([step], {}, wf_result)

        assert len(wf_result.steps_completed) == 1

    @pytest.mark.asyncio
    async def test_condition_false(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        step = WorkflowStep("a", "A", condition=lambda ctx: False)
        with patch.object(orch, "get_agent", return_value=MagicMock()):
            await orch._execute_conditional([step], {}, wf_result)
        assert len(wf_result.steps_completed) == 0


# ---------------------------------------------------------------------------
# execute_workflow
# ---------------------------------------------------------------------------

class TestExecuteWorkflow:
    @pytest.mark.asyncio
    async def test_sequential(self, orch: Orchestrator) -> None:
        orch._checkpoint_manager.create.return_value = "cp-1"
        with patch.object(orch, "_execute_sequential", new_callable=AsyncMock):
            result = await orch.execute_workflow(
                workflow_name="build",
                context={"task": "test"},
                mode=ExecutionMode.SEQUENTIAL,
            )
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_parallel(self, orch: Orchestrator) -> None:
        orch._checkpoint_manager.create.return_value = "cp-1"
        with patch.object(orch, "_execute_parallel", new_callable=AsyncMock):
            result = await orch.execute_workflow(
                workflow_name="build",
                context={"task": "test"},
                mode=ExecutionMode.PARALLEL,
            )
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_skip_checkpoint(self, orch: Orchestrator) -> None:
        orch._checkpoint_manager.create.return_value = "cp-1"
        with patch.object(orch, "_execute_sequential", new_callable=AsyncMock):
            result = await orch.execute_workflow(
                workflow_name="build",
                context={"task": "test"},
                mode=ExecutionMode.SEQUENTIAL,
                skip_checkpoint=True,
            )
        orch._checkpoint_manager.create.assert_not_called()
        assert result.status == WorkflowStatus.COMPLETED


# ---------------------------------------------------------------------------
# invoke_subagent
# ---------------------------------------------------------------------------

class TestInvokeSubagent:
    @pytest.mark.asyncio
    async def test_success(self, orch: Orchestrator) -> None:
        mock_agent = MagicMock()
        mock_agent.name = "sub"
        mock_agent.execute = AsyncMock(return_value=AgentOutput(
            agent_name="sub", status=AgentStatus.COMPLETED, result="ok",
            artifacts={}, recommendations=[], next_agent=None,
            usage={}, execution_time=0.0, error=None, timestamp="",
        ))

        with (
            patch.object(orch, "get_agent", return_value=mock_agent),
            patch("src.agents.base.AgentContext", return_value=MagicMock()),
        ):
            result = await orch.invoke_subagent("sub", "do it", {})

        assert result.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_timeout(self, orch: Orchestrator) -> None:
        mock_agent = MagicMock()
        mock_agent.name = "slow"
        mock_agent.execute = AsyncMock(side_effect=asyncio.TimeoutError)

        with (
            patch.object(orch, "get_agent", return_value=mock_agent),
            patch("src.agents.base.AgentContext", return_value=MagicMock()),
        ):
            result = await orch.invoke_subagent(
                "slow", "do it", {"subagent_timeout": 1}
            )

        assert result.status == AgentStatus.FAILED
        assert "超时" in (result.error or "")

    def test_max_depth(self, orch: Orchestrator) -> None:
        ctx: dict[str, Any] = {"_subagent_depth": 5}
        with pytest.raises(RecursionError, match="深度"):
            asyncio.run(orch.invoke_subagent("x", "deep", ctx, max_depth=3))


# ---------------------------------------------------------------------------
# _maybe_learn_from_workflow
# ---------------------------------------------------------------------------

class TestMaybeLearn:
    @pytest.mark.asyncio
    async def test_not_worthy(self, orch: Orchestrator) -> None:
        from src.agents.self_improving import SelfImprovingAgent

        orch._skill_manager.evaluate_skill_worthy.return_value = False
        result = WorkflowResult(
            workflow_id="wf-1", status=WorkflowStatus.COMPLETED,
            steps_completed=["a"], steps_failed=[],
            outputs={}, total_tokens=0, total_cost=0.0,
            execution_time=0.0, agent_names=["a"],
        )
        with patch.object(SelfImprovingAgent, "auto_create_skill") as mock_auto:
            await orch._maybe_learn_from_workflow("build", {}, result)
            mock_auto.assert_not_called()

    @pytest.mark.asyncio
    async def test_worthy(self, orch: Orchestrator) -> None:
        from src.agents.self_improving import SelfImprovingAgent

        orch._skill_manager.evaluate_skill_worthy.return_value = True
        outputs = {
            "a": AgentOutput(
                agent_name="a", status=AgentStatus.COMPLETED, result="ok",
                artifacts={"tool_calls": [1, 2, 3, 4, 5]},
                recommendations=[], next_agent=None,
                usage={}, execution_time=0.0, error=None, timestamp="",
            )
        }
        result = WorkflowResult(
            workflow_id="wf-1", status=WorkflowStatus.COMPLETED,
            steps_completed=["a", "b", "c"], steps_failed=[],
            outputs=outputs, total_tokens=0, total_cost=0.0,
            execution_time=0.0, agent_names=["a", "b", "c"],
        )
        with patch.object(SelfImprovingAgent, "auto_create_skill") as mock_auto:
            await orch._maybe_learn_from_workflow("build", {"task": "test"}, result)
            mock_auto.assert_called_once()


# ---------------------------------------------------------------------------
# _build_agent_context
# ---------------------------------------------------------------------------

class TestBuildAgentContext:
    def test_basic(self, orch: Orchestrator) -> None:
        orch.inject_skill_context = MagicMock(return_value="skill-x")
        orch.inject_memory_context = MagicMock(return_value="")
        ctx = orch._build_agent_context("explore", {
            "project_path": "/tmp",
            "task": "find bugs",
        })
        assert isinstance(ctx, AgentContext)
        assert ctx.project_path == Path("/tmp")
        assert ctx.skill_context == "skill-x"

    def test_memory_injection(self, orch: Orchestrator) -> None:
        orch.inject_skill_context = MagicMock(return_value="")
        orch.inject_memory_context = MagicMock(return_value="mem")
        ctx = orch._build_agent_context("a", {"task": "t"})
        assert "mem" in ctx.skill_context
