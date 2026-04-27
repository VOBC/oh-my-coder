from __future__ import annotations

"""
任务状态同步模块

实现多人共享任务状态，支持实时更新和订阅。
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MemberRole(str, Enum):
    """成员角色"""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


@dataclass
class TeamTask:
    """团队任务"""

    task_id: str
    team_id: str
    creator_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    assignee_id: str | None = None
    workflow: str = "build"
    model: str = "deepseek"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    tokens_used: int = 0
    cost: float = 0.0
    subscribers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "team_id": self.team_id,
            "creator_id": self.creator_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "assignee_id": self.assignee_id,
            "workflow": self.workflow,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "result": self.result,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "subscribers": self.subscribers,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TeamTask":
        """从字典创建"""
        return cls(
            task_id=data["task_id"],
            team_id=data["team_id"],
            creator_id=data["creator_id"],
            title=data["title"],
            description=data.get("description", ""),
            status=TaskStatus(data["status"]),
            assignee_id=data.get("assignee_id"),
            workflow=data.get("workflow", "build"),
            model=data.get("model", "deepseek"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            result=data.get("result"),
            error=data.get("error"),
            tokens_used=data.get("tokens_used", 0),
            cost=data.get("cost", 0.0),
            subscribers=data.get("subscribers", []),
        )


class TaskSync:
    """
    任务状态同步器

    支持：
    - 创建/更新/删除任务
    - 订阅任务更新
    - 获取团队任务列表
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        初始化

        Args:
            redis_url: Redis 连接地址
        """
        self.redis_url = redis_url
        self._redis: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._subscribers: dict[str, list[Callable]] = {}
        self._tasks_cache: dict[str, TeamTask] = {}
        self._use_memory = not REDIS_AVAILABLE

    async def connect(self) -> None:
        """连接 Redis"""
        if self._use_memory:
            return

        try:
            self._redis = await redis.from_url(self.redis_url)
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe("task_updates")
        except Exception as e:
            print(f"⚠️ Redis 连接失败，使用内存模式: {e}")
            self._use_memory = True

    async def disconnect(self) -> None:
        """断开连接"""
        if self._redis:
            await self._redis.close()

    def _get_task_key(self, task_id: str) -> str:
        """获取任务的 Redis 键"""
        return f"task:{task_id}"

    def _get_team_tasks_key(self, team_id: str) -> str:
        """获取团队任务列表的 Redis 键"""
        return f"team:{team_id}:tasks"

    async def create_task(
        self,
        task_id: str,
        team_id: str,
        creator_id: str,
        title: str,
        description: str = "",
        workflow: str = "build",
        model: str = "deepseek",
    ) -> TeamTask:
        """
        创建任务

        Args:
            task_id: 任务 ID
            team_id: 团队 ID
            creator_id: 创建者 ID
            title: 任务标题
            description: 任务描述
            workflow: 工作流类型
            model: 使用的模型

        Returns:
            TeamTask: 创建的任务
        """
        now = datetime.now()
        task = TeamTask(
            task_id=task_id,
            team_id=team_id,
            creator_id=creator_id,
            title=title,
            description=description,
            workflow=workflow,
            model=model,
            created_at=now,
            updated_at=now,
            subscribers=[creator_id],
        )

        if self._use_memory:
            self._tasks_cache[task_id] = task
        else:
            # 存储任务
            await self._redis.hset(
                self._get_task_key(task_id),
                mapping={"data": json.dumps(task.to_dict())},
            )
            # 添加到团队任务列表
            await self._redis.sadd(self._get_team_tasks_key(team_id), task_id)

        # 发布创建事件
        await self._publish_event("task_created", task.to_dict())

        return task

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        tokens_used: int = 0,
        cost: float = 0.0,
    ) -> TeamTask | None:
        """
        更新任务状态

        Args:
            task_id: 任务 ID
            status: 新状态
            result: 执行结果
            error: 错误信息
            tokens_used: 消耗的 Token 数
            cost: 成本

        Returns:
            TeamTask: 更新后的任务
        """
        task = await self.get_task(task_id)
        if not task:
            return None

        task.status = status
        task.updated_at = datetime.now()
        task.result = result
        task.error = error
        task.tokens_used = tokens_used
        task.cost = cost

        if status == TaskStatus.RUNNING:
            task.started_at = datetime.now()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.completed_at = datetime.now()

        if self._use_memory:
            self._tasks_cache[task_id] = task
        else:
            await self._redis.hset(
                self._get_task_key(task_id),
                mapping={"data": json.dumps(task.to_dict())},
            )

        # 发布更新事件
        await self._publish_event("task_updated", task.to_dict())

        return task

    async def get_task(self, task_id: str) -> TeamTask | None:
        """
        获取任务

        Args:
            task_id: 任务 ID

        Returns:
            TeamTask: 任务对象
        """
        if self._use_memory:
            return self._tasks_cache.get(task_id)

        data = await self._redis.hget(self._get_task_key(task_id), "data")
        if data:
            return TeamTask.from_dict(json.loads(data))
        return None

    async def get_team_tasks(self, team_id: str) -> list[TeamTask]:
        """
        获取团队所有任务

        Args:
            team_id: 团队 ID

        Returns:
            List[TeamTask]: 任务列表
        """
        if self._use_memory:
            return [t for t in self._tasks_cache.values() if t.team_id == team_id]

        task_ids = await self._redis.smembers(self._get_team_tasks_key(team_id))
        tasks = []
        for tid in task_ids:
            task = await self.get_task(tid.decode())
            if task:
                tasks.append(task)
        return tasks

    async def subscribe_task(self, task_id: str, user_id: str) -> bool:
        """
        订阅任务更新

        Args:
            task_id: 任务 ID
            user_id: 用户 ID

        Returns:
            bool: 是否成功
        """
        task = await self.get_task(task_id)
        if not task:
            return False

        if user_id not in task.subscribers:
            task.subscribers.append(user_id)
            if self._use_memory:
                self._tasks_cache[task_id] = task
            else:
                await self._redis.hset(
                    self._get_task_key(task_id),
                    mapping={"data": json.dumps(task.to_dict())},
                )

        return True

    async def unsubscribe_task(self, task_id: str, user_id: str) -> bool:
        """
        取消订阅任务

        Args:
            task_id: 任务 ID
            user_id: 用户 ID

        Returns:
            bool: 是否成功
        """
        task = await self.get_task(task_id)
        if not task:
            return False

        if user_id in task.subscribers:
            task.subscribers.remove(user_id)
            if self._use_memory:
                self._tasks_cache[task_id] = task
            else:
                await self._redis.hset(
                    self._get_task_key(task_id),
                    mapping={"data": json.dumps(task.to_dict())},
                )

        return True

    async def delete_task(self, task_id: str) -> bool:
        """
        删除任务

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功
        """
        task = await self.get_task(task_id)
        if not task:
            return False

        if self._use_memory:
            del self._tasks_cache[task_id]
        else:
            await self._redis.delete(self._get_task_key(task_id))
            await self._redis.srem(self._get_team_tasks_key(task.team_id), task_id)

        await self._publish_event("task_deleted", {"task_id": task_id})

        return True

    async def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """发布事件"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        if not self._use_memory and self._redis:
            await self._redis.publish("task_updates", json.dumps(event))

    async def listen_updates(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """
        监听任务更新

        Args:
            callback: 回调函数
        """
        if self._use_memory or not self._pubsub:
            return

        async for message in self._pubsub.listen():
            if message["type"] == "message":
                try:
                    event = json.loads(message["data"])
                    await callback(event)
                except Exception as e:
                    print(f"处理消息失败: {e}")


# 全局实例
task_sync = TaskSync()
