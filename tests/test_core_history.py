"""Tests for core/history.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.history import (
    HistoryManager,
    ReplayStatus,
    StepExecution,
    StepStatus,
    TaskCheckpoint,
    TaskHistory,
    TaskReplay,
    complete_step_execution,
    create_step_execution,
    fail_step_execution,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_step() -> StepExecution:
    """Create a sample step execution."""
    return StepExecution(
        step_id="step_001",
        agent_name="coder",
        description="Write code",
        status=StepStatus.COMPLETED,
        input_context={"task": "implement feature"},
        output={"files": ["main.py"]},
        start_time="2025-01-01T10:00:00",
        end_time="2025-01-01T10:05:00",
        duration_seconds=300.0,
        tokens_used=1000,
        cost=0.05,
        retry_count=0,
        metadata={"key": "val"},
    )


@pytest.fixture
def sample_history() -> TaskHistory:
    """Create a sample task history."""
    return TaskHistory(
        history_id="hist_001",
        task_description="Build feature X",
        workflow_name="dev_workflow",
        tags=["backend", "urgent"],
    )


@pytest.fixture
def sample_history_with_steps() -> TaskHistory:
    """Create a task history with steps."""
    steps = [
        StepExecution(
            step_id="step_001",
            agent_name="coder",
            description="Write code",
            status=StepStatus.COMPLETED,
            input_context={"task": "code"},
            output={"result": "done"},
            tokens_used=500,
            cost=0.02,
            duration_seconds=100.0,
        ),
        StepExecution(
            step_id="step_002",
            agent_name="tester",
            description="Run tests",
            status=StepStatus.FAILED,
            input_context={"task": "test"},
            error="test failure",
            tokens_used=300,
            cost=0.01,
            duration_seconds=50.0,
        ),
        StepExecution(
            step_id="step_003",
            agent_name="coder",
            description="Fix bug",
            status=StepStatus.PENDING,
            input_context={"task": "fix"},
            tokens_used=0,
            cost=0.0,
            duration_seconds=0.0,
        ),
    ]
    return TaskHistory(
        history_id="hist_002",
        task_description="Fix and test",
        workflow_name="dev_workflow",
        steps=steps,
    )


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    """Create a temporary storage directory."""
    return tmp_path / "history"


@pytest.fixture
def manager(tmp_storage: Path) -> HistoryManager:
    """Create a HistoryManager with temporary storage."""
    return HistoryManager(storage_dir=tmp_storage)


# ---------------------------------------------------------------------------
# StepStatus Enum
# ---------------------------------------------------------------------------

class TestStepStatus:
    def test_step_status_values(self) -> None:
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.SKIPPED.value == "skipped"


# ---------------------------------------------------------------------------
# ReplayStatus Enum
# ---------------------------------------------------------------------------

class TestReplayStatus:
    def test_replay_status_values(self) -> None:
        assert ReplayStatus.READY.value == "ready"
        assert ReplayStatus.PLAYING.value == "playing"
        assert ReplayStatus.PAUSED.value == "paused"
        assert ReplayStatus.COMPLETED.value == "completed"
        assert ReplayStatus.FAILED.value == "failed"


# ---------------------------------------------------------------------------
# StepExecution
# ---------------------------------------------------------------------------

class TestStepExecution:
    def test_creation_defaults(self) -> None:
        step = StepExecution(
            step_id="s1",
            agent_name="agent",
            description="desc",
            status=StepStatus.PENDING,
            input_context={},
        )
        assert step.step_id == "s1"
        assert step.output is None
        assert step.error is None
        assert step.start_time is None
        assert step.end_time is None
        assert step.duration_seconds == 0.0
        assert step.tokens_used == 0
        assert step.cost == 0.0
        assert step.retry_count == 0
        assert step.metadata == {}

    def test_to_dict(self, sample_step: StepExecution) -> None:
        result = sample_step.to_dict()
        assert result["step_id"] == "step_001"
        assert result["agent_name"] == "coder"
        assert result["status"] == "completed"
        assert result["output"] == {"files": ["main.py"]}
        assert result["error"] is None
        assert result["duration_seconds"] == 300.0
        assert result["tokens_used"] == 1000
        assert result["cost"] == 0.05
        assert result["metadata"] == {"key": "val"}

    def test_from_dict_full(self) -> None:
        data = {
            "step_id": "s1",
            "agent_name": "agent",
            "description": "desc",
            "status": "running",
            "input_context": {"k": "v"},
            "output": {"out": "val"},
            "error": None,
            "start_time": "2025-01-01T00:00:00",
            "end_time": "2025-01-01T00:01:00",
            "duration_seconds": 60.0,
            "tokens_used": 200,
            "cost": 0.03,
            "retry_count": 2,
            "metadata": {"a": 1},
        }
        step = StepExecution.from_dict(data)
        assert step.step_id == "s1"
        assert step.status == StepStatus.RUNNING
        assert step.retry_count == 2
        assert step.metadata == {"a": 1}

    def test_from_dict_minimal(self) -> None:
        data = {
            "step_id": "s1",
            "agent_name": "agent",
            "description": "desc",
            "status": "pending",
        }
        step = StepExecution.from_dict(data)
        assert step.input_context == {}
        assert step.output is None
        assert step.error is None
        assert step.duration_seconds == 0.0
        assert step.tokens_used == 0
        assert step.cost == 0.0
        assert step.retry_count == 0
        assert step.metadata == {}

    def test_roundtrip(self, sample_step: StepExecution) -> None:
        data = sample_step.to_dict()
        restored = StepExecution.from_dict(data)
        assert restored.step_id == sample_step.step_id
        assert restored.status == sample_step.status
        assert restored.duration_seconds == sample_step.duration_seconds
        assert restored.metadata == sample_step.metadata


# ---------------------------------------------------------------------------
# TaskHistory
# ---------------------------------------------------------------------------

class TestTaskHistory:
    def test_creation_defaults(self) -> None:
        h = TaskHistory(
            history_id="h1",
            task_description="desc",
            workflow_name="wf",
        )
        assert h.steps == []
        assert h.total_tokens == 0
        assert h.total_cost == 0.0
        assert h.total_duration == 0.0
        assert h.tags == []
        assert h.metadata == {}
        assert h.created_at is not None
        assert h.updated_at is not None

    def test_add_step(self, sample_history: TaskHistory) -> None:
        step = StepExecution(
            step_id="s1", agent_name="a", description="d",
            status=StepStatus.RUNNING, input_context={},
        )
        old_updated = sample_history.updated_at
        sample_history.add_step(step)
        assert len(sample_history.steps) == 1
        assert sample_history.steps[0].step_id == "s1"
        assert sample_history.updated_at != old_updated

    def test_update_totals(self, sample_history_with_steps: TaskHistory) -> None:
        sample_history_with_steps.update_totals()
        assert sample_history_with_steps.total_tokens == 800
        assert sample_history_with_steps.total_cost == pytest.approx(0.03)
        assert sample_history_with_steps.total_duration == pytest.approx(150.0)

    def test_update_totals_empty(self, sample_history: TaskHistory) -> None:
        sample_history.update_totals()
        assert sample_history.total_tokens == 0
        assert sample_history.total_cost == 0.0
        assert sample_history.total_duration == 0.0

    def test_to_dict(self, sample_history_with_steps: TaskHistory) -> None:
        result = sample_history_with_steps.to_dict()
        assert result["history_id"] == "hist_002"
        assert result["workflow_name"] == "dev_workflow"
        assert len(result["steps"]) == 3
        assert result["steps"][0]["status"] == "completed"
        # to_dict calls update_totals
        assert result["total_tokens"] == 800
        assert result["total_cost"] == pytest.approx(0.03)

    def test_from_dict(self, sample_history_with_steps: TaskHistory) -> None:
        data = sample_history_with_steps.to_dict()
        restored = TaskHistory.from_dict(data)
        assert restored.history_id == "hist_002"
        assert len(restored.steps) == 3
        assert restored.tags == []

    def test_from_dict_minimal(self) -> None:
        data = {
            "history_id": "h1",
            "task_description": "desc",
            "workflow_name": "wf",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        h = TaskHistory.from_dict(data)
        assert h.steps == []
        assert h.tags == []
        assert h.metadata == {}

    def test_get_step_found(self, sample_history_with_steps: TaskHistory) -> None:
        step = sample_history_with_steps.get_step("step_001")
        assert step is not None
        assert step.agent_name == "coder"

    def test_get_step_not_found(self, sample_history_with_steps: TaskHistory) -> None:
        step = sample_history_with_steps.get_step("nonexistent")
        assert step is None

    def test_get_steps_by_agent(self, sample_history_with_steps: TaskHistory) -> None:
        coder_steps = sample_history_with_steps.get_steps_by_agent("coder")
        assert len(coder_steps) == 2
        tester_steps = sample_history_with_steps.get_steps_by_agent("tester")
        assert len(tester_steps) == 1

    def test_get_steps_by_agent_no_match(self, sample_history_with_steps: TaskHistory) -> None:
        steps = sample_history_with_steps.get_steps_by_agent("nonexistent")
        assert steps == []

    def test_get_failed_steps(self, sample_history_with_steps: TaskHistory) -> None:
        failed = sample_history_with_steps.get_failed_steps()
        assert len(failed) == 1
        assert failed[0].step_id == "step_002"

    def test_get_failed_steps_none(self, sample_history: TaskHistory) -> None:
        failed = sample_history.get_failed_steps()
        assert failed == []


# ---------------------------------------------------------------------------
# TaskCheckpoint
# ---------------------------------------------------------------------------

class TestTaskCheckpoint:
    def test_creation(self, sample_history: TaskHistory) -> None:
        cp = TaskCheckpoint(sample_history, step_index=0)
        assert cp.history is sample_history
        assert cp.step_index == 0
        assert cp.checkpoint_id is not None
        assert cp.created_at is not None

    def test_can_resume_from_found_within(self, sample_history_with_steps: TaskHistory) -> None:
        cp = TaskCheckpoint(sample_history_with_steps, step_index=2)
        assert cp.can_resume_from("step_001") is True  # index 0 <= 2
        assert cp.can_resume_from("step_002") is True  # index 1 <= 2

    def test_can_resume_from_found_beyond(self, sample_history_with_steps: TaskHistory) -> None:
        cp = TaskCheckpoint(sample_history_with_steps, step_index=0)
        assert cp.can_resume_from("step_002") is False  # index 1 > 0

    def test_can_resume_from_not_found(self, sample_history_with_steps: TaskHistory) -> None:
        cp = TaskCheckpoint(sample_history_with_steps, step_index=0)
        assert cp.can_resume_from("nonexistent") is False

    def test_get_resume_context(self, sample_history_with_steps: TaskHistory) -> None:
        cp = TaskCheckpoint(sample_history_with_steps, step_index=2)
        ctx = cp.get_resume_context()
        assert ctx["history_id"] == "hist_002"
        assert ctx["resume_from_index"] == 2
        # step_001 has output, step_002 has no output (error)
        assert "step_001" in ctx["completed_outputs"]

    def test_get_resume_context_empty(self, sample_history: TaskHistory) -> None:
        cp = TaskCheckpoint(sample_history, step_index=0)
        ctx = cp.get_resume_context()
        assert ctx["completed_outputs"] == {}

    def test_to_dict(self, sample_history: TaskHistory) -> None:
        cp = TaskCheckpoint(sample_history, step_index=1)
        result = cp.to_dict()
        assert result["history_id"] == "hist_001"
        assert result["step_index"] == 1
        assert "checkpoint_id" in result
        assert "created_at" in result


# ---------------------------------------------------------------------------
# TaskReplay
# ---------------------------------------------------------------------------

class TestTaskReplay:
    @pytest.fixture
    def replay(self, sample_history_with_steps: TaskHistory) -> TaskReplay:
        return TaskReplay(sample_history_with_steps)

    def test_creation(self, sample_history_with_steps: TaskHistory) -> None:
        rp = TaskReplay(sample_history_with_steps)
        assert rp.status == ReplayStatus.READY
        assert rp.current_step_index == 0
        assert rp.speed == 1.0

    def test_register_callbacks(self, replay: TaskReplay) -> None:
        cb1 = MagicMock()
        cb2 = MagicMock()
        cb3 = MagicMock()
        replay.on_step_start(cb1)
        replay.on_step_complete(cb2)
        replay.on_replay_complete(cb3)
        assert replay._callbacks["step_start"] is cb1
        assert replay._callbacks["step_complete"] is cb2
        assert replay._callbacks["replay_complete"] is cb3

    @pytest.mark.asyncio
    async def test_replay_full(self, replay: TaskReplay) -> None:
        # Zero out durations to avoid actual sleeps
        for s in replay.history.steps:
            s.duration_seconds = 0.0

        await replay.replay()
        assert replay.status == ReplayStatus.COMPLETED
        assert replay.current_step_index == 3

    @pytest.mark.asyncio
    async def test_replay_step_by_step(self, replay: TaskReplay) -> None:
        for s in replay.history.steps:
            s.duration_seconds = 0.0

        await replay.replay(step_by_step=True)
        assert replay.status == ReplayStatus.PAUSED
        assert replay.current_step_index == 1

    @pytest.mark.asyncio
    async def test_replay_from_start(self, replay: TaskReplay) -> None:
        for s in replay.history.steps:
            s.duration_seconds = 0.0

        await replay.replay(start_from=1)
        assert replay.current_step_index == 3

    @pytest.mark.asyncio
    async def test_replay_callbacks(self, replay: TaskReplay) -> None:
        for s in replay.history.steps:
            s.duration_seconds = 0.0

        start_cb = AsyncMock()
        complete_cb = AsyncMock()
        done_cb = AsyncMock()
        replay.on_step_start(start_cb)
        replay.on_step_complete(complete_cb)
        replay.on_replay_complete(done_cb)

        await replay.replay()
        assert start_cb.call_count == 3
        assert complete_cb.call_count == 3
        assert done_cb.call_count == 1

    @pytest.mark.asyncio
    async def test_replay_paused_midway(self, replay: TaskReplay) -> None:
        for s in replay.history.steps:
            s.duration_seconds = 0.0

        # Pause after first step via step_start callback
        async def pause_on_second(step, index):
            if index == 1:
                replay.pause()

        replay.on_step_start(pause_on_second)
        await replay.replay()
        # Should stop after step at index 1 starts (paused check in loop)
        assert replay.status == ReplayStatus.PAUSED

    @pytest.mark.asyncio
    async def test_replay_stopped_midway(self, replay: TaskReplay) -> None:
        for s in replay.history.steps:
            s.duration_seconds = 0.0

        async def stop_on_first(step, index):
            if index == 0:
                replay.stop()

        replay.on_step_start(stop_on_first)
        await replay.replay()
        assert replay.status == ReplayStatus.FAILED

    def test_pause(self, replay: TaskReplay) -> None:
        replay.pause()
        assert replay.status == ReplayStatus.PAUSED

    def test_resume_from_paused(self, replay: TaskReplay) -> None:
        replay.pause()
        replay.resume()
        assert replay.status == ReplayStatus.PLAYING

    def test_resume_from_non_paused(self, replay: TaskReplay) -> None:
        replay.resume()  # not paused, should stay READY
        assert replay.status == ReplayStatus.READY

    def test_stop(self, replay: TaskReplay) -> None:
        replay.stop()
        assert replay.status == ReplayStatus.FAILED

    def test_set_speed(self, replay: TaskReplay) -> None:
        replay.set_speed(5.0)
        assert replay.speed == 5.0

    def test_set_speed_clamp_min(self, replay: TaskReplay) -> None:
        replay.set_speed(0.01)
        assert replay.speed == 0.1

    def test_set_speed_clamp_max(self, replay: TaskReplay) -> None:
        replay.set_speed(20.0)
        assert replay.speed == 10.0

    def test_get_progress(self, replay: TaskReplay) -> None:
        progress = replay.get_progress()
        assert progress["status"] == "ready"
        assert progress["current_step"] == 0
        assert progress["total_steps"] == 3
        assert progress["progress_percent"] == 0.0
        assert progress["speed"] == 1.0

    def test_get_progress_midway(self, replay: TaskReplay) -> None:
        replay.current_step_index = 2
        progress = replay.get_progress()
        assert progress["progress_percent"] == pytest.approx(200.0 / 3.0)

    @pytest.mark.asyncio
    async def test_replay_with_delay(self, sample_history_with_steps: TaskHistory) -> None:
        sample_history_with_steps.steps[0].duration_seconds = 0.01
        sample_history_with_steps.steps[1].duration_seconds = 0.0
        sample_history_with_steps.steps[2].duration_seconds = 0.0

        rp = TaskReplay(sample_history_with_steps)
        rp.set_speed(10.0)  # speed up
        with patch.object(rp, "_async_sleep", new_callable=AsyncMock) as mock_sleep:
            await rp.replay()
            mock_sleep.assert_called_once()
            # delay = 0.01 / 10.0 = 0.001
            mock_sleep.assert_called_with(0.001)

    @pytest.mark.asyncio
    async def test_replay_empty_history(self) -> None:
        h = TaskHistory(
            history_id="h_empty", task_description="empty",
            workflow_name="wf",
        )
        rp = TaskReplay(h)
        await rp.replay()
        assert rp.status == ReplayStatus.COMPLETED
        assert rp.current_step_index == 0

    @pytest.mark.asyncio
    async def test_replay_complete_callback_not_called_on_partial(
        self, replay: TaskReplay,
    ) -> None:
        for s in replay.history.steps:
            s.duration_seconds = 0.0

        done_cb = AsyncMock()
        replay.on_replay_complete(done_cb)
        await replay.replay(step_by_step=True)
        done_cb.assert_not_called()


# ---------------------------------------------------------------------------
# HistoryManager
# ---------------------------------------------------------------------------

class TestHistoryManager:
    def test_creation_default_dir(self) -> None:
        mgr = HistoryManager()
        assert mgr.storage_dir == Path(".omc/history")

    def test_creation_custom_dir(self, tmp_storage: Path) -> None:
        mgr = HistoryManager(storage_dir=tmp_storage)
        assert mgr.storage_dir == tmp_storage
        assert tmp_storage.exists()

    def test_create_history(self, manager: HistoryManager) -> None:
        h = manager.create_history("Build feature", "dev_workflow", tags=["backend"])
        assert h.task_description == "Build feature"
        assert h.workflow_name == "dev_workflow"
        assert h.tags == ["backend"]
        assert h.history_id in manager._histories

    def test_create_history_no_tags(self, manager: HistoryManager) -> None:
        h = manager.create_history("Build feature", "dev_workflow")
        assert h.tags == []

    def test_save_and_load_history(self, manager: HistoryManager, sample_history: TaskHistory) -> None:
        # Put in cache and save
        manager._histories[sample_history.history_id] = sample_history
        path = manager.save_history(sample_history)
        assert path.exists()

        # Load from disk (clear cache first)
        del manager._histories[sample_history.history_id]
        loaded = manager.load_history(sample_history.history_id)
        assert loaded is not None
        assert loaded.history_id == sample_history.history_id
        assert loaded.task_description == "Build feature X"

    def test_load_history_from_cache(self, manager: HistoryManager, sample_history: TaskHistory) -> None:
        manager._histories[sample_history.history_id] = sample_history
        loaded = manager.load_history(sample_history.history_id)
        assert loaded is sample_history

    def test_load_history_not_found(self, manager: HistoryManager) -> None:
        result = manager.load_history("nonexistent")
        assert result is None

    def test_list_histories(self, manager: HistoryManager) -> None:
        manager.create_history("Task 1", "wf1")
        manager.create_history("Task 2", "wf2")

        # Save to disk
        for h in manager._histories.values():
            manager.save_history(h)

        histories = manager.list_histories()
        assert len(histories) == 2

    def test_list_histories_with_tags(self, manager: HistoryManager) -> None:
        h1 = manager.create_history("Task 1", "wf1", tags=["backend"])
        h2 = manager.create_history("Task 2", "wf2", tags=["frontend"])
        manager.save_history(h1)
        manager.save_history(h2)

        # Clear cache to force disk load
        manager._histories.clear()

        result = manager.list_histories(tags=["backend"])
        assert len(result) == 1
        assert result[0].task_description == "Task 1"

    def test_list_histories_no_matching_tags(self, manager: HistoryManager) -> None:
        h1 = manager.create_history("Task 1", "wf1", tags=["backend"])
        manager.save_history(h1)
        manager._histories.clear()

        result = manager.list_histories(tags=["nonexistent"])
        assert result == []

    def test_list_histories_limit(self, manager: HistoryManager) -> None:
        for i in range(5):
            h = manager.create_history(f"Task {i}", "wf")
            manager.save_history(h)
        manager._histories.clear()

        result = manager.list_histories(limit=3)
        assert len(result) == 3

    def test_list_histories_handles_corrupt_file(self, manager: HistoryManager) -> None:
        # Write a corrupt JSON file
        corrupt_file = manager.storage_dir / "history_corrupt.json"
        corrupt_file.write_text("not valid json{{{")

        result = manager.list_histories()
        assert isinstance(result, list)  # Should not raise

    def test_create_checkpoint(self, manager: HistoryManager, sample_history: TaskHistory) -> None:
        manager._histories[sample_history.history_id] = sample_history
        manager.save_history(sample_history)

        cp = manager.create_checkpoint(sample_history, step_index=0)
        assert cp.history is sample_history
        assert cp.step_index == 0
        assert cp.checkpoint_id in manager._checkpoints

        # Check file was created
        cp_file = manager.storage_dir / f"checkpoint_{cp.checkpoint_id}.json"
        assert cp_file.exists()

    def test_load_checkpoint_from_cache(self, manager: HistoryManager, sample_history: TaskHistory) -> None:
        manager._histories[sample_history.history_id] = sample_history
        manager.save_history(sample_history)

        cp = manager.create_checkpoint(sample_history, step_index=1)
        loaded = manager.load_checkpoint(cp.checkpoint_id)
        assert loaded is cp

    def test_load_checkpoint_from_disk(self, manager: HistoryManager, sample_history: TaskHistory) -> None:
        manager._histories[sample_history.history_id] = sample_history
        manager.save_history(sample_history)

        cp = manager.create_checkpoint(sample_history, step_index=1)
        # Clear cache
        manager._checkpoints.clear()
        manager._histories.clear()

        loaded = manager.load_checkpoint(cp.checkpoint_id)
        assert loaded is not None
        assert loaded.step_index == 1

    def test_load_checkpoint_not_found(self, manager: HistoryManager) -> None:
        result = manager.load_checkpoint("nonexistent")
        assert result is None

    def test_load_checkpoint_missing_history(self, manager: HistoryManager) -> None:
        # Create a checkpoint file that references a non-existent history
        cp_file = manager.storage_dir / "checkpoint_ghost.json"
        cp_file.write_text(json.dumps({
            "checkpoint_id": "ghost",
            "history_id": "missing_hist",
            "step_index": 0,
            "created_at": "2025-01-01T00:00:00",
        }))

        result = manager.load_checkpoint("ghost")
        assert result is None

    def test_delete_history(self, manager: HistoryManager, sample_history: TaskHistory) -> None:
        manager.save_history(sample_history)
        assert (manager.storage_dir / f"history_{sample_history.history_id}.json").exists()

        result = manager.delete_history(sample_history.history_id)
        assert result is True
        assert not (manager.storage_dir / f"history_{sample_history.history_id}.json").exists()
        assert sample_history.history_id not in manager._histories

    def test_delete_history_not_on_disk(self, manager: HistoryManager) -> None:
        # Should still return True
        result = manager.delete_history("nonexistent")
        assert result is True

    def test_get_stats_empty(self, manager: HistoryManager) -> None:
        stats = manager.get_stats()
        assert stats["total_histories"] == 0
        assert stats["total_steps"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["total_duration_hours"] == 0.0
        assert stats["average_steps_per_task"] == 0

    def test_get_stats_with_data(self, manager: HistoryManager) -> None:
        h = manager.create_history("Task", "wf")
        step = StepExecution(
            step_id="s1", agent_name="a", description="d",
            status=StepStatus.COMPLETED, input_context={},
            tokens_used=100, cost=1.5, duration_seconds=3600.0,
        )
        h.add_step(step)
        h.update_totals()
        manager.save_history(h)

        stats = manager.get_stats()
        assert stats["total_histories"] == 1
        assert stats["total_steps"] == 1
        assert stats["total_tokens"] == 100
        assert stats["total_cost"] == 1.5
        assert stats["total_duration_hours"] == pytest.approx(1.0)
        assert stats["average_steps_per_task"] == 1.0


# ---------------------------------------------------------------------------
# Module-level functions
# ---------------------------------------------------------------------------

class TestCreateStepExecution:
    def test_create_step_execution(self) -> None:
        step = create_step_execution("coder", "Write code", {"task": "impl"})
        assert step.agent_name == "coder"
        assert step.description == "Write code"
        assert step.status == StepStatus.PENDING
        assert step.input_context == {"task": "impl"}
        assert step.start_time is not None
        assert step.step_id.startswith("coder_")

    def test_create_step_execution_has_unique_ids(self) -> None:
        s1 = create_step_execution("a", "d", {})
        s2 = create_step_execution("a", "d", {})
        assert s1.step_id != s2.step_id


class TestCompleteStepExecution:
    def test_complete_step(self) -> None:
        step = StepExecution(
            step_id="s1", agent_name="a", description="d",
            status=StepStatus.RUNNING, input_context={},
            start_time="2025-01-01T10:00:00",
        )
        result = complete_step_execution(step, {"output": "done"}, tokens_used=500, cost=0.02)
        assert result.status == StepStatus.COMPLETED
        assert result.output == {"output": "done"}
        assert result.end_time is not None
        assert result.tokens_used == 500
        assert result.cost == 0.02
        assert result.duration_seconds > 0

    def test_complete_step_no_start_time(self) -> None:
        step = StepExecution(
            step_id="s1", agent_name="a", description="d",
            status=StepStatus.RUNNING, input_context={},
            start_time=None,
        )
        result = complete_step_execution(step, {})
        assert result.duration_seconds == 0.0


class TestFailStepExecution:
    def test_fail_step(self) -> None:
        step = StepExecution(
            step_id="s1", agent_name="a", description="d",
            status=StepStatus.RUNNING, input_context={},
            start_time="2025-01-01T10:00:00",
        )
        result = fail_step_execution(step, "something broke")
        assert result.status == StepStatus.FAILED
        assert result.error == "something broke"
        assert result.end_time is not None
        assert result.duration_seconds > 0

    def test_fail_step_no_start_time(self) -> None:
        step = StepExecution(
            step_id="s1", agent_name="a", description="d",
            status=StepStatus.RUNNING, input_context={},
            start_time=None,
        )
        result = fail_step_execution(step, "error")
        assert result.duration_seconds == 0.0
