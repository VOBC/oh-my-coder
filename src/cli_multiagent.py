"""
多 Agent 协作 CLI 命令

omc multiagent status      - 查看协作状态
omc multiagent spawn <role> <name> - 创建子 Agent
omc multiagent dispatch <task>     - 分发任务
omc multiagent list                - 列出所有子 Agent
omc multiagent remove <agent_id>   - 移除 Agent
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .multiagent.coordinator import (
    SubAgentStatus,
    get_coordinator,
)

app = typer.Typer(
    name="multiagent",
    help="多 Agent 协作 - 创建、调度、查看子 Agent",
    add_completion=False,
)
console = Console()


def _agent_status_color(status: SubAgentStatus) -> str:
    return {
        SubAgentStatus.IDLE: "dim",
        SubAgentStatus.RUNNING: "cyan",
        SubAgentStatus.COMPLETED: "green",
        SubAgentStatus.FAILED: "red",
    }.get(status, "white")


@app.command("status")
def multiagent_status() -> None:
    """
    查看多 Agent 协作状态

    示例:
        omc multiagent status
    """
    coordinator = get_coordinator()
    status = coordinator.get_status()

    console.print(
        Panel(
            f"[bold]总 Agent 数:[/bold] {status['total_agents']}\n"
            f"[bold]活跃任务:[/bold] {status['active_tasks']}\n\n"
            f"🔄 运行中: [cyan]{status['running']}[/cyan]\n"
            f"✅ 已完成: [green]{status['completed']}[/green]\n"
            f"❌ 失败: [red]{status['failed']}[/red]\n"
            f"⏳ 空闲: [dim]{status['idle']}[/dim]",
            title="🤖 多 Agent 状态",
            border_style="cyan",
        )
    )

    if status["agents"]:
        table = Table(title="子 Agent 列表")
        table.add_column("ID", style="cyan", width=10)
        table.add_column("名称", style="white")
        table.add_column("角色", style="yellow")
        table.add_column("状态", width=10)

        for agent in status["agents"]:
            color = _agent_status_color(SubAgentStatus(agent["status"]))
            status_display = f"[{color}]{agent['status']}[/{color}]"
            table.add_row(
                agent["agent_id"],
                agent["name"],
                agent["role"],
                status_display,
            )

        console.print(table)
    else:
        console.print("[dim]暂无子 Agent，使用 `omc multiagent spawn` 创建[/dim]")


@app.command("spawn")
def multiagent_spawn(
    role: str = typer.Argument(
        ..., help="Agent 角色 (coder/reviewer/tester/planner/explorer/executor)"
    ),
    name: str = typer.Argument(..., help="Agent 名称"),
    metadata: str = typer.Option(
        None,
        "--metadata",
        "-m",
        help="元数据 JSON 字符串",
    ),
) -> None:
    """
    创建子 Agent

    示例:
        omc multiagent spawn coder review-agent-1
        omc multiagent spawn reviewer security-checker -m '{"priority": "high"}'
    """
    import json

    meta = {}
    if metadata:
        try:
            meta = json.loads(metadata)
        except json.JSONDecodeError as e:
            console.print(f"[red]❗ metadata JSON 解析失败: {e}[/red]")
            raise typer.Exit(1)

    coordinator = get_coordinator()
    agent = coordinator.spawn(role=role, name=name, metadata=meta)

    console.print(
        Panel.fit(
            f"[green]✓ 子 Agent 已创建[/green]\n\n"
            f"ID:   [cyan]{agent.agent_id}[/cyan]\n"
            f"名称: [cyan]{agent.name}[/cyan]\n"
            f"角色: {role}\n"
            f"状态: [dim]idle[/dim]",
            title="🤖 子 Agent",
            border_style="green",
        )
    )


@app.command("list")
def multiagent_list() -> None:
    """
    列出所有子 Agent

    示例:
        omc multiagent list
    """
    coordinator = get_coordinator()
    agents = list(coordinator.agents.values())

    if not agents:
        console.print("[dim]暂无子 Agent[/dim]")
        return

    table = Table(title=f"子 Agent 列表 ({len(agents)})")
    table.add_column("ID", style="cyan", width=10)
    table.add_column("名称", style="white")
    table.add_column("角色", style="yellow")
    table.add_column("状态", width=10)
    table.add_column("创建时间", style="dim", width=18)

    for agent in agents:
        color = _agent_status_color(agent.status)
        status_display = f"[{color}]{agent.status.value}[/{color}]"
        table.add_row(
            agent.agent_id,
            agent.name,
            agent.role,
            status_display,
            agent.created_at[:19].replace("T", " "),
        )

    console.print(table)


@app.command("dispatch")
def multiagent_dispatch(
    task: str = typer.Argument(..., help="任务描述"),
    agent_ids: str = typer.Option(
        None,
        "--agents",
        "-a",
        help="指定 Agent ID（逗号分隔，默认全部）",
    ),
    mode: str = typer.Option(
        "parallel",
        "--mode",
        "-m",
        help="执行模式: parallel（并行）/ sequential（顺序）",
    ),
) -> None:
    """
    分发任务给子 Agent

    示例:
        omc multiagent dispatch "审查代码变更" -a agent1,agent2
        omc multiagent dispatch "实现功能X" --mode sequential
    """
    import asyncio

    coordinator = get_coordinator()
    all_agents = list(coordinator.agents.values())

    if not all_agents:
        console.print("[red]❗ 暂无子 Agent，先用 `omc multiagent spawn` 创建[/red]")
        raise typer.Exit(1)

    if agent_ids:
        target_ids = [id_.strip() for id_ in agent_ids.split(",")]
        target_agents = [coordinator.get_agent(aid) for aid in target_ids]
        target_agents = [a for a in target_agents if a is not None]
        if not target_agents:
            console.print(f"[red]❗ 未找到指定的 Agent: {agent_ids}[/red]")
            raise typer.Exit(1)
    else:
        target_agents = all_agents

    console.print(f"[cyan]分发任务给 {len(target_agents)} 个 Agent（{mode}）[/cyan]")
    for a in target_agents:
        console.print(f"  - {a.name} [{a.role}]")

    try:
        if mode == "sequential":
            result = asyncio.run(coordinator.dispatch_sequential(task, target_agents))
        else:
            result = asyncio.run(coordinator.dispatch(task, target_agents))

        console.print(
            Panel.fit(
                f"[green]✓ 任务完成[/green]\n\n"
                f"任务ID: [cyan]{result.task_id}[/cyan]\n"
                f"开始: {result.started_at}\n"
                f"完成: {result.completed_at}\n\n"
                f"[bold]汇总:[/bold]\n{result.summary}",
                title="📊 协作结果",
                border_style="green",
            )
        )

        # 各 Agent 结果
        for r in result.results:
            icon = "✅" if r.success else "❌"
            console.print(f"\n{icon} [{r.role}] {r.agent_id}")
            if r.success:
                output = str(r.output)[:200]
                if len(str(r.output)) > 200:
                    output += "..."
                console.print(f"   {output}")
            else:
                console.print(f"   [red]错误: {r.error}[/red]")

    except Exception as e:
        console.print(f"[red]❗ 分发失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("remove")
def multiagent_remove(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    force: bool = typer.Option(False, "--force", "-f", help="强制移除"),
) -> None:
    """
    移除子 Agent

    示例:
        omc multiagent remove abc12345
    """
    coordinator = get_coordinator()
    agent = coordinator.get_agent(agent_id)

    if agent is None:
        console.print(f"[red]❗ Agent 不存在: {agent_id}[/red]")
        raise typer.Exit(1)

    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"确认移除 Agent [cyan]{agent.name}[/cyan] ({agent_id})？"):
            console.print("[dim]已取消[/dim]")
            return

    if coordinator.remove_agent(agent_id):
        console.print(f"[green]✓ Agent 已移除: {agent_id}[/green]")
    else:
        console.print("[red]❗ 移除失败[/red]")
        raise typer.Exit(1)


@app.command("clear")
def multiagent_clear(
    force: bool = typer.Option(False, "--force", "-f", help="强制清空"),
) -> None:
    """
    清空所有子 Agent

    示例:
        omc multiagent clear -f
    """
    coordinator = get_coordinator()
    count = len(coordinator.agents)

    if count == 0:
        console.print("[dim]暂无子 Agent[/dim]")
        return

    if not force:
        from rich.prompt import Confirm

        if not Confirm.ask(f"确认清空所有 {count} 个子 Agent？"):
            console.print("[dim]已取消[/dim]")
            return

    coordinator.clear_agents()
    console.print(f"[green]✓ 已清空 {count} 个子 Agent[/green]")
