from __future__ import annotations

# mypy: disable-error-code="abstract,arg-type,assignment,attr-defined,call-arg,call-overload,dict-item,func-returns-value,import-untyped,index,misc,no-any-return,no-redef,operator,override,return,return-value,syntax,union-attr,var-annotated"

"""
Quest Mode CLI - 异步自主编程

将需求交给 AI，自动生成 SPEC 文档，后台执行，完成后通知验收。
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.quest import QuestStatus

console = Console()
app = typer.Typer(name="quest", help="Quest Mode 命令")


def _print_fatal(msg: str):
    """打印致命错误"""
    console.print(f"[bold red]❌ {msg}[/bold red]")


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

    from src.quest import QuestManager

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
                console.print("  [dim]或使用 [green]-y[/green] 自动确认[/dim]")
                raise typer.Exit(0)

        # 3. 开始执行
        console.print("[yellow]⏳ 后台执行中...[/yellow]")
        console.print("[dim]使用 [green]omc quest status[/green] 查看进度[/dim]")
        console.print("[dim]使用 [green]omc quest log {id}[/green] 查看详细日志[/dim]")

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
    from src.quest import QuestManager, QuestStatus

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
    from src.quest import QuestManager

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
    from src.quest import QuestManager

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
    from src.quest import QuestManager

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
    from src.quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    if manager.pause(quest_id):
        console.print(f"[yellow]⏸️ Quest {quest_id[:8]} 已暂停[/yellow]")
        console.print("[dim]使用 [green]omc quest resume {id}[/green] 恢复[/dim]")
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
    from src.quest import QuestManager

    project_path = project_path.resolve()
    manager = QuestManager(project_path)

    quest = manager.resume(quest_id)
    if quest:
        console.print(f"[green]▶️ Quest {quest_id[:8]} 已恢复[/green]")
        console.print("[dim]使用 [green]omc quest status {id}[/green] 查看进度[/dim]")
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

    from src.quest import NotificationConfig, NotificationManager, QuestManager

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
    from src.quest.notifications import ConsoleNotificationChannel

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

    from src.quest import QuestManager, QuestStatus

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

    from src.quest import QuestStatus

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
