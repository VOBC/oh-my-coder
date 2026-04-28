"""
Models CLI - 模型配置分享与浏览

命令：
- omc models share      # 分享模型配置到社区
- omc models browse     # 浏览社区分享的模型配置
- omc models list       # 列出本地分享的配置
- omc models remove     # 删除已分享的配置
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()

app = typer.Typer(
    name="models",
    help="模型配置分享 - 分享/浏览社区模型配置",
    add_completion=False,
)

# 配置存储路径
SHARED_MODELS_DIR = Path.home() / ".oh-my-coder" / "shared_models"


def _ensure_shared_dir() -> None:
    """确保分享目录存在"""
    SHARED_MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _list_shared_configs() -> list[dict]:
    """列出所有已分享的配置"""
    configs = []
    if not SHARED_MODELS_DIR.exists():
        return configs

    for json_file in sorted(SHARED_MODELS_DIR.glob("*.json")):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                data["_file"] = json_file.name
                configs.append(data)
        except Exception:
            continue

    return configs


def _get_author_name() -> str:
    """获取作者名称（优先环境变量，其次 git config）"""
    # 1. 环境变量
    author = os.getenv("OMC_AUTHOR_NAME")
    if author:
        return author

    # 2. git config
    try:
        import subprocess

        result = subprocess.run(
            ["git", "config", "--get", "user.name"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # 3. 默认
    return "Anonymous"


@app.command("share")
def share_model(
    name: str = typer.Option(None, "--name", "-n", help="模型配置名称"),
    provider: str = typer.Option(
        None, "--provider", "-p", help="提供商（如 deepseek, glm）"
    ),
    base_url: str = typer.Option(None, "--url", "-u", help="API Base URL"),
    model: str = typer.Option(None, "--model", "-m", help="模型 ID"),
    description: str = typer.Option(None, "--desc", "-d", help="使用说明/描述"),
    author: str = typer.Option(None, "--author", "-a", help="作者名称"),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", help="交互式输入"
    ),
) -> None:
    """
    分享模型配置到社区目录

    示例:
        omc models share
        omc models share --name "My DeepSeek" --provider deepseek --url https://api.deepseek.com --model deepseek-chat
    """
    _ensure_shared_dir()

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]📤 分享模型配置[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    # 交互式输入
    if interactive and not all([name, provider, base_url, model]):
        console.print("[dim]请输入模型配置信息（Ctrl+C 取消）:[/dim]")
        console.print()

        if not name:
            name = Prompt.ask("[bold]配置名称[/]", default="My Model Config")

        if not provider:
            provider = Prompt.ask(
                "[bold]提供商[/]",
                default="deepseek",
            )

        if not model:
            model = Prompt.ask(
                "[bold]模型 ID[/]",
                default="deepseek-chat",
            )

        if not base_url:
            base_url = Prompt.ask(
                "[bold]API Base URL[/]",
                default="https://api.deepseek.com/v1",
            )

        if not description:
            description = Prompt.ask(
                "[bold]描述/使用说明[/]",
                default="",
            )

    # 验证必填字段
    if not all([name, provider, base_url, model]):
        console.print("[red]✗ 缺少必填参数: name, provider, base_url, model[/red]")
        raise typer.Exit(1)

    # 作者
    if not author:
        author = _get_author_name()

    # 构建配置
    config_id = str(uuid.uuid4())[:8]
    config = {
        "id": config_id,
        "name": name,
        "provider": provider,
        "base_url": base_url,
        "model": model,
        "description": description or "",
        "author": author,
        "created_at": datetime.now().isoformat(),
        "version": "1.0",
    }

    # 确认
    console.print()
    console.print("[dim]配置预览:[/dim]")
    console.print(f"  [cyan]名称:[/] {config['name']}")
    console.print(f"  [cyan]提供商:[/] {config['provider']}")
    console.print(f"  [cyan]模型 ID:[/] {config['model']}")
    console.print(f"  [cyan]API URL:[/] {config['base_url']}")
    console.print(f"  [cyan]作者:[/] {config['author']}")
    console.print()

    if interactive:
        if not Confirm.ask("[bold]确认分享此配置？[/]", default=True):
            console.print("[yellow]已取消[/yellow]")
            return

    # 保存
    filename = f"{config_id}-{provider}-{model.replace('/', '-')}.json"
    filepath = SHARED_MODELS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    console.print()
    console.print("[green]✓ 已分享模型配置[/green]")
    console.print(f"[dim]保存路径: {filepath}[/dim]")
    console.print()
    console.print(
        "[dim]💡 提示: 可通过 [cyan]omc models browse[/cyan] 查看社区配置[/dim]"
    )


@app.command("browse")
def browse_models(
    provider: str = typer.Option(None, "--provider", "-p", help="按提供商过滤"),
    author: str = typer.Option(None, "--author", "-a", help="按作者过滤"),
    search: str = typer.Option(None, "--search", "-s", help="搜索关键词"),
    limit: int = typer.Option(20, "--limit", "-l", help="显示数量限制"),
) -> None:
    """
    浏览社区分享的模型配置

    示例:
        omc models browse
        omc models browse --provider deepseek
        omc models browse --search "免费"
    """
    _ensure_shared_dir()
    configs = _list_shared_configs()

    if not configs:
        console.print()
        console.print("[yellow]暂无分享的模型配置[/yellow]")
        console.print()
        console.print("[dim]💡 使用 [cyan]omc models share[/cyan] 分享你的配置[/dim]")
        return

    # 过滤
    if provider:
        configs = [c for c in configs if c.get("provider") == provider]
    if author:
        configs = [c for c in configs if author.lower() in c.get("author", "").lower()]
    if search:
        q = search.lower()
        configs = [
            c
            for c in configs
            if q in c.get("name", "").lower()
            or q in c.get("description", "").lower()
            or q in c.get("model", "").lower()
        ]

    # 限制数量
    configs = configs[:limit]

    # 显示
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]📚 社区模型配置[/bold cyan] — 共 {len(configs)} 个",
            border_style="cyan",
        )
    )
    console.print()

    table = Table(show_lines=True)
    table.add_column("ID", style="dim", width=8)
    table.add_column("名称", style="cyan", no_wrap=False)
    table.add_column("提供商", style="blue")
    table.add_column("模型", style="green")
    table.add_column("作者", style="magenta")
    table.add_column("描述", style="dim", no_wrap=False)

    for cfg in configs:
        table.add_row(
            cfg.get("id", "-")[:8],
            cfg.get("name", "-"),
            cfg.get("provider", "-"),
            cfg.get("model", "-"),
            cfg.get("author", "-"),
            cfg.get("description", "")[:50] or "-",
        )

    console.print(table)
    console.print()
    console.print(f"[dim]配置目录: {SHARED_MODELS_DIR}[/dim]")
    console.print("[dim]💡 使用 [cyan]omc models show <id>[/cyan] 查看详情[/dim]")


@app.command("show")
def show_model(
    config_id: str = typer.Argument(..., help="配置 ID（前 8 位）"),
    export: bool = typer.Option(False, "--export", "-e", help="导出为 JSON"),
) -> None:
    """
    查看模型配置详情

    示例:
        omc models show abc12345
        omc models show abc12345 --export
    """
    configs = _list_shared_configs()

    # 查找
    target = None
    for cfg in configs:
        if cfg.get("id", "").startswith(config_id):
            target = cfg
            break

    if not target:
        console.print(f"[red]✗ 未找到配置: {config_id}[/red]")
        raise typer.Exit(1)

    if export:
        # 移除内部字段
        output = dict(target)
        output.pop("_file", None)
        console.print_json(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # 详细显示
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]{target.get('name', 'Unknown')}[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()
    console.print(f"  [dim]ID:[/]       {target.get('id', '-')}")
    console.print(f"  [dim]提供商:[/]   {target.get('provider', '-')}")
    console.print(f"  [dim]模型 ID:[/]  {target.get('model', '-')}")
    console.print(f"  [dim]API URL:[/]  {target.get('base_url', '-')}")
    console.print(f"  [dim]作者:[/]     {target.get('author', '-')}")
    console.print(f"  [dim]创建时间:[/] {target.get('created_at', '-')}")
    console.print(f"  [dim]版本:[/]     {target.get('version', '-')}")
    console.print()
    if target.get("description"):
        console.print(f"  [dim]描述:[/] {target['description']}")
        console.print()
    console.print(f"  [dim]文件:[/] {target.get('_file', '-')}")
    console.print()


@app.command("list")
def list_shared() -> None:
    """
    列出本地分享的所有配置

    示例:
        omc models list
    """
    configs = _list_shared_configs()

    if not configs:
        console.print("[yellow]暂无分享的配置[/yellow]")
        return

    console.print()
    console.print(f"[bold cyan]本地分享的配置 ({len(configs)} 个):[/]")
    console.print()

    for cfg in configs:
        console.print(
            f"  • [cyan]{cfg.get('id', '-')}[/] - {cfg.get('name', '-')} ({cfg.get('provider', '-')})"
        )

    console.print()
    console.print(f"[dim]目录: {SHARED_MODELS_DIR}[/dim]")


@app.command("remove")
def remove_model(
    config_id: str = typer.Argument(..., help="配置 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="跳过确认"),
) -> None:
    """
    删除已分享的配置

    示例:
        omc models remove abc12345
        omc models remove abc12345 --force
    """
    configs = _list_shared_configs()

    # 查找
    target = None
    for cfg in configs:
        if cfg.get("id", "").startswith(config_id):
            target = cfg
            break

    if not target:
        console.print(f"[red]✗ 未找到配置: {config_id}[/red]")
        raise typer.Exit(1)

    filepath = SHARED_MODELS_DIR / target["_file"]

    if not force:
        console.print(
            f"[yellow]即将删除:[/] {target.get('name', '-')} ({target.get('id', '-')})"
        )
        if not Confirm.ask("[bold]确认删除？[/]", default=False):
            console.print("[dim]已取消[/dim]")
            return

    filepath.unlink()
    console.print(f"[green]✓ 已删除: {target.get('name', '-')}[/green]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """默认显示帮助"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
