"""
Oh My Coder CLI - 命令行入口

使用 typer 构建友好的 CLI 界面。

主要命令：
- omc run <task>         # 执行任务
- omc explore            # 探索代码库
- omc wiki               # 生成项目 Wiki
- omc agents             # 列出所有 Agent
- omc status             # 查看状态
- omc --version          # 显示版本
- omc --help             # 帮助信息
"""

import asyncio
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .core.orchestrator import Orchestrator
from .core.router import ModelRouter, RouterConfig
from .wiki import WikiGenerator
from .quest import QuestStatus

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
        console.print(
            Panel.fit(
                f"[bold cyan]Oh My Coder[/bold cyan] v{__version__}\n"
                f"[dim]多智能体 AI 编程助手[/dim]\n\n"
                f"[dim]使用 [bold]omc --help[/bold] 查看所有命令[/dim]\n"
                f"[dim]仓库: {__repo__}[/dim]",
                border_style="cyan",
            )
        )
        raise typer.Exit(0)


def _print_version():
    """打印版本信息"""
    console.print(
        f"[bold cyan]oh-my-coder[/bold cyan] version [green]{__version__}[/green]"
    )
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

    console.print(
        Panel.fit(
            f"[bold green]Oh My Coder[/bold green]\n"
            f"任务: {task}\n"
            f"项目: {project_path}\n"
            f"工作流: {workflow}",
            title="🚀 启动",
        )
    )

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
            result = asyncio.run(
                orchestrator.execute_workflow(
                    workflow,
                    {
                        "project_path": str(project_path.absolute()),
                        "task": task,
                    },
                )
            )

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
        result = asyncio.run(
            orchestrator.execute_single_agent(
                "explore",
                {
                    "project_path": str(project_path.absolute()),
                    "task": "探索代码库并生成项目地图",
                },
            )
        )

        if result.result:
            console.print(Panel(result.result, title="项目地图"))
        else:
            _print_fatal(f"探索失败: {result.error}")

    except Exception as e:
        _print_fatal(f"探索出错: {e}", hint="确认项目路径存在且可读")
        raise typer.Exit(1)


@app.command()
def wiki(
    project_path: Path = typer.Argument(".", help="项目路径"),
    output: Path = typer.Option(
        None, "--output", "-o", help="输出文件路径，默认 REPO_WIKI.md"
    ),
):
    """生成项目 Wiki 文档"""
    project_path = project_path.resolve()

    if not project_path.exists():
        _print_fatal(f"项目路径不存在: {project_path}")
        raise typer.Exit(1)

    # 确定输出路径
    if output is None:
        output = project_path / "REPO_WIKI.md"

    console.print(f"[bold]📝 生成 Wiki: {project_path}[/bold]")

    try:
        # 从 pyproject.toml 或目录名获取项目名
        project_name = _detect_project_name(project_path)

        # 生成 Wiki
        generator = WikiGenerator(
            project_name=project_name,
            project_path=project_path,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("解析代码...", total=None)
            content = generator.generate(output)

        console.print(
            Panel.fit(
                f"[green]✓ Wiki 已生成[/green]\n\n"
                f"文件: [cyan]{output}[/cyan]\n\n"
                f"[dim]使用 `omc wiki` 重新生成[/dim]",
                title="📚 Wiki",
            )
        )

    except Exception as e:
        _print_fatal(f"Wiki 生成失败: {e}")
        raise typer.Exit(1)


def _detect_project_name(project_path: Path) -> str:
    """检测项目名称"""
    # 尝试从 pyproject.toml 读取
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib

            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            if "project" in data and "name" in data["project"]:
                return data["project"]["name"]
        except Exception:
            pass

    # 尝试从 setup.py 读取
    setup_py = project_path / "setup.py"
    if setup_py.exists():
        try:
            content = setup_py.read_text()
            import re

            match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
        except Exception:
            pass

    # 默认使用目录名
    return project_path.name


# ============================================================
# Quest Mode - 异步自主编程
# ============================================================


@app.command()
def quest(
    ctx: typer.Context,
    description: str = typer.Argument(..., help="任务描述（自然语言）"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
    title: str = typer.Option(None, "--title", "-t", help="任务标题（可选）"),
    skip_spec: bool = typer.Option(False, "--skip-spec", help="跳过 SPEC 生成直接执行"),
    auto_confirm: bool = typer.Option(False, "--yes", "-y", help="自动确认并执行"),
):
    """
    🧙 Quest Mode - 异步自主编程

    将需求交给 AI，自动生成 SPEC 文档，后台执行，完成后通知验收。

    示例:
      omc quest "实现用户认证模块，支持 JWT"
      omc quest "添加缓存层" -p myproject/
      omc quest "重构数据库访问层" --skip-spec
    """
    import asyncio

    project_path = project_path.resolve()
    if not project_path.exists():
        _print_fatal(f"项目路径不存在: {project_path}")
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold magenta]🧙 Quest Mode[/bold magenta]\n\n"
            f"[cyan]需求:[/cyan] {description}\n"
            f"[cyan]项目:[/cyan] {project_path}",
            title="🚀 启动",
            border_style="magenta",
        )
    )

    from .quest import QuestManager

    manager = QuestManager(project_path)

    async def run():
        # 1. 创建 Quest
        quest_obj = await manager.create_quest(description, title=title)
        console.print(f"[dim]📋 Quest 已创建: {quest_obj.id[:8]}[/dim]")

        # 2. 生成 SPEC
        if not skip_spec:
            console.print("[yellow]⏳ 正在生成 SPEC...[/yellow]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("生成 SPEC 规格文档...", total=None)
                quest_obj = await manager.generate_spec(quest_obj)

            # 显示 SPEC
            spec = quest_obj.spec
            if spec:
                spec_content = spec.to_markdown()
                console.print(
                    Panel.fit(
                        spec_content[:3000]
                        + ("\n..." if len(spec_content) > 3000 else ""),
                        title="📄 SPEC 规格文档",
                        border_style="cyan",
                    )
                )

            if not auto_confirm:
                console.print("\n[yellow]⚠️ 审查 SPEC 后，运行以下命令执行:[/yellow]")
                console.print(f"  [green]omc quest exec {quest_obj.id}[/green]")
                console.print("  [dim]或使用 [green]-y[/dim] 自动确认[/dim]")
                raise typer.Exit(0)

        # 3. 开始执行
        console.print("[yellow]⏳ 后台执行中...[/yellow]")
        console.print("[dim]使用 [green]omc quest status[/dim] 查看进度[/dim]")
        console.print("[dim]使用 [green]omc quest log {id}[/dim] 查看详细日志[/dim]")

        manager.confirm_and_execute(quest_obj.id)
        console.print(f"[green]✅ Quest 已启动 (ID: {quest_obj.id[:8]})[/green]")
        console.print("[dim]完成时会收到通知[/dim]")

    try:
        asyncio.run(run())
    except SystemExit:
        raise
    except Exception as e:
        _print_fatal(f"Quest 执行出错: {e}")
        raise typer.Exit(1)


@app.command("quest-list")
def quest_list(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
    status_filter: str = typer.Option(
        None, "--status", "-s", help="按状态筛选 (pending/executing/completed/failed)"
    ),
    all_quests: bool = typer.Option(False, "--all", "-a", help="显示所有 Quest"),
):
    """
    📋 查看 Quest 列表
    """
    from .quest import QuestManager, QuestStatus

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    # 解析状态筛选
    sf = None
    if status_filter:
        try:
            sf = QuestStatus(status_filter)
        except ValueError:
            _print_fatal(f"未知状态: {status_filter}")
            raise typer.Exit(1)

    quests = manager.list_quests(status_filter=sf)

    if not quests:
        console.print("[dim]暂无 Quest[/dim]")
        return

    # 状态颜色
    status_colors = {
        QuestStatus.PENDING: "dim",
        QuestStatus.SPEC_GENERATING: "yellow",
        QuestStatus.SPEC_READY: "cyan",
        QuestStatus.EXECUTING: "green",
        QuestStatus.COMPLETED: "bold green",
        QuestStatus.FAILED: "bold red",
        QuestStatus.CANCELLED: "dim",
        QuestStatus.PAUSED: "yellow",
    }

    table = Table(title=f"Quest 列表 ({len(quests)})")
    table.add_column("ID", style="cyan", width=8)
    table.add_column("标题", style="white")
    table.add_column("状态", width=14)
    table.add_column("进度", width=12)
    table.add_column("耗时", width=8)
    table.add_column("创建时间", style="dim")

    for q in quests:
        color = status_colors.get(q.status, "white")
        progress = int(q.progress() * 10)
        bar = "█" * progress + "░" * (10 - progress)
        table.add_row(
            q.id[:8],
            q.title[:35],
            f"[{color}]{q.status.value}[/{color}]",
            f"{bar} {int(q.progress()*100)}%",
            f"{q.duration():.0f}s" if q.duration() else "—",
            q.created_at.strftime("%m-%d %H:%M"),
        )

    console.print(table)


@app.command("quest-status")
def quest_status(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
):
    """
    📊 查看 Quest 详细状态
    """
    from .quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.get_quest(quest_id)
    if quest is None:
        _print_fatal(f"Quest {quest_id} 不存在")
        raise typer.Exit(1)

    # 状态颜色
    status_color = {
        QuestStatus.PENDING: "dim",
        QuestStatus.SPEC_GENERATING: "yellow",
        QuestStatus.SPEC_READY: "cyan",
        QuestStatus.EXECUTING: "green",
        QuestStatus.COMPLETED: "bold green",
        QuestStatus.FAILED: "bold red",
        QuestStatus.CANCELLED: "dim",
        QuestStatus.PAUSED: "yellow",
    }
    sc = status_color.get(quest.status, "white")

    lines = [
        f"[cyan]ID:[/cyan]     {quest.id}",
        f"[cyan]标题:[/cyan]   {quest.title}",
        f"[cyan]状态:[/cyan]   [{sc}]{quest.status.value}[/{sc}]",
        f"[cyan]进度:[/cyan]   {int(quest.progress()*100)}%",
    ]

    if quest.duration():
        lines.append(f"[cyan]耗时:[/cyan]   {quest.duration():.1f}s")

    if quest.spec_path:
        lines.append(f"[cyan]SPEC:[/cyan]  {quest.spec_path}")

    if quest.error_message:
        lines.append(f"[red]错误:[/red]   {quest.error_message}")

    if quest.result_summary:
        lines.append(f"[green]结果:[/green]  {quest.result_summary}")

    console.print(
        Panel("\n".join(lines), title=f"Quest {quest.id[:8]}", border_style="cyan")
    )

    # 显示步骤
    if quest.steps:
        console.print("\n[bold]📌 执行步骤:[/bold]")
        step_table = Table()
        step_table.add_column("ID", width=4)
        step_table.add_column("步骤", width=20)
        step_table.add_column("Agent", width=15)
        step_table.add_column("状态", width=12)

        step_colors = {
            QuestStatus.PENDING: "dim",
            QuestStatus.EXECUTING: "yellow",
            QuestStatus.COMPLETED: "bold green",
            QuestStatus.FAILED: "bold red",
        }

        for step in quest.steps:
            sc2 = step_colors.get(step.status, "white")
            step_table.add_row(
                step.step_id,
                step.title[:20],
                step.agent,
                f"[{sc2}]{step.status.value}[/{sc2}]",
            )

        console.print(step_table)


@app.command("quest-exec")
def quest_exec(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
):
    """
    ▶️ 执行已就绪的 Quest
    """
    from .quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.get_quest(quest_id)
    if quest is None:
        _print_fatal(f"Quest {quest_id} 不存在")
        raise typer.Exit(1)

    if quest.status != QuestStatus.SPEC_READY:
        _print_fatal(f"Quest 状态为 {quest.status}，需要 SPEC_READY 状态")
        console.print("[dim]使用 [green]omc quest[/green] 创建新 Quest[/dim]")
        raise typer.Exit(1)

    manager.confirm_and_execute(quest_id)
    console.print(
        Panel.fit(
            f"[green]✅ Quest 已启动[/green]\n\n"
            f"ID: {quest.id[:8]}\n"
            f"标题: {quest.title}\n\n"
            "[dim]使用 [green]omc quest status {id}[/green] 查看进度[/dim]",
            title="🚀 启动成功",
            border_style="green",
        )
    )


@app.command("quest-cancel")
def quest_cancel(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
):
    """
    ⏹️ 取消 Quest
    """
    from .quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    if manager.cancel(quest_id):
        console.print(f"[yellow]⏹️ Quest {quest_id[:8]} 已取消[/yellow]")
    else:
        _print_fatal(f"Quest {quest_id} 不存在")
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
        AnalystAgent,
        ArchitectAgent,
        CodeReviewerAgent,
        CodeSimplifierAgent,
        CriticAgent,
        DebuggerAgent,
        DesignerAgent,
        ExecutorAgent,
        ExploreAgent,
        GitMasterAgent,
        PlannerAgent,
        QATesterAgent,
        ScientistAgent,
        SecurityReviewerAgent,
        TestEngineerAgent,
        TracerAgent,
        VerifierAgent,
        WriterAgent,
    )

    agents_list = [
        ("explore", ExploreAgent.description, ExploreAgent.default_tier),
        ("analyst", AnalystAgent.description, AnalystAgent.default_tier),
        ("planner", PlannerAgent.description, PlannerAgent.default_tier),
        ("architect", ArchitectAgent.description, ArchitectAgent.default_tier),
        ("executor", ExecutorAgent.description, ExecutorAgent.default_tier),
        ("verifier", VerifierAgent.description, VerifierAgent.default_tier),
        (
            "test-engineer",
            TestEngineerAgent.description,
            TestEngineerAgent.default_tier,
        ),
        (
            "code-reviewer",
            CodeReviewerAgent.description,
            CodeReviewerAgent.default_tier,
        ),
        ("debugger", DebuggerAgent.description, DebuggerAgent.default_tier),
        ("tracer", TracerAgent.description, TracerAgent.default_tier),
        ("critic", CriticAgent.description, CriticAgent.default_tier),
        ("writer", WriterAgent.description, WriterAgent.default_tier),
        ("designer", DesignerAgent.description, DesignerAgent.default_tier),
        (
            "security-reviewer",
            SecurityReviewerAgent.description,
            SecurityReviewerAgent.default_tier,
        ),
        ("git-master", GitMasterAgent.description, GitMasterAgent.default_tier),
        (
            "code-simplifier",
            CodeSimplifierAgent.description,
            CodeSimplifierAgent.default_tier,
        ),
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
        console.print(
            Panel(
                f"[green]✓ 路由器就绪[/green]\n"
                f"总请求数: [cyan]{stats['total_requests']}[/cyan]\n"
                f"总成本:   [cyan]¥{stats['total_cost']:.4f}[/cyan]",
                title="路由器",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(
            Panel(
                f"[red]✗ 路由器初始化失败[/red]\n\n{e}",
                title="路由器",
                border_style="red",
            )
        )


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

    console.print()
    console.print(
        Panel(
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
        )
    )
    console.print()


def _print_fatal(msg: str, hint: str = ""):
    """打印致命错误并退出"""

    console.print()
    console.print(
        Panel(
            f"[bold red]✗ {msg}[/bold red]"
            + (f"\n\n[cyan]提示:[/cyan] {hint}" if hint else ""),
            title="❌ 执行失败",
            border_style="red",
        )
    )
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
        console.print("\n[green]✓ 已完成步骤:[/green]")
        for step in result.steps_completed:
            console.print(f"  - {step}")

    if result.steps_failed:
        console.print("\n[red]✗ 失败步骤:[/red]")
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
