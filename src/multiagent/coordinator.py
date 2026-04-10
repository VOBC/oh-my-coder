"""
多 Agent 协作调度器

功能：
- 创建和调度子 Agent
- 并行任务分发
- 自动汇总结果
- omc multiagent status 查看协作状态
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


# ─────────────────────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────────────────────


class AgentRole(Enum):
    """Agent 角色"""

    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    PLANNER = "planner"
    EXPLORER = "explorer"
    EXECUTOR = "executor"
    CUSTOM = "custom"


class SubAgentStatus(Enum):
    """子 Agent 状态"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SubAgent:
    """子 Agent"""

    agent_id: str
    name: str
    role: str
    status: SubAgentStatus = SubAgentStatus.IDLE
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class TaskResult:
    """任务执行结果"""

    agent_id: str
    role: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration: Optional[float] = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "success": self.success,
            "output": str(self.output) if self.output is not None else None,
            "error": self.error,
            "duration": self.duration,
            "timestamp": self.timestamp,
        }


@dataclass
class CoordinationResult:
    """协作任务结果"""

    task_id: str
    results: list[TaskResult]
    summary: str
    started_at: str
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ─────────────────────────────────────────────────────────────
# 调度器
# ─────────────────────────────────────────────────────────────


AgentRunner = Callable[[SubAgent, str], Any]


class MultiAgentCoordinator:
    """多 Agent 协作调度器"""

    def __init__(self) -> None:
        self.agents: dict[str, SubAgent] = {}
        self.tasks: dict[str, list[str]] = {}  # task_id -> agent_ids
        self._runner: Optional[AgentRunner] = None
        self._history: list[CoordinationResult] = []

    def set_runner(self, runner: AgentRunner) -> None:
        """
        设置 Agent 执行器

        Args:
            runner: 异步函数 (agent: SubAgent, task: str) -> Any
        """
        self._runner = runner

    def spawn(
        self,
        role: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> SubAgent:
        """
        创建子 Agent

        Args:
            role: 角色（coder/reviewer/tester/...）
            name: Agent 名称
            metadata: 元数据

        Returns:
            SubAgent 实例
        """
        agent = SubAgent(
            agent_id=str(uuid.uuid4())[:8],
            name=name,
            role=role,
            status=SubAgentStatus.IDLE,
            metadata=metadata or {},
        )
        self.agents[agent.agent_id] = agent
        return agent

    async def dispatch(
        self,
        task: str,
        agents: list[SubAgent],
        task_id: str | None = None,
    ) -> CoordinationResult:
        """
        分发任务给多个 Agent（并行执行）

        Args:
            task: 任务描述
            agents: 目标 Agent 列表
            task_id: 任务 ID（可选，自动生成）

        Returns:
            协作结果
        """
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]

        started_at = datetime.now().isoformat()
        self.tasks[task_id] = [a.agent_id for a in agents]

        # 并行执行
        results: list[TaskResult] = []
        coroutines = [self._run_agent(agent, task) for agent in agents]
        task_results = await asyncio.gather(*coroutines, return_exceptions=True)

        for agent, result in zip(agents, task_results):
            if isinstance(result, Exception):
                results.append(
                    TaskResult(
                        agent_id=agent.agent_id,
                        role=agent.role,
                        success=False,
                        output=None,
                        error=str(result),
                    )
                )
            else:
                results.append(result)

        coordination = CoordinationResult(
            task_id=task_id,
            results=results,
            summary=self._summarize(results),
            started_at=started_at,
            completed_at=datetime.now().isoformat(),
        )
        self._history.append(coordination)
        return coordination

    async def dispatch_sequential(
        self,
        task: str,
        agents: list[SubAgent],
        task_id: str | None = None,
    ) -> CoordinationResult:
        """
        分发任务给多个 Agent（顺序执行）

        Args:
            task: 任务描述
            agents: 目标 Agent 列表
            task_id: 任务 ID（可选，自动生成）

        Returns:
            协作结果
        """
        if task_id is None:
            task_id = str(uuid.uuid4())[:8]

        started_at = datetime.now().isoformat()
        self.tasks[task_id] = [a.agent_id for a in agents]

        results: list[TaskResult] = []
        context = task

        for agent in agents:
            result = await self._run_agent(agent, context)
            results.append(result)
            if isinstance(result, Exception):
                break
            # 将前一个 Agent 的输出作为下一个 Agent 的输入
            if result.output:
                context = f"{context}\n\n上一Agent输出:\n{result.output}"

        coordination = CoordinationResult(
            task_id=task_id,
            results=results,
            summary=self._summarize(results),
            started_at=started_at,
            completed_at=datetime.now().isoformat(),
        )
        self._history.append(coordination)
        return coordination

    async def _run_agent(self, agent: SubAgent, task: str) -> TaskResult:
        """运行单个 Agent"""
        import time

        agent.status = SubAgentStatus.RUNNING
        start = time.time()

        try:
            if self._runner is not None:
                output = await self._runner(agent, task)
            else:
                output = f"[模拟] {agent.name} 执行任务: {task[:50]}..."

            agent.status = SubAgentStatus.COMPLETED
            return TaskResult(
                agent_id=agent.agent_id,
                role=agent.role,
                success=True,
                output=output,
                duration=time.time() - start,
            )
        except Exception as e:
            agent.status = SubAgentStatus.FAILED
            return TaskResult(
                agent_id=agent.agent_id,
                role=agent.role,
                success=False,
                output=None,
                error=str(e),
                duration=time.time() - start,
            )

    def get_status(self) -> dict[str, Any]:
        """获取所有 Agent 状态"""
        return {
            "agents": [a.to_dict() for a in self.agents.values()],
            "active_tasks": len(self.tasks),
            "total_agents": len(self.agents),
            "running": sum(
                1 for a in self.agents.values() if a.status == SubAgentStatus.RUNNING
            ),
            "completed": sum(
                1 for a in self.agents.values() if a.status == SubAgentStatus.COMPLETED
            ),
            "failed": sum(
                1 for a in self.agents.values() if a.status == SubAgentStatus.FAILED
            ),
            "idle": sum(
                1 for a in self.agents.values() if a.status == SubAgentStatus.IDLE
            ),
        }

    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        """获取指定 Agent"""
        return self.agents.get(agent_id)

    def remove_agent(self, agent_id: str) -> bool:
        """移除 Agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False

    def clear_agents(self) -> None:
        """清空所有 Agent"""
        self.agents.clear()
        self.tasks.clear()

    def _summarize(self, results: list[TaskResult]) -> str:
        """汇总结果"""
        total = len(results)
        success = sum(1 for r in results if r.success)
        failed = total - success

        role_summary = {}
        for r in results:
            role_summary.setdefault(r.role, {"success": 0, "failed": 0})
            if r.success:
                role_summary[r.role]["success"] += 1
            else:
                role_summary[r.role]["failed"] += 1

        lines = [f"总任务: {total}, 成功: {success}, 失败: {failed}"]
        for role, counts in role_summary.items():
            lines.append(f"  {role}: 成功 {counts['success']}, 失败 {counts['failed']}")

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 全局单例
# ─────────────────────────────────────────────────────────────


_coordinator: Optional[MultiAgentCoordinator] = None


def get_coordinator() -> MultiAgentCoordinator:
    """获取全局协调器实例"""
    global _coordinator
    if _coordinator is None:
        _coordinator = MultiAgentCoordinator()
    return _coordinator
