"""
Tests for src/web/team_api.py

Tests team management, task sync, statistics, and notification API routes.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the router and models
from src.web.team_api import (
    BroadcastRequest,
    CreateTaskRequest,
    CreateTeamRequest,
    JoinTeamRequest,
    RecordUsageRequest,
    UpdateTaskRequest,
    router,
)


# ========================================
# Fixtures
# ========================================
@pytest.fixture
def app():
    """Create test FastAPI app"""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_team():
    """Create a mock team object"""
    team = MagicMock()
    team.to_dict.return_value = {
        "team_id": "team_123",
        "name": "Test Team",
        "owner_id": "user_001",
        "description": "Test Description",
        "invite_code": "INVITE123",
        "members": ["user_001"],
    }
    return team


@pytest.fixture
def mock_task():
    """Create a mock task object"""
    task = MagicMock()
    task.task_id = "task_abc123"
    task.team_id = "team_123"
    task.creator_id = "user_001"
    task.title = "Test Task"
    task.to_dict.return_value = {
        "task_id": "task_abc123",
        "team_id": "team_123",
        "creator_id": "user_001",
        "title": "Test Task",
        "status": "pending",
        "workflow": "build",
        "model": "deepseek",
    }
    return task


@pytest.fixture
def mock_notification():
    """Create a mock notification object"""
    notification = MagicMock()
    notification.to_dict.return_value = {
        "notification_id": "notif_001",
        "team_id": "team_123",
        "title": "Test Notification",
        "message": "Test message",
        "priority": "normal",
        "read": False,
    }
    return notification


@pytest.fixture
def mock_stats():
    """Create a mock stats object"""
    stats = MagicMock()
    stats.to_dict.return_value = {
        "total_tasks": 10,
        "completed_tasks": 5,
        "failed_tasks": 2,
        "total_tokens": 10000,
        "total_cost": 5.50,
    }
    return stats


@pytest.fixture
def mock_usage_record():
    """Create a mock usage record"""
    record = MagicMock()
    record.to_dict.return_value = {
        "record_id": "usage_abc123",
        "team_id": "team_123",
        "user_id": "user_001",
        "task_id": "task_abc123",
        "tokens_used": 1000,
        "cost": 0.5,
    }
    return record


# ========================================
# Request Model Tests
# ========================================
class TestRequestModels:
    """Test Pydantic request models"""

    def test_create_team_request_basic(self):
        """Test CreateTeamRequest with basic fields"""
        request = CreateTeamRequest(name="My Team", owner_id="user_001")
        assert request.name == "My Team"
        assert request.owner_id == "user_001"
        assert request.description == ""

    def test_create_team_request_full(self):
        """Test CreateTeamRequest with all fields"""
        request = CreateTeamRequest(
            name="My Team", owner_id="user_001", description="A test team"
        )
        assert request.name == "My Team"
        assert request.description == "A test team"

    def test_join_team_request_basic(self):
        """Test JoinTeamRequest with basic fields"""
        request = JoinTeamRequest(invite_code="INV123", user_id="user_001")
        assert request.invite_code == "INV123"
        assert request.user_id == "user_001"
        assert request.display_name == ""
        assert request.email == ""

    def test_join_team_request_full(self):
        """Test JoinTeamRequest with all fields"""
        request = JoinTeamRequest(
            invite_code="INV123",
            user_id="user_001",
            display_name="Test User",
            email="test@example.com",
        )
        assert request.display_name == "Test User"
        assert request.email == "test@example.com"

    def test_create_task_request_basic(self):
        """Test CreateTaskRequest with basic fields"""
        request = CreateTaskRequest(
            team_id="team_123", creator_id="user_001", title="My Task"
        )
        assert request.team_id == "team_123"
        assert request.creator_id == "user_001"
        assert request.title == "My Task"
        assert request.description == ""
        assert request.workflow == "build"
        assert request.model == "deepseek"

    def test_create_task_request_full(self):
        """Test CreateTaskRequest with all fields"""
        request = CreateTaskRequest(
            team_id="team_123",
            creator_id="user_001",
            title="My Task",
            description="Task description",
            workflow="chat",
            model="qwen",
        )
        assert request.description == "Task description"
        assert request.workflow == "chat"
        assert request.model == "qwen"

    def test_update_task_request_basic(self):
        """Test UpdateTaskRequest with basic fields"""
        request = UpdateTaskRequest(status="completed")
        assert request.status == "completed"
        assert request.result is None
        assert request.error is None
        assert request.tokens_used == 0
        assert request.cost == 0.0

    def test_update_task_request_full(self):
        """Test UpdateTaskRequest with all fields"""
        request = UpdateTaskRequest(
            status="completed",
            result={"output": "success"},
            error=None,
            tokens_used=500,
            cost=0.25,
        )
        assert request.result == {"output": "success"}
        assert request.tokens_used == 500
        assert request.cost == 0.25

    def test_record_usage_request_basic(self):
        """Test RecordUsageRequest with basic fields"""
        request = RecordUsageRequest(
            team_id="team_123",
            user_id="user_001",
            task_id="task_001",
            task_type="build",
            model="deepseek",
            tokens_used=1000,
            cost=0.5,
            execution_time=10.5,
        )
        assert request.team_id == "team_123"
        assert request.status == "success"

    def test_record_usage_request_full(self):
        """Test RecordUsageRequest with all fields"""
        request = RecordUsageRequest(
            team_id="team_123",
            user_id="user_001",
            task_id="task_001",
            task_type="build",
            model="deepseek",
            tokens_used=1000,
            cost=0.5,
            execution_time=10.5,
            status="failed",
        )
        assert request.status == "failed"

    def test_broadcast_request_basic(self):
        """Test BroadcastRequest with basic fields"""
        request = BroadcastRequest(
            team_id="team_123", title="Alert", message="Test message"
        )
        assert request.team_id == "team_123"
        assert request.title == "Alert"
        assert request.message == "Test message"
        assert request.priority == "normal"

    def test_broadcast_request_full(self):
        """Test BroadcastRequest with all fields"""
        request = BroadcastRequest(
            team_id="team_123",
            title="Alert",
            message="Test message",
            priority="high",
        )
        assert request.priority == "high"


# ========================================
# Team Management API Tests
# ========================================
class TestCreateTeam:
    """Test POST /api/team/create"""

    @patch("src.web.team_api.team_auth")
    def test_create_team_success(self, mock_auth, client, mock_team):
        """Test successful team creation"""
        mock_auth.create_team = AsyncMock(return_value=mock_team)

        response = client.post(
            "/api/team/create",
            json={"name": "Test Team", "owner_id": "user_001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == "team_123"
        assert data["name"] == "Test Team"

    @patch("src.web.team_api.team_auth")
    def test_create_team_with_description(self, mock_auth, client, mock_team):
        """Test team creation with description"""
        mock_auth.create_team = AsyncMock(return_value=mock_team)

        response = client.post(
            "/api/team/create",
            json={
                "name": "Test Team",
                "owner_id": "user_001",
                "description": "A test team",
            },
        )
        assert response.status_code == 200

    def test_create_team_missing_name(self, client):
        """Test team creation without name"""
        response = client.post(
            "/api/team/create",
            json={"owner_id": "user_001"},
        )
        assert response.status_code == 422

    def test_create_team_missing_owner(self, client):
        """Test team creation without owner_id"""
        response = client.post(
            "/api/team/create",
            json={"name": "Test Team"},
        )
        assert response.status_code == 422

    @patch("src.web.team_api.team_auth")
    def test_create_team_exception(self, mock_auth, client):
        """Test team creation with exception"""
        mock_auth.create_team = AsyncMock(side_effect=Exception("DB error"))

        # With raise_server_exceptions=False, FastAPI returns 500 for unhandled exceptions
        test_app = FastAPI()
        test_app.include_router(router)
        test_client = TestClient(test_app, raise_server_exceptions=False)

        response = test_client.post(
            "/api/team/create",
            json={"name": "Test Team", "owner_id": "user_001"},
        )
        assert response.status_code == 500


class TestJoinTeam:
    """Test POST /api/team/join"""

    @patch("src.web.team_api.team_auth")
    def test_join_team_success(self, mock_auth, client, mock_team):
        """Test successful team join"""
        mock_auth.join_team = AsyncMock(return_value=mock_team)

        response = client.post(
            "/api/team/join",
            json={"invite_code": "INVITE123", "user_id": "user_001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == "team_123"

    @patch("src.web.team_api.team_auth")
    def test_join_team_invalid_code(self, mock_auth, client):
        """Test join with invalid invite code"""
        mock_auth.join_team = AsyncMock(return_value=None)

        response = client.post(
            "/api/team/join",
            json={"invite_code": "INVALID", "user_id": "user_001"},
        )
        assert response.status_code == 404
        assert "无效的邀请码" in response.json()["detail"]

    @patch("src.web.team_api.team_auth")
    def test_join_team_with_display_name(self, mock_auth, client, mock_team):
        """Test join with display name"""
        mock_auth.join_team = AsyncMock(return_value=mock_team)

        response = client.post(
            "/api/team/join",
            json={
                "invite_code": "INVITE123",
                "user_id": "user_001",
                "display_name": "Test User",
            },
        )
        assert response.status_code == 200

    def test_join_team_missing_code(self, client):
        """Test join without invite code"""
        response = client.post(
            "/api/team/join",
            json={"user_id": "user_001"},
        )
        assert response.status_code == 422

    def test_join_team_missing_user(self, client):
        """Test join without user_id"""
        response = client.post(
            "/api/team/join",
            json={"invite_code": "INVITE123"},
        )
        assert response.status_code == 422


class TestLeaveTeam:
    """Test POST /api/team/leave"""

    @patch("src.web.team_api.team_auth")
    def test_leave_team_success(self, mock_auth, client):
        """Test successful leave"""
        mock_auth.leave_team = AsyncMock(return_value=True)

        response = client.post(
            "/api/team/leave?user_id=user_001&team_id=team_123"
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("src.web.team_api.team_auth")
    def test_leave_team_failed(self, mock_auth, client):
        """Test failed leave"""
        mock_auth.leave_team = AsyncMock(return_value=False)

        response = client.post(
            "/api/team/leave?user_id=user_001&team_id=team_123"
        )
        assert response.status_code == 400
        assert "无法离开团队" in response.json()["detail"]

    def test_leave_team_missing_params(self, client):
        """Test leave without parameters"""
        response = client.post("/api/team/leave")
        assert response.status_code == 422


class TestDeleteTeam:
    """Test POST /api/team/delete"""

    @patch("src.web.team_api.team_auth")
    def test_delete_team_success(self, mock_auth, client):
        """Test successful deletion"""
        mock_auth.delete_team = AsyncMock(return_value=True)

        response = client.post(
            "/api/team/delete?team_id=team_123&requester_id=user_001"
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("src.web.team_api.team_auth")
    def test_delete_team_unauthorized(self, mock_auth, client):
        """Test deletion by non-owner"""
        mock_auth.delete_team = AsyncMock(return_value=False)

        response = client.post(
            "/api/team/delete?team_id=team_123&requester_id=user_002"
        )
        assert response.status_code == 403
        assert "无权删除团队" in response.json()["detail"]

    def test_delete_team_missing_params(self, client):
        """Test delete without parameters"""
        response = client.post("/api/team/delete")
        assert response.status_code == 422


class TestGetTeam:
    """Test GET /api/team/{team_id}"""

    @patch("src.web.team_api.team_auth")
    def test_get_team_success(self, mock_auth, client, mock_team):
        """Test successful get team"""
        mock_auth.get_team = AsyncMock(return_value=mock_team)

        response = client.get("/api/team/team_123")
        assert response.status_code == 200
        assert response.json()["team_id"] == "team_123"

    @patch("src.web.team_api.team_auth")
    def test_get_team_not_found(self, mock_auth, client):
        """Test get non-existent team"""
        mock_auth.get_team = AsyncMock(return_value=None)

        response = client.get("/api/team/nonexistent")
        assert response.status_code == 404
        assert "团队不存在" in response.json()["detail"]


class TestGetUserTeam:
    """Test GET /api/team/user/{user_id}"""

    @patch("src.web.team_api.team_auth")
    def test_get_user_team_success(self, mock_auth, client, mock_team):
        """Test get user's team"""
        mock_auth.get_user_team = AsyncMock(return_value=mock_team)

        response = client.get("/api/team/user/user_001")
        assert response.status_code == 200
        assert response.json()["team_id"] == "team_123"

    @patch("src.web.team_api.team_auth")
    def test_get_user_team_not_found(self, mock_auth, client):
        """Test get team for user not in any team"""
        mock_auth.get_user_team = AsyncMock(return_value=None)

        response = client.get("/api/team/user/user_999")
        assert response.status_code == 404
        assert "用户未加入任何团队" in response.json()["detail"]


class TestRegenerateInvite:
    """Test POST /api/team/{team_id}/regenerate-invite"""

    @patch("src.web.team_api.team_auth")
    def test_regenerate_invite_success(self, mock_auth, client):
        """Test successful invite regeneration"""
        mock_auth.regenerate_invite_code = AsyncMock(return_value="NEWINVITE123")

        response = client.post(
            "/api/team/team_123/regenerate-invite?requester_id=user_001"
        )
        assert response.status_code == 200
        assert response.json()["invite_code"] == "NEWINVITE123"

    @patch("src.web.team_api.team_auth")
    def test_regenerate_invite_unauthorized(self, mock_auth, client):
        """Test regeneration by non-owner"""
        mock_auth.regenerate_invite_code = AsyncMock(return_value=None)

        response = client.post(
            "/api/team/team_123/regenerate-invite?requester_id=user_002"
        )
        assert response.status_code == 403
        assert "无权生成邀请码" in response.json()["detail"]

    def test_regenerate_invite_missing_params(self, client):
        """Test regeneration without requester_id"""
        response = client.post("/api/team/team_123/regenerate-invite")
        assert response.status_code == 422


# ========================================
# Task Sync API Tests
# ========================================
class TestCreateTask:
    """Test POST /api/team/task/create"""

    @patch("src.web.team_api.team_notifier")
    @patch("src.web.team_api.task_sync")
    def test_create_task_success(self, mock_sync, mock_notifier, client, mock_task):
        """Test successful task creation"""
        mock_sync.create_task = AsyncMock(return_value=mock_task)
        mock_notifier.notify_task_created = AsyncMock()

        response = client.post(
            "/api/team/task/create",
            json={
                "team_id": "team_123",
                "creator_id": "user_001",
                "title": "Test Task",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task_abc123"
        mock_notifier.notify_task_created.assert_called_once()

    @patch("src.web.team_api.team_notifier")
    @patch("src.web.team_api.task_sync")
    def test_create_task_with_description(self, mock_sync, mock_notifier, client, mock_task):
        """Test task creation with description"""
        mock_sync.create_task = AsyncMock(return_value=mock_task)
        mock_notifier.notify_task_created = AsyncMock()

        response = client.post(
            "/api/team/task/create",
            json={
                "team_id": "team_123",
                "creator_id": "user_001",
                "title": "Test Task",
                "description": "Task description",
            },
        )
        assert response.status_code == 200

    @patch("src.web.team_api.team_notifier")
    @patch("src.web.team_api.task_sync")
    def test_create_task_custom_workflow(self, mock_sync, mock_notifier, client, mock_task):
        """Test task creation with custom workflow"""
        mock_sync.create_task = AsyncMock(return_value=mock_task)
        mock_notifier.notify_task_created = AsyncMock()

        response = client.post(
            "/api/team/task/create",
            json={
                "team_id": "team_123",
                "creator_id": "user_001",
                "title": "Test Task",
                "workflow": "chat",
                "model": "qwen",
            },
        )
        assert response.status_code == 200

    def test_create_task_missing_team_id(self, client):
        """Test task creation without team_id"""
        response = client.post(
            "/api/team/task/create",
            json={"creator_id": "user_001", "title": "Test"},
        )
        assert response.status_code == 422

    def test_create_task_missing_title(self, client):
        """Test task creation without title"""
        response = client.post(
            "/api/team/task/create",
            json={"team_id": "team_123", "creator_id": "user_001"},
        )
        assert response.status_code == 422


class TestUpdateTaskStatus:
    """Test PUT /api/team/task/{task_id}/status"""

    @patch("src.web.team_api.team_notifier")
    @patch("src.web.team_api.task_sync")
    @patch("src.web.team_api.TaskStatus")
    def test_update_task_completed(self, mock_status, mock_sync, mock_notifier, client, mock_task):
        """Test update to completed status"""
        mock_status.COMPLETED = "completed"
        mock_status.return_value = "completed"
        mock_sync.update_status = AsyncMock(return_value=mock_task)
        mock_notifier.notify_task_completed = AsyncMock()

        response = client.put(
            "/api/team/task/task_abc123/status",
            json={"status": "completed"},
        )
        assert response.status_code == 200
        mock_notifier.notify_task_completed.assert_called_once()

    @patch("src.web.team_api.team_notifier")
    @patch("src.web.team_api.task_sync")
    @patch("src.web.team_api.TaskStatus")
    def test_update_task_failed(self, mock_status, mock_sync, mock_notifier, client, mock_task):
        """Test update to failed status"""
        mock_status.FAILED = "failed"
        mock_status.return_value = "failed"
        mock_sync.update_status = AsyncMock(return_value=mock_task)
        mock_notifier.notify_task_failed = AsyncMock()

        response = client.put(
            "/api/team/task/task_abc123/status",
            json={"status": "failed", "error": "Test error"},
        )
        assert response.status_code == 200
        mock_notifier.notify_task_failed.assert_called_once()

    @patch("src.web.team_api.team_notifier")
    @patch("src.web.team_api.task_sync")
    @patch("src.web.team_api.TaskStatus")
    def test_update_task_not_found(self, mock_status, mock_sync, mock_notifier, client):
        """Test update non-existent task"""
        mock_status.return_value = "completed"
        mock_sync.update_status = AsyncMock(return_value=None)

        response = client.put(
            "/api/team/task/nonexistent/status",
            json={"status": "completed"},
        )
        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    def test_update_task_missing_status(self, client):
        """Test update without status"""
        response = client.put(
            "/api/team/task/task_abc123/status",
            json={},
        )
        assert response.status_code == 422


class TestGetTask:
    """Test GET /api/team/task/{task_id}"""

    @patch("src.web.team_api.task_sync")
    def test_get_task_success(self, mock_sync, client, mock_task):
        """Test get task success"""
        mock_sync.get_task = AsyncMock(return_value=mock_task)

        response = client.get("/api/team/task/task_abc123")
        assert response.status_code == 200
        assert response.json()["task_id"] == "task_abc123"

    @patch("src.web.team_api.task_sync")
    def test_get_task_not_found(self, mock_sync, client):
        """Test get non-existent task"""
        mock_sync.get_task = AsyncMock(return_value=None)

        response = client.get("/api/team/task/nonexistent")
        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]


class TestGetTeamTasks:
    """Test GET /api/team/{team_id}/tasks"""

    @patch("src.web.team_api.task_sync")
    def test_get_team_tasks_success(self, mock_sync, client, mock_task):
        """Test get team tasks"""
        mock_sync.get_team_tasks = AsyncMock(return_value=[mock_task])

        response = client.get("/api/team/team_123/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["task_id"] == "task_abc123"

    @patch("src.web.team_api.task_sync")
    def test_get_team_tasks_empty(self, mock_sync, client):
        """Test get empty task list"""
        mock_sync.get_team_tasks = AsyncMock(return_value=[])

        response = client.get("/api/team/team_123/tasks")
        assert response.status_code == 200
        assert response.json() == []

    @patch("src.web.team_api.task_sync")
    def test_get_team_tasks_multiple(self, mock_sync, client):
        """Test get multiple tasks"""
        task1 = MagicMock()
        task1.to_dict.return_value = {"task_id": "task_1", "title": "Task 1"}
        task2 = MagicMock()
        task2.to_dict.return_value = {"task_id": "task_2", "title": "Task 2"}
        mock_sync.get_team_tasks = AsyncMock(return_value=[task1, task2])

        response = client.get("/api/team/team_123/tasks")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestSubscribeTask:
    """Test POST /api/team/task/{task_id}/subscribe"""

    @patch("src.web.team_api.task_sync")
    def test_subscribe_task_success(self, mock_sync, client):
        """Test subscribe to task"""
        mock_sync.subscribe_task = AsyncMock(return_value=True)

        response = client.post(
            "/api/team/task/task_abc123/subscribe?user_id=user_001"
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("src.web.team_api.task_sync")
    def test_subscribe_task_not_found(self, mock_sync, client):
        """Test subscribe to non-existent task"""
        mock_sync.subscribe_task = AsyncMock(return_value=False)

        response = client.post(
            "/api/team/task/nonexistent/subscribe?user_id=user_001"
        )
        assert response.status_code == 404

    def test_subscribe_task_missing_user(self, client):
        """Test subscribe without user_id"""
        response = client.post("/api/team/task/task_abc123/subscribe")
        assert response.status_code == 422


class TestDeleteTask:
    """Test DELETE /api/team/task/{task_id}"""

    @patch("src.web.team_api.task_sync")
    def test_delete_task_success(self, mock_sync, client):
        """Test delete task success"""
        mock_sync.delete_task = AsyncMock(return_value=True)

        response = client.delete("/api/team/task/task_abc123")
        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("src.web.team_api.task_sync")
    def test_delete_task_not_found(self, mock_sync, client):
        """Test delete non-existent task"""
        mock_sync.delete_task = AsyncMock(return_value=False)

        response = client.delete("/api/team/task/nonexistent")
        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]


# ========================================
# Statistics API Tests
# ========================================
class TestRecordUsage:
    """Test POST /api/team/usage/record"""

    @patch("src.web.team_api.team_statistics")
    def test_record_usage_success(self, mock_stats, client, mock_usage_record):
        """Test record usage success"""
        mock_stats.record_usage = MagicMock(return_value=mock_usage_record)

        response = client.post(
            "/api/team/usage/record",
            json={
                "team_id": "team_123",
                "user_id": "user_001",
                "task_id": "task_001",
                "task_type": "build",
                "model": "deepseek",
                "tokens_used": 1000,
                "cost": 0.5,
                "execution_time": 10.5,
            },
        )
        assert response.status_code == 200
        assert response.json()["record_id"] == "usage_abc123"

    @patch("src.web.team_api.team_statistics")
    def test_record_usage_failed_status(self, mock_stats, client, mock_usage_record):
        """Test record usage with failed status"""
        mock_stats.record_usage = MagicMock(return_value=mock_usage_record)

        response = client.post(
            "/api/team/usage/record",
            json={
                "team_id": "team_123",
                "user_id": "user_001",
                "task_id": "task_001",
                "task_type": "build",
                "model": "deepseek",
                "tokens_used": 1000,
                "cost": 0.5,
                "execution_time": 10.5,
                "status": "failed",
            },
        )
        assert response.status_code == 200

    def test_record_usage_missing_fields(self, client):
        """Test record usage without required fields"""
        response = client.post(
            "/api/team/usage/record",
            json={"team_id": "team_123"},
        )
        assert response.status_code == 422


class TestGetTeamStats:
    """Test GET /api/team/{team_id}/stats"""

    @patch("src.web.team_api.team_statistics")
    def test_get_team_stats_default_period(self, mock_stats, client, mock_stats_obj):
        """Test get team stats with default period"""
        mock_stats.get_team_stats = MagicMock(return_value=mock_stats_obj)

        response = client.get("/api/team/team_123/stats")
        assert response.status_code == 200
        mock_stats.get_team_stats.assert_called_with("team_123", "week")

    @patch("src.web.team_api.team_statistics")
    def test_get_team_stats_day_period(self, mock_stats, client, mock_stats_obj):
        """Test get team stats with day period"""
        mock_stats.get_team_stats = MagicMock(return_value=mock_stats_obj)

        response = client.get("/api/team/team_123/stats?period=day")
        assert response.status_code == 200
        mock_stats.get_team_stats.assert_called_with("team_123", "day")

    @patch("src.web.team_api.team_statistics")
    def test_get_team_stats_month_period(self, mock_stats, client, mock_stats_obj):
        """Test get team stats with month period"""
        mock_stats.get_team_stats = MagicMock(return_value=mock_stats_obj)

        response = client.get("/api/team/team_123/stats?period=month")
        assert response.status_code == 200

    def test_get_team_stats_invalid_period(self, client):
        """Test get team stats with invalid period"""
        response = client.get("/api/team/team_123/stats?period=year")
        assert response.status_code == 422


class TestGetUserStats:
    """Test GET /api/team/{team_id}/user/{user_id}/stats"""

    @patch("src.web.team_api.team_statistics")
    def test_get_user_stats_success(self, mock_stats, client, mock_stats_obj):
        """Test get user stats"""
        mock_stats.get_user_stats = MagicMock(return_value=mock_stats_obj)

        response = client.get("/api/team/team_123/user/user_001/stats")
        assert response.status_code == 200

    @patch("src.web.team_api.team_statistics")
    def test_get_user_stats_with_period(self, mock_stats, client, mock_stats_obj):
        """Test get user stats with specific period"""
        mock_stats.get_user_stats = MagicMock(return_value=mock_stats_obj)

        response = client.get("/api/team/team_123/user/user_001/stats?period=day")
        assert response.status_code == 200
        mock_stats.get_user_stats.assert_called_with("user_001", "team_123", "day")


# ========================================
# Notification API Tests
# ========================================
class TestBroadcastMessage:
    """Test POST /api/team/broadcast"""

    @patch("src.team.notification.NotificationPriority")
    @patch("src.web.team_api.team_notifier")
    def test_broadcast_success(self, mock_notifier, mock_priority, client, mock_notification):
        """Test broadcast message success"""
        mock_priority.return_value = "normal"
        mock_notifier.broadcast = AsyncMock(return_value=mock_notification)

        response = client.post(
            "/api/team/broadcast",
            json={
                "team_id": "team_123",
                "title": "Alert",
                "message": "Test message",
            },
        )
        assert response.status_code == 200
        assert response.json()["notification_id"] == "notif_001"

    @patch("src.team.notification.NotificationPriority")
    @patch("src.web.team_api.team_notifier")
    def test_broadcast_high_priority(self, mock_notifier, mock_priority, client, mock_notification):
        """Test broadcast with high priority"""
        mock_priority.return_value = "high"
        mock_notifier.broadcast = AsyncMock(return_value=mock_notification)

        response = client.post(
            "/api/team/broadcast",
            json={
                "team_id": "team_123",
                "title": "Urgent",
                "message": "Urgent message",
                "priority": "high",
            },
        )
        assert response.status_code == 200

    def test_broadcast_missing_fields(self, client):
        """Test broadcast without required fields"""
        response = client.post(
            "/api/team/broadcast",
            json={"team_id": "team_123"},
        )
        assert response.status_code == 422


class TestGetTeamNotifications:
    """Test GET /api/team/{team_id}/notifications"""

    @patch("src.web.team_api.team_notifier")
    def test_get_team_notifications_success(self, mock_notifier, client, mock_notification):
        """Test get team notifications"""
        mock_notifier.get_team_notifications = MagicMock(return_value=[mock_notification])

        response = client.get("/api/team/team_123/notifications")
        assert response.status_code == 200
        assert len(response.json()) == 1

    @patch("src.web.team_api.team_notifier")
    def test_get_team_notifications_unread_only(self, mock_notifier, client, mock_notification):
        """Test get only unread notifications"""
        mock_notifier.get_team_notifications = MagicMock(return_value=[mock_notification])

        response = client.get("/api/team/team_123/notifications?unread_only=true")
        assert response.status_code == 200
        mock_notifier.get_team_notifications.assert_called_with("team_123", True)

    @patch("src.web.team_api.team_notifier")
    def test_get_team_notifications_empty(self, mock_notifier, client):
        """Test get empty notification list"""
        mock_notifier.get_team_notifications = MagicMock(return_value=[])

        response = client.get("/api/team/team_123/notifications")
        assert response.status_code == 200
        assert response.json() == []


class TestGetUserNotifications:
    """Test GET /api/team/{team_id}/user/{user_id}/notifications"""

    @patch("src.web.team_api.team_notifier")
    def test_get_user_notifications_success(self, mock_notifier, client, mock_notification):
        """Test get user notifications"""
        mock_notifier.get_user_notifications = MagicMock(return_value=[mock_notification])

        response = client.get("/api/team/team_123/user/user_001/notifications")
        assert response.status_code == 200
        assert len(response.json()) == 1

    @patch("src.web.team_api.team_notifier")
    def test_get_user_notifications_unread_only(self, mock_notifier, client, mock_notification):
        """Test get only unread user notifications"""
        mock_notifier.get_user_notifications = MagicMock(return_value=[mock_notification])

        response = client.get(
            "/api/team/team_123/user/user_001/notifications?unread_only=true"
        )
        assert response.status_code == 200


class TestMarkNotificationRead:
    """Test POST /api/team/notification/{notification_id}/read"""

    @patch("src.web.team_api.team_notifier")
    def test_mark_notification_read_success(self, mock_notifier, client):
        """Test mark notification as read"""
        mock_notifier.mark_as_read = MagicMock(return_value=True)

        response = client.post("/api/team/notification/notif_001/read")
        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("src.web.team_api.team_notifier")
    def test_mark_notification_read_failed(self, mock_notifier, client):
        """Test mark notification as read failure"""
        mock_notifier.mark_as_read = MagicMock(return_value=False)

        response = client.post("/api/team/notification/notif_001/read")
        assert response.status_code == 200
        assert response.json()["success"] is False


# ========================================
# Edge Cases and Error Handling
# ========================================
class TestEdgeCases:
    """Test edge cases and error handling"""

    @patch("src.web.team_api.team_auth")
    def test_empty_team_name(self, mock_auth, client, mock_team):
        """Test team creation with empty name"""
        mock_auth.create_team = AsyncMock(return_value=mock_team)

        response = client.post(
            "/api/team/create",
            json={"name": "", "owner_id": "user_001"},
        )
        # FastAPI/Pydantic allows empty strings by default
        assert response.status_code in [200, 422]

    @patch("src.web.team_api.task_sync")
    def test_task_with_special_characters(self, mock_sync, client, mock_task):
        """Test task with special characters in title"""
        mock_sync.get_task = AsyncMock(return_value=mock_task)

        # Test with URL-encoded special characters
        response = client.get("/api/team/task/task_%40%23%24")
        # Should decode properly or return 404
        assert response.status_code in [200, 404]

    @patch("src.web.team_api.team_auth")
    def test_team_id_with_slash(self, mock_auth, client, mock_team):
        """Test team ID containing slash"""
        mock_auth.get_team = AsyncMock(return_value=None)

        # FastAPI should handle path parameters correctly
        response = client.get("/api/team/team%2F123")
        assert response.status_code in [200, 404]

    @patch("src.web.team_api.team_notifier")
    @patch("src.web.team_api.task_sync")
    def test_task_creation_with_long_title(self, mock_sync, mock_notifier, client, mock_task):
        """Test task creation with very long title"""
        mock_sync.create_task = AsyncMock(return_value=mock_task)
        mock_notifier.notify_task_created = AsyncMock()

        long_title = "A" * 1000
        response = client.post(
            "/api/team/task/create",
            json={
                "team_id": "team_123",
                "creator_id": "user_001",
                "title": long_title,
            },
        )
        assert response.status_code == 200

    @patch("src.web.team_api.team_statistics")
    def test_usage_record_large_values(self, mock_stats, client, mock_usage_record):
        """Test usage record with large token counts"""
        mock_stats.record_usage = MagicMock(return_value=mock_usage_record)

        response = client.post(
            "/api/team/usage/record",
            json={
                "team_id": "team_123",
                "user_id": "user_001",
                "task_id": "task_001",
                "task_type": "build",
                "model": "deepseek",
                "tokens_used": 10_000_000,
                "cost": 1000.0,
                "execution_time": 3600.0,
            },
        )
        assert response.status_code == 200


# ========================================
# Integration-style Tests
# ========================================
class TestIntegration:
    """Integration tests with multiple endpoints"""

    @patch("src.web.team_api.team_auth")
    def test_create_and_get_team(self, mock_auth, client, mock_team):
        """Test create and get team flow"""
        mock_auth.create_team = AsyncMock(return_value=mock_team)
        mock_auth.get_team = AsyncMock(return_value=mock_team)

        # Create team
        response = client.post(
            "/api/team/create",
            json={"name": "Test Team", "owner_id": "user_001"},
        )
        assert response.status_code == 200
        team_id = response.json()["team_id"]

        # Get team
        response = client.get(f"/api/team/{team_id}")
        assert response.status_code == 200

    @patch("src.web.team_api.team_notifier")
    @patch("src.web.team_api.task_sync")
    @patch("src.web.team_api.team_auth")
    def test_team_workflow(
        self, mock_auth, mock_sync, mock_notifier, client, mock_team, mock_task
    ):
        """Test complete team workflow"""
        mock_auth.create_team = AsyncMock(return_value=mock_task)
        mock_auth.join_team = AsyncMock(return_value=mock_team)
        mock_sync.create_task = AsyncMock(return_value=mock_task)
        mock_sync.get_team_tasks = AsyncMock(return_value=[mock_task])
        mock_notifier.notify_task_created = AsyncMock()

        # Create team
        response = client.post(
            "/api/team/create",
            json={"name": "Workflow Team", "owner_id": "user_001"},
        )
        assert response.status_code == 200

        # Create task
        response = client.post(
            "/api/team/task/create",
            json={
                "team_id": "team_123",
                "creator_id": "user_001",
                "title": "Workflow Task",
            },
        )
        assert response.status_code == 200

        # Get team tasks
        response = client.get("/api/team/team_123/tasks")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_all_routes_exist(self, client):
        """Test all routes are accessible"""
        routes = [
            ("POST", "/api/team/create"),
            ("POST", "/api/team/join"),
            ("POST", "/api/team/leave"),
            ("POST", "/api/team/delete"),
        ]
        for method, path in routes:
            if method == "POST":
                response = client.post(path, json={})
            else:
                response = client.get(path)
            # Should get validation error (422) not 404
            assert response.status_code != 404, f"Route {path} not found"


# ========================================
# Additional fixture for mock_stats_obj
# ========================================
@pytest.fixture
def mock_stats_obj():
    """Create a mock stats object for stats endpoints"""
    stats = MagicMock()
    stats.to_dict.return_value = {
        "total_tasks": 10,
        "completed_tasks": 5,
        "total_tokens": 10000,
        "total_cost": 5.50,
    }
    return stats
