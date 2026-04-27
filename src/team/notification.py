from __future__ import annotations

"""
消息通知模块

实现任务完成通知和团队广播。
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

try:
    from fastapi import WebSocket

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    WebSocket = None


class NotificationType(str, Enum):
    """通知类型"""

    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TEAM_BROADCAST = "team_broadcast"
    USER_MENTION = "user_mention"
    SYSTEM = "system"


class NotificationPriority(str, Enum):
    """通知优先级"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """通知消息"""

    notification_id: str
    type: NotificationType
    title: str
    message: str
    team_id: str | None = None
    user_id: str | None = None
    task_id: str | None = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    read: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "team_id": self.team_id,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "priority": self.priority.value,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "read": self.read,
        }


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self._connections: dict[str, list[Any]] = {}
        self._user_connections: dict[str, Any] = {}

    async def connect(self, websocket: Any, user_id: str, team_id: str) -> None:
        """建立连接"""
        await websocket.accept()
        key = f"{team_id}:{user_id}"
        if key not in self._connections:
            self._connections[key] = []
        self._connections[key].append(websocket)
        self._user_connections[user_id] = websocket

    def disconnect(self, websocket: Any, user_id: str, team_id: str) -> None:
        """断开连接"""
        key = f"{team_id}:{user_id}"
        if key in self._connections:
            if websocket in self._connections[key]:
                self._connections[key].remove(websocket)
            if not self._connections[key]:
                del self._connections[key]
        if user_id in self._user_connections:
            del self._user_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> bool:
        """发送消息给用户"""
        if user_id in self._user_connections:
            try:
                await self._user_connections[user_id].send_json(message)
                return True
            except Exception:
                self._user_connections.pop(user_id, None)
        return False

    async def broadcast_to_team(self, team_id: str, message: dict[str, Any]) -> int:
        """广播给团队"""
        count = 0
        for key, connections in list(self._connections.items()):
            if key.startswith(f"{team_id}:"):
                for conn in connections:
                    try:
                        await conn.send_json(message)
                        count += 1
                    except Exception:
                        pass
        return count


class TeamNotifier:
    """
    团队通知器

    支持：
    - 任务完成/失败通知
    - 团队广播
    - WebSocket 实时推送
    """

    def __init__(self):
        self.manager = ConnectionManager()
        self._notification_history: dict[str, list[Notification]] = {}
        self._handlers: dict[NotificationType, list[Callable]] = {}

    def register_handler(
        self,
        notification_type: NotificationType,
        handler: Callable[[Notification], None],
    ) -> None:
        """注册通知处理器"""
        if notification_type not in self._handlers:
            self._handlers[notification_type] = []
        self._handlers[notification_type].append(handler)

    async def _dispatch(self, notification: Notification) -> None:
        """分发通知到处理器"""
        handlers = self._handlers.get(notification.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(notification)
                else:
                    handler(notification)
            except Exception as e:
                print(f"通知处理器执行失败: {e}")

    async def notify_task_created(
        self,
        task_id: str,
        team_id: str,
        creator_id: str,
        title: str,
    ) -> Notification:
        """
        通知任务创建

        Args:
            task_id: 任务 ID
            team_id: 团队 ID
            creator_id: 创建者 ID
            title: 任务标题

        Returns:
            Notification: 创建的通知
        """
        notification = Notification(
            notification_id=f"notif_{task_id}_created",
            type=NotificationType.TASK_CREATED,
            title="新任务已创建",
            message=f"任务「{title}」已创建",
            team_id=team_id,
            user_id=creator_id,
            task_id=task_id,
            data={"title": title},
        )

        await self._store_notification(notification)
        await self._dispatch(notification)

        # 广播给团队
        await self.manager.broadcast_to_team(
            team_id,
            {
                "type": "notification",
                "data": notification.to_dict(),
            },
        )

        return notification

    async def notify_task_completed(
        self,
        task_id: str,
        team_id: str,
        title: str,
        result: dict[str, Any],
    ) -> Notification:
        """
        通知任务完成

        Args:
            task_id: 任务 ID
            team_id: 团队 ID
            title: 任务标题
            result: 执行结果

        Returns:
            Notification: 创建的通知
        """
        notification = Notification(
            notification_id=f"notif_{task_id}_completed",
            type=NotificationType.TASK_COMPLETED,
            title="任务执行完成",
            message=f"任务「{title}」已成功完成",
            team_id=team_id,
            task_id=task_id,
            priority=NotificationPriority.NORMAL,
            data={"result": result},
        )

        await self._store_notification(notification)
        await self._dispatch(notification)

        # 广播给团队
        await self.manager.broadcast_to_team(
            team_id,
            {
                "type": "notification",
                "data": notification.to_dict(),
            },
        )

        return notification

    async def notify_task_failed(
        self,
        task_id: str,
        team_id: str,
        title: str,
        error: str,
    ) -> Notification:
        """
        通知任务失败

        Args:
            task_id: 任务 ID
            team_id: 团队 ID
            title: 任务标题
            error: 错误信息

        Returns:
            Notification: 创建的通知
        """
        notification = Notification(
            notification_id=f"notif_{task_id}_failed",
            type=NotificationType.TASK_FAILED,
            title="任务执行失败",
            message=f"任务「{title}」执行失败: {error}",
            team_id=team_id,
            task_id=task_id,
            priority=NotificationPriority.HIGH,
            data={"error": error},
        )

        await self._store_notification(notification)
        await self._dispatch(notification)

        # 广播给团队
        await self.manager.broadcast_to_team(
            team_id,
            {
                "type": "notification",
                "data": notification.to_dict(),
            },
        )

        return notification

    async def broadcast(
        self,
        team_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> Notification:
        """
        团队广播消息

        Args:
            team_id: 团队 ID
            title: 消息标题
            message: 消息内容
            priority: 优先级

        Returns:
            Notification: 创建的通知
        """
        notification = Notification(
            notification_id=f"notif_broadcast_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=NotificationType.TEAM_BROADCAST,
            title=title,
            message=message,
            team_id=team_id,
            priority=priority,
        )

        await self._store_notification(notification)
        await self._dispatch(notification)

        # 广播给团队所有成员
        count = await self.manager.broadcast_to_team(
            team_id,
            {
                "type": "broadcast",
                "data": notification.to_dict(),
            },
        )

        notification.data["delivered_to"] = count
        return notification

    async def notify_user(
        self,
        user_id: str,
        team_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> Notification:
        """
        发送用户通知

        Args:
            user_id: 用户 ID
            team_id: 团队 ID
            title: 标题
            message: 消息内容
            priority: 优先级

        Returns:
            Notification: 创建的通知
        """
        notification = Notification(
            notification_id=f"notif_user_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            type=NotificationType.USER_MENTION,
            title=title,
            message=message,
            team_id=team_id,
            user_id=user_id,
            priority=priority,
        )

        await self._store_notification(notification)
        await self._dispatch(notification)

        # 发送给特定用户
        await self.manager.send_to_user(
            user_id,
            {
                "type": "notification",
                "data": notification.to_dict(),
            },
        )

        return notification

    async def _store_notification(self, notification: Notification) -> None:
        """存储通知到历史记录"""
        key = notification.team_id or "system"
        if key not in self._notification_history:
            self._notification_history[key] = []
        self._notification_history[key].append(notification)

        # 只保留最近100条
        if len(self._notification_history[key]) > 100:
            self._notification_history[key] = self._notification_history[key][-100:]

    def get_team_notifications(
        self, team_id: str, unread_only: bool = False
    ) -> list[Notification]:
        """获取团队通知"""
        notifications = self._notification_history.get(team_id, [])
        if unread_only:
            return [n for n in notifications if not n.read]
        return notifications

    def get_user_notifications(
        self, user_id: str, team_id: str, unread_only: bool = False
    ) -> list[Notification]:
        """获取用户通知"""
        notifications = self._notification_history.get(team_id, [])
        user_notifs = [
            n for n in notifications if n.user_id == user_id or n.user_id is None
        ]
        if unread_only:
            return [n for n in user_notifs if not n.read]
        return user_notifs

    def mark_as_read(self, notification_id: str) -> bool:
        """标记通知为已读"""
        for notifications in self._notification_history.values():
            for notif in notifications:
                if notif.notification_id == notification_id:
                    notif.read = True
                    return True
        return False


# 全局实例
team_notifier = TeamNotifier()
