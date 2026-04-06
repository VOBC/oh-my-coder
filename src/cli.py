"""
Oh My Coder CLI - 命令行入口

使用 typer 构建友好的 CLI 界面。

主要命令：
- omc run <task>         # 执行任务
- omc explore            # 探索代码库
- omc agents             # 列出所有 Agent
- omc status             # 查看状态
- omc --version          # 显示版本
- omc --help             # 帮助信息
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style

from .core.router import ModelRouter, RouterConfig
from .core.orchestrator import Orchestrator
from .agents.base import list_agents

# 版本信息
__version__ = "0.2.0"
__author__ = "VOBC"
__repo__ = "https://github.com/VOBC/oh-my-coder"

app = typer.Typer(
    name="omc",
    help=f"Oh My Coder v{__version__} - 多智能体 AI 编程助手",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="显示版本信息",
        is_eager=True,
    ),
):
    """Oh My Coder - 多智能体 AI 编程助手"""
    if version:
        _print_version()
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit(
            f"[bold cyan]Oh My Coder[/bold cyan] v{__version__}\n"
            f"[dim]多智能体 AI 编程助手[/dim]\n\n"
            f"[dim]使用 [bold]omc --help[/bold] 查看所有命令[/dim]\n"
            f"[dim]仓库: {__repo__}[/dim]",
            border_style="cyan",
        ))
        raise typer.Exit(0)


def _print_version():
    """打印版本信息"""
    console.print(f"[bold cyan]oh-my-coder[/bold cyan] version [green]{__version__}[/green]")
    console.print(f"[dim]Author: {__author__}[/dim]")
    console.print(f"[dim]Repo: {__repo__}[/dim]")


@app.command()
def run(
    task: str = typer.Argument(..., help="任务描述"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
    model: str = typer.Option("deepseek", "--model", "-m", help="模型选择"),
    workflow: str = typer.Option("build", "--workflow", "-w", help="工作流名称"),
):
    """执行编程任务"""
    # 前置检查
    if not _check_env():
        raise typer.Exit(1)

    console.print(Panel.fit(
        f"[bold green]Oh My Coder[/bold green]\n"
        f"任务: {task}\n"
        f"项目: {project_path}\n"
        f"工作流: {workflow}",
        title="🚀 启动",
    ))

    # 初始化路由器和编排器
    try:
        router = _init_router()
    except SystemExit:
        raise typer.Exit(1)

    orchestrator = Orchestrator(router, state_dir=project_path / ".omc" / "state")

    # 执行工作流
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("执行工作流...", total=None)

        try:
            result = asyncio.run(orchestrator.execute_workflow(
                workflow,
                {
                    "project_path": str(project_path.absolute()),
                    "task": task,
                }
            ))

            # 显示结果
            _display_result(result)

        except Exception as e:
            _print_fatal(
                f"工作流执行出错: {e}",
                hint="可尝试以下方法：\n"
                     "  1. 检查网络连接\n"
                     "  2. 确认 API Key 有效：omc status\n"
                     "  3. 查看详细日志",
            )
            raise typer.Exit(1)


@app.command()
def explore(
    project_path: Path = typer.Argument(".", help="项目路径"),
):
    """探索代码库"""
    if not _check_env():
        raise typer.Exit(1)

    console.print(f"[bold]🔍 探索项目: {project_path}[/bold]")

    try:
        router = _init_router()
    except SystemExit:
        raise typer.Exit(1)

    orchestrator = Orchestrator(router)

    try:
        result = asyncio.run(orchestrator.execute_single_agent(
            "explore",
            {
                "project_path": str(project_path.absolute()),
                "task": "探索代码库并生成项目地图",
            }
        ))

        if result.result:
            console.print(Panel(result.result, title="项目地图"))
        else:
            _print_fatal(f"探索失败: {result.error}")

    except Exception as e:
        _print_fatal(f"探索出错: {e}", hint="确认项目路径存在且可读")
        raise typer.Exit(1)


@app.command()
def agents():
    """列出所有可用 Agent"""
    table = Table(title="可用智能体")
    table.add_column("名称", style="cyan")
    table.add_column("描述")
    table.add_column("层级", style="green")
    
    # 导入所有 Agent
    from .agents import (
        ExploreAgent, AnalystAgent, PlannerAgent, ArchitectAgent, ExecutorAgent,
        VerifierAgent, TestEngineerAgent, CodeReviewerAgent, DebuggerAgent, CriticAgent,
        WriterAgent, DesignerAgent, SecurityReviewerAgent, GitMasterAgent,
        CodeSimplifierAgent, TracerAgent, ScientistAgent, QATesterAgent
    )
    
    agents_list = [
        ("explore", ExploreAgent.description, ExploreAgent.default_tier),
        ("analyst", AnalystAgent.description, AnalystAgent.default_tier),
        ("planner", PlannerAgent.description, PlannerAgent.default_tier),
        ("architect", ArchitectAgent.description, ArchitectAgent.default_tier),
        ("executor", ExecutorAgent.description, ExecutorAgent.default_tier),
        ("verifier", VerifierAgent.description, VerifierAgent.default_tier),
        ("test-engineer", TestEngineerAgent.description, TestEngineerAgent.default_tier),
        ("code-reviewer", CodeReviewerAgent.description, CodeReviewerAgent.default_tier),
        ("debugger", DebuggerAgent.description, DebuggerAgent.default_tier),
        ("tracer", TracerAgent.description, TracerAgent.default_tier),
        ("critic", CriticAgent.description, CriticAgent.default_tier),
        ("writer", WriterAgent.description, WriterAgent.default_tier),
        ("designer", DesignerAgent.description, DesignerAgent.default_tier),
        ("security-reviewer", SecurityReviewerAgent.description, SecurityReviewerAgent.default_tier),
        ("git-master", GitMasterAgent.description, GitMasterAgent.default_tier),
        ("code-simplifier", CodeSimplifierAgent.description, CodeSimplifierAgent.default_tier),
        ("scientist", ScientistAgent.description, ScientistAgent.default_tier),
        ("qa-tester", QATesterAgent.description, QATesterAgent.default_tier),
    ]
    
    for name, desc, tier in agents_list:
        table.add_row(name, desc, tier)
    
    console.print(table)
    
    console.print(f"\n[dim]共 {len(agents_list)} 个智能体[/dim]")


@app.command()
def status():
    """查看系统状态"""
    console.print("[bold]系统状态[/bold]\n")

    # 检查 API Key
    api_keys = {
        "DEEPSEEK_API_KEY": "🟢 生产就绪",
        "KIMI_API_KEY": "🟢 生产就绪",
        "DOUBAO_API_KEY": "🟢 生产就绪",
        "MINIMAX_API_KEY": "🟡 Beta",
        "GLM_API_KEY": "🟡 Beta",
        "TONGYI_API_KEY": "🟡 Beta",
        "WENXIN_API_KEY": "🔴 待完善",
        "HUNYUAN_API_KEY": "🔴 待完善",
    }

    console.print("[bold]模型支持状态:[/bold]")
    for key, status_label in api_keys.items():
        value = os.getenv(key)
        if value:
            console.print(f"  {key}: [{status_label}] 已配置")
        else:
            console.print(f"  {key}: [red]✗ 未配置[/red]")

    # 检查路由器
    console.print()
    try:
        router = _init_router()
        stats = router.get_stats()
        console.print(Panel(
            f"[green]✓ 路由器就绪[/green]\n"
            f"总请求数: [cyan]{stats['total_requests']}[/cyan]\n"
            f"总成本:   [cyan]¥{stats['total_cost']:.4f}[/cyan]",
            title="路由器",
            border_style="green",
        ))
    except Exception as e:
        console.print(Panel(
            f"[red]✗ 路由器初始化失败[/red]\n\n{e}",
            title="路由器",
            border_style="red",
        ))


def _init_router() -> ModelRouter:
    """初始化模型路由器，失败时给出友好提示"""
    config = RouterConfig()

    if not config.deepseek_api_key:
        _print_missing_key_hint("DEEPSEEK_API_KEY", "性价比最高，推荐配置")

    try:
        return ModelRouter(config)
    except Exception as e:
        _print_fatal(f"路由器初始化失败: {e}")


def _print_missing_key_hint(key: str, reason: str = ""):
    """打印缺失 API Key 的友好提示"""
    from rich.columns import Columns
    from rich.text import Text

    console.print()
    console.print(Panel(
        f"[bold red]✗ 未找到 {key}[/bold red]\n\n"
        f"[yellow]请先配置 API Key[/yellow]\n\n"
        f"[dim]推荐:[/dim] DeepSeek — {reason}\n\n"
        f"[cyan]方法一:[/cyan] 设置环境变量\n"
        f"  [green]export {key}=your_key_here[green]\n\n"
        f"[cyan]方法二:[/cyan] 写入 .env 文件\n"
        f"  [green]echo '{key}=your_key_here' >> .env[green]\n\n"
        f"[dim]获取地址:[/dim] https://platform.deepseek.com/",
        title="⚠️ 缺少 API Key",
        border_style="red",
    ))
    console.print()


def _print_fatal(msg: str, hint: str = ""):
    """打印致命错误并退出"""
    from rich.markdown import Markdown

    console.print()
    console.print(Panel(
        f"[bold red]✗ {msg}[/bold red]" + (f"\n\n[cyan]提示:[/cyan] {hint}" if hint else ""),
        title="❌ 执行失败",
        border_style="red",
    ))
    console.print()


def _check_env() -> bool:
    """检查环境是否就绪，返回 True 表示就绪"""
    missing = []
    if not os.getenv("DEEPSEEK_API_KEY"):
        missing.append("DEEPSEEK_API_KEY")
    if missing:
        _print_missing_key_hint(missing[0], "性价比最高，推荐配置")
        return False
    return True


def _display_result(result):
    """显示工作流结果"""
    console.print(f"\n[bold]工作流 {result.workflow_id}[/bold]")
    console.print(f"状态: {_status_color(result.status.value)}")
    console.print(f"执行时间: {result.execution_time:.2f}s")
    console.print(f"Token 使用: {result.total_tokens:,}")
    
    if result.steps_completed:
        console.print(f"\n[green]✓ 已完成步骤:[/green]")
        for step in result.steps_completed:
            console.print(f"  - {step}")
    
    if result.steps_failed:
        console.print(f"\n[red]✗ 失败步骤:[/red]")
        for step in result.steps_failed:
            console.print(f"  - {step}")
    
    if result.error:
        console.print(f"\n[red]错误: {result.error}[/red]")


def _status_color(status: str) -> str:
    """给状态上色"""
    colors = {
        "completed": "[green]已完成[/green]",
        "failed": "[red]失败[/red]",
        "running": "[yellow]运行中[/yellow]",
        "pending": "[dim]等待中[/dim]",
    }
    return colors.get(status, status)


if __name__ == "__main__":
    app()
