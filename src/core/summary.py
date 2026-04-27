"""
任务总结模块 - 自动化任务完成后生成结构化总结

功能：
- 记录工作流执行全过程
- 统计 Token 消耗和成本
- 分析 Agent 执行情况
- 导出多种格式（JSON/TXT/HTML）
- 生成下次优化建议

使用场景：
1. 任务完成后自动生成总结报告
2. 分析 Token 消耗，优化成本
3. 回顾工作流执行情况
4. 团队协作时分享执行结果

使用示例：
    from src.core.summary import generate_summary, print_summary, save_summary

    # 生成总结
    summary = generate_summary(
        task="实现用户认证模块",
        workflow="build",
        completed_steps=[...],
    )

    # 打印到终端
    print_summary(summary)

    # 保存到文件
    save_path = save_summary(summary, format="json")
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


# ============================================================
# 数据模型
# ============================================================
@dataclass
class StepRecord:
    """单个步骤的执行记录"""

    agent: str
    status: str  # "completed" | "failed" | "skipped"
    duration: float  # 秒
    tokens: int = 0
    cost: float = 0.0
    result: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModelUsage:
    """单个模型的调用统计"""

    provider: str
    model_name: str
    calls: int = 0
    tokens: int = 0
    cost: float = 0.0


@dataclass
class TaskSummary:
    """
    任务总结数据类

    Attributes:
        task: 任务描述
        workflow: 工作流名称（build/review/debug/test）
        start_time: 开始时间（ISO 格式）
        end_time: 结束时间（ISO 格式）
        duration_seconds: 总耗时（秒）
        total_tokens: Token 总消耗
        total_cost: 总成本（元）
        steps_completed: 已完成步骤列表
        agent_count: 涉及的 Agent 数量
        models_used: 使用过的模型列表
        success: 是否全部成功
        errors: 错误列表
        recommendations: 优化建议
    """

    task: str
    workflow: str
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0
    steps_completed: list = field(default_factory=list)
    agent_count: int = 0
    models_used: list = field(default_factory=list)
    success: bool = True
    errors: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskSummary":
        return cls(**data)


# ============================================================
# 总结生成
# ============================================================
def generate_summary(
    task: str,
    workflow: str,
    completed_steps: list[dict],
    project_path: str = "",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> TaskSummary:
    """
    根据已完成步骤生成任务总结

    Args:
        task: 任务描述
        workflow: 工作流名称
        completed_steps: 步骤列表，每个 dict 包含:
            - agent: Agent 名称
            - status: 状态（completed/failed/skipped）
            - duration: 耗时（秒）
            - tokens: Token 消耗
            - result: 执行结果描述
            - error: 错误信息（如有）
        project_path: 项目路径

    Returns:
        TaskSummary 对象
    """
    now = datetime.now()
    start = start_time or now
    end = end_time or now

    # 转换步骤
    steps = []
    agents_used = set()
    total_tokens = 0
    total_cost = 0.0
    success = True
    errors = []

    for step_data in completed_steps:
        step = StepRecord(
            agent=step_data.get("agent", "unknown"),
            status=step_data.get("status", "unknown"),
            duration=step_data.get("duration", 0.0),
            tokens=step_data.get("tokens", 0),
            cost=step_data.get("cost", 0.0),
            result=step_data.get("result", ""),
            error=step_data.get("error", ""),
        )
        steps.append(step)

        agents_used.add(step.agent)
        total_tokens += step.tokens
        total_cost += step.cost

        if step.status != "completed":
            success = False
            if step.error:
                errors.append(f"{step.agent}: {step.error}")

    # 估算成本（按 DeepSeek 价格：¥1/百万 Token）
    if total_cost == 0 and total_tokens > 0:
        total_cost = total_tokens / 1_000_000 * 1.0

    # 生成优化建议
    recommendations = _generate_recommendations(
        steps=steps,
        total_cost=total_cost,
        total_tokens=total_tokens,
        workflow=workflow,
    )

    # 推断使用的模型（简化版：从 Agent 名推断）
    models_used = _infer_models(workflow, len(agents_used))

    return TaskSummary(
        task=task,
        workflow=workflow,
        start_time=start.isoformat(),
        end_time=end.isoformat(),
        duration_seconds=(end - start).total_seconds(),
        total_tokens=total_tokens,
        total_cost=total_cost,
        steps_completed=[s.to_dict() for s in steps],
        agent_count=len(agents_used),
        models_used=models_used,
        success=success,
        errors=errors,
        recommendations=recommendations,
    )


def _generate_recommendations(
    steps: list[StepRecord],
    total_cost: float,
    total_tokens: int,
    workflow: str,
) -> list[str]:
    """生成优化建议"""
    recs = []

    # 成本建议
    if total_cost > 1.0:
        recs.append("💡 成本较高，考虑使用 DeepSeek-V3（低成本）处理简单任务")
    elif total_cost > 0.1:
        recs.append("💡 当前成本适中，继续保持")

    # Token 建议
    if total_tokens > 50000:
        recs.append("💡 Token 消耗较高，可考虑减少探索深度或分批处理")

    # 执行时间建议
    total_duration = sum(s.duration for s in steps)
    if total_duration > 60:
        recs.append("💡 执行时间较长，可考虑并行执行独立步骤")

    # 失败建议
    failed_steps = [s for s in steps if s.status == "failed"]
    if failed_steps:
        recs.append(f"⚠️  {len(failed_steps)} 个步骤失败，建议检查相关 Agent 配置")

    if not recs:
        recs.append("✅ 执行效率良好，无需特殊优化")

    return recs


def _infer_models(workflow: str, agent_count: int) -> list[str]:
    """推断使用的模型"""
    if workflow == "build":
        return ["deepseek-chat", "deepseek-chat", "deepseek-reasoner"]
    if workflow == "review":
        return ["deepseek-chat"]
    if workflow == "debug":
        return ["deepseek-reasoner"]
    if workflow == "test":
        return ["deepseek-chat", "deepseek-chat"]
    return ["deepseek-chat"]


# ============================================================
# 打印总结
# ============================================================
def print_summary(summary: TaskSummary) -> None:
    """在终端打印总结（带格式）"""
    status_icon = "✅" if summary.success else "❌"

    print(f"\n{status_icon} 任务: {summary.task}")
    print(f"📋 工作流: {summary.workflow}")
    print(f"⏱️  耗时: {summary.duration_seconds:.1f}s")
    print(f"💰 成本: ¥{summary.total_cost:.4f}")
    print(f"🔢 Token: {summary.total_tokens:,}")
    print(f"🤖 Agent 数: {summary.agent_count}")
    print(f"🔧 模型: {', '.join(summary.models_used)}")

    if summary.steps_completed:
        print("\n📊 执行步骤：")
        for i, step in enumerate(summary.steps_completed, 1):
            icon = (
                "✅"
                if step["status"] == "completed"
                else ("❌" if step["status"] == "failed" else "⏭️")
            )
            agent_short = step["agent"].replace("Agent", "")
            print(
                f"  {i}. {icon} {agent_short:<15} - {step['duration']:.1f}s"
                f" | {step['tokens']:,} tokens | {step['result'][:50]}..."
            )

    if summary.errors:
        print("\n❌ 错误：")
        for err in summary.errors:
            print(f"  • {err}")

    if summary.recommendations:
        print("\n💡 优化建议：")
        for rec in summary.recommendations:
            print(f"  {rec}")


def print_summary_compact(summary: TaskSummary) -> None:
    """紧凑版总结（单行）"""
    status = "✅" if summary.success else "❌"
    print(
        f"{status} [{summary.workflow}] {summary.task[:40]} | "
        f"{summary.duration_seconds:.1f}s | "
        f"¥{summary.total_cost:.4f} | "
        f"{summary.agent_count} agents"
    )


# ============================================================
# 保存与加载
# ============================================================
def save_summary(
    summary: TaskSummary,
    output_dir: Path | None = None,
    format: str = "json",
    filename: str | None = None,
) -> Path:
    """
    保存总结到文件

    Args:
        summary: 总结对象
        output_dir: 输出目录（默认 reports/）
        format: 格式（json/txt/html）
        filename: 自定义文件名

    Returns:
        保存的文件路径
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / "reports"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_task = "".join(c if c.isalnum() else "_" for c in summary.task[:30])
        filename = f"summary_{summary.workflow}_{safe_task}_{timestamp}.{format}"

    filepath = output_dir / filename

    if format == "json":
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, ensure_ascii=False, indent=2)
    elif format == "txt":
        with open(filepath, "w", encoding="utf-8") as f:
            _write_txt_summary(f, summary)
    elif format == "html":
        with open(filepath, "w", encoding="utf-8") as f:
            _write_html_summary(f, summary)
    else:
        raise ValueError(f"不支持的格式: {format}")

    return filepath


def _write_txt_summary(f, summary: TaskSummary) -> None:
    """写入 TXT 格式"""
    f.write("任务总结\n")
    f.write(f"{'=' * 50}\n")
    f.write(f"任务: {summary.task}\n")
    f.write(f"工作流: {summary.workflow}\n")
    f.write(f"状态: {'成功' if summary.success else '失败'}\n")
    f.write(f"耗时: {summary.duration_seconds:.1f}s\n")
    f.write(f"Token: {summary.total_tokens:,}\n")
    f.write(f"成本: ¥{summary.total_cost:.4f}\n")
    f.write("\n执行步骤:\n")
    for step in summary.steps_completed:
        f.write(f"  - {step['agent']}: {step['result']}\n")
    if summary.recommendations:
        f.write("\n优化建议:\n")
        for rec in summary.recommendations:
            f.write(f"  {rec}\n")


def _write_html_summary(f, summary: TaskSummary) -> None:
    """写入 HTML 格式"""
    status_color = "#4CAF50" if summary.success else "#F44336"
    f.write(
        f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>任务总结 - {summary.task[:30]}</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
h1 {{ color: #333; }}
.stat {{ display: inline-block; background: #f5f5f5; padding: 8px 16px; margin: 4px; border-radius: 4px; }}
.step {{ border-left: 3px solid #ddd; padding: 8px 16px; margin: 8px 0; }}
.step.success {{ border-color: #4CAF50; }}
.step.failed {{ border-color: #F44336; }}
.rec {{ background: #fff3cd; padding: 8px 16px; border-radius: 4px; margin: 4px 0; }}
</style>
</head>
<body>
<h1>📋 {summary.task}</h1>
<p>工作流: <strong>{summary.workflow}</strong> |
   状态: <span style="color:{status_color}">{"✅ 成功" if summary.success else "❌ 失败"}</span></p>

<div class="stat">⏱️ {summary.duration_seconds:.1f}s</div>
<div class="stat">💰 ¥{summary.total_cost:.4f}</div>
<div class="stat">🔢 {summary.total_tokens:,} tokens</div>
<div class="stat">🤖 {summary.agent_count} agents</div>

<h2>执行步骤</h2>
"""
    )
    for step in summary.steps_completed:
        cls = "success" if step["status"] == "completed" else "failed"
        icon = "✅" if step["status"] == "completed" else "❌"
        f.write(
            f"""<div class="step {cls}">
<strong>{icon} {step["agent"]}</strong> ({step["duration"]:.1f}s)<br>
{step["result"]}
</div>
"""
        )
    if summary.recommendations:
        f.write("<h2>💡 优化建议</h2>\n")
        for rec in summary.recommendations:
            f.write(f"<div class='rec'>{rec}</div>\n")
    f.write("</body></html>")


def load_summary(filepath: Path) -> TaskSummary:
    """从文件加载总结"""
    filepath = Path(filepath)
    if filepath.suffix == ".json":
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return TaskSummary.from_dict(data)
    raise ValueError(f"不支持的文件格式: {filepath.suffix}")


# ============================================================
# 便捷函数
# ============================================================
def quick_summary(
    task: str,
    workflow: str,
    duration: float,
    tokens: int,
    steps: list[str],
) -> TaskSummary:
    """
    快速生成简单总结（用于不需要完整信息的场景）

    Args:
        task: 任务描述
        workflow: 工作流名称
        duration: 总耗时（秒）
        tokens: Token 总消耗
        steps: 步骤描述列表

    Returns:
        TaskSummary 对象
    """
    completed = [
        {
            "agent": f"Step{i + 1}",
            "status": "completed",
            "duration": 0,
            "tokens": 0,
            "result": s,
        }
        for i, s in enumerate(steps)
    ]
    return generate_summary(
        task=task,
        workflow=workflow,
        completed_steps=completed,
        start_time=datetime.now(),
        end_time=datetime.now(),
    )
