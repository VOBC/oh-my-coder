"""
任务状态 CLI 命令

omc task list              - 列出所有任务
omc task status <id>      - 查看任务详情
omc task pause <id>       - 暂停任务
omc task resume <id>      - 恢复任务
omc task delete <id>      - 删除任务
omc task steps <id>       - 查看任务步骤历史
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .state.task_state import (
    TaskStatus,
    delete_task,
    get_task,
    list_tasks,
    pause_task,
    resume_task,
)

app = typer.Typer(
    name="task",
    help="任务状态管理 - 列出、暂停、恢复、查看任务",
    add_completion=False,
)
console = Console()


def _status_color(status: TaskStatus) -> str:
    """状态颜色映射"""
    return {
        TaskStatus.PENDING: "dim",
        TaskStatus.RUNNING: "cyan",
        TaskStatus.PAUSED: "yellow",
        TaskStatus.COMPLETED: "green",
        TaskStatus.FAILED: "red",
    }.get(status, "white")


def _status_emoji(status: TaskStatus) -> str:
    """状态 emoji 映射"""
    return {
        TaskStatus.PENDING: "⏳",
        TaskStatus.RUNNING: "🔄",
        TaskStatus.PAUSED: "⏸️",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
    }.get(status, "❓")


@app.command("list")
def task_list(
    status_filter: str = typer.Option(
        None,
        "--status",
        "-s",
        help="按状态筛选 (pending/running/paused/completed/failed)",
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="最多显示数量"),
) -> None:
    """
    列出所有任务

    示例:
        omc task list
        omc task list --status running
        omc task list --status failed -n 50
    """
    status_enum: TaskStatus | None = None
    if status_filter:
        try:
            status_enum = TaskStatus(status_filter.lower())
        except ValueError:
            console.print(
                f"[red]❗ 无效状态: {status_filter}[/red]\n"
                "有效值: pending, running, paused, completed, failed"
            )
            raise typer.Exit(1)

    states = list_tasks(status_enum)
    if not states:
        console.print("[dim]暂无任务[/dim]")
        return

    states = states[:limit]

    table = Table(title=f"任务列表 ({len(states)})")
    table.add_column("状态", width=3)
    table.add_column("任务ID", style="cyan", width=12)
    table.add_column("当前步骤", style="white")
    table.add_column("进度", width=10)
    table.add_column("创建时间", style="dim", width=18)

    for state in states:
        progress_str = f"{state.progress * 100:.0f}%"
        table.add_row(
            _status_emoji(state.status),
            state.task_id,
            (
                (state.current_step[:40] + "...")
                if len(state.current_step) > 40
                else state.current_step
            ),
            progress_str,
            state.created_at[:19].replace("T", " "),
        )

    console.print(table)

    # 统计
    len(states)
    counts = {s: sum(1 for s_ in states if s_.status == s) for s in TaskStatus}
    stats = " ".join(f"{_status_emoji(s)} {v}" for s, v in counts.items() if v > 0)
    console.print(f"\n[dim]{stats}[/dim]")


@app.command("status")
def task_status(
    task_id: str = typer.Argument(..., help="任务 ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示完整步骤"),
) -> None:
    """
    查看任务详情

    示例:
        omc task status abc123
        omc task status abc123 -v
    """
    state = get_task(task_id)
    if state is None:
        console.print(f"[red]❗ 任务不存在: {task_id}[/red]")
        raise typer.Exit(1)

    status_color = _status_color(state.status)
    emoji = _status_emoji(state.status)

    info_lines = [
        f"ID: [cyan]{state.task_id}[/cyan]",
        f"状态: [{status_color}]{emoji} {state.status.value}[/{status_color}]",
        f"进度: [cyan]{state.progress * 100:.1f}%[/cyan]",
        f"当前步骤: {state.current_step or '无'}",
        f"创建时间: {state.created_at}",
        f"更新时间: {state.updated_at}",
    ]

    if state.error:
        info_lines.append(f"错误: [red]{state.error}[/red]")

    if state.artifacts:
        info_lines.append(f"产物数: [dim]{len(state.artifacts)}[/dim]")

    console.print(
        Panel(
            "\n".join(info_lines),
            title="📋 任务详情",
            border_style="cyan",
        )
    )

    if verbose and state.steps:
        console.print("\n[bold]执行步骤:[/bold]")
        for i, step in enumerate(state.steps, 1):
            console.print(f"  {i}. [{step.timestamp[11:19]}] {step.step}")
            if step.result:
                result_display = (
                    step.result[:100] + "..."
                    if len(str(step.result)) > 100
                    else step.result
                )
                console.print(f"     → {result_display}")


@app.command("pause")
def task_pause(
    task_id: str = typer.Argument(..., help="任务 ID"),
) -> None:
    """
    暂停任务

    示例:
        omc task pause abc123
    """
    state = get_task(task_id)
    if state is None:
        console.print(f"[red]❗ 任务不存在: {task_id}[/red]")
        raise typer.Exit(1)

    if state.status == TaskStatus.PAUSED:
        console.print("[yellow]任务已经是暂停状态[/yellow]")
        return

    if state.status not in (TaskStatus.RUNNING, TaskStatus.PENDING):
        console.print(f"[red]❗ 无法暂停: 当前状态为 {state.status.value}[/red]")
        raise typer.Exit(1)

    if pause_task(task_id):
        console.print(f"[green]✓ 任务已暂停: {task_id}[/green]")
        console.print(f"  当前步骤: {state.current_step or '无'}")
    else:
        console.print("[red]❗ 暂停失败[/red]")
        raise typer.Exit(1)


@app.command("resume")
def task_resume(
    task_id: str = typer.Argument(..., help="任务 ID"),
) -> None:
    """
    恢复任务

    示例:
        omc task resume abc123
    """
    state = get_task(task_id)
    if state is None:
        console.print(f"[red]❗ 任务不存在: {task_id}[/red]")
        raise typer.Exit(1)

    if state.status != TaskStatus.PAUSED:
        console.print(
            f"[yellow]任务不是暂停状态（当前: {state.status.value}）[/yellow]"
        )
        return

    if resume_task(task_id):
        console.print(f"[green]✓ 任务已恢复: {task_id}[/green]")
        console.print(f"  从断点继续: {state.current_step or '任务开始'}")
    else:
        console.print("[red]❗ 恢复失败[/red]")
        raise typer.Exit(1)


@app.command("delete")
def task_delete(
    task_id: str = typer.Argument(..., help="任务 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除"),
) -> None:
    """
    删除任务

    示例:
        omc task delete abc123
        omc task delete abc123 -f
    """
    state = get_task(task_id)
    if state is None:
        console.print(f"[red]❗ 任务不存在: {task_id}[/red]")
        raise typer.Exit(1)

    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(
            f"确认删除任务 [cyan]{task_id}[/cyan]（状态: {state.status.value}）？"
        ):
            console.print("[dim]已取消[/dim]")
            return

    if delete_task(task_id):
        console.print(f"[green]✓ 任务已删除: {task_id}[/green]")
    else:
        console.print("[red]❗ 删除失败[/red]")
        raise typer.Exit(1)
