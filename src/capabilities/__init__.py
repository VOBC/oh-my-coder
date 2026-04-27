from __future__ import annotations
"""
能力包 CLI 命令

提供能力包的导出、列表、应用和发布功能。
"""

from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .package import (
    CapabilityPackage as CapabilityPackage,
)
from .package import (
    CapabilityPackageManager,
    get_manager,
)

app = typer.Typer(
    name="cap",
    help="能力包管理 - 导出、导入和分享 Agent 配置",
    add_completion=False,
)
console = Console()


def _get_manager() -> CapabilityPackageManager:
    """获取能力包管理器"""
    return get_manager()


@app.command("export")
def export_capability(
    name: str = typer.Argument(..., help="能力包名称"),
    version: str = typer.Option("1.0.0", "--version", "-v", help="版本号 (semver)"),
    description: str = typer.Option(None, "--description", "-d", help="功能描述"),
    author: str = typer.Option(None, "--author", "-a", help="作者"),
    tags: str = typer.Option(None, "--tags", "-t", help="标签（逗号分隔）"),
    config_path: Path = typer.Option(
        None, "--config", "-c", help="配置文件路径（默认从当前项目读取）"
    ),
):
    """
    导出能力包

    将当前 Agent 配置打包导出为能力包，方便分享和复用。

    示例:
        omc cap export my-config --version 1.0.0 --description "我的配置"
        omc cap export code-review -t "review,python,quality"
    """
    manager = _get_manager()

    # 交互式输入缺失信息
    if description is None:
        description = Prompt.ask("功能描述", default=f"{name} 配置包")

    if author is None:
        author = Prompt.ask("作者", default="anonymous")

    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

    # 从当前项目读取配置
    agents, model_config, tools, prompts = _load_current_config(config_path)

    # 创建能力包
    try:
        package = manager.export_from_config(
            name=name,
            version=version,
            description=description,
            author=author,
            tags=tag_list,
            agents=agents,
            model_config=model_config,
            tools=tools,
            prompts=prompts,
            readme=f"# {name}\n\n{description}",
        )

        # 验证
        errors = package.validate()
        if errors:
            console.print("[red]验证失败:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            raise typer.Exit(1)

        console.print(
            Panel.fit(
                f"[green]✓ 能力包已导出[/green]\n\n"
                f"名称: [cyan]{package.name}[/cyan]\n"
                f"版本: [cyan]{package.version}[/cyan]\n"
                f"描述: [dim]{package.description}[/dim]\n"
                f"作者: [dim]{package.author}[/dim]\n"
                f"标签: [dim]{', '.join(package.tags) or '无'}[/dim]\n\n"
                f"路径: [cyan]{manager._get_package_path(name)}[/cyan]",
                title="📦 能力包",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]导出失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_capabilities(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
):
    """
    列出所有能力包

    显示本地存储的所有能力包。

    示例:
        omc cap list
        omc cap list -v
    """
    manager = _get_manager()
    packages = manager.list_packages()

    if not packages:
        console.print("[dim]暂无能力包，使用 `omc cap export` 创建[/dim]")
        return

    if verbose:
        # 详细列表
        for pkg in packages:
            console.print(
                Panel(
                    f"[bold cyan]{pkg.name}[/bold cyan] [dim]v{pkg.version}[/dim]\n"
                    f"{pkg.description}\n"
                    f"[dim]作者: {pkg.author} | "
                    f"标签: {', '.join(pkg.tags) or '无'} | "
                    f"创建: {pkg.created_at[:10]}[/dim]",
                    border_style="cyan",
                )
            )
    else:
        # 简洁表格
        table = Table(title=f"能力包列表 ({len(packages)})")
        table.add_column("名称", style="cyan")
        table.add_column("版本", style="dim", width=10)
        table.add_column("描述", style="white")
        table.add_column("标签", style="dim")
        table.add_column("创建时间", style="dim", width=12)

        for pkg in packages:
            table.add_row(
                pkg.name,
                pkg.version,
                (
                    pkg.description[:40] + "..."
                    if len(pkg.description) > 40
                    else pkg.description
                ),
                ", ".join(pkg.tags[:3]),
                pkg.created_at[:10],
            )

        console.print(table)


@app.command("apply")
def apply_capability(
    name: str = typer.Argument(..., help="能力包名称"),
    dry_run: bool = typer.Option(False, "--dry-run", help="预览应用结果，不实际修改"),
    force: bool = typer.Option(False, "--force", "-f", help="强制应用，不提示确认"),
):
    """
    应用能力包

    将能力包中的配置应用到当前项目。

    示例:
        omc cap apply my-config
        omc cap apply my-config --dry-run
    """
    manager = _get_manager()

    package = manager.get_package(name)
    if package is None:
        console.print(f"[red]能力包不存在: {name}[/red]")
        raise typer.Exit(1)

    # 显示能力包信息
    console.print(
        Panel(
            f"[bold cyan]{package.name}[/bold cyan] v{package.version}\n"
            f"{package.description}\n"
            f"[dim]作者: {package.author}[/dim]",
            title="📦 即将应用的能力包",
            border_style="cyan",
        )
    )

    # 显示配置概览
    config_summary = []
    if package.agents:
        config_summary.append(f"- Agent 配置: {len(package.agents)} 个")
    if package.model_config:
        config_summary.append(f"- 模型配置: {len(package.model_config)} 项")
    if package.tools:
        config_summary.append(f"- 工具: {len(package.tools)} 个")
    if package.prompts:
        config_summary.append(f"- Prompt 模板: {len(package.prompts)} 个")

    if config_summary:
        console.print("[bold]配置内容:[/bold]")
        for item in config_summary:
            console.print(f"  {item}")

    if dry_run:
        console.print("\n[yellow]Dry-run 模式，未实际应用[/yellow]")
        return

    # 确认
    if not force and not Confirm.ask("\n确认应用此配置？"):
        console.print("[dim]已取消[/dim]")
        return

    # 应用配置
    try:
        # 读取当前配置
        current_config = _load_config_file() or {}

        # 应用能力包
        new_config = manager.apply_package(name, current_config)

        # 保存配置
        _save_config_file(new_config)

        console.print("[green]✓ 能力包已应用[/green]")

    except Exception as e:
        console.print(f"[red]应用失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("publish")
def publish_capability(
    name: str = typer.Argument(..., help="能力包名称"),
    registry: str = typer.Option(None, "--registry", "-r", help="社区仓库地址"),
):
    """
    发布能力包到社区

    将能力包分享到社区仓库（开发中）。

    示例:
        omc cap publish my-config
    """
    console.print(
        Panel.fit(
            "[yellow]社区功能开发中[/yellow]\n\n"
            "能力包发布功能将在未来版本支持，\n"
            "目前您可以手动分享能力包文件。\n\n"
            f"[dim]能力包位置: ~/.omc/capabilities/{name}.json[/dim]",
            title="🚀 发布",
            border_style="yellow",
        )
    )


@app.command("show")
def show_capability(
    name: str = typer.Argument(..., help="能力包名称"),
):
    """
    查看能力包详情

    示例:
        omc cap show my-config
    """
    manager = _get_manager()

    package = manager.get_package(name)
    if package is None:
        console.print(f"[red]能力包不存在: {name}[/red]")
        raise typer.Exit(1)

    # 基本信息
    console.print(
        Panel(
            f"[bold cyan]{package.name}[/bold cyan] [dim]v{package.version}[/dim]\n\n"
            f"[bold]描述:[/bold] {package.description}\n"
            f"[bold]作者:[/bold] {package.author}\n"
            f"[bold]创建时间:[/bold] {package.created_at}\n"
            f"[bold]标签:[/bold] {', '.join(package.tags) or '无'}",
            title="📦 能力包详情",
            border_style="cyan",
        )
    )

    # 配置详情
    if package.readme:
        console.print("\n[bold]使用说明:[/bold]")
        console.print(package.readme)

    if package.agents:
        console.print(f"\n[bold]Agent 配置 ({len(package.agents)}):[/bold]")
        for agent_name in package.agents:
            console.print(f"  - {agent_name}")

    if package.tools:
        console.print(f"\n[bold]工具列表 ({len(package.tools)}):[/bold]")
        for tool in package.tools:
            console.print(f"  - {tool}")

    if package.examples:
        console.print(f"\n[bold]使用示例 ({len(package.examples)}):[/bold]")
        for i, example in enumerate(package.examples, 1):
            console.print(f"\n  示例 {i}:")
            for key, value in example.items():
                console.print(f"    {key}: {value}")


@app.command("delete")
def delete_capability(
    name: str = typer.Argument(..., help="能力包名称"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除，不提示确认"),
):
    """
    删除能力包

    示例:
        omc cap delete my-config
    """
    manager = _get_manager()

    package = manager.get_package(name)
    if package is None:
        console.print(f"[red]能力包不存在: {name}[/red]")
        raise typer.Exit(1)

    if not force and not Confirm.ask(f"确认删除能力包 '{name}'？"):
        console.print("[dim]已取消[/dim]")
        return

    if manager.delete_package(name):
        console.print(f"[green]✓ 能力包 '{name}' 已删除[/green]")
    else:
        console.print("[red]删除失败[/red]")
        raise typer.Exit(1)


def _load_current_config(
    config_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str], dict[str, Any]]:
    """
    加载当前项目配置

    Returns:
        (agents, model_config, tools, prompts)
    """
    # 默认配置
    agents = {}
    model_config = {}
    tools = []
    prompts = {}

    # 尝试从配置文件加载
    if config_path and config_path.exists():
        try:
            import json

            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            agents = config.get("agents", {})
            model_config = config.get("model_config", {})
            tools = config.get("tools", [])
            prompts = config.get("prompts", {})
        except Exception:
            pass

    # 如果配置为空，使用示例配置
    if not agents:
        agents = {
            "explore": {
                "enabled": True,
                "tier": "medium",
            },
            "analyst": {
                "enabled": True,
                "tier": "medium",
            },
            "planner": {
                "enabled": True,
                "tier": "high",
            },
            "executor": {
                "enabled": True,
                "tier": "high",
            },
        }

    if not model_config:
        model_config = {
            "default_model": "deepseek",
            "temperature": 0.7,
            "max_tokens": 4000,
        }

    if not tools:
        tools = [
            "file_read",
            "file_write",
            "shell_exec",
            "web_search",
        ]

    if not prompts:
        prompts = {
            "system": "You are a helpful coding assistant.",
        }

    return agents, model_config, tools, prompts


def _load_config_file() -> dict[str, Any] | None:
    """加载项目配置文件"""
    config_paths = [
        Path(".omc/config.json"),
        Path("oh-my-coder.json"),
        Path.home() / ".omc" / "config.json",
    ]

    for path in config_paths:
        if path.exists():
            try:
                import json

                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue

    return None


def _save_config_file(config: dict[str, Any]) -> None:
    """保存项目配置文件"""
    config_dir = Path(".omc")
    config_dir.mkdir(exist_ok=True)

    config_path = config_dir / "config.json"

    import json

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
