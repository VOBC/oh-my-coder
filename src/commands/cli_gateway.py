from __future__ import annotations

"""
Gateway CLI - 多平台网关命令

omc gateway status
omc gateway start
"""


import asyncio

import typer
from rich.console import Console
from rich.table import Table

console = Console()

app = typer.Typer(
    name="gateway",
    help="多平台消息网关",
    add_completion=False,
)


def _load_gateway():
    """懒加载 Gateway（避免未安装依赖时 import 报错）"""
    from src.gateway.gateway import Gateway

    return Gateway(orchestrator=None)


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
def start():
    """启动网关（会阻塞当前进程，按 Ctrl+C 停止）"""
    console.print("[green]启动网关...[/green]")

    try:
        from src.gateway.gateway import Gateway

        gateway = Gateway(orchestrator=None)

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

    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def stop():
    """停止网关（仅在使用后台进程时有意义）"""
    console.print("[yellow]停止网关...（当前版本需要 Ctrl+C）[/yellow]")
