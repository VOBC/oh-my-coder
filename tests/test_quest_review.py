"""
Quest 执行结果验收 UI 测试
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.quest.executor import QuestExecutor
from src.quest.models import Quest, QuestStatus, QuestStep
from src.quest.store import QuestStore


class TestStepReview:
    """测试步骤验收流程"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """创建临时项目目录"""
        project = tmp_path / "test_project"
        project.mkdir()
        return project

    @pytest.fixture
    def mock_store(self):
        """Mock QuestStore"""
        store = MagicMock(spec=QuestStore)
        return store

    def test_pending_review_status_exists(self):
        """验证 PENDING_REVIEW 状态已定义"""
        assert hasattr(QuestStatus, "PENDING_REVIEW")
        assert QuestStatus.PENDING_REVIEW.value == "pending_review"

    def test_executor_accepts_review_callback(self, temp_project, mock_store):
        """验证 executor 接受 review_callback"""
        review_cb = AsyncMock(return_value="pass")
        executor = QuestExecutor(
            project_path=temp_project,
            store=mock_store,
            review_callback=review_cb,
        )
        assert executor.review_callback is review_cb

    def test_wait_for_review_calls_callback(self, temp_project, mock_store):
        """验证 _wait_for_review 调用回调"""
        review_cb = AsyncMock(return_value="pass")
        executor = QuestExecutor(
            project_path=temp_project,
            store=mock_store,
            review_callback=review_cb,
        )

        # Mock quest 和 step
        quest = MagicMock(spec=Quest)
        quest.steps = [
            MagicMock(spec=QuestStep, step_id="step_1", result="test result")
        ]
        mock_store.get.return_value = quest

        # 运行异步方法
        result = asyncio.run(executor._wait_for_review("quest_1", "step_1"))

        assert result == "pass"
        review_cb.assert_called_once_with("quest_1", "step_1", "test result")

    def test_wait_for_review_default_pass(self, temp_project, mock_store):
        """没有回调时默认通过"""
        executor = QuestExecutor(
            project_path=temp_project,
            store=mock_store,
            review_callback=None,
        )

        result = asyncio.run(executor._wait_for_review("quest_1", "step_1"))
        assert result == "pass"

    def test_wait_for_review_retry(self, temp_project, mock_store):
        """测试重试选择"""
        review_cb = AsyncMock(return_value="retry")
        executor = QuestExecutor(
            project_path=temp_project,
            store=mock_store,
            review_callback=review_cb,
        )

        quest = MagicMock(spec=Quest)
        quest.steps = [MagicMock(spec=QuestStep, step_id="step_1", result="")]
        mock_store.get.return_value = quest

        result = asyncio.run(executor._wait_for_review("quest_1", "step_1"))
        assert result == "retry"

    def test_wait_for_review_skip(self, temp_project, mock_store):
        """测试跳过选择"""
        review_cb = AsyncMock(return_value="skip")
        executor = QuestExecutor(
            project_path=temp_project,
            store=mock_store,
            review_callback=review_cb,
        )

        quest = MagicMock(spec=Quest)
        quest.steps = [MagicMock(spec=QuestStep, step_id="step_1", result="")]
        mock_store.get.return_value = quest

        result = asyncio.run(executor._wait_for_review("quest_1", "step_1"))
        assert result == "skip"


class TestManagerReviewCallback:
    """测试 QuestManager 传递 review_callback"""

    def test_manager_accepts_review_callback(self, tmp_path):
        """验证 manager 接受 review_callback"""
        from src.quest import QuestManager

        review_cb = AsyncMock(return_value="pass")
        manager = QuestManager(
            project_path=tmp_path,
            review_callback=review_cb,
        )
        assert manager.review_callback is review_cb

    def test_manager_passes_callback_to_executor(self, tmp_path):
        """验证 manager 把回调传给 executor"""
        from src.quest import QuestManager

        review_cb = AsyncMock(return_value="pass")
        manager = QuestManager(
            project_path=tmp_path,
            review_callback=review_cb,
        )

        # 访问 executor 属性触发初始化
        executor = manager.executor
        assert executor.review_callback is review_cb
