"""
Search CLI - omc search 命令

omc search <query> [--language LANG] [--repo REPO] [--limit N]
                  [--json|--table|--code] [--status] [--setup]

omc search setup   # 配置 Sourcegraph API Key
omc search status  # 检查 API/CLI 可用性
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from src.tools.sourcegraph import (
    SearchResult,
    check_status,
    install_src_cli,
    search,
    setup_api_key,
)

console = Console()

app = typer.Typer(
    name="search",
    help="代码搜索 - 通过 Sourcegraph 搜索公开代码库",
    add_completion=False,
)


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="搜索查询，支持 Sourcegraph 搜索语法"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="语言过滤，如 rust/python/go"
    ),
    repo: str | None = typer.Option(
        None, "--repo", "-r", help="仓库过滤，支持 glob 模式"
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="返回结果数量（1-100）"),
    output: str = typer.Option(
        "table",
        "--output",
        "-o",
        help="输出格式: table（表格）/ code（代码片段）/ json",
    ),
    json_output: bool = typer.Option(False, "--json", help="JSON 输出"),
    code_output: bool = typer.Option(False, "--code", help="AI 友好代码格式输出"),
    after: str | None = typer.Option(
        None, "--after", help="时间过滤，之后（如 2024-01-01）"
    ),
    before: str | None = typer.Option(None, "--before", help="时间过滤，之前"),
) -> None:
    """搜索 GitHub/GitLab 等公开代码库"""
    result: SearchResult = search(
        query=query,
        language=language,
        repo=repo,
        limit=limit,
        after=after,
        before=before,
    )

    # 输出
    if json_output or output == "json":
        console.print(result.format_json())
    elif code_output or output == "code":
        console.print(result.format_code(limit=min(limit, 10)))
    else:
        console.print()
        if result.source == "none":
            console.print(
                Panel.fit(
                    "[bold red]⚠ Sourcegraph 未配置[/bold red]\n\n"
                    "配置方式：\n"
                    "  [cyan]omc search setup[/cyan]  - 配置 API Key\n"
                    "  [cyan]omc search install[/cyan] - 安装 src CLI",
                    border_style="red",
                )
            )
            for w in result.warnings:
                console.print(f"  [dim]- {w}[/dim]")
        else:
            console.print(result.format_table(limit=limit))
            console.print()
            console.print(
                f"[dim]后端: {result.source}  "
                f"查询: {query}  "
                f"语言: {language or '全部'}  "
                f"仓库: {repo or '全部'}[/dim]"
            )


@app.command("setup")
def setup_cmd(
    api_key: str | None = typer.Argument(
        None, help="Sourcegraph API Key（省略则提示输入）"
    ),
    install_cli: bool = typer.Option(False, "--cli", help="同时安装 src CLI"),
) -> None:
    """配置 Sourcegraph API Key"""
    if install_cli:
        console.print("[dim]正在安装 src CLI...[/dim]")
        ok, msg = install_src_cli()
        if ok:
            console.print(f"[green]✓ {msg}[/green]")
        else:
            console.print(f"[red]✗ {msg}[/red]")
            console.print("[dim]手动安装: https://sourcegraph.com/cli[/dim]")

    if not api_key:
        try:
            import getpass

            api_key = getpass.getpass("Sourcegraph API Key: ").strip()
        except Exception:
            console.print("[red]无法读取密码，请直接传入 API Key[/red]")
            raise typer.Exit(1)

    if not api_key:
        console.print("[red]API Key 不能为空[/red]")
        raise typer.Exit(1)

    ok, msg = setup_api_key(api_key)
    if ok:
        console.print(f"[green]✓ {msg}[/green]")
        console.print()
        console.print(
            "[dim]获取 API Key: https://sourcegraph.com/user/settings/tokens[/dim]"
        )
        console.print("[dim]免费 tier: 每月 10 万次搜索，足够日常使用[/dim]")
    else:
        console.print(f"[red]✗ {msg}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status_cmd() -> None:
    """检查 Sourcegraph 搜索状态"""
    status = check_status()

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🔍 Sourcegraph 搜索状态[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    # API 状态
    api = status["api"]
    if api["available"]:
        console.print(
            f"  [green]✓[/green] Sourcegraph API  [dim]{api['endpoint']}[/dim]"
        )
        console.print(f"      Key: {api['key_prefix']}")
    else:
        console.print(
            "  [red]✗[/red] Sourcegraph API  [dim]未配置 SOURCEGRAPH_API_KEY[/dim]"
        )
        console.print("      获取: https://sourcegraph.com/user/settings/tokens")

    # CLI 状态
    cli = status["cli"]
    if cli["available"]:
        console.print(f"  [green]✓[/green] src CLI  [dim]{cli['path']}[/dim]")
    else:
        console.print("  [red]✗[/red] src CLI  [dim]未安装[/dim]")
        console.print("      安装: [cyan]omc search install[/cyan]")

    console.print()
    rec = status["recommendation"]
    if rec == "api":
        console.print("  [green]推荐: 使用 Sourcegraph API[/green]")
    elif rec == "cli":
        console.print("  [green]推荐: 使用 src CLI[/green]")
    else:
        console.print("  [yellow]⚠ 请先配置 API Key 或安装 src CLI[/yellow]")
        console.print("  [cyan]omc search setup[/cyan]  # 配置 API Key")
        console.print("  [cyan]omc search install[/cyan]  # 安装 src CLI")


@app.command("install")
def install_cmd() -> None:
    """安装 src CLI"""
    console.print("[dim]正在安装 src CLI...[/dim]")
    ok, msg = install_src_cli()
    if ok:
        console.print(f"[green]✓ {msg}[/green]")
    else:
        console.print(f"[red]✗ {msg}[/red]")
        console.print()
        console.print("手动安装方式：")
        console.print("  macOS:  [cyan]brew install sourcegraph/tap/src[/cyan]")
        console.print(
            "  Linux:  [cyan]curl -L https://sourcegraph.com/.api/src-cli.sh | sh[/cyan]"
        )
        console.print("  Windows:[cyan]scoop install src[/cyan]")
        console.print()
        console.print("下载页: https://sourcegraph.com/cli")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """默认显示帮助"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
