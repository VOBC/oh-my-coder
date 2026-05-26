from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import Optional

"""
omc plan - Plan Mode 命令

只输出改动计划，用户确认后才执行。
"""


from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..agents.planner import PlannerAgent
from ..core.router import ModelRouter, RouterConfig

app = typer.Typer(help="Plan Mode - 先规划后执行")
console = Console()


def _init_router() -> ModelRouter:
    """初始化模型路由器"""
    config = RouterConfig()
    return ModelRouter(config)


def _check_env() -> bool:
    """检查环境配置"""
    import os

    keys = [
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OLLAMA_BASE_URL",
        "DASHSCOPE_API_KEY",
        "QWEN_API_KEY",
        "XAI_API_KEY",
        "ZHIPUAI_API_KEY",
    ]
    if not any(os.getenv(k) for k in keys):
        console.print(
            "[red]❌ 未检测到任何 API Key，请先配置：[/red]\n"
            "  [cyan]omc self-config set deepseek.api_key sk-xxx[/cyan]"
        )
        return False
    return True


@app.command()
def plan(
    task: str = typer.Argument(..., help="自然语言任务描述"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
    model: str = typer.Option("deepseek", "--model", "-m", help="模型选择"),
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认直接执行"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="保存计划到文件"
    ),
):
    """
    Plan Mode - 分析任务并输出改动计划，确认后执行。

    Examples:
        omc plan "给 src/utils.py 加个日志功能"
        omc plan "重构 core/agent.py 的错误处理"
        omc plan "添加用户认证模块" -o plan.md
    """
    # 前置检查
    if not _check_env():
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]Plan Mode[/bold cyan]\n"
            f"任务: [yellow]{task}[/yellow]\n"
            f"项目: [dim]{project_path.absolute()}[/dim]",
            title="📋 规划模式",
        )
    )

    # 初始化
    try:
        router = _init_router()
    except SystemExit:
        raise typer.Exit(1)

    planner = PlannerAgent(model_router=router)

    # Step 1: 生成计划
    console.print("\n[bold]🔍 分析任务...[/bold]")

    from ..agents.base import AgentContext

    context = AgentContext(
        project_path=project_path,
        task_description=task,
    )

    # 调用 planner 生成计划
    import asyncio

    try:
        result = asyncio.run(
            planner._run(
                context,
                prompt=[
                    {
                        "role": "user",
                        "content": f"请为以下任务制定详细的执行计划：\n\n{task}",
                    }
                ],
            )
        )
        output_obj = planner._post_process(result, context)
    except Exception as e:
        console.print(f"[red]❌ 规划失败: {type(e).__name__}[/red]")
        raise typer.Exit(1)

    # Step 2: 展示计划
    plan_data = output_obj.artifacts.get("plan", {})
    execution_order = output_obj.artifacts.get("execution_order", [])

    _display_plan(plan_data, execution_order, console)

    # 保存到文件
    if output:
        _save_plan(plan_data, execution_order, output, console)

    # Step 3: 询问是否执行
    if yes:
        execute = True
    else:
        console.print()
        response = typer.prompt(
            "是否执行此计划？[y/N]",
            default="N",
            show_default=False,
        )
        execute = response.lower() in ("y", "yes")

    if not execute:
        console.print("\n[dim]已取消执行。计划已保存到内存。[/dim]")
        raise typer.Exit(0)

    # Step 4: 执行计划
    console.print("\n[bold green]🚀 开始执行计划...[/bold green]")
    console.print("[dim]提示：实际执行逻辑待实现，当前仅展示计划[/dim]\n")

    # TODO: 接入真实 Orchestrator 执行计划
    # 需先实现 WorkflowLoader 动态加载用户自定义 YAML
    # orchestrator = Orchestrator(router, state_dir=project_path / ".omc" / "state")
    # await orchestrator.run_workflow("build", task)

    console.print("[yellow]⚠️ Plan Mode 执行功能开发中...[/yellow]")
    console.print("当前可使用: [cyan]omc run[/cyan] 命令执行任务")


def _display_plan(
    plan_data: dict, execution_order: list[str], console: Console
) -> None:
    """展示计划"""
    if not plan_data:
        console.print("[yellow]⚠️ 未生成有效计划[/yellow]")
        return

    # 标题和摘要
    title = plan_data.get("title", "未命名计划")
    summary = plan_data.get("summary", "")
    console.print(f"\n[bold cyan]📋 {title}[/bold cyan]")
    if summary:
        console.print(f"[dim]{summary}[/dim]\n")

    # 阶段表格
    phases = plan_data.get("phases", [])
    if phases:
        table = Table(title="执行阶段", show_lines=True)
        table.add_column("阶段", style="cyan", no_wrap=True)
        table.add_column("任务", style="white")
        table.add_column("文件", style="green")
        table.add_column("Agent", style="magenta")

        for phase in phases:
            phase_name = phase.get("name", "?")
            tasks = phase.get("tasks", [])
            task_lines = []
            file_lines = []
            agent_lines = []

            for t in tasks:
                tid = t.get("id", "?")
                ttitle = t.get("title", "?")
                task_lines.append(f"[{tid}] {ttitle}")
                files = t.get("files_to_modify", [])
                file_lines.append(", ".join(files) if files else "-")
                agent_lines.append(t.get("agent", "?"))

            table.add_row(
                phase_name,
                "\n".join(task_lines),
                "\n".join(file_lines),
                "\n".join(agent_lines),
            )

        console.print(table)

    # 执行顺序
    if execution_order:
        console.print(
            f"\n[bold]执行顺序:[/bold] [dim]{' → '.join(execution_order[:8])}"
            + ("..." if len(execution_order) > 8 else "")
            + "[/dim]"
        )


def _save_plan(
    plan_data: dict, execution_order: list[str], output: Path, console: Console
) -> None:
    """保存计划到文件"""
    import json

    content = f"""# 执行计划

## 摘要
{plan_data.get("summary", "无")}

## 执行顺序
{" → ".join(execution_order)}

## 详细计划

```json
{json.dumps(plan_data, indent=2, ensure_ascii=False)}
```
"""
    output.write_text(content, encoding="utf-8")
    console.print(f"\n[green]✓ 计划已保存到:[/green] [dim]{output}[/dim]")
