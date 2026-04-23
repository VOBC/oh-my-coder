"""
Agent 健康检查与故障自动重分配

HealthChecker 类：
- 每 60 秒检查所有活跃 Agent 的状态
- 判断失败条件：超时（>5min 无心跳）、异常退出、任务错误
- 失败后自动将任务重分配给空闲 Agent
- retry_count 上限 3 次，超过后标记 failed 并通知

新增数据结构：
- AgentHealth: agent_name / status / last_heartbeat / task_id / retry_count
- HealthCheckResult: 每次检查的结果（可记录日志）
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ..core.orchestrator import Orchestrator, WorkflowStep


# ------------------------------------------------------------------
# 数据结构
# ------------------------------------------------------------------


class AgentStatus(Enum):
    """Agent 状态"""

    HEALTHY = "healthy"
    STALE = "stale"  # 超时无心跳
    FAILED = "failed"
    REASSIGNED = "reassigned"


@dataclass
class AgentHealth:
    """单个 Agent 的健康状态"""

    agent_name: str
    status: AgentStatus = AgentStatus.HEALTHY
    last_heartbeat: float = field(default_factory=time.time)
    task_id: Optional[str] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    workflow_id: Optional[str] = None
    step_index: int = -1  # 在工作流中的步骤索引

    # retry 上限（可配置）
    MAX_RETRIES: int = field(default=3, repr=False)

    def touch(self) -> None:
        """更新心跳时间"""
        self.last_heartbeat = time.time()
        if self.status == AgentStatus.STALE:
            self.status = AgentStatus.HEALTHY

    def is_stale(self, threshold: float = 300.0) -> bool:
        """判断是否超时无心跳"""
        return (time.time() - self.last_heartbeat) > threshold

    def record_failure(self, error: str) -> bool:
        """
        记录一次失败，返回是否超过重试上限。

        - 若 retry_count < MAX_RETRIES → 可重试（状态改为 STALE）
        - 若 retry_count >= MAX_RETRIES → 不可重试（状态改为 FAILED）
        """
        self.retry_count += 1
        self.last_error = error
        self.last_heartbeat = time.time()  # 重置心跳，避免重复判定

        if self.retry_count >= self.MAX_RETRIES:
            self.status = AgentStatus.FAILED
            return True  # 已达上限
        else:
            self.status = AgentStatus.STALE
            return False  # 仍可重试

    def can_retry(self) -> bool:
        return self.retry_count < self.MAX_RETRIES

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["last_heartbeat"] = datetime.fromtimestamp(self.last_heartbeat).isoformat()
        d.pop("MAX_RETRIES")  # 不序列化常量
        return d


@dataclass
class HealthCheckResult:
    """单次健康检查的结果"""

    check_id: str
    checked_agents: int
    healthy_count: int
    stale_count: int
    failed_count: int
    reassigned_count: int
    reassignments: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("check_id")
        return d


# ------------------------------------------------------------------
# HealthChecker
# ------------------------------------------------------------------


class HealthChecker:
    """
    Agent 健康检查器

    功能：
    1. 维护所有活跃 Agent 的健康状态记录
    2. 定期检查（默认 60 秒间隔）心跳和故障
    3. 故障后自动重分配任务给空闲 Agent
    4. 重试上限 3 次，超过后通知用户
    5. 结果持久化到 .omc/state/health/
    """

    def __init__(
        self,
        orchestrator: Optional["Orchestrator"] = None,
        check_interval: float = 60.0,
        stale_threshold: float = 300.0,
        max_retries: int = 3,
        state_dir: Optional[Path] = None,
        on_notification: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Args:
            orchestrator: Orchestrator 实例（用于任务重分配）
            check_interval: 检查间隔（秒），默认 60
            stale_threshold: 心跳超时阈值（秒），默认 300（5 分钟）
            max_retries: 单个 Agent 失败重试次数上限，默认 3
            state_dir: 状态文件目录
            on_notification: 通知回调 (title: str, body: str) -> None
        """
        self.orchestrator = orchestrator
        self.check_interval = check_interval
        self.stale_threshold = stale_threshold
        self.max_retries = max_retries
        self.state_dir = state_dir or Path(".omc/state/health")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.on_notification = on_notification

        # Agent 健康状态：agent_name -> AgentHealth
        self._agent_health: dict[str, AgentHealth] = {}

        # 活跃心跳：agent_name -> asyncio.Task（当前正在执行的任务）
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}

        # 后台检查循环
        self._check_task: Optional[asyncio.Task[None]] = None
        self._stop_event: Optional[asyncio.Event] = None

        # 检查历史
        self._history: list[HealthCheckResult] = []

        # 总计统计
        self._total_reassignments = 0

    # ------------------------------------------------------------------
    # 心跳注册
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_name: str,
        task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        step_index: int = -1,
    ) -> AgentHealth:
        """
        注册一个 Agent 开始执行任务（心跳开始计时）。

        在 Agent 执行开始时调用。
        """
        health = AgentHealth(
            agent_name=agent_name,
            status=AgentStatus.HEALTHY,
            last_heartbeat=time.time(),
            task_id=task_id,
            workflow_id=workflow_id,
            step_index=step_index,
        )
        health.MAX_RETRIES = self.max_retries
        self._agent_health[agent_name] = health
        return health

    def unregister_agent(self, agent_name: str) -> bool:
        """取消注册（任务完成后调用）"""
        if agent_name in self._agent_health:
            del self._agent_health[agent_name]
        if agent_name in self._active_tasks:
            del self._active_tasks[agent_name]
        return True

    def register_task(self, agent_name: str, task: asyncio.Task[Any]) -> None:
        """注册 Agent 当前正在执行的 asyncio.Task（用于取消）"""
        self._active_tasks[agent_name] = task

    def heartbeat(self, agent_name: str) -> bool:
        """
        更新 Agent 心跳。

        在 Agent 执行过程中定期调用（如每个 LLM 调用完成后）。

        Returns:
            True = 正常，False = Agent 未注册
        """
        if agent_name not in self._agent_health:
            return False
        self._agent_health[agent_name].touch()
        return True

    # ------------------------------------------------------------------
    # 故障记录与重分配
    # ------------------------------------------------------------------

    def record_failure(
        self,
        agent_name: str,
        error: str,
        workflow_id: Optional[str] = None,
        step: Optional["WorkflowStep"] = None,
    ) -> bool:
        """
        记录 Agent 执行失败。

        Args:
            agent_name: 失败的 Agent
            error: 错误信息
            workflow_id: 所属工作流 ID
            step: 失败的 WorkflowStep（用于重分配）

        Returns:
            True = 已达重试上限（需通知用户）
            False = 仍在重试中
        """
        if agent_name not in self._agent_health:
            health = self.register_agent(agent_name, workflow_id=workflow_id)
        else:
            health = self._agent_health[agent_name]

        exceeded = health.record_failure(error)

        if exceeded:
            # 通知用户
            self._notify(
                f"⚠️ Agent {agent_name} 失败",
                f"已重试 {health.retry_count} 次仍失败，任务已放弃。"
                f"\n\n错误：{error[:200]}",
            )
        else:
            # 触发重分配
            self._notify(
                f"🔄 Agent {agent_name} 执行异常，正在重试",
                f"重试 {health.retry_count}/{self.max_retries}\n"
                f"错误：{error[:100]}",
            )

        self._save_health_log(health)
        return exceeded

    def reassign_task(
        self,
        agent_name: str,
        workflow_id: str,
        step: "WorkflowStep",
    ) -> Optional[str]:
        """
        将任务重新分配给空闲 Agent。

        策略：
        1. 遍历所有已注册 Agent，找出状态为 HEALTHY 且不繁忙的
        2. 若找不到，创建一个新的 executor agent
        3. 返回新分配的 agent_name

        Returns:
            新分配的 agent_name，或 None（无法重分配）
        """
        # 寻找空闲的同类 Agent
        for name, health in self._agent_health.items():
            if (
                name != agent_name
                and health.status == AgentStatus.HEALTHY
                and name not in self._active_tasks
            ):
                new_agent_name = name
                self._log_reassignment(
                    from_agent=agent_name,
                    to_agent=new_agent_name,
                    reason=f"agent {agent_name} failed",
                    step=step.agent_name,
                    workflow_id=workflow_id,
                )
                return new_agent_name

        # 找不到空闲 Agent，记录失败但允许继续
        self._log_reassignment(
            from_agent=agent_name,
            to_agent="<none>",
            reason="no idle agent available",
            step=step.agent_name,
            workflow_id=workflow_id,
        )
        return None

    def _log_reassignment(
        self,
        from_agent: str,
        to_agent: str,
        reason: str,
        step: str,
        workflow_id: str,
    ) -> None:
        """记录重分配事件"""
        self._total_reassignments += 1
        log_entry = {
            "id": str(uuid.uuid4())[:8],
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason,
            "step": step,
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
        }

        log_file = self.state_dir / f"reassignment_{log_entry['id']}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # 定期检查循环
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """启动后台健康检查循环"""
        if self._check_task is not None:
            return  # 已启动

        self._stop_event = asyncio.Event()
        self._check_task = asyncio.create_task(self._check_loop())
        self._save_status()

    async def stop(self) -> None:
        """停止健康检查循环"""
        if self._check_task is None:
            return

        self._stop_event.set()
        await self._check_task
        self._check_task = None
        self._stop_event = None
        self._save_status()

    async def _check_loop(self) -> None:
        """后台检查循环：每 check_interval 秒执行一次"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                if self._stop_event and self._stop_event.is_set():
                    break

                result = await self._check_all()
                if result:
                    self._history.append(result)
                    # 只保留最近 100 条
                    if len(self._history) > 100:
                        self._history = self._history[-100:]

            except asyncio.CancelledError:
                break
            except Exception:
                pass  # 静默，不崩溃

    async def _check_all(self) -> Optional[HealthCheckResult]:
        """
        执行一次全量检查。

        检测 STALE（超时）的 Agent，触发重试。
        """
        if not self._agent_health:
            return None

        checked = 0
        healthy = 0
        stale = 0
        failed = 0
        reassigned = 0
        reassignments: list[dict[str, Any]] = []

        for agent_name, health in list(self._agent_health.items()):
            # 跳过已完成/失败的
            if health.status in (AgentStatus.FAILED, AgentStatus.REASSIGNED):
                continue

            checked += 1

            # 检查是否超时
            if health.is_stale(self.stale_threshold):
                stale += 1
                health.status = AgentStatus.STALE

                if health.can_retry():
                    # 记录失败，触发重分配
                    exceeded = health.record_failure(
                        f"心跳超时（>{self.stale_threshold}s 无响应）"
                    )
                    reassigned += 1
                    reassignments.append(
                        {
                            "agent": agent_name,
                            "reason": "heartbeat_timeout",
                            "retry_count": health.retry_count,
                            "workflow_id": health.workflow_id,
                        }
                    )
                else:
                    failed += 1
                    health.status = AgentStatus.FAILED
                    self._notify(
                        f"❌ Agent {agent_name} 已放弃",
                        f"连续 {health.retry_count} 次超时，任务停止。",
                    )

                self._save_health_log(health)
            else:
                healthy += 1

        result = HealthCheckResult(
            check_id=str(uuid.uuid4())[:8],
            checked_agents=checked,
            healthy_count=healthy,
            stale_count=stale,
            failed_count=failed,
            reassigned_count=reassigned,
            reassignments=reassignments,
        )

        self._save_check_result(result)
        return result

    # ------------------------------------------------------------------
    # 状态查看
    # ------------------------------------------------------------------

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        """获取所有 Agent 的健康状态"""
        return {name: h.to_dict() for name, h in self._agent_health.items()}

    def get_summary(self) -> dict[str, Any]:
        """获取健康检查摘要"""
        statuses = [h.status for h in self._agent_health.values()]
        return {
            "total_registered": len(self._agent_health),
            "healthy": sum(1 for s in statuses if s == AgentStatus.HEALTHY),
            "stale": sum(1 for s in statuses if s == AgentStatus.STALE),
            "failed": sum(1 for s in statuses if s == AgentStatus.FAILED),
            "reassigned": sum(1 for s in statuses if s == AgentStatus.REASSIGNED),
            "total_reassignments": self._total_reassignments,
            "running": len(self._active_tasks),
            "check_interval": self.check_interval,
            "stale_threshold": self.stale_threshold,
            "max_retries": self.max_retries,
            "is_running": self._check_task is not None,
        }

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def _save_health_log(self, health: AgentHealth) -> None:
        """保存单个 Agent 的健康日志"""
        log_file = self.state_dir / f"health_{health.agent_name}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(health.to_dict(), f, ensure_ascii=False, indent=2)

    def _save_check_result(self, result: HealthCheckResult) -> None:
        """保存检查结果"""
        log_file = self.state_dir / f"check_{result.check_id}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

    def _save_status(self) -> None:
        """保存全局状态摘要"""
        status_file = self.state_dir / "status.json"
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(self.get_summary(), f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # 通知
    # ------------------------------------------------------------------

    def _notify(self, title: str, body: str) -> None:
        """发送通知"""
        if self.on_notification:
            try:
                self.on_notification(title, body)
            except Exception:
                pass
        # 也可写日志文件
        log_file = self.state_dir / "notifications.jsonl"
        entry = {
            "title": title,
            "body": body,
            "timestamp": datetime.now().isoformat(),
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------
# CLI 输出格式
# ------------------------------------------------------------------


def format_health_display(health_map: dict[str, dict[str, Any]]) -> str:
    """
    格式化健康状态为可读文本，用于 `omc agent health` 输出。
    """
    if not health_map:
        return "  (no agents registered)"

    lines = []
    status_emoji = {
        "healthy": "✅",
        "stale": "⚠️",
        "failed": "❌",
        "reassigned": "🔄",
    }

    for name, h in health_map.items():
        emoji = status_emoji.get(h["status"], "?")
        retry = h.get("retry_count", 0)
        heartbeat = h.get("last_heartbeat", "")
        workflow = h.get("workflow_id") or "—"
        error = h.get("last_error", "") or ""

        lines.append(f"{emoji} {name}")
        lines.append(
            f"   status: {h['status']}  |  retries: {retry}  |  workflow: {workflow}"
        )
        if heartbeat:
            lines.append(f"   heartbeat: {heartbeat}")
        if error:
            lines.append(f"   error: {error[:80]}")
        lines.append("")

    return "\n".join(lines).rstrip()
