"""
Model CLI - 模型切换命令

omc model list          - 列出所有可用模型
omc model current       - 显示当前模型
omc model switch <name> - 切换默认模型
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

app = typer.Typer(
    name="model",
    help="模型管理 - 查看/切换默认模型",
    add_completion=False,
)

# 配置文件路径
CONFIG_DIR = Path.home() / ".config" / "oh-my-coder"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 支持的模型列表（与 src/models/__init__.py 同步）
SUPPORTED_MODELS = {
    # 低成本/免费模型
    "deepseek": {"name": "DeepSeek", "tier": "low", "note": "高性价比，推荐"},
    "glm": {"name": "智谱 GLM", "tier": "low", "note": "GLM-4-Flash 永久免费"},
    # 主流模型
    "wenxin": {"name": "文心一言", "tier": "medium", "note": "百度"},
    "tongyi": {"name": "通义千问", "tier": "medium", "note": "阿里"},
    "minimax": {"name": "MiniMax", "tier": "medium", "note": ""},
    "kimi": {"name": "Kimi", "tier": "medium", "note": "月之暗面"},
    "hunyuan": {"name": "腾讯混元", "tier": "medium", "note": "腾讯"},
    "doubao": {"name": "字节豆包", "tier": "medium", "note": "字节跳动"},
    # 其他模型
    "tiangong": {"name": "天工 AI", "tier": "medium", "note": ""},
    "spark": {"name": "讯飞星火", "tier": "medium", "note": ""},
    "baichuan": {"name": "百川智能", "tier": "medium", "note": ""},
    "mimo": {"name": "小米 MiMo", "tier": "medium", "note": "小米"},
}


def _ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict):
    """保存配置文件"""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _get_current_model() -> str:
    """获取当前默认模型"""
    # 1. 环境变量优先
    env_model = os.getenv("OMC_DEFAULT_MODEL")
    if env_model:
        return env_model

    # 2. 配置文件
    config = _load_config()
    return config.get("default_model", "deepseek")


@app.command("list")
def list_models():
    """列出所有可用模型"""
    table = Table(title="支持的模型列表")
    table.add_column("模型 ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("层级", style="yellow")
    table.add_column("备注", style="dim")
    table.add_column("当前", style="magenta")

    current = _get_current_model()

    for model_id, info in SUPPORTED_MODELS.items():
        is_current = "✓" if model_id == current else ""
        table.add_row(
            model_id,
            info["name"],
            info["tier"],
            info["note"],
            is_current,
        )

    console.print(table)
    console.print()
    console.print(f"[dim]配置文件: {CONFIG_FILE}[/dim]")
    console.print(f"[dim]当前模型: {current}[/dim]")


@app.command("current")
def show_current():
    """显示当前默认模型"""
    current = _get_current_model()
    info = SUPPORTED_MODELS.get(current, {})

    console.print()
    console.print(f"[bold cyan]当前模型:[/] [green]{current}[/]")
    if info:
        console.print(f"[bold cyan]名称:[/] {info.get('name', '-')}")
        console.print(f"[bold cyan]层级:[/] {info.get('tier', '-')}")
        console.print(f"[bold cyan]备注:[/] [dim]{info.get('note', '-')}[/dim]")
    console.print()


@app.command("switch")
def switch_model(
    model_name: str = typer.Argument(..., help="模型 ID（如 deepseek, glm）"),
):
    """切换默认模型（写入配置文件，无需重启）"""
    # 验证模型名称
    if model_name not in SUPPORTED_MODELS:
        console.print(f"[red]错误: 不支持的模型 '{model_name}'[/red]")
        console.print()
        console.print("支持的模型:")
        for model_id in SUPPORTED_MODELS:
            console.print(f"  - {model_id}")
        raise typer.Exit(1)

    # 加载现有配置
    config = _load_config()

    # 更新配置
    old_model = config.get("default_model", "未设置")
    config["default_model"] = model_name
    _save_config(config)

    # 打印确认信息
    info = SUPPORTED_MODELS[model_name]
    console.print()
    console.print("[bold green]✓ 模型切换成功[/]")
    console.print(f"  [dim]旧模型:[/] {old_model}")
    console.print(f"  [dim]新模型:[/] {info['name']} ({model_name})")
    console.print(f"  [dim]配置文件:[/] {CONFIG_FILE}")
    console.print()
    console.print("[dim]提示: 环境变量 OMC_DEFAULT_MODEL 会覆盖配置文件[/dim]")


# 别名：支持 omc model switch 和 omc modelswitch
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """默认显示帮助"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
