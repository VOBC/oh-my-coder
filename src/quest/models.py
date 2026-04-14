"""
Quest Mode 数据模型

Quest = 异步自主编程任务
一个 Quest 包含：描述、生成的 SPEC、执行状态、结果
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuestStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"  # 等待生成 SPEC
    SPEC_GENERATING = "spec_generating"  # 正在生成 SPEC
    SPEC_READY = "spec_ready"  # SPEC 已就绪，等待用户确认
    EXECUTING = "executing"  # 后台执行中
    PENDING_REVIEW = "pending_review"  # 步骤执行完，等待用户验收
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 取消
    PAUSED = "paused"  # 暂停（等待用户输入）


class QuestPriority(str, Enum):
    """优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================
# Pydantic 模型（用于 CLI 展示和 API）
# ============================================================


class SpecSection(BaseModel):
    """SPEC 文档章节"""

    title: str = Field(..., description="章节标题")
    content: str = Field(..., description="章节内容")
    order: int = Field(default=0, description="顺序")


class AcceptanceCriteria(BaseModel):
    """验收标准"""

    id: str = Field(..., description="标准 ID，格式 AC1, AC2...")
    description: str = Field(..., description="验收标准描述")
    testable: bool = Field(default=True, description="是否可自动测试")


class QuestSpec(BaseModel):
    """任务规格文档"""

    title: str = Field(..., description="任务标题")
    overview: str = Field(..., description="任务概述")
    motivation: str = Field(..., description="为什么要做这个任务")
    scope: List[str] = Field(default_factory=list, description="包含范围")
    out_of_scope: List[str] = Field(default_factory=list, description="不包含范围")
    acceptance_criteria: List[AcceptanceCriteria] = Field(
        default_factory=list, description="验收标准"
    )
    risks: List[str] = Field(default_factory=list, description="风险提示")
    estimated_time: str = Field(default="1h", description="预估耗时")
    sections: List[SpecSection] = Field(default_factory=list, description="额外章节")

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = [
            f"# {self.title}",
            "",
            "## 概述",
            self.overview,
            "",
            "## 动机",
            self.motivation,
            "",
        ]

        if self.scope:
            lines.extend(["## 包含范围", *[f"- {s}" for s in self.scope], ""])

        if self.out_of_scope:
            lines.extend(["## 不包含范围", *[f"- {s}" for s in self.out_of_scope], ""])

        if self.acceptance_criteria:
            lines.append("## 验收标准")
            for ac in self.acceptance_criteria:
                lines.append(f"- [ ] **[{ac.id}]** {ac.description}")
            lines.append("")

        if self.risks:
            lines.extend(["## 风险提示", *[f"- ⚠️ {r}" for r in self.risks], ""])

        for section in sorted(self.sections, key=lambda s: s.order):
            lines.extend([f"## {section.title}", section.content, ""])

        lines.extend(
            [
                "---",
                f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            ]
        )

        return "\n".join(lines)


class QuestStep(BaseModel):
    """Quest 执行步骤"""

    step_id: str = Field(..., description="步骤 ID")
    title: str = Field(..., description="步骤标题")
    description: str = Field(..., description="步骤描述")
    agent: str = Field(..., description="执行的 Agent")
    status: QuestStatus = Field(default=QuestStatus.PENDING)
    result: Optional[str] = Field(None, description="步骤结果")
    error: Optional[str] = Field(None, description="错误信息")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Quest(BaseModel):
    """Quest 任务"""

    id: str = Field(..., description="Quest ID（UUID）")
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="用户原始需求描述")
    project_path: str = Field(..., description="项目路径")
    status: QuestStatus = Field(default=QuestStatus.PENDING)
    priority: QuestPriority = Field(default=QuestPriority.MEDIUM)
    spec: Optional[QuestSpec] = Field(None, description="生成的 SPEC")
    spec_path: Optional[str] = Field(None, description="SPEC 文件路径")
    steps: List[QuestStep] = Field(default_factory=list, description="执行步骤")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_summary: Optional[str] = None
    output_dir: str = Field(default=".omc/quests", description="输出目录")

    def duration(self) -> Optional[float]:
        """返回执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        if self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None

    def progress(self) -> float:
        """返回完成进度 0.0 - 1.0"""
        if not self.steps:
            if self.status == QuestStatus.SPEC_READY:
                return 0.0
            if self.status in (
                QuestStatus.COMPLETED,
                QuestStatus.FAILED,
                QuestStatus.CANCELLED,
            ):
                return 1.0
            return 0.0
        completed = sum(1 for s in self.steps if s.status == QuestStatus.COMPLETED)
        return completed / len(self.steps)

    def to_summary(self) -> str:
        """转换为摘要字符串"""
        duration = self.duration()
        duration_str = f"{duration:.0f}s" if duration else "进行中"
        progress = int(self.progress() * 100)
        return (
            f"[{self.status.value:16}] [{self.priority.value:8}] "
            f"{self.title[:40]} | {progress}% | {duration_str}"
        )


# ============================================================
# CLI 输出格式
# ============================================================


@dataclass
class QuestDisplay:
    """Quest CLI 展示格式"""

    id: str
    title: str
    status: QuestStatus
    priority: QuestPriority
    progress_bar: str  # e.g. "██░░░░░░░░" 50%
    duration: str
    created_at: str

    @classmethod
    def from_quest(cls, quest: Quest) -> "QuestDisplay":
        progress = int(quest.progress() * 10)
        bar = "█" * progress + "░" * (10 - progress)
        duration = quest.duration()
        duration_str = f"{duration:.0f}s" if duration else "进行中"
        return cls(
            id=quest.id[:8],
            title=quest.title[:45],
            status=quest.status,
            priority=quest.priority,
            progress_bar=f"{bar} {int(quest.progress() * 100)}%",
            duration=duration_str,
            created_at=quest.created_at.strftime("%m-%d %H:%M"),
        )


# ============================================================
# 通知模型
# ============================================================


@dataclass
class QuestNotification:
    """Quest 通知"""

    quest_id: str
    title: str
    event: str  # "started" | "spec_ready" | "step_completed" | "completed" | "failed"
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
