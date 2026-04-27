from __future__ import annotations

"""
任务历史和回放模块

功能：
1. TaskHistory - 任务历史记录
2. TaskReplay - 任务回放功能
3. TaskCheckpoint - 任务检查点
4. 支持从任意点恢复执行
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ReplayStatus(str, Enum):
    """回放状态"""

    READY = "ready"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    """步骤状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepExecution:
    """步骤执行记录"""

    step_id: str
    agent_name: str
    description: str
    status: StepStatus
    input_context: dict[str, Any]
    output: dict[str, Any] | None = None
    error: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    duration_seconds: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "agent_name": self.agent_name,
            "description": self.description,
            "status": self.status.value,
            "input_context": self.input_context,
            "output": self.output,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepExecution":
        """从字典创建"""
        return cls(
            step_id=data["step_id"],
            agent_name=data["agent_name"],
            description=data["description"],
            status=StepStatus(data["status"]),
            input_context=data.get("input_context", {}),
            output=data.get("output"),
            error=data.get("error"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            duration_seconds=data.get("duration_seconds", 0.0),
            tokens_used=data.get("tokens_used", 0),
            cost=data.get("cost", 0.0),
            retry_count=data.get("retry_count", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TaskHistory:
    """任务历史记录"""

    history_id: str
    task_description: str
    workflow_name: str
    steps: list[StepExecution] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    total_duration: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: StepExecution) -> None:
        """添加步骤"""
        self.steps.append(step)
        self.updated_at = datetime.now().isoformat()

    def update_totals(self) -> None:
        """更新总计"""
        self.total_tokens = sum(s.tokens_used for s in self.steps)
        self.total_cost = sum(s.cost for s in self.steps)
        self.total_duration = sum(s.duration_seconds for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        self.update_totals()
        return {
            "history_id": self.history_id,
            "task_description": self.task_description,
            "workflow_name": self.workflow_name,
            "steps": [s.to_dict() for s in self.steps],
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "total_duration": self.total_duration,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskHistory":
        """从字典创建"""
        return cls(
            history_id=data["history_id"],
            task_description=data["task_description"],
            workflow_name=data["workflow_name"],
            steps=[StepExecution.from_dict(s) for s in data.get("steps", [])],
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
            total_duration=data.get("total_duration", 0.0),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def get_step(self, step_id: str) -> StepExecution | None:
        """获取步骤"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_steps_by_agent(self, agent_name: str) -> list[StepExecution]:
        """按 Agent 获取步骤"""
        return [s for s in self.steps if s.agent_name == agent_name]

    def get_failed_steps(self) -> list[StepExecution]:
        """获取失败步骤"""
        return [s for s in self.steps if s.status == StepStatus.FAILED]


class TaskCheckpoint:
    """任务检查点"""

    def __init__(self, history: TaskHistory, step_index: int = 0):
        """
        Args:
            history: 任务历史
            step_index: 检查点位置
        """
        self.history = history
        self.step_index = step_index
        self.checkpoint_id = str(uuid.uuid4())[:8]
        self.created_at = datetime.now().isoformat()

    def can_resume_from(self, step_id: str) -> bool:
        """检查是否可以从指定步骤恢复"""
        for i, step in enumerate(self.history.steps):
            if step.step_id == step_id:
                return i <= self.step_index
        return False

    def get_resume_context(self) -> dict[str, Any]:
        """获取恢复上下文"""
        completed_steps = self.history.steps[: self.step_index]
        return {
            "completed_outputs": {
                s.step_id: s.output for s in completed_steps if s.output
            },
            "history_id": self.history.history_id,
            "resume_from_index": self.step_index,
        }

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "history_id": self.history.history_id,
            "step_index": self.step_index,
            "created_at": self.created_at,
        }


class TaskReplay:
    """任务回放器"""

    def __init__(self, history: TaskHistory):
        """
        Args:
            history: 任务历史记录
        """
        self.history = history
        self.current_step_index = 0
        self.status = ReplayStatus.READY
        self.speed = 1.0  # 回放速度倍数
        self._callbacks: dict[str, Any] = {}

    def on_step_start(self, callback) -> None:
        """注册步骤开始回调"""
        self._callbacks["step_start"] = callback

    def on_step_complete(self, callback) -> None:
        """注册步骤完成回调"""
        self._callbacks["step_complete"] = callback

    def on_replay_complete(self, callback) -> None:
        """注册回放完成回调"""
        self._callbacks["replay_complete"] = callback

    async def replay(
        self,
        step_by_step: bool = False,
        start_from: int = 0,
    ) -> None:
        """
        执行回放

        Args:
            step_by_step: 是否单步执行
            start_from: 开始位置
        """
        self.status = ReplayStatus.PLAYING
        self.current_step_index = start_from

        steps = self.history.steps[start_from:]

        for i, step in enumerate(steps):
            if self.status == ReplayStatus.PAUSED:
                break

            if self.status == ReplayStatus.FAILED:
                break

            index = start_from + i

            # 触发步骤开始回调
            if "step_start" in self._callbacks:
                await self._callbacks["step_start"](step, index)

            # 模拟执行延迟
            if step.duration_seconds > 0:
                delay = step.duration_seconds / self.speed
                await self._async_sleep(delay)

            # 触发步骤完成回调
            if "step_complete" in self._callbacks:
                await self._callbacks["step_complete"](step, index)

            self.current_step_index = index + 1

            # 单步模式暂停
            if step_by_step:
                self.status = ReplayStatus.PAUSED
                break

        if self.current_step_index >= len(self.history.steps):
            self.status = ReplayStatus.COMPLETED
            if "replay_complete" in self._callbacks:
                await self._callbacks["replay_complete"]()

    async def _async_sleep(self, seconds: float) -> None:
        """异步睡眠"""
        import asyncio

        await asyncio.sleep(seconds)

    def pause(self) -> None:
        """暂停回放"""
        self.status = ReplayStatus.PAUSED

    def resume(self) -> None:
        """恢复回放"""
        if self.status == ReplayStatus.PAUSED:
            self.status = ReplayStatus.PLAYING

    def stop(self) -> None:
        """停止回放"""
        self.status = ReplayStatus.FAILED

    def set_speed(self, speed: float) -> None:
        """设置回放速度"""
        self.speed = max(0.1, min(10.0, speed))

    def get_progress(self) -> dict[str, Any]:
        """获取进度"""
        total = len(self.history.steps)
        current = self.current_step_index
        return {
            "status": self.status.value,
            "current_step": current,
            "total_steps": total,
            "progress_percent": (current / total * 100) if total > 0 else 0,
            "speed": self.speed,
        }


class HistoryManager:
    """历史记录管理器"""

    def __init__(self, storage_dir: Path | None = None):
        """
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = storage_dir or Path(".omc/history")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存
        self._histories: dict[str, TaskHistory] = {}
        self._checkpoints: dict[str, TaskCheckpoint] = {}

    def create_history(
        self,
        task_description: str,
        workflow_name: str,
        tags: list[str] | None = None,
    ) -> TaskHistory:
        """创建新的历史记录"""
        history_id = str(uuid.uuid4())[:8]

        history = TaskHistory(
            history_id=history_id,
            task_description=task_description,
            workflow_name=workflow_name,
            tags=tags or [],
        )

        self._histories[history_id] = history
        return history

    def save_history(self, history: TaskHistory) -> Path:
        """保存历史记录"""
        history_file = self.storage_dir / f"history_{history.history_id}.json"

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history.to_dict(), f, ensure_ascii=False, indent=2)

        return history_file

    def load_history(self, history_id: str) -> TaskHistory | None:
        """加载历史记录"""
        if history_id in self._histories:
            return self._histories[history_id]

        history_file = self.storage_dir / f"history_{history_id}.json"

        if not history_file.exists():
            return None

        with open(history_file, encoding="utf-8") as f:
            data = json.load(f)

        history = TaskHistory.from_dict(data)
        self._histories[history_id] = history
        return history

    def list_histories(
        self,
        limit: int = 50,
        tags: list[str] | None = None,
    ) -> list[TaskHistory]:
        """列出历史记录"""
        histories = []

        for file in self.storage_dir.glob("history_*.json"):
            try:
                history = self.load_history(file.stem.replace("history_", ""))
                if history:
                    if tags and not any(t in history.tags for t in tags):
                        continue
                    histories.append(history)
            except Exception:
                continue

        # 按时间排序
        histories.sort(key=lambda h: h.created_at, reverse=True)
        return histories[:limit]

    def create_checkpoint(
        self,
        history: TaskHistory,
        step_index: int,
    ) -> TaskCheckpoint:
        """创建检查点"""
        checkpoint = TaskCheckpoint(history, step_index)
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint

        # 保存检查点元数据
        checkpoint_file = (
            self.storage_dir / f"checkpoint_{checkpoint.checkpoint_id}.json"
        )
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)

        return checkpoint

    def load_checkpoint(self, checkpoint_id: str) -> TaskCheckpoint | None:
        """加载检查点"""
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]

        checkpoint_file = self.storage_dir / f"checkpoint_{checkpoint_id}.json"

        if not checkpoint_file.exists():
            return None

        with open(checkpoint_file, encoding="utf-8") as f:
            data = json.load(f)

        history = self.load_history(data["history_id"])
        if not history:
            return None

        checkpoint = TaskCheckpoint(history, data["step_index"])
        checkpoint.checkpoint_id = data["checkpoint_id"]
        checkpoint.created_at = data["created_at"]
        self._checkpoints[checkpoint_id] = checkpoint

        return checkpoint

    def delete_history(self, history_id: str) -> bool:
        """删除历史记录"""
        history_file = self.storage_dir / f"history_{history_id}.json"

        if history_file.exists():
            history_file.unlink()

        if history_id in self._histories:
            del self._histories[history_id]

        return True

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        histories = self.list_histories()

        total_tokens = sum(h.total_tokens for h in histories)
        total_cost = sum(h.total_cost for h in histories)
        total_duration = sum(h.total_duration for h in histories)

        return {
            "total_histories": len(histories),
            "total_steps": sum(len(h.steps) for h in histories),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "total_duration_hours": total_duration / 3600,
            "average_steps_per_task": (
                sum(len(h.steps) for h in histories) / len(histories)
                if histories
                else 0
            ),
        }


def create_step_execution(
    agent_name: str,
    description: str,
    input_context: dict[str, Any],
) -> StepExecution:
    """创建步骤执行记录"""
    return StepExecution(
        step_id=f"{agent_name}_{str(uuid.uuid4())[:6]}",
        agent_name=agent_name,
        description=description,
        status=StepStatus.PENDING,
        input_context=input_context,
        start_time=datetime.now().isoformat(),
    )


def complete_step_execution(
    step: StepExecution,
    output: dict[str, Any],
    tokens_used: int = 0,
    cost: float = 0.0,
) -> StepExecution:
    """完成步骤执行"""
    step.status = StepStatus.COMPLETED
    step.output = output
    step.end_time = datetime.now().isoformat()
    step.tokens_used = tokens_used
    step.cost = cost

    if step.start_time:
        start = datetime.fromisoformat(step.start_time)
        end = datetime.fromisoformat(step.end_time)
        step.duration_seconds = (end - start).total_seconds()

    return step


def fail_step_execution(
    step: StepExecution,
    error: str,
) -> StepExecution:
    """标记步骤失败"""
    step.status = StepStatus.FAILED
    step.error = error
    step.end_time = datetime.now().isoformat()

    if step.start_time:
        start = datetime.fromisoformat(step.start_time)
        end = datetime.fromisoformat(step.end_time)
        step.duration_seconds = (end - start).total_seconds()

    return step
