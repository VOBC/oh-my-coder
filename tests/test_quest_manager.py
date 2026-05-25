"""
Quest Mode 管理器测试 - QuestManager 核心操作
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.quest.manager import QuestManager
from src.quest.models import Quest, QuestSpec, QuestStatus

# =============================================================================
# QuestManager 初始化测试
# =============================================================================


class TestQuestManagerInit:
    """测试 QuestManager 初始化"""

    def test_init_creates_store(self, tmp_path):
        """测试初始化创建 QuestStore"""
        manager = QuestManager(tmp_path)
        assert manager.store is not None
        assert manager.project_path == tmp_path

    def test_init_sets_callbacks(self, tmp_path):
        """测试初始化设置回调"""
        notify = MagicMock()
        review = AsyncMock()

        manager = QuestManager(
            tmp_path,
            notify_callback=notify,
            review_callback=review,
        )
        assert manager.notify_callback is notify
        assert manager.review_callback is review

    def test_init_router_not_created_yet(self, tmp_path):
        """测试初始化时 router 未创建（延迟初始化）"""
        manager = QuestManager(tmp_path)
        assert manager._router is None

    def test_init_executor_not_created_yet(self, tmp_path):
        """测试初始化时 executor 未创建（延迟初始化）"""
        manager = QuestManager(tmp_path)
        assert manager._executor is None

    def test_init_with_string_path(self, tmp_path):
        """测试字符串路径初始化"""
        manager = QuestManager(str(tmp_path))
        assert manager.project_path == tmp_path

    def test_init_normalizes_path(self, tmp_path):
        """测试初始化规范化路径"""
        manager = QuestManager(tmp_path / "subdir")
        assert manager.project_path == tmp_path / "subdir"


# =============================================================================
# router / executor 延迟初始化测试
# =============================================================================


class TestQuestManagerLazyInit:
    """测试延迟初始化"""

    def test_router_created_on_first_access(self, tmp_path):
        """测试 router 第一次访问时创建"""
        manager = QuestManager(tmp_path)
        assert manager._router is None

        with patch("src.quest.manager.ModelRouter") as MockRouter:
            _ = manager.router  # trigger lazy init
            MockRouter.assert_called_once()
            assert manager._router is not None

    def test_router_cached_on_second_access(self, tmp_path):
        """测试 router 第二次访问使用缓存"""
        manager = QuestManager(tmp_path)

        with patch("src.quest.manager.ModelRouter") as MockRouter:
            r1 = manager.router
            r2 = manager.router
            assert MockRouter.call_count == 1
            assert r1 is r2

    def test_executor_created_on_first_access(self, tmp_path):
        """测试 executor 第一次访问时创建"""
        manager = QuestManager(tmp_path)
        assert manager._executor is None

        with patch("src.quest.manager.QuestExecutor") as MockExecutor:
            _ = manager.executor  # trigger lazy init
            MockExecutor.assert_called_once()
            assert manager._executor is not None

    def test_executor_passed_store_and_callbacks(self, tmp_path):
        """测试 executor 创建时传入 store 和 callbacks"""
        notify = MagicMock()
        review = AsyncMock()
        manager = QuestManager(
            tmp_path,
            notify_callback=notify,
            review_callback=review,
        )

        with patch("src.quest.manager.QuestExecutor") as MockExecutor:
            _ = manager.executor  # trigger lazy init
            _, kwargs = MockExecutor.call_args
            assert kwargs["store"] is manager.store
            assert kwargs["notify_callback"] is notify
            assert kwargs["review_callback"] is review


# =============================================================================
# create_quest 测试
# =============================================================================


class TestCreateQuest:
    """测试创建 Quest"""

    @pytest.mark.asyncio
    async def test_create_quest_returns_quest(self, tmp_path):
        """测试创建返回 Quest 对象"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("实现用户登录功能")
        assert quest is not None
        assert isinstance(quest, Quest)
        assert quest.description == "实现用户登录功能"
        assert quest.status == QuestStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_quest_uses_provided_title(self, tmp_path):
        """测试使用提供的标题"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("实现功能", title="自定义标题")
        assert quest.title == "自定义标题"

    @pytest.mark.asyncio
    async def test_create_quest_extracts_title_from_description(self, tmp_path):
        """测试从描述中提取标题（<=50 字符）"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("实现用户登录功能并包含测试用例")
        assert "实现用户登录功能并包含测试用例" in quest.title

    @pytest.mark.asyncio
    async def test_create_quest_truncates_long_title(self, tmp_path):
        """测试截断长描述（>50 字符）"""
        manager = QuestManager(tmp_path)
        long_desc = "a" * 55  # 55 chars > 50, triggers truncation
        quest = await manager.create_quest(long_desc)
        # 标题取前 50 字符，超长时加 "..."
        assert quest.title == "a" * 50 + "..."
        assert len(quest.title) == 53

    @pytest.mark.asyncio
    async def test_create_quest_saved_to_store(self, tmp_path):
        """测试创建后保存到 store"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("保存测试")
        retrieved = manager.store.get(quest.id)
        assert retrieved is not None
        assert retrieved.id == quest.id

    @pytest.mark.asyncio
    async def test_create_quest_multiple_quests(self, tmp_path):
        """测试创建多个 Quest"""
        manager = QuestManager(tmp_path)
        q1 = await manager.create_quest("任务一")
        q2 = await manager.create_quest("任务二")
        assert q1.id != q2.id


# =============================================================================
# generate_spec 测试
# =============================================================================


class TestGenerateSpec:
    """测试 SPEC 生成"""

    @pytest.mark.asyncio
    async def test_generate_spec_updates_quest(self, tmp_path):
        """测试 SPEC 生成更新 Quest"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("生成 SPEC 测试")

        # 必须用真实 QuestSpec 而非 MagicMock，避免 store.set_spec 写文件时报错
        real_spec = QuestSpec(title="Test", overview="Overview", motivation="Why")
        with patch("src.quest.manager.SpecGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate = AsyncMock(return_value=real_spec)

            result = await manager.generate_spec(quest)

        assert result.spec is not None

    @pytest.mark.asyncio
    async def test_generate_spec_final_status_is_ready(self, tmp_path):
        """测试生成完成后最终状态为 SPEC_READY"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("状态测试")

        real_spec = QuestSpec(title="Test", overview="Overview", motivation="Why")
        with patch("src.quest.manager.SpecGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate = AsyncMock(return_value=real_spec)

            await manager.generate_spec(quest)

        updated = manager.store.get(quest.id)
        assert updated.status == QuestStatus.SPEC_READY

    @pytest.mark.asyncio
    async def test_generate_spec_success_updates_status_to_ready(self, tmp_path):
        """测试成功时状态更新为 SPEC_READY"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("成功测试")

        real_spec = QuestSpec(title="Test", overview="Overview", motivation="Why")
        with patch("src.quest.manager.SpecGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate = AsyncMock(return_value=real_spec)

            await manager.generate_spec(quest)

        updated = manager.store.get(quest.id)
        assert updated.status == QuestStatus.SPEC_READY

    @pytest.mark.asyncio
    async def test_generate_spec_failure_updates_status_to_failed(self, tmp_path):
        """测试失败时状态更新为 FAILED"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("失败测试")

        with patch("src.quest.manager.SpecGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate = AsyncMock(side_effect=RuntimeError("生成失败"))

            with pytest.raises(RuntimeError):
                await manager.generate_spec(quest)

        updated = manager.store.get(quest.id)
        assert updated.status == QuestStatus.FAILED

    @pytest.mark.asyncio
    async def test_generate_spec_failure_sets_error_message(self, tmp_path):
        """测试失败时设置错误消息"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("错误消息测试")

        with patch("src.quest.manager.SpecGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate = AsyncMock(side_effect=ValueError("参数错误"))

            with pytest.raises(ValueError):
                await manager.generate_spec(quest)

        updated = manager.store.get(quest.id)
        assert updated.error_message is not None
        assert "SPEC 生成失败" in updated.error_message

    @pytest.mark.asyncio
    async def test_generate_spec_uses_router(self, tmp_path):
        """测试使用 router"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("router 测试")

        real_spec = QuestSpec(title="Test", overview="Overview", motivation="Why")
        with patch("src.quest.manager.SpecGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate = AsyncMock(return_value=real_spec)

            await manager.generate_spec(quest)

            # 验证 SpecGenerator 使用了 manager.router
            _, gen_kwargs = MockGen.call_args
            assert "model_router" in gen_kwargs

    @pytest.mark.asyncio
    async def test_generate_spec_returns_updated_quest(self, tmp_path):
        """测试返回更新后的 Quest"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("返回测试")

        real_spec = QuestSpec(title="Test", overview="Overview", motivation="Why")
        with patch("src.quest.manager.SpecGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate = AsyncMock(return_value=real_spec)

            result = await manager.generate_spec(quest)

        assert result is not None
        assert result.status == QuestStatus.SPEC_READY

    @pytest.mark.asyncio
    async def test_generate_spec_with_nonexistent_quest_returns_none(self, tmp_path):
        """测试为不存在的 Quest 生成 SPEC（返回 None 而非抛出异常）"""
        manager = QuestManager(tmp_path)
        fake_quest = MagicMock()
        fake_quest.id = "non-existent"

        real_spec = QuestSpec(title="Test", overview="Overview", motivation="Why")
        with patch("src.quest.manager.SpecGenerator") as MockGen:
            instance = MockGen.return_value
            instance.generate = AsyncMock(return_value=real_spec)

            # 不存在的 Quest：update_status 返回 None → set_spec 返回 None → get 返回 None
            # 最终 return self.store.get(quest.id) 返回 None，不抛出异常
            result = await manager.generate_spec(fake_quest)
            assert result is None


# =============================================================================
# confirm_and_execute 测试
# =============================================================================


class TestConfirmAndExecute:
    """测试确认并执行"""

    def test_confirm_and_execute_starts_execution(self, tmp_path):
        """测试确认后开始执行"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="执行测试",
            description="Desc",
            project_path=str(tmp_path),
        )
        # 设置为 SPEC_READY 状态
        manager.store.update_status(quest.id, QuestStatus.SPEC_READY)

        with patch.object(manager.executor, "start") as mock_start:
            manager.confirm_and_execute(quest.id)
            mock_start.assert_called_once()

    def test_confirm_and_execute_updates_status_to_executing(self, tmp_path):
        """测试确认后状态更新为 EXECUTING"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="状态测试",
            description="Desc",
            project_path=str(tmp_path),
        )
        manager.store.update_status(quest.id, QuestStatus.SPEC_READY)

        with patch.object(manager.executor, "start"):
            manager.confirm_and_execute(quest.id)

        updated = manager.store.get(quest.id)
        assert updated.status == QuestStatus.EXECUTING

    def test_confirm_and_execute_nonexistent_quest_raises(self, tmp_path):
        """测试不存在的 Quest 抛出异常"""
        manager = QuestManager(tmp_path)
        with pytest.raises(ValueError) as exc_info:
            manager.confirm_and_execute("non-existent-id")
        assert "不存在" in str(exc_info.value)

    def test_confirm_and_execute_wrong_status_raises(self, tmp_path):
        """测试错误状态抛出异常"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="状态错误",
            description="Desc",
            project_path=str(tmp_path),
        )
        # 保持 PENDING 状态而非 SPEC_READY
        assert quest.status == QuestStatus.PENDING

        with pytest.raises(ValueError) as exc_info:
            manager.confirm_and_execute(quest.id)
        assert "SPEC_READY" in str(exc_info.value)

    def test_confirm_and_execute_returns_quest(self, tmp_path):
        """测试返回 Quest 对象"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="返回测试",
            description="Desc",
            project_path=str(tmp_path),
        )
        manager.store.update_status(quest.id, QuestStatus.SPEC_READY)

        with patch.object(manager.executor, "start"):
            result = manager.confirm_and_execute(quest.id)

        assert result is not None
        assert result.id == quest.id


# =============================================================================
# execute_without_spec 测试
# =============================================================================


class TestExecuteWithoutSpec:
    """测试直接执行（无 SPEC）"""

    def test_execute_without_spec_starts_executor(self, tmp_path):
        """测试直接启动执行器"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="直接执行测试",
            description="Desc",
            project_path=str(tmp_path),
        )

        with patch.object(manager.executor, "start") as mock_start:
            manager.execute_without_spec(quest.id)
            mock_start.assert_called_once()

    def test_execute_without_spec_nonexistent_raises(self, tmp_path):
        """测试不存在的 Quest 抛出异常"""
        manager = QuestManager(tmp_path)
        with pytest.raises(ValueError) as exc_info:
            manager.execute_without_spec("non-existent-id")
        assert "不存在" in str(exc_info.value)

    def test_execute_without_spec_returns_quest(self, tmp_path):
        """测试返回 Quest 对象"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="返回测试",
            description="Desc",
            project_path=str(tmp_path),
        )

        with patch.object(manager.executor, "start"):
            result = manager.execute_without_spec(quest.id)

        assert result is not None
        assert result.id == quest.id

    def test_execute_without_spec_no_status_check(self, tmp_path):
        """测试不检查状态（任意状态都可执行）"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="任意状态测试",
            description="Desc",
            project_path=str(tmp_path),
        )
        # 使用 FAILED 状态测试
        manager.store.update_status(quest.id, QuestStatus.FAILED)

        with patch.object(manager.executor, "start"):
            # 不应抛出异常
            result = manager.execute_without_spec(quest.id)
        assert result is not None


# =============================================================================
# get_quest 测试
# =============================================================================


class TestGetQuest:
    """测试获取单个 Quest"""

    def test_get_existing_quest(self, tmp_path):
        """测试获取存在的 Quest"""
        manager = QuestManager(tmp_path)
        created = manager.store.create(
            title="Test",
            description="Desc",
            project_path=str(tmp_path),
        )

        result = manager.get_quest(created.id)
        assert result is not None
        assert result.id == created.id

    def test_get_nonexistent_quest_returns_none(self, tmp_path):
        """测试获取不存在的 Quest 返回 None"""
        manager = QuestManager(tmp_path)
        result = manager.get_quest("non-existent-id")
        assert result is None


# =============================================================================
# list_quests 测试
# =============================================================================


class TestListQuests:
    """测试列出 Quest"""

    def test_list_empty(self, tmp_path):
        """测试空列表"""
        manager = QuestManager(tmp_path)
        quests = manager.list_quests()
        assert quests == []

    def test_list_returns_all(self, tmp_path):
        """测试列出所有"""
        manager = QuestManager(tmp_path)
        manager.store.create(title="Q1", description="D", project_path=str(tmp_path))
        manager.store.create(title="Q2", description="D", project_path=str(tmp_path))

        quests = manager.list_quests()
        assert len(quests) == 2

    def test_list_with_status_filter(self, tmp_path):
        """测试状态过滤"""
        manager = QuestManager(tmp_path)
        q1 = manager.store.create(
            title="Q1", description="D", project_path=str(tmp_path)
        )
        q2 = manager.store.create(
            title="Q2", description="D", project_path=str(tmp_path)
        )
        manager.store.update_status(q1.id, QuestStatus.COMPLETED)

        completed = manager.list_quests(status_filter=QuestStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].id == q1.id

        pending = manager.list_quests(status_filter=QuestStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].id == q2.id


# =============================================================================
# get_active_quests 测试
# =============================================================================


class TestGetActiveQuests:
    """测试获取活跃 Quest"""

    def _make_quest(self, manager, status: QuestStatus) -> Quest:
        q = manager.store.create(
            title=str(status), description="D", project_path=str(manager.project_path)
        )
        if status != QuestStatus.PENDING:
            manager.store.update_status(q.id, status)
        return q

    def test_active_includes_pending(self, tmp_path):
        """测试 PENDING 状态包含在活跃中"""
        manager = QuestManager(tmp_path)
        q = self._make_quest(manager, QuestStatus.PENDING)
        active = manager.get_active_quests()
        assert any(x.id == q.id for x in active)

    def test_active_includes_executing(self, tmp_path):
        """测试 EXECUTING 状态包含在活跃中"""
        manager = QuestManager(tmp_path)
        q = self._make_quest(manager, QuestStatus.EXECUTING)
        active = manager.get_active_quests()
        assert any(x.id == q.id for x in active)

    def test_active_includes_paused(self, tmp_path):
        """测试 PAUSED 状态包含在活跃中"""
        manager = QuestManager(tmp_path)
        q = self._make_quest(manager, QuestStatus.PAUSED)
        active = manager.get_active_quests()
        assert any(x.id == q.id for x in active)

    def test_active_includes_spec_generating(self, tmp_path):
        """测试 SPEC_GENERATING 状态包含在活跃中"""
        manager = QuestManager(tmp_path)
        q = self._make_quest(manager, QuestStatus.SPEC_GENERATING)
        active = manager.get_active_quests()
        assert any(x.id == q.id for x in active)

    def test_active_includes_spec_ready(self, tmp_path):
        """测试 SPEC_READY 状态包含在活跃中"""
        manager = QuestManager(tmp_path)
        q = self._make_quest(manager, QuestStatus.SPEC_READY)
        active = manager.get_active_quests()
        assert any(x.id == q.id for x in active)

    def test_active_excludes_completed(self, tmp_path):
        """测试 COMPLETED 状态不包含在活跃中"""
        manager = QuestManager(tmp_path)
        q = self._make_quest(manager, QuestStatus.COMPLETED)
        active = manager.get_active_quests()
        assert not any(x.id == q.id for x in active)

    def test_active_excludes_failed(self, tmp_path):
        """测试 FAILED 状态不包含在活跃中"""
        manager = QuestManager(tmp_path)
        q = self._make_quest(manager, QuestStatus.FAILED)
        active = manager.get_active_quests()
        assert not any(x.id == q.id for x in active)

    def test_active_excludes_cancelled(self, tmp_path):
        """测试 CANCELLED 状态不包含在活跃中"""
        manager = QuestManager(tmp_path)
        q = self._make_quest(manager, QuestStatus.CANCELLED)
        active = manager.get_active_quests()
        assert not any(x.id == q.id for x in active)

    def test_active_empty_when_all_finished(self, tmp_path):
        """测试全部完成时返回空"""
        manager = QuestManager(tmp_path)
        self._make_quest(manager, QuestStatus.COMPLETED)
        self._make_quest(manager, QuestStatus.FAILED)
        active = manager.get_active_quests()
        assert len(active) == 0


# =============================================================================
# 控制操作测试（cancel / stop / pause / resume / delete）
# =============================================================================


class TestQuestManagerControl:
    """测试控制操作"""

    def test_cancel_calls_executor(self, tmp_path):
        """测试 cancel 调用执行器"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="Cancel Test",
            description="Desc",
            project_path=str(tmp_path),
        )

        with patch.object(manager.executor, "cancel", return_value=True) as mock_cancel:
            result = manager.cancel(quest.id)
            mock_cancel.assert_called_once_with(quest.id)
            assert result is True

    def test_cancel_nonexistent_returns_false(self, tmp_path):
        """测试取消不存在的 Quest 返回 False"""
        manager = QuestManager(tmp_path)
        with patch.object(manager.executor, "cancel", return_value=False):
            result = manager.cancel("non-existent")
        assert result is False

    def test_stop_calls_executor(self, tmp_path):
        """测试 stop 调用执行器"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="Stop Test",
            description="Desc",
            project_path=str(tmp_path),
        )

        with patch.object(manager.executor, "stop", return_value=True) as mock_stop:
            result = manager.stop(quest.id)
            mock_stop.assert_called_once_with(quest.id)
            assert result is True

    def test_pause_calls_executor(self, tmp_path):
        """测试 pause 调用执行器"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="Pause Test",
            description="Desc",
            project_path=str(tmp_path),
        )

        with patch.object(manager.executor, "pause", return_value=True) as mock_pause:
            result = manager.pause(quest.id)
            mock_pause.assert_called_once_with(quest.id)
            assert result is True

    def test_resume_calls_executor(self, tmp_path):
        """测试 resume 调用执行器"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="Resume Test",
            description="Desc",
            project_path=str(tmp_path),
        )
        mock_quest = MagicMock()
        with patch.object(
            manager.executor, "resume", return_value=mock_quest
        ) as mock_resume:
            result = manager.resume(quest.id)
            mock_resume.assert_called_once_with(quest.id)
            assert result is mock_quest

    def test_delete_calls_store(self, tmp_path):
        """测试 delete 调用 store"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="Delete Test",
            description="Desc",
            project_path=str(tmp_path),
        )

        with patch.object(manager.store, "delete", return_value=True) as mock_delete:
            result = manager.delete(quest.id)
            mock_delete.assert_called_once_with(quest.id)
            assert result is True

    def test_delete_nonexistent_returns_false(self, tmp_path):
        """测试删除不存在的 Quest 返回 False"""
        manager = QuestManager(tmp_path)
        with patch.object(manager.store, "delete", return_value=False):
            result = manager.delete("non-existent")
        assert result is False

    def test_is_running_calls_executor(self, tmp_path):
        """测试 is_running 调用执行器"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="IsRunning Test",
            description="Desc",
            project_path=str(tmp_path),
        )

        with patch.object(
            manager.executor, "is_running", return_value=True
        ) as mock_is_running:
            result = manager.is_running(quest.id)
            mock_is_running.assert_called_once_with(quest.id)
            assert result is True

    def test_is_running_returns_false_for_nonexistent(self, tmp_path):
        """测试不存在的 Quest is_running 返回 False"""
        manager = QuestManager(tmp_path)
        with patch.object(manager.executor, "is_running", return_value=False):
            result = manager.is_running("non-existent")
        assert result is False


# =============================================================================
# 辅助方法测试
# =============================================================================


class TestExtractTitle:
    """测试 _extract_title 辅助方法"""

    def test_short_description(self, tmp_path):
        """测试短描述"""
        manager = QuestManager(tmp_path)
        title = manager._extract_title("简短描述")
        assert title == "简短描述"

    def test_exactly_50_chars(self, tmp_path):
        """测试恰好 50 字符（不截断）"""
        manager = QuestManager(tmp_path)
        text = "a" * 50
        title = manager._extract_title(text)
        assert title == text

    def test_longer_than_50_chars(self, tmp_path):
        """测试超过 50 字符（截断）"""
        manager = QuestManager(tmp_path)
        text = "a" * 60
        title = manager._extract_title(text)
        assert title == "a" * 50 + "..."

    def test_whitespace_trimmed(self, tmp_path):
        """测试空白字符去除"""
        manager = QuestManager(tmp_path)
        title = manager._extract_title("  前后有空格  ")
        assert title == "前后有空格"

    def test_newline_handled(self, tmp_path):
        """测试换行处理"""
        manager = QuestManager(tmp_path)
        title = manager._extract_title("包含\n换行")
        assert title == "包含\n换行"


# =============================================================================
# 边界情况测试
# =============================================================================


class TestQuestManagerEdgeCases:
    """边界情况测试"""

    def test_confirm_and_execute_already_executing_raises(self, tmp_path):
        """测试正在执行时再次确认抛出异常"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="重复执行测试",
            description="Desc",
            project_path=str(tmp_path),
        )
        manager.store.update_status(quest.id, QuestStatus.EXECUTING)

        with pytest.raises(ValueError) as exc_info:
            manager.confirm_and_execute(quest.id)
        assert "SPEC_READY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_quest_empty_description(self, tmp_path):
        """测试空描述创建 Quest"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("")
        assert quest is not None
        assert quest.description == ""

    @pytest.mark.asyncio
    async def test_create_quest_whitespace_only(self, tmp_path):
        """测试纯空白描述"""
        manager = QuestManager(tmp_path)
        quest = await manager.create_quest("   ")
        assert quest is not None

    def test_multiple_operations_same_quest(self, tmp_path):
        """测试对同一 Quest 执行多个操作"""
        manager = QuestManager(tmp_path)
        quest = manager.store.create(
            title="多操作测试",
            description="Desc",
            project_path=str(tmp_path),
        )

        # get
        result = manager.get_quest(quest.id)
        assert result is not None

        # is_running
        with patch.object(manager.executor, "is_running", return_value=False):
            running = manager.is_running(quest.id)
            assert running is False

        # delete
        with patch.object(manager.store, "delete", return_value=True):
            deleted = manager.delete(quest.id)
            assert deleted is True
