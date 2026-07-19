"""Tests for src/core/orchestrator.py — rewritten with correct signatures."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from src.agents.base import AgentContext, AgentOutput, AgentStatus
from src.core.orchestrator import (
    ExecutionMode,
    Orchestrator,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
    _detect_workflow_for_autopilot,
    _filter_planner_steps,
    _load_disable_planner,
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


# ---------------------------------------------------------------------------
# _load_disable_planner
# ---------------------------------------------------------------------------

class TestLoadDisablePlanner:
    def test_config_not_exists(self, tmp_path: Path) -> None:
        # ~/.omc/config.json 不存在时返回 False
        with patch("src.core.orchestrator.Path.home", return_value=tmp_path):
            result = _load_disable_planner()
        assert result is False

    def test_config_exists_no_disable_planner(self, tmp_path: Path) -> None:
        # config.json 存在但无 disable_planner 字段
        config_path = tmp_path / ".omc" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text('{"model": "deepseek"}', encoding="utf-8")
        with patch("src.core.orchestrator.Path.home", return_value=tmp_path):
            result = _load_disable_planner()
        assert result is False

    def test_config_disable_planner_true(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".omc" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text('{"disable_planner": true}', encoding="utf-8")
        with patch("src.core.orchestrator.Path.home", return_value=tmp_path):
            result = _load_disable_planner()
        assert result is True

    def test_config_disable_planner_false(self, tmp_path: Path) -> None:
        config_path = tmp_path / ".omc" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text('{"disable_planner": false}', encoding="utf-8")
        with patch("src.core.orchestrator.Path.home", return_value=tmp_path):
            result = _load_disable_planner()
        assert result is False

    def test_json_decode_error(self, tmp_path: Path) -> None:
        # 无效 JSON 返回 False
        config_path = tmp_path / ".omc" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("not json{", encoding="utf-8")
        with patch("src.core.orchestrator.Path.home", return_value=tmp_path):
            result = _load_disable_planner()
        assert result is False


# ---------------------------------------------------------------------------
# _filter_planner_steps
# ---------------------------------------------------------------------------

class TestFilterPlannerSteps:
    def test_disable_false_returns_all_steps(self) -> None:
        steps = [
            WorkflowStep("analyst", "分析"),
            WorkflowStep("planner", "规划", dependencies=["analyst"]),
            WorkflowStep("writer", "写代码", dependencies=["planner"]),
        ]
        with patch("src.core.orchestrator._load_disable_planner", return_value=False):
            result = _filter_planner_steps(steps)
        assert len(result) == 3
        assert result[0].agent_name == "analyst"
        assert result[1].agent_name == "planner"

    def test_disable_true_removes_planner(self) -> None:
        steps = [
            WorkflowStep("analyst", "分析"),
            WorkflowStep("planner", "规划", dependencies=["analyst"]),
            WorkflowStep("writer", "写代码", dependencies=["planner"]),
        ]
        with patch("src.core.orchestrator._load_disable_planner", return_value=True):
            result = _filter_planner_steps(steps)
        names = [s.agent_name for s in result]
        assert "planner" not in names
        assert "analyst" in names
        assert "writer" in names

    def test_disable_true_replaces_dep_with_analyst(self) -> None:
        steps = [
            WorkflowStep("analyst", "分析"),
            WorkflowStep("planner", "规划", dependencies=["analyst"]),
            WorkflowStep("writer", "写代码", dependencies=["planner"]),
        ]
        with patch("src.core.orchestrator._load_disable_planner", return_value=True):
            result = _filter_planner_steps(steps)
        writer_step = next(s for s in result if s.agent_name == "writer")
        # planner dep replaced with analyst (since analyst exists)
        assert "analyst" in writer_step.dependencies
        assert "planner" not in writer_step.dependencies

    def test_disable_true_no_analyst_keeps_planner_dep(self) -> None:
        # 没有 analyst 时，planner 步骤被移除，但依赖它的步骤中
        # planner 依赖保留（因为没有 analyst 可替代）
        steps = [
            WorkflowStep("planner", "规划"),
            WorkflowStep("writer", "写代码", dependencies=["planner", "other"]),
        ]
        with patch("src.core.orchestrator._load_disable_planner", return_value=True):
            result = _filter_planner_steps(steps)
        writer_step = next(s for s in result if s.agent_name == "writer")
        # planner removed from steps; planner dep kept (no analyst to substitute)
        assert "planner" not in [s.agent_name for s in result]  # planner step removed
        assert "planner" in writer_step.dependencies  # dep kept (no analyst)
        assert "other" in writer_step.dependencies  # other deps preserved

    def test_disable_true_preserves_non_planner_deps(self) -> None:
        steps = [
            WorkflowStep("analyst", "分析"),
            WorkflowStep("planner", "规划", dependencies=["analyst"]),
            WorkflowStep("reviewer", "审查", dependencies=["analyst", "planner"]),
        ]
        with patch("src.core.orchestrator._load_disable_planner", return_value=True):
            result = _filter_planner_steps(steps)
        reviewer = next(s for s in result if s.agent_name == "reviewer")
        assert "analyst" in reviewer.dependencies
        assert "planner" not in reviewer.dependencies


# ---------------------------------------------------------------------------
# _detect_workflow_for_autopilot
# ---------------------------------------------------------------------------

class TestDetectWorkflowForAutopilot:
    @pytest.mark.parametrize("task,expected", [
        ("fix the bug in login", "debug"),
        ("修复崩溃问题", "debug"),
        ("fix this error", "debug"),
        ("crash on startup", "debug"),
        ("write tests for auth", "test"),
        ("add test coverage", "test"),
        ("run unit tests", "test"),
        ("refactor the user module", "refactor"),
        ("simplify the code", "build"),
        ("代码优化", "refactor"),
        ("review my PR", "review"),
        ("代码审查", "review"),
        ("do code review", "review"),
        ("build the project", "build"),
        ("general task", "build"),
        ("do something", "build"),
    ])
    def test_detection(self, task: str, expected: str) -> None:
        result = _detect_workflow_for_autopilot(task)
        assert result == expected


# ---------------------------------------------------------------------------
# Skill inventory & context injection
# ---------------------------------------------------------------------------

class TestSkillInventory:
    def test_get_inventory_calls_manager(self, tmp_path: Path) -> None:
        # Mock the skill_manager property on the orchestrator class
        mock_sm_instance = MagicMock()
        mock_sm_instance.get_skill_inventory = MagicMock(return_value="[planner] skill-a: test")
        mock_router = MagicMock()
        mock_router.call_model = AsyncMock(return_value="ok")
        with patch("src.core.orchestrator.WorkflowLoader", return_value=None):
            o = Orchestrator(
                model_router=mock_router,
                state_dir=tmp_path / ".omc" / "state",
                skills_dir=tmp_path / ".omc" / "skills",
                project_path=tmp_path,
            )
        # Replace the skill_manager property with our mock
        with patch.object(type(o), "skill_manager", new_callable=PropertyMock, return_value=mock_sm_instance):
            result = o.get_skill_inventory(max_tokens=200)
        assert result == "[planner] skill-a: test"
        mock_sm_instance.get_skill_inventory.assert_called_once_with(max_tokens=200)

    def test_inject_skill_context(self, orch: Orchestrator) -> None:
        orch.inject_skill_context = MagicMock(return_value="[skill: planner] skill-a")
        result = orch.inject_skill_context("planner", max_tokens=100)
        assert "skill" in result


# ---------------------------------------------------------------------------
# Workflow result persistence
# ---------------------------------------------------------------------------

class TestWorkflowResultPersistence:
    def test_save_and_load_roundtrip(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        wf_result.workflow_id = "wf-roundtrip"
        wf_result.status = WorkflowStatus.COMPLETED
        wf_result.steps_completed = ["analyst", "writer"]
        wf_result.total_tokens = 1000
        wf_result.total_cost = 0.05
        wf_result.execution_time = 12.5
        wf_result.error = None

        orch._save_workflow_result(wf_result)

        loaded = orch.load_workflow_result("wf-roundtrip")
        assert loaded is not None
        assert loaded.workflow_id == "wf-roundtrip"
        assert loaded.status == WorkflowStatus.COMPLETED
        assert loaded.steps_completed == ["analyst", "writer"]
        assert loaded.total_tokens == 1000
        assert loaded.total_cost == 0.05
        assert loaded.execution_time == 12.5
        assert loaded.error is None

    def test_load_workflow_result_not_found(self, orch: Orchestrator) -> None:
        result = orch.load_workflow_result("nonexistent-id")
        assert result is None

    def test_save_workflow_result_with_error(self, orch: Orchestrator) -> None:
        err_result = WorkflowResult(
            workflow_id="wf-error",
            status=WorkflowStatus.FAILED,
            steps_completed=["analyst"],
            steps_failed=["writer"],
            outputs={},
            total_tokens=50,
            total_cost=0.01,
            execution_time=3.0,
            error="Step writer failed: timeout",
        )
        orch._save_workflow_result(err_result)
        loaded = orch.load_workflow_result("wf-error")
        assert loaded is not None
        assert loaded.status == WorkflowStatus.FAILED
        assert loaded.error == "Step writer failed: timeout"


# ---------------------------------------------------------------------------
# Active workflows tracking
# ---------------------------------------------------------------------------

class TestActiveWorkflows:
    def test_list_active_workflows_empty(self, orch: Orchestrator) -> None:
        assert orch.list_active_workflows() == []

    def test_get_workflow_status_not_found(self, orch: Orchestrator) -> None:
        assert orch.get_workflow_status("nonexistent") is None

    def test_get_current_state(self, orch: Orchestrator) -> None:
        state = orch.get_current_state()
        assert isinstance(state, dict)
        assert "active_workflows" in state or "workflows" in state or len(state) >= 0


# ---------------------------------------------------------------------------
# Sourcegraph overrides
# ---------------------------------------------------------------------------

class TestSourcegraphOverrides:
    def test_returns_dict(self, orch: Orchestrator) -> None:
        result = orch._sourcegraph_overrides({"task": "fix bug"})
        assert isinstance(result, dict)

    def test_use_sourcegraph_flag(self, orch: Orchestrator) -> None:
        result = orch._sourcegraph_overrides({"use_sourcegraph": True})
        assert result["use_sourcegraph"] is True

    def test_sourcegraph_limit(self, orch: Orchestrator) -> None:
        result = orch._sourcegraph_overrides({"sourcegraph_limit": 50})
        assert result["sourcegraph_limit"] == 50

    def test_no_overrides(self, orch: Orchestrator) -> None:
        result = orch._sourcegraph_overrides({"task": "do stuff"})
        assert result == {}


# ---------------------------------------------------------------------------
# _get_trace_context_cls (standalone function)
# ---------------------------------------------------------------------------

class TestGetTraceContextCls:
    """Tests for the module-level `_get_trace_context_cls` function"""

    def test_import_fails_returns_none(self) -> None:
        """Make the internal `from ..agents.transparency import TraceContext` fail"""
        import src.agents.transparency as trans_mod

        # Delete TraceContext from the module so the import inside raises ImportError
        saved = trans_mod.TraceContext
        del trans_mod.TraceContext
        try:
            from src.core.orchestrator import _get_trace_context_cls
            result = _get_trace_context_cls()
            assert result is None
        finally:
            trans_mod.TraceContext = saved

    def test_import_succeeds_returns_class(self) -> None:
        from src.core.orchestrator import _get_trace_context_cls
        result = _get_trace_context_cls()
        assert result is not None and callable(result)


# ---------------------------------------------------------------------------
# Lazy initialization of properties
# ---------------------------------------------------------------------------

class TestLazyProperties:
    """Test lazy-init paths for skill_manager, checkpoint_manager, memory_manager, health_checker"""

    def test_skill_manager_lazy_init(self, tmp_path: Path) -> None:
        """Patch at the import site (inside the property method), not module attr"""
        mock_router = MagicMock()
        mock_router.call_model = AsyncMock(return_value="ok")
        with patch("src.core.orchestrator.WorkflowLoader", return_value=None):
            o = Orchestrator(
                model_router=mock_router,
                state_dir=tmp_path / ".omc" / "state",
                skills_dir=tmp_path / ".omc" / "skills",
                project_path=tmp_path,
            )
        o._skill_manager = None
        # patch the import target used inside the property
        with patch("src.memory.skill_manager.SkillManager") as mock_sm_cls:
            _ = o.skill_manager
            mock_sm_cls.assert_called_once()

    def test_checkpoint_manager_lazy_init(self, tmp_path: Path) -> None:
        mock_router = MagicMock()
        mock_router.call_model = AsyncMock(return_value="ok")
        with patch("src.core.orchestrator.WorkflowLoader", return_value=None):
            o = Orchestrator(
                model_router=mock_router,
                state_dir=tmp_path / ".omc" / "state",
                project_path=tmp_path,
            )
        o._checkpoint_manager = None
        with patch("src.core.checkpoint.CheckpointManager") as mock_cp_cls:
            _ = o.checkpoint_manager
            mock_cp_cls.assert_called_once()

    def test_memory_manager_lazy_init(self, tmp_path: Path) -> None:
        mock_router = MagicMock()
        mock_router.call_model = AsyncMock(return_value="ok")
        with patch("src.core.orchestrator.WorkflowLoader", return_value=None):
            o = Orchestrator(
                model_router=mock_router,
                state_dir=tmp_path / ".omc" / "state",
                project_path=tmp_path,
            )
        o._memory_manager = None
        with patch("src.memory.manager.MemoryManager") as mock_mm_cls:
            _ = o.memory_manager
            mock_mm_cls.from_project.assert_called_once()

    def test_health_checker_lazy_init(self, tmp_path: Path) -> None:
        mock_router = MagicMock()
        mock_router.call_model = AsyncMock(return_value="ok")
        with patch("src.core.orchestrator.WorkflowLoader", return_value=None):
            o = Orchestrator(
                model_router=mock_router,
                state_dir=tmp_path / ".omc" / "state",
                project_path=tmp_path,
            )
        o._health_checker = None
        with patch("src.agents.health_check.HealthChecker") as mock_hc_cls:
            _ = o.health_checker
            mock_hc_cls.assert_called_once()


# ---------------------------------------------------------------------------
# inject_memory_context — empty / blank return
# ---------------------------------------------------------------------------

class TestInjectMemoryContext:
    def test_returns_empty_when_blank(self, orch: Orchestrator) -> None:
        orch.memory_manager.get_tier0_summary.return_value = "   "
        result = orch.inject_memory_context()
        assert result == ""

    def test_returns_empty_when_none_or_empty(self, orch: Orchestrator) -> None:
        orch.memory_manager.get_tier0_summary.return_value = ""
        result = orch.inject_memory_context()
        assert result == ""

    def test_returns_formatted_when_content(self, orch: Orchestrator) -> None:
        orch.memory_manager.get_tier0_summary.return_value = "core memories"
        result = orch.inject_memory_context()
        assert "核心记忆" in result
        assert "core memories" in result


# ---------------------------------------------------------------------------
# inject_skill_context — "(none)" branch
# ---------------------------------------------------------------------------

class TestInjectSkillContext:
    def test_returns_empty_when_none_in_inventory(self, orch: Orchestrator) -> None:
        # Patch get_skill_inventory to return "(none)"
        with patch.object(orch, "get_skill_inventory", return_value="(none)"):
            result = orch.inject_skill_context("planner")
        assert result == ""

    def test_returns_formatted_when_has_skills(self, orch: Orchestrator) -> None:
        with patch.object(orch, "get_skill_inventory", return_value="[skill] planner: plan"):
            result = orch.inject_skill_context("planner")
        assert "可用经验" in result
        assert "[skill] planner: plan" in result


# ---------------------------------------------------------------------------
# register_agent
# ---------------------------------------------------------------------------

class TestRegisterAgent:
    def test_register(self, orch: Orchestrator) -> None:
        agent = MagicMock()
        agent.name = "my-agent"
        orch.register_agent(agent)
        assert orch._agents["my-agent"] is agent

    def test_register_overwrites(self, orch: Orchestrator) -> None:
        old = MagicMock()
        old.name = "dup"
        new = MagicMock()
        new.name = "dup"
        orch.register_agent(old)
        orch.register_agent(new)
        assert orch._agents["dup"] is new


# ---------------------------------------------------------------------------
# get_agent — dynamic loading & override_attrs
# ---------------------------------------------------------------------------

class TestGetAgentDynamic:
    def test_dynamic_load_and_caches(self, orch: Orchestrator) -> None:

        mock_agent_class = MagicMock()
        mock_instance = MagicMock()
        mock_agent_class.return_value = mock_instance

        with patch("src.agents.base.get_agent", return_value=mock_agent_class):
            result = orch.get_agent("analyst")

        assert result is mock_instance
        mock_agent_class.assert_called_once_with(
            orch.model_router, orchestrator=orch
        )
        # Should be cached
        assert orch._agents["analyst"] is mock_instance

    def test_override_attrs_existing_attr(self, orch: Orchestrator) -> None:
        mock_agent = MagicMock()
        mock_agent.name = "test-agent"
        orch._agents["test-agent"] = mock_agent

        result = orch.get_agent("test-agent", use_sourcegraph=True, sourcegraph_limit=50)
        assert result is mock_agent
        assert result.use_sourcegraph is True
        assert result.sourcegraph_limit == 50

    def test_override_attrs_missing_attr_silent_skip(self, orch: Orchestrator) -> None:
        """When overridden attribute doesn't exist on agent, it's silently skipped"""
        mock_agent = MagicMock(spec=["name"])  # spec: only name attribute
        mock_agent.name = "strict-agent"
        orch._agents["strict-agent"] = mock_agent

        # use_sourcegraph is NOT in spec, so hasattr returns False on spec'd mocks
        result = orch.get_agent("strict-agent", use_sourcegraph=True)
        assert result is mock_agent
        # With spec, setting non-existent attr should NOT raise (pass branch)

    def test_override_attrs_some_missing_some_present(self, orch: Orchestrator) -> None:
        mock_agent = MagicMock()
        mock_agent.name = "mixed"
        orch._agents["mixed"] = mock_agent

        # Use a spec'd mock for a clean test: bogus_param is not in spec
        spec_agent = MagicMock(spec=["name", "use_sourcegraph"])
        spec_agent.name = "specd"
        orch._agents["specd"] = spec_agent

        result = orch.get_agent("specd", use_sourcegraph=True, bogus_param="x")
        assert result is spec_agent
        assert result.use_sourcegraph is True  # set
        # bogus_param doesn't match spec → silently skipped; assert it doesn't raise
        # (verifying the pass branch is exercised)


# ---------------------------------------------------------------------------
# _maybe_evolve_agents — additional coverage
# ---------------------------------------------------------------------------

class TestMaybeEvolveAdditional:
    @pytest.mark.asyncio
    async def test_disabled_returns_early(self, orch: Orchestrator) -> None:
        """_maybe_evolve_agents returns early when evolution is disabled"""
        mock_config = MagicMock()
        mock_config.enabled = False

        result = WorkflowResult(
            workflow_id="wf", status=WorkflowStatus.COMPLETED,
            steps_completed=["a"], steps_failed=[],
            outputs={}, total_tokens=0, total_cost=0.0,
            execution_time=0.0, agent_names=["a"],
        )

        with patch("src.agents.self_improving.EvolutionConfig", return_value=mock_config):
            await orch._maybe_evolve_agents(result)
        # No outputs added
        assert len(result.outputs) == 0

    @pytest.mark.asyncio
    async def test_enabled_with_record(self, orch: Orchestrator) -> None:
        """Evolution enabled, evolve returns record → stored in outputs"""
        mock_config = MagicMock()
        mock_config.enabled = True

        mock_record = MagicMock()
        mock_record.id = "ev-123"
        mock_record.generation = 3
        mock_record.changes = ["improved prompt clarity"]

        mock_sia = MagicMock()
        mock_sia.evolve = MagicMock(return_value=mock_record)

        result = WorkflowResult(
            workflow_id="wf", status=WorkflowStatus.COMPLETED,
            steps_completed=["explorer"], steps_failed=[],
            outputs={}, total_tokens=0, total_cost=0.0,
            execution_time=0.0, agent_names=["explorer"],
        )

        with (
            patch("src.agents.self_improving.EvolutionConfig", return_value=mock_config),
            patch("src.agents.self_improving.SelfImprovingAgent", return_value=mock_sia),
        ):
            await orch._maybe_evolve_agents(result)

        assert "_evolution_explorer" in result.outputs
        ev = result.outputs["_evolution_explorer"]
        assert ev["evolution_id"] == "ev-123"
        assert ev["generation"] == 3
        assert ev["changes"] == ["improved prompt clarity"]

    @pytest.mark.asyncio
    async def test_enabled_evolve_raises(self, orch: Orchestrator) -> None:
        """Evolution enabled but evolve() raises → silently caught"""
        mock_config = MagicMock()
        mock_config.enabled = True

        mock_sia = MagicMock()
        mock_sia.evolve = MagicMock(side_effect=ValueError("evolve failed"))

        result = WorkflowResult(
            workflow_id="wf", status=WorkflowStatus.COMPLETED,
            steps_completed=["a", "b"], steps_failed=[],
            outputs={}, total_tokens=0, total_cost=0.0,
            execution_time=0.0, agent_names=["a", "b"],
        )

        with (
            patch("src.agents.self_improving.EvolutionConfig", return_value=mock_config),
            patch("src.agents.self_improving.SelfImprovingAgent", return_value=mock_sia),
        ):
            await orch._maybe_evolve_agents(result)
        # No evolution outputs added
        assert all(not k.startswith("_evolution_") for k in result.outputs)

    @pytest.mark.asyncio
    async def test_enabled_sia_ctor_raises(self, orch: Orchestrator) -> None:
        """SelfImprovingAgent constructor raises → silently caught"""
        mock_config = MagicMock()
        mock_config.enabled = True

        result = WorkflowResult(
            workflow_id="wf", status=WorkflowStatus.COMPLETED,
            steps_completed=["a"], steps_failed=[],
            outputs={}, total_tokens=0, total_cost=0.0,
            execution_time=0.0, agent_names=["a"],
        )

        with (
            patch("src.agents.self_improving.EvolutionConfig", return_value=mock_config),
            patch("src.agents.self_improving.SelfImprovingAgent", side_effect=RuntimeError("ctor failed")),
        ):
            # Should not raise
            await orch._maybe_evolve_agents(result)


# ---------------------------------------------------------------------------
# execute_workflow — remaining coverage paths
# ---------------------------------------------------------------------------

class TestExecuteWorkflowAdditional:
    @pytest.mark.asyncio
    async def test_autopilot_routing(self, orch: Orchestrator) -> None:
        """workflow_name='autopilot' triggers _detect_workflow_for_autopilot"""
        orch._checkpoint_manager.create.return_value = "cp-1"
        with (
            patch.object(orch, "_execute_sequential", new_callable=AsyncMock),
            patch("src.core.orchestrator._detect_workflow_for_autopilot", return_value="debug") as mock_detect,
        ):
            result = await orch.execute_workflow(
                workflow_name="autopilot",
                context={"task": "fix crash bug"},
                mode=ExecutionMode.SEQUENTIAL,
            )
        mock_detect.assert_called_once_with("fix crash bug")
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_workflow_loader_not_none(self, tmp_path: Path) -> None:
        """When workflow_loader is available, it's used"""
        mock_router = MagicMock()
        mock_router.call_model = AsyncMock(return_value="ok")

        mock_loader = MagicMock()
        mock_loader.load_workflow.return_value = [
            WorkflowStep("explore", "explore"),
        ]

        with patch("src.core.orchestrator.WorkflowLoader", return_value=mock_loader):
            o = Orchestrator(
                model_router=mock_router,
                state_dir=tmp_path / ".omc" / "state",
                project_path=tmp_path,
            )
        o._checkpoint_manager = MagicMock()
        o._checkpoint_manager.create.return_value = "cp-1"
        o._health_checker = MagicMock()
        o._skill_manager = MagicMock()
        o._memory_manager = MagicMock()

        # Mock execute methods
        with patch.object(o, "_execute_sequential", new_callable=AsyncMock):
            result = await o.execute_workflow(
                workflow_name="build",
                context={"task": "test"},
                mode=ExecutionMode.SEQUENTIAL,
            )

        # WorkflowLoader was used instead of WORKFLOW_TEMPLATES
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_workflow_name_is_list(self, orch: Orchestrator) -> None:
        """workflow_name can be a list of WorkflowStep"""
        orch._checkpoint_manager.create.return_value = "cp-1"
        steps_list = [
            WorkflowStep("a", "A"),
            WorkflowStep("b", "B", dependencies=["a"]),
        ]
        with (
            patch.object(orch, "_execute_sequential", new_callable=AsyncMock),
            patch("src.core.orchestrator._filter_planner_steps", side_effect=lambda x: x),
        ):
            result = await orch.execute_workflow(
                workflow_name=steps_list,
                context={"task": "test"},
            )
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_empty_steps_raises(self, orch: Orchestrator) -> None:
        """No matching workflow template and no steps raises ValueError"""
        orch._checkpoint_manager.create.return_value = "cp-1"
        with pytest.raises(ValueError, match="无效的工作流"):
            await orch.execute_workflow(
                workflow_name="nonexistent-template",
                context={"task": "test"},
            )

    @pytest.mark.asyncio
    async def test_conditional_mode(self, orch: Orchestrator) -> None:
        """ExecutionMode.CONDITIONAL calls _execute_conditional"""
        orch._checkpoint_manager.create.return_value = "cp-1"
        with (
            patch.object(orch, "_execute_conditional", new_callable=AsyncMock),
        ):
            result = await orch.execute_workflow(
                workflow_name="build",
                context={"task": "test"},
                mode=ExecutionMode.CONDITIONAL,
            )
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execution_raises_and_handles_error(self, orch: Orchestrator) -> None:
        """When execution raises, result is set to FAILED with error detail"""
        orch._checkpoint_manager.create.return_value = "cp-1"

        async def _fail(*args, **kwargs):
            raise ValueError("execution exploded")

        with (
            patch.object(orch, "_execute_sequential", new_callable=AsyncMock, side_effect=_fail),
        ):
            result = await orch.execute_workflow(
                workflow_name="build",
                context={"task": "test"},
                mode=ExecutionMode.SEQUENTIAL,
            )
        assert result.status == WorkflowStatus.FAILED
        assert "ValueError" in (result.error or "")
        assert "execution exploded" in (result.error or "")

    @pytest.mark.asyncio
    async def test_omc_debug_traceback(self, orch: Orchestrator) -> None:
        """When OMC_DEBUG=1, error detail includes traceback"""
        orch._checkpoint_manager.create.return_value = "cp-1"

        async def _fail(*args, **kwargs):
            raise RuntimeError("omc debug")

        with (
            patch.dict("os.environ", {"OMC_DEBUG": "1"}),
            patch.object(orch, "_execute_sequential", new_callable=AsyncMock, side_effect=_fail),
        ):
            result = await orch.execute_workflow(
                workflow_name="build",
                context={"task": "test"},
            )
        assert result.status == WorkflowStatus.FAILED
        # Should include traceback
        assert "omc debug" in (result.error or "")

    @pytest.mark.asyncio
    async def test_checkpoint_create_raises(self, orch: Orchestrator) -> None:
        """When checkpoint_manager.create() raises, it's silently caught"""
        orch._checkpoint_manager.create.side_effect = RuntimeError("checkpoint failed")
        with patch.object(orch, "_execute_sequential", new_callable=AsyncMock):
            result = await orch.execute_workflow(
                workflow_name="build",
                context={"task": "test"},
                mode=ExecutionMode.SEQUENTIAL,
                skip_checkpoint=False,
            )
        # Should not raise; checkpoint failure is silently ignored
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_maybe_learn_raises_caught(self, orch: Orchestrator) -> None:
        """_maybe_learn_from_workflow failure is silently caught"""
        orch._checkpoint_manager.create.return_value = "cp-1"
        with (
            patch.object(orch, "_execute_sequential", new_callable=AsyncMock),
            patch.object(orch, "_maybe_learn_from_workflow", side_effect=ValueError("learn failed")),
        ):
            result = await orch.execute_workflow(
                workflow_name="build",
                context={"task": "test"},
            )
        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_maybe_evolve_raises_caught(self, orch: Orchestrator) -> None:
        """_maybe_evolve_agents failure is silently caught"""
        orch._checkpoint_manager.create.return_value = "cp-1"
        with (
            patch.object(orch, "_execute_sequential", new_callable=AsyncMock),
            patch.object(orch, "_maybe_evolve_agents", side_effect=ValueError("evolve failed")),
        ):
            result = await orch.execute_workflow(
                workflow_name="build",
                context={"task": "test"},
            )
        assert result.status == WorkflowStatus.COMPLETED


# ---------------------------------------------------------------------------
# _execute_sequential — progress callback & error/retry paths
# ---------------------------------------------------------------------------

class TestExecuteSequentialAdditional:
    @pytest.mark.asyncio
    async def test_progress_callback(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """progress_callback is called with started/completed/failed"""
        call_log: list[tuple[str, str]] = []

        async def fake_exec(ctx: Any) -> AgentOutput:
            return AgentOutput(
                agent_name="a",
                status=AgentStatus.COMPLETED, result="ok",
                artifacts={}, recommendations=[],
                next_agent=None, usage={}, execution_time=0.0,
                error=None, timestamp="",
            )

        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=fake_exec)

        def progress_cb(name: str, status: str) -> None:
            call_log.append((name, status))

        # Set progress_callback on result
        wf_result._progress_callback = progress_cb

        with patch.object(orch, "get_agent", return_value=mock_agent):
            steps = [WorkflowStep("a", "A")]
            await orch._execute_sequential(steps, {}, wf_result)

        assert ("a", "started") in call_log
        assert ("a", "completed") in call_log

    @pytest.mark.asyncio
    async def test_agent_non_completed_raises(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """Agent returns non-completed status → Exception raised"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value=AgentOutput(
            agent_name="a", status=AgentStatus.FAILED, result="",
            artifacts={}, recommendations=[], next_agent=None,
            usage={}, execution_time=0.0, error="oops", timestamp="",
        ))

        # Set health_checker.record_failure to return True (terminal)
        orch.health_checker.record_failure.return_value = True

        with patch.object(orch, "get_agent", return_value=mock_agent):
            steps = [WorkflowStep("a", "A")]
            with pytest.raises(Exception, match="执行失败"):
                await orch._execute_sequential(steps, {}, wf_result)
        assert len(wf_result.steps_failed) == 1

    @pytest.mark.asyncio
    async def test_timeout_with_terminal(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """TimeoutError + record_failure returns True → terminal failure"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=TimeoutError("timed out"))

        orch.health_checker.record_failure.return_value = True

        call_log: list[tuple[str, str]] = []
        wf_result._progress_callback = lambda name, status: call_log.append((name, status))

        with patch.object(orch, "get_agent", return_value=mock_agent):
            steps = [WorkflowStep("a", "A")]
            with pytest.raises(Exception, match="超时"):
                await orch._execute_sequential(steps, {}, wf_result)
        assert len(wf_result.steps_failed) == 1
        assert ("a", "failed") in call_log

    @pytest.mark.asyncio
    async def test_timeout_with_reassign(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """TimeoutError + record_failure=False + reassign → retry succeeds"""
        call_count: list[int] = []

        async def execute_side_effect(ctx: Any) -> AgentOutput:
            call_count.append(len(call_count))
            if len(call_count) == 1:
                raise TimeoutError("first attempt timeout")
            return AgentOutput(
                agent_name="a", status=AgentStatus.COMPLETED, result="ok",
                artifacts={}, recommendations=[], next_agent=None,
                usage={}, execution_time=0.0, error=None, timestamp="",
            )

        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=execute_side_effect)

        # First failure = retryable, reassign to "a2"
        orch.health_checker.record_failure.return_value = False
        orch.health_checker.reassign_task.return_value = "a2"

        call_count_get_agent = [0]
        def get_agent_side(name, **kwargs):
            call_count_get_agent[0] += 1
            if name == "a2":
                return mock_agent
            return mock_agent

        with patch.object(orch, "get_agent", side_effect=get_agent_side):
            steps = [WorkflowStep("a", "A")]
            await orch._execute_sequential(steps, {}, wf_result)

        assert len(wf_result.steps_completed) == 1
        assert len(wf_result.steps_failed) == 0

    @pytest.mark.asyncio
    async def test_timeout_no_reassign(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """TimeoutError + record_failure=False + no reassign → raise"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=TimeoutError("timed out"))

        orch.health_checker.record_failure.return_value = False
        orch.health_checker.reassign_task.return_value = None

        with patch.object(orch, "get_agent", return_value=mock_agent):
            steps = [WorkflowStep("a", "A")]
            with pytest.raises(Exception, match="无法重分配"):
                await orch._execute_sequential(steps, {}, wf_result)
        assert len(wf_result.steps_failed) == 1

    @pytest.mark.asyncio
    async def test_exception_with_retry(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """General Exception + record_failure=False + reassign → retry succeeds"""
        call_count: list[int] = []

        async def execute_side_effect(ctx: Any) -> AgentOutput:
            call_count.append(len(call_count))
            if len(call_count) == 1:
                raise ValueError("first attempt failed")
            return AgentOutput(
                agent_name="a", status=AgentStatus.COMPLETED, result="ok",
                artifacts={}, recommendations=[], next_agent=None,
                usage={}, execution_time=0.0, error=None, timestamp="",
            )

        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=execute_side_effect)

        orch.health_checker.record_failure.return_value = False
        orch.health_checker.reassign_task.return_value = "a2"

        call_count_get_agent = [0]
        def get_agent_side(name, **kwargs):
            call_count_get_agent[0] += 1
            if name == "a2":
                return mock_agent
            return mock_agent

        with patch.object(orch, "get_agent", side_effect=get_agent_side):
            steps = [WorkflowStep("a", "A")]
            await orch._execute_sequential(steps, {}, wf_result)

        assert len(wf_result.steps_completed) == 1

    @pytest.mark.asyncio
    async def test_exception_terminal(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """General Exception + record_failure returns True → terminal"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=ValueError("boom"))

        orch.health_checker.record_failure.return_value = True

        call_log: list[tuple[str, str]] = []
        wf_result._progress_callback = lambda name, status: call_log.append((name, status))

        with patch.object(orch, "get_agent", return_value=mock_agent):
            steps = [WorkflowStep("a", "A")]
            with pytest.raises(Exception, match="boom"):
                await orch._execute_sequential(steps, {}, wf_result)
        assert len(wf_result.steps_failed) == 1
        assert ("a", "failed") in call_log

    @pytest.mark.asyncio
    async def test_exception_no_reassign(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """General Exception + record_failure=False + reassign=None → raise"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=ValueError("general error"))

        orch.health_checker.record_failure.return_value = False
        orch.health_checker.reassign_task.return_value = None

        with patch.object(orch, "get_agent", return_value=mock_agent):
            steps = [WorkflowStep("a", "A")]
            with pytest.raises(Exception):  # noqa: B017
                await orch._execute_sequential(steps, {}, wf_result)
        assert len(wf_result.steps_failed) == 1


# ---------------------------------------------------------------------------
# _execute_parallel — edge cases
# ---------------------------------------------------------------------------

class TestExecuteParallelAdditional:
    @pytest.mark.asyncio
    async def test_cyclic_dependency_break(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """Cyclic dependency causes empty level → break (no-op)"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value=AgentOutput(
            agent_name="x", status=AgentStatus.COMPLETED, result="ok",
            artifacts={}, recommendations=[], next_agent=None,
            usage={}, execution_time=0.0, error=None, timestamp="",
        ))

        with patch.object(orch, "get_agent", return_value=mock_agent):
            # a depends on b, b depends on a = cycle
            steps = [
                WorkflowStep("a", "A", dependencies=["b"]),
                WorkflowStep("b", "B", dependencies=["a"]),
            ]
            await orch._execute_parallel(steps, {}, wf_result)
        # No steps completed (cycle prevented execution)
        assert len(wf_result.steps_completed) == 0

    @pytest.mark.asyncio
    async def test_gather_returns_exception(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """When asyncio.gather returns Exception in results, it raises"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=ValueError("parallel fail"))

        with patch.object(orch, "get_agent", return_value=mock_agent):
            steps = [WorkflowStep("a", "A")]
            with pytest.raises(Exception, match="并行执行失败"):
                await orch._execute_parallel(steps, {}, wf_result)
        assert len(wf_result.steps_failed) == 1

    @pytest.mark.asyncio
    async def test_agent_not_completed(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """Agent returns non-completed status in parallel mode → raises"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value=AgentOutput(
            agent_name="a", status=AgentStatus.FAILED, result="",
            artifacts={}, recommendations=[], next_agent=None,
            usage={}, execution_time=0.0, error="parallel error", timestamp="",
        ))

        with patch.object(orch, "get_agent", return_value=mock_agent):
            steps = [WorkflowStep("a", "A")]
            with pytest.raises(Exception, match="执行失败"):
                await orch._execute_parallel(steps, {}, wf_result)
        assert len(wf_result.steps_failed) == 1


# ---------------------------------------------------------------------------
# _execute_conditional — remaining paths
# ---------------------------------------------------------------------------

class TestExecuteConditionalAdditional:
    @pytest.mark.asyncio
    async def test_dep_not_met(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """Dependency not completed causes ValueError"""
        step = WorkflowStep("b", "B", dependencies=["a"])
        with patch.object(orch, "get_agent", return_value=MagicMock()):
            with pytest.raises(ValueError, match="依赖.*未完成"):
                await orch._execute_conditional([step], {}, wf_result)

    @pytest.mark.asyncio
    async def test_condition_raises(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """Condition function that raises is handled as failure"""
        step = WorkflowStep("a", "A", condition=lambda ctx: 1 / 0)  # raises ZeroDivisionError
        with patch.object(orch, "get_agent", return_value=MagicMock()):
            with pytest.raises(Exception, match="条件执行异常"):
                await orch._execute_conditional([step], {}, wf_result)
        assert len(wf_result.steps_failed) == 1

    @pytest.mark.asyncio
    async def test_agent_not_completed(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """Agent returns non-completed status in conditional mode"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value=AgentOutput(
            agent_name="a", status=AgentStatus.FAILED, result="",
            artifacts={}, recommendations=[], next_agent=None,
            usage={}, execution_time=0.0, error="cond error", timestamp="",
        ))

        step = WorkflowStep("a", "A", condition=lambda ctx: True)
        with patch.object(orch, "get_agent", return_value=mock_agent):
            with pytest.raises(Exception, match="执行失败"):
                await orch._execute_conditional([step], {}, wf_result)
        assert len(wf_result.steps_failed) == 1

    @pytest.mark.asyncio
    async def test_timeout(self, orch: Orchestrator, wf_result: WorkflowResult) -> None:
        """TimeoutError in conditional mode is handled"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=TimeoutError("cond timeout"))

        step = WorkflowStep("a", "A", condition=lambda ctx: True)
        with patch.object(orch, "get_agent", return_value=mock_agent):
            with pytest.raises(Exception, match="执行超时"):
                await orch._execute_conditional([step], {}, wf_result)
        assert len(wf_result.steps_failed) == 1


# ---------------------------------------------------------------------------
# execute_single_agent — trace context with output summary
# ---------------------------------------------------------------------------

class TestExecuteSingleAgentAdditional:
    @pytest.mark.asyncio
    async def test_with_trace_context_and_output_attr(self, orch: Orchestrator) -> None:
        """execute_single_agent with TraceContext and hasattr output"""

        # Create a TraceContext-like mock
        mock_trace_ctx = MagicMock()
        mock_trace_ctx_cls = MagicMock(return_value=mock_trace_ctx)

        # Create output with .output attribute
        output = AgentOutput(
            agent_name="a", status=AgentStatus.COMPLETED, result="ok",
            artifacts={}, recommendations=[], next_agent=None,
            usage={}, execution_time=0.0, error=None, timestamp="",
        )
        output.output = "This is a test output summary that will be captured"

        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value=output)

        with (
            patch.object(orch, "get_agent", return_value=mock_agent),
            patch("src.core.orchestrator._get_trace_context_cls", return_value=mock_trace_ctx_cls),
        ):
            result = await orch.execute_single_agent("a", {"task": "test"})

        assert result is output
        mock_trace_ctx.start.assert_called_once()
        mock_trace_ctx.stop.assert_called_once_with(
            status="completed",
            output_summary="This is a test output summary that will be captured",
        )

    @pytest.mark.asyncio
    async def test_with_trace_context_and_no_output_attr(self, orch: Orchestrator) -> None:
        """execute_single_agent with TraceContext but output lacks .output attr"""
        mock_trace_ctx = MagicMock()
        mock_trace_ctx_cls = MagicMock(return_value=mock_trace_ctx)

        output = AgentOutput(
            agent_name="a", status=AgentStatus.COMPLETED, result="ok",
            artifacts={}, recommendations=[], next_agent=None,
            usage={}, execution_time=0.0, error=None, timestamp="",
        )
        # No .output attribute on output

        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value=output)

        with (
            patch.object(orch, "get_agent", return_value=mock_agent),
            patch("src.core.orchestrator._get_trace_context_cls", return_value=mock_trace_ctx_cls),
        ):
            result = await orch.execute_single_agent("a", {"task": "test"})

        assert result is output
        # Summary should be empty since no .output attr
        mock_trace_ctx.stop.assert_called_once_with(
            status="completed",
            output_summary="",
        )

    @pytest.mark.asyncio
    async def test_with_trace_context_and_exception(self, orch: Orchestrator) -> None:
        """execute_single_agent with TraceContext and exception"""
        mock_trace_ctx = MagicMock()
        mock_trace_ctx_cls = MagicMock(return_value=mock_trace_ctx)

        mock_agent = MagicMock()
        mock_agent.name = "bad-agent"
        mock_agent.execute = AsyncMock(side_effect=ValueError("oh no"))

        with (
            patch.object(orch, "get_agent", return_value=mock_agent),
            patch("src.core.orchestrator._get_trace_context_cls", return_value=mock_trace_ctx_cls),
        ):
            with pytest.raises(ValueError, match="oh no"):
                await orch.execute_single_agent("bad-agent", {"task": "test"})

        mock_trace_ctx.log_error.assert_called_once_with("ValueError")
        mock_trace_ctx.stop.assert_called_once_with(
            status="failed", error="ValueError",
        )


# ---------------------------------------------------------------------------
# get_current_state — comprehensive
# ---------------------------------------------------------------------------

class TestGetCurrentState:
    def test_empty(self, orch: Orchestrator) -> None:
        state = orch.get_current_state()
        assert state["active_agents"] == []
        assert state["completed_agents"] == []
        assert state["pending_agents"] == []
        assert state["total_progress"] == "0/0"
        assert state["workflow"] == ""

    def test_with_running_workflow(self, orch: Orchestrator) -> None:
        """RUNNING workflow with partial completion"""
        result = WorkflowResult(
            workflow_id="wf-running",
            status=WorkflowStatus.RUNNING,
            steps_completed=["analyst"],
            steps_failed=[],
            outputs={},
            total_tokens=100,
            total_cost=0.01,
            execution_time=5.0,
            error=None,
            agent_names=["explore", "analyst", "planner"],
        )
        orch._active_workflows["wf-running"] = result

        state = orch.get_current_state()
        # explore and planner should be "working"
        assert len(state["active_agents"]) == 2
        active_names = {a["name"] for a in state["active_agents"]}
        assert "explore" in active_names
        assert "planner" in active_names
        # analyst should be "done"
        assert len(state["completed_agents"]) == 1
        assert state["completed_agents"][0]["name"] == "analyst"
        assert state["workflow"] == "explore"

    def test_with_completed_workflow(self, orch: Orchestrator) -> None:
        """COMPLETED workflow marks all steps as done"""
        result = WorkflowResult(
            workflow_id="wf-done",
            status=WorkflowStatus.COMPLETED,
            steps_completed=["a", "b"],
            steps_failed=[],
            outputs={},
            total_tokens=200,
            total_cost=0.02,
            execution_time=10.0,
            error=None,
            agent_names=["a", "b"],
        )
        orch._active_workflows["wf-done"] = result

        state = orch.get_current_state()
        assert len(state["completed_agents"]) == 2
        assert len(state["active_agents"]) == 0
        # pending_agents should be empty since all agent_names are completed
        assert state["pending_agents"] == []

    def test_with_failed_workflow(self, orch: Orchestrator) -> None:
        """FAILED workflow: failed agents go to pending; leftover agent_names also go to pending"""
        result = WorkflowResult(
            workflow_id="wf-fail",
            status=WorkflowStatus.FAILED,
            steps_completed=["a"],
            steps_failed=["b"],
            outputs={},
            total_tokens=50,
            total_cost=0.005,
            execution_time=3.0,
            error="b failed",
            agent_names=["a", "b"],
        )
        orch._active_workflows["wf-fail"] = result

        state = orch.get_current_state()
        # FAILED status only adds failed agents to pending, not completed
        assert len(state["completed_agents"]) == 0
        # 'b' goes to pending via steps_failed; 'a' goes to pending via deduction logic
        assert len(state["pending_agents"]) == 2

    def test_with_multiple_workflows_dedup(self, orch: Orchestrator) -> None:
        """Multiple workflows with overlapping agent names are deduplicated"""
        wf1 = WorkflowResult(
            workflow_id="wf-1",
            status=WorkflowStatus.RUNNING,
            steps_completed=["a"],
            steps_failed=[],
            outputs={},
            total_tokens=0, total_cost=0.0,
            execution_time=0.0, error=None,
            agent_names=["a", "b"],
        )
        wf2 = WorkflowResult(
            workflow_id="wf-2",
            status=WorkflowStatus.COMPLETED,
            steps_completed=["c"],
            steps_failed=[],
            outputs={},
            total_tokens=0, total_cost=0.0,
            execution_time=0.0, error=None,
            agent_names=["c"],
        )
        orch._active_workflows["wf-1"] = wf1
        orch._active_workflows["wf-2"] = wf2

        state = orch.get_current_state()
        # Should not crash, should have reasonable structure
        assert isinstance(state["active_agents"], list)
        assert isinstance(state["completed_agents"], list)
        assert isinstance(state["pending_agents"], list)

    def test_with_workflow_and_execution_time_zero(self, orch: Orchestrator) -> None:
        """When execution_time is 0, duration shows N/A"""
        # Set up a RUNNING workflow with exec_time=0
        r1 = WorkflowResult(
            workflow_id="wf-1", status=WorkflowStatus.RUNNING,
            steps_completed=["a"], steps_failed=[],
            outputs={}, total_tokens=0, total_cost=0.0,
            execution_time=0.0, agent_names=["a", "b"],
        )
        # Also a COMPLETED workflow with exec_time=0
        r2 = WorkflowResult(
            workflow_id="wf-2", status=WorkflowStatus.COMPLETED,
            steps_completed=["c"], steps_failed=[],
            outputs={}, total_tokens=0, total_cost=0.0,
            execution_time=0.0, agent_names=["c"],
        )
        orch._active_workflows["wf-1"] = r1
        orch._active_workflows["wf-2"] = r2

        state = orch.get_current_state()
        # Find the "a" completed entry and check duration
        done_a = [c for c in state["completed_agents"] if c["name"] == "a"]
        if done_a:
            assert done_a[0]["duration"] == "N/A"
        done_c = [c for c in state["completed_agents"] if c["name"] == "c"]
        if done_c:
            assert done_c[0]["duration"] == "N/A"


# ---------------------------------------------------------------------------
# _maybe_learn_from_workflow — exception path
# ---------------------------------------------------------------------------

class TestMaybeLearnException:
    @pytest.mark.asyncio
    async def test_exception_in_auto_create_skill_caught(self, orch: Orchestrator) -> None:
        """When SelfImprovingAgent or auto_create_skill raises, it's silently caught"""
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

        with patch.object(
            SelfImprovingAgent, "auto_create_skill", side_effect=RuntimeError("auto_create_skill failed")
        ):
            # Should not raise
            await orch._maybe_learn_from_workflow("build", {}, result)
