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
from .cli_context import context_app
from .capabilities import app as cap_app
from .cli_config_ext import app as config_ext_app
from .cli_task import app as task_app
from .cli_multiagent import app as multiagent_app
from .cli_security import app as security_app
from .cli_checkpoint import app as checkpoint_app
from .cli_mcp import app as mcp_app
from .cli_memory import app as memory_app

# 版本信息
__version__ = "1.0.0"
__author__ = "VOBC"
__repo__ = "https://github.com/VOBC/oh-my-coder"

app = typer.Typer(
    name="omc",
    help=f"Oh My Coder v{__version__} - 多智能体 AI 编程助手",
    add_completion=False,
    no_args_is_help=True,
)

# 注册子命令
app.add_typer(context_app, name="context")
app.add_typer(config_ext_app, name="agent-config")
app.add_typer(task_app, name="task")
app.add_typer(multiagent_app, name="multiagent")
app.add_typer(security_app, name="security")
app.add_typer(checkpoint_app, name="checkpoint")
app.add_typer(mcp_app, name="mcp")
app.add_typer(memory_app, name="memory", help="分层记忆管理 - 查看核心/精选/完整记忆")

# 代码清理命令
try:
    from .cli_clean import app as clean_app

    app.add_typer(clean_app, name="clean", help="代码清理 - 检测和清理冗余代码")
except Exception:
    pass

# 成本优化命令
try:
    from .cli_cost import app as cost_app

    app.add_typer(cost_app, name="cost", help="成本优化 - 根据任务推荐最优模型")
except Exception:
    pass

# 本地模型命令
try:
    from .cli_local_models import app as local_models_app

    app.add_typer(
        local_models_app, name="local", help="本地模型管理 - Ollama 零成本运行"
    )
except Exception:
    pass

# model 子命令
from .cli_model import app as model_app  # noqa: E402

app.add_typer(model_app, name="model", help="模型管理 - 查看/切换默认模型")

# gateway 子命令（懒导入，避免 gateway 依赖缺失时报错）
try:
    from .cli_gateway import app as gateway_app  # noqa: E402

    app.add_typer(gateway_app, name="gateway", help="多平台网关 - Telegram / Discord")
except Exception:
    pass  # gateway 依赖缺失时跳过

# agent 子命令 - Agent 配置管理与自进化
try:
    from .cli_agent import app as agent_app  # noqa: E402

    app.add_typer(agent_app, name="agent", help="Agent 管理 - 导出/导入/进化")
except Exception:
    pass

# template 子命令 - 工作流模板
try:
    from .cli_template import app as template_app  # noqa: E402

    app.add_typer(template_app, name="template", help="工作流模板 - 列出/使用模板")
except Exception:
    pass

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
    workflow: str = typer.Option(
        "build",
        "--workflow",
        "-w",
        help=(
            "工作流名称：build（开发）/ review（审查）/ debug（调试）/ test（测试）"
            " / autopilot（自动路由）/ pair（结对编程）/ refactor（重构）"
            " / doc（文档生成）/ sequential（顺序执行编排）"
        ),
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览执行计划，不实际运行"),
    notify: bool = typer.Option(
        False, "--notify", "-n", help="完成后发送通知（桌面+钉钉）"
    ),
    no_checkpoint: bool = typer.Option(
        False, "--no-checkpoint", help="跳过自动快照（断点续传）"
    ),
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

    # Dry-run 模式：只展示计划
    if dry_run:
        console.print(
            Panel.fit(
                "[yellow]🔍 Dry-run 模式 — 仅展示执行计划[/yellow]\n\n"
                "[bold]工作流:[/bold] "
                + workflow
                + "\n[bold]任务:[/bold] "
                + task
                + "\n[bold]项目:[/bold] "
                + str(project_path.absolute())
                + "\n\n[dim]实际执行请去掉 --dry-run 参数[/dim]",
                title="📋 执行计划预览",
                border_style="yellow",
            )
        )
        raise typer.Exit(0)

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
                    skip_checkpoint=no_checkpoint,
                )
            )

            # 显示结果
            _display_result(result)

            # 发送通知
            if notify:
                from .utils.notify import (
                    notify_workflow_complete,
                    notify_workflow_complete_dingtalk,
                )

                status = "completed" if result.success else "failed"
                steps = len(result.steps) if hasattr(result, "steps") else 1
                exec_time = getattr(result, "execution_time", 0.0)

                # 桌面通知
                notify_workflow_complete(workflow, status, steps, exec_time)
                # 钉钉通知
                notify_workflow_complete_dingtalk(
                    None, workflow, status, steps, exec_time, str(project_path)
                )

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
            generator.generate(output)

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

    # 步骤验收回调（交互式）
    async def review_callback(quest_id: str, step_id: str, preview: str) -> str:
        console.print(f"\n[bold cyan]📋 步骤验收: {step_id}[/bold cyan]")
        if preview:
            console.print(
                Panel.fit(preview[:500], title="执行结果预览", border_style="dim")
            )

        from rich.prompt import Prompt

        choice = Prompt.ask(
            "请选择",
            choices=["p", "r", "s"],
            default="p",
            show_choices=True,
        )
        mapping = {"p": "pass", "r": "retry", "s": "skip"}
        return mapping.get(choice, "pass")

    manager = QuestManager(project_path, review_callback=review_callback)

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
            f"{bar} {int(q.progress() * 100)}%",
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
        f"[cyan]进度:[/cyan]   {int(quest.progress() * 100)}%",
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


@app.command("quest-pause")
def quest_pause(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
):
    """
    ⏸️ 暂停 Quest（在当前步骤完成后暂停）
    """
    from .quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    if manager.pause(quest_id):
        console.print(f"[yellow]⏸️ Quest {quest_id[:8]} 已暂停[/yellow]")
        console.print("[dim]使用 [green]omc quest resume {id}[/dim] 恢复[/dim]")
    else:
        _print_fatal(f"Quest {quest_id} 不存在或无法暂停")
        raise typer.Exit(1)


@app.command("quest-resume")
def quest_resume(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
):
    """
    ▶️ 恢复已暂停的 Quest（从断点继续）
    """
    from .quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.resume(quest_id)
    if quest:
        console.print(f"[green]▶️ Quest {quest_id[:8]} 已恢复[/green]")
        console.print("[dim]使用 [green]omc quest status {id}[/dim] 查看进度[/dim]")
    else:
        _print_fatal(f"Quest {quest_id} 不存在或未处于暂停状态")
        raise typer.Exit(1)


@app.command("quest-notify")
def quest_notify(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
    dingtalk_webhook: str = typer.Option(
        None, "--dingtalk", "-d", help="钉钉 Webhook URL"
    ),
    dingtalk_secret: str = typer.Option(None, "--secret", "-s", help="钉钉加签密钥"),
    telegram_bot_token: str = typer.Option(
        None, "--telegram-bot-token", help="Telegram Bot Token"
    ),
    telegram_chat_id: str = typer.Option(
        None, "--telegram-chat-id", help="Telegram Chat ID"
    ),
    discord_webhook: str = typer.Option(None, "--discord", help="Discord Webhook URL"),
    slack_webhook: str = typer.Option(
        None, "--slack", help="Slack Incoming Webhook URL"
    ),
    teams_webhook: str = typer.Option(
        None, "--teams", help="Microsoft Teams Webhook URL"
    ),
    feishu_webhook: str = typer.Option(
        None, "--feishu", help="飞书（Lark）Webhook URL"
    ),
    wecom_webhook: str = typer.Option(None, "--wecom", help="企业微信 Webhook URL"),
    pushplus_token: str = typer.Option(None, "--pushplus", help="PushPlus Token"),
):
    """
    🔔 订阅 Quest 通知（桌面 + 多种 Webhook 渠道）
    """
    import asyncio

    from .quest import NotificationConfig, NotificationManager, QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.get_quest(quest_id)
    if quest is None:
        _print_fatal(f"Quest {quest_id} 不存在")
        raise typer.Exit(1)

    # 配置通知
    config = NotificationConfig(
        desktop=True,
        dingtalk_webhook=dingtalk_webhook,
        dingtalk_secret=dingtalk_secret,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        discord_webhook=discord_webhook,
        slack_webhook=slack_webhook,
        teams_webhook=teams_webhook,
        feishu_webhook=feishu_webhook,
        wecom_webhook=wecom_webhook,
        pushplus_token=pushplus_token,
    )
    notifier = NotificationManager(config)

    def on_progress(title: str, body: str, level: str) -> None:
        """实时显示进度（控制台回调）"""
        color_map = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }
        color = color_map.get(level, "white")
        console.print(f"[{color}]{title}[/{color}]: {body}")

    # 添加控制台回调渠道
    from .quest.notifications import ConsoleNotificationChannel

    notifier._channels.append(ConsoleNotificationChannel(callback=on_progress))

    # 跟踪进度直到完成
    last_status = quest.status.value
    last_step = -1

    async def watch():
        nonlocal last_status, last_step
        console.print(f"[dim]⏳ 监控 Quest {quest_id[:8]}，按 Ctrl+C 退出...[/dim]\n")
        try:
            while True:
                await asyncio.sleep(5)
                fresh = manager.get_quest(quest_id)
                if fresh is None:
                    break

                # 实时进度（步骤变化时输出）
                if fresh.steps:
                    completed = sum(
                        1 for s in fresh.steps if s.status == QuestStatus.COMPLETED
                    )
                    total = len(fresh.steps)
                    if completed != last_step:
                        last_step = completed
                        bar = "█" * completed + "░" * (total - completed)
                        console.print(
                            f"  [{fresh.status.value:12}] "
                            f"{bar} {completed}/{total} 步骤"
                        )

                # 状态变化时发送桌面/钉钉通知
                if fresh.status.value != last_status:
                    last_status = fresh.status.value
                    if fresh.status.value == "completed":
                        notifier.notify_completed(
                            fresh.title, fresh.result_summary or "", fresh.id
                        )
                    elif fresh.status.value == "failed":
                        notifier.notify_failed(
                            fresh.title,
                            fresh.error_message or "未知错误",
                            fresh.id,
                        )
                    elif fresh.status.value == "paused":
                        notifier.send(
                            "⏸️ Quest 已暂停",
                            fresh.title,
                            event="paused",
                            quest_id=fresh.id,
                        )

                # 完成或终止
                if fresh.status.value in ("completed", "failed", "cancelled"):
                    console.print(f"\n[bold]最终状态: {fresh.status.value}[/bold]")
                    break
        except asyncio.CancelledError:
            pass

    try:
        asyncio.run(watch())
    except KeyboardInterrupt:
        console.print("\n[dim]监控已退出[/dim]")


@app.command("quest-wait")
def quest_wait(
    quest_id: str = typer.Argument(..., help="Quest ID"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
    timeout: int = typer.Option(0, "--timeout", "-t", help="超时秒数（0=无限）"),
):
    """
    ⏳ 阻塞等待 Quest 完成并展示验收结果

    完成后展示详细验收报告，包括各步骤通过情况、结果摘要。
    """
    import asyncio
    from .quest import QuestManager, QuestStatus

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.get_quest(quest_id)
    if quest is None:
        _print_fatal(f"Quest {quest_id} 不存在")
        raise typer.Exit(1)

    # 已完成的情况直接显示结果
    if quest.status in (
        QuestStatus.COMPLETED,
        QuestStatus.FAILED,
        QuestStatus.CANCELLED,
    ):
        _show_acceptance_report(quest, console)
        return

    # 实时跟踪直到完成
    elapsed = 0

    async def watch():
        nonlocal elapsed
        try:
            while True:
                await asyncio.sleep(3)
                elapsed += 3
                fresh = manager.get_quest(quest_id)
                if fresh is None:
                    break

                # 实时进度
                if fresh.steps:
                    completed = sum(
                        1 for s in fresh.steps if s.status == QuestStatus.COMPLETED
                    )
                    total = len(fresh.steps)
                    int(completed / total * 100)
                    bar = "█" * completed + "░" * (total - completed)
                    console.print(
                        f"\r  [{fresh.status.value:12}] "
                        f"{bar} {completed}/{total} | {elapsed}s",
                        end="",
                    )

                if fresh.status in (
                    QuestStatus.COMPLETED,
                    QuestStatus.FAILED,
                    QuestStatus.CANCELLED,
                ):
                    console.print()  # 换行
                    _show_acceptance_report(fresh, console)
                    break

                if timeout > 0 and elapsed >= timeout:
                    console.print(f"\n[yellow]⏰ 超时（{timeout}s）[/yellow]")
                    break
        except asyncio.CancelledError:
            console.print()

    try:
        asyncio.run(watch())
    except KeyboardInterrupt:
        console.print("\n[dim]等待已中断[/dim]")


def _show_acceptance_report(quest, console):
    """展示 Quest 验收报告"""
    from rich.panel import Panel
    from rich.table import Table
    from .quest import QuestStatus

    status_color_map = {
        QuestStatus.COMPLETED: "bold green",
        QuestStatus.FAILED: "bold red",
        QuestStatus.CANCELLED: "dim",
        QuestStatus.EXECUTING: "yellow",
        QuestStatus.PAUSED: "yellow",
    }
    sc = status_color_map.get(quest.status, "white")

    # 标题
    emoji = {
        QuestStatus.COMPLETED: "✅",
        QuestStatus.FAILED: "❌",
        QuestStatus.CANCELLED: "⏹️",
    }.get(quest.status, "⏳")
    console.print(
        Panel.fit(
            f"[bold]{emoji} {quest.title}[/bold]",
            title=f"验收报告 — {quest.status.value}",
            border_style=sc.value if hasattr(sc, "value") else "green",
        )
    )

    # 基本信息
    duration = quest.duration()
    duration_str = f"{duration:.1f}s" if duration else "—"
    console.print(
        f"  [cyan]ID:[/cyan]     {quest.id[:8]}\n"
        f"  [cyan]耗时:[/cyan]   {duration_str}\n"
        + (
            f"  [cyan]摘要:[/cyan]  {quest.result_summary}\n"
            if quest.result_summary
            else ""
        )
        + (
            f"  [red]错误:[/red]   {quest.error_message}\n"
            if quest.error_message
            else ""
        )
    )

    # 步骤验收表格
    if quest.steps:
        table = Table(title="📋 步骤验收", show_header=True)
        table.add_column("步骤", width=6)
        table.add_column("标题", width=30)
        table.add_column("状态", width=12)

        step_sc_map = {
            QuestStatus.PENDING: "dim",
            QuestStatus.EXECUTING: "yellow",
            QuestStatus.COMPLETED: "bold green",
            QuestStatus.FAILED: "bold red",
        }

        for step in quest.steps:
            sc2 = step_sc_map.get(step.status, "white")
            status_icon = {
                QuestStatus.COMPLETED: "✅",
                QuestStatus.FAILED: "❌",
                QuestStatus.PENDING: "⏳",
                QuestStatus.EXECUTING: "⚙️",
            }.get(step.status, "?")
            table.add_row(
                step.step_id,
                step.title[:30],
                f"[{sc2}]{status_icon} {step.status.value}[/{sc2}]",
            )

        console.print(table)

        # 失败步骤详情
        failed_steps = [s for s in quest.steps if s.status == QuestStatus.FAILED]
        if failed_steps:
            console.print("\n[bold red]❌ 失败详情:[/bold red]")
            for s in failed_steps:
                console.print(f"  [{s.step_id}] {s.title}: {s.error}")


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
        DatabaseAgent,
        DebuggerAgent,
        DesignerAgent,
        DevOpsAgent,
        ExecutorAgent,
        ExploreAgent,
        GitMasterAgent,
        MigrationAgent,
        PerformanceAgent,
        PlannerAgent,
        PromptAgent,
        QATesterAgent,
        ScientistAgent,
        SecurityReviewerAgent,
        TestEngineerAgent,
        TracerAgent,
        UMLAgent,
        VerifierAgent,
        VisionAgent,
        WriterAgent,
        APIAgent,
        AuthAgent,
        DataAgent,
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
        ("database", DatabaseAgent.description, DatabaseAgent.default_tier),
        ("api", APIAgent.description, APIAgent.default_tier),
        ("devops", DevOpsAgent.description, DevOpsAgent.default_tier),
        ("uml", UMLAgent.description, UMLAgent.default_tier),
        ("performance", PerformanceAgent.description, PerformanceAgent.default_tier),
        ("migration", MigrationAgent.description, MigrationAgent.default_tier),
        ("prompt", PromptAgent.description, PromptAgent.default_tier),
        ("vision", VisionAgent.description, VisionAgent.default_tier),
        ("auth", AuthAgent.description, AuthAgent.default_tier),
        ("data", DataAgent.description, DataAgent.default_tier),
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


@app.command()
def config(
    action: str = typer.Argument(
        "show",
        help="操作: show（查看）/ set（设置）/ list（列出可用配置项）",
    ),
    key: str = typer.Option(None, "--key", "-k", help="配置项名称"),
    value: str = typer.Option(None, "--value", "-v", help="配置值"),
):
    """
    ⚙️ 管理配置

    用法:
      omc config show          # 查看当前配置
      omc config list         # 列出所有配置项
      omc config set -k DEEPSEEK_API_KEY -v xxx   # 设置配置项
    """
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    config_path = Path(".env")
    if config_path.exists():
        load_dotenv(config_path)

    if action == "list":
        console.print("[bold]可用配置项:[/bold]\n")
        items = [
            ("DEEPSEEK_API_KEY", "DeepSeek API Key（推荐，性价比高）"),
            ("DEEPSEEK_BASE_URL", "DeepSeek API 地址（默认官方）"),
            ("KIMI_API_KEY", "KIMI API Key"),
            ("DOUBAO_API_KEY", "豆包 API Key"),
            ("DINGTALK_WEBHOOK_URL", "钉钉 Webhook URL（Quest 通知）"),
            ("DINGTALK_SECRET", "钉钉加签密钥"),
            ("DEFAULT_MODEL", "默认模型（默认 deepseek）"),
            ("DEFAULT_WORKFLOW", "默认工作流（默认 build）"),
        ]
        for k, desc in items:
            val = os.getenv(k, "")
            masked = _mask_secret(val)
            status = "[green]✓[/green]" if val else "[red]✗[/red]"
            console.print(f"  {status} [cyan]{k}[/cyan]")
            console.print(f"       [dim]{desc}[/dim]")
            if val:
                console.print(f"       当前值: {masked}")
            console.print()
        return

    if action == "show":
        console.print("[bold]当前配置:[/bold]\n")
        keys_to_show = [
            "DEEPSEEK_API_KEY",
            "DEEPSEEK_BASE_URL",
            "KIMI_API_KEY",
            "DOUBAO_API_KEY",
            "DINGTALK_WEBHOOK_URL",
            "DINGTALK_SECRET",
            "DEFAULT_MODEL",
            "DEFAULT_WORKFLOW",
        ]
        for key_name in keys_to_show:
            val = os.getenv(key_name, "")
            masked = _mask_secret(val)
            status = "[green]✓[/green]" if val else "[dim]—[/dim]"
            console.print(f"  {status} [cyan]{key_name}[/cyan] = {masked}")
        return

    if action == "set":
        if not key or not value:
            console.print(
                "[red]❗ 需要同时提供 --key 和 --value[/red]\n"
                "示例: [green]omc config set -k DEFAULT_MODEL -v kimi[/green]"
            )
            raise typer.Exit(1)

        # 写到 .env 文件
        env_path = Path(".env")
        env_vars: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()

        env_vars[key] = value
        lines = [f"{k}={v}" for k, v in env_vars.items()]
        env_path.write_text("\n".join(lines) + "\n")
        console.print(
            f"[green]✓ 已设置[/green] [cyan]{key}[/cyan] = {_mask_secret(value)}"
        )
        console.print("[dim]已写入 .env 文件[/dim]")
        return

    console.print("[red]未知操作[/red]，可用: show / list / set")
    raise typer.Exit(1)


def _mask_secret(value: str) -> str:
    """脱敏显示密钥"""
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def _status_color(status: str) -> str:
    """给状态上色"""
    colors = {
        "completed": "[green]已完成[/green]",
        "failed": "[red]失败[/red]",
        "running": "[yellow]运行中[/yellow]",
        "pending": "[dim]等待中[/dim]",
    }
    return colors.get(status, status)


# 注册子命令
app.add_typer(cap_app, name="cap", help="能力包管理 - 导出、导入和分享 Agent 配置")

if __name__ == "__main__":
    app()
    app()
