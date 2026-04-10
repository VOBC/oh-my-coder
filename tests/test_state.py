"""
测试任务状态管理模块
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.state.task_state import (
    TaskState,
    TaskStatus,
    StepRecord,
    TaskStore,
    create_task,
    get_task,
    list_tasks,
    pause_task,
    resume_task,
    delete_task,
)


class TestTaskState:
    """TaskState 模型测试"""

    def test_init_defaults(self) -> None:
        state = TaskState(task_id="test-123")
        assert state.task_id == "test-123"
        assert state.status == TaskStatus.PENDING
        assert state.progress == 0.0
        assert state.steps == []
        assert state.created_at != ""

    def test_add_step(self) -> None:
        state = TaskState(task_id="test-123")
        state.add_step("分析需求", "已完成需求分析")
        state.add_step("编写代码", None)

        assert len(state.steps) == 2
        assert state.current_step == "编写代码"
        assert state.steps[0].step == "分析需求"
        assert state.steps[0].result == "已完成需求分析"
        assert state.steps[1].result is None
        assert state.steps[0].timestamp != ""

    def test_pause_resume(self) -> None:
        state = TaskState(task_id="test-123")
        state.status = TaskStatus.RUNNING

        state.pause()
        assert state.status == TaskStatus.PAUSED

        state.resume()
        assert state.status == TaskStatus.RUNNING

    def test_complete(self) -> None:
        state = TaskState(task_id="test-123")
        state.add_step("完成", "result")
        state.complete("final result")

        assert state.status == TaskStatus.COMPLETED
        assert state.progress == 1.0
        assert state.artifacts.get("result") == "final result"

    def test_fail(self) -> None:
        state = TaskState(task_id="test-123")
        state.fail("网络超时")

        assert state.status == TaskStatus.FAILED
        assert state.error == "网络超时"

    def test_set_progress(self) -> None:
        state = TaskState(task_id="test-123")
        state.set_progress(0.5)
        assert state.progress == 0.5

        # 边界值
        state.set_progress(1.5)
        assert state.progress == 1.0

        state.set_progress(-0.1)
        assert state.progress == 0.0

    def test_to_dict_from_dict(self) -> None:
        state = TaskState(task_id="test-123", status=TaskStatus.RUNNING)
        state.add_step("step1", "result1")
        state.set_progress(0.3)

        data = state.to_dict()
        restored = TaskState.from_dict(data)

        assert restored.task_id == "test-123"
        assert restored.status == TaskStatus.RUNNING
        assert restored.progress == 0.3
        assert len(restored.steps) == 1
        assert restored.steps[0].step == "step1"

    def test_invalid_status_fallback(self) -> None:
        data = {"task_id": "t", "status": "invalid_status"}
        state = TaskState.from_dict(data)
        assert state.status == TaskStatus.PENDING


class TestStepRecord:
    """StepRecord 测试"""

    def test_init_auto_timestamp(self) -> None:
        record = StepRecord(step="test")
        assert record.timestamp != ""
        assert record.step == "test"
        assert record.result is None

    def test_to_dict_from_dict(self) -> None:
        record = StepRecord(step="分析", result="done", duration=1.5)
        data = record.to_dict()
        restored = StepRecord.from_dict(data)

        assert restored.step == "分析"
        assert restored.result == "done"
        assert restored.duration == 1.5


class TestTaskStore:
    """TaskStore 持久化测试"""

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(base_dir=Path(tmpdir))

            state = TaskState(task_id="store-test")
            state.add_step("step1", "result1")
            state.set_progress(0.5)

            store.save(state)

            loaded = store.load("store-test")
            assert loaded is not None
            assert loaded.task_id == "store-test"
            assert loaded.progress == 0.5
            assert len(loaded.steps) == 1

    def test_load_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(base_dir=Path(tmpdir))
            assert store.load("nonexistent") is None

    def test_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(base_dir=Path(tmpdir))

            state = TaskState(task_id="delete-me")
            store.save(state)
            assert store.load("delete-me") is not None

            assert store.delete("delete-me") is True
            assert store.load("delete-me") is None

            # 删除不存在的文件
            assert store.delete("nonexistent") is False

    def test_list_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(base_dir=Path(tmpdir))

            for i in range(3):
                state = TaskState(task_id=f"task-{i}")
                store.save(state)

            all_tasks = store.list_all()
            assert len(all_tasks) == 3

    def test_list_by_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(base_dir=Path(tmpdir))

            state1 = TaskState(task_id="running")
            state1.status = TaskStatus.RUNNING
            store.save(state1)

            state2 = TaskState(task_id="paused")
            state2.status = TaskStatus.PAUSED
            store.save(state2)

            state3 = TaskState(task_id="completed")
            state3.status = TaskStatus.COMPLETED
            store.save(state3)

            running = store.list_by_status(TaskStatus.RUNNING)
            assert len(running) == 1
            assert running[0].task_id == "running"

    def test_json_corruption_handling(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(base_dir=Path(tmpdir))
            task_file = Path(tmpdir) / "corrupt.json"
            task_file.write_text("{ invalid json }", encoding="utf-8")

            # 应该不抛异常，返回 None
            assert store.load("corrupt") is None


class TestConvenienceFunctions:
    """便捷函数测试（使用临时目录）"""

    def test_create_and_get_task(self) -> None:
        # 使用临时目录避免污染真实数据
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(base_dir=Path(tmpdir))
            TaskStore._instance = store  # 替换单例

            try:
                state = create_task("conv-test", {"source": "test"})
                assert state.task_id == "conv-test"

                loaded = get_task("conv-test")
                assert loaded is not None
                assert loaded.metadata["source"] == "test"
            finally:
                TaskStore._instance = None

    def test_pause_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(base_dir=Path(tmpdir))
            TaskStore._instance = store

            try:
                create_task("pause-test")
                assert pause_task("pause-test") is True

                state = get_task("pause-test")
                assert state is not None
                assert state.status == TaskStatus.PAUSED

                assert resume_task("pause-test") is True
                state2 = get_task("pause-test")
                assert state2 is not None
                assert state2.status == TaskStatus.RUNNING
            finally:
                TaskStore._instance = None

    def test_delete_convenience(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(base_dir=Path(tmpdir))
            TaskStore._instance = store

            try:
                create_task("del-test")
                assert delete_task("del-test") is True
                assert get_task("del-test") is None
                assert delete_task("nonexistent") is False
            finally:
                TaskStore._instance = None

    def test_list_tasks_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaskStore(base_dir=Path(tmpdir))
            TaskStore._instance = store

            try:
                tasks = list_tasks()
                assert tasks == []
            finally:
                TaskStore._instance = None
