"""
omc compact - 自动压缩工具

用法:
  omc compact stats           # 查看压缩统计
  omc compact sweep          # 手动触发压缩
  omc compact sweep --since-last-user  # 从最后用户消息开始压缩
"""

from __future__ import annotations
from typing import Optional

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="compact",
    help="自动压缩统计 - 查看压缩历史和 token 使用情况",
    no_args_is_help=True,
)

console = Console()


def _get_manager(project_path: Path):
    from src.memory.manager import MemoryManager

    return MemoryManager.from_project(project_path)


@app.command("stats")
def compact_stats(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
):
    """
    📊 显示当前会话的压缩统计

    显示内容：
    - 压缩总次数
    - 节省的 token 数
    - 清理的消息数
    - 工具调用去重次数
    - 历史错误清理数
    """
    manager = _get_manager(project_path.resolve())
    stats = manager.compact_stats

    table = Table(title="🗜️ AutoCompact 统计", show_header=True, header_style="bold cyan")
    table.add_column("指标", style="dim")
    table.add_column("值", justify="right")

    table.add_row("压缩次数", f"{stats['total_compact_count']}")
    table.add_row("节省 token", f"{stats['total_tokens_saved']:,}")
    table.add_row("清理消息数", f"{stats['total_messages_removed']:,}")
    table.add_row("去重 tool_call", f"{stats['total_deduplicated']}")
    table.add_row("清理错误消息", f"{stats['total_errors_removed']}")

    console.print(table)

    if stats["total_compact_count"] == 0:
        console.print("\n[dim]尚未执行过压缩，暂无统计数据。[/dim]")


@app.command("sweep")
def compact_sweep(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
    since_last_user: bool = typer.Option(
        False,
        "--since-last-user",
        help="从最后用户消息开始压缩（丢弃之前的消息）",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示结果，不实际压缩"),
):
    """
    🧹 手动触发压缩（sweep）

    可选标志：
      --since-last-user  从最后用户消息开始清理
      --dry-run           只显示结果，不实际压缩
    """
    manager = _get_manager(project_path.resolve())
    session = manager.get_latest_session()

    if session is None:
        console.print("[red]未找到活跃会话。[/red]")
        raise typer.Exit(1)

    if since_last_user:
        console.print("[cyan]从最后用户消息开始裁剪...[/cyan]")
        # 找到最后一条 user 消息
        messages = session.messages
        last_user_idx = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].role == "user":
                last_user_idx = i
                break
        if last_user_idx is not None and last_user_idx > 0:
            session.messages = messages[last_user_idx:]
            console.print(
                f"[green]已裁剪到第 {last_user_idx + 1} 条消息（共 {len(messages)} 条）[/green]"
            )
        else:
            console.print("[yellow]未找到更早的用户消息，无需裁剪。[/yellow]")
            raise typer.Exit(0)

    if dry_run:
        # 只检查，不压缩
        result = manager.auto_compact_check(session, force=False, since_last_user=False)
        if result.compacted:
            console.print(
                f"[yellow]Dry-run: 将压缩 {result.messages_removed} 条消息，"
                f"节省约 {result.tokens_saved} tokens[/yellow]"
            )
        else:
            console.print(
                "[dim]Dry-run: 当前使用率未达到阈值，无需压缩。[/dim]"
            )
            console.print(f"  当前 token: {result.tokens_before}")
        raise typer.Exit(0)

    result = manager.auto_compact_check(session, force=True)
    manager.save_session(session)

    if result.compacted:
        console.print(
            f"[green]✅ 压缩完成: 清理 {result.messages_removed} 条消息，"
            f"节省 ~{result.tokens_saved} tokens[/green]"
        )
    else:
        console.print(
            "[yellow]⚠️  未触发压缩（usage_ratio < threshold）。[/yellow]"
        )
        console.print(f"  当前 token: {result.tokens_before}")
