"""Tests for team/notification.py."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.team.notification import (
    ConnectionManager,
    Notification,
    NotificationPriority,
    NotificationType,
    TeamNotifier,
    team_notifier,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def notifier() -> TeamNotifier:
    """Create a fresh TeamNotifier instance."""
    return TeamNotifier()


@pytest.fixture
def manager() -> ConnectionManager:
    """Create a fresh ConnectionManager instance."""
    return ConnectionManager()


@pytest.fixture
def mock_websocket() -> AsyncMock:
    """Create a mock WebSocket with async methods."""
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    return websocket


@pytest.fixture
def sample_notification() -> Notification:
    """Create a sample notification."""
    return Notification(
        notification_id="notif_123",
        type=NotificationType.TASK_CREATED,
        title="Test Task",
        message="Test Message",
        team_id="team1",
        user_id="user1",
        task_id="task1",
        priority=NotificationPriority.NORMAL,
    )


# ---------------------------------------------------------------------------
# NotificationType Enum
# ---------------------------------------------------------------------------

class TestNotificationType:
    def test_notification_type_values(self) -> None:
        assert NotificationType.TASK_CREATED.value == "task_created"
        assert NotificationType.TASK_UPDATED.value == "task_updated"
        assert NotificationType.TASK_COMPLETED.value == "task_completed"
        assert NotificationType.TASK_FAILED.value == "task_failed"
        assert NotificationType.TEAM_BROADCAST.value == "team_broadcast"
        assert NotificationType.USER_MENTION.value == "user_mention"
        assert NotificationType.SYSTEM.value == "system"


# ---------------------------------------------------------------------------
# NotificationPriority Enum
# ---------------------------------------------------------------------------

class TestNotificationPriority:
    def test_notification_priority_values(self) -> None:
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"


# ---------------------------------------------------------------------------
# Notification Dataclass
# ---------------------------------------------------------------------------

class TestNotification:
    def test_notification_creation(self) -> None:
        notif = Notification(
            notification_id="notif_123",
            type=NotificationType.TASK_CREATED,
            title="New Task",
            message="Task created",
            team_id="team1",
            user_id="user1",
            task_id="task1",
        )
        assert notif.notification_id == "notif_123"
        assert notif.type == NotificationType.TASK_CREATED
        assert notif.title == "New Task"
        assert notif.team_id == "team1"
        assert notif.user_id == "user1"
        assert notif.task_id == "task1"
        assert notif.priority == NotificationPriority.NORMAL
        assert notif.read is False
        assert isinstance(notif.created_at, datetime)

    def test_notification_to_dict(self, sample_notification: Notification) -> None:
        result = sample_notification.to_dict()
        assert result["notification_id"] == "notif_123"
        assert result["type"] == "task_created"
        assert result["title"] == "Test Task"
        assert result["message"] == "Test Message"
        assert result["team_id"] == "team1"
        assert result["user_id"] == "user1"
        assert result["task_id"] == "task1"
        assert result["priority"] == "normal"
        assert result["read"] is False
        assert "created_at" in result
        assert isinstance(result["created_at"], str)

    def test_notification_to_dict_with_data(self) -> None:
        notif = Notification(
            notification_id="notif_456",
            type=NotificationType.SYSTEM,
            title="System Alert",
            message="Alert",
            data={"key": "value", "count": 42},
        )
        result = notif.to_dict()
        assert result["data"] == {"key": "value", "count": 42}

    def test_notification_default_values(self) -> None:
        notif = Notification(
            notification_id="notif_789",
            type=NotificationType.TEAM_BROADCAST,
            title="Broadcast",
            message="Message",
        )
        assert notif.team_id is None
        assert notif.user_id is None
        assert notif.task_id is None
        assert notif.priority == NotificationPriority.NORMAL
        assert notif.data == {}
        assert notif.read is False


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------

class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_success(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        await manager.connect(mock_websocket, "user1", "team1")
        mock_websocket.accept.assert_called_once()
        assert "team1:user1" in manager._connections
        assert mock_websocket in manager._connections["team1:user1"]
        assert manager._user_connections["user1"] is mock_websocket

    @pytest.mark.asyncio
    async def test_connect_multiple_connections_same_user(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        second_ws = AsyncMock()
        second_ws.accept = AsyncMock()
        second_ws.send_json = AsyncMock()

        await manager.connect(mock_websocket, "user1", "team1")
        await manager.connect(second_ws, "user1", "team1")

        assert len(manager._connections["team1:user1"]) == 2
        # _user_connections should point to the latest connection
        assert manager._user_connections["user1"] is second_ws

    def test_disconnect_success(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        # Setup: manually add connection
        manager._connections["team1:user1"] = [mock_websocket]
        manager._user_connections["user1"] = mock_websocket

        manager.disconnect(mock_websocket, "user1", "team1")

        assert "team1:user1" not in manager._connections
        assert "user1" not in manager._user_connections

    def test_disconnect_with_multiple_connections(
        self, manager: ConnectionManager
    ) -> None:
        ws1 = MagicMock()
        ws2 = MagicMock()

        manager._connections["team1:user1"] = [ws1, ws2]
        manager._user_connections["user1"] = ws2

        manager.disconnect(ws1, "user1", "team1")

        assert len(manager._connections["team1:user1"]) == 1
        assert ws2 in manager._connections["team1:user1"]
        # Note: disconnect always removes from _user_connections
        # This may be a bug in the original code
        assert "user1" not in manager._user_connections

    def test_disconnect_removes_empty_list(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        manager._connections["team1:user1"] = [mock_websocket]
        manager._user_connections["user1"] = mock_websocket

        manager.disconnect(mock_websocket, "user1", "team1")

        assert "team1:user1" not in manager._connections

    def test_disconnect_websocket_not_in_list(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        ws_other = MagicMock()
        manager._connections["team1:user1"] = [ws_other]

        # Should not raise
        manager.disconnect(mock_websocket, "user1", "team1")

        assert len(manager._connections["team1:user1"]) == 1

    @pytest.mark.asyncio
    async def test_send_to_user_success(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        manager._user_connections["user1"] = mock_websocket

        message = {"type": "test", "data": "hello"}
        result = await manager.send_to_user("user1", message)

        assert result is True
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_user_not_connected(self, manager: ConnectionManager) -> None:
        message = {"type": "test", "data": "hello"}
        result = await manager.send_to_user("user1", message)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_user_exception(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        manager._user_connections["user1"] = mock_websocket
        mock_websocket.send_json.side_effect = Exception("Connection lost")

        message = {"type": "test", "data": "hello"}
        result = await manager.send_to_user("user1", message)

        assert result is False
        # Should remove the broken connection
        assert "user1" not in manager._user_connections

    @pytest.mark.asyncio
    async def test_broadcast_to_team_success(
        self, manager: ConnectionManager
    ) -> None:
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        # Users in team1
        manager._connections["team1:user1"] = [ws1]
        manager._connections["team1:user2"] = [ws2]
        # User in different team
        manager._connections["team2:user3"] = [ws3]

        message = {"type": "broadcast", "data": "hello"}
        count = await manager.broadcast_to_team("team1", message)

        assert count == 2
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)
        ws3.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_to_team_with_multiple_connections(
        self, manager: ConnectionManager
    ) -> None:
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        manager._connections["team1:user1"] = [ws1, ws2]

        message = {"type": "broadcast", "data": "hello"}
        count = await manager.broadcast_to_team("team1", message)

        assert count == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_team_empty(
        self, manager: ConnectionManager
    ) -> None:
        message = {"type": "broadcast", "data": "hello"}
        count = await manager.broadcast_to_team("team1", message)

        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_team_with_exception(
        self, manager: ConnectionManager
    ) -> None:
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json.side_effect = Exception("Connection lost")

        manager._connections["team1:user1"] = [ws1]
        manager._connections["team1:user2"] = [ws2]

        message = {"type": "broadcast", "data": "hello"}
        count = await manager.broadcast_to_team("team1", message)

        # Only successful attempts are counted
        assert count == 1
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)


# ---------------------------------------------------------------------------
# TeamNotifier - Register Handler
# ---------------------------------------------------------------------------

class TestRegisterHandler:
    def test_register_handler_success(self, notifier: TeamNotifier) -> None:
        handler = MagicMock()
        notifier.register_handler(NotificationType.TASK_CREATED, handler)

        assert NotificationType.TASK_CREATED in notifier._handlers
        assert handler in notifier._handlers[NotificationType.TASK_CREATED]

    def test_register_multiple_handlers(self, notifier: TeamNotifier) -> None:
        handler1 = MagicMock()
        handler2 = MagicMock()

        notifier.register_handler(NotificationType.TASK_CREATED, handler1)
        notifier.register_handler(NotificationType.TASK_CREATED, handler2)

        assert len(notifier._handlers[NotificationType.TASK_CREATED]) == 2

    def test_register_different_types(self, notifier: TeamNotifier) -> None:
        handler1 = MagicMock()
        handler2 = MagicMock()

        notifier.register_handler(NotificationType.TASK_CREATED, handler1)
        notifier.register_handler(NotificationType.TASK_COMPLETED, handler2)

        assert len(notifier._handlers[NotificationType.TASK_CREATED]) == 1
        assert len(notifier._handlers[NotificationType.TASK_COMPLETED]) == 1


# ---------------------------------------------------------------------------
# TeamNotifier - Dispatch
# ---------------------------------------------------------------------------

class TestDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_sync_handler(self, notifier: TeamNotifier) -> None:
        handler = MagicMock()
        notifier.register_handler(NotificationType.TASK_CREATED, handler)

        notification = Notification(
            notification_id="test",
            type=NotificationType.TASK_CREATED,
            title="Test",
            message="Test",
        )

        await notifier._dispatch(notification)
        handler.assert_called_once_with(notification)

    @pytest.mark.asyncio
    async def test_dispatch_async_handler(self, notifier: TeamNotifier) -> None:
        handler = AsyncMock()
        notifier.register_handler(NotificationType.TASK_CREATED, handler)

        notification = Notification(
            notification_id="test",
            type=NotificationType.TASK_CREATED,
            title="Test",
            message="Test",
        )

        await notifier._dispatch(notification)
        handler.assert_called_once_with(notification)

    @pytest.mark.asyncio
    async def test_dispatch_handler_exception(self, notifier: TeamNotifier) -> None:
        handler = MagicMock(side_effect=Exception("Handler failed"))
        notifier.register_handler(NotificationType.TASK_CREATED, handler)

        notification = Notification(
            notification_id="test",
            type=NotificationType.TASK_CREATED,
            title="Test",
            message="Test",
        )

        # Should not raise
        await notifier._dispatch(notification)

    @pytest.mark.asyncio
    async def test_dispatch_no_handlers(self, notifier: TeamNotifier) -> None:
        notification = Notification(
            notification_id="test",
            type=NotificationType.TASK_CREATED,
            title="Test",
            message="Test",
        )

        # Should not raise
        await notifier._dispatch(notification)


# ---------------------------------------------------------------------------
# TeamNotifier - Notify Task Created
# ---------------------------------------------------------------------------

class TestNotifyTaskCreated:
    @pytest.mark.asyncio
    async def test_notify_task_created_success(
        self, notifier: TeamNotifier, mock_websocket: AsyncMock
    ) -> None:
        notifier.manager._user_connections["user1"] = mock_websocket

        result = await notifier.notify_task_created(
            task_id="task1",
            team_id="team1",
            creator_id="user1",
            title="New Task",
        )

        assert isinstance(result, Notification)
        assert result.type == NotificationType.TASK_CREATED
        assert result.title == "新任务已创建"
        assert result.message == "任务「New Task」已创建"
        assert result.team_id == "team1"
        assert result.user_id == "user1"
        assert result.task_id == "task1"
        assert result.data == {"title": "New Task"}

    @pytest.mark.asyncio
    async def test_notify_task_created_stores_notification(
        self, notifier: TeamNotifier
    ) -> None:
        await notifier.notify_task_created(
            task_id="task1",
            team_id="team1",
            creator_id="user1",
            title="New Task",
        )

        notifications = notifier.get_team_notifications("team1")
        assert len(notifications) == 1
        assert notifications[0].type == NotificationType.TASK_CREATED

    @pytest.mark.asyncio
    async def test_notify_task_created_broadcasts(
        self, notifier: TeamNotifier
    ) -> None:
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        notifier.manager._connections["team1:user1"] = [ws1]
        notifier.manager._connections["team1:user2"] = [ws2]

        await notifier.notify_task_created(
            task_id="task1",
            team_id="team1",
            creator_id="user1",
            title="New Task",
        )

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_task_created_with_handler(
        self, notifier: TeamNotifier
    ) -> None:
        handler = MagicMock()
        notifier.register_handler(NotificationType.TASK_CREATED, handler)

        await notifier.notify_task_created(
            task_id="task1",
            team_id="team1",
            creator_id="user1",
            title="New Task",
        )

        assert handler.call_count == 1


# ---------------------------------------------------------------------------
# TeamNotifier - Notify Task Completed
# ---------------------------------------------------------------------------

class TestNotifyTaskCompleted:
    @pytest.mark.asyncio
    async def test_notify_task_completed_success(self, notifier: TeamNotifier) -> None:
        result = await notifier.notify_task_completed(
            task_id="task1",
            team_id="team1",
            title="Completed Task",
            result={"output": "success"},
        )

        assert isinstance(result, Notification)
        assert result.type == NotificationType.TASK_COMPLETED
        assert result.title == "任务执行完成"
        assert result.message == "任务「Completed Task」已成功完成"
        assert result.priority == NotificationPriority.NORMAL
        assert result.data == {"result": {"output": "success"}}

    @pytest.mark.asyncio
    async def test_notify_task_completed_broadcasts(
        self, notifier: TeamNotifier
    ) -> None:
        ws1 = AsyncMock()
        notifier.manager._connections["team1:user1"] = [ws1]

        await notifier.notify_task_completed(
            task_id="task1",
            team_id="team1",
            title="Completed Task",
            result={"output": "success"},
        )

        ws1.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_task_completed_no_user_id(
        self, notifier: TeamNotifier
    ) -> None:
        result = await notifier.notify_task_completed(
            task_id="task1",
            team_id="team1",
            title="Completed Task",
            result={},
        )

        assert result.user_id is None


# ---------------------------------------------------------------------------
# TeamNotifier - Notify Task Failed
# ---------------------------------------------------------------------------

class TestNotifyTaskFailed:
    @pytest.mark.asyncio
    async def test_notify_task_failed_success(self, notifier: TeamNotifier) -> None:
        result = await notifier.notify_task_failed(
            task_id="task1",
            team_id="team1",
            title="Failed Task",
            error="Something went wrong",
        )

        assert isinstance(result, Notification)
        assert result.type == NotificationType.TASK_FAILED
        assert result.title == "任务执行失败"
        assert result.message == "任务「Failed Task」执行失败: Something went wrong"
        assert result.priority == NotificationPriority.HIGH
        assert result.data == {"error": "Something went wrong"}

    @pytest.mark.asyncio
    async def test_notify_task_failed_high_priority(self, notifier: TeamNotifier) -> None:
        result = await notifier.notify_task_failed(
            task_id="task1",
            team_id="team1",
            title="Failed Task",
            error="Error",
        )

        assert result.priority == NotificationPriority.HIGH


# ---------------------------------------------------------------------------
# TeamNotifier - Broadcast
# ---------------------------------------------------------------------------

class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_success(self, notifier: TeamNotifier) -> None:
        result = await notifier.broadcast(
            team_id="team1",
            title="Important Update",
            message="Please read this",
            priority=NotificationPriority.HIGH,
        )

        assert isinstance(result, Notification)
        assert result.type == NotificationType.TEAM_BROADCAST
        assert result.title == "Important Update"
        assert result.message == "Please read this"
        assert result.priority == NotificationPriority.HIGH
        assert result.team_id == "team1"
        assert "delivered_to" in result.data

    @pytest.mark.asyncio
    async def test_broadcast_default_priority(self, notifier: TeamNotifier) -> None:
        result = await notifier.broadcast(
            team_id="team1",
            title="Update",
            message="Message",
        )

        assert result.priority == NotificationPriority.NORMAL

    @pytest.mark.asyncio
    async def test_broadcast_stores_notification(self, notifier: TeamNotifier) -> None:
        await notifier.broadcast(
            team_id="team1",
            title="Update",
            message="Message",
        )

        notifications = notifier.get_team_notifications("team1")
        assert len(notifications) == 1
        assert notifications[0].type == NotificationType.TEAM_BROADCAST

    @pytest.mark.asyncio
    async def test_broadcast_counts_delivered(
        self, notifier: TeamNotifier
    ) -> None:
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        notifier.manager._connections["team1:user1"] = [ws1]
        notifier.manager._connections["team1:user2"] = [ws2]

        result = await notifier.broadcast(
            team_id="team1",
            title="Update",
            message="Message",
        )

        assert result.data["delivered_to"] == 2


# ---------------------------------------------------------------------------
# TeamNotifier - Notify User
# ---------------------------------------------------------------------------

class TestNotifyUser:
    @pytest.mark.asyncio
    async def test_notify_user_success(self, notifier: TeamNotifier) -> None:
        result = await notifier.notify_user(
            user_id="user1",
            team_id="team1",
            title="Personal Notification",
            message="Hello user1",
            priority=NotificationPriority.URGENT,
        )

        assert isinstance(result, Notification)
        assert result.type == NotificationType.USER_MENTION
        assert result.title == "Personal Notification"
        assert result.message == "Hello user1"
        assert result.user_id == "user1"
        assert result.team_id == "team1"
        assert result.priority == NotificationPriority.URGENT

    @pytest.mark.asyncio
    async def test_notify_user_sends_to_user(
        self, notifier: TeamNotifier, mock_websocket: AsyncMock
    ) -> None:
        notifier.manager._user_connections["user1"] = mock_websocket

        await notifier.notify_user(
            user_id="user1",
            team_id="team1",
            title="Test",
            message="Test",
        )

        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_user_not_connected(
        self, notifier: TeamNotifier
    ) -> None:
        # Should not raise
        result = await notifier.notify_user(
            user_id="user1",
            team_id="team1",
            title="Test",
            message="Test",
        )

        assert isinstance(result, Notification)


# ---------------------------------------------------------------------------
# TeamNotifier - Store Notification
# ---------------------------------------------------------------------------

class TestStoreNotification:
    @pytest.mark.asyncio
    async def test_store_notification_new_team(self, notifier: TeamNotifier) -> None:
        notification = Notification(
            notification_id="test",
            type=NotificationType.SYSTEM,
            title="Test",
            message="Test",
            team_id="new_team",
        )

        await notifier._store_notification(notification)

        assert "new_team" in notifier._notification_history
        assert len(notifier._notification_history["new_team"]) == 1

    @pytest.mark.asyncio
    async def test_store_notification_system_no_team(self, notifier: TeamNotifier) -> None:
        notification = Notification(
            notification_id="test",
            type=NotificationType.SYSTEM,
            title="System",
            message="System message",
            team_id=None,
        )

        await notifier._store_notification(notification)

        assert "system" in notifier._notification_history

    @pytest.mark.asyncio
    async def test_store_notification_limits_history(self, notifier: TeamNotifier) -> None:
        # Add 101 notifications
        for i in range(101):
            notification = Notification(
                notification_id=f"notif_{i}",
                type=NotificationType.SYSTEM,
                title="Test",
                message="Test",
                team_id="team1",
            )
            await notifier._store_notification(notification)

        # Should only keep last 100
        assert len(notifier._notification_history["team1"]) == 100
        # First one should be notif_1 (notif_0 was pushed out)
        assert notifier._notification_history["team1"][0].notification_id == "notif_1"
        assert notifier._notification_history["team1"][-1].notification_id == "notif_100"


# ---------------------------------------------------------------------------
# TeamNotifier - Get Team Notifications
# ---------------------------------------------------------------------------

class TestGetTeamNotifications:
    @pytest.mark.asyncio
    async def test_get_team_notifications_all(self, notifier: TeamNotifier) -> None:
        await notifier.notify_task_created("task1", "team1", "user1", "Task 1")
        await notifier.notify_task_completed("task1", "team1", "Task 1", {})

        notifications = notifier.get_team_notifications("team1")
        assert len(notifications) == 2

    @pytest.mark.asyncio
    async def test_get_team_notifications_unread_only(self, notifier: TeamNotifier) -> None:
        await notifier.notify_task_created("task1", "team1", "user1", "Task 1")
        await notifier.notify_task_completed("task1", "team1", "Task 1", {})

        # Mark one as read
        notifs = notifier.get_team_notifications("team1")
        notifs[0].read = True

        unread = notifier.get_team_notifications("team1", unread_only=True)
        assert len(unread) == 1

    @pytest.mark.asyncio
    async def test_get_team_notifications_empty_team(self, notifier: TeamNotifier) -> None:
        notifications = notifier.get_team_notifications("nonexistent")
        assert notifications == []

    @pytest.mark.asyncio
    async def test_get_team_notifications_after_mark_read(
        self, notifier: TeamNotifier
    ) -> None:
        await notifier.notify_task_created("task1", "team1", "user1", "Task 1")

        notification = notifier.get_team_notifications("team1")[0]
        notifier.mark_as_read(notification.notification_id)

        unread = notifier.get_team_notifications("team1", unread_only=True)
        assert len(unread) == 0


# ---------------------------------------------------------------------------
# TeamNotifier - Get User Notifications
# ---------------------------------------------------------------------------

class TestGetUserNotifications:
    @pytest.mark.asyncio
    async def test_get_user_notifications_all(self, notifier: TeamNotifier) -> None:
        await notifier.notify_task_created("task1", "team1", "user1", "Task 1")
        await notifier.notify_user("user1", "team1", "Mention", "Hello")

        notifications = notifier.get_user_notifications("user1", "team1")
        assert len(notifications) == 2

    @pytest.mark.asyncio
    async def test_get_user_notifications_unread_only(self, notifier: TeamNotifier) -> None:
        await notifier.notify_user("user1", "team1", "Mention 1", "Hello")
        await notifier.notify_user("user1", "team1", "Mention 2", "World")

        notifications = notifier.get_user_notifications("user1", "team1", unread_only=True)
        assert len(notifications) == 2

    @pytest.mark.asyncio
    async def test_get_user_notifications_filters_by_user(
        self, notifier: TeamNotifier
    ) -> None:
        await notifier.notify_user("user1", "team1", "For user1", "Hello")
        await notifier.notify_user("user2", "team1", "For user2", "World")

        user1_notifs = notifier.get_user_notifications("user1", "team1")
        assert len(user1_notifs) == 1
        assert user1_notifs[0].user_id == "user1"

    @pytest.mark.asyncio
    async def test_get_user_notifications_includes_none_user_id(
        self, notifier: TeamNotifier
    ) -> None:
        # Broadcast has no specific user_id
        await notifier.broadcast("team1", "Broadcast", "Everyone")

        notifications = notifier.get_user_notifications("user1", "team1")
        assert len(notifications) == 1

    @pytest.mark.asyncio
    async def test_get_user_notifications_empty(self, notifier: TeamNotifier) -> None:
        notifications = notifier.get_user_notifications("user1", "team1")
        assert notifications == []


# ---------------------------------------------------------------------------
# TeamNotifier - Mark As Read
# ---------------------------------------------------------------------------

class TestMarkAsRead:
    @pytest.mark.asyncio
    async def test_mark_as_read_success(self, notifier: TeamNotifier) -> None:
        await notifier.notify_task_created("task1", "team1", "user1", "Task 1")

        notification = notifier.get_team_notifications("team1")[0]
        result = notifier.mark_as_read(notification.notification_id)

        assert result is True
        assert notification.read is True

    def test_mark_as_read_not_found(self, notifier: TeamNotifier) -> None:
        result = notifier.mark_as_read("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_mark_as_read_marks_correct_notification(
        self, notifier: TeamNotifier
    ) -> None:
        await notifier.notify_task_created("task1", "team1", "user1", "Task 1")
        await notifier.notify_task_completed("task1", "team1", "Task 1", {})

        notifications = notifier.get_team_notifications("team1")
        first_id = notifications[0].notification_id

        notifier.mark_as_read(first_id)

        assert notifications[0].read is True
        assert notifications[1].read is False


# ---------------------------------------------------------------------------
# Global Instance
# ---------------------------------------------------------------------------

class TestGlobalInstance:
    def test_team_notifier_global_instance(self) -> None:
        assert isinstance(team_notifier, TeamNotifier)
