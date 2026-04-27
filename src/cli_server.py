"""
Server CLI - omc server 命令

omc server [--port PORT] [--host HOST] [--api-key KEY] [--no-open]
omc server stop

文档：docs/guide/server-mode.md
API: http://localhost:{port}/docs（Swagger UI）
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import socket
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel

from src.api.server_api import create_app

console = Console()

app = typer.Typer(
    name="server",
    help="启动远程 AI 编程助手 Server（HTTP REST API）",
    add_completion=False,
)

# 全局进程引用
_server_process: uvicorn.Server | None = None
_config: dict | None = None


def _find_free_port(port: int) -> int:
    """查找可用端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", port)) != 0:
            return port
    # 端口被占用，尝试 +1
    for p in range(port + 1, port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
            if s2.connect_ex(("localhost", p)) != 0:
                return p
    return port + 1


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


@app.command("start")
def start(
    port: int = typer.Option(8080, "--port", "-p", help="监听端口"),
    host: str = typer.Option(
        "0.0.0.0", "--host", help="监听地址（0.0.0.0 = 所有网卡）"
    ),
    api_key: str | None = typer.Option(
        None, "--api-key", help="API 密钥（不设置则无认证）"
    ),
    no_auth: bool = typer.Option(
        False, "--no-auth", help="禁用认证（与 --api-key 互斥）"
    ),
    no_open: bool = typer.Option(False, "--no-open", help="启动后不打开浏览器"),
    reload: bool = typer.Option(False, "--reload", help="开发模式：代码变更自动重载"),
) -> None:
    """启动 Server"""
    global _server_process, _config

    # 互斥检查
    if api_key and no_auth:
        console.print("[red]--api-key 和 --no-auth 不能同时使用[/red]")
        raise typer.Exit(1)

    # 确认端口占用
    if _is_port_in_use(port):
        free = _find_free_port(port)
        console.print(f"[yellow]⚠ 端口 {port} 已被占用[/yellow]")
        if free != port:
            console.print(f"[green]→ 自动切换到端口 {free}[/green]")
            port = free
        else:
            console.print("[red]✗ 无法找到可用端口[/red]")
            raise typer.Exit(1)

    # API Key 处理
    if no_auth:
        effective_key: str | None = None
    elif api_key:
        effective_key = api_key
    else:
        # 从环境变量或配置文件读取
        effective_key = os.getenv("OMC_SERVER_API_KEY") or _load_api_key_from_config()
        if effective_key:
            console.print("[dim]API Key: 从配置文件加载（已设置）[/dim]")
        else:
            console.print(
                "[yellow]⚠ 未设置 API Key，所有请求无需认证（生产环境建议设置）[/yellow]"
            )

    # 创建 FastAPI app
    fastapi_app, store = create_app(api_key=effective_key)
    _config = {
        "port": port,
        "host": host,
        "api_key": effective_key,
        "store": store,
    }

    # 启动参数
    api_url = f"http://localhost:{port}"
    docs_url = f"{api_url}/docs"
    redoc_url = f"{api_url}/redoc"

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🚀 Oh My Coder Server[/bold cyan]\n\n"
            f"  [green]API:[/]   {api_url}\n"
            f"  [green]Docs:[/]  {docs_url}\n"
            f"  [green]Redoc:[/]{redoc_url}\n"
            f"  [green]Host:[/]  {host}\n"
            f"  [green]Port:[/]  {port}\n"
            + (
                "  [yellow]Auth:[/]  API Key 已启用[/yellow]\n"
                if effective_key
                else "  [dim]Auth:[/]  无认证[/dim]\n"
            ),
            border_style="cyan",
        )
    )
    console.print()
    console.print("[dim]按 Ctrl+C 停止服务[/dim]")
    console.print()

    # 注册信号处理
    def stop_handler(sig: int, frame) -> None:
        console.print("\n[yellow]收到停止信号，正在关闭...[/yellow]")
        if _server_process:
            _server_process.should_exit = True

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    # 启动 uvicorn
    config = uvicorn.Config(
        fastapi_app,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True,
    )
    _server_process = uvicorn.Server(config)

    # 打开浏览器
    if not no_open:
        import threading

        threading.Timer(1.5, _open_browser, args=(docs_url,)).start()

    # 同步运行（阻塞）
    asyncio.run(_server_process.serve())


@app.command("stop")
def stop() -> None:
    """停止 Server（通过 PID 文件）"""
    pid_file = Path.home() / ".omc" / "server.pid"
    if not pid_file.exists():
        console.print("[yellow]Server 未启动（找不到 PID 文件）[/yellow]")
        raise typer.Exit(1)
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink()
        console.print(f"[green]✓ Server (PID {pid}) 已停止[/green]")
    except ProcessLookupError:
        console.print("[yellow]进程已不存在，清理 PID 文件[/yellow]")
        pid_file.unlink()
    except Exception as e:
        console.print(f"[red]✗ 停止失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status() -> None:
    """检查 Server 运行状态"""
    # 读 PID 文件
    pid_file = Path.home() / ".omc" / "server.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # 检查进程是否存在
            console.print(f"[green]✓ Server 运行中 (PID {pid})[/green]")
        except (ProcessLookupError, ValueError):
            console.print("[yellow]⚠ PID 文件存在但进程已不存在[/yellow]")
            pid_file.unlink()
            console.print("[red]✗ Server 未运行[/red]")
    else:
        console.print("[red]✗ Server 未运行[/red]")


@app.command("logs")
def logs(
    lines: int = typer.Option(50, "-n", "--lines", help="显示最近 N 行"),
) -> None:
    """查看 Server 日志"""
    log_file = Path.home() / ".omc" / "logs" / "server.log"
    if not log_file.exists():
        console.print("[yellow]暂无日志文件[/yellow]")
        raise typer.Exit(1)
    content = log_file.read_text(encoding="utf-8", errors="replace")
    log_lines = content.splitlines()
    for line in log_lines[-lines:]:
        console.print(f"[dim]{line}[/dim]")


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _load_api_key_from_config() -> str | None:
    """从 ~/.omc/.env 读取 API Key"""
    env_file = Path.home() / ".omc" / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(errors="replace").splitlines():
        if line.strip().startswith("OMC_SERVER_API_KEY"):
            _, _, key = line.partition("=")
            return key.strip()
    return None


def _open_browser(url: str) -> None:
    import webbrowser

    with contextlib.suppress(Exception):
        webbrowser.open(url)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """omc server — 启动远程 AI 编程助手 HTTP API"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
