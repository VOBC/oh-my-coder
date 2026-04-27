"""
Quest 管理器

统一管理 Quest 的创建、SPEC 生成、执行、查询。
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

from ..core.router import ModelRouter, RouterConfig
from .executor import QuestExecutor
from .models import Quest, QuestNotification, QuestStatus
from .spec_generator import SpecGenerator
from .store import QuestStore


class QuestManager:
    """
    Quest Mode 总管理器

    用法:
        manager = QuestManager(project_path)
        quest = await manager.create_quest("实现用户认证")
        quest = await manager.generate_spec(quest)  # 生成 SPEC
        manager.confirm_and_execute(quest)           # 确认后执行
        quests = manager.list_quests()                # 查看状态
    """

    def __init__(
        self,
        project_path: Path,
        notify_callback: Callable[[QuestNotification], None] | None = None,
        review_callback: Callable[[str, str, str], Awaitable[str]] | None = None,
    ):
        self.project_path = Path(project_path)
        self.store = QuestStore(self.project_path)
        self.notify_callback = notify_callback
        self.review_callback = review_callback

        # 延迟初始化 ModelRouter
        self._router: ModelRouter | None = None
        self._executor: QuestExecutor | None = None

    @property
    def router(self) -> ModelRouter:
        if self._router is None:
            self._router = ModelRouter(RouterConfig())
        return self._router

    @property
    def executor(self) -> QuestExecutor:
        if self._executor is None:
            self._executor = QuestExecutor(
                project_path=self.project_path,
                store=self.store,
                notify_callback=self.notify_callback,
                review_callback=self.review_callback,
            )
        return self._executor

    # ============================================================
    # 核心操作
    # ============================================================

    async def create_quest(
        self,
        description: str,
        title: str | None = None,
        priority: str = "medium",
    ) -> Quest:
        """创建新 Quest"""
        return self.store.create(
            title=title or self._extract_title(description),
            description=description,
            project_path=str(self.project_path),
        )

    async def generate_spec(self, quest: Quest) -> Quest:
        """
        为 Quest 生成 SPEC

        会自动更新 quest.spec 和 quest.spec_path
        """
        # 更新状态
        self.store.update_status(quest.id, QuestStatus.SPEC_GENERATING)

        try:
            generator = SpecGenerator(
                model_router=self.router,
                project_path=self.project_path,
            )
            spec = await generator.generate(quest)
            self.store.set_spec(quest.id, spec)
            self.store.update_status(quest.id, QuestStatus.SPEC_READY)
        except Exception as e:
            self.store.update_status(quest.id, QuestStatus.FAILED)
            quest = self.store.get(quest.id)
            if quest:
                quest.error_message = f"SPEC 生成失败: {e}"
                self.store.save(quest)
            raise

        return self.store.get(quest.id)

    def confirm_and_execute(self, quest_id: str) -> Quest:
        """用户确认 SPEC 后，开始后台执行"""
        quest = self.store.get(quest_id)
        if quest is None:
            raise ValueError(f"Quest {quest_id} 不存在")

        if quest.status != QuestStatus.SPEC_READY:
            raise ValueError(
                f"Quest 状态为 {quest.status}，需要 SPEC_READY 状态才能执行"
            )

        self.store.update_status(quest_id, QuestStatus.EXECUTING)
        quest = self.store.get(quest_id)
        if quest:
            self.executor.start(quest)
        return self.store.get(quest_id)

    def execute_without_spec(self, quest_id: str) -> Quest:
        """直接执行（不生成 SPEC）"""
        quest = self.store.get(quest_id)
        if quest is None:
            raise ValueError(f"Quest {quest_id} 不存在")

        self.executor.start(quest)
        return quest

    # ============================================================
    # 查询操作
    # ============================================================

    def get_quest(self, quest_id: str) -> Quest | None:
        """获取单个 Quest"""
        return self.store.get(quest_id)

    def list_quests(
        self,
        status_filter: QuestStatus | None = None,
    ) -> list[Quest]:
        """列出 Quest"""
        return self.store.list(status_filter=status_filter)

    def get_active_quests(self) -> list[Quest]:
        """获取活跃的 Quest"""
        quests = self.store.list()
        active_statuses = {
            QuestStatus.PENDING,
            QuestStatus.SPEC_GENERATING,
            QuestStatus.SPEC_READY,
            QuestStatus.EXECUTING,
            QuestStatus.PAUSED,
        }
        return [q for q in quests if q.status in active_statuses]

    # ============================================================
    # 控制操作
    # ============================================================

    def cancel(self, quest_id: str) -> bool:
        """取消 Quest"""
        return self.executor.cancel(quest_id)

    def stop(self, quest_id: str) -> bool:
        """停止执行"""
        return self.executor.stop(quest_id)

    def pause(self, quest_id: str) -> bool:
        """暂停"""
        return self.executor.pause(quest_id)

    def resume(self, quest_id: str) -> Quest | None:
        """恢复"""
        return self.executor.resume(quest_id)

    def delete(self, quest_id: str) -> bool:
        """删除 Quest"""
        return self.store.delete(quest_id)

    def is_running(self, quest_id: str) -> bool:
        """检查是否在运行"""
        return self.executor.is_running(quest_id)

    # ============================================================
    # 辅助方法
    # ============================================================

    def _extract_title(self, description: str) -> str:
        """从描述中提取简洁标题"""
        # 取前 50 个字符
        title = description.strip()[:50]
        if len(description) > 50:
            title += "..."
        return title
