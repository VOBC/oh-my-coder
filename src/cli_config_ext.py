"""
Agent 配置 CLI 命令

omc config load <file>    - 加载 YAML/JSON 配置
omc config validate <file> - 验证配置文件
omc config list           - 列出本地配置
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config.agent_config import (
    list_configs_in_dir,
    load_config_file,
    validate_config_file,
)

app = typer.Typer(
    name="agent-config",
    help="Agent 配置管理 - 加载、验证 YAML/JSON 配置文件",
    add_completion=False,
)
console = Console()


@app.command("load")
def load_config(
    file: Path = typer.Argument(..., help="配置文件路径 (.yaml/.yml/.json)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
) -> None:
    """
    加载 Agent 配置文件

    示例:
        omc config load agents/code_review.yaml
        omc config load config/agent.json -v
    """
    try:
        config = load_config_file(file)

        console.print(
            Panel.fit(
                f"[green]✓ 配置加载成功[/green]\n\n"
                f"名称: [cyan]{config.name}[/cyan]\n"
                f"描述: [dim]{config.description or '无'}[/dim]\n"
                f"模型: [cyan]{config.model}[/cyan]",
                title="📋 Agent 配置",
                border_style="green",
            )
        )

        if verbose:
            console.print("\n[bold]工具:[/bold]")
            for tool in config.tools:
                console.print(f"  - {tool}")

            console.print("\n[bold]环境配置:[/bold]")
            console.print(f"  max_tokens: {config.environment.max_tokens}")
            console.print(f"  temperature: {config.environment.temperature}")
            console.print(f"  timeout: {config.environment.timeout}s")

            console.print("\n[bold]权限规则:[/bold]")
            perm = config.permissions
            console.print(f"  allowed_patterns: {perm.get('allowed_patterns', '无')}")
            console.print(f"  denied_patterns: {perm.get('denied_patterns', '无')}")
            console.print(f"  require_approval: {perm.get('require_approval', '无')}")

    except FileNotFoundError:
        console.print(f"[red]❗ 配置文件不存在: {file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❗ 加载失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("validate")
def validate_config(
    file: Path = typer.Argument(..., help="配置文件路径"),
) -> None:
    """
    验证 Agent 配置文件合法性

    示例:
        omc config validate agents/code_review.yaml
    """
    valid, errors = validate_config_file(file)

    if valid:
        console.print(f"[green]✓ 配置文件合法: {file}[/green]")
    else:
        console.print(f"[red]✗ 配置文件有误: {file}[/red]\n")
        for error in errors:
            console.print(f"  - [red]{error}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_configs(
    dir: Path = typer.Option(
        None,
        "--dir",
        "-d",
        help="搜索目录（默认: ~/.omc/agents/）",
    ),
) -> None:
    """
    列出本地 Agent 配置文件

    示例:
        omc config list
        omc config list --dir ./agents/
    """
    if dir is None:
        dir = Path.home() / ".omc" / "agents"

    configs = list_configs_in_dir(dir)

    if not configs:
        console.print(
            f"[dim]目录下没有配置文件: {dir}\n"
            "使用 `omc config load <file>` 加载配置[/dim]"
        )
        return

    table = Table(title=f"Agent 配置列表 ({len(configs)})")
    table.add_column("文件", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("模型", style="dim")
    table.add_column("工具数", style="dim", width=8)

    for path in configs:
        try:
            config = load_config_file(path)
            table.add_row(
                Path(path).name,
                config.name,
                config.model,
                str(len(config.tools)),
            )
        except Exception:
            table.add_row(Path(path).name, "[red]解析失败[/red]", "-", "-")

    console.print(table)


@app.command("create")
def create_from_config(
    file: Path = typer.Argument(..., help="配置文件路径"),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="输出路径（默认打印到终端）",
    ),
) -> None:
    """
    从配置创建 Agent（生成配置快照）

    示例:
        omc config create agents/code_review.yaml
        omc config create agents/code_review.yaml -o .omc/my_agent.json
    """
    try:
        config = load_config_file(file)
        data = config.to_dict()

        import json

        content = json.dumps(data, ensure_ascii=False, indent=2)

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8")
            console.print(f"[green]✓ 已保存到: {output}[/green]")
        else:
            console.print(content)

    except FileNotFoundError:
        console.print(f"[red]❗ 配置文件不存在: {file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❗ 创建失败: {e}[/red]")
        raise typer.Exit(1)
