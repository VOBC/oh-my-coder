"""
omc memory - 分层记忆查询命令

用法:
  omc memory tier0    # 查看 Tier 0 核心记忆（< 500 token）
  omc memory tier1    # 查看 Tier 1 精选记忆（< 2000 token）
  omc memory summary  # 查看完整记忆摘要
  omc memory stats    # 查看记忆统计（条数、token 数）
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="memory",
    help="分层记忆管理 - 查看、统计 Agent 记忆",
    no_args_is_help=True,
)

console = Console()


def _get_manager(project_path: Path):
    """初始化 MemoryManager"""
    from src.memory.manager import MemoryManager

    return MemoryManager.from_project(project_path)


@app.command("tier0")
def memory_tier0(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
):
    """
    🧠 查看 Tier 0 核心记忆（< 500 token）

    用于系统 Prompt 注入的最精简记忆。
    """
    manager = _get_manager(project_path.resolve())
    tier0 = manager.get_tier0_summary()

    tokens = manager.count_tokens(tier0)

    console.print(
        Panel(
            tier0 if tier0.strip() else "[dim]（空）[/dim]",
            title=f"🧠 Tier 0 核心记忆 [{tokens} tokens]",
            border_style="cyan",
        )
    )


@app.command("tier1")
def memory_tier1(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
):
    """
    📋 查看 Tier 1 精选记忆（< 2000 token）

    项目特定知识、常用命令、重要经验。
    """
    manager = _get_manager(project_path.resolve())
    tier1 = manager.get_tier1_summary()

    tokens = manager.count_tokens(tier1)

    console.print(
        Panel(
            tier1 if tier1.strip() else "[dim]（空）[/dim]",
            title=f"📋 Tier 1 精选记忆 [{tokens} tokens]",
            border_style="green",
        )
    )


@app.command("summary")
def memory_summary(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
):
    """
    📦 查看完整记忆摘要（Tier 2 存档）

    所有项目、所有学习记录、所有偏好。
    """
    manager = _get_manager(project_path.resolve())
    archive = manager.get_tier2_archive()

    tokens = manager.count_tokens(archive)

    console.print(
        Panel(
            archive[:5000]
            + (
                "\n\n[dim]... （截断显示，共 {} tokens）[/dim]".format(tokens)
                if len(archive) > 5000
                else ""
            ),
            title=f"📦 Tier 2 完整存档 [{tokens} tokens]",
            border_style="yellow",
        )
    )


@app.command("stats")
def memory_stats(
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
):
    """
    📊 查看记忆统计

    项目数、学习记录数、各层 token 消耗。
    """
    manager = _get_manager(project_path.resolve())
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

    console.print(table)
