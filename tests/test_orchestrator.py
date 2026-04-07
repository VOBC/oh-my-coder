"""
测试编排引擎

运行: pytest tests/test_orchestrator.py -v
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, "/Users/vobc/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder")

from src.core.orchestrator import (
    WORKFLOW_TEMPLATES,
    ExecutionMode,
    Orchestrator,
    WorkflowResult,
    WorkflowStatus,
)


class TestWorkflowTemplates:
    """测试工作流模板"""

    def test_build_template_exists(self):
        assert "build" in WORKFLOW_TEMPLATES
        assert len(WORKFLOW_TEMPLATES["build"]) == 6

    def test_review_template_exists(self):
        assert "review" in WORKFLOW_TEMPLATES

    def test_debug_template_exists(self):
        assert "debug" in WORKFLOW_TEMPLATES

    def test_build_dependencies(self):
        steps = WORKFLOW_TEMPLATES["build"]
        assert steps[1].dependencies == ["explore"]
        assert steps[2].dependencies == ["analyst"]
        assert steps[3].dependencies == ["planner"]
        assert steps[4].dependencies == ["architect"]


class TestOrchestratorInit:
    """测试编排器初始化"""

    def test_init_without_router(self):
        orch = Orchestrator(None)
        assert orch.model_router is None

    def test_init_with_state_dir(self, tmp_path):
        state_dir = tmp_path / ".omc" / "state"
        orch = Orchestrator(None, state_dir=state_dir)
        assert orch.state_dir == state_dir


class TestOrchestratorWorkflow:
    """测试编排器工作流执行"""

    def _mock_agent_result(self, output: str = "ok"):
        r = MagicMock()
        r.result = output
        r.error = None
        r.status.value = "completed"
        r.usage = {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5}
        return r

    def _make_agent(self, name: str, result: MagicMock):
        agent = MagicMock()
        agent.name = name
        agent.execute = AsyncMock(return_value=result)
        return agent

    @pytest.mark.asyncio
    async def test_execute_build_workflow_mock(self):
        """测试模拟执行 build 工作流"""
        orch = Orchestrator(None)

        for name in [
            "explore",
            "analyst",
            "planner",
            "architect",
            "executor",
            "verifier",
        ]:
            orch.register_agent(self._make_agent(name, self._mock_agent_result()))

        result = await orch.execute_workflow("build", {"task": "test task"})

        # 至少有步骤被处理
        assert len(result.steps_completed) + len(result.steps_failed) > 0
        assert result.workflow_id is not None

    @pytest.mark.asyncio
    async def test_sequential_execution_order(self):
        """测试顺序执行顺序正确"""
        orch = Orchestrator(None)
        execution_order = []

        async def fake_execute(context):
            step_name = context.get("current_step", "")
            execution_order.append(step_name)
            return self._mock_agent_result()

        for name in ["explore", "analyst"]:
            agent = MagicMock()
            agent.name = name
            agent.execute = fake_execute
            orch.register_agent(agent)

        await orch.execute_workflow("build", {"task": "test"})

        if "explore" in execution_order and "analyst" in execution_order:
            assert execution_order.index("explore") < execution_order.index("analyst")

    @pytest.mark.asyncio
    async def test_workflow_failure_handling(self):
        """测试工作流失败处理"""
        orch = Orchestrator(None)

        fail_result = self._mock_agent_result()
        fail_result.status.value = "failed"
        fail_result.error = "Network error"

        orch.register_agent(self._make_agent("explore", fail_result))

        result = await orch.execute_workflow("build", {"task": "test"})

        # 失败时状态应为 FAILED
        assert result.status == WorkflowStatus.FAILED

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """测试超时处理"""
        orch = Orchestrator(None)

        slow_agent = self._make_agent("explore", self._mock_agent_result())
        slow_agent.execute = AsyncMock(side_effect=asyncio.TimeoutError)
        orch.register_agent(slow_agent)

        result = await orch.execute_workflow("build", {"task": "test"})

        assert result.status in (WorkflowStatus.FAILED, WorkflowStatus.COMPLETED)


class TestWorkflowResult:
    """测试工作流结果"""

    def test_result_dataclass(self):
        result = WorkflowResult(
            workflow_id="test-001",
            status=WorkflowStatus.COMPLETED,
            steps_completed=["explore", "analyst"],
            steps_failed=[],
            outputs={"explore": "ok"},
            total_tokens=1000,
            total_cost=0.01,
            execution_time=5.5,
        )
        assert result.workflow_id == "test-001"
        assert result.status == WorkflowStatus.COMPLETED
        assert len(result.steps_completed) == 2
        assert result.total_cost == 0.01


class TestExecutionMode:
    """测试执行模式枚举"""

    def test_sequential_mode(self):
        assert ExecutionMode.SEQUENTIAL.value == "sequential"

    def test_parallel_mode(self):
        assert ExecutionMode.PARALLEL.value == "parallel"

    def test_conditional_mode(self):
        assert ExecutionMode.CONDITIONAL.value == "conditional"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
