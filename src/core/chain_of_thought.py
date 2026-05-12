"""
思维链可视化 — 记录和展示 Agent 推理过程

功能：
1. 捕获 Agent 的思维链（推理步骤、决策依据）
2. 结构化存储推理过程
3. 可视化展示（文本/JSON/HTML）
4. 支持回溯和调试
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ReasoningStepType(Enum):
    """推理步骤类型"""
    ANALYSIS = "analysis"           # 分析问题
    PLANNING = "planning"           # 制定计划
    DECISION = "decision"           # 做出决策
    EXECUTION = "execution"         # 执行操作
    OBSERVATION = "observation"     # 观察结果
    REFLECTION = "reflection"       # 反思总结
    CORRECTION = "correction"       # 错误修正


class ConfidenceLevel(Enum):
    """置信度级别"""
    HIGH = "high"       # 高置信度
    MEDIUM = "medium"   # 中等置信度
    LOW = "low"         # 低置信度
    UNCERTAIN = "uncertain"  # 不确定


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_id: str
    step_type: ReasoningStepType
    agent_name: str
    description: str
    reasoning: str                    # 推理过程
    evidence: list[str]               # 支持证据
    conclusion: str                   # 结论
    confidence: ConfidenceLevel
    timestamp: str
    duration_ms: int = 0
    parent_step_id: Optional[str] = None  # 父步骤（用于层级结构）
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "agent_name": self.agent_name,
            "description": self.description,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "conclusion": self.conclusion,
            "confidence": self.confidence.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "parent_step_id": self.parent_step_id,
            "metadata": self.metadata,
        }


@dataclass
class ChainOfThought:
    """思维链"""
    chain_id: str
    task_description: str
    agent_name: str
    steps: list[ReasoningStep] = field(default_factory=list)
    start_time: str = ""
    end_time: Optional[str] = None
    status: str = "running"  # running / completed / failed
    final_conclusion: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "task_description": self.task_description,
            "agent_name": self.agent_name,
            "steps": [s.to_dict() for s in self.steps],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "final_conclusion": self.final_conclusion,
            "metadata": self.metadata,
        }

    def add_step(self, step: ReasoningStep) -> None:
        """添加推理步骤"""
        self.steps.append(step)

    def complete(self, conclusion: str = "") -> None:
        """完成思维链"""
        self.status = "completed"
        self.end_time = datetime.now().isoformat()
        self.final_conclusion = conclusion

    def fail(self, error: str = "") -> None:
        """标记为失败"""
        self.status = "failed"
        self.end_time = datetime.now().isoformat()
        self.final_conclusion = f"失败: {error}"


class ChainOfThoughtRecorder:
    """思维链记录器"""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".omc" / "chains"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.active_chains: dict[str, ChainOfThought] = {}

    def start_chain(
        self,
        task_description: str,
        agent_name: str,
        metadata: Optional[dict] = None,
    ) -> ChainOfThought:
        """开始记录思维链"""
        chain = ChainOfThought(
            chain_id=f"chain-{uuid.uuid4().hex[:8]}",
            task_description=task_description,
            agent_name=agent_name,
            start_time=datetime.now().isoformat(),
            metadata=metadata or {},
        )
        self.active_chains[chain.chain_id] = chain
        return chain

    def add_step(
        self,
        chain_id: str,
        step_type: ReasoningStepType,
        description: str,
        reasoning: str,
        evidence: Optional[list[str]] = None,
        conclusion: str = "",
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        parent_step_id: Optional[str] = None,
    ) -> Optional[ReasoningStep]:
        """添加推理步骤"""
        chain = self.active_chains.get(chain_id)
        if not chain:
            return None

        step = ReasoningStep(
            step_id=f"step-{len(chain.steps)+1:03d}",
            step_type=step_type,
            agent_name=chain.agent_name,
            description=description,
            reasoning=reasoning,
            evidence=evidence or [],
            conclusion=conclusion,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
            parent_step_id=parent_step_id,
        )
        chain.add_step(step)
        return step

    def complete_chain(self, chain_id: str, conclusion: str = "") -> None:
        """完成思维链"""
        chain = self.active_chains.get(chain_id)
        if chain:
            chain.complete(conclusion)
            self._save_chain(chain)

    def fail_chain(self, chain_id: str, error: str = "") -> None:
        """标记思维链失败"""
        chain = self.active_chains.get(chain_id)
        if chain:
            chain.fail(error)
            self._save_chain(chain)

    def get_chain(self, chain_id: str) -> Optional[ChainOfThought]:
        """获取思维链"""
        return self.active_chains.get(chain_id)

    def list_chains(self, agent_name: Optional[str] = None) -> list[ChainOfThought]:
        """列出思维链"""
        chains = list(self.active_chains.values())
        if agent_name:
            chains = [c for c in chains if c.agent_name == agent_name]
        return chains

    def _save_chain(self, chain: ChainOfThought) -> None:
        """保存思维链到文件"""
        filepath = self.storage_dir / f"{chain.chain_id}.json"
        filepath.write_text(
            json.dumps(chain.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class ChainVisualizer:
    """思维链可视化"""

    @staticmethod
    def to_text(chain: ChainOfThought) -> str:
        """转换为文本格式"""
        lines = [
            "=" * 60,
            f"思维链: {chain.chain_id}",
            f"任务: {chain.task_description}",
            f"Agent: {chain.agent_name}",
            f"状态: {chain.status}",
            f"时间: {chain.start_time} ~ {chain.end_time or '进行中'}",
            "=" * 60,
            "",
        ]

        for step in chain.steps:
            icon = {
                ReasoningStepType.ANALYSIS: "🔍",
                ReasoningStepType.PLANNING: "📋",
                ReasoningStepType.DECISION: "🎯",
                ReasoningStepType.EXECUTION: "⚡",
                ReasoningStepType.OBSERVATION: "👁️",
                ReasoningStepType.REFLECTION: "💭",
                ReasoningStepType.CORRECTION: "🔧",
            }.get(step.step_type, "•")

            confidence_icon = {
                ConfidenceLevel.HIGH: "✓",
                ConfidenceLevel.MEDIUM: "~",
                ConfidenceLevel.LOW: "?",
                ConfidenceLevel.UNCERTAIN: "!",
            }.get(step.confidence, "")

            lines.extend([
                f"{icon} [{step.step_id}] {step.step_type.value.upper()}",
                f"   描述: {step.description}",
                f"   推理: {step.reasoning[:100]}..." if len(step.reasoning) > 100 else f"   推理: {step.reasoning}",
            ])

            if step.evidence:
                lines.append(f"   证据: {', '.join(step.evidence[:3])}")
            if step.conclusion:
                lines.append(f"   结论: {step.conclusion}")

            lines.append(f"   置信度: {confidence_icon} {step.confidence.value}")
            lines.append("")

        if chain.final_conclusion:
            lines.extend([
                "-" * 60,
                f"最终结论: {chain.final_conclusion}",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)

    @staticmethod
    def to_html(chain: ChainOfThought) -> str:
        """转换为 HTML 格式"""
        steps_html = []
        for step in chain.steps:
            color = {
                ReasoningStepType.ANALYSIS: "#3b82f6",
                ReasoningStepType.PLANNING: "#8b5cf6",
                ReasoningStepType.DECISION: "#10b981",
                ReasoningStepType.EXECUTION: "#f59e0b",
                ReasoningStepType.OBSERVATION: "#06b6d4",
                ReasoningStepType.REFLECTION: "#ec4899",
                ReasoningStepType.CORRECTION: "#ef4444",
            }.get(step.step_type, "#6b7280")

            steps_html.append(f"""
            <div class="step" style="border-left: 4px solid {color}; padding-left: 12px; margin: 12px 0;">
                <div style="color: {color}; font-weight: bold;">
                    {step.step_type.value.upper()} [{step.step_id}]
                </div>
                <div style="margin: 4px 0;"><b>描述:</b> {step.description}</div>
                <div style="margin: 4px 0; color: #666;"><b>推理:</b> {step.reasoning[:200]}</div>
                {f'<div style="margin: 4px 0;"><b>结论:</b> {step.conclusion}</div>' if step.conclusion else ''}
                <div style="font-size: 0.9em; color: #999;">
                    置信度: {step.confidence.value} | {step.timestamp}
                </div>
            </div>
            """)

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>思维链 - {chain.chain_id}</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        .header {{ background: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .step {{ background: #fafafa; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🧠 思维链可视化</h2>
        <p><b>任务:</b> {chain.task_description}</p>
        <p><b>Agent:</b> {chain.agent_name} | <b>状态:</b> {chain.status}</p>
    </div>
    {''.join(steps_html)}
    {f'<div style="margin-top: 20px; padding: 16px; background: #e0f2fe; border-radius: 8px;"><b>最终结论:</b> {chain.final_conclusion}</div>' if chain.final_conclusion else ''}
</body>
</html>"""

    @staticmethod
    def to_mermaid(chain: ChainOfThought) -> str:
        """转换为 Mermaid 流程图"""
        lines = ["graph TD"]

        for step in chain.steps:
            node_id = step.step_id.replace("-", "_")
            label = f"{step.step_type.value[:3]}: {step.description[:30]}"
            lines.append(f"    {node_id}[{label}]")

            if step.parent_step_id:
                parent_id = step.parent_step_id.replace("-", "_")
                lines.append(f"    {parent_id} --> {node_id}")

        return "\n".join(lines)


# ===== 便捷函数 =====

def create_recorder() -> ChainOfThoughtRecorder:
    """创建思维链记录器"""
    return ChainOfThoughtRecorder()


def visualize_chain(chain: ChainOfThought, format: str = "text") -> str:
    """可视化思维链

    Args:
        chain: 思维链
        format: 输出格式 (text/html/mermaid)

    Returns:
        格式化字符串
    """
    if format == "html":
        return ChainVisualizer.to_html(chain)
    elif format == "mermaid":
        return ChainVisualizer.to_mermaid(chain)
    else:
        return ChainVisualizer.to_text(chain)
