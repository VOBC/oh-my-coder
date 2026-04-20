"""
记忆迁移 CLI - 从其他工具导入配置

命令：
- omc migrate claude <path>     # 从 Claude Code 导入 CLAUDE.md 配置
- omc migrate gemini <path>     # 从 Gemini CLI 导入配置
- omc migrate list              # 列出支持的迁移来源
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="记忆迁移 - 从其他工具导入配置")
console = Console()


# 支持的迁移来源
MIGRATION_SOURCES = {
    "claude": {
        "name": "Claude Code",
        "config_file": "CLAUDE.md",
        "description": "从 Claude Code 的项目配置导入",
        "fields": ["working_directory", "agent", "commands"],
    },
    "gemini": {
        "name": "Gemini CLI",
        "config_file": ".clinerules",
        "description": "从 Gemini CLI 的规则配置导入",
        "fields": ["rules", "model", "project"],
    },
}


@app.command("list")
def list_sources():
    """列出支持的迁移来源"""
    table = Table(title="支持的迁移来源")
    table.add_column("来源", style="cyan")
    table.add_column("配置文件", style="yellow")
    table.add_column("描述", style="white")

    for key, info in MIGRATION_SOURCES.items():
        table.add_row(
            info["name"],
            info["config_file"],
            info["description"],
        )

    console.print(table)
    console.print("\n[dim]使用 'omc migrate claude <path>' 或 'omc migrate gemini <path>' 导入配置[/dim]")


@app.command("claude")
def migrate_claude(
    path: Optional[Path] = typer.Argument(
        None,
        help="项目路径（默认当前目录）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="只显示导入内容，不实际执行",
    ),
):
    """从 Claude Code 导入配置"""
    project_path = path or Path.cwd()
    claude_md = project_path / "CLAUDE.md"

    if not claude_md.exists():
        console.print(f"[red]错误：未找到 CLAUDE.md 文件[/red]")
        console.print(f"[dim]请在项目目录: {project_path} 中创建 CLAUDE.md[/dim]")
        raise typer.Exit(1)

    console.print(f"[cyan]读取 CLAUDE.md from {project_path}...[/cyan]")

    content = claude_md.read_text(encoding="utf-8")

    if dry_run:
        console.print("[yellow]=== 导入内容预览 ===[/yellow]")
        console.print(content[:500] + "..." if len(content) > 500 else content)
        console.print(f"\n[dim]共 {len(content)} 字符[/dim]")
        return

    # 解析 CLAUDE.md 内容并转换
    config = _parse_claude_config(content)

    # 保存到 OMC 记忆目录
    memory_dir = Path.home() / ".omc" / "memory" / "imported"
    memory_dir.mkdir(parents=True, exist_ok=True)

    output_file = memory_dir / f"claude_import_{project_path.name}.md"
    output_file.write_text(
        f"# 从 Claude Code 导入\n\n"
        f"来源: {project_path}\n"
        f"导入时间: {__import__('datetime').datetime.now().isoformat()}\n\n"
        f"---\n\n"
        f"{content}",
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green] 配置已导入到: {output_file}")
    console.print(f"[dim]可使用 'omc memory view' 查看导入的记忆[/dim]")


@app.command("gemini")
def migrate_gemini(
    path: Optional[Path] = typer.Argument(
        None,
        help="项目路径（默认当前目录）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="只显示导入内容，不实际执行",
    ),
):
    """从 Gemini CLI 导入配置"""
    project_path = path or Path.cwd()

    # Gemini CLI 使用 .clinerules 或 .clinerules.json
    clinerules = project_path / ".clinerules"
    clinerules_json = project_path / ".clinerules.json"

    config_file = None
    if clinerules.exists():
        config_file = clinerules
    elif clinerules_json.exists():
        config_file = clinerules_json

    if not config_file:
        console.print(f"[red]错误：未找到 .clinerules 文件[/red]")
        console.print(f"[dim]请在项目目录: {project_path} 中创建 .clinerules[/dim]")
        raise typer.Exit(1)

    console.print(f"[cyan]读取 {config_file.name} from {project_path}...[/cyan]")

    content = config_file.read_text(encoding="utf-8")

    if dry_run:
        console.print("[yellow]=== 导入内容预览 ===[/yellow]")
        console.print(content[:500] + "..." if len(content) > 500 else content)
        console.print(f"\n[dim]共 {len(content)} 字符[/dim]")
        return

    # 保存到 OMC 记忆目录
    memory_dir = Path.home() / ".omc" / "memory" / "imported"
    memory_dir.mkdir(parents=True, exist_ok=True)

    output_file = memory_dir / f"gemini_import_{project_path.name}.md"
    output_file.write_text(
        f"# 从 Gemini CLI 导入\n\n"
        f"来源: {project_path}\n"
        f"配置文件: {config_file.name}\n"
        f"导入时间: {__import__('datetime').datetime.now().isoformat()}\n\n"
        f"---\n\n"
        f"{content}",
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green] 配置已导入到: {output_file}")
    console.print(f"[dim]可使用 'omc memory view' 查看导入的记忆[/dim]")


def _parse_claude_config(content: str) -> dict:
    """解析 CLAUDE.md 内容"""
    config = {
        "working_directory": None,
        "agent": None,
        "commands": [],
    }

    lines = content.split("\n")
    in_commands = False

    for line in lines:
        if line.startswith("## Working Directory:"):
            config["working_directory"] = line.split(":", 1)[1].strip()
        elif line.startswith("## Agent:"):
            config["agent"] = line.split(":", 1)[1].strip()
        elif "## Commands" in line:
            in_commands = True
        elif in_commands and line.strip().startswith("- "):
            config["commands"].append(line.strip()[2:])

    return config


if __name__ == "__main__":
    app()
