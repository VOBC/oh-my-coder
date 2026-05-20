from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
omc usage 命令 - 用量统计与追踪

合并自三个文件：
- cli_stats.py - 项目文件统计
- cli_trace.py - Agent 执行记录追踪
- cli_memory.py - 分层记忆管理

用法：
    omc usage stats [PATH]     — 统计项目文件数量
    omc usage trace list       — 列出最近 session 和 trace
    omc usage trace show <agent> — 显示某个 Agent 的详细执行过程
    omc usage trace agents     — 显示当前 session 的所有 Agent
    omc usage trace latest     — 显示最新 session
    omc usage memory tier0     — 查看 Tier 0 核心记忆（< 500 token）
    omc usage memory tier1     — 查看 Tier 1 精选记忆（< 2000 token）
    omc usage memory summary   — 查看完整记忆摘要
    omc usage memory stats     — 查看记忆统计（条数、token 数）
"""

import json
import os
from pathlib import Path
from typing import Optional, Union

import click
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ============================================================================
# Stats 子命令（来自 cli_stats.py）
# ============================================================================


def _get_count_files():
    """延迟导入 count_files 以避免 stats 模块的兼容性问题"""
    from src.stats import count_files
    return count_files


def stats_command(
    path: str = ".",
    output_json: bool = False,
    exclude_dirs: tuple = (),
    exclude_files: tuple = (),
    exclude_extensions: tuple = (),
    max_depth: Optional[int] = None,
    follow_symlinks: bool = False,
    sort_by: str = "count",
) -> None:
    """统计项目文件数量。

    PATH 是要统计的项目根目录路径，默认为当前目录。
    """
    count_files = _get_count_files()
    result = count_files(
        root_path=path,
        exclude_dirs=set(exclude_dirs),
        exclude_files=set(exclude_files),
        exclude_extensions=set(exclude_extensions),
        max_depth=max_depth,
        follow_symlinks=follow_symlinks,
    )

    if output_json:
        data = {
            "total_files": result.total_files,
            "total_dirs": result.total_dirs,
            "total_size": result.total_size,
            "by_type": {k: v.to_dict() for k, v in result.by_type.items()},
            "by_directory": result.by_directory,
            "errors": result.errors,
        }
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        console = Console()
        console.print(f"📊 项目统计: {path}")
        console.print(f"  文件总数: {result.total_files}")
        console.print(f"  目录总数: {result.total_dirs}")
        console.print(f"  总大小: {result.total_size:,} 字节")
        if result.by_type:
            console.print("\n📁 按类型分类:")
            sorted_types = sorted(
                result.by_type.items(),
                key=lambda x: x[1].count,
                reverse=True,
            )
            for ext, stats in sorted_types:
                console.print(
                    f"  {ext or '(无扩展名)'}: {stats.count} 个文件, {stats.total_size:,} 字节"
                )
        if result.errors:
            console.print(f"\n⚠️ {len(result.errors)} 个错误:", err=True)
            for error in result.errors:
                console.print(f"  {error}", err=True)


# ============================================================================
# Trace 子命令（来自 cli_trace.py）
# ============================================================================

console_trace = Console()


def _get_store():
    """延迟导入 TraceStore"""
    from src.agents.transparency import TraceStore

    return TraceStore.get_instance()


def trace_list(
    session: str = None,
    limit: int = 20,
) -> None:
    """列出最近执行记录"""
    store = _get_store()
    sessions = [session] if session else store.list_sessions()[:limit]

    if not sessions:
        console_trace.print("[dim]暂无执行记录[/dim]")
        return

    for sid in sessions:
        traces = store.list_traces(sid)
        if not traces:
            continue
        console_trace.print(f"\n[bold cyan]Session: {sid}[/bold cyan] ({len(traces)} 条记录)")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Agent", style="green")
        table.add_column("状态", style="yellow")
        table.add_column("耗时", style="blue")
        table.add_column("开始时间", style="dim")
        table.add_column("摘要", style="white")
        for t in traces[:10]:
            duration = f"{t.get('total_duration_ms', 0) / 1000:.2f}s"
            started = t.get("started_at", "")[:19]
            status = t.get("status", "unknown")
            summary = t.get("output_summary", "")[:40]
            error = t.get("error", "")
            table.add_row(
                t.get("agent_name", ""),
                status,
                duration,
                started,
                (summary + " ❌ " + error[:20]) if error else summary,
            )
        console_trace.print(table)


def trace_show(
    agent: str,
    session: str = None,
) -> None:
    """显示某个 Agent 的详细执行过程"""
    store = _get_store()
    sid = session or store.get_latest_session()
    if not sid:
        console_trace.print("[red]没有可用的 session[/red]")
        raise typer.Exit(1)

    trace_data = store.get_trace(sid, agent)
    if not trace_data:
        # 尝试模糊匹配
        all_agents = store.get_all_agents_in_session(sid)
        if agent in all_agents:
            trace_data = store.get_trace(sid, agent)
        else:
            # 模糊匹配
            matches = [a for a in all_agents if agent.lower() in a.lower()]
            if matches:
                trace_data = store.get_trace(sid, matches[0])
                console_trace.print(f"[dim]模糊匹配到: {matches[0]}[/dim]")
            else:
                console_trace.print(f"[red]未找到 Agent '{agent}' 的记录[/red]")
                if all_agents:
                    console_trace.print("[dim]可用 Agent:[/dim] " + ", ".join(all_agents))
                raise typer.Exit(1)

    # Header
    console_trace.print(
        Panel(
            f"[green]Agent:[/green] {trace_data['agent_name']}\n"
            f"[green]Session:[/green] {trace_data['session_id']}\n"
            f"[green]状态:[/green] {trace_data['status']}\n"
            f"[green]总耗时:[/green] {trace_data['total_duration_ms'] / 1000:.2f}s\n"
            f"[green]开始:[/green] {trace_data['started_at'][:19]}\n"
            f"[green]结束:[/green] {trace_data['ended_at'][:19]}",
            title=f"Trace: {trace_data['agent_name']}",
            border_style="cyan",
        )
    )

    if trace_data.get("error"):
        console_trace.print(f"[red]错误: {trace_data['error']}[/red]")

    # Events timeline
    events = trace_data.get("events", [])
    if not events:
        console_trace.print("[dim]无事件记录[/dim]")
        return

    for _i, ev in enumerate(events):
        etype = ev.get("type", "")
        ts = ev.get("timestamp", "")[11:23]  # HH:MM:SS.mmm
        desc = ev.get("description", "")
        dur_ms = ev.get("duration_ms", 0)
        dur_str = f"[dim]@{dur_ms / 1000:.3f}s[/dim]"

        # 类型标签颜色
        color_map = {
            "start": "bold green",
            "end": "bold red",
            "read_file": "cyan",
            "write_file": "yellow",
            "call_api": "magenta",
            "run_command": "blue",
            "error": "bold red",
            "thinking": "white",
            "metadata": "dim",
        }
        style = color_map.get(etype, "white")
        label = f"[{style}]{etype:12s}[/{style}]"

        details = ev.get("details", {})
        extra = ""
        if details:
            if "path" in details:
                extra = f"  → {details['path']}"
            elif "command" in details:
                extra = f"  → {details['command'][:60]}"
            elif "model" in details:
                extra = (
                    f"  → model={details['model']} tokens={details.get('tokens', 0)}"
                )

        console_trace.print(f"  {ts} {dur_str} {label} {desc}{extra}")

        preview = ev.get("output_preview", "")
        if preview:
            console_trace.print(f"         [dim]│ {preview[:80]}[/dim]")


def trace_agents(
    session: str = None,
) -> None:
    """显示当前 session 的所有 Agent"""
    store = _get_store()
    sid = session or store.get_latest_session()
    if not sid:
        console_trace.print("[red]没有可用的 session[/red]")
        raise typer.Exit(1)
    agents = store.get_all_agents_in_session(sid)
    if not agents:
        console_trace.print("[dim]暂无 Agent 记录[/dim]")
    else:
        console_trace.print(f"[cyan]Session {sid}[/cyan] 的 Agents:")
        for a in agents:
            console_trace.print(f"  • {a}")


def trace_latest() -> None:
    """显示最新 session"""
    store = _get_store()
    sid = store.get_latest_session()
    if not sid:
        console_trace.print("[dim]暂无执行记录[/dim]")
        return
    console_trace.print(f"[green]最新 Session: {sid}[/green]")
    trace_list(session=sid, limit=10)


# ============================================================================
# Memory 子命令（来自 cli_memory.py）
# ============================================================================

console_memory = Console()


def _get_manager(project_path: Path):
    """初始化 MemoryManager"""
    from src.memory.manager import MemoryManager

    return MemoryManager.from_project(project_path)


def memory_tier0(
    project_path: Path = ".",
) -> None:
    """
    🧠 查看 Tier 0 核心记忆（< 500 token）

    用于系统 Prompt 注入的最精简记忆。
    """
    manager = _get_manager(Path(project_path).resolve())
    tier0 = manager.get_tier0_summary()

    tokens = manager.count_tokens(tier0)

    console_memory.print(
        Panel(
            tier0 if tier0.strip() else "[dim]（空）[/dim]",
            title=f"🧠 Tier 0 核心记忆 [{tokens} tokens]",
            border_style="cyan",
        )
    )


def memory_tier1(
    project_path: Path = ".",
) -> None:
    """
    📋 查看 Tier 1 精选记忆（< 2000 token）

    项目特定知识、常用命令、重要经验。
    """
    manager = _get_manager(Path(project_path).resolve())
    tier1 = manager.get_tier1_summary()

    tokens = manager.count_tokens(tier1)

    console_memory.print(
        Panel(
            tier1 if tier1.strip() else "[dim]（空）[/dim]",
            title=f"📋 Tier 1 精选记忆 [{tokens} tokens]",
            border_style="green",
        )
    )


def memory_summary(
    project_path: Path = ".",
) -> None:
    """
    📦 查看完整记忆摘要（Tier 2 存档）

    所有项目、所有学习记录、所有偏好。
    """
    manager = _get_manager(Path(project_path).resolve())
    archive = manager.get_tier2_archive()

    tokens = manager.count_tokens(archive)

    console_memory.print(
        Panel(
            archive[:5000]
            + (
                f"\n\n[dim]... （截断显示，共 {tokens} tokens）[/dim]"
                if len(archive) > 5000
                else ""
            ),
            title=f"📦 Tier 2 完整存档 [{tokens} tokens]",
            border_style="yellow",
        )
    )


def memory_stats(
    project_path: Path = ".",
) -> None:
    """
    📊 查看记忆统计

    项目数、学习记录数、各层 token 消耗。
    """
    manager = _get_manager(Path(project_path).resolve())
    stats = manager.get_memory_stats()

    table = Table(title="📊 记忆统计")
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green")

    table.add_row("项目数", str(stats["projects_count"]))
    table.add_row("学习记录数", str(stats["learnings_count"]))
    table.add_row("Tier 0 tokens", str(stats["tier0_tokens"]))
    table.add_row("Tier 1 tokens", str(stats["tier1_tokens"]))

    if stats["categories"]:
        table.add_row("分类", ", ".join(stats["categories"]))

    console_memory.print(table)


# ============================================================================
# Typer App 定义
# ============================================================================

app = typer.Typer(
    name="usage",
    help="用量统计与追踪 - stats/trace/memory",
    no_args_is_help=True,
)

# Stats 子命令
stats_app = typer.Typer(name="stats", help="项目文件统计")
app.add_typer(stats_app, name="stats")


@stats_app.callback(invoke_without_command=True)
def stats_main(
    ctx: typer.Context,
    path: str = typer.Argument(
        ".",
        help="项目路径",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="以 JSON 格式输出统计结果",
    ),
    exclude_dir: list[str] = typer.Option(
        [],
        "--exclude-dir",
        help="额外排除的目录名（可多次指定）",
    ),
    exclude_file: list[str] = typer.Option(
        [],
        "--exclude-file",
        help="额外排除的文件名（可多次指定）",
    ),
    exclude_ext: list[str] = typer.Option(
        [],
        "--exclude-ext",
        help="额外排除的文件扩展名（可多次指定）",
    ),
    max_depth: Optional[int] = typer.Option(
        None,
        "--max-depth",
        help="最大递归深度",
    ),
    follow_symlinks: bool = typer.Option(
        False,
        "--follow-symlinks",
        help="跟随符号链接",
    ),
    sort: str = typer.Option(
        "count",
        "--sort",
        help="排序方式（仅 JSON 输出有效）",
    ),
) -> None:
    """统计项目文件数量"""
    if ctx.invoked_subcommand is None:
        stats_command(
            path=path,
            output_json=json_output,
            exclude_dirs=tuple(exclude_dir),
            exclude_files=tuple(exclude_file),
            exclude_extensions=tuple(exclude_ext),
            max_depth=max_depth,
            follow_symlinks=follow_symlinks,
            sort_by=sort,
        )


# Trace 子命令
trace_app = typer.Typer(name="trace", help="查看 Agent 执行记录")
app.add_typer(trace_app, name="trace")


@trace_app.command("list")
def trace_list_cmd(
    session: str = typer.Option(None, "--session", "-s", help="指定 session ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="显示条数"),
) -> None:
    """列出最近执行记录"""
    trace_list(session=session, limit=limit)


@trace_app.command("show")
def trace_show_cmd(
    agent: str = typer.Argument(..., help="Agent 名称"),
    session: str = typer.Option(None, "--session", "-s", help="指定 session ID"),
) -> None:
    """显示某个 Agent 的详细执行过程"""
    trace_show(agent=agent, session=session)


@trace_app.command("agents")
def trace_agents_cmd(
    session: str = typer.Option(None, "--session", "-s", help="指定 session ID"),
) -> None:
    """显示当前 session 的所有 Agent"""
    trace_agents(session=session)


@trace_app.command("latest")
def trace_latest_cmd() -> None:
    """显示最新 session"""
    trace_latest()


# Memory 子命令
memory_app = typer.Typer(name="memory", help="分层记忆管理")
app.add_typer(memory_app, name="memory")


@memory_app.command("tier0")
def memory_tier0_cmd(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
) -> None:
    """
    🧠 查看 Tier 0 核心记忆（< 500 token）

    用于系统 Prompt 注入的最精简记忆。
    """
    memory_tier0(project_path=project_path)


@memory_app.command("tier1")
def memory_tier1_cmd(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
) -> None:
    """
    📋 查看 Tier 1 精选记忆（< 2000 token）

    项目特定知识、常用命令、重要经验。
    """
    memory_tier1(project_path=project_path)


@memory_app.command("summary")
def memory_summary_cmd(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
) -> None:
    """
    📦 查看完整记忆摘要（Tier 2 存档）

    所有项目、所有学习记录、所有偏好。
    """
    memory_summary(project_path=project_path)


@memory_app.command("stats")
def memory_stats_cmd(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
) -> None:
    """
    📊 查看记忆统计

    项目数、学习记录数、各层 token 消耗。
    """
    memory_stats(project_path=project_path)


if __name__ == "__main__":
    app()
