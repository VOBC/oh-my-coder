"""多 Agent 协作模块"""

from .coordinator import (
    AgentRole,
    CoordinationResult,
    MultiAgentCoordinator,
    SubAgent,
    SubAgentStatus,
    TaskResult,
    get_coordinator,
)

__all__ = [
    "AgentRole",
    "CoordinationResult",
    "MultiAgentCoordinator",
    "SubAgent",
    "SubAgentStatus",
    "TaskResult",
    "get_coordinator",
]
