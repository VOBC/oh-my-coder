"""
Oh My Coder CLI - 命令行入口

使用 typer 构建友好的 CLI 界面。

主要命令：
- omc run <task>         # 执行任务
- omc explore            # 探索代码库
- omc workflow <name>    # 执行预定义工作流
- omc agents             # 列出所有 Agent
- omc status             # 查看状态
"""
import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.router import ModelRouter, RouterConfig
from .core.orchestrator import Orchestrator
from .agents.base import list_agents

app = typer.Typer(
    name="omc",
    help="Oh My Coder - 多智能体编程助手",
    add_completion=False,
)

console = Console()


@app.command()
def run(
    task: str = typer.Argument(..., help="任务描述"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
    model: str = typer.Option("deepseek", "--model", "-m", help="模型选择"),
    workflow: str = typer.Option("build", "--workflow", "-w", help="工作流名称"),
):
    """执行编程任务"""
    console.print(Panel.fit(
        f"[bold green]Oh My Coder[/bold green]\n"
        f"任务: {task}\n"
        f"项目: {project_path}\n"
        f"工作流: {workflow}",
        title="🚀 启动",
    ))
    
    # 初始化路由器和编排器
    router = _init_router()
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
            console.print(f"[red]错误: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def explore(
    project_path: Path = typer.Argument(".", help="项目路径"),
):
    """探索代码库"""
    console.print(f"[bold]🔍 探索项目: {project_path}[/bold]")
    
    router = _init_router()
    orchestrator = Orchestrator(router)
    
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
        console.print(f"[red]探索失败: {result.error}[/red]")


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
        WriterAgent, DesignerAgent, SecurityReviewerAgent
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
        ("critic", CriticAgent.description, CriticAgent.default_tier),
        ("writer", WriterAgent.description, WriterAgent.default_tier),
        ("designer", DesignerAgent.description, DesignerAgent.default_tier),
        ("security-reviewer", SecurityReviewerAgent.description, SecurityReviewerAgent.default_tier),
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
    import os
    api_keys = {
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
        "WENXIN_API_KEY": os.getenv("WENXIN_API_KEY"),
        "TONGYI_API_KEY": os.getenv("TONGYI_API_KEY"),
        "GLM_API_KEY": os.getenv("GLM_API_KEY"),
    }
    
    console.print("[bold]API Keys:[/bold]")
    for key, value in api_keys.items():
        status = "✓ 已配置" if value else "✗ 未配置"
        color = "green" if value else "red"
        console.print(f"  {key}: [{color}]{status}[/{color}]")
    
    # 检查路由器
    try:
        router = _init_router()
        stats = router.get_stats()
        console.print(f"\n[bold]路由器统计:[/bold]")
        console.print(f"  总请求数: {stats['total_requests']}")
        console.print(f"  总成本: ¥{stats['total_cost']:.4f}")
    except Exception as e:
        console.print(f"\n[red]路由器初始化失败: {e}[/red]")


def _init_router() -> ModelRouter:
    """初始化模型路由器"""
    config = RouterConfig()
    
    if not config.deepseek_api_key:
        console.print("[yellow]警告: DEEPSEEK_API_KEY 未配置[/yellow]")
        console.print("请设置环境变量: export DEEPSEEK_API_KEY=your_key")
    
    return ModelRouter(config)


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
