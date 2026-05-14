from __future__ import annotations

from typing import Optional

"""
Models Recommend CLI - 模型精选推荐

命令：
- omc models --recommend              # 显示所有类型推荐表
- omc models --recommend --task coding # 按任务类型筛选推荐
"""


import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# ── 推荐数据 ──────────────────────────────────────────────────

RECOMMENDATIONS: dict[str, list[dict]] = {
    "coding": [
        {
            "model": "deepseek-chat",
            "provider": "DeepSeek",
            "reason": "代码生成与补全能力强，支持 128K 上下文",
            "free_quota": "500万 tokens/月",
        },
        {
            "model": "qwen2.5-coder-32b-instruct",
            "provider": "通义千问",
            "reason": "专为代码场景优化，多语言编程表现出色",
            "free_quota": "500万 tokens/月",
        },
        {
            "model": "glm-4-flash",
            "provider": "智谱 AI",
            "reason": "代码理解与生成速度快，零成本起步",
            "free_quota": "免费无限量",
        },
    ],
    "reasoning": [

        {
            "model": "qwen3-235b-a22b",
            "provider": "通义千问",
            "reason": "MoE 架构推理出色，思维链完整透明",
            "free_quota": "500万 tokens/月",
        },
        {
            "model": "glm-4-plus",
            "provider": "智谱 AI",
            "reason": "复杂推理与知识问答表现优异",
            "free_quota": "赠送额度",
        },
    ],
    "creative": [
        {
            "model": "qwen-max",
            "provider": "通义千问",
            "reason": "创意写作与多风格文本生成能力突出",
            "free_quota": "500万 tokens/月",
        },
        {
            "model": "deepseek-chat",
            "provider": "DeepSeek",
            "reason": "长文本创作流畅，中文表达自然",
            "free_quota": "500万 tokens/月",
        },
        {
            "model": "glm-4-flash",
            "provider": "智谱 AI",
            "reason": "快速生成创意内容，零成本迭代",
            "free_quota": "免费无限量",
        },
    ],
    "fast": [
        {
            "model": "glm-4-flash",
            "provider": "智谱 AI",
            "reason": "响应速度极快，适合高频调用场景",
            "free_quota": "免费无限量",
        },
        {
            "model": "deepseek-chat",
            "provider": "DeepSeek",
            "reason": "首 token 延迟低，吞吐量大",
            "free_quota": "500万 tokens/月",
        },
        {
            "model": "qwen2.5-7b-instruct",
            "provider": "通义千问",
            "reason": "小模型极速推理，适合简单任务",
            "free_quota": "500万 tokens/月",
        },
    ],
    "chat": [
        {
            "model": "glm-4-flash",
            "provider": "智谱 AI",
            "reason": "日常对话流畅自然，完全免费",
            "free_quota": "免费无限量",
        },
        {
            "model": "deepseek-chat",
            "provider": "DeepSeek",
            "reason": "对话连贯性好，知识面广",
            "free_quota": "500万 tokens/月",
        },
        {
            "model": "qwen-turbo",
            "provider": "通义千问",
            "reason": "轻量对话模型，响应快成本低",
            "free_quota": "500万 tokens/月",
        },
    ],
}

TASK_ALIASES: dict[str, str] = {
    "code": "coding",
    "写代码": "coding",
    "编程": "coding",
    "推理": "reasoning",
    "逻辑": "reasoning",
    "创意": "creative",
    "写作": "creative",
    "快": "fast",
    "速度": "fast",
    "聊天": "chat",
    "对话": "chat",
}

VALID_TASKS = list(RECOMMENDATIONS.keys())


def _resolve_task(task: str) -> str:
    """解析任务类型（支持别名）"""
    task_lower = task.lower().strip()
    if task_lower in VALID_TASKS:
        return task_lower
    if task_lower in TASK_ALIASES:
        return TASK_ALIASES[task_lower]
    return task_lower


def _show_all_recommendations() -> None:
    """显示所有类型的推荐表"""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🏆 模型精选推荐[/bold cyan]  — 免费模型，按场景优选",
            border_style="cyan",
        )
    )
    console.print()

    for task_type, models in RECOMMENDATIONS.items():
        table = Table(
            title=f"📦 {task_type.upper()}",
            show_lines=False,
            title_style="bold yellow",
            expand=True,
        )
        table.add_column("模型", style="cyan", no_wrap=True)
        table.add_column("提供商", style="blue")
        table.add_column("推荐理由", style="white", no_wrap=False)
        table.add_column("免费额度", style="green")

        for m in models:
            table.add_row(m["model"], m["provider"], m["reason"], m["free_quota"])

        console.print(table)
        console.print()

    console.print(
        "[dim]💡 使用 [cyan]omc models --recommend --task <type>[/cyan] 查看特定类型推荐[/dim]"
    )
    console.print(f"[dim]   可用类型: {', '.join(VALID_TASKS)}[/dim]")
    console.print()


def _show_task_recommendation(task: str) -> None:
    """显示特定任务类型的推荐"""
    resolved = _resolve_task(task)

    if resolved not in RECOMMENDATIONS:
        console.print(f"[red]✗ 未知任务类型: {task}[/red]")
        console.print(f"[dim]可用类型: {', '.join(VALID_TASKS)}[/dim]")
        raise typer.Exit(1)

    models = RECOMMENDATIONS[resolved]
    label = resolved.upper()

    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]🏆 {label} 场景推荐[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    table = Table(show_lines=False, expand=True)
    table.add_column("模型", style="cyan", no_wrap=True)
    table.add_column("提供商", style="blue")
    table.add_column("推荐理由", style="white", no_wrap=False)
    table.add_column("免费额度", style="green")

    for m in models:
        table.add_row(m["model"], m["provider"], m["reason"], m["free_quota"])

    console.print(table)
    console.print()


def show_recommend(
    task: Optional[str] = typer.Option(
        None, "--task", "-t", help="任务类型: coding/reasoning/creative/fast/chat"
    ),
) -> None:
    """
    模型精选推荐 — 按场景推荐免费模型

    示例:
        omc models --recommend
        omc models --recommend --task coding
        omc models --recommend --task fast
    """
    if task:
        _show_task_recommendation(task)
    else:
        _show_all_recommendations()
