"""
omc trace 命令 - 查看 Agent 执行记录

用法：
    omc trace list          — 列出最近 session 和 trace
    omc trace show <agent>  — 显示某个 Agent 的详细执行过程
    omc trace agents        — 显示当前 session 的所有 Agent
    omc trace latest        — 显示最新 session
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agents.transparency import TraceStore

console = Console()
app = typer.Typer(name="trace", help="查看 Agent 执行记录")


def _get_store() -> TraceStore:
    return TraceStore.get_instance()


@app.command("list")
def trace_list(
    session: str = typer.Option(None, "--session", "-s", help="指定 session ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="显示条数"),
) -> None:
    """列出最近执行记录"""
    sessions = [session] if session else _get_store().list_sessions()[:limit]

    if not sessions:
        console.print("[dim]暂无执行记录[/dim]")
        return

    for sid in sessions:
        traces = _get_store().list_traces(sid)
        if not traces:
            continue
        console.print(f"\n[bold cyan]Session: {sid}[/bold cyan] ({len(traces)} 条记录)")
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
        console.print(table)


@app.command("show")
def trace_show(
    agent: str = typer.Argument(..., help="Agent 名称"),
    session: str = typer.Option(None, "--session", "-s", help="指定 session ID"),
) -> None:
    """显示某个 Agent 的详细执行过程"""
    sid = session or _get_store().get_latest_session()
    if not sid:
        console.print("[red]没有可用的 session[/red]")
        raise typer.Exit(1)

    trace_data = _get_store().get_trace(sid, agent)
    if not trace_data:
        # 尝试模糊匹配
        all_agents = _get_store().get_all_agents_in_session(sid)
        if agent in all_agents:
            trace_data = _get_store().get_trace(sid, agent)
        else:
            # 模糊匹配
            matches = [a for a in all_agents if agent.lower() in a.lower()]
            if matches:
                trace_data = _get_store().get_trace(sid, matches[0])
                console.print(f"[dim]模糊匹配到: {matches[0]}[/dim]")
            else:
                console.print(f"[red]未找到 Agent '{agent}' 的记录[/red]")
                if all_agents:
                    console.print("[dim]可用 Agent:[/dim] " + ", ".join(all_agents))
                raise typer.Exit(1)

    # Header
    console.print(
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
        console.print(f"[red]错误: {trace_data['error']}[/red]")

    # Events timeline
    events = trace_data.get("events", [])
    if not events:
        console.print("[dim]无事件记录[/dim]")
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

        console.print(f"  {ts} {dur_str} {label} {desc}{extra}")

        preview = ev.get("output_preview", "")
        if preview:
            console.print(f"         [dim]│ {preview[:80]}[/dim]")


@app.command("agents")
def trace_agents(
    session: str = typer.Option(None, "--session", "-s", help="指定 session ID"),
) -> None:
    """显示当前 session 的所有 Agent"""
    sid = session or _get_store().get_latest_session()
    if not sid:
        console.print("[red]没有可用的 session[/red]")
        raise typer.Exit(1)
    agents = _get_store().get_all_agents_in_session(sid)
    if not agents:
        console.print("[dim]暂无 Agent 记录[/dim]")
    else:
        console.print(f"[cyan]Session {sid}[/cyan] 的 Agents:")
        for a in agents:
            console.print(f"  • {a}")


@app.command("latest")
def trace_latest() -> None:
    """显示最新 session"""
    sid = _get_store().get_latest_session()
    if not sid:
        console.print("[dim]暂无执行记录[/dim]")
        return
    console.print(f"[green]最新 Session: {sid}[/green]")
    ctx = typer.get_current_context()
    ctx.invoke(trace_list, session=sid, limit=10)


if __name__ == "__main__":
    app()
