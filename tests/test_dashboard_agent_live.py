"""
测试 Dashboard Agent Live SSE 端点
P2-3: Web Agent 协作可视化

- orchestrator.get_current_state() 逻辑测试（纯单元测试）
- WorkflowResult.agent_names 字段测试
- execute_workflow 填充 agent_names 测试
- SSE HTTP 行为测试（见 test_web.py）
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock


# ------------------------------------------------------------------
# 测试 get_current_state() - orchestrator 核心方法
# ------------------------------------------------------------------


def test_get_current_state_empty():
    """空状态时返回空列表"""
    from src.core.orchestrator import Orchestrator

    orch = Orchestrator(model_router=MagicMock())
    state = orch.get_current_state()

    assert state["active_agents"] == []
    assert state["completed_agents"] == []
    assert state["pending_agents"] == []
    assert state["total_progress"] == "0/0"
    assert "timestamp" in state


def test_get_current_state_single_running_workflow():
    """单个运行中工作流：正确区分 active / pending"""
    from src.core.orchestrator import Orchestrator, WorkflowResult, WorkflowStatus

    orch = Orchestrator(model_router=MagicMock())

    wf = WorkflowResult(
        workflow_id="wf-001",
        status=WorkflowStatus.RUNNING,
        steps_completed=["explore"],
        steps_failed=[],
        outputs={},
        total_tokens=0,
        total_cost=0.0,
        execution_time=0.0,
        agent_names=["explore", "analyst", "planner"],
    )
    orch._active_workflows["wf-001"] = wf

    state = orch.get_current_state()

    active_names = [a["name"] for a in state["active_agents"]]
    assert "analyst" in active_names
    assert "planner" in active_names
    assert "explore" not in active_names

    completed_names = [a["name"] for a in state["completed_agents"]]
    assert "explore" in completed_names

    assert state["pending_agents"] == []


def test_get_current_state_completed_workflow():
    """已完成工作流：全部标记为 done"""
    from src.core.orchestrator import Orchestrator, WorkflowResult, WorkflowStatus

    orch = Orchestrator(model_router=MagicMock())

    wf = WorkflowResult(
        workflow_id="wf-002",
        status=WorkflowStatus.COMPLETED,
        steps_completed=["explore", "analyst", "planner", "executor", "verifier"],
        steps_failed=[],
        outputs={},
        total_tokens=100,
        total_cost=0.05,
        execution_time=12.5,
        agent_names=["explore", "analyst", "planner", "executor", "verifier"],
    )
    orch._active_workflows["wf-002"] = wf

    state = orch.get_current_state()

    assert state["active_agents"] == []
    completed_names = [a["name"] for a in state["completed_agents"]]
    assert "explore" in completed_names
    assert "executor" in completed_names
    assert "verifier" in completed_names
    assert state["total_progress"] == "5/5"


def test_get_current_state_failed_workflow():
    """失败工作流：failed agent 放入 pending"""
    from src.core.orchestrator import Orchestrator, WorkflowResult, WorkflowStatus

    orch = Orchestrator(model_router=MagicMock())

    wf = WorkflowResult(
        workflow_id="wf-003",
        status=WorkflowStatus.FAILED,
        steps_completed=["explore", "analyst"],
        steps_failed=["planner"],
        outputs={},
        total_tokens=50,
        total_cost=0.02,
        execution_time=5.0,
        agent_names=["explore", "analyst", "planner", "executor"],
    )
    orch._active_workflows["wf-003"] = wf

    state = orch.get_current_state()

    assert "planner" in state["pending_agents"]
    assert "executor" in state["pending_agents"]


def test_get_current_state_progress():
    """进度统计正确"""
    from src.core.orchestrator import Orchestrator, WorkflowResult, WorkflowStatus

    orch = Orchestrator(model_router=MagicMock())

    wf = WorkflowResult(
        workflow_id="wf-004",
        status=WorkflowStatus.RUNNING,
        steps_completed=["explore", "analyst", "planner"],
        steps_failed=[],
        outputs={},
        total_tokens=0,
        total_cost=0.0,
        execution_time=0.0,
        agent_names=[
            "explore",
            "analyst",
            "planner",
            "executor",
            "verifier",
            "debugger",
        ],
    )
    orch._active_workflows["wf-004"] = wf

    state = orch.get_current_state()
    assert state["total_progress"] == "3/6"


def test_get_current_state_duration_shown():
    """已完成 Agent 显示耗时"""
    from src.core.orchestrator import Orchestrator, WorkflowResult, WorkflowStatus

    orch = Orchestrator(model_router=MagicMock())

    wf = WorkflowResult(
        workflow_id="wf-005",
        status=WorkflowStatus.COMPLETED,
        steps_completed=["explore", "analyst"],
        steps_failed=[],
        outputs={},
        total_tokens=80,
        total_cost=0.04,
        execution_time=7.3,
        agent_names=["explore", "analyst"],
    )
    orch._active_workflows["wf-005"] = wf

    state = orch.get_current_state()
    completed = {a["name"]: a for a in state["completed_agents"]}
    assert completed["explore"]["duration"] == "7s"
    assert completed["analyst"]["duration"] == "7s"


# ------------------------------------------------------------------
# 测试 WorkflowResult.agent_names 字段
# ------------------------------------------------------------------


def test_workflow_result_has_agent_names():
    """WorkflowResult 支持 agent_names"""
    from src.core.orchestrator import WorkflowResult, WorkflowStatus

    wf = WorkflowResult(
        workflow_id="test",
        status=WorkflowStatus.PENDING,
        steps_completed=[],
        steps_failed=[],
        outputs={},
        total_tokens=0,
        total_cost=0.0,
        execution_time=0.0,
        agent_names=["explore", "analyst"],
    )
    assert wf.agent_names == ["explore", "analyst"]


def test_execute_workflow_sets_agent_names():
    """execute_workflow 自动填充 agent_names"""
    from src.core.orchestrator import ExecutionMode, Orchestrator, WorkflowStatus

    orch = Orchestrator(model_router=MagicMock())

    for agent_name in [
        "explore",
        "analyst",
        "planner",
        "architect",
        "executor",
        "verifier",
    ]:
        mock_agent = MagicMock()
        mock_agent.name = agent_name
        mock_agent.execute = AsyncMock(
            return_value=MagicMock(
                status=MagicMock(value="completed"), usage={"total_tokens": 0}
            )
        )
        orch.register_agent(mock_agent)

    result = asyncio.run(
        orch.execute_workflow(
            "build",
            {"task": "test"},
            mode=ExecutionMode.SEQUENTIAL,
            skip_checkpoint=True,
        )
    )

    assert result.agent_names == [
        "explore",
        "analyst",
        "planner",
        "architect",
        "executor",
        "verifier",
    ]
    assert result.status == WorkflowStatus.COMPLETED
