"""
MCP CLI 命令

omc mcp --start              # 启动 MCP Server（stdio 模式）
omc mcp --install            # 生成 Claude Desktop / Cursor 的 MCP 配置
omc mcp --list               # 列出可用工具
omc mcp --status             # 查看 MCP 连接状态
"""

import contextlib
import json
import sys
from pathlib import Path

import typer
from rich.console import Console

from src.mcp.resources import get_mcp_resources
from src.mcp.server import McpServer
from src.mcp.tools import get_mcp_tools

app = typer.Typer(
    name="mcp",
    help="MCP（Model Context Protocol）支持 — 作为 Server 向外部暴露 Agent 能力",
)
console = Console()


@app.command()
def start(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="工作区路径"),
) -> None:
    """启动 MCP Server（stdio 模式）"""
    console.print("[dim]启动 oh-my-coder MCP Server...[/dim]")
    console.print("[dim]按 Ctrl+C 退出[/dim]")
    server = McpServer(workspace=workspace.resolve())
    with contextlib.suppress(KeyboardInterrupt):
        server.run()


@app.command()
def install(
    client: str = typer.Option(
        "claude-desktop",
        "--client",
        "-c",
        help="客户端类型：claude-desktop（Claude Desktop）/ cursor（Cursor）/ dify（Dify）",
    ),
    project_path: Path = typer.Option(Path("."), "--project", "-p", help="项目路径"),
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认直接覆盖"),
) -> None:
    """生成 MCP 客户端配置文件"""
    config: dict = {}

    if client == "claude-desktop":
        config_path = Path.home() / ".claude-desktop" / "mcp.json"
    elif client == "cursor":
        config_path = Path.home() / ".cursor" / "mcp.json"
    elif client == "dify":
        config_path = project_path / "mcp-dify.json"
        config["mcpServers"] = {
            "oh-my-coder": {
                "command": "python3",
                "args": ["-m", "src.mcp.server", "--start"],
                "cwd": str(project_path.resolve()),
            }
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2))
        console.print(f"[green]✅ Dify MCP 配置已生成: {config_path}[/green]")
        console.print(f"  在 Dify 中添加 MCP Server，使用配置: {config_path}")
        raise typer.Exit(0)
    else:
        console.print(f"[red]❌ 不支持的客户端: {client}[/red]")
        raise typer.Exit(1)

    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 读取现有配置
    existing = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {"mcpServers": {}}

    existing.setdefault("mcpServers", {})
    proj_abs = project_path.resolve()

    # 填充 oh-my-coder 配置
    existing["mcpServers"]["oh-my-coder"] = {
        "command": sys.executable,
        "args": ["-m", "src.mcp.server", "--start"],
        "cwd": str(proj_abs),
    }

    if not yes and config_path.exists():
        console.print(f"[yellow]⚠️  配置文件已存在: {config_path}[/yellow]")
        confirm = typer.prompt("覆盖现有配置？输入 'yes' 继续", default="no")
        if confirm.lower() != "yes":
            console.print("[dim]已取消[/dim]")
            raise typer.Exit(0)

    config_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    console.print(f"[green]✅ MCP 配置已写入: {config_path}[/green]")
    console.print(f"  客户端: {client}")
    console.print(f"  工作目录: {proj_abs}")
    console.print(f"  重启 {client} 即可使用")


@app.command()
def list() -> None:
    """列出所有可用 MCP tools 和 resources"""
    tools = get_mcp_tools()
    resources = get_mcp_resources()

    from rich.table import Table

    console.print("\n[bold cyan]🛠 MCP Tools[/bold cyan]")
    table = Table()
    table.add_column("名称", style="green")
    table.add_column("描述", style="white")
    for t in tools:
        table.add_row(t["name"], t["description"][:60])
    console.print(table)

    console.print("\n[bold cyan]📄 MCP Resources[/bold cyan]")
    for r in resources:
        console.print(f"  • [green]{r['uri']}[/green] — {r['description']}")

    console.print(f"\n[dim]共 {len(tools)} tools · {len(resources)} resources[/dim]")


@app.command()
def status() -> None:
    """查看 MCP 连接状态"""
    # 检查 MCP SDK 是否可用
    try:
        import mcp

        sdk_version = getattr(mcp, "__version__", "unknown")
        console.print(f"[green]✅ MCP SDK[/green] 已安装 (v{sdk_version})")
    except Exception:
        console.print("[yellow]⚠️  MCP SDK 未安装[/yellow]")
        console.print("  本服务使用原生 JSON-RPC stdio 实现（Python 3.9 兼容）")
        console.print("  如需 SDK（Python 3.10+）：pip install mcp")

    # 检查工作区
    workspace = Path.cwd()
    omc_dir = workspace / ".omc"
    if omc_dir.exists():
        console.print(f"\n[green]✅ 工作区[/green] {workspace}")
        console.print("  .omc/ 存在，checkpoint 和 skill 功能可用")
    else:
        console.print(f"\n[yellow]⚠️  工作区[/yellow] {workspace}")
        console.print("  .omc/ 不存在，部分功能可能受限")

    console.print("\n[bold]可用命令[/bold]")
    console.print("  omc mcp --start      # 启动 Server")
    console.print("  omc mcp --install    # 生成客户端配置")
    console.print("  omc mcp --list       # 列出工具和资源")
