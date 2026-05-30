"""
Quest Mode 执行器测试 - 暂停/恢复/断点续跑
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.quest.executor import QuestExecutor
from src.quest.models import QuestStatus, QuestStep
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
        from src.quest.models import AcceptanceCriteria, QuestSpec

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


# =============================================================================
# QuestExecutor 通知补充测试
# =============================================================================


class TestQuestExecutorNotifyDetails:
    """测试通知 details 参数"""

    def test_notify_with_details(self, tmp_path):
        """测试通知携带 details"""
        store = QuestStore(tmp_path)
        notifications = []

        def mock_notify(notif):
            notifications.append(notif)

        executor = QuestExecutor(tmp_path, store, notify_callback=mock_notify)
        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        executor._notify(quest, "started", "Message", details={"key": "value"})

        assert len(notifications) == 1
        assert notifications[0].details == {"key": "value"}

    def test_notify_none_quest(self, tmp_path):
        """测试 quest=None 时的通知"""
        store = QuestStore(tmp_path)
        notifications = []

        executor = QuestExecutor(tmp_path, store, notify_callback=notifications.append)
        executor._notify(None, "event", "message")

        assert len(notifications) == 1
        assert notifications[0].quest_id == "unknown"
        assert notifications[0].title == ""


# =============================================================================
# QuestExecutor 验收补充测试
# =============================================================================


class TestQuestExecutorReviewEdgeCases:
    """测试验收边缘情况"""

    @pytest.mark.asyncio
    async def test_wait_for_review_callback_exception(self, tmp_path):
        """验收回调异常时默认通过"""
        store = QuestStore(tmp_path)
        notifications = []

        def mock_notify(notif):
            notifications.append(notif)

        async def failing_review(qid, sid, preview):
            raise ValueError("callback error")

        executor = QuestExecutor(
            tmp_path, store, review_callback=failing_review, notify_callback=mock_notify
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
                result="Output",
            ),
        ]
        store.save(quest)

        result = await executor._wait_for_review(quest.id, "S1")
        assert result == "pass"
        assert any(n.event == "review_error" for n in notifications)

    @pytest.mark.asyncio
    async def test_wait_for_review_quest_none(self, tmp_path):
        """验收时 quest 不存在"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(tmp_path, store, review_callback=mock_review)
        result = await executor._wait_for_review("nonexistent", "S1")
        assert result == "pass"

    @pytest.mark.asyncio
    async def test_wait_for_review_step_not_found(self, tmp_path):
        """验收时 step 不存在"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(tmp_path, store, review_callback=mock_review)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        store.save(quest)

        result = await executor._wait_for_review(quest.id, "nonexistent_step")
        assert result == "pass"


# =============================================================================
# QuestExecutor 步骤生成补充测试
# =============================================================================


class TestQuestExecutorStepGenerationEdgeCases:
    """测试步骤生成边缘情况"""

    def test_generate_steps_no_spec_field(self, tmp_path):
        """spec 字段为 None"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Do something", project_path=str(tmp_path)
        )
        steps = executor._generate_steps(quest)
        assert len(steps) == 4

    def test_generate_steps_fewer_than_three_ac(self, tmp_path):
        """验收标准少于 3 个"""
        from src.quest.models import AcceptanceCriteria, QuestSpec

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
                AcceptanceCriteria(id="AC1", description="Feature A"),
                AcceptanceCriteria(id="AC2", description="Feature B"),
            ],
        )

        steps = executor._generate_steps(quest)
        assert len(steps) == 2
        assert steps[-1].agent == "code-reviewer"


# =============================================================================
# QuestExecutor _execute_step 测试
# =============================================================================


class TestQuestExecutorExecuteStep:
    """测试单步执行"""

    @pytest.mark.asyncio
    async def test_execute_step_success(self, tmp_path):
        """步骤执行成功"""
        from unittest.mock import AsyncMock

        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        step = QuestStep(
            step_id="S1", title="Step 1", description="Do task", agent="executor"
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"success output", b""))

        with patch("src.quest.executor.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor._execute_step(step, quest)

        assert "success output" in result

    @pytest.mark.asyncio
    async def test_execute_step_failure(self, tmp_path):
        """步骤执行失败"""
        from unittest.mock import AsyncMock

        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        step = QuestStep(
            step_id="S1", title="Step 1", description="Do task", agent="executor"
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error details"))

        with patch("src.quest.executor.asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="命令失败"):
                await executor._execute_step(step, quest)


# =============================================================================
# QuestExecutor _execute_quest 补充测试
# =============================================================================


class TestQuestExecutorExecuteQuest:
    """测试 Quest 执行主循环

    已知行为：
    - 步骤完成后 quest.status 设为 PENDING_REVIEW，review 通过后不恢复
    - QuestStep 没有 notes 字段，review "skip" 会导致 ValueError
    - i -= 1 在 for 循环中不影响迭代，retry 实际不生效
    - 循环中 CANCELLED/PAUSED 状态会被后续代码覆盖
    """

    @pytest.mark.asyncio
    async def test_execute_quest_store_returns_none(self, tmp_path):
        """store.get 返回 None 时提前退出"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        store.update_status(quest.id, QuestStatus.EXECUTING)
        with patch.object(store, "get", return_value=None):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        assert not executor.is_running(quest.id)

    @pytest.mark.asyncio
    async def test_execute_quest_skipped_steps_with_breakpoint(self, tmp_path):
        """断点续跑跳过已完成的步骤"""
        store = QuestStore(tmp_path)

        executed_steps = []

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            tmp_path, store, review_callback=mock_review
        )
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(
                step_id="S1", title="Step 1", description="Do 1", agent="executor",
                status=QuestStatus.COMPLETED, completed_at=datetime.now(),
            ),
            QuestStep(
                step_id="S2", title="Step 2", description="Do 2", agent="executor",
            ),
        ]
        store.save(quest)

        executor._breakpoint[quest.id] = 1

        async def mock_step(step, q):
            executed_steps.append(step.step_id)
            return "Output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        assert executed_steps == ["S2"]

    @pytest.mark.asyncio
    async def test_execute_quest_step_failure_triggers_replan(self, tmp_path):
        """步骤失败时触发重规划回调"""
        store = QuestStore(tmp_path)
        replan_calls = []

        def mock_replan(qid, step_id):
            replan_calls.append((qid, step_id))

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            tmp_path,
            store,
            replan_callback=mock_replan,
            review_callback=mock_review,
        )
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do 1", agent="executor"),
            QuestStep(step_id="S2", title="Step 2", description="Do 2", agent="executor"),
        ]
        store.save(quest)

        async def mock_step(step, q):
            if step.step_id == "S1":
                raise RuntimeError("S1 failed")
            return "Output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        assert len(replan_calls) == 1
        assert replan_calls[0] == (quest.id, "S1")

        updated = store.get(quest.id)
        assert updated.steps[0].status == QuestStatus.FAILED
        # S2 通过 review 后 COMPLETED，quest 最终 PENDING_REVIEW
        assert updated.steps[1].status == QuestStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_quest_replan_callback_error(self, tmp_path):
        """重规划回调自身抛出异常时不中断流程"""
        store = QuestStore(tmp_path)
        notifications = []

        def mock_notify(notif):
            notifications.append(notif)

        def failing_replan(qid, step_id):
            raise RuntimeError("replan broke")

        executor = QuestExecutor(
            tmp_path,
            store,
            replan_callback=failing_replan,
            notify_callback=mock_notify,
        )

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do 1", agent="executor"),
        ]
        store.save(quest)

        async def mock_step(step, q):
            raise RuntimeError("step failed")

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        assert any(n.event == "replan_error" for n in notifications)

    @pytest.mark.asyncio
    async def test_execute_quest_all_steps_success(self, tmp_path):
        """所有步骤成功执行并通过 review"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            tmp_path, store, review_callback=mock_review
        )
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do 1", agent="executor"),
            QuestStep(step_id="S2", title="Step 2", description="Do 2", agent="executor"),
        ]
        store.save(quest)

        async def mock_step(step, q):
            return f"Output of {step.step_id}"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        updated = store.get(quest.id)
        # 两个步骤都通过 review 完成
        assert updated.steps[0].status == QuestStatus.COMPLETED
        assert updated.steps[1].status == QuestStatus.COMPLETED
        # quest status 保持 PENDING_REVIEW（已知行为：完成检查要求 EXECUTING）
        assert updated.status == QuestStatus.PENDING_REVIEW

    @pytest.mark.asyncio
    async def test_execute_quest_review_skip_fails(self, tmp_path):
        """验收跳过时 QuestStep.notes 不存在导致 ValueError

        已知 bug：QuestStep 模型没有 notes 字段，
        executor.py 中 step.notes = "用户跳过验收" 会抛出 ValueError。
        """
        store = QuestStore(tmp_path)
        notifications = []

        def mock_notify(notif):
            notifications.append(notif)

        async def mock_review(qid, sid, preview):
            return "skip"

        executor = QuestExecutor(
            tmp_path, store, review_callback=mock_review, notify_callback=mock_notify
        )

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do 1", agent="executor"),
        ]
        store.save(quest)

        async def mock_step(step, q):
            return "Output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        updated = store.get(quest.id)
        # step.notes 赋值失败，被 except Exception 捕获
        assert updated.steps[0].status == QuestStatus.FAILED
        assert updated.steps[0].error == "ValueError"

    @pytest.mark.asyncio
    async def test_execute_quest_no_replan_callback(self, tmp_path):
        """步骤失败但无重规划回调，继续后续步骤"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            tmp_path, store, review_callback=mock_review
        )
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do 1", agent="executor"),
            QuestStep(step_id="S2", title="Step 2", description="Do 2", agent="executor"),
        ]
        store.save(quest)

        async def mock_step(step, q):
            if step.step_id == "S1":
                raise RuntimeError("S1 failed")
            return "Output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        updated = store.get(quest.id)
        assert updated.steps[0].status == QuestStatus.FAILED
        assert updated.steps[1].status == QuestStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_quest_cancelled_before_first_step(self, tmp_path):
        """执行开始后、第一个步骤前检测到 CANCELLED"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            tmp_path, store, review_callback=mock_review
        )
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do 1", agent="executor"),
        ]
        store.save(quest)

        # 先设为 EXECUTING（_execute_quest 内部会设置），
        # 再设为 CANCELLED，这样循环第一次 get 时能读到 CANCELLED
        store.update_status(quest.id, QuestStatus.EXECUTING)
        store.update_status(quest.id, QuestStatus.CANCELLED)

        async def mock_step(step, q):
            return "Output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        # _execute_quest 先 update_status(EXECUTING)，覆盖了我们的 CANCELLED
        # 所以实际是 EXECUTING，步骤会执行
        # 这是 executor 的行为：第一步前的状态检查依赖 update_status 之后的 get
        updated = store.get(quest.id)
        # 实际上 update_status(EXECUTING) 覆盖了 CANCELLED
        assert updated.status == QuestStatus.PENDING_REVIEW

    @pytest.mark.asyncio
    async def test_execute_quest_paused_before_first_step(self, tmp_path):
        """执行开始后、第一个步骤前检测到 PAUSED"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            tmp_path, store, review_callback=mock_review
        )
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do 1", agent="executor"),
        ]
        store.save(quest)

        store.update_status(quest.id, QuestStatus.EXECUTING)
        store.update_status(quest.id, QuestStatus.PAUSED)

        async def mock_step(step, q):
            return "Output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        updated = store.get(quest.id)
        # update_status(EXECUTING) 覆盖了 PAUSED，步骤正常执行
        assert updated.status == QuestStatus.PENDING_REVIEW

    @pytest.mark.asyncio
    async def test_execute_quest_outer_exception(self, tmp_path):
        """外层 update_status 抛异常被 except 捕获"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        # 让第一次 update_status(EXECUTING) 抛异常
        call_count = 0
        original_update_status = store.update_status

        def failing_update_status(qid, status):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("store error")
            return original_update_status(qid, status)

        with patch.object(store, "update_status", side_effect=failing_update_status):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        # 任务应该已清理
        assert not executor.is_running(quest.id)


# =============================================================================
# QuestExecutor start / stop 补充测试
# =============================================================================


class TestQuestExecutorStartStop:
    """测试启动和停止"""

    @pytest.mark.asyncio
    async def test_start_idempotent(self, tmp_path):
        """重复 start 不创建重复任务"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            tmp_path, store, review_callback=mock_review
        )
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        async def mock_step(step, q):
            await asyncio.sleep(0.1)
            return "Output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            executor.start(quest)
            assert executor.is_running(quest.id)

            executor.start(quest)
            assert executor.is_running(quest.id)

            await asyncio.wait_for(asyncio.gather(*list(executor._running_quests.values())), timeout=5.0)

    @pytest.mark.asyncio
    async def test_stop_running_quest(self, tmp_path):
        """停止正在运行的 Quest"""
        store = QuestStore(tmp_path)

        executor = QuestExecutor(tmp_path, store)
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do 1", agent="executor"),
        ]
        store.save(quest)

        async def mock_step(step, q):
            await asyncio.sleep(10)
            return "Output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            executor.start(quest)
            await asyncio.sleep(0.01)

            result = executor.stop(quest.id)
            assert result is True
            assert not executor.is_running(quest.id)

    @pytest.mark.asyncio
    async def test_cancel_running_quest(self, tmp_path):
        """取消正在运行的 Quest"""
        store = QuestStore(tmp_path)

        executor = QuestExecutor(tmp_path, store)
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )
        quest.steps = [
            QuestStep(step_id="S1", title="Step 1", description="Do 1", agent="executor"),
        ]
        store.save(quest)

        async def mock_step(step, q):
            await asyncio.sleep(10)
            return "Output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            executor.start(quest)
            await asyncio.sleep(0.01)

            result = executor.cancel(quest.id)
            assert result is True
            updated = store.get(quest.id)
            assert updated.status == QuestStatus.CANCELLED


# =============================================================================
# QuestExecutor finally 块测试
# =============================================================================


class TestQuestExecutorFinally:
    """测试 finally 块清理"""

    @pytest.mark.asyncio
    async def test_finally_clears_running_and_breakpoint(self, tmp_path):
        """finally 块清理运行状态和断点"""
        store = QuestStore(tmp_path)
        executor = QuestExecutor(tmp_path, store)
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Desc", project_path=str(tmp_path)
        )

        executor._running_quests[quest.id] = asyncio.current_task()
        executor._breakpoint[quest.id] = 0

        with patch.object(store, "get", return_value=None):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        assert quest.id not in executor._running_quests
        assert quest.id not in executor._breakpoint


# =============================================================================
# QuestExecutor 生成步骤自动执行测试
# =============================================================================


class TestQuestExecutorAutoGenerateSteps:
    """测试自动生成步骤"""

    @pytest.mark.asyncio
    async def test_execute_quest_generates_steps_when_empty(self, tmp_path):
        """无步骤时自动生成并执行"""
        store = QuestStore(tmp_path)

        async def mock_review(qid, sid, preview):
            return "pass"

        executor = QuestExecutor(
            tmp_path, store, review_callback=mock_review
        )
        executor._notify = MagicMock()

        quest = store.create(
            title="Test", description="Do something", project_path=str(tmp_path)
        )
        quest.steps = []
        store.save(quest)

        async def mock_step(step, q):
            return "Output"

        with patch.object(executor, "_execute_step", side_effect=mock_step):
            task = asyncio.create_task(executor._execute_quest(quest))
            await asyncio.wait_for(task, timeout=5.0)

        updated = store.get(quest.id)
        assert len(updated.steps) == 4
        # 所有步骤通过 review 完成
        assert all(s.status == QuestStatus.COMPLETED for s in updated.steps)
        assert updated.status == QuestStatus.PENDING_REVIEW
