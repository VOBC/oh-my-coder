"""
Gateway CLI - 多平台网关命令

omc gateway start --telegram <token>
omc gateway start --discord <token>
omc gateway status
"""

from __future__ import annotations

import asyncio
import os

import typer
from rich.console import Console
from rich.table import Table

console = Console()

app = typer.Typer(
    name="gateway",
    help="多平台消息网关（Telegram / Discord）",
    add_completion=False,
)


def _load_gateway():
    """懒加载 Gateway（避免未安装依赖时 import 报错）"""
    from src.gateway.gateway import Gateway

    return Gateway

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    discord_token = os.getenv("DISCORD_BOT_TOKEN")

    return Gateway(
        orchestrator=None,
        telegram_token=telegram_token,
        discord_token=discord_token,
    )


@app.command()
def status():
    """查看网关状态"""
    try:
        gateway = _load_gateway()
        status_data = gateway.status()

        table = Table(title="Gateway Status")
        table.add_column("平台", style="cyan")
        table.add_column("类型", style="yellow")
        table.add_column("已配置", style="green")
        table.add_column("运行中", style="green")

        for platform, info in status_data["handlers"].items():
            table.add_row(
                platform,
                info["type"],
                "✅" if info["configured"] else "❌",
                "✅" if info["started"] else "❌",
            )

        console.print(table)
        console.print(
            f"\n运行平台: {', '.join(status_data['started_platforms']) or '(none)'}"
        )

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def start(
    telegram: str = typer.Option(
        None, "--telegram", help="Telegram Bot Token（也可设 env TELEGRAM_BOT_TOKEN）"
    ),
    discord: str = typer.Option(
        None, "--discord", help="Discord Bot Token（也可设 env DISCORD_BOT_TOKEN）"
    ),
):
    """启动网关（会阻塞当前进程，按 Ctrl+C 停止）"""
    telegram_token = telegram or os.getenv("TELEGRAM_BOT_TOKEN")
    discord_token = discord or os.getenv("DISCORD_BOT_TOKEN")

    if not telegram_token and not discord_token:
        console.print(
            "[yellow]⚠️ 未指定任何平台 Token。\n"
            "设置以下环境变量之一：\n"
            "  TELEGRAM_BOT_TOKEN=<token>  omc gateway start --telegram <token>\n"
            "  DISCORD_BOT_TOKEN=<token>   omc gateway start --discord <token>[/yellow]"
        )
        raise typer.Exit(code=1)

    console.print("[green]启动网关...[/green]")
    if telegram_token:
        console.print("  ✅ Telegram: 已配置")
    if discord_token:
        console.print("  ✅ Discord: 已配置")

    try:
        from src.gateway.gateway import Gateway

        gateway = Gateway(
            orchestrator=None,  # TODO: 接入真实 Orchestrator
            telegram_token=telegram_token,
            discord_token=discord_token,
        )

        async def run():
            await gateway.start_all()
            console.print("\n[green]✅ 网关已启动，按 Ctrl+C 停止[/green]")
            # 保持运行直到收到信号
            try:
                while True:
                    await asyncio.sleep(3600)
            except asyncio.CancelledError:
                pass
            finally:
                await gateway.stop_all()

        asyncio.run(run())

    except ImportError as e:
        console.print(f"[red]❌ 依赖缺失: {e}[/red]")
        console.print("安装命令：pip install python-telegram-bot discord.py")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def stop():
    """停止网关（仅在使用后台进程时有意义）"""
    console.print("[yellow]停止网关...（当前版本需要 Ctrl+C）[/yellow]")
