"""
Core 模块 - 核心功能

提供：
- Agent 基类和注册机制
- 模型路由器
- 任务路由器
- 编排器
- 任务历史和回放
- 上下文管理
"""

from .router import ModelRouter, TaskType
from .orchestrator import Orchestrator, WorkflowResult, WorkflowStep
from .history import (
    HistoryManager,
    TaskHistory,
    TaskReplay,
    TaskCheckpoint,
    StepExecution,
    create_step_execution,
    complete_step_execution,
    fail_step_execution,
)

__all__ = [
    # Router
    "ModelRouter",
    "TaskType",
    # Orchestrator
    "Orchestrator",
    "WorkflowResult",
    "WorkflowStep",
    # History
    "HistoryManager",
    "TaskHistory",
    "TaskReplay",
    "TaskCheckpoint",
    "StepExecution",
    "create_step_execution",
    "complete_step_execution",
    "fail_step_execution",
]
