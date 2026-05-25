"""Tests for team/task_sync.py."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.team.task_sync import (
    MemberRole,
    TaskStatus,
    TaskSync,
    TeamTask,
    task_sync,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sync() -> TaskSync:
    """Create a fresh TaskSync instance forced into memory mode.

    Redis is available in this environment, so we explicitly set _use_memory
    to True to test the in-memory code path.
    """
    s = TaskSync()
    s._use_memory = True
    return s


@pytest.fixture
def sample_task() -> TeamTask:
    """Create a sample TeamTask."""
    now = datetime.now()
    return TeamTask(
        task_id="task_001",
        team_id="team_001",
        creator_id="user_001",
        title="Test Task",
        description="A test task",
        status=TaskStatus.PENDING,
        created_at=now,
        updated_at=now,
        subscribers=["user_001"],
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestTaskStatus:
    def test_task_status_values(self) -> None:
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestMemberRole:
    def test_member_role_values(self) -> None:
        assert MemberRole.OWNER.value == "owner"
        assert MemberRole.ADMIN.value == "admin"
        assert MemberRole.MEMBER.value == "member"


# ---------------------------------------------------------------------------
# TeamTask - to_dict / from_dict
# ---------------------------------------------------------------------------

class TestTeamTaskToDict:
    def test_to_dict_basic(self, sample_task: TeamTask) -> None:
        result = sample_task.to_dict()
        assert result["task_id"] == "task_001"
        assert result["team_id"] == "team_001"
        assert result["creator_id"] == "user_001"
        assert result["title"] == "Test Task"
        assert result["description"] == "A test task"
        assert result["status"] == "pending"
        assert result["workflow"] == "build"
        assert result["model"] == "deepseek"
        assert "created_at" in result
        assert "updated_at" in result

    def test_to_dict_optional_fields(self, sample_task: TeamTask) -> None:
        sample_task.assignee_id = "user_002"
        sample_task.started_at = datetime.now()
        sample_task.completed_at = datetime.now()
        sample_task.result = {"output": "done"}
        sample_task.error = "some error"
        sample_task.tokens_used = 100
        sample_task.cost = 0.5

        result = sample_task.to_dict()
        assert result["assignee_id"] == "user_002"
        assert result["started_at"] is not None
        assert result["completed_at"] is not None
        assert result["result"] == {"output": "done"}
        assert result["error"] == "some error"
        assert result["tokens_used"] == 100
        assert result["cost"] == 0.5

    def test_to_dict_none_optionals(self, sample_task: TeamTask) -> None:
        result = sample_task.to_dict()
        assert result["started_at"] is None
        assert result["completed_at"] is None
        assert result["result"] is None
        assert result["error"] is None
        assert result["assignee_id"] is None

    def test_to_dict_subscribers(self, sample_task: TeamTask) -> None:
        sample_task.subscribers = ["user_001", "user_002"]
        result = sample_task.to_dict()
        assert result["subscribers"] == ["user_001", "user_002"]


class TestTeamTaskFromDict:
    def test_from_dict_basic(self) -> None:
        data = {
            "task_id": "task_002",
            "team_id": "team_002",
            "creator_id": "user_003",
            "title": "From Dict Task",
            "description": "Created from dict",
            "status": "running",
            "workflow": "test",
            "model": "gpt-4",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T11:00:00",
            "started_at": "2025-01-01T10:30:00",
            "completed_at": None,
            "result": None,
            "error": None,
            "tokens_used": 50,
            "cost": 0.25,
            "subscribers": ["user_003"],
        }
        task = TeamTask.from_dict(data)
        assert task.task_id == "task_002"
        assert task.team_id == "team_002"
        assert task.creator_id == "user_003"
        assert task.title == "From Dict Task"
        assert task.status == TaskStatus.RUNNING
        assert task.workflow == "test"
        assert task.model == "gpt-4"
        assert task.started_at is not None
        assert task.tokens_used == 50
        assert task.cost == 0.25

    def test_from_dict_defaults(self) -> None:
        data = {
            "task_id": "task_003",
            "team_id": "team_003",
            "creator_id": "user_004",
            "title": "Minimal Task",
            "status": "pending",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
        }
        task = TeamTask.from_dict(data)
        assert task.description == ""
        assert task.workflow == "build"
        assert task.model == "deepseek"
        assert task.assignee_id is None
        assert task.subscribers == []

    def test_from_dict_all_statuses(self) -> None:
        for status_str, expected in [
            ("pending", TaskStatus.PENDING),
            ("running", TaskStatus.RUNNING),
            ("completed", TaskStatus.COMPLETED),
            ("failed", TaskStatus.FAILED),
            ("cancelled", TaskStatus.CANCELLED),
        ]:
            data = {
                "task_id": f"task_{status_str}",
                "team_id": "team_x",
                "creator_id": "user_x",
                "title": "Status Test",
                "status": status_str,
                "created_at": "2025-01-01T10:00:00",
                "updated_at": "2025-01-01T10:00:00",
            }
            task = TeamTask.from_dict(data)
            assert task.status == expected

    def test_roundtrip(self, sample_task: TeamTask) -> None:
        """to_dict -> from_dict should preserve all fields."""
        d = sample_task.to_dict()
        restored = TeamTask.from_dict(d)
        assert restored.task_id == sample_task.task_id
        assert restored.team_id == sample_task.team_id
        assert restored.status == sample_task.status
        assert restored.title == sample_task.title
        assert restored.creator_id == sample_task.creator_id


# ---------------------------------------------------------------------------
# TaskSync - init (memory mode forced)
# ---------------------------------------------------------------------------

class TestTaskSyncInit:
    def test_init_sets_attributes(self) -> None:
        sync = TaskSync()
        assert sync.redis_url == "redis://localhost:6379"
        assert sync._redis is None
        assert sync._pubsub is None
        assert sync._subscribers == {}
        assert sync._tasks_cache == {}

    def test_init_custom_redis_url(self) -> None:
        sync = TaskSync(redis_url="redis://custom:1234")
        assert sync.redis_url == "redis://custom:1234"


# ---------------------------------------------------------------------------
# TaskSync - create_task (memory mode)
# ---------------------------------------------------------------------------

class TestCreateTask:
    @pytest.mark.asyncio
    async def test_create_task_success(self, sync: TaskSync) -> None:
        task = await sync.create_task(
            task_id="task_001",
            team_id="team_001",
            creator_id="user_001",
            title="Build Feature",
            description="Build a new feature",
            workflow="build",
            model="deepseek",
        )
        assert task.task_id == "task_001"
        assert task.team_id == "team_001"
        assert task.creator_id == "user_001"
        assert task.title == "Build Feature"
        assert task.description == "Build a new feature"
        assert task.status == TaskStatus.PENDING
        assert task.workflow == "build"
        assert task.model == "deepseek"
        assert task.subscribers == ["user_001"]
        assert task.created_at == task.updated_at
        assert task.started_at is None
        assert task.completed_at is None

    @pytest.mark.asyncio
    async def test_create_task_default_fields(self, sync: TaskSync) -> None:
        task = await sync.create_task(
            task_id="task_002",
            team_id="team_002",
            creator_id="user_002",
            title="Minimal Task",
        )
        assert task.description == ""
        assert task.workflow == "build"
        assert task.model == "deepseek"

    @pytest.mark.asyncio
    async def test_create_task_caches(self, sync: TaskSync) -> None:
        task = await sync.create_task(
            task_id="task_003",
            team_id="team_003",
            creator_id="user_003",
            title="Cached Task",
        )
        assert task.task_id in sync._tasks_cache
        assert sync._tasks_cache[task.task_id] is task


# ---------------------------------------------------------------------------
# TaskSync - get_task (memory mode)
# ---------------------------------------------------------------------------

class TestGetTask:
    @pytest.mark.asyncio
    async def test_get_task_exists(self, sync: TaskSync) -> None:
        created = await sync.create_task(
            task_id="task_010",
            team_id="team_010",
            creator_id="user_010",
            title="Get Me",
        )
        task = await sync.get_task("task_010")
        assert task is not None
        assert task.task_id == created.task_id
        assert task.title == created.title

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, sync: TaskSync) -> None:
        task = await sync.get_task("nonexistent")
        assert task is None


# ---------------------------------------------------------------------------
# TaskSync - update_status (memory mode)
# ---------------------------------------------------------------------------

class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_update_status_to_running(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_020",
            team_id="team_020",
            creator_id="user_020",
            title="Running Task",
        )
        task = await sync.update_status(
            "task_020",
            TaskStatus.RUNNING,
            tokens_used=100,
            cost=0.1,
        )
        assert task is not None
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None
        assert task.tokens_used == 100
        assert task.cost == 0.1
        assert task.completed_at is None

    @pytest.mark.asyncio
    async def test_update_status_to_completed(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_021",
            team_id="team_021",
            creator_id="user_021",
            title="Complete Me",
        )
        task = await sync.update_status(
            "task_021",
            TaskStatus.COMPLETED,
            result={"output": "success"},
            tokens_used=500,
            cost=1.0,
        )
        assert task is not None
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"output": "success"}
        assert task.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_status_to_failed(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_022",
            team_id="team_022",
            creator_id="user_022",
            title="Fail Me",
        )
        task = await sync.update_status(
            "task_022",
            TaskStatus.FAILED,
            error="Something went wrong",
        )
        assert task is not None
        assert task.status == TaskStatus.FAILED
        assert task.error == "Something went wrong"
        assert task.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_status_to_cancelled(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_023",
            team_id="team_023",
            creator_id="user_023",
            title="Cancel Me",
        )
        task = await sync.update_status("task_023", TaskStatus.CANCELLED)
        assert task is not None
        assert task.status == TaskStatus.CANCELLED
        assert task.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, sync: TaskSync) -> None:
        result = await sync.update_status("nonexistent", TaskStatus.RUNNING)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status_updates_updated_at(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_024",
            team_id="team_024",
            creator_id="user_024",
            title="Time Check",
        )
        task = await sync.get_task("task_024")
        assert task is not None
        original_updated = task.updated_at

        import asyncio

        await asyncio.sleep(0.01)

        updated = await sync.update_status("task_024", TaskStatus.RUNNING)
        assert updated is not None
        assert updated.updated_at >= original_updated


# ---------------------------------------------------------------------------
# TaskSync - get_team_tasks (memory mode)
# ---------------------------------------------------------------------------

class TestGetTeamTasks:
    @pytest.mark.asyncio
    async def test_get_team_tasks_empty(self, sync: TaskSync) -> None:
        tasks = await sync.get_team_tasks("team_030")
        assert tasks == []

    @pytest.mark.asyncio
    async def test_get_team_tasks_multiple(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_030a",
            team_id="team_030",
            creator_id="user_030",
            title="Task A",
        )
        await sync.create_task(
            task_id="task_030b",
            team_id="team_030",
            creator_id="user_030",
            title="Task B",
        )
        await sync.create_task(
            task_id="task_030c",
            team_id="team_030",
            creator_id="user_030",
            title="Task C",
        )
        tasks = await sync.get_team_tasks("team_030")
        assert len(tasks) == 3
        titles = {t.title for t in tasks}
        assert titles == {"Task A", "Task B", "Task C"}

    @pytest.mark.asyncio
    async def test_get_team_tasks_different_teams(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_031a",
            team_id="team_031",
            creator_id="user_031",
            title="Team 31 Task",
        )
        await sync.create_task(
            task_id="task_031b",
            team_id="team_032",
            creator_id="user_031",
            title="Team 32 Task",
        )
        tasks_31 = await sync.get_team_tasks("team_031")
        tasks_32 = await sync.get_team_tasks("team_032")
        assert len(tasks_31) == 1
        assert len(tasks_32) == 1
        assert tasks_31[0].title == "Team 31 Task"
        assert tasks_32[0].title == "Team 32 Task"


# ---------------------------------------------------------------------------
# TaskSync - subscribe_task (memory mode)
# ---------------------------------------------------------------------------

class TestSubscribeTask:
    @pytest.mark.asyncio
    async def test_subscribe_task_success(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_040",
            team_id="team_040",
            creator_id="user_040",
            title="Subscribe Me",
        )
        result = await sync.subscribe_task("task_040", "user_041")
        assert result is True
        task = await sync.get_task("task_040")
        assert task is not None
        assert "user_040" in task.subscribers
        assert "user_041" in task.subscribers

    @pytest.mark.asyncio
    async def test_subscribe_task_idempotent(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_041",
            team_id="team_041",
            creator_id="user_040",
            title="Subscribe Me Twice",
        )
        await sync.subscribe_task("task_041", "user_040")
        await sync.subscribe_task("task_041", "user_040")
        task = await sync.get_task("task_041")
        assert task is not None
        assert task.subscribers.count("user_040") == 1

    @pytest.mark.asyncio
    async def test_subscribe_task_not_found(self, sync: TaskSync) -> None:
        result = await sync.subscribe_task("nonexistent", "user_099")
        assert result is False


# ---------------------------------------------------------------------------
# TaskSync - unsubscribe_task (memory mode)
# ---------------------------------------------------------------------------

class TestUnsubscribeTask:
    @pytest.mark.asyncio
    async def test_unsubscribe_task_success(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_050",
            team_id="team_050",
            creator_id="user_050",
            title="Unsubscribe Me",
        )
        await sync.subscribe_task("task_050", "user_051")
        result = await sync.unsubscribe_task("task_050", "user_050")
        assert result is True
        task = await sync.get_task("task_050")
        assert task is not None
        assert "user_050" not in task.subscribers
        assert "user_051" in task.subscribers

    @pytest.mark.asyncio
    async def test_unsubscribe_task_idempotent(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_051",
            team_id="team_051",
            creator_id="user_050",
            title="Unsubscribe Twice",
        )
        # user_050 is creator, but already in subscribers; remove first
        await sync.unsubscribe_task("task_051", "user_050")
        # Now try to unsubscribe again (already removed)
        result = await sync.unsubscribe_task("task_051", "user_050")
        # unsubscribe returns True even if user was not in list
        assert result is True

    @pytest.mark.asyncio
    async def test_unsubscribe_task_not_found(self, sync: TaskSync) -> None:
        result = await sync.unsubscribe_task("nonexistent", "user_099")
        assert result is False


# ---------------------------------------------------------------------------
# TaskSync - delete_task (memory mode)
# ---------------------------------------------------------------------------

class TestDeleteTask:
    @pytest.mark.asyncio
    async def test_delete_task_success(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_060",
            team_id="team_060",
            creator_id="user_060",
            title="Delete Me",
        )
        result = await sync.delete_task("task_060")
        assert result is True
        task = await sync.get_task("task_060")
        assert task is None

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, sync: TaskSync) -> None:
        result = await sync.delete_task("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_task_removes_from_cache(self, sync: TaskSync) -> None:
        await sync.create_task(
            task_id="task_061",
            team_id="team_061",
            creator_id="user_061",
            title="Remove From Cache",
        )
        assert "task_061" in sync._tasks_cache
        await sync.delete_task("task_061")
        assert "task_061" not in sync._tasks_cache


# ---------------------------------------------------------------------------
# TaskSync - _publish_event
# ---------------------------------------------------------------------------

class TestPublishEvent:
    @pytest.mark.asyncio
    async def test_publish_event_no_error_memory_mode(self, sync: TaskSync) -> None:
        """Publishing an event should not raise in memory mode."""
        await sync._publish_event("task_created", {"task_id": "x"})


# ---------------------------------------------------------------------------
# TaskSync - listen_updates
# ---------------------------------------------------------------------------

class TestListenUpdates:
    @pytest.mark.asyncio
    async def test_listen_updates_memory_mode_returns(self, sync: TaskSync) -> None:
        """In memory mode, listen_updates should return immediately."""
        callback = MagicMock()
        await sync.listen_updates(callback)
        callback.assert_not_called()


# ---------------------------------------------------------------------------
# TaskSync - Redis mode (forced with _use_memory=False and mock Redis)
# ---------------------------------------------------------------------------

class TestTaskSyncRedisMode:
    """Test TaskSync when operating in Redis mode (mocked)."""

    @pytest.fixture
    def redis_sync(self) -> TaskSync:
        """TaskSync forced into Redis mode with a mock Redis client."""
        sync = TaskSync()
        sync._use_memory = False
        sync._redis = AsyncMock()
        sync._pubsub = AsyncMock()
        return sync

    @pytest.mark.asyncio
    async def test_create_task_redis(self, redis_sync: TaskSync) -> None:
        """create_task stores to Redis when in Redis mode."""
        redis_sync._redis.hset = AsyncMock(return_value=1)
        redis_sync._redis.sadd = AsyncMock(return_value=1)
        redis_sync._redis.publish = AsyncMock(return_value=1)

        task = await redis_sync.create_task(
            task_id="redis_task",
            team_id="redis_team",
            creator_id="redis_user",
            title="Redis Task",
        )

        assert task.task_id == "redis_task"
        redis_sync._redis.hset.assert_called()
        redis_sync._redis.sadd.assert_called()

    @pytest.mark.asyncio
    async def test_get_task_redis_found(self, redis_sync: TaskSync) -> None:
        """get_task reads from Redis and returns a TeamTask."""
        import json as _json

        task_dict = {
            "task_id": "redis_get_task",
            "team_id": "redis_team",
            "creator_id": "redis_user",
            "title": "Redis Get Task",
            "description": "",
            "status": "pending",
            "workflow": "build",
            "model": "deepseek",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "tokens_used": 0,
            "cost": 0.0,
            "subscribers": [],
        }
        redis_sync._redis.hget = AsyncMock(
            return_value=_json.dumps(task_dict).encode()
        )

        task = await redis_sync.get_task("redis_get_task")
        assert task is not None
        assert task.task_id == "redis_get_task"
        assert task.title == "Redis Get Task"
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_task_redis_not_found(self, redis_sync: TaskSync) -> None:
        """get_task returns None when Redis has no data."""
        redis_sync._redis.hget = AsyncMock(return_value=None)

        task = await redis_sync.get_task("nonexistent")
        assert task is None

    @pytest.mark.asyncio
    async def test_get_team_tasks_redis(self, redis_sync: TaskSync) -> None:
        """get_team_tasks reads task IDs from Redis set and fetches each."""
        import json as _json

        task_dict = {
            "task_id": "team_task_1",
            "team_id": "redis_team_2",
            "creator_id": "redis_user",
            "title": "Team Task 1",
            "description": "",
            "status": "pending",
            "workflow": "build",
            "model": "deepseek",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "tokens_used": 0,
            "cost": 0.0,
            "subscribers": [],
        }
        redis_sync._redis.smembers = AsyncMock(return_value={b"team_task_1"})
        redis_sync._redis.hget = AsyncMock(
            return_value=_json.dumps(task_dict).encode()
        )

        tasks = await redis_sync.get_team_tasks("redis_team_2")
        assert len(tasks) == 1
        assert tasks[0].task_id == "team_task_1"

    @pytest.mark.asyncio
    async def test_get_team_tasks_redis_empty(self, redis_sync: TaskSync) -> None:
        """get_team_tasks returns empty list when no tasks in Redis set."""
        redis_sync._redis.smembers = AsyncMock(return_value=set())

        tasks = await redis_sync.get_team_tasks("empty_team")
        assert tasks == []

    @pytest.mark.asyncio
    async def test_update_status_redis(self, redis_sync: TaskSync) -> None:
        """update_status writes updated task to Redis."""
        import json as _json

        original_dict = {
            "task_id": "redis_update_task",
            "team_id": "redis_team",
            "creator_id": "redis_user",
            "title": "Redis Update Task",
            "description": "",
            "status": "pending",
            "workflow": "build",
            "model": "deepseek",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "tokens_used": 0,
            "cost": 0.0,
            "subscribers": [],
        }
        redis_sync._redis.hget = AsyncMock(
            return_value=_json.dumps(original_dict).encode()
        )
        redis_sync._redis.hset = AsyncMock(return_value=1)
        redis_sync._redis.publish = AsyncMock(return_value=1)

        task = await redis_sync.update_status(
            "redis_update_task",
            TaskStatus.COMPLETED,
            result={"output": "done"},
            tokens_used=200,
            cost=0.5,
        )

        assert task is not None
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"output": "done"}
        redis_sync._redis.hset.assert_called()

    @pytest.mark.asyncio
    async def test_delete_task_redis(self, redis_sync: TaskSync) -> None:
        """delete_task removes task from Redis."""
        import json as _json

        task_dict = {
            "task_id": "redis_delete_task",
            "team_id": "redis_team_del",
            "creator_id": "redis_user",
            "title": "Redis Delete Task",
            "description": "",
            "status": "pending",
            "workflow": "build",
            "model": "deepseek",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "tokens_used": 0,
            "cost": 0.0,
            "subscribers": [],
        }
        redis_sync._redis.hget = AsyncMock(
            return_value=_json.dumps(task_dict).encode()
        )
        redis_sync._redis.delete = AsyncMock(return_value=1)
        redis_sync._redis.srem = AsyncMock(return_value=1)
        redis_sync._redis.publish = AsyncMock(return_value=1)

        result = await redis_sync.delete_task("redis_delete_task")
        assert result is True
        redis_sync._redis.delete.assert_called()
        redis_sync._redis.srem.assert_called()

    @pytest.mark.asyncio
    async def test_subscribe_task_redis(self, redis_sync: TaskSync) -> None:
        """subscribe_task writes updated task to Redis."""
        import json as _json

        original_dict = {
            "task_id": "redis_sub_task",
            "team_id": "redis_team",
            "creator_id": "redis_user",
            "title": "Redis Subscribe Task",
            "description": "",
            "status": "pending",
            "workflow": "build",
            "model": "deepseek",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "tokens_used": 0,
            "cost": 0.0,
            "subscribers": ["redis_user"],
        }
        redis_sync._redis.hget = AsyncMock(
            return_value=_json.dumps(original_dict).encode()
        )
        redis_sync._redis.hset = AsyncMock(return_value=1)

        result = await redis_sync.subscribe_task("redis_sub_task", "new_user")
        assert result is True
        redis_sync._redis.hset.assert_called()

    @pytest.mark.asyncio
    async def test_unsubscribe_task_redis(self, redis_sync: TaskSync) -> None:
        """unsubscribe_task writes updated task to Redis."""
        import json as _json

        original_dict = {
            "task_id": "redis_unsub_task",
            "team_id": "redis_team",
            "creator_id": "redis_user",
            "title": "Redis Unsubscribe Task",
            "description": "",
            "status": "pending",
            "workflow": "build",
            "model": "deepseek",
            "created_at": "2025-01-01T10:00:00",
            "updated_at": "2025-01-01T10:00:00",
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
            "tokens_used": 0,
            "cost": 0.0,
            "subscribers": ["redis_user", "other_user"],
        }
        redis_sync._redis.hget = AsyncMock(
            return_value=_json.dumps(original_dict).encode()
        )
        redis_sync._redis.hset = AsyncMock(return_value=1)

        result = await redis_sync.unsubscribe_task("redis_unsub_task", "other_user")
        assert result is True
        redis_sync._redis.hset.assert_called()

    @pytest.mark.asyncio
    async def test_connect_redis_fails_falls_back(self) -> None:
        """When Redis connect fails, _use_memory becomes True."""
        sync = TaskSync()
        # Patch the redis.asyncio module at the source used by task_sync
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Connection refused")
            await sync.connect()
        assert sync._use_memory is True

    @pytest.mark.asyncio
    async def test_disconnect_redis(self) -> None:
        """disconnect closes Redis connection."""
        mock_redis_instance = AsyncMock()

        sync = TaskSync()
        sync._use_memory = False
        sync._redis = mock_redis_instance

        await sync.disconnect()
        mock_redis_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_memory_mode_noop(self, sync: TaskSync) -> None:
        """disconnect does nothing in memory mode."""
        # Should not raise
        await sync.disconnect()


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------

class TestGlobalInstance:
    def test_task_sync_global_instance(self) -> None:
        assert isinstance(task_sync, TaskSync)
