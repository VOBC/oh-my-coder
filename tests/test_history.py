"""
任务历史模块测试
"""

import json
import pytest
import tempfile
from pathlib import Path

from src.core.history import (
    HistoryManager,
    StepExecution,
    StepStatus,
    TaskCheckpoint,
    TaskHistory,
    TaskReplay,
    complete_step_execution,
    create_step_execution,
    fail_step_execution,
)


class TestStepExecution:
    """步骤执行测试"""

    def test_create_step(self):
        """测试创建步骤"""
        step = StepExecution(
            step_id="test_step_001",
            agent_name="Executor",
            description="生成代码",
            status=StepStatus.PENDING,
            input_context={"task": "实现登录功能"},
        )
        assert step.step_id == "test_step_001"
        assert step.agent_name == "Executor"
        assert step.status == StepStatus.PENDING
        assert step.tokens_used == 0

    def test_step_to_dict(self):
        """测试步骤序列化"""
        step = StepExecution(
            step_id="step_001",
            agent_name="Planner",
            description="制定计划",
            status=StepStatus.COMPLETED,
            input_context={},
            output={"plan": "step1, step2"},
            tokens_used=100,
        )
        data = step.to_dict()
        assert data["step_id"] == "step_001"
        assert data["status"] == "completed"
        assert data["tokens_used"] == 100

    def test_step_from_dict(self):
        """测试步骤反序列化"""
        data = {
            "step_id": "step_002",
            "agent_name": "Verifier",
            "description": "验证代码",
            "status": "running",
            "input_context": {},
            "tokens_used": 50,
        }
        step = StepExecution.from_dict(data)
        assert step.step_id == "step_002"
        assert step.status == StepStatus.RUNNING

    def test_complete_step(self):
        """测试完成步骤"""
        step = create_step_execution(
            agent_name="Executor",
            description="生成代码",
            input_context={"task": "test"},
        )
        complete_step_execution(
            step, output={"code": "print('hello')"}, tokens_used=200
        )
        assert step.status == StepStatus.COMPLETED
        assert step.output["code"] == "print('hello')"
        assert step.tokens_used == 200
        assert step.duration_seconds > 0

    def test_fail_step(self):
        """测试失败步骤"""
        step = create_step_execution(
            agent_name="Executor",
            description="生成代码",
            input_context={},
        )
        fail_step_execution(step, error="API 超时")
        assert step.status == StepStatus.FAILED
        assert step.error == "API 超时"


class TestTaskHistory:
    """任务历史测试"""

    def test_create_history(self):
        """测试创建历史记录"""
        history = TaskHistory(
            history_id="hist_001",
            task_description="实现用户登录功能",
            workflow_name="build",
        )
        assert history.history_id == "hist_001"
        assert history.workflow_name == "build"
        assert len(history.steps) == 0

    def test_add_step(self):
        """测试添加步骤"""
        history = TaskHistory(
            history_id="hist_002",
            task_description="测试任务",
            workflow_name="test",
        )
        step = StepExecution(
            step_id="s1",
            agent_name="Planner",
            description="规划",
            status=StepStatus.COMPLETED,
            input_context={},
            tokens_used=100,
        )
        history.add_step(step)
        assert len(history.steps) == 1
        assert history.steps[0].step_id == "s1"

    def test_update_totals(self):
        """测试更新总计"""
        history = TaskHistory(
            history_id="hist_003",
            task_description="测试",
            workflow_name="build",
        )
        history.add_step(
            StepExecution(
                step_id="s1",
                agent_name="A",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
                tokens_used=100,
                cost=0.01,
                duration_seconds=10,
            )
        )
        history.add_step(
            StepExecution(
                step_id="s2",
                agent_name="B",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
                tokens_used=200,
                cost=0.02,
                duration_seconds=20,
            )
        )
        history.update_totals()
        assert history.total_tokens == 300
        assert history.total_cost == 0.03
        assert history.total_duration == 30

    def test_get_failed_steps(self):
        """测试获取失败步骤"""
        history = TaskHistory(
            history_id="hist_004",
            task_description="测试",
            workflow_name="build",
        )
        history.add_step(
            StepExecution(
                step_id="s1",
                agent_name="A",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
            )
        )
        history.add_step(
            StepExecution(
                step_id="s2",
                agent_name="B",
                description="",
                status=StepStatus.FAILED,
                input_context={},
                error="超时",
            )
        )
        failed = history.get_failed_steps()
        assert len(failed) == 1
        assert failed[0].step_id == "s2"

    def test_history_serialization(self):
        """测试历史序列化"""
        history = TaskHistory(
            history_id="hist_005",
            task_description="序列化测试",
            workflow_name="build",
            tags=["test", "unit"],
        )
        history.add_step(
            StepExecution(
                step_id="s1",
                agent_name="Test",
                description="测试步骤",
                status=StepStatus.COMPLETED,
                input_context={},
                tokens_used=50,
            )
        )

        data = history.to_dict()
        restored = TaskHistory.from_dict(data)

        assert restored.history_id == history.history_id
        assert restored.task_description == history.task_description
        assert restored.tags == ["test", "unit"]
        assert len(restored.steps) == 1


class TestTaskCheckpoint:
    """检查点测试"""

    def test_create_checkpoint(self):
        """测试创建检查点"""
        history = TaskHistory(
            history_id="cp_001",
            task_description="检查点测试",
            workflow_name="build",
        )
        for i in range(5):
            history.add_step(
                StepExecution(
                    step_id=f"s{i}",
                    agent_name=f"Agent{i}",
                    description="",
                    status=StepStatus.COMPLETED,
                    input_context={},
                    output={"result": f"output{i}"},
                )
            )

        checkpoint = TaskCheckpoint(history, step_index=3)
        assert checkpoint.step_index == 3
        assert checkpoint.checkpoint_id is not None

    def test_get_resume_context(self):
        """测试获取恢复上下文"""
        history = TaskHistory(
            history_id="cp_002",
            task_description="恢复测试",
            workflow_name="build",
        )
        history.add_step(
            StepExecution(
                step_id="s0",
                agent_name="A",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
                output={"plan": "step1"},
            )
        )
        history.add_step(
            StepExecution(
                step_id="s1",
                agent_name="B",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
                output={"code": "print(1)"},
            )
        )

        checkpoint = TaskCheckpoint(history, step_index=2)
        context = checkpoint.get_resume_context()

        assert context["history_id"] == "cp_002"
        assert context["resume_from_index"] == 2
        assert "s0" in context["completed_outputs"]
        assert "s1" in context["completed_outputs"]


class TestTaskReplay:
    """回放测试"""

    def test_create_replay(self):
        """测试创建回放器"""
        history = TaskHistory(
            history_id="replay_001",
            task_description="回放测试",
            workflow_name="test",
        )
        for i in range(3):
            history.add_step(
                StepExecution(
                    step_id=f"s{i}",
                    agent_name=f"A{i}",
                    description=f"步骤{i}",
                    status=StepStatus.COMPLETED,
                    input_context={},
                    duration_seconds=1.0,
                )
            )

        replay = TaskReplay(history)
        assert replay.current_step_index == 0

    def test_get_progress(self):
        """测试获取进度"""
        history = TaskHistory(
            history_id="replay_002",
            task_description="进度测试",
            workflow_name="test",
        )
        for i in range(5):
            history.add_step(
                StepExecution(
                    step_id=f"s{i}",
                    agent_name=f"A{i}",
                    description="",
                    status=StepStatus.COMPLETED,
                    input_context={},
                    duration_seconds=0.1,
                )
            )

        replay = TaskReplay(history)
        replay.current_step_index = 2

        progress = replay.get_progress()
        assert progress["current_step"] == 2
        assert progress["total_steps"] == 5
        assert progress["progress_percent"] == 40.0

    def test_set_speed(self):
        """测试设置速度"""
        history = TaskHistory(
            history_id="replay_003",
            task_description="速度测试",
            workflow_name="test",
        )
        history.add_step(
            StepExecution(
                step_id="s1",
                agent_name="A",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
            )
        )

        replay = TaskReplay(history)
        replay.set_speed(2.0)
        assert replay.speed == 2.0

        replay.set_speed(0.1)
        assert replay.speed == 0.1

        replay.set_speed(20.0)
        assert replay.speed == 10.0  # 最大值


class TestHistoryManager:
    """历史管理器测试"""

    def test_create_history(self):
        """测试创建历史"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HistoryManager(Path(tmpdir))
            history = manager.create_history(
                task_description="测试任务",
                workflow_name="build",
                tags=["test"],
            )
            assert (
                history.history_id.startswith("hist-") or len(history.history_id) == 8
            )
            assert history.workflow_name == "build"

    def test_save_and_load(self):
        """测试保存和加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HistoryManager(Path(tmpdir))
            history = manager.create_history(
                task_description="持久化测试",
                workflow_name="test",
            )
            history.add_step(
                StepExecution(
                    step_id="s1",
                    agent_name="Test",
                    description="测试",
                    status=StepStatus.COMPLETED,
                    input_context={},
                    tokens_used=100,
                )
            )

            # 保存
            manager.save_history(history)

            # 加载
            loaded = manager.load_history(history.history_id)
            assert loaded is not None
            assert loaded.task_description == "持久化测试"
            assert len(loaded.steps) == 1

    def test_list_histories(self):
        """测试列出历史"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HistoryManager(Path(tmpdir))

            # 创建多条记录
            for i in range(5):
                h = manager.create_history(
                    task_description=f"任务{i}",
                    workflow_name="build" if i % 2 == 0 else "test",
                )
                manager.save_history(h)

            histories = manager.list_histories()
            assert len(histories) == 5

    def test_delete_history(self):
        """测试删除历史"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HistoryManager(Path(tmpdir))
            history = manager.create_history(
                task_description="待删除",
                workflow_name="test",
            )
            manager.save_history(history)

            # 删除
            manager.delete_history(history.history_id)

            # 确认已删除
            loaded = manager.load_history(history.history_id)
            assert loaded is None

    def test_get_stats(self):
        """测试获取统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HistoryManager(Path(tmpdir))

            # 创建一些历史记录
            for i in range(10):
                h = manager.create_history(
                    task_description=f"任务{i}",
                    workflow_name="build",
                )
                h.add_step(
                    StepExecution(
                        step_id=f"s{i}",
                        agent_name="A",
                        description="",
                        status=StepStatus.COMPLETED,
                        input_context={},
                        tokens_used=100,
                        cost=0.01,
                        duration_seconds=10,
                    )
                )
                manager.save_history(h)

            stats = manager.get_stats()
            assert stats["total_histories"] == 10
            assert stats["total_tokens"] == 1000
            assert abs(stats["total_cost"] - 0.1) < 0.01


class TestHelperFunctions:
    """辅助函数测试"""

    def test_create_step_execution(self):
        """测试创建步骤执行"""
        step = create_step_execution(
            agent_name="TestAgent",
            description="测试描述",
            input_context={"key": "value"},
        )
        assert step.agent_name == "TestAgent"
        assert step.status == StepStatus.PENDING
        assert step.input_context["key"] == "value"
        assert step.start_time is not None

    def test_complete_step_execution(self):
        """测试完成步骤"""
        step = create_step_execution("A", "test", {})
        result = complete_step_execution(
            step, {"output": "result"}, tokens_used=500, cost=0.05
        )
        assert result.status == StepStatus.COMPLETED
        assert result.tokens_used == 500
        assert result.cost == 0.05

    def test_fail_step_execution(self):
        """测试标记失败"""
        step = create_step_execution("A", "test", {})
        result = fail_step_execution(step, "Something went wrong")
        assert result.status == StepStatus.FAILED
        assert result.error == "Something went wrong"


class TestTaskCheckpointMissing:
    """TaskCheckpoint 缺失测试"""

    def test_can_resume_from(self):
        """测试是否可恢复"""
        history = TaskHistory(
            history_id="cp_003",
            task_description="恢复测试",
            workflow_name="test",
        )
        for i in range(5):
            history.add_step(
                StepExecution(
                    step_id=f"s{i}",
                    agent_name=f"A{i}",
                    description="",
                    status=StepStatus.COMPLETED,
                    input_context={},
                )
            )

        checkpoint = TaskCheckpoint(history, step_index=3)

        # step_index=3, 可以恢复 s2 (index=2 <= 3)
        assert checkpoint.can_resume_from("s2") is True

        # 不可以恢复 s4 (index=4 > 3)
        assert checkpoint.can_resume_from("s4") is False

        # 不存在的 step
        assert checkpoint.can_resume_from("nonexistent") is False

    def test_to_dict(self):
        """测试转换为字典"""
        history = TaskHistory(
            history_id="cp_004",
            task_description="字典测试",
            workflow_name="test",
        )
        checkpoint = TaskCheckpoint(history, step_index=2)

        data = checkpoint.to_dict()
        assert "checkpoint_id" in data
        assert data["history_id"] == "cp_004"
        assert data["step_index"] == 2
        assert "created_at" in data


class TestTaskReplayMissing:
    """TaskReplay 缺失测试"""

    @pytest.mark.asyncio
    async def test_replay_callbacks(self):
        """测试回放回调"""
        history = TaskHistory(
            history_id="replay_004",
            task_description="回调测试",
            workflow_name="test",
        )
        history.add_step(
            StepExecution(
                step_id="s1",
                agent_name="A",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
                duration_seconds=0.01,
            )
        )

        replay = TaskReplay(history)

        step_start_called = False
        step_complete_called = False
        replay_complete_called = False

        async def on_start(step, index):
            nonlocal step_start_called
            step_start_called = True

        async def on_complete(step, index):
            nonlocal step_complete_called
            step_complete_called = True

        async def on_complete_all():
            nonlocal replay_complete_called
            replay_complete_called = True

        replay.on_step_start(on_start)
        replay.on_step_complete(on_complete)
        replay.on_replay_complete(on_complete_all)

        await replay.replay()

        assert step_start_called is True
        assert step_complete_called is True
        assert replay_complete_called is True
        assert replay.status.value == "completed"

    def test_pause_and_resume(self):
        """测试暂停和恢复"""
        history = TaskHistory(
            history_id="replay_005",
            task_description="暂停测试",
            workflow_name="test",
        )
        history.add_step(
            StepExecution(
                step_id="s1",
                agent_name="A",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
            )
        )

        replay = TaskReplay(history)
        assert replay.status.value == "ready"

        replay.pause()
        assert replay.status.value == "paused"

        replay.resume()
        assert replay.status.value == "playing"

    def test_stop(self):
        """测试停止"""
        history = TaskHistory(
            history_id="replay_006",
            task_description="停止测试",
            workflow_name="test",
        )
        history.add_step(
            StepExecution(
                step_id="s1",
                agent_name="A",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
            )
        )

        replay = TaskReplay(history)
        replay.stop()
        assert replay.status.value == "failed"

    @pytest.mark.asyncio
    async def test_replay_step_by_step(self):
        """测试单步回放"""
        history = TaskHistory(
            history_id="replay_007",
            task_description="单步测试",
            workflow_name="test",
        )
        for i in range(3):
            history.add_step(
                StepExecution(
                    step_id=f"s{i}",
                    agent_name=f"A{i}",
                    description="",
                    status=StepStatus.COMPLETED,
                    input_context={},
                    duration_seconds=0.01,
                )
            )

        replay = TaskReplay(history)
        await replay.replay(step_by_step=True)

        # 只执行了第一步，然后暂停
        assert replay.status.value == "paused"
        assert replay.current_step_index == 1

    @pytest.mark.asyncio
    async def test_replay_stop_during_execution(self):
        """测试执行中停止"""
        history = TaskHistory(
            history_id="replay_009",
            task_description="停止测试",
            workflow_name="test",
        )
        for i in range(5):
            history.add_step(
                StepExecution(
                    step_id=f"s{i}",
                    agent_name=f"A{i}",
                    description="",
                    status=StepStatus.COMPLETED,
                    input_context={},
                    duration_seconds=0.01,
                )
            )

        replay = TaskReplay(history)

        async def on_start(step, index):
            # 执行第一步后停止
            if index == 1:
                replay.stop()

        replay.on_step_start(on_start)
        await replay.replay()

        # 应该停在第二步（index=1）
        assert replay.status.value == "failed"
        assert replay.current_step_index <= 2

    @pytest.mark.asyncio
    async def test_replay_from_middle(self):
        """测试从中间开始回放"""
        history = TaskHistory(
            history_id="replay_008",
            task_description="中间开始测试",
            workflow_name="test",
        )
        for i in range(5):
            history.add_step(
                StepExecution(
                    step_id=f"s{i}",
                    agent_name=f"A{i}",
                    description="",
                    status=StepStatus.COMPLETED,
                    input_context={},
                    duration_seconds=0.01,
                )
            )

        replay = TaskReplay(history)
        await replay.replay(start_from=2)

        assert replay.current_step_index == 5
        assert replay.status.value == "completed"


class TestHistoryManagerMissing:
    """HistoryManager 缺失测试"""

    def test_create_and_load_checkpoint(self):
        """测试创建和加载检查点"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HistoryManager(Path(tmpdir))
            history = manager.create_history(
                task_description="检查点测试",
                workflow_name="test",
            )
            for i in range(5):
                history.add_step(
                    StepExecution(
                        step_id=f"s{i}",
                        agent_name=f"A{i}",
                        description="",
                        status=StepStatus.COMPLETED,
                        input_context={},
                    )
                )
            manager.save_history(history)

            # 创建检查点
            checkpoint = manager.create_checkpoint(history, step_index=3)
            assert checkpoint.checkpoint_id is not None
            assert checkpoint.step_index == 3

            # 加载检查点
            loaded = manager.load_checkpoint(checkpoint.checkpoint_id)
            assert loaded is not None
            assert loaded.checkpoint_id == checkpoint.checkpoint_id
            assert loaded.step_index == 3

    def test_load_nonexistent_checkpoint(self):
        """测试加载不存在的检查点"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HistoryManager(Path(tmpdir))
            result = manager.load_checkpoint("nonexistent")
            assert result is None

    def test_load_checkpoint_with_invalid_history(self):
        """测试加载检查点但历史不存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HistoryManager(Path(tmpdir))

            # 手动创建一个检查点文件，但历史不存在
            checkpoint_file = Path(tmpdir) / "checkpoint_test123.json"
            checkpoint_data = {
                "checkpoint_id": "test123",
                "history_id": "nonexistent",
                "step_index": 0,
                "created_at": "2024-01-01T00:00:00",
            }
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoint_data, f)

            result = manager.load_checkpoint("test123")
            assert result is None

    def test_get_steps_by_agent(self):
        """测试按 Agent 获取步骤"""
        history = TaskHistory(
            history_id="hist_006",
            task_description="Agent 测试",
            workflow_name="test",
        )
        history.add_step(
            StepExecution(
                step_id="s1",
                agent_name="Planner",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
            )
        )
        history.add_step(
            StepExecution(
                step_id="s2",
                agent_name="Executor",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
            )
        )
        history.add_step(
            StepExecution(
                step_id="s3",
                agent_name="Planner",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
            )
        )

        planner_steps = history.get_steps_by_agent("Planner")
        assert len(planner_steps) == 2
        assert planner_steps[0].step_id == "s1"
        assert planner_steps[1].step_id == "s3"

    def test_get_step_by_id(self):
        """测试按 ID 获取步骤"""
        history = TaskHistory(
            history_id="hist_007",
            task_description="步骤 ID 测试",
            workflow_name="test",
        )
        history.add_step(
            StepExecution(
                step_id="target_step",
                agent_name="A",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
            )
        )

        step = history.get_step("target_step")
        assert step is not None
        assert step.step_id == "target_step"

        missing = history.get_step("nonexistent")
        assert missing is None

    def test_list_histories_with_tags(self):
        """测试按标签列出历史"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HistoryManager(Path(tmpdir))

            h1 = manager.create_history(
                task_description="任务1",
                workflow_name="build",
                tags=["python", "web"],
            )
            h2 = manager.create_history(
                task_description="任务2",
                workflow_name="test",
                tags=["python"],
            )
            h3 = manager.create_history(
                task_description="任务3",
                workflow_name="build",
                tags=["rust"],
            )

            manager.save_history(h1)
            manager.save_history(h2)
            manager.save_history(h3)

            # 按 python 标签过滤
            python_histories = manager.list_histories(tags=["python"])
            assert len(python_histories) == 2

            # 按 rust 标签过滤
            rust_histories = manager.list_histories(tags=["rust"])
            assert len(rust_histories) == 1

    def test_delete_and_verify(self):
        """测试删除后验证"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HistoryManager(Path(tmpdir))
            history = manager.create_history(
                task_description="待删除验证",
                workflow_name="test",
            )
            manager.save_history(history)

            # 删除
            result = manager.delete_history(history.history_id)
            assert result is True

            # 确认已删除
            loaded = manager.load_history(history.history_id)
            assert loaded is None

    def test_update_totals_auto_in_to_dict(self):
        """测试 to_dict 自动更新总计"""
        history = TaskHistory(
            history_id="hist_008",
            task_description="自动更新测试",
            workflow_name="test",
        )
        history.add_step(
            StepExecution(
                step_id="s1",
                agent_name="A",
                description="",
                status=StepStatus.COMPLETED,
                input_context={},
                tokens_used=100,
                cost=0.01,
                duration_seconds=10,
            )
        )

        data = history.to_dict()
        assert data["total_tokens"] == 100
        assert data["total_cost"] == 0.01
        assert data["total_duration"] == 10.0
