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

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Forward reference for FileNode (defined in cli.py)
try:
    from src.commands.cli import FileNode
except ImportError:
    # Type checking only
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from src.commands.cli import FileNode

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
                    f"  {ext or '(无扩展名)'}: {stats.count} 个文件, {stats.size:,} 字节"
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
        raise typer.Exit(0)
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


# ============================================================================
# Compact 子命令（来自 cli_compact.py）
# ============================================================================

console_compact = Console()


@app.command("stats")
def compact_stats(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
) -> None:
    """
    📊 显示当前会话的压缩统计

    显示内容：
    - 压缩总次数
    - 节省的 token 数
    - 清理的消息数
    - 工具调用去重次数
    - 历史错误清理数
    """
    from src.memory.manager import MemoryManager
    manager = MemoryManager.from_project(project_path.resolve())
    stats = manager.compact_stats

    table = Table(
        title="🗜️ AutoCompact 统计", show_header=True, header_style="bold cyan"
    )
    table.add_column("指标", style="dim")
    table.add_column("值", justify="right")

    table.add_row("压缩次数", f"{stats['total_compact_count']}")
    table.add_row("节省 token", f"{stats['total_tokens_saved']:,}")
    table.add_row("清理消息数", f"{stats['total_messages_removed']:,}")
    table.add_row("去重 tool_call", f"{stats['total_deduplicated']}")
    table.add_row("清理错误消息", f"{stats['total_errors_removed']}")

    console_compact.print(table)

    if stats["total_compact_count"] == 0:
        console_compact.print("\n[dim]尚未执行过压缩，暂无统计数据。[/dim]")


@app.command("sweep")
def compact_sweep(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
    since_last_user: bool = typer.Option(
        False,
        "--since-last-user",
        help="从最后用户消息开始压缩（丢弃之前的消息）",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示结果，不实际压缩"),
) -> None:
    """
    🧹 手动触发压缩（sweep）

    可选标志：
      --since-last-user  从最后用户消息开始清理
      --dry-run           只显示结果，不实际压缩
    """
    from src.memory.manager import MemoryManager
    manager = MemoryManager.from_project(project_path.resolve())
    session = manager.get_latest_session()

    if session is None:
        console_compact.print("[red]未找到活跃会话。[/red]")
        raise typer.Exit(1)

    if since_last_user:
        console_compact.print("[cyan]从最后用户消息开始裁剪...[/cyan]")
        # 找到最后一条 user 消息
        messages = session.messages
        last_user_idx = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].role == "user":
                last_user_idx = i
                break
        if last_user_idx is not None and last_user_idx > 0:
            session.messages = messages[last_user_idx:]
            console_compact.print(
                f"[green]已裁剪到第 {last_user_idx + 1} 条消息（共 {len(messages)} 条）[/green]"
            )
        else:
            console_compact.print("[yellow]未找到更早的用户消息，无需裁剪。[/yellow]")
            raise typer.Exit(0)

    if dry_run:
        # 只检查，不压缩
        result = manager.auto_compact_check(session, force=False, since_last_user=False)
        if result.compacted:
            console_compact.print(
                f"[yellow]Dry-run: 将压缩 {result.messages_removed} 条消息，"
                f"节省约 {result.tokens_saved} tokens[/yellow]"
            )
        else:
            console_compact.print("[dim]Dry-run: 当前使用率未达到阈值，无需压缩。[/dim]")
            console_compact.print(f"  当前 token: {result.tokens_before}")
        raise typer.Exit(0)

    result = manager.auto_compact_check(session, force=True)
    manager.save_session(session)

    if result.compacted:
        console_compact.print(
            f"[green]✅ 压缩完成: 清理 {result.messages_removed} 条消息，"
            f"节省 ~{result.tokens_saved} tokens[/green]"
        )
    else:
        console_compact.print("[yellow]⚠️  未触发压缩（usage_ratio < threshold）。[/yellow]")
        console_compact.print(f"  当前 token: {result.tokens_before}")


# ============================================================================
# Thought 子命令（来自 cli_thought.py）
# ============================================================================

console_thought = Console()


@app.command("start")
def thought_start(
    task: str = typer.Argument(..., help="任务描述"),
    agent: str = typer.Option("assistant", "--agent", "-a", help="Agent 名称"),
) -> None:
    """开始记录思维链"""
    from src.core.chain_of_thought import ChainOfThoughtRecorder
    recorder = ChainOfThoughtRecorder()
    chain = recorder.start_chain(task, agent)

    console_thought.print("[green]✅ 思维链已启动[/green]")
    console_thought.print(f"[dim]ID: {chain.chain_id}[/dim]")
    console_thought.print(f"任务: {chain.task_description}")
    console_thought.print("\n[dim]使用以下命令添加步骤:[/dim]")
    console_thought.print(f"  omc thought step {chain.chain_id} -t analysis -d '分析...'")


@app.command("step")
def thought_step(
    chain_id: str = typer.Argument(..., help="思维链 ID"),
    step_type: str = typer.Option("analysis", "--type", "-t", help="步骤类型"),
    description: str = typer.Option(..., "--desc", "-d", help="步骤描述"),
    reasoning: str = typer.Option("", "--reasoning", "-r", help="推理过程"),
    conclusion: str = typer.Option("", "--conclusion", "-c", help="结论"),
    confidence: str = typer.Option("medium", "--confidence", help="置信度"),
) -> None:
    """添加推理步骤"""
    from src.core.chain_of_thought import (
        ChainOfThoughtRecorder,
        ConfidenceLevel,
        ReasoningStepType,
    )
    recorder = ChainOfThoughtRecorder()

    try:
        st = ReasoningStepType(step_type)
    except ValueError:
        console_thought.print(f"[red]无效步骤类型: {step_type}[/red]")
        console_thought.print(f"可用: {[t.value for t in ReasoningStepType]}")
        raise typer.Exit(1)

    try:
        conf = ConfidenceLevel(confidence)
    except ValueError:
        conf = ConfidenceLevel.MEDIUM

    step = recorder.add_step(
        chain_id=chain_id,
        step_type=st,
        description=description,
        reasoning=reasoning or description,
        conclusion=conclusion,
        confidence=conf,
    )

    if step:
        console_thought.print(f"[green]✅ 步骤已添加[/green] [{step.step_id}]")
    else:
        console_thought.print(f"[red]思维链不存在: {chain_id}[/red]")
        raise typer.Exit(1)


@app.command("complete")
def thought_complete(
    chain_id: str = typer.Argument(..., help="思维链 ID"),
    conclusion: str = typer.Option("", "--conclusion", "-c", help="最终结论"),
) -> None:
    """完成思维链"""
    from src.core.chain_of_thought import ChainOfThoughtRecorder
    recorder = ChainOfThoughtRecorder()
    recorder.complete_chain(chain_id, conclusion)
    console_thought.print(f"[green]✅ 思维链已完成[/green] {chain_id}")


@app.command("show")
def thought_show(
    chain_id: str = typer.Argument(..., help="思维链 ID"),
    format: str = typer.Option(
        "text", "--format", "-f", help="格式: text/html/mermaid"
    ),
) -> None:
    """查看思维链"""
    import tempfile

    from src.core.chain_of_thought import (
        ChainOfThoughtRecorder,
        visualize_chain,
    )
    recorder = ChainOfThoughtRecorder()
    chain = recorder.get_chain(chain_id)

    if not chain:
        console_thought.print(f"[red]思维链不存在: {chain_id}[/red]")
        raise typer.Exit(1)

    output = visualize_chain(chain, format)

    if format == "html":
        # 保存到临时文件
        output_path = os.path.join(tempfile.gettempdir(), f"chain_{chain_id}.html")
        with open(output_path, "w") as f:
            f.write(output)
        console_thought.print(f"[green]HTML 已保存:[/green] {output_path}")
    else:
        console_thought.print(output)


@app.command("list")
def thought_list(
    agent: str = typer.Option(None, "--agent", "-a", help="按 Agent 过滤"),
) -> None:
    """列出思维链"""
    from src.core.chain_of_thought import ChainOfThoughtRecorder
    recorder = ChainOfThoughtRecorder()
    chains = recorder.list_chains(agent)

    if not chains:
        console_thought.print("[dim]没有思维链[/dim]")
        return

    table = Table(title="思维链列表")
    table.add_column("ID", style="cyan")
    table.add_column("任务", style="green")
    table.add_column("Agent", style="blue")
    table.add_column("步骤数", justify="right")
    table.add_column("状态", style="yellow")

    for c in chains:
        table.add_row(
            c.chain_id,
            c.task_description[:40],
            c.agent_name,
            str(len(c.steps)),
            c.status,
        )

    console_thought.print(table)


# ============================================================================
# Context 子命令（来自 cli_context.py）
# ============================================================================

console_context = Console()

# 延迟导入以避免循环依赖

def _get_scanner():
    """延迟导入 WorkspaceScanner"""
    from src.context import WorkspaceScanner
    return WorkspaceScanner


def _get_browser_awareness():
    """延迟导入 BrowserAwareness"""
    from src.context import BrowserAwareness
    return BrowserAwareness


context_app = typer.Typer(
    name="context",
    help="工作目录上下文管理 — 扫描文件、获取摘要、感知浏览器",
    add_completion=False,
    no_args_is_help=True,
)

app.add_typer(context_app, name="context")


@context_app.command("scan")
def context_scan(
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="项目路径",
    ),
    depth: int = typer.Option(3, "--depth", "-d", help="扫描深度（最大递归层数）"),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="以 JSON 格式输出（便于程序解析）"
    ),
) -> None:
    """
    扫描当前工作目录，生成文件树结构

    示例：
        omc usage context scan
        omc usage context scan -p /path/to/project -d 2
        omc usage context scan --depth 5
        omc usage context scan --json
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    scanner = _get_scanner()(project_path.resolve())

    # 执行扫描
    tree = scanner.scan(max_depth=depth)
    stats = scanner._scan_stats

    if json_output:
        import json

        console.print(
            json.dumps(
                {
                    "tree": tree.to_dict(),
                    "stats": {
                        "files_scanned": stats["files_scanned"],
                        "dirs_scanned": stats["dirs_scanned"],
                        "bytes_scanned": stats["bytes_scanned"],
                        "errors": stats["errors"],
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # 渲染文件树
    lines = scanner._render_tree(tree, prefix="", is_last=True)
    tree_str = "\n".join(lines)

    # 格式化统计
    size_str = scanner._format_size(stats["bytes_scanned"])

    console.print(
        Panel(
            f"[bold cyan]{project_path.name}[/bold cyan] ({project_path})\n"
            f"[dim]深度: {depth} | "
            f"文件: {stats['files_scanned']} | "
            f"目录: {stats['dirs_scanned']} | "
            f"大小: {size_str}[/dim]",
            title="📁 工作目录扫描",
            border_style="cyan",
        )
    )

    console.print(f"\n[white]{tree_str}[/white]\n")

    # 错误提示
    if stats["errors"]:
        console.print(f"[yellow]⚠️  {len(stats['errors'])} 个错误[/yellow]")
        for err in stats["errors"][:5]:
            console.print(f"  [dim]{err}[/dim]")
        if len(stats["errors"]) > 5:
            console.print(f"  [dim]... 共 {len(stats['errors'])} 个[/dim]")


@context_app.command("summary")
def context_summary(
    path: str = typer.Argument(..., help="文件或目录路径"),
    max_lines: int = typer.Option(50, "--lines", "-n", help="最大读取行数"),
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="项目根目录（用于计算相对路径）",
    ),
) -> None:
    """
    生成文件摘要

    显示指定文件的内容摘要，包括：
    - 基本信息（大小、修改时间）
    - 代码结构（导入、类、函数）
    - 内容预览

    示例：
        omc usage context summary src/main.py
        omc usage context summary config.yaml -n 100
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax

    console = Console()
    scanner = _get_scanner()(project_path.resolve())

    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = project_path / file_path

    if not file_path.exists():
        console.print(f"[red]✗ 文件不存在: {file_path}[/red]")
        raise typer.Exit(1)

    result = scanner.get_file_summary(file_path, max_lines=max_lines)

    # 解析摘要结果
    lines = result.split("\n")
    header_lines = []
    content_lines = []
    in_content = False

    for line in lines:
        if line.startswith("---"):
            in_content = True
            continue
        if in_content:
            content_lines.append(line)
        else:
            header_lines.append(line)

    header = "\n".join(header_lines)
    content = "\n".join(content_lines)

    # 检测语言用于语法高亮
    lang = None
    for line in header_lines:
        if line.startswith("["):
            lang = line.split("]")[0][1:]
            break

    console.print(Panel(header, title=f"📄 {file_path.name}", border_style="green"))

    if content_lines:
        # 如果是代码，尝试语法高亮
        if lang and lang not in ("unknown", "markdown", "rst"):
            try:
                syntax = Syntax(content, lang, theme="monokai", line_numbers=True)
                console.print(syntax)
            except Exception:
                console.print(content)
        else:
            console.print(content)


@context_app.command("browser")
def context_browser(
    watch: bool = typer.Option(
        False, "--watch", "-w", help="持续监控浏览器变化（Ctrl+C 退出）"
    ),
    interval: int = typer.Option(5, "--interval", "-i", help="监控间隔（秒）"),
) -> None:
    """
    获取浏览器当前上下文

    读取当前浏览器标签页的标题、URL 和内容摘要。
    需要安装 Playwright 或 Selenium。

    示例：
        omc usage context browser
        omc usage context browser --watch
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    awareness = _get_browser_awareness()()

    async def get_and_display():
        ctx = await awareness.get_current_tab()

        if not ctx.available:
            console.print(
                Panel(
                    "[yellow]浏览器上下文不可用[/yellow]\n\n"
                    "[dim]可能的原因：\n"
                    "  1. 未安装 Playwright 或 Selenium\n"
                    "  2. 没有活跃的浏览器标签页\n"
                    "  3. 浏览器拒绝了 CDP 连接[/dim]",
                    title="🌐 浏览器上下文",
                    border_style="yellow",
                )
            )
            return

        # 显示链接列表
        links_text = ""
        if ctx.links:
            links_text = "\n\n[cyan]链接预览:[/cyan]\n"
            for link in ctx.links[:10]:
                links_text += f"  • {link}\n"

        console.print(
            Panel(
                f"[bold]{ctx.title}[/bold]\n"
                f"[dim]{ctx.url}[/dim]\n\n"
                f"[green]内容摘要:[/green]\n"
                f"{ctx.content[:500]}"
                + ("..." if len(ctx.content) > 500 else "")
                + links_text,
                title="🌐 浏览器上下文",
                border_style="green",
            )
        )

    async def watch_loop():
        console.print("[dim]持续监控浏览器，按 Ctrl+C 退出...[/dim]\n")
        try:
            while True:
                console.clear()
                await get_and_display()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            console.print("\n[dim]监控已退出[/dim]")

    if watch:
        asyncio.run(watch_loop())
    else:
        asyncio.run(get_and_display())


@context_app.command("tree")
def context_tree(
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="项目路径",
    ),
    depth: int = typer.Option(3, "--depth", "-d", help="显示深度"),
    filter_ext: str = typer.Option(
        None, "--ext", "-e", help="只显示特定扩展名（如 py, js）"
    ),
) -> None:
    """
    显示文件树

    以树形结构显示项目目录，类似于 tree 命令。

    示例：
        omc usage context tree
        omc usage context tree -p src -d 2
        omc usage context tree --ext py
    """
    from rich.console import Console
    from rich.tree import Tree

    console = Console()

    scanner = _get_scanner()(project_path.resolve())
    tree_node = scanner.scan(max_depth=depth)

    def build_rich_tree(node: FileNode, filter_ext: Optional[str] = None) -> Tree:
        """构建 rich Tree"""
        label = f"[cyan]{node.name}[/cyan]"
        if node.language:
            label += f" [dim][[{node.language}]][/dim]"
        if node.size > 0 and not node.is_dir:
            label += f" [dim]({scanner._format_size(node.size)})[/dim]"

        t = Tree(label)

        if node.is_dir and node.children:
            for child in node.children:
                if filter_ext:
                    ext = filter_ext.lstrip(".").lower()
                    child_lang = scanner.LANGUAGE_EXTENSIONS.get(f".{ext}")
                    if child.is_dir or child.language == child_lang:
                        t.add(build_rich_tree(child, filter_ext))
                else:
                    t.add(build_rich_tree(child, filter_ext))

        return t

    console.print(
        build_rich_tree(tree_node, filter_ext),
        soft_wrap=True,
    )


@context_app.command("stats")
def context_stats(
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="项目路径",
    ),
) -> None:
    """
    显示项目统计信息

    统计项目的文件数量、代码行数、各语言占比等信息。

    示例：
        omc usage context stats
        omc usage context stats -p /path/to/project
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    scanner = _get_scanner()(project_path.resolve())

    # 扫描两次（一次深度大，一次深度小）
    tree = scanner.scan(max_depth=10)

    # 统计各语言文件数和行数
    lang_stats: dict = {}

    def collect_stats(node: FileNode):
        if node.is_dir:
            for child in node.children:
                collect_stats(child)
        else:
            lang = node.language or "other"
            if lang not in lang_stats:
                lang_stats[lang] = {"files": 0, "lines": 0, "size": 0}

            lang_stats[lang]["files"] += 1
            lang_stats[lang]["size"] += node.size

            # 统计行数
            try:
                with open(node.path, encoding="utf-8", errors="replace") as f:
                    lang_stats[lang]["lines"] += sum(1 for _ in f if _.strip())
            except Exception:
                pass

    collect_stats(tree)

    # 按文件数排序
    sorted_langs = sorted(
        lang_stats.items(),
        key=lambda x: x[1]["files"],
        reverse=True,
    )

    # 统计表
    table = Table(title="语言统计")
    table.add_column("语言", style="cyan")
    table.add_column("文件", justify="right")
    table.add_column("行数", justify="right")
    table.add_column("大小", justify="right")

    total_files = sum(s["files"] for _, s in sorted_langs)
    total_lines = sum(s["lines"] for _, s in sorted_langs)
    total_size = sum(s["size"] for _, s in sorted_langs)

    for lang, s in sorted_langs[:15]:
        table.add_row(
            lang,
            str(s["files"]),
            f"{s['lines']:,}",
            scanner._format_size(s["size"]),
        )

    console.print(
        Panel(
            f"[cyan]项目:[/cyan] {project_path}\n"
            f"[cyan]文件:[/cyan] {total_files} 个\n"
            f"[cyan]代码行数:[/cyan] {total_lines:,} 行\n"
            f"[cyan]总大小:[/cyan] {scanner._format_size(total_size)}",
            title="📊 项目统计",
            border_style="green",
        )
    )
    console.print(table)


# ============================================================================
# Cost 子命令（来自 cli_cost.py）
# ============================================================================

console_cost = Console()

# 配置路径
_COST_CONFIG_DIR = Path.home() / ".config" / "oh-my-coder"
_COST_USAGE_FILE = _COST_CONFIG_DIR / "usage.json"
_COST_PRICES_FILE = _COST_CONFIG_DIR / "model_prices.json"

# 默认模型价格（元/1k tokens）
_COST_DEFAULT_PRICES = {
    "deepseek-chat": {"prompt": 0.001, "completion": 0.002},
    "deepseek-coder": {"prompt": 0.001, "completion": 0.002},
    "gpt-4o": {"prompt": 0.036, "completion": 0.108},
    "gpt-4o-mini": {"prompt": 0.003, "completion": 0.012},
    "claude-3-opus": {"prompt": 0.105, "completion": 0.525},
    "claude-3-sonnet": {"prompt": 0.021, "completion": 0.105},
    "claude-3-haiku": {"prompt": 0.004, "completion": 0.02},
    "glm-4": {"prompt": 0.01, "completion": 0.01},
    "glm-4-flash": {"prompt": 0.0, "completion": 0.0},
    "qwen-turbo": {"prompt": 0.002, "completion": 0.006},
    "qwen-plus": {"prompt": 0.008, "completion": 0.02},
    "moonshot-v1": {"prompt": 0.006, "completion": 0.006},
    "hunyuan-lite": {"prompt": 0.0, "completion": 0.0},
    "hunyuan-standard": {"prompt": 0.0045, "completion": 0.005},
    "doubao-lite": {"prompt": 0.0003, "completion": 0.0006},
    "doubao-pro": {"prompt": 0.0008, "completion": 0.002},
    "minimax": {"prompt": 0.005, "completion": 0.005},
    "spark": {"prompt": 0.006, "completion": 0.006},
    "baichuan": {"prompt": 0.005, "completion": 0.005},
    "tiangong": {"prompt": 0.005, "completion": 0.005},
    "mimo": {"prompt": 0.002, "completion": 0.006},
    "ollama": {"prompt": 0.0, "completion": 0.0},
}


def _cost_load_prices() -> dict[str, dict[str, float]]:
    """加载模型价格配置"""
    if _COST_PRICES_FILE.exists():
        try:
            with open(_COST_PRICES_FILE, encoding="utf-8") as f:
                custom_prices = json.load(f)
                return {**_COST_DEFAULT_PRICES, **custom_prices}
        except Exception:
            pass
    return _COST_DEFAULT_PRICES


def _cost_load_usage_data() -> list[dict[str, Any]]:
    """加载使用记录"""
    if _COST_USAGE_FILE.exists():
        try:
            with open(_COST_USAGE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _cost_calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """计算单次调用成本"""
    prices = _cost_load_prices()
    model_lower = model.lower()

    if model_lower in prices:
        p = prices[model_lower]
        return (prompt_tokens / 1000) * p["prompt"] + (completion_tokens / 1000) * p["completion"]

    for key, p in prices.items():
        if model_lower.startswith(key) or key in model_lower:
            return (prompt_tokens / 1000) * p["prompt"] + (completion_tokens / 1000) * p["completion"]

    return (prompt_tokens + completion_tokens) / 1000 * 0.01


def _cost_format_datetime(dt_str: str) -> str:
    """格式化日期时间"""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str


def _cost_format_cost(cost: float) -> str:
    """格式化成本显示"""
    if cost == 0:
        return "Free"
    elif cost < 0.01:
        return "< 0.01"
    else:
        return f"{cost:.3f}"


def _cost_list_models(optimizer) -> None:
    """列出所有可用模型"""
    models = optimizer.get_all_models()
    by_provider: dict = {}
    for m in models:
        provider = m["provider"]
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(m)

    for provider, model_list in by_provider.items():
        console_cost.print(f"\n### {provider.upper()}")
        for m in model_list:
            cost_bars = "💰" * m["cost"]
            console_cost.print(f"  {m['model']:30s} {cost_bars}")


@app.command("suggest")
def cost_suggest(
    task: str = typer.Argument("", help="Task description"),
    files: int = typer.Option(0, "--files", "-f", help="Number of files involved"),
    list_models: bool = typer.Option(False, "--list", "-l", help="List all available models"),
    prefer_local: bool = typer.Option(True, "--prefer-local/--no-local", help="Prefer local models"),
) -> None:
    """Recommend optimal model based on task complexity"""
    from src.agents.cost_optimizer import CostOptimizer

    optimizer = CostOptimizer(prefer_local=prefer_local)

    if list_models:
        _cost_list_models(optimizer)
        return

    if not task:
        console_cost.print("[yellow]Please enter a task description, e.g.:[/yellow]")
        console_cost.print("  omc cost suggest 'fix login bug'")
        console_cost.print("  omc cost suggest 'design new system architecture'")
        console_cost.print("  omc cost suggest --files 15 'implement payment'")
        return

    recommendation = optimizer.recommend(task, file_count=files if files > 0 else None)

    complexity_colors = {"low": "green", "medium": "yellow", "high": "red"}
    cost_bars = "💰" * int(recommendation.estimated_cost)
    complexity_color = complexity_colors.get(recommendation.complexity.value, "white")
    complexity_val = recommendation.complexity.value.upper()
    complexity_text = f"[{complexity_color}]{complexity_val}[/]"

    panel = Panel(
        f"**Recommended Model**: [cyan]{recommendation.model}[/cyan]\n\n"
        f"**Provider**: {recommendation.provider}\n\n"
        f"**Complexity**: {complexity_text}\n\n"
        f"**Est. Cost**: {cost_bars}\n\n"
        f"**Reason**:\n{recommendation.reason}",
        title="🎯 Model Recommendation",
        border_style="cyan",
    )
    console_cost.print(panel)

    if recommendation.alternatives:
        console_cost.print("\n[dim]Alternatives:[/dim]")
        for alt in recommendation.alternatives:
            console_cost.print(f"  • {alt['model']}: {alt['reason']}")

    console_cost.print("\n[dim]💡 Tips:[/dim]")
    if recommendation.complexity.value == "low":
        console_cost.print("  Use local model for simple tasks - completely free")
    elif recommendation.complexity.value == "medium":
        console_cost.print("  Chinese models offer great value for medium complexity")
    else:
        console_cost.print("  For complex tasks, try local model first to validate ideas")


@app.command("report")
def cost_report(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to report"),
) -> None:
    """Show token usage summary (month/week/today)"""
    usage_data = _cost_load_usage_data()

    if not usage_data:
        console_cost.print(
            Panel.fit(
                "[yellow]No usage records found[/yellow]\n\n"
                "Usage data will be recorded automatically when you run tasks.",
                title="📊 Cost Report",
                border_style="yellow",
            )
        )
        return

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    stats = {
        "today": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
        "week": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
        "month": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
        "total": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
    }

    for record in usage_data:
        try:
            record_time = datetime.fromisoformat(record.get("timestamp", ""))
        except Exception:
            continue

        prompt = record.get("prompt_tokens", 0)
        completion = record.get("completion_tokens", 0)
        model = record.get("model", "unknown")
        cost = _cost_calculate_cost(model, prompt, completion)

        stats["total"]["calls"] += 1
        stats["total"]["prompt"] += prompt
        stats["total"]["completion"] += completion
        stats["total"]["cost"] += cost

        if record_time >= month_start:
            stats["month"]["calls"] += 1
            stats["month"]["prompt"] += prompt
            stats["month"]["completion"] += completion
            stats["month"]["cost"] += cost

            if record_time >= week_start:
                stats["week"]["calls"] += 1
                stats["week"]["prompt"] += prompt
                stats["week"]["completion"] += completion
                stats["week"]["cost"] += cost

                if record_time >= today_start:
                    stats["today"]["calls"] += 1
                    stats["today"]["prompt"] += prompt
                    stats["today"]["completion"] += completion
                    stats["today"]["cost"] += cost

    console_cost.print()
    console_cost.print(Panel.fit("[bold cyan]📊 Token Usage Summary[/bold cyan]", border_style="cyan"))
    console_cost.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Period", style="green")
    table.add_column("Calls", justify="right")
    table.add_column("Prompt Tokens", justify="right")
    table.add_column("Completion Tokens", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Est. Cost (CNY)", justify="right")

    for period, label in [("today", "Today"), ("week", "This Week"), ("month", "This Month"), ("total", "Total")]:
        s = stats[period]
        table.add_row(
            label,
            str(s["calls"]),
            f"{s['prompt']:,}",
            f"{s['completion']:,}",
            f"{s['prompt'] + s['completion']:,}",
            f"[green]{_cost_format_cost(s['cost'])}[/green]" if period != "total" else f"[bold green]{_cost_format_cost(s['cost'])}[/bold green]",
        )

    console_cost.print(table)
    console_cost.print(f"\n[dim]Data source: {_COST_USAGE_FILE}[/dim]")
    console_cost.print(f"[dim]Prices configured: {len(_cost_load_prices())} models[/dim]")


@app.command("model")
def cost_model(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to report"),
) -> None:
    """Show usage grouped by model"""
    usage_data = _cost_load_usage_data()

    if not usage_data:
        console_cost.print(
            Panel.fit(
                "[yellow]No usage records found[/yellow]\n\n"
                "Usage data will be recorded automatically when you run tasks.",
                title="📈 Model Usage",
                border_style="yellow",
            )
        )
        return

    model_stats: dict[str, dict[str, Any]] = {}

    for record in usage_data:
        model = record.get("model", "unknown")
        prompt = record.get("prompt_tokens", 0)
        completion = record.get("completion_tokens", 0)
        cost = _cost_calculate_cost(model, prompt, completion)

        if model not in model_stats:
            model_stats[model] = {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0}
        model_stats[model]["calls"] += 1
        model_stats[model]["prompt"] += prompt
        model_stats[model]["completion"] += completion
        model_stats[model]["cost"] += cost

    sorted_models = sorted(model_stats.items(), key=lambda x: x[1]["calls"], reverse=True)

    console_cost.print()
    console_cost.print(Panel.fit("[bold cyan]📈 Usage by Model[/bold cyan]", border_style="cyan"))
    console_cost.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Model", style="green")
    table.add_column("Calls", justify="right")
    table.add_column("Prompt Tokens", justify="right")
    table.add_column("Completion Tokens", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Est. Cost (CNY)", justify="right")

    total_calls = total_prompt = total_completion = total_cost = 0
    for model, stats in sorted_models:
        total_tokens = stats["prompt"] + stats["completion"]
        total_calls += stats["calls"]
        total_prompt += stats["prompt"]
        total_completion += stats["completion"]
        total_cost += stats["cost"]
        table.add_row(
            model,
            str(stats["calls"]),
            f"{stats['prompt']:,}",
            f"{stats['completion']:,}",
            f"{total_tokens:,}",
            f"[green]{_cost_format_cost(stats['cost'])}[/green]",
        )

    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_calls}[/bold]",
        f"[bold]{total_prompt:,}[/bold]",
        f"[bold]{total_completion:,}[/bold]",
        f"[bold]{total_prompt + total_completion:,}[/bold]",
        f"[bold green]{_cost_format_cost(total_cost)}[/bold green]",
    )

    console_cost.print(table)


@app.command("history")
def cost_history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to show"),
    model: str = typer.Option(None, "--model", "-m", help="Filter by model"),
) -> None:
    """Show recent call history"""
    usage_data = _cost_load_usage_data()

    if not usage_data:
        console_cost.print(
            Panel.fit(
                "[yellow]No usage records found[/yellow]\n\n"
                "Usage data will be recorded automatically when you run tasks.",
                title="📜 Call History",
                border_style="yellow",
            )
        )
        return

    filtered = usage_data
    if isinstance(model, str) and model:
        filtered = [r for r in filtered if model.lower() in r.get("model", "").lower()]

    sorted_records = sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

    console_cost.print()
    console_cost.print(
        Panel.fit(f"[bold cyan]📜 Recent Calls (last {len(sorted_records)})[/bold cyan]", border_style="cyan")
    )
    console_cost.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Time", style="dim", width=16)
    table.add_column("Model", style="green")
    table.add_column("Prompt", justify="right", width=10)
    table.add_column("Completion", justify="right", width=12)
    table.add_column("Total", justify="right", width=10)
    table.add_column("Cost", justify="right", width=10)

    for record in sorted_records:
        ts = _cost_format_datetime(record.get("timestamp", ""))
        m = record.get("model", "unknown")
        prompt = record.get("prompt_tokens", 0)
        completion = record.get("completion_tokens", 0)
        total = prompt + completion
        cost = _cost_calculate_cost(m, prompt, completion)
        table.add_row(ts, m[:30], f"{prompt:,}", f"{completion:,}", f"{total:,}", f"[green]{_cost_format_cost(cost)}[/green]")

    console_cost.print(table)
    if model:
        console_cost.print(f"\n[dim]Filtered by model: {model}[/dim]")


if __name__ == "__main__":
    app()
