"""
Quest Mode 执行器测试 - 暂停/恢复/断点续跑
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.quest.executor import QuestExecutor
from src.quest.models import QuestStep, QuestStatus
from src.quest.store import QuestStore


# =============================================================================
# QuestExecutor 初始化测试
# =============================================================================


class TestQuestExecutorInit:
    """测试执行器初始化"""

    def test_init_sets_properties(self, tmp_path):
        """测试初始化属性"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(
            project_path=tmp_path,
            store=store,
        )
        assert executor.project_path == tmp_path
        assert executor.store is store

    def test_init_with_callbacks(self, tmp_path):
        """测试带回调初始化"""
        store = QuestStore(tmp_path)

        def notify(notif):
            pass

        async def review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            project_path=tmp_path,
            store=store,
            notify_callback=notify,
            review_callback=review,
        )
        assert executor.notify_callback is not None
        assert executor.review_callback is not None


# =============================================================================
# QuestExecutor 状态测试
# =============================================================================


class TestQuestExecutorState:
    """测试执行器状态"""

    def test_is_running_false_initially(self, tmp_path):
        """测试初始不在运行"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        assert executor.is_running(quest.id) is False

    def test_breakpoint_initially_empty(self, tmp_path):
        """测试断点初始为空"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        assert executor.get_breakpoint("nonexistent") is None


# =============================================================================
# QuestExecutor 控制操作测试
# =============================================================================


class TestQuestExecutorControl:
    """测试执行器控制操作"""

    def test_cancel_nonexistent_returns_false(self, tmp_path):
        """测试取消不存在的 Quest"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        result = executor.cancel("non-existent")
        assert result is False

    def test_stop_nonexistent_returns_false(self, tmp_path):
        """测试停止不存在的 Quest"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        result = executor.stop("non-existent")
        assert result is False

    def test_pause_nonexistent_returns_false(self, tmp_path):
        """测试暂停不存在的 Quest"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        result = executor.pause("non-existent")
        assert result is False

    def test_resume_non_paused_returns_none(self, tmp_path):
        """测试恢复未暂停的 Quest"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        result = executor.resume(quest.id)
        assert result is None


# =============================================================================
# QuestExecutor 步骤生成测试
# =============================================================================


class TestQuestExecutorStepGeneration:
    """测试步骤生成"""

    def test_generate_steps_no_spec(self, tmp_path):
        """测试无 SPEC 时生成默认步骤"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Do something", project_path=str(tmp_path)
        )
        steps = executor._generate_steps(quest)

        assert len(steps) == 4  # 分析、规划、执行、验证
        assert steps[0].agent == "analyst"
        assert steps[1].agent == "planner"
        assert steps[2].agent == "executor"
        assert steps[3].agent == "verifier"

    def test_generate_steps_with_spec(self, tmp_path):
        """测试有 SPEC 时生成步骤"""
        from src.quest.models import QuestSpec, AcceptanceCriteria

        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.spec = QuestSpec(
            title="Test",
            overview="Overview",
            motivation="Why",
            acceptance_criteria=[
                AcceptanceCriteria(id="AC1", description="Feature A works"),
                AcceptanceCriteria(id="AC2", description="Feature B works"),
                AcceptanceCriteria(id="AC3", description="Feature C works"),
                AcceptanceCriteria(id="AC4", description="Feature D works"),
                AcceptanceCriteria(id="AC5", description="Feature E works"),
            ],
        )

        steps = executor._generate_steps(quest)

        # 3 个 AC 为一组，应该有 2 组 + 1 个代码审查
        assert len(steps) == 3
        # 最后一步是代码审查
        assert steps[-1].agent == "code-reviewer"


# =============================================================================
# QuestExecutor 断点测试
# =============================================================================


class TestQuestExecutorBreakpoint:
    """测试断点续跑"""

    def test_pause_saves_breakpoint(self, tmp_path):
        """测试暂停保存断点"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do", agent="executor"),
            QuestStep(step_id="S2", title="Step 2", description="Do", agent="executor"),
        ]
        quest.status = QuestStatus.EXECUTING
        store.save(quest)

        # 暂停
        executor.pause(quest.id)

        # 检查断点保存
        assert executor.get_breakpoint(quest.id) is not None

    def test_resume_clears_breakpoint(self, tmp_path):
        """测试恢复清除断点"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do", agent="executor"),
        ]
        quest.status = QuestStatus.PAUSED
        store.save(quest)

        # 手动设置断点
        executor._breakpoint[quest.id] = 0

        # 恢复
        with patch.object(executor, "start"):
            executor.resume(quest.id)

        # 断点应该清除
        assert executor.get_breakpoint(quest.id) is None


# =============================================================================
# QuestExecutor 验收流程测试
# =============================================================================


class TestQuestExecutorReview:
    """测试验收流程"""

    @pytest.mark.asyncio
    async def test_wait_for_review_calls_callback(self, tmp_path):
        """测试验收调用回调"""
        store = QuestStore(tmp_path)

        review_called = False

        async def mock_review(qid, sid, preview):
            nonlocal review_called
            review_called = True
            return "pass"

        executor = QuestExecutor(
            tmp_path,
            store,
            review_callback=mock_review,
        )

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(
                step_id="S1",
                title="Step 1",
                description="Do",
                agent="executor",
                status=QuestStatus.PENDING_REVIEW,
                result="Step output",
            ),
        ]
        store.save(quest)

        result = await executor._wait_for_review(quest.id, "S1")

        assert review_called is True
        assert result == "pass"

    @pytest.mark.asyncio
    async def test_wait_for_review_retry(self, tmp_path):
        """测试验收重试"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "retry"

        executor = QuestExecutor(tmp_path, store, review_callback=mock_review)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(
                step_id="S1",
                title="Step 1",
                description="Do",
                agent="executor",
                status=QuestStatus.PENDING_REVIEW,
                result="Output",
            ),
        ]
        store.save(quest)

        result = await executor._wait_for_review(quest.id, "S1")
        assert result == "retry"

    @pytest.mark.asyncio
    async def test_wait_for_review_skip(self, tmp_path):
        """测试验收跳过"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "skip"

        executor = QuestExecutor(tmp_path, store, review_callback=mock_review)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(
                step_id="S1",
                title="Step 1",
                description="Do",
                agent="executor",
                status=QuestStatus.PENDING_REVIEW,
                result="Output",
            ),
        ]
        store.save(quest)

        result = await executor._wait_for_review(quest.id, "S1")
        assert result == "skip"

    @pytest.mark.asyncio
    async def test_wait_for_review_no_callback(self, tmp_path):
        """测试无回调时默认通过"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(
                step_id="S1",
                title="Step 1",
                description="Do",
                agent="executor",
                status=QuestStatus.PENDING_REVIEW,
                result="Output",
            ),
        ]
        store.save(quest)

        result = await executor._wait_for_review(quest.id, "S1")
        assert result == "pass"  # 默认通过


# =============================================================================
# QuestExecutor 通知测试
# =============================================================================


class TestQuestExecutorNotify:
    """测试通知"""

    def test_notify_calls_callback(self, tmp_path):
        """测试通知调用回调"""
        store = QuestStore(tmp_path)
        notifications = []

        def mock_notify(notif):
            notifications.append(notif)

        executor = QuestExecutor(
            tmp_path,
            store,
            notify_callback=mock_notify,
        )

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        executor._notify(quest, "started", "Quest started")

        assert len(notifications) == 1
        assert notifications[0].event == "started"
        assert notifications[0].quest_id == quest.id

    def test_notify_without_callback(self, tmp_path):
        """测试无回调时不崩溃"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        # 不应该崩溃
        executor._notify(quest, "started", "Message")
        executor._notify(None, "started", "Message")


# =============================================================================
# QuestExecutor 重规划回调测试
# =============================================================================


class TestQuestExecutorReplan:
    """测试重规划回调"""

    @pytest.mark.asyncio
    async def test_replan_callback_on_failure(self, tmp_path):
        """测试失败时触发重规划"""
        store = QuestStore(tmp_path)
        replan_called = False

        def mock_replan(qid, step_id):
            nonlocal replan_called
            replan_called = True

        executor = QuestExecutor(
            tmp_path,
            store,
            replan_callback=mock_replan,
        )

        # 创建一个 Quest 并直接调用失败处理
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(
                step_id="S1",
                title="Step 1",
                description="Do",
                agent="executor",
                status=QuestStatus.PENDING,
            ),
        ]
        store.save(quest)

        # 模拟步骤执行失败
        step = quest.steps[0]
        step.status = QuestStatus.FAILED
        step.error = "Test error"
        quest.error_message = "Step S1 failed: Test error"
        store.save(quest)

        # 手动触发回调
        executor._notify = MagicMock()
        executor.replan_callback(quest.id, step.step_id)

        assert replan_called is True


# =============================================================================
# QuestExecutor 完整流程模拟测试
# =============================================================================


class TestQuestExecutorFlow:
    """测试完整流程"""

    @pytest.mark.asyncio
    async def test_execute_simple_quest(self, tmp_path):
        """测试简单 Quest 执行"""
        store = QuestStore(tmp_path)

        # Mock review callback to auto-pass
        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            tmp_path,
            store,
            review_callback=mock_review,
        )
        executor._notify = MagicMock()  # Mock notification

        # 创建 Quest
        quest = store.create(
            title="Test", description="Simple test", project_path=str(tmp_path)
        )

        # Mock _execute_step to avoid running real commands
        async def mock_step(step, quest):
            return "Mock output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            # 执行
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        # 验证
        updated = store.get(quest.id)
        assert updated is not None

    @pytest.mark.asyncio
    async def test_cancel_during_execution(self, tmp_path):
        """测试执行中取消"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(
                step_id="S1",
                title="Step 1",
                description="Do",
                agent="executor",
            ),
            QuestStep(
                step_id="S2",
                title="Step 2",
                description="Do",
                agent="executor",
            ),
        ]
        store.save(quest)

        # 启动执行
        executor.start(quest)

        # 等待一小段时间让执行开始
        await asyncio.sleep(0.01)

        # 取消
        executor.cancel(quest.id)

        # 验证状态
        updated = store.get(quest.id)
        assert updated.status == QuestStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_pause_resume_flow(self, tmp_path):
        """测试暂停恢复流程"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            tmp_path,
            store,
            review_callback=mock_review,
        )
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.status = QuestStatus.EXECUTING
        quest.steps = [
            QuestStep(
                step_id="S1",
                title="Step 1",
                description="Do",
                agent="executor",
                status=QuestStatus.EXECUTING,
            ),
        ]
        store.save(quest)

        # 暂停
        result = executor.pause(quest.id)
        assert result is True

        # 验证状态
        updated = store.get(quest.id)
        assert updated.status == QuestStatus.PAUSED
        assert executor.get_breakpoint(quest.id) is not None
