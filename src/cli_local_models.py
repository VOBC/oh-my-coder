"""
本地模型 CLI 命令

管理 Ollama 本地模型：检查状态、列出模型、拉取模型等。
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
app = typer.Typer(help="本地模型管理 - Ollama 支持")


@app.command("status")
def check_status():
    """
    检查 Ollama 服务状态

    示例:
        omc local status
    """
    from ..models.ollama import OllamaModel, OLLAMA_DEFAULT_URL
    import os

    base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)

    console.print(f"[cyan]检测 Ollama 服务 ({base_url})...[/cyan]")

    # 尝试使用健康检查模块（增强版）
    try:
        from ..core.ollama_health import OllamaHealthChecker

        health = OllamaHealthChecker(base_url=base_url)
        status = health.check_ollama()

        if status.running:
            console.print("[green]✓ Ollama 服务运行中[/green]")
            console.print(f"  版本: {status.version or '未知'}")
            console.print(f"  模型数: {status.model_count}")
            console.print(f"  延迟: {status.latency_ms:.0f}ms")

            # 列出本地模型（使用模型发现）
            if status.available_models:
                console.print(
                    f"\n[bold]本地可用模型 ({len(status.available_models)} 个):[/bold]"
                )
                try:
                    from ..core.local_model_discovery import discover_ollama_models

                    discovered = discover_ollama_models(base_url)
                    table = Table()
                    table.add_column("模型名称", style="cyan")
                    table.add_column("大小")
                    table.add_column("参数量")
                    table.add_column("量化")

                    for m in discovered:
                        size_str = (
                            f"{m.size_gb:.1f} GB"
                            if m.size_gb >= 1
                            else f"{m.size_mb:.0f} MB"
                        )
                        table.add_row(
                            m.model_name,
                            size_str,
                            m.parameter_size or "-",
                            m.quantization or "-",
                        )
                    console.print(table)
                except ImportError:
                    for name in status.available_models:
                        console.print(f"  • {name}")
            else:
                console.print("[yellow]暂无本地模型[/yellow]")
                console.print("\n[dim]运行以下命令拉取模型：[/dim]")
                console.print("[green]  omc local pull qwen2:7b[/green]")
        else:
            console.print("[red]✗ Ollama 服务未运行[/red]")
            console.print("\n[yellow]请先启动 Ollama：[/yellow]")
            console.print("[green]  ollama serve[/green]")
            console.print("\n或安装 Ollama：https://ollama.ai/")
        return
    except ImportError:
        pass  # 回退到基础检测

        # 回退：基础检测
        console.print("[green]✓ Ollama 服务运行中[/green]")

        # 列出本地模型（基础版）
        models = OllamaModel.list_models(base_url)
        if models:
            console.print(f"\n[bold]本地可用模型 ({len(models)} 个):[/bold]")

            table = Table()
            table.add_column("模型名称", style="cyan")
            table.add_column("大小")
            table.add_column("修改时间")

            for m in models:
                size = m.get("size", 0)
                if size > 1e9:
                    size_str = f"{size / 1e9:.1f} GB"
                else:
                    size_str = f"{size / 1e6:.0f} MB"

                table.add_row(
                    m.get("name", "unknown"),
                    size_str,
                    m.get("modified_at", "")[:10] if m.get("modified_at") else "",
                )

            console.print(table)
        else:
            console.print("[yellow]暂无本地模型[/yellow]")
            console.print("\n[dim]运行以下命令拉取模型：[/dim]")
            console.print("[green]  omc local pull qwen2:7b[/green]")
    else:
        console.print("[red]✗ Ollama 服务未运行[/red]")
        console.print("\n[yellow]请先启动 Ollama：[/yellow]")
        console.print("[green]  ollama serve[/green]")
        console.print("\n或安装 Ollama：https://ollama.ai/")


@app.command("list")
def list_models():
    """
    列出本地可用的模型

    示例:
        omc local list
    """
    from ..models.ollama import OllamaModel, OLLAMA_MODELS
    from ..models.base import ModelTier

    console.print("[bold]本地模型状态:[/bold]\n")

    # 检查已安装模型
    installed = OllamaModel.list_models()
    installed_names = {m["name"] for m in installed}

    # 显示推荐模型
    for tier in [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH]:
        console.print(f"\n[cyan]{tier.value.upper()} Tier:[/cyan]")

        table = Table()
        table.add_column("模型", style="cyan")
        table.add_column("描述")
        table.add_column("状态")

        for m in OLLAMA_MODELS.get(tier, []):
            status = (
                "[green]✓ 已安装[/green]"
                if m["name"] in installed_names
                else "[dim]未安装[/dim]"
            )
            table.add_row(m["name"], m["desc"], status)

        console.print(table)

    console.print(f"\n[dim]已安装 {len(installed)} 个本地模型[/dim]")


@app.command("pull")
def pull_model(
    model_name: str = typer.Argument(..., help="模型名称（如 qwen2:7b）"),
):
    """
    拉取模型到本地

    示例:
        omc local pull qwen2:7b
        omc local pull llama3:8b
    """
    from ..models.ollama import OllamaModel

    console.print(f"[cyan]拉取模型: {model_name}[/cyan]")
    console.print("[dim]这可能需要几分钟，取决于模型大小...[/dim]\n")

    success = OllamaModel.pull_model(model_name)

    if success:
        console.print(f"\n[green]✓ 模型 {model_name} 拉取成功[/green]")
        console.print("[dim]使用 [green]omc local status[/dim] 查看已安装模型[/dim]")
    else:
        console.print("\n[red]✗ 拉取失败[/red]")
        console.print("\n[yellow]请确保：[/yellow]")
        console.print("  1. Ollama 已安装并运行：ollama serve")
        console.print("  2. 模型名称正确：https://ollama.ai/library")


@app.command("run")
def run_ollama(
    model_name: str = typer.Argument("qwen2:7b", help="默认模型"),
    port: int = typer.Option(11434, "--port", "-p", help="端口"),
):
    """
    启动 Ollama 服务（如果未运行）

    示例:
        omc local run
        omc local run --port 11435
    """
    import subprocess

    from ..models.ollama import OllamaModel

    if OllamaModel.is_available():
        console.print("[green]✓ Ollama 已在运行[/green]")
        return

    console.print("[cyan]启动 Ollama 服务...[/cyan]")

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        console.print(f"[green]✓ Ollama 已启动 (端口 {port})[/green]")
        console.print("[dim]默认模型:[/dim] " + model_name)
    except FileNotFoundError:
        console.print("[red]✗ Ollama 未安装[/red]")
        console.print("\n[yellow]请先安装 Ollama：[/yellow]")
        console.print("[green]  https://ollama.ai/[/green]")


@app.command("info")
def model_info(
    model_name: str = typer.Argument(..., help="模型名称"),
):
    """
    显示模型详细信息

    示例:
        omc local info qwen2:7b
    """
    from ..models.ollama import OLLAMA_MODELS

    # 查找模型描述
    desc = "开源大语言模型"
    tier = "medium"

    for t, models in OLLAMA_MODELS.items():
        for m in models:
            if m["name"] == model_name:
                desc = m["desc"]
                tier = t.value
                break

    console.print(
        Panel.fit(
            f"[bold cyan]{model_name}[/bold cyan]\n\n"
            f"[dim]描述:[/dim] {desc}\n"
            f"[dim]层级:[/dim] {tier}\n\n"
            f"[dim]使用方法:[/dim]\n"
            f"  1. 拉取模型: [green]omc local pull {model_name}[/green]\n"
            f"  2. 设为默认: [green]export OLLAMA_MODEL={model_name}[/green]",
            title="模型信息",
            border_style="cyan",
        )
    )


if __name__ == "__main__":
    app()
