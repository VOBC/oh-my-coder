"""
Checkpoint CLI 命令

omc checkpoint --list                      # 列出所有快照
omc checkpoint --restore <id>             # 回滚到指定快照
omc checkpoint --diff <id>                 # 查看快照与当前差异
omc checkpoint --delete <id>               # 删除快照
omc checkpoint --info <id>                 # 查看快照详情
omc checkpoint --stats                     # 查看统计
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from src.core.checkpoint import CheckpointManager

app = typer.Typer(
    name="checkpoint", help="Checkpoint 快照管理 — 任务开始前自动记录，出问题可一键回滚"
)
console = Console()


@app.command()
def list(
    task_id: str = typer.Option(None, "--task", "-t", help="按任务 ID 过滤"),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="项目路径"),
    limit: int = typer.Option(20, "--limit", "-n", help="返回条数"),
):
    """列出所有 Checkpoint"""
    cm = CheckpointManager(project_path=project_path)
    checkpoints = cm.list(task_id=task_id, limit=limit)

    if not checkpoints:
        console.print("[dim]暂无快照，使用 `omc run` 会自动创建[/dim]")
        raise typer.Exit(0)

    table = Table(title="Checkpoint 列表")
    table.add_column("ID", style="cyan", no_wrap=False)
    table.add_column("任务", style="green")
    table.add_column("描述", style="white")
    table.add_column("文件", style="yellow", justify="right")
    table.add_column("大小", style="magenta")
    table.add_column("创建时间", style="dim")

    for cp in checkpoints:
        size_kb = cp.get("total_size", 0) // 1024
        size_str = f"{size_kb} KB" if size_kb > 0 else "<1 KB"
        table.add_row(
            cp["id"],
            cp.get("task_id", ""),
            cp.get("description", "")[:40],
            str(cp.get("file_count", 0)),
            size_str,
            cp.get("created_at", "")[:19],
        )

    console.print(table)
    console.print(
        f"\n[dim]共 {len(checkpoints)} 个快照 | 备份位置: ~/.omc/backup/[/dim]"
    )


@app.command()
def restore(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID"),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="项目路径"),
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认"),
):
    """回滚到指定 Checkpoint（恢复前自动备份当前状态）"""
    cm = CheckpointManager(project_path=project_path)

    # 先获取 checkpoint 信息
    cp = cm.get_checkpoint(checkpoint_id)
    if cp is None:
        console.print(f"[red]❌ 未找到 Checkpoint: {checkpoint_id}[/red]")
        raise typer.Exit(1)

    # 确认
    if not yes:
        console.print(
            f"[yellow]⚠️  将回滚以下 Checkpoint：[/yellow]\n"
            f"  ID:      {checkpoint_id}\n"
            f"  任务:    {cp.task_id}\n"
            f"  描述:    {cp.description}\n"
            f"  文件:    {cp.file_count} 个\n"
            f"\n[yellow]当前工作区的变更文件将自动备份到 ~/.omc/backup/[/yellow]"
        )
        confirm = typer.prompt("确认回滚？输入 'yes' 继续", default="no")
        if confirm.lower() != "yes":
            console.print("[dim]已取消[/dim]")
            raise typer.Exit(0)

    try:
        backup_path = cm.restore(checkpoint_id)
        console.print("[green]✅ 回滚成功！[/green]")
        console.print(f"   快照 ID: {checkpoint_id}")
        console.print(f"   文件数:  {cp.file_count} 个")
        console.print(f"   当前状态已备份至: {backup_path}")
    except Exception as e:
        console.print(f"[red]❌ 回滚失败: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def diff(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID"),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="项目路径"),
):
    """查看 Checkpoint 与当前工作区的差异"""
    cm = CheckpointManager(project_path=project_path)

    try:
        diff_result = cm.diff(checkpoint_id)
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]Checkpoint:[/bold cyan] {checkpoint_id}\n")
    console.print(cm.format_diff(diff_result))

    total_changes = (
        len(diff_result["added"])
        + len(diff_result["removed"])
        + len(diff_result["modified"])
    )
    console.print(f"\n[dim]共 {total_changes} 处变更[/dim]")


@app.command()
def delete(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID"),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="项目路径"),
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认"),
):
    """删除指定 Checkpoint"""
    cm = CheckpointManager(project_path=project_path)

    if not cm.delete(checkpoint_id):
        console.print(f"[red]❌ 未找到 Checkpoint: {checkpoint_id}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]✅ 已删除: {checkpoint_id}[/green]")


@app.command()
def info(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID"),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="项目路径"),
):
    """查看 Checkpoint 详情"""
    cm = CheckpointManager(project_path=project_path)

    cp = cm.get_checkpoint(checkpoint_id)
    if cp is None:
        console.print(f"[red]❌ 未找到 Checkpoint: {checkpoint_id}[/red]")
        raise typer.Exit(1)

    from rich.panel import Panel

    files = "\n".join(f"  • {e.path} ({e.size} B)" for e in cp.entries[:30])
    if len(cp.entries) > 30:
        files += f"\n  ... 还有 {len(cp.entries) - 30} 个文件"

    panel = Panel(
        f"[bold]ID:[/bold]       {cp.id}\n"
        f"[bold]任务:[/bold]     {cp.task_id}\n"
        f"[bold]描述:[/bold]     {cp.description}\n"
        f"[bold]创建:[/bold]     {cp.created_at}\n"
        f"[bold]文件:[/bold]     {cp.file_count} 个\n"
        f"[bold]大小:[/bold]     {cp.total_size // 1024} KB\n"
        f"[bold]工作区:[/bold]  {cp.working_dir}\n\n"
        f"[bold]文件列表:[/bold]\n{files}",
        title=f"Checkpoint: {checkpoint_id}",
        border_style="cyan",
    )
    console.print(panel)


@app.command()
def stats(
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="项目路径"),
):
    """查看 Checkpoint 统计"""
    cm = CheckpointManager(project_path=project_path)
    stats = cm.get_stats()

    console.print(
        f"[bold cyan]Checkpoint 统计[/bold cyan]\n\n"
        f"  快照数量:  {stats['total_checkpoints']} 个\n"
        f"  文件总数:  {stats['total_files']} 个\n"
        f"  总大小:    {stats['total_size_bytes'] // 1024} KB\n"
        f"\n[dim]备份目录: ~/.omc/backup/[/dim]"
    )
