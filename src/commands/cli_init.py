"""
Init CLI - 交互式初始化引导

命令：
- omc init  # 交互式引导新用户完成首次配置

流程：
1. 欢迎界面
2. 选择模型
3. 输入 API Key
4. 设置工作目录
5. 配置验证
6. 完成提示
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

app = typer.Typer(
    name="init",
    help="交互式初始化引导 - 帮助新用户完成首次配置",
    add_completion=False,
)

# 配置文件路径
CONFIG_DIR = Path.home() / ".config" / "oh-my-coder"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 支持的模型列表（参考 cli_model.py）
SUPPORTED_MODELS = {
    "deepseek": {
        "name": "DeepSeek",
        "tier": "low",
        "note": "高性价比，推荐",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "glm": {
        "name": "智谱 GLM",
        "tier": "low",
        "note": "GLM-4-Flash 免费使用",
        "api_key_env": "ZHIPU_API_KEY",
    },
    "wenxin": {
        "name": "文心一言",
        "tier": "medium",
        "note": "百度",
        "api_key_env": "ERNIE_API_KEY",
    },
    "tongyi": {
        "name": "通义千问",
        "tier": "medium",
        "note": "阿里",
        "api_key_env": "DASHSCOPE_API_KEY",
    },
    "minimax": {
        "name": "MiniMax",
        "tier": "medium",
        "note": "",
        "api_key_env": "MINIMAX_API_KEY",
    },
    "kimi": {
        "name": "Kimi",
        "tier": "medium",
        "note": "月之暗面",
        "api_key_env": "KIMI_API_KEY",
    },
    "hunyuan": {
        "name": "腾讯混元",
        "tier": "medium",
        "note": "腾讯",
        "api_key_env": "HUNYUAN_API_KEY",
    },
    "doubao": {
        "name": "字节豆包",
        "tier": "medium",
        "note": "字节跳动",
        "api_key_env": "DOUBAO_API_KEY",
    },
    "tiangong": {
        "name": "天工 AI",
        "tier": "medium",
        "note": "",
        "api_key_env": "TIANGONG_API_KEY",
    },
    "spark": {
        "name": "讯飞星火",
        "tier": "medium",
        "note": "",
        "api_key_env": "SPARK_API_KEY",
    },
    "baichuan": {
        "name": "百川智能",
        "tier": "medium",
        "note": "",
        "api_key_env": "BAICHUAN_API_KEY",
    },
    "mimo": {
        "name": "小米 MiMo",
        "tier": "medium",
        "note": "小米",
        "api_key_env": "MIMO_API_KEY",
    },
}

# 版本号（从 cli.py 同步）
__version__ = "0.2.0"


# =============================================================================
# 工具函数
# =============================================================================


def _ensure_config_dir() -> None:
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict) -> None:
    """保存配置文件"""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _mask_api_key(key: str) -> str:
    """脱敏显示 API Key"""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def _tier_style(tier: str) -> str:
    """根据 tier 返回颜色"""
    return {"free": "green", "low": "cyan", "medium": "yellow", "high": "red"}.get(
        tier, "white"
    )


# =============================================================================
# 主命令
# =============================================================================


@app.callback(invoke_without_command=True)
def init_wizard(
    ctx: typer.Context,
) -> None:
    """
    交互式初始化引导 - 帮助新用户完成首次配置

    流程：
    1. 欢迎界面
    2. 选择默认模型
    3. 输入 API Key
    4. 设置工作目录
    5. 确认配置
    6. 完成
    """
    if ctx.invoked_subcommand is not None:
        return

    # ============================================================
    # 步骤 1: 欢迎界面
    # ============================================================
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]🎉 欢迎使用 Oh My Coder![/bold cyan]\n\n"
            f"[dim]版本: v{__version__}[/dim]\n"
            f"[dim]多智能体 AI 编程助手[/dim]\n\n"
            f"[yellow]让我们开始配置您的开发环境吧！[/yellow]",
            title="🚀 初始化向导",
            border_style="cyan",
        )
    )
    console.print()

    # ============================================================
    # 步骤 2: 选择模型
    # ============================================================
    console.print("[bold]📋 步骤 1/4: 选择默认模型[/bold]")
    console.print(
        "[dim]请选择您要使用的 AI 模型作为默认模型[/dim]"
    )
    console.print()

    # 显示模型列表
    table = Table(title="可用模型", show_header=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("模型 ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("层级", style="yellow")
    table.add_column("推荐", style="magenta")
    table.add_column("备注", style="dim")

    # 按推荐程度排序：free > low > medium
    tier_order = {"free": 0, "low": 1, "medium": 2, "high": 3}
    sorted_models = sorted(
        SUPPORTED_MODELS.items(),
        key=lambda x: tier_order.get(x[1]["tier"], 99),
    )

    for i, (model_id, info) in enumerate(sorted_models, 1):
        tier = info["tier"]
        tier_color = _tier_style(tier)
        recommend = "⭐ 推荐" if tier in ("free", "low") else ""
        table.add_row(
            str(i),
            model_id,
            info["name"],
            f"[{tier_color}]{tier}[/{tier_color}]",
            recommend,
            info.get("note", ""),
        )

    console.print(table)
    console.print()

    # 用户选择模型
    model_choices = [str(i) for i in range(1, len(sorted_models) + 1)]
    model_id_choices = [m[0] for m in sorted_models]

    while True:
        choice = Prompt.ask(
            "[bold]请输入序号选择模型[/bold]",
            default="1",
        )
        if choice in model_choices:
            idx = int(choice) - 1
            selected_model_id = model_id_choices[idx]
            selected_model_info = sorted_models[idx][1]
            break
        else:
            console.print(f"[red]无效选择: {choice}，请输入 1-{len(sorted_models)}[/red]")

    console.print()
    console.print(
        f"[green]✓ 已选择: {selected_model_info['name']} ({selected_model_id})[/green]"
    )
    console.print()

    # ============================================================
    # 步骤 3: 输入 API Key
    # ============================================================
    console.print("[bold]🔑 步骤 2/4: 配置 API Key[/bold]")

    # 检查环境变量中是否已有 API Key
    api_key_env = selected_model_info["api_key_env"]
    existing_key = os.getenv(api_key_env)

    if existing_key:
        console.print(
            f"[dim]检测到环境变量 {api_key_env} 已设置[/dim]"
        )
        use_existing = Confirm.ask(
            "是否使用现有的 API Key？",
            default=True,
        )
        if use_existing:
            api_key = existing_key
            console.print(f"[green]✓ 使用现有 API Key: {_mask_api_key(api_key)}[/green]")
        else:
            api_key = Prompt.ask(
                f"请输入新的 {selected_model_info['name']} API Key",
                password=True,
            )
    else:
        console.print(
            f"[dim]请输入 {selected_model_info['name']} 的 API Key[/dim]"
        )
        console.print(
            "[dim]提示: API Key 不会显示在屏幕上[/dim]"
        )
        api_key = Prompt.ask(
            "API Key",
            password=True,
        )

    if not api_key:
        console.print("[yellow]⚠ 未输入 API Key，配置将保存但不包含密钥[/yellow]")
        api_key = ""

    console.print()

    # ============================================================
    # 步骤 4: 设置工作目录
    # ============================================================
    console.print("[bold]📁 步骤 3/4: 设置工作目录[/bold]")
    console.print(
        "[dim]工作目录是 Oh My Coder 默认的项目路径[/dim]"
    )

    current_dir = str(Path.cwd())
    work_dir = Prompt.ask(
        "请输入工作目录路径",
        default=current_dir,
    )

    # 验证路径
    work_path = Path(work_dir).expanduser().resolve()
    if not work_path.exists():
        create_dir = Confirm.ask(
            f"目录 {work_path} 不存在，是否创建？",
            default=True,
        )
        if create_dir:
            try:
                work_path.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]✓ 已创建目录: {work_path}[/green]")
            except Exception as e:
                console.print(f"[red]✗ 创建目录失败: {e}[/red]")
                work_path = Path.cwd()
                console.print(f"[yellow]使用当前目录: {work_path}[/yellow]")
    else:
        console.print(f"[green]✓ 工作目录: {work_path}[/green]")

    console.print()

    # ============================================================
    # 步骤 5: 配置验证
    # ============================================================
    console.print("[bold]✅ 步骤 4/4: 确认配置[/bold]")
    console.print()

    # 汇总显示
    summary_table = Table(title="配置汇总", show_header=False)
    summary_table.add_column("项目", style="cyan")
    summary_table.add_column("值", style="green")

    summary_table.add_row("默认模型", f"{selected_model_info['name']} ({selected_model_id})")
    summary_table.add_row("API Key", _mask_api_key(api_key) if api_key else "[yellow]未设置[/yellow]")
    summary_table.add_row("工作目录", str(work_path))
    summary_table.add_row("配置文件", str(CONFIG_FILE))

    console.print(summary_table)
    console.print()

    # 确认
    confirm = Confirm.ask(
        "[bold]确认保存以上配置？[/bold]",
        default=True,
    )

    if not confirm:
        console.print("[yellow]❌ 配置已取消[/yellow]")
        raise typer.Exit(0)

    # ============================================================
    # 保存配置
    # ============================================================
    config = _load_config()
    config["default_model"] = selected_model_id
    config["work_dir"] = str(work_path)

    # 保存 API Key 到配置（如果用户输入了新的）
    if api_key and api_key != existing_key:
        api_keys = config.get("api_keys", {})
        api_keys[selected_model_id] = api_key
        config["api_keys"] = api_keys

    _save_config(config)

    # 同时设置环境变量（当前会话生效）
    if api_key:
        os.environ[api_key_env] = api_key

    # ============================================================
    # 步骤 6: 完成提示
    # ============================================================
    console.print()
    console.print(
        Panel.fit(
            "[bold green]✅ 配置完成！[/bold green]\n\n"
            f"[dim]配置已保存到: {CONFIG_FILE}[/dim]\n\n"
            "[bold]🚀 下一步:[/bold]\n"
            "  [cyan]omc agent list[/cyan]     查看可用 Agent\n"
            "  [cyan]omc model list[/cyan]      查看所有模型\n"
            "  [cyan]omc run \"<task>\"[/cyan]   执行任务\n"
            "  [cyan]omc --help[/cyan]          查看所有命令\n\n"
            "[dim]提示: 使用 [cyan]omc model switch <name>[/cyan] 可随时切换模型[/dim]",
            title="🎉 初始化完成",
            border_style="green",
        )
    )
    console.print()


@app.command("reset")
def reset_config() -> None:
    """重置配置（删除配置文件）"""
    if not CONFIG_FILE.exists():
        console.print("[yellow]配置文件不存在，无需重置[/yellow]")
        return

    confirm = Confirm.ask(
        f"[bold red]确定要删除配置文件 {CONFIG_FILE}？[/bold red]",
        default=False,
    )

    if confirm:
        CONFIG_FILE.unlink()
        console.print(f"[green]✓ 已删除配置文件: {CONFIG_FILE}[/green]")
        console.print("[dim]运行 [cyan]omc init[/cyan] 重新配置[/dim]")
    else:
        console.print("[dim]已取消[/dim]")


@app.command("show")
def show_config() -> None:
    """显示当前配置"""
    if not CONFIG_FILE.exists():
        console.print("[yellow]配置文件不存在，请先运行 [cyan]omc init[/cyan][/yellow]")
        raise typer.Exit(1)

    config = _load_config()
    if not config:
        console.print("[yellow]配置文件为空，请先运行 [cyan]omc init[/cyan][/yellow]")
        raise typer.Exit(1)

    console.print()
    console.print(f"[bold cyan]配置文件: {CONFIG_FILE}[/bold cyan]")
    console.print()

    table = Table(show_header=False)
    table.add_column("项目", style="cyan")
    table.add_column("值", style="green")

    # 显示主要配置项
    if "default_model" in config:
        model_id = config["default_model"]
        model_info = SUPPORTED_MODELS.get(model_id, {})
        model_name = model_info.get("name", model_id)
        table.add_row("默认模型", f"{model_name} ({model_id})")

    if "work_dir" in config:
        table.add_row("工作目录", config["work_dir"])

    # API Keys（脱敏显示）
    if "api_keys" in config:
        for model_id, key in config["api_keys"].items():
            table.add_row(f"{model_id} API Key", _mask_api_key(key))

    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
