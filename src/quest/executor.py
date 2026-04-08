"""
Quest 执行引擎

负责任务的后台执行。
使用 asyncio 在后台运行 omc 工作流，实时跟踪进度。
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from .models import Quest, QuestNotification, QuestStatus, QuestStep
from .store import QuestStore


class QuestExecutor:
    """Quest 后台执行引擎"""

    def __init__(
        self,
        project_path: Path,
        store: QuestStore,
        notify_callback: Optional[Callable[[QuestNotification], None]] = None,
    ):
        self.project_path = project_path
        self.store = store
        self.notify_callback = notify_callback
        self._running_quests: dict[str, asyncio.Task] = {}
        self._omc_path = self._find_omc()

    def _find_omc(self) -> str:
        """找到 omc 命令"""
        # 优先使用当前 Python 环境中的 omc
        python_dir = Path(sys.executable).parent
        omc_in_venv = python_dir / "omc"
        if omc_in_venv.exists():
            return str(omc_in_venv)

        # 使用 python -m 方式调用
        return f"{sys.executable} -m oh_my_coder"

    def _notify(self, quest: Quest, event: str, message: str, details=None) -> None:
        """发送通知"""
        if self.notify_callback:
            self.notify_callback(
                QuestNotification(
                    quest_id=quest.id,
                    title=quest.title,
                    event=event,
                    message=message,
                    details=details,
                )
            )

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
        """异步执行 Quest 主循环"""
        try:
            # 更新状态为执行中
            self.store.update_status(quest.id, QuestStatus.EXECUTING)
            quest = self.store.get(quest.id)
            if quest is None:
                return

            self._notify(quest, "started", f"Quest 已开始: {quest.title}")

            # 从 SPEC 提取步骤（基于 acceptance_criteria）
            steps = self._generate_steps(quest)
            quest.steps = steps
            self.store.save(quest)

            # 执行每个步骤
            for step in steps:
                quest = self.store.get(quest.id)
                if quest is None or quest.status == QuestStatus.CANCELLED:
                    break

                step.status = QuestStatus.EXECUTING
                self.store.save(quest)

                try:
                    result = await self._execute_step(step, quest)
                    step.status = QuestStatus.COMPLETED
                    step.completed_at = datetime.now()
                    step.result = result
                    self._notify(
                        quest,
                        "step_completed",
                        f"步骤 [{step.step_id}] {step.title} 已完成",
                    )
                except Exception as e:
                    step.status = QuestStatus.FAILED
                    step.error = str(e)
                    quest.error_message = f"步骤 {step.step_id} 失败: {e}"
                    self.store.save(quest)
                    self._notify(
                        quest,
                        "failed",
                        f"步骤 [{step.step_id}] {step.title} 失败: {e}",
                        details={"step_id": step.step_id, "error": str(e)},
                    )
                    # 继续执行后续步骤
                    continue

                self.store.save(quest)

            # 所有步骤完成
            quest = self.store.get(quest.id)
            if quest and quest.status == QuestStatus.EXECUTING:
                failed_count = sum(
                    1 for s in quest.steps if s.status == QuestStatus.FAILED
                )
                if failed_count == 0:
                    self.store.update_status(quest.id, QuestStatus.COMPLETED)
                    self._notify(
                        quest,
                        "completed",
                        f"✅ Quest 已完成: {quest.title}",
                    )
                    quest.result_summary = f"全部 {len(quest.steps)} 个步骤成功完成"
                    self.store.save(quest)
                else:
                    self.store.update_status(quest.id, QuestStatus.FAILED)
                    self._notify(
                        quest,
                        "failed",
                        f"⚠️ Quest 完成但有 {failed_count} 个步骤失败",
                    )
                    quest.result_summary = (
                        f"{len(quest.steps) - failed_count}/{len(quest.steps)} 步骤成功"
                    )
                    self.store.save(quest)

        except Exception as e:
            self.store.update_status(quest.id, QuestStatus.FAILED)
            quest = self.store.get(quest.id)
            if quest:
                quest.error_message = str(e)
                self.store.save(quest)
            self._notify(
                (
                    Quest(
                        id=quest.id if quest else "unknown",
                        title="",
                        description="",
                        project_path=str(self.project_path),
                    )
                    if quest
                    else None
                ),
                "failed",
                f"❌ Quest 执行失败: {e}",
            )
        finally:
            self._running_quests.pop(quest.id, None)

    def _generate_steps(self, quest: Quest) -> List[QuestStep]:
        """从 SPEC 生成执行步骤"""
        steps = []

        if not quest.spec or not quest.spec.acceptance_criteria:
            # 默认步骤
            steps.append(
                QuestStep(
                    step_id="S1",
                    title="分析需求",
                    description=f"分析并理解: {quest.description}",
                    agent="analyst",
                )
            )
            steps.append(
                QuestStep(
                    step_id="S2",
                    title="规划实现",
                    description="制定实现计划",
                    agent="planner",
                )
            )
            steps.append(
                QuestStep(
                    step_id="S3",
                    title="执行编码",
                    description="按照计划执行编码",
                    agent="executor",
                )
            )
            steps.append(
                QuestStep(
                    step_id="S4",
                    title="验证结果",
                    description="运行测试验证",
                    agent="verifier",
                )
            )
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

        # 最后的代码审查
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

        # 构建 omc 命令
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

        # 在后台进程中运行
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

        return output[:2000]  # 限制结果长度

    # ============================================================
    # 控制操作
    # ============================================================

    def stop(self, quest_id: str) -> bool:
        """停止正在运行的 Quest"""
        task = self._running_quests.get(quest_id)
        if task:
            task.cancel()
            self._running_quests.pop(quest_id, None)
            self.store.update_status(quest_id, QuestStatus.CANCELLED)
            return True
        return False

    def is_running(self, quest_id: str) -> bool:
        """检查 Quest 是否在运行"""
        return quest_id in self._running_quests

    def cancel(self, quest_id: str) -> bool:
        """取消 Quest（不中断正在运行的，但标记为取消）"""
        self.stop(quest_id)
        return bool(self.store.update_status(quest_id, QuestStatus.CANCELLED))

    def pause(self, quest_id: str) -> bool:
        """暂停 Quest"""
        self.stop(quest_id)
        return bool(self.store.update_status(quest_id, QuestStatus.PAUSED))

    def resume(self, quest_id: str) -> Optional[Quest]:
        """恢复暂停的 Quest"""
        quest = self.store.get(quest_id)
        if quest and quest.status == QuestStatus.PAUSED:
            self.store.update_status(quest_id, QuestStatus.EXECUTING)
            quest = self.store.get(quest_id)
            if quest:
                self.start(quest)
            return quest
        return None
