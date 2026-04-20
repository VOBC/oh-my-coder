"""
TUI 交互界面 - 简易交互界面

提供基于终端的交互式界面，快速选择 Agent/工作流。
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel
from rich import box

app = typer.Typer(help="TUI 交互界面 - 简易终端交互")
console = Console()

# 工作流选项
WORKFLOWS = [
    ("explore", "探索代码库", "了解项目结构和代码组织"),
    ("build", "构建/开发", "实现新功能或重构代码"),
    ("debug", "调试修复", "定位和修复 Bug"),
    ("review", "代码审查", "审查代码质量和安全性"),
    ("test", "测试生成", "生成单元测试和集成测试"),
    ("pair", "结对编程", "与 AI 一起协作开发"),
    ("autopilot", "自动驾驶", "全自动完成复杂任务"),
]

# Agent 分类
AGENT_CATEGORIES = {
    "构建/分析": [
        "ExploreAgent",
        "AnalystAgent",
        "PlannerAgent",
        "ArchitectAgent",
        "ExecutorAgent",
        "VerifierAgent",
        "DebuggerAgent",
        "TracerAgent",
        "PerformanceAgent",
    ],
    "审查": [
        "CodeReviewerAgent",
        "SecurityReviewerAgent",
    ],
    "领域": [
        "TestEngineerAgent",
        "DesignerAgent",
        "VisionAgent",
        "DocumentAgent",
        "WriterAgent",
        "ScientistAgent",
        "GitMasterAgent",
        "CodeSimplifierAgent",
        "QATesterAgent",
        "DatabaseAgent",
        "APIAgent",
        "DevOpsAgent",
        "UMLAgent",
        "MigrationAgent",
        "AuthAgent",
        "DataAgent",
    ],
    "协调": [
        "PromptAgent",
        "SelfImprovingAgent",
        "SkillManageAgent",
        "CriticAgent",
    ],
}


@app.command()
def start(
    task: Optional[str] = typer.Argument(None, help="任务描述（可选）"),
):
    """启动交互式 TUI 界面"""
    console.print(
        Panel.fit(
            "[bold cyan]🤖 Oh My Coder TUI[/bold cyan]\n"
            "[dim]快速选择 Agent 和工作流[/dim]",
            border_style="cyan",
        )
    )

    # 如果直接提供了任务，直接执行
    if task:
        console.print(f"\n[yellow]任务:[/yellow] {task}")
        _select_workflow(task)
        return

    # 交互式选择
    console.print("\n[bold]请选择操作:[/bold]\n")

    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("编号", style="cyan", width=4)
    table.add_column("操作", style="white")
    table.add_column("说明", style="dim")

    for i, (key, desc, detail) in enumerate(WORKFLOWS, 1):
        table.add_row(str(i), f"[bold]{key}[/bold]", detail)

    console.print(table)

    # 选择工作流
    choice = Prompt.ask(
        "\n[bold]选择工作流[/bold] (输入编号或名称)",
        choices=[str(i) for i in range(1, len(WORKFLOWS) + 1)]
        + [w[0] for w in WORKFLOWS],
        default="1",
    )

    # 解析选择
    if choice.isdigit():
        workflow = WORKFLOWS[int(choice) - 1][0]
    else:
        workflow = choice

    _select_workflow(workflow)


def _select_workflow(workflow: str):
    """选择工作流后，提示输入任务"""
    console.print(f"\n[green]✓[/green] 已选择工作流: [bold]{workflow}[/bold]")

    task = Prompt.ask(
        "\n[bold]请描述你的任务[/bold]",
        default="",
    )

    if not task:
        console.print("[yellow]未输入任务，请使用 'omc run' 命令直接运行[/yellow]")
        return

    console.print(f"\n[green]✓[/green] 任务: {task}")
    console.print("\n[cyan]运行命令:[/cyan]")
    console.print(f'  [bold]omc run[/bold] "{task}" --workflow {workflow}')

    # 询问是否立即执行
    run_now = Prompt.ask(
        "\n[bold]立即执行?[/bold]",
        choices=["y", "n"],
        default="n",
    )

    if run_now == "y":
        console.print("\n[yellow]正在启动 omc run...[/yellow]")
        # 这里可以调用 orchestrator 执行任务
        console.print("[dim]（实际执行功能开发中）[/dim]")
    else:
        console.print("\n[dim]请手动运行上述命令[/dim]")


@app.command("agents")
def list_agents():
    """列出所有 Agent"""
    console.print(
        Panel.fit(
            "[bold cyan]🤖 Agent 清单[/bold cyan]\n" "[dim]共 31 个专业 Agent[/dim]",
            border_style="cyan",
        )
    )

    for category, agents in AGENT_CATEGORIES.items():
        table = Table(title=f"\n[bold]{category}[/bold]", box=box.SIMPLE)
        table.add_column("Agent", style="cyan")
        table.add_column("数量", style="dim", width=6)

        for agent in agents:
            table.add_row(agent, "")

        # 只显示最后一行的数量
        for i, row in enumerate(table.rows):
            if i < len(table.rows) - 1:
                row.style = None

        console.print(table)

    console.print(
        f"\n[dim]共 {sum(len(a) for a in AGENT_CATEGORIES.values())} 个 Agent[/dim]"
    )


@app.command("workflows")
def list_workflows():
    """列出所有工作流"""
    table = Table(
        title="[bold cyan]📋 工作流清单[/bold cyan]",
        box=box.ROUNDED,
    )
    table.add_column("工作流", style="cyan")
    table.add_column("说明", style="white")
    table.add_column("适用场景", style="dim")

    scenario_map = {
        "explore": "了解新项目、代码审查",
        "build": "新功能开发、代码重构",
        "debug": "Bug 定位、错误修复",
        "review": "代码质量检查、安全审计",
        "test": "单元测试、集成测试",
        "pair": "协作开发、学习编码",
        "autopilot": "复杂任务、全自动处理",
    }

    for key, desc, _ in WORKFLOWS:
        table.add_row(
            f"[bold]{key}[/bold]",
            desc,
            scenario_map.get(key, ""),
        )

    console.print(table)


if __name__ == "__main__":
    app()
