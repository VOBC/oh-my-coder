"""
Quest 执行引擎

负责任务的后台执行，支持真正的暂停/恢复。
使用 asyncio 在后台运行 omc 工作流，实时跟踪进度。
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, List, Optional

from .models import Quest, QuestNotification, QuestStatus, QuestStep
from .store import QuestStore


class QuestExecutor:
    """Quest 后台执行引擎"""

    def __init__(
        self,
        project_path: Path,
        store: QuestStore,
        notify_callback: Optional[Callable[[QuestNotification], None]] = None,
        replan_callback: Optional[Callable[[str, str], None]] = None,
        review_callback: Optional[Callable[[str, str, str], Awaitable[str]]] = None,
    ):
        self.project_path = Path(project_path)
        self.store = store
        self.notify_callback = notify_callback
        # 失败时触发重规划回调（传入 quest_id, failed_step_id）
        self.replan_callback = replan_callback
        # 验收回调：传入 quest_id, step_id, result_preview，返回 "pass"/"retry"/"skip"
        self.review_callback = review_callback
        # 运行时状态（内存中）：存储当前正在等待输入的步骤
        self._running_quests: dict[str, asyncio.Task] = {}
        # 断点记录：quest_id -> 当前步骤索引
        self._breakpoint: dict[str, int] = {}

    def _notify(
        self, quest: Optional[Quest], event: str, message: str, details=None
    ) -> None:
        """发送通知"""
        if self.notify_callback:
            notification = QuestNotification(
                quest_id=quest.id if quest else "unknown",
                title=quest.title if quest else "",
                event=event,
                message=message,
                details=details,
            )
            self.notify_callback(notification)

    # ============================================================
    # 启动执行
    # ============================================================

    def start(self, quest: Quest) -> None:
        """启动后台执行（仅启动，不会阻塞）"""
        if quest.id in self._running_quests:
            return  # 已经在运行

        task = asyncio.create_task(self._execute_quest(quest))
        self._running_quests[quest.id] = task

    async def _execute_quest(self, quest: Quest) -> None:
        """异步执行 Quest 主循环（支持断点续跑）"""
        try:
            self.store.update_status(quest.id, QuestStatus.EXECUTING)
            fresh = self.store.get(quest.id)
            if fresh is None:
                return

            self._notify(fresh, "started", f"🧙 Quest 已开始: {fresh.title}")

            # 确定起始步骤（断点续跑）
            start_index = self._breakpoint.pop(quest.id, 0)

            # 从 SPEC 生成步骤（仅首次生成，后续从 store 恢复）
            if not fresh.steps:
                steps = self._generate_steps(fresh)
                fresh.steps = steps
                self.store.save(fresh)
            else:
                steps = fresh.steps

            # 执行每个步骤（跳过已完成/失败）
            for i, step in enumerate(steps):
                # 跳过已完成的步骤
                if i < start_index:
                    continue

                # 每次迭代都重新读取最新状态
                fresh = self.store.get(quest.id)
                if fresh is None:
                    return

                # 检查取消/暂停
                if fresh.status == QuestStatus.CANCELLED:
                    self._notify(fresh, "cancelled", "⏹️ Quest 已取消")
                    return
                if fresh.status == QuestStatus.PAUSED:
                    # 保存断点位置
                    self._breakpoint[quest.id] = i
                    self._notify(
                        fresh,
                        "paused",
                        f"⏸️ Quest 已暂停（将在步骤 {step.step_id} 恢复）",
                    )
                    return

                # 更新当前步骤状态
                step.status = QuestStatus.EXECUTING
                self.store.save(fresh)

                try:
                    result = await self._execute_step(step, fresh)
                    step.result = result
                    # 进入验收状态，等待用户确认
                    step.status = QuestStatus.PENDING_REVIEW
                    fresh.status = QuestStatus.PENDING_REVIEW
                    self.store.save(fresh)
                    self._notify(
                        fresh,
                        "pending_review",
                        f"⏳ 步骤 [{step.step_id}] {step.title} 执行完成，等待验收",
                        details={
                            "step_id": step.step_id,
                            "result_preview": result[:200] if result else "",
                        },
                    )
                    # 等待用户验收（阻塞）
                    review_result = await self._wait_for_review(fresh.id, step.step_id)
                    if review_result == "retry":
                        # 重试当前步骤
                        step.status = QuestStatus.PENDING
                        step.result = None
                        self.store.save(fresh)
                        i -= 1  # 回退索引重试
                        continue
                    elif review_result == "skip":
                        # 跳过（标记为警告）
                        step.status = QuestStatus.COMPLETED
                        step.completed_at = datetime.now()
                        step.notes = "用户跳过验收"
                        self.store.save(fresh)
                        self._notify(
                            fresh, "step_skipped", f"⏭️ 步骤 [{step.step_id}] 已跳过"
                        )
                    else:
                        # 通过
                        step.status = QuestStatus.COMPLETED
                        step.completed_at = datetime.now()
                        self.store.save(fresh)
                        self._notify(
                            fresh,
                            "step_completed",
                            f"✅ 步骤 [{step.step_id}] {step.title} 已验收通过",
                        )
                except asyncio.CancelledError:
                    # 被暂停/取消打断
                    self.store.save(fresh)
                    self._breakpoint[quest.id] = i
                    return
                except Exception as e:
                    step.status = QuestStatus.FAILED
                    step.error = str(e)
                    fresh.error_message = f"步骤 {step.step_id} 失败: {e}"
                    self.store.save(fresh)
                    self._notify(
                        fresh,
                        "failed",
                        f"⚠️ 步骤 [{step.step_id}] {step.title} 失败: {e}",
                        details={"step_id": step.step_id, "error": str(e)},
                    )
                    # 触发重规划回调
                    if self.replan_callback:
                        try:
                            self.replan_callback(fresh.id, step.step_id)
                        except Exception as cb_err:
                            self._notify(
                                fresh, "replan_error", f"重规划回调失败: {cb_err}"
                            )
                    # 继续执行后续步骤
                    continue

            # 所有步骤完成
            fresh = self.store.get(quest.id)
            if fresh and fresh.status == QuestStatus.EXECUTING:
                failed_count = sum(
                    1 for s in fresh.steps if s.status == QuestStatus.FAILED
                )
                if failed_count == 0:
                    self.store.update_status(fresh.id, QuestStatus.COMPLETED)
                    fresh.result_summary = f"✅ 全部 {len(fresh.steps)} 个步骤成功完成"
                    self.store.save(fresh)
                    self._notify(
                        fresh,
                        "completed",
                        f"🎉 Quest 已完成: {fresh.title}",
                    )
                else:
                    self.store.update_status(fresh.id, QuestStatus.FAILED)
                    fresh.result_summary = (
                        f"{len(fresh.steps) - failed_count}/{len(fresh.steps)} 步骤成功"
                    )
                    self.store.save(fresh)
                    self._notify(
                        fresh,
                        "failed",
                        f"⚠️ Quest 完成但有 {failed_count} 个步骤失败",
                    )

        except Exception as e:
            self.store.update_status(quest.id, QuestStatus.FAILED)
            fresh = self.store.get(quest.id)
            if fresh:
                fresh.error_message = str(e)
                self.store.save(fresh)
            self._notify(
                fresh,
                "failed",
                f"❌ Quest 执行失败: {e}",
            )
        finally:
            self._running_quests.pop(quest.id, None)
            self._breakpoint.pop(quest.id, None)

    async def _wait_for_review(self, quest_id: str, step_id: str) -> str:
        """等待用户验收步骤结果

        Returns:
            "pass" - 验收通过
            "retry" - 重试该步骤
            "skip" - 跳过该步骤
        """
        if self.review_callback:
            quest = self.store.get(quest_id)
            step = (
                next((s for s in quest.steps if s.step_id == step_id), None)
                if quest
                else None
            )
            preview = step.result[:500] if step and step.result else ""
            try:
                return await self.review_callback(quest_id, step_id, preview)
            except Exception as e:
                self._notify(quest, "review_error", f"验收回调失败: {e}")
                return "pass"  # 默认通过
        # 没有回调时默认通过
        return "pass"

    def _generate_steps(self, quest: Quest) -> List[QuestStep]:
        """从 SPEC 生成执行步骤"""
        steps: List[QuestStep] = []

        if not quest.spec or not quest.spec.acceptance_criteria:
            steps = [
                QuestStep(
                    step_id="S1",
                    title="分析需求",
                    description=f"分析并理解: {quest.description}",
                    agent="analyst",
                ),
                QuestStep(
                    step_id="S2",
                    title="规划实现",
                    description="制定实现计划",
                    agent="planner",
                ),
                QuestStep(
                    step_id="S3",
                    title="执行编码",
                    description="按照计划执行编码",
                    agent="executor",
                ),
                QuestStep(
                    step_id="S4",
                    title="验证结果",
                    description="运行测试验证",
                    agent="verifier",
                ),
            ]
            return steps

        # 基于 acceptance_criteria 生成步骤
        ac_chunks = [
            quest.spec.acceptance_criteria[i : i + 3]
            for i in range(0, len(quest.spec.acceptance_criteria), 3)
        ]

        for i, chunk in enumerate(ac_chunks, 1):
            criteria_text = "; ".join(ac.description for ac in chunk)
            steps.append(
                QuestStep(
                    step_id=f"S{i}",
                    title=f"实现: {criteria_text[:30]}...",
                    description=f"验收标准: {criteria_text}",
                    agent="executor",
                )
            )

        steps.append(
            QuestStep(
                step_id=f"S{len(steps)+1}",
                title="代码审查",
                description="进行代码审查和质量检查",
                agent="code-reviewer",
            )
        )

        return steps

    async def _execute_step(self, step: QuestStep, quest: Quest) -> str:
        """执行单个步骤"""
        project_path = quest.project_path

        cmd = [
            sys.executable,
            "-m",
            "oh_my_coder",
            "run",
            step.description,
            "--project",
            project_path,
            "--workflow",
            "build",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_path,
            env={**os.environ},
        )

        stdout, stderr = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            error = stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"命令失败 (code={proc.returncode}): {error[:500]}")

        return output[:2000]

    # ============================================================
    # 控制操作
    # ============================================================

    def stop(self, quest_id: str) -> bool:
        """立即停止（不等完成，直接取消任务）"""
        task = self._running_quests.pop(quest_id, None)
        if task:
            task.cancel()
            return True
        return False

    def cancel(self, quest_id: str) -> bool:
        """取消 Quest"""
        self.stop(quest_id)
        self._breakpoint.pop(quest_id, None)
        return bool(self.store.update_status(quest_id, QuestStatus.CANCELLED))

    def pause(self, quest_id: str) -> bool:
        """暂停 Quest（在当前步骤完成后暂停）"""
        quest = self.store.get(quest_id)
        if quest is None:
            return False

        # 如果正在运行，停止任务，下次启动时会从断点继续
        self.stop(quest_id)

        # 找到当前正在执行的步骤索引
        running_idx = 0
        for i, step in enumerate(quest.steps):
            if step.status == QuestStatus.EXECUTING:
                running_idx = i
                break
            if step.status in (QuestStatus.PENDING, QuestStatus.EXECUTING):
                running_idx = i
                break

        self._breakpoint[quest_id] = running_idx
        return bool(self.store.update_status(quest_id, QuestStatus.PAUSED))

    def resume(self, quest_id: str) -> Optional[Quest]:
        """恢复暂停的 Quest，从断点继续"""
        quest = self.store.get(quest_id)
        if quest is None or quest.status != QuestStatus.PAUSED:
            return None

        # 清除之前的断点（会从已保存的步骤继续）
        self._breakpoint.pop(quest_id, None)
        self.store.update_status(quest_id, QuestStatus.EXECUTING)
        quest = self.store.get(quest_id)
        if quest:
            self.start(quest)
        return quest

    def is_running(self, quest_id: str) -> bool:
        """检查 Quest 是否在运行"""
        return quest_id in self._running_quests

    def get_breakpoint(self, quest_id: str) -> Optional[int]:
        """获取暂停时的断点位置"""
        return self._breakpoint.get(quest_id)
