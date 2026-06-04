"""
Profile CLI - omc profile 命令

管理子 Agent 的隔离 profile，解决上下文污染问题。
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.profile_manager import (
    PREDEFINED_PROFILES,
    ProfileManager,
    create_predefined_profile,
    get_profile_summary,
)

app = typer.Typer(help="Profile 管理 - 子 Agent 上下文隔离")
console = Console()


@app.command("create")
def create_profile(
    agent_id: str = typer.Argument(..., help="Agent 唯一标识"),
    name: str = typer.Option(..., "--name", "-n", help="Agent 名称"),
    template: str = typer.Option(
        None,
        "--template",
        "-t",
        help=f"使用预定义模板: {', '.join(PREDEFINED_PROFILES.keys())}",
    ),
):
    """创建新的 Agent Profile"""
    manager = ProfileManager()

    if manager.get_profile(agent_id):
        console.print(f"[red]Profile 已存在: {agent_id}[/red]")
        raise typer.Exit(1)

    if template:
        if template not in PREDEFINED_PROFILES:
            console.print(f"[red]未知模板: {template}[/red]")
            console.print(f"可用模板: {', '.join(PREDEFINED_PROFILES.keys())}")
            raise typer.Exit(1)

        profile = create_predefined_profile(template)
        if profile:
            # 覆盖 ID 和名称
            profile.agent_id = agent_id
            profile.agent_name = name
            manager.update_profile(profile)
        else:
            profile = manager.create_profile(agent_id, name)
    else:
        profile = manager.create_profile(agent_id, name)

    console.print("[green]✅ Profile 创建成功[/green]")
    console.print(f"[dim]ID: {profile.agent_id}[/dim]")
    console.print(f"Name: {profile.agent_name}")
    if profile.skills:
        console.print(f"Skills: {', '.join(profile.skills)}")


@app.command("list")
def list_profiles():
    """列出所有 Agent Profiles"""
    manager = ProfileManager()
    profiles = manager.list_profiles()

    if not profiles:
        console.print("[dim]没有 Profile[/dim]")
        return

    table = Table(title="Agent Profiles")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("记忆数", justify="right")
    table.add_column("任务数", justify="right")
    table.add_column("技能", style="dim")

    for p in profiles:
        table.add_row(
            p.agent_id[:20] + "..." if len(p.agent_id) > 20 else p.agent_id,
            p.agent_name,
            str(len(p.memories)),
            str(len(p.task_history)),
            ", ".join(p.skills[:3]) or "-",
        )

    console.print(table)


@app.command("show")
def show_profile(agent_id: str):
    """查看 Profile 详情"""
    summary = get_profile_summary(agent_id)
    console.print(Panel(summary, title="Profile Details"))


@app.command("context")
def show_context(agent_id: str):
    """查看 Agent 的隔离上下文（用于调试）"""
    manager = ProfileManager()
    context = manager.get_context_for_agent(agent_id)

    if not context:
        console.print(f"[red]Profile 不存在: {agent_id}[/red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold]{context['agent_name']}[/bold]\n\n"
            f"[dim]最近记忆 ({len(context['memories'])}):[/dim]\n"
            + "\n".join(f"  • {m[:80]}" for m in context["memories"][-5:])
            + f"\n\n[dim]最近任务 ({len(context['recent_tasks'])}):[/dim]\n"
            + "\n".join(
                f"  • {t['task'][:60]}... [{t['status']}]"
                for t in context["recent_tasks"][-5:]
            )
            + "\n\n[dim]偏好设置:[/dim]\n"
            + "\n".join(f"  {k}: {v}" for k, v in context["preferences"].items()),
            title="Agent Context (Isolated)",
        )
    )


@app.command("add-memory")
def add_memory(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    memory: str = typer.Argument(..., help="记忆内容"),
):
    """向 Profile 添加记忆"""
    manager = ProfileManager()
    if manager.add_memory(agent_id, memory):
        console.print("[green]✅ 记忆已添加[/green]")
    else:
        console.print(f"[red]Profile 不存在: {agent_id}[/red]")
        raise typer.Exit(1)


@app.command("add-task")
def add_task(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    task: str = typer.Argument(..., help="任务描述"),
    status: str = typer.Option("completed", "--status", "-s", help="任务状态"),
):
    """记录任务执行历史"""
    manager = ProfileManager()
    if manager.add_task(agent_id, task, status):
        console.print("[green]✅ 任务已记录[/green]")
    else:
        console.print(f"[red]Profile 不存在: {agent_id}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_profile(agent_id: str):
    """删除 Profile"""
    manager = ProfileManager()
    if manager.delete_profile(agent_id):
        console.print(f"[green]✅ 已删除: {agent_id}[/green]")
    else:
        console.print(f"[red]Profile 不存在: {agent_id}[/red]")
        raise typer.Exit(1)


@app.command("templates")
def list_templates():
    """列出预定义 Profile 模板"""
    console.print("[bold]预定义 Profile 模板:[/bold]\n")

    for key, config in PREDEFINED_PROFILES.items():
        prefs = config["preferences"]
        suitable = prefs.get("suitable_for", [])
        not_suitable = prefs.get("not_suitable_for", [])

        console.print(
            Panel(
                f"[bold]{config['name']}[/bold] ({key})\n"
                f"技能: {', '.join(config['skills'])}\n"
                + (
                    "\n[green]✓ 适合:[/green]\n  " + "\n  ".join(suitable)
                    if suitable
                    else ""
                )
                + (
                    "\n[red]✗ 不适合:[/red]\n  " + "\n  ".join(not_suitable)
                    if not_suitable
                    else ""
                )
                + f"\n\n[dim]使用: omc profile create <id> -n <name> -t {key}[/dim]",
                expand=False,
            )
        )


if __name__ == "__main__":
    app()
