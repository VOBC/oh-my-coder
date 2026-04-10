"""多 Agent 协作模块"""

from .coordinator import (
    SubAgent,
    SubAgentStatus,
    AgentRole,
    TaskResult,
    CoordinationResult,
    MultiAgentCoordinator,
    get_coordinator,
)

__all__ = [
    "SubAgent",
    "SubAgentStatus",
    "AgentRole",
    "TaskResult",
    "CoordinationResult",
    "MultiAgentCoordinator",
    "get_coordinator",
]
