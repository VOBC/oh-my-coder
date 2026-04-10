"""
Quest Mode 模型测试 - 数据结构与状态转换
"""

from datetime import datetime, timedelta

from src.quest.models import (
    Quest,
    QuestStep,
    QuestSpec,
    QuestStatus,
    QuestPriority,
    AcceptanceCriteria,
    QuestNotification,
    QuestDisplay,
)


# =============================================================================
# QuestStatus 测试
# =============================================================================


class TestQuestStatus:
    """测试任务状态枚举"""

    def test_all_statuses_defined(self):
        """测试所有状态都定义了"""
        expected = {
            "pending",
            "spec_generating",
            "spec_ready",
            "executing",
            "pending_review",
            "completed",
            "failed",
            "cancelled",
            "paused",
        }
        actual = {s.value for s in QuestStatus}
        assert expected == actual

    def test_status_ordering(self):
        """测试状态值可以比较"""
        # 验证都是字符串
        for status in QuestStatus:
            assert isinstance(status.value, str)


# =============================================================================
# Quest 模型测试
# =============================================================================


class TestQuestCreation:
    """测试 Quest 创建"""

    def test_create_minimal_quest(self):
        """测试创建最小 Quest"""
        quest = Quest(
            id="test-123",
            title="Test Quest",
            description="A test quest",
            project_path="/tmp/test",
        )
        assert quest.id == "test-123"
        assert quest.title == "Test Quest"
        assert quest.status == QuestStatus.PENDING
        assert quest.priority == QuestPriority.MEDIUM
        assert quest.steps == []

    def test_create_quest_with_priority(self):
        """测试创建带优先级的 Quest"""
        quest = Quest(
            id="test-123",
            title="High Priority",
            description="Important task",
            project_path="/tmp/test",
            priority=QuestPriority.HIGH,
        )
        assert quest.priority == QuestPriority.HIGH


class TestQuestProgress:
    """测试 Quest 进度计算"""

    def test_progress_zero_for_pending(self):
        """测试 PENDING 状态进度为 0"""
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
            status=QuestStatus.PENDING,
        )
        assert quest.progress() == 0.0

    def test_progress_full_for_completed(self):
        """测试 COMPLETED 状态进度为 1"""
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
            status=QuestStatus.COMPLETED,
        )
        assert quest.progress() == 1.0

    def test_progress_full_for_failed(self):
        """测试 FAILED 状态进度为 1"""
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
            status=QuestStatus.FAILED,
        )
        assert quest.progress() == 1.0

    def test_progress_with_steps_none(self):
        """测试无步骤时进度"""
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
            steps=[],
        )
        assert quest.progress() == 0.0

    def test_progress_with_steps_all_complete(self):
        """测试所有步骤完成时进度"""
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
            steps=[
                QuestStep(
                    step_id="S1",
                    title="Step 1",
                    description="Do something",
                    agent="executor",
                    status=QuestStatus.COMPLETED,
                ),
                QuestStep(
                    step_id="S2",
                    title="Step 2",
                    description="Do more",
                    agent="executor",
                    status=QuestStatus.COMPLETED,
                ),
            ],
        )
        assert quest.progress() == 1.0

    def test_progress_with_steps_partial(self):
        """测试部分步骤完成时进度"""
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
            steps=[
                QuestStep(
                    step_id="S1",
                    title="Step 1",
                    description="Do something",
                    agent="executor",
                    status=QuestStatus.COMPLETED,
                ),
                QuestStep(
                    step_id="S2",
                    title="Step 2",
                    description="Do more",
                    agent="executor",
                    status=QuestStatus.PENDING,
                ),
            ],
        )
        assert quest.progress() == 0.5

    def test_progress_with_failed_steps(self):
        """测试有失败步骤时进度"""
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
            steps=[
                QuestStep(
                    step_id="S1",
                    title="Step 1",
                    description="Do something",
                    agent="executor",
                    status=QuestStatus.COMPLETED,
                ),
                QuestStep(
                    step_id="S2",
                    title="Step 2",
                    description="Do more",
                    agent="executor",
                    status=QuestStatus.FAILED,
                ),
            ],
        )
        # 失败步骤也算完成（计入分母）
        assert quest.progress() == 0.5


class TestQuestDuration:
    """测试 Quest 时长计算"""

    def test_duration_no_timing(self):
        """测试未开始时无时长"""
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
        )
        assert quest.duration() is None

    def test_duration_in_progress(self):
        """测试进行中时长"""
        now = datetime.now()
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
            started_at=now - timedelta(minutes=5),
        )
        duration = quest.duration()
        assert duration is not None
        assert 290 < duration < 310  # 约 5 分钟

    def test_duration_completed(self):
        """测试已完成时长"""
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
            started_at=datetime(2024, 1, 1, 10, 0, 0),
            completed_at=datetime(2024, 1, 1, 10, 30, 0),
        )
        assert quest.duration() == 1800.0  # 30 分钟


class TestQuestSummary:
    """测试 Quest 摘要"""

    def test_to_summary_pending(self):
        """测试 PENDING 摘要"""
        quest = Quest(
            id="test-123",
            title="Test Quest Title Here",
            description="Test",
            project_path="/tmp/test",
            status=QuestStatus.PENDING,
            priority=QuestPriority.MEDIUM,
        )
        summary = quest.to_summary()
        assert "pending" in summary
        assert "medium" in summary
        assert "Test Quest Title Here" in summary
        assert "0%" in summary

    def test_to_summary_in_progress(self):
        """测试进行中摘要"""
        now = datetime.now()
        quest = Quest(
            id="test-123",
            title="Test",
            description="Test",
            project_path="/tmp/test",
            status=QuestStatus.EXECUTING,
            priority=QuestPriority.HIGH,
            started_at=now - timedelta(minutes=5),
            steps=[
                QuestStep(
                    step_id="S1",
                    title="Step 1",
                    description="Do",
                    agent="executor",
                    status=QuestStatus.COMPLETED,
                ),
                QuestStep(
                    step_id="S2",
                    title="Step 2",
                    description="Do",
                    agent="executor",
                    status=QuestStatus.PENDING,
                ),
            ],
        )
        summary = quest.to_summary()
        assert "executing" in summary
        assert "50%" in summary


# =============================================================================
# QuestStep 测试
# =============================================================================


class TestQuestStep:
    """测试 QuestStep"""

    def test_create_step(self):
        """测试创建步骤"""
        step = QuestStep(
            step_id="S1",
            title="First Step",
            description="Do something important",
            agent="planner",
        )
        assert step.step_id == "S1"
        assert step.status == QuestStatus.PENDING
        assert step.result is None
        assert step.error is None

    def test_step_with_result(self):
        """测试步骤带结果"""
        step = QuestStep(
            step_id="S1",
            title="Step",
            description="Do",
            agent="executor",
            status=QuestStatus.COMPLETED,
            result="Output from execution",
            completed_at=datetime.now(),
        )
        assert step.result == "Output from execution"
        assert step.completed_at is not None


# =============================================================================
# QuestSpec 测试
# =============================================================================


class TestQuestSpec:
    """测试 QuestSpec"""

    def test_create_spec(self):
        """测试创建 SPEC"""
        spec = QuestSpec(
            title="Test Spec",
            overview="Overview here",
            motivation="Motivation here",
        )
        assert spec.title == "Test Spec"
        assert spec.scope == []
        assert spec.acceptance_criteria == []

    def test_spec_to_markdown(self):
        """测试 SPEC 转 Markdown"""
        spec = QuestSpec(
            title="My Quest",
            overview="Build something",
            motivation="Because it's useful",
            scope=["Feature A", "Feature B"],
            acceptance_criteria=[
                AcceptanceCriteria(id="AC1", description="Works correctly"),
                AcceptanceCriteria(id="AC2", description="Tests pass"),
            ],
        )
        md = spec.to_markdown()
        assert "# My Quest" in md
        assert "## 概述" in md
        assert "Build something" in md
        assert "## 包含范围" in md
        assert "Feature A" in md
        assert "## 验收标准" in md
        assert "[ ] **[AC1]**" in md


# =============================================================================
# QuestDisplay 测试
# =============================================================================


class TestQuestDisplay:
    """测试 CLI 展示格式"""

    def test_from_quest_complete(self):
        """测试从 Quest 创建 Display"""
        quest = Quest(
            id="test-12345678",
            title="Test Quest Title",
            description="Test",
            project_path="/tmp/test",
            status=QuestStatus.EXECUTING,
            priority=QuestPriority.MEDIUM,
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            started_at=datetime(2024, 1, 1, 10, 5, 0),
        )
        # 添加步骤使进度为 50%
        quest.steps = [
            QuestStep(
                step_id="S1",
                title="Step 1",
                description="Do",
                agent="executor",
                status=QuestStatus.COMPLETED,
            ),
            QuestStep(
                step_id="S2",
                title="Step 2",
                description="Do",
                agent="executor",
                status=QuestStatus.PENDING,
            ),
        ]

        display = QuestDisplay.from_quest(quest)

        assert display.id == "test-123"
        assert display.title == "Test Quest Title"
        assert display.status == QuestStatus.EXECUTING
        assert "50%" in display.progress_bar
        assert "█" in display.progress_bar

    def test_from_quest_truncates_long_title(self):
        """测试长标题截断"""
        quest = Quest(
            id="test-123",
            title="A Very Very Very Long Title That Definitely Exceeds Forty Five Characters",
            description="Test",
            project_path="/tmp/test",
        )
        display = QuestDisplay.from_quest(quest)
        # 截断到 45 字符
        assert len(display.title) == 45
        assert display.title == "A Very Very Very Long Title That Definitely E"


# =============================================================================
# QuestNotification 测试
# =============================================================================


class TestQuestNotification:
    """测试通知"""

    def test_create_notification(self):
        """测试创建通知"""
        notif = QuestNotification(
            quest_id="q-123",
            title="Test Quest",
            event="started",
            message="Quest has started",
            details={"step": "S1"},
        )
        assert notif.quest_id == "q-123"
        assert notif.event == "started"
        assert notif.timestamp is not None

    def test_notification_details_optional(self):
        """测试通知 details 可选"""
        notif = QuestNotification(
            quest_id="q-123",
            title="Test",
            event="completed",
            message="Done",
        )
        assert notif.details is None
