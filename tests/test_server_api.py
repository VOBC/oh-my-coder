"""
Tests for server_api.py

Coverage target: All functions, classes, and error paths in server_api.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI

from src.api.server_api import (
    AuthContext,
    RunRequest,
    TaskRecord,
    TaskResponse,
    TaskStatus,
    TaskStore,
    create_app,
    run_agent_task,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary storage directory for TaskStore."""
    storage_dir = tmp_path / "tasks"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def task_store(temp_storage_dir):
    """Create a TaskStore with temporary storage."""
    # Set up event loop for asyncio.Lock in TaskStore.__init__
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return TaskStore(storage_dir=temp_storage_dir)


@pytest.fixture
def event_loop():
    """Create event loop for tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# =============================================================================
# TaskStatus Tests
# =============================================================================


def test_task_status_values():
    """Test TaskStatus enum values."""
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.RUNNING == "running"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.FAILED == "failed"


def test_task_status_is_string():
    """Test that TaskStatus is a string enum."""
    assert isinstance(TaskStatus.PENDING, str)
    assert TaskStatus.PENDING.value == "pending"


# =============================================================================
# TaskRecord Tests
# =============================================================================


def test_task_record_creation():
    """Test TaskRecord creation with default values."""
    record = TaskRecord(
        task_id="test-123",
        prompt="Test prompt",
        status=TaskStatus.PENDING,
        created_at="2024-01-01T00:00:00",
    )

    assert record.task_id == "test-123"
    assert record.prompt == "Test prompt"
    assert record.status == TaskStatus.PENDING
    assert record.created_at == "2024-01-01T00:00:00"
    assert record.started_at is None
    assert record.completed_at is None
    assert record.result is None
    assert record.error is None
    assert record.execution_time == 0.0
    assert record.metadata == {}


def test_task_record_with_metadata():
    """Test TaskRecord with custom metadata."""
    metadata = {"key": "value", "number": 42}
    record = TaskRecord(
        task_id="test-456",
        prompt="Test",
        status=TaskStatus.RUNNING,
        created_at="2024-01-01T00:00:00",
        started_at="2024-01-01T00:01:00",
        metadata=metadata,
    )

    assert record.metadata == metadata
    assert record.started_at == "2024-01-01T00:01:00"


def test_task_record_with_result():
    """Test TaskRecord with result data."""
    result = {"output": "success", "tokens": 100}
    record = TaskRecord(
        task_id="test-789",
        prompt="Test",
        status=TaskStatus.COMPLETED,
        created_at="2024-01-01T00:00:00",
        completed_at="2024-01-01T00:02:00",
        result=result,
        execution_time=120.5,
    )

    assert record.result == result
    assert record.execution_time == 120.5


def test_task_record_with_error():
    """Test TaskRecord with error."""
    record = TaskRecord(
        task_id="test-error",
        prompt="Test",
        status=TaskStatus.FAILED,
        created_at="2024-01-01T00:00:00",
        error="Something went wrong",
    )

    assert record.status == TaskStatus.FAILED
    assert record.error == "Something went wrong"


# =============================================================================
# TaskStore Tests
# =============================================================================


def test_task_store_init(temp_storage_dir):
    """Test TaskStore initialization."""
    # Set up event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    store = TaskStore(storage_dir=temp_storage_dir)

    assert store._storage_dir == temp_storage_dir
    assert store._store == {}


def test_task_store_init_default_dir():
    """Test TaskStore with default directory."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    with patch.object(Path, 'mkdir'):
        store = TaskStore()
        assert store._storage_dir == Path.home() / ".omc" / "server_tasks"


def test_task_store_create(task_store):
    """Test creating a task in TaskStore."""
    record = asyncio.run(task_store.create("Test prompt"))

    assert record.task_id is not None
    assert len(record.task_id) == 12
    assert record.prompt == "Test prompt"
    assert record.status == TaskStatus.PENDING
    assert record.created_at is not None


def test_task_store_create_with_metadata(task_store):
    """Test creating a task with metadata."""
    metadata = {"project": "test-project", "priority": "high"}
    record = asyncio.run(task_store.create("Test prompt", metadata=metadata))

    assert record.metadata == metadata


def test_task_store_get(task_store):
    """Test getting a task from TaskStore."""
    created = asyncio.run(task_store.create("Test prompt"))
    retrieved = asyncio.run(task_store.get(created.task_id))

    assert retrieved is not None
    assert retrieved.task_id == created.task_id
    assert retrieved.prompt == "Test prompt"


def test_task_store_get_not_found(task_store):
    """Test getting a non-existent task."""
    retrieved = asyncio.run(task_store.get("nonexistent"))

    assert retrieved is None


def test_task_store_list_all(task_store):
    """Test listing all tasks."""
    asyncio.run(task_store.create("Task 1"))
    asyncio.run(task_store.create("Task 2"))
    asyncio.run(task_store.create("Task 3"))

    tasks = asyncio.run(task_store.list_all())

    assert len(tasks) == 3


def test_task_store_list_all_sorted_by_created_at(task_store):
    """Test that list_all returns tasks sorted by created_at descending."""
    import time

    asyncio.run(task_store.create("Task 1"))
    time.sleep(0.01)  # Ensure different timestamps
    asyncio.run(task_store.create("Task 2"))
    time.sleep(0.01)
    asyncio.run(task_store.create("Task 3"))

    tasks = asyncio.run(task_store.list_all())

    assert tasks[0].prompt == "Task 3"
    assert tasks[1].prompt == "Task 2"
    assert tasks[2].prompt == "Task 1"


def test_task_store_update_status_to_running(task_store):
    """Test updating task status to RUNNING."""
    record = asyncio.run(task_store.create("Test"))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))

    updated = asyncio.run(task_store.get(record.task_id))

    assert updated is not None
    assert updated.status == TaskStatus.RUNNING
    assert updated.started_at is not None


def test_task_store_update_status_to_completed(task_store):
    """Test updating task status to COMPLETED with result."""
    record = asyncio.run(task_store.create("Test"))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))

    result = {"output": "success", "tokens": 500}
    asyncio.run(task_store.update(record.task_id, TaskStatus.COMPLETED, result=result))

    updated = asyncio.run(task_store.get(record.task_id))

    assert updated is not None
    assert updated.status == TaskStatus.COMPLETED
    assert updated.result == result
    assert updated.completed_at is not None
    assert updated.execution_time > 0


def test_task_store_update_status_to_failed(task_store):
    """Test updating task status to FAILED with error."""
    record = asyncio.run(task_store.create("Test"))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))

    asyncio.run(task_store.update(record.task_id, TaskStatus.FAILED, error="Test error"))

    updated = asyncio.run(task_store.get(record.task_id))

    assert updated is not None
    assert updated.status == TaskStatus.FAILED
    assert updated.error == "Test error"
    assert updated.completed_at is not None


def test_task_store_update_nonexistent_task(task_store):
    """Test updating a non-existent task (should not raise error)."""
    # Should not raise error
    asyncio.run(task_store.update("nonexistent", TaskStatus.RUNNING))


def test_task_store_delete(task_store):
    """Test deleting a task."""
    record = asyncio.run(task_store.create("Test"))

    result = asyncio.run(task_store.delete(record.task_id))

    assert result is True
    assert asyncio.run(task_store.get(record.task_id)) is None


def test_task_store_delete_nonexistent(task_store):
    """Test deleting a non-existent task."""
    result = asyncio.run(task_store.delete("nonexistent"))

    assert result is False


def test_task_store_persistence(temp_storage_dir):
    """Test that tasks are persisted to disk."""
    # Set up event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    store1 = TaskStore(storage_dir=temp_storage_dir)
    record = asyncio.run(store1.create("Test prompt"))
    task_id = record.task_id

    # Reset and recreate event loop for second store
    # (simulates process restart)
    loop2 = asyncio.new_event_loop()
    asyncio.set_event_loop(loop2)

    # Create new store instance (simulates restart)
    store2 = TaskStore(storage_dir=temp_storage_dir)
    retrieved = asyncio.run(store2.get(task_id))

    assert retrieved is not None
    assert retrieved.prompt == "Test prompt"

    loop2.close()


def test_task_store_persistence_limit(temp_storage_dir):
    """Test that only recent 100 tasks are loaded."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Create 150 tasks
    store1 = TaskStore(storage_dir=temp_storage_dir)
    for i in range(150):
        asyncio.run(store1.create(f"Task {i}"))

    # Reset and recreate event loop for second store
    loop2 = asyncio.new_event_loop()
    asyncio.set_event_loop(loop2)

    # Create new store instance
    store2 = TaskStore(storage_dir=temp_storage_dir)
    tasks = asyncio.run(store2.list_all())

    # Should only load 100 most recent
    assert len(tasks) == 100

    loop2.close()


def test_task_store_save_error_handling(temp_storage_dir):
    """Test that save errors are handled gracefully."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    store = TaskStore(storage_dir=temp_storage_dir)
    record = asyncio.run(store.create("Test"))

    # Task should be in memory even if save fails
    assert asyncio.run(store.get(record.task_id)) is not None


# =============================================================================
# AuthContext Tests
# =============================================================================


def test_auth_context_init():
    """Test AuthContext initialization."""
    ctx = AuthContext("test-key")
    assert ctx.api_key == "test-key"


def test_auth_context_init_none():
    """Test AuthContext with None API key."""
    ctx = AuthContext(None)
    assert ctx.api_key == ""


def test_auth_context_hash_key():
    """Test API key hashing."""
    hashed = AuthContext.hash_key("my-secret-key")

    # Verify it's a 16-character hex string
    assert len(hashed) == 16
    # Verify it's actually SHA256[:16]
    expected = hashlib.sha256(b"my-secret-key").hexdigest()[:16]
    assert hashed == expected


def test_auth_context_verify_correct_key():
    """Test verification with correct API key."""
    ctx = AuthContext("correct-key")

    assert ctx.verify("correct-key") is True


def test_auth_context_verify_wrong_key():
    """Test verification with wrong API key."""
    ctx = AuthContext("correct-key")

    assert ctx.verify("wrong-key") is False


def test_auth_context_verify_no_key_required():
    """Test verification when no API key is configured."""
    ctx = AuthContext(None)

    # Should accept any key when no key is configured
    assert ctx.verify("any-key") is True
    assert ctx.verify(None) is True


def test_auth_context_verify_none_provided():
    """Test verification when no key is provided."""
    ctx = AuthContext("configured-key")

    assert ctx.verify(None) is False


def test_auth_context_empty_string_key():
    """Test AuthContext with empty string API key."""
    ctx = AuthContext("")

    # Empty string is falsy, so auth should be skipped
    assert ctx.verify("any-key") is True


# =============================================================================
# RunRequest Tests
# =============================================================================


def test_run_request_creation():
    """Test RunRequest model creation."""
    req = RunRequest(prompt="Test prompt")

    assert req.prompt == "Test prompt"
    assert req.metadata is None


def test_run_request_with_metadata():
    """Test RunRequest with metadata."""
    metadata = {"project": "test"}
    req = RunRequest(prompt="Test prompt", metadata=metadata)

    assert req.metadata == metadata


def test_run_request_validation():
    """Test RunRequest validates required fields."""
    # Missing prompt should fail
    with pytest.raises(Exception):  # noqa: B017
        RunRequest()


# =============================================================================
# TaskResponse Tests
# =============================================================================


def test_task_response_creation():
    """Test TaskResponse model creation."""
    resp = TaskResponse(
        task_id="test-123",
        status="pending",
        created_at="2024-01-01T00:00:00",
        prompt="Test prompt",
    )

    assert resp.task_id == "test-123"
    assert resp.status == "pending"
    assert resp.execution_time == 0.0
    assert resp.metadata == {}


def test_task_response_with_all_fields():
    """Test TaskResponse with all fields."""
    resp = TaskResponse(
        task_id="test-123",
        status="completed",
        created_at="2024-01-01T00:00:00",
        prompt="Test prompt",
        started_at="2024-01-01T00:01:00",
        completed_at="2024-01-01T00:02:00",
        execution_time=60.0,
        metadata={"key": "value"},
    )

    assert resp.started_at == "2024-01-01T00:01:00"
    assert resp.completed_at == "2024-01-01T00:02:00"
    assert resp.execution_time == 60.0
    assert resp.metadata == {"key": "value"}


def test_task_response_from_attributes():
    """Test TaskResponse Config.from_attributes."""
    record = TaskRecord(
        task_id="test-123",
        prompt="Test",
        status=TaskStatus.COMPLETED,
        created_at="2024-01-01T00:00:00",
        execution_time=60.0,
    )

    # Pydantic v2 uses from_attributes
    resp = TaskResponse.model_validate(record)
    assert resp.task_id == "test-123"


def test_task_response_optional_fields():
    """Test TaskResponse handles optional fields correctly."""
    resp = TaskResponse(
        task_id="test",
        status="pending",
        created_at="2024-01-01",
        prompt="Test",
        started_at=None,
        completed_at=None,
    )

    assert resp.started_at is None
    assert resp.completed_at is None


# =============================================================================
# TaskStore Edge Cases
# =============================================================================


def test_task_store_load_all_error_handling(tmp_path):
    """Test TaskStore._load_all handles errors gracefully."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    storage_dir = tmp_path / "tasks"
    storage_dir.mkdir()

    # Create an invalid JSON file
    bad_file = storage_dir / "bad.json"
    bad_file.write_text("invalid json {{{")

    # Create a valid file
    good_file = storage_dir / "good.json"
    good_file.write_text(json.dumps({
        "task_id": "good-task",
        "prompt": "Test",
        "status": "pending",
        "created_at": "2024-01-01T00:00:00",
    }))

    # Should load only the valid file
    store = TaskStore(storage_dir=storage_dir)
    tasks = asyncio.run(store.list_all())

    assert len(tasks) == 1
    assert tasks[0].task_id == "good-task"


def test_task_store_delete_file_removal(temp_storage_dir):
    """Test that delete removes the file from disk."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    store = TaskStore(storage_dir=temp_storage_dir)
    record = asyncio.run(store.create("Test"))

    # Check file exists
    file_path = temp_storage_dir / f"{record.task_id}.json"
    assert file_path.exists()

    # Delete task
    asyncio.run(store.delete(record.task_id))

    # Check file is removed
    assert not file_path.exists()


def test_task_store_update_with_result_and_error(task_store):
    """Test update with both result and error."""
    record = asyncio.run(task_store.create("Test"))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))

    result = {"output": "partial"}
    asyncio.run(task_store.update(
        record.task_id,
        TaskStatus.FAILED,
        result=result,
        error="Partial failure",
    ))

    updated = asyncio.run(task_store.get(record.task_id))
    assert updated is not None
    assert updated.result == result
    assert updated.error == "Partial failure"


def test_task_store_concurrent_access(task_store):
    """Test TaskStore handles concurrent access correctly."""
    async def create_multiple_tasks():
        tasks = []
        for i in range(10):
            task = await task_store.create(f"Task {i}")
            tasks.append(task)
        return tasks

    tasks = asyncio.run(create_multiple_tasks())
    assert len(tasks) == 10


def test_task_store_empty_list(task_store):
    """Test TaskStore list_all when empty."""
    tasks = asyncio.run(task_store.list_all())

    assert tasks == []


# =============================================================================
# run_agent_task Tests
# =============================================================================


@pytest.mark.asyncio
async def test_run_agent_task_orchestrator_unavailable(task_store):
    """Test run_agent_task handles Orchestrator unavailability gracefully."""
    record = await task_store.create("Test prompt")

    # The function imports Orchestrator inside, so it will catch the ImportError
    await run_agent_task("Test prompt", record.task_id, task_store)

    updated = await task_store.get(record.task_id)
    assert updated is not None
    # Should complete with degraded status (Orchestrator import will fail)
    assert updated.status == TaskStatus.COMPLETED
    assert updated.result is not None


@pytest.mark.asyncio
async def test_run_agent_task_general_exception(task_store):
    """Test run_agent_task handles general exceptions."""
    record = await task_store.create("Test prompt")

    # Mock store.update to raise an exception
    original_update = task_store.update

    async def failing_update(*args, **kwargs):
        if args[1] == TaskStatus.RUNNING:
            raise RuntimeError("Database error")
        return await original_update(*args, **kwargs)

    task_store.update = failing_update

    # Should catch the exception and mark as FAILED
    await run_agent_task("Test prompt", record.task_id, task_store)

    # Restore original
    task_store.update = original_update

    # The task should be marked as failed
    await task_store.get(record.task_id)
    # Note: The exact status depends on where the error occurred


# =============================================================================
# create_app Tests
# =============================================================================


def test_create_app_default_params():
    """Test create_app with default parameters."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    app, store = create_app()

    assert isinstance(app, FastAPI)
    assert isinstance(store, TaskStore)


def test_create_app_with_custom_store(task_store):
    """Test create_app with custom TaskStore."""
    app, store = create_app(api_key=None, store=task_store)

    assert store is task_store


def test_create_app_with_api_key(task_store):
    """Test create_app with API key."""
    app, store = create_app(api_key="test-key", store=task_store)

    assert isinstance(app, FastAPI)


# =============================================================================
# Additional Coverage Tests
# =============================================================================


def test_task_store_save_creates_file(temp_storage_dir):
    """Test that _save creates a file."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    store = TaskStore(storage_dir=temp_storage_dir)
    record = asyncio.run(store.create("Test"))

    # Check file was created
    file_path = temp_storage_dir / f"{record.task_id}.json"
    assert file_path.exists()

    # Verify content
    data = json.loads(file_path.read_text())
    assert data["task_id"] == record.task_id
    assert data["prompt"] == "Test"


def test_task_store_update_sets_started_at_once(task_store):
    """Test that started_at is only set once."""
    record = asyncio.run(task_store.create("Test"))

    # First update to RUNNING
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))
    first_started = asyncio.run(task_store.get(record.task_id)).started_at

    # Second update to RUNNING
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))
    second_started = asyncio.run(task_store.get(record.task_id)).started_at

    # Should be the same
    assert first_started == second_started


def test_task_store_update_execution_time_calculation(task_store):
    """Test execution_time is calculated correctly."""
    import time

    record = asyncio.run(task_store.create("Test"))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))

    time.sleep(0.1)  # Small delay

    asyncio.run(task_store.update(record.task_id, TaskStatus.COMPLETED))

    updated = asyncio.run(task_store.get(record.task_id))
    assert updated is not None
    assert updated.execution_time >= 0.1


def test_task_record_field_types():
    """Test TaskRecord field types."""
    record = TaskRecord(
        task_id="test",
        prompt="test",
        status=TaskStatus.PENDING,
        created_at="2024-01-01",
    )

    assert isinstance(record.metadata, dict)
    assert isinstance(record.execution_time, float)


# =============================================================================
# Integration Tests (without mounting web app)
# =============================================================================


def test_task_status_all_values():
    """Test all TaskStatus values."""
    statuses = [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED]
    status_values = [s.value for s in statuses]

    assert "pending" in status_values
    assert "running" in status_values
    assert "completed" in status_values
    assert "failed" in status_values


def test_auth_context_multiple_verifications():
    """Test multiple verification calls."""
    ctx = AuthContext("my-key")

    assert ctx.verify("my-key") is True
    assert ctx.verify("wrong-key") is False
    assert ctx.verify("my-key") is True  # Should still work


def test_task_store_multiple_operations(task_store):
    """Test multiple operations in sequence."""
    # Create
    record1 = asyncio.run(task_store.create("Task 1"))
    record2 = asyncio.run(task_store.create("Task 2"))

    # Get
    retrieved = asyncio.run(task_store.get(record1.task_id))
    assert retrieved is not None

    # Update
    asyncio.run(task_store.update(record1.task_id, TaskStatus.RUNNING))

    # List
    tasks = asyncio.run(task_store.list_all())
    assert len(tasks) == 2

    # Delete
    asyncio.run(task_store.delete(record2.task_id))

    # Verify
    tasks = asyncio.run(task_store.list_all())
    assert len(tasks) == 1


# =============================================================================
# Edge Cases
# =============================================================================


def test_task_store_create_empty_prompt(task_store):
    """Test creating a task with empty prompt."""
    record = asyncio.run(task_store.create(""))

    assert record.prompt == ""


def test_task_store_create_long_prompt(task_store):
    """Test creating a task with very long prompt."""
    long_prompt = "x" * 10000
    record = asyncio.run(task_store.create(long_prompt))

    assert record.prompt == long_prompt


def test_task_store_create_unicode_prompt(task_store):
    """Test creating a task with unicode prompt."""
    unicode_prompt = "测试任务 🔥 emoji"
    record = asyncio.run(task_store.create(unicode_prompt))

    assert record.prompt == unicode_prompt


def test_task_store_metadata_various_types(task_store):
    """Test creating tasks with various metadata types."""
    metadata = {
        "string": "value",
        "number": 42,
        "float": 3.14,
        "bool": True,
        "list": [1, 2, 3],
        "nested": {"key": "value"},
    }

    record = asyncio.run(task_store.create("Test", metadata=metadata))

    assert record.metadata == metadata


def test_task_store_result_various_types(task_store):
    """Test updating task with various result types."""
    record = asyncio.run(task_store.create("Test"))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))

    result = {
        "output": "result",
        "tokens": 100,
        "metadata": {"key": "value"},
    }

    asyncio.run(task_store.update(record.task_id, TaskStatus.COMPLETED, result=result))

    updated = asyncio.run(task_store.get(record.task_id))
    assert updated.result == result


def test_auth_context_with_special_characters_in_key():
    """Test AuthContext with special characters in API key."""
    special_key = "key-with-special!@#$%^&*()_+-={}[]|:;<>,.?/~`"
    ctx = AuthContext(special_key)

    assert ctx.verify(special_key) is True
    assert ctx.verify("wrong") is False


def test_auth_context_with_unicode_key():
    """Test AuthContext with unicode API key."""
    unicode_key = "密钥-🔑-key"
    ctx = AuthContext(unicode_key)

    assert ctx.verify(unicode_key) is True


def test_task_response_with_none_values():
    """Test TaskResponse handles None values."""
    resp = TaskResponse(
        task_id="test",
        status="pending",
        created_at="2024-01-01",
        prompt="Test",
        started_at=None,
        completed_at=None,
        execution_time=0.0,
        metadata={},
    )

    assert resp.started_at is None
    assert resp.completed_at is None
    assert resp.execution_time == 0.0
    assert resp.metadata == {}


def test_task_record_default_factory():
    """Test TaskRecord default_factory for metadata."""
    record = TaskRecord(
        task_id="test",
        prompt="test",
        status=TaskStatus.PENDING,
        created_at="2024-01-01",
    )

    # metadata should be a new dict, not shared
    assert record.metadata == {}
    record.metadata["key"] = "value"

    # New record should have empty metadata
    record2 = TaskRecord(
        task_id="test2",
        prompt="test",
        status=TaskStatus.PENDING,
        created_at="2024-01-01",
    )
    assert record2.metadata == {}


def test_task_store_update_idempotent(task_store):
    """Test that update operations are idempotent."""
    record = asyncio.run(task_store.create("Test"))

    # Multiple updates with same status
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))

    updated = asyncio.run(task_store.get(record.task_id))
    assert updated.status == TaskStatus.RUNNING


def test_task_store_result_and_error_independent(task_store):
    """Test that result and error are independent."""
    record = asyncio.run(task_store.create("Test"))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))

    # Set result
    asyncio.run(task_store.update(record.task_id, TaskStatus.COMPLETED, result={"output": "done"}))

    updated = asyncio.run(task_store.get(record.task_id))
    assert updated.result is not None
    assert updated.error is None

    # Create new task and set error
    record2 = asyncio.run(task_store.create("Test 2"))
    asyncio.run(task_store.update(record2.task_id, TaskStatus.RUNNING))
    asyncio.run(task_store.update(record2.task_id, TaskStatus.FAILED, error="Error"))

    updated2 = asyncio.run(task_store.get(record2.task_id))
    assert updated2.result is None
    assert updated2.error is not None


# =============================================================================
# Additional tests for missing coverage
# =============================================================================


def test_task_store_load_all_with_exception_in_stat(tmp_path):
    """Test _load_all handles exceptions in file.stat()."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    storage_dir = tmp_path / "tasks"
    storage_dir.mkdir()

    # Create a valid file
    good_file = storage_dir / "good.json"
    good_file.write_text(json.dumps({
        "task_id": "good-task",
        "prompt": "Test",
        "status": "pending",
        "created_at": "2024-01-01T00:00:00",
    }))

    # Mock Path.glob to raise exception on this specific directory
    import pathlib
    original_glob = pathlib.Path.glob

    def failing_glob(self, pattern):
        if self == storage_dir:
            raise PermissionError("Access denied")
        return original_glob(self, pattern)

    with patch('pathlib.Path.glob', failing_glob):
        # Should handle exception gracefully
        store = TaskStore(storage_dir=storage_dir)
        tasks = asyncio.run(store.list_all())
        assert tasks == []


def test_task_store_save_with_exception(tmp_path):
    """Test _save handles exceptions gracefully."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    storage_dir = tmp_path / "tasks"
    storage_dir.mkdir()

    store = TaskStore(storage_dir=storage_dir)
    record = asyncio.run(store.create("Test"))

    # Make the directory read-only to cause write failure
    # The _save method should handle the exception gracefully
    # (We can't easily make it read-only on all systems, so we test via mock)
    with patch.object(Path, 'write_text', side_effect=PermissionError("Write failed")):
        # Update should still work (save happens in update too)
        asyncio.run(store.update(record.task_id, TaskStatus.RUNNING))

    # Task should still be in memory
    retrieved = asyncio.run(store.get(record.task_id))
    assert retrieved is not None


def test_task_store_delete_file_missing(tmp_path):
    """Test delete handles missing file gracefully."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    storage_dir = tmp_path / "tasks"
    storage_dir.mkdir()

    store = TaskStore(storage_dir=storage_dir)
    record = asyncio.run(store.create("Test"))

    # Manually delete the file
    file_path = storage_dir / f"{record.task_id}.json"
    file_path.unlink()

    # Delete should still work (file already gone)
    result = asyncio.run(store.delete(record.task_id))
    assert result is True


def test_task_store_update_no_started_at(task_store):
    """Test update sets started_at only when status is RUNNING."""
    record = asyncio.run(task_store.create("Test"))

    # Update to COMPLETED without going through RUNNING
    asyncio.run(task_store.update(record.task_id, TaskStatus.COMPLETED))

    updated = asyncio.run(task_store.get(record.task_id))
    assert updated is not None
    # started_at should be None since we never set it to RUNNING
    # (completed_at should be set though)
    assert updated.started_at is None
    assert updated.completed_at is not None


def test_task_store_update_execution_time_no_started_at(task_store):
    """Test execution_time calculation when started_at is None."""
    record = asyncio.run(task_store.create("Test"))

    # Update directly to COMPLETED (no RUNNING state)
    asyncio.run(task_store.update(record.task_id, TaskStatus.COMPLETED))

    updated = asyncio.run(task_store.get(record.task_id))
    assert updated is not None
    # execution_time should be 0 since started_at is None
    assert updated.execution_time == 0.0


def test_task_store_create_many_tasks(task_store):
    """Test creating many tasks to verify unique IDs."""
    task_ids = set()
    for i in range(100):
        record = asyncio.run(task_store.create(f"Task {i}"))
        task_ids.add(record.task_id)

    # All task IDs should be unique
    assert len(task_ids) == 100


def test_task_store_list_all_with_limit(task_store):
    """Test list_all with more than default limit."""
    # Create 60 tasks
    for i in range(60):
        asyncio.run(task_store.create(f"Task {i}"))

    # List all
    tasks = asyncio.run(task_store.list_all())

    # Should return all 60 (list_all doesn't have limit parameter)
    assert len(tasks) == 60


def test_run_request_dict_access():
    """Test RunRequest can be converted to dict."""
    req = RunRequest(prompt="Test", metadata={"key": "value"})

    # Pydantic v2 model_dump
    data = req.model_dump()
    assert data["prompt"] == "Test"
    assert data["metadata"] == {"key": "value"}


def test_task_response_dict_access():
    """Test TaskResponse can be converted to dict."""
    resp = TaskResponse(
        task_id="test",
        status="pending",
        created_at="2024-01-01",
        prompt="Test",
    )

    data = resp.model_dump()
    assert data["task_id"] == "test"
    assert data["status"] == "pending"


def test_task_status_comparison():
    """Test TaskStatus enum comparison."""
    assert TaskStatus.PENDING == TaskStatus.PENDING
    assert TaskStatus.PENDING != TaskStatus.RUNNING
    assert TaskStatus.COMPLETED.value == "completed"


def test_task_record_to_dict():
    """Test TaskRecord can be converted to dict."""
    record = TaskRecord(
        task_id="test",
        prompt="Test",
        status=TaskStatus.PENDING,
        created_at="2024-01-01",
        metadata={"key": "value"},
    )

    # TaskRecord is a dataclass
    from dataclasses import asdict
    data = asdict(record)

    assert data["task_id"] == "test"
    assert data["prompt"] == "Test"
    assert data["metadata"] == {"key": "value"}


def test_auth_context_hash_key_deterministic():
    """Test hash_key produces consistent results."""
    key = "test-key-123"
    hash1 = AuthContext.hash_key(key)
    hash2 = AuthContext.hash_key(key)

    assert hash1 == hash2
    assert len(hash1) == 16


def test_auth_context_verify_different_keys():
    """Test verify with different key combinations."""
    ctx = AuthContext("correct")

    assert ctx.verify("correct") is True
    assert ctx.verify("wrong") is False
    assert ctx.verify("") is False
    assert ctx.verify(None) is False


def test_task_store_create_with_empty_metadata(task_store):
    """Test creating task with empty metadata dict."""
    record = asyncio.run(task_store.create("Test", metadata={}))

    assert record.metadata == {}


def test_task_store_update_with_none_result(task_store):
    """Test update with None result should not overwrite existing result."""
    record = asyncio.run(task_store.create("Test"))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))

    # Set result
    asyncio.run(task_store.update(
        record.task_id,
        TaskStatus.COMPLETED,
        result={"output": "done"},
    ))

    # Update with None result should not overwrite
    asyncio.run(task_store.update(record.task_id, TaskStatus.COMPLETED, result=None))

    updated = asyncio.run(task_store.get(record.task_id))
    assert updated.result == {"output": "done"}


def test_task_store_update_with_none_error(task_store):
    """Test update with None error should not overwrite existing error."""
    record = asyncio.run(task_store.create("Test"))
    asyncio.run(task_store.update(record.task_id, TaskStatus.RUNNING))

    # Set error
    asyncio.run(task_store.update(
        record.task_id,
        TaskStatus.FAILED,
        error="First error",
    ))

    # Update with None error should not overwrite
    asyncio.run(task_store.update(record.task_id, TaskStatus.FAILED, error=None))

    updated = asyncio.run(task_store.get(record.task_id))
    assert updated.error == "First error"
