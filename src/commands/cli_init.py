"""
Init CLI - 交互式初始化引导

命令：
- omc init  # 交互式引导新用户完成首次配置
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

from src.core.monorepo import detect_monorepo, list_subprojects
from src.tools.sourcegraph import check_status

console = Console()

app = typer.Typer(
    name="init",
    help="初始化引导 - 交互式配置 oh-my-coder",
    add_completion=False,
)

# 配置文件路径（与 cli_model.py 一致）
CONFIG_DIR = Path.home() / ".config" / "oh-my-coder"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 版本号（与 cli.py 一致）
__version__ = "0.2.0"

# ── 可选模型列表 ──────────────────────────────────────────────

MODEL_CHOICES = [
    ("deepseek", "DeepSeek", "高性价比，推荐首选", "low"),
    ("glm", "智谱 GLM", "GLM-4-Flash 免费使用", "low"),
    ("tongyi", "通义千问", "阿里云出品", "medium"),
    ("wenxin", "文心一言", "百度出品", "medium"),
    ("doubao", "字节豆包", "字节跳动出品", "medium"),
    ("hunyuan", "腾讯混元", "腾讯出品", "medium"),
    ("kimi", "Kimi", "月之暗面出品", "medium"),
    ("minimax", "MiniMax", "高性价比", "medium"),
    ("spark", "讯飞星火", "科大讯飞出品", "medium"),
    ("baichuan", "百川智能", "百川出品", "medium"),
    ("tiangong", "天工 AI", "天工出品", "medium"),
    ("mimo", "小米 MiMo", "小米出品", "medium"),
]

# API Key 环境变量映射
API_KEY_ENV_MAP = {
    "deepseek": "DEEPSEEK_API_KEY",
    "glm": "ZHIPU_API_KEY",
    "tongyi": "DASHSCOPE_API_KEY",
    "wenxin": "QIANFAN_API_KEY",
    "doubao": "ARK_API_KEY",
    "hunyuan": "HUNYUAN_API_KEY",
    "kimi": "MOONSHOT_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "spark": "SPARK_API_KEY",
    "baichuan": "BAICHUAN_API_KEY",
    "tiangong": "TIANGONG_API_KEY",
    "mimo": "MIMO_API_KEY",
}


# ── 工具函数 ──────────────────────────────────────────────────


def _load_config() -> dict:
    """加载现有配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict) -> None:
    """保存配置文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _get_env_file() -> Path:
    """获取 .env 文件路径"""
    return Path.home() / ".omc" / ".env"


def _save_api_key(model_id: str, api_key: str) -> None:
    """保存 API Key 到 .env 文件"""
    env_var = API_KEY_ENV_MAP.get(model_id, f"{model_id.upper()}_API_KEY")
    env_file = _get_env_file()
    env_file.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            lines = f.readlines()

    # 更新或追加
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{env_var}="):
            lines[i] = f"{env_var}={api_key}\n"
            found = True
            break
    if not found:
        lines.append(f"{env_var}={api_key}\n")

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(lines)


# ── 主命令 ────────────────────────────────────────────────────


@app.callback(invoke_without_command=True)
def init_wizard(
    ctx: typer.Context,
    monorepo: bool = typer.Option(
        False,
        "--monorepo",
        "-m",
        help="在 Monorepo 根目录初始化，自动检测子项目",
    ),
) -> None:
    """交互式初始化引导 - 首次使用推荐运行"""
    if ctx.invoked_subcommand is not None:
        return

    # ── Step 0: Monorepo 检测 ──
    monorepo_info = None
    if monorepo:
        monorepo_info = detect_monorepo(Path.cwd())
        if monorepo_info is None:
            console.print(
                "[yellow]⚠[/yellow] 当前目录不是 Monorepo 根目录"
            )
            console.print(
                "[dim]支持的配置: pnpm-workspace.yaml, lerna.json, nx.json, turbo.json[/dim]"
            )
            if not Confirm.ask("是否继续普通初始化？", default=True):
                raise typer.Exit(0)
        else:
            console.print()
            console.print(
                Panel.fit(
                    f"[bold cyan]📦 检测到 Monorepo: {monorepo_info.type}[/bold cyan]\n"
                    f"[dim]根目录: {monorepo_info.root}[/dim]\n"
                    f"[dim]子项目数: {len(monorepo_info.packages)}[/dim]",
                    title="Monorepo 模式",
                    border_style="cyan",
                )
            )
            console.print()

    # ── Step 1: 欢迎界面 ──
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]🚀 欢迎使用 Oh My Coder v{__version__}[/bold cyan]\n\n"
            "[dim]多智能体 AI 编程助手 · 31个专业 Agent · 12种国产模型[/dim]\n"
            "[dim]不用翻墙，国内网络直接用[/dim]\n\n"
            "[bold]接下来只需 3 步即可开始使用：[/bold]",
            title="✨ 初始化向导",
            border_style="cyan",
        )
    )
    console.print()

    # ── Step 2: 选择模型 ──
    console.print("[bold yellow]📋 Step 1/3: 选择默认模型[/bold yellow]")
    console.print()

    model_table = Table(show_header=True, header_style="bold cyan", expand=True)
    model_table.add_column("#", style="dim", width=4)
    model_table.add_column("模型 ID", style="green")
    model_table.add_column("名称", style="white")
    model_table.add_column("说明")
    model_table.add_column("成本", style="dim")

    for i, (mid, name, note, tier) in enumerate(MODEL_CHOICES, 1):
        tier_label = "🟢 免费/低成本" if tier == "low" else "🟡 中等"
        model_table.add_row(str(i), mid, name, note, tier_label)

    console.print(model_table)
    console.print()

    # 加载现有配置作为默认值
    existing_config = _load_config()
    current_default = existing_config.get("default_model", "deepseek")

    model_choice = Prompt.ask(
        "选择默认模型",
        choices=[m[0] for m in MODEL_CHOICES],
        default=current_default,
    )
    console.print(f"  ✅ 已选择: [bold green]{model_choice}[/bold green]")
    console.print()

    # ── Step 3: 输入 API Key ──
    console.print("[bold yellow]🔑 Step 2/3: 配置 API Key[/bold yellow]")
    console.print()

    env_var = API_KEY_ENV_MAP.get(model_choice, f"{model_choice.upper()}_API_KEY")
    existing_key = os.getenv(env_var, "")

    if existing_key:
        console.print(f"  检测到已有 [cyan]{env_var}[/cyan]，按 Enter 跳过")
        api_key = Prompt.ask(
            f"输入 {env_var}",
            password=True,
            default="",
        )
        if api_key == "":
            api_key = existing_key
            console.print("  ✅ 保留已有 Key")
    else:
        console.print(f"  环境变量: [cyan]{env_var}[/cyan]")
        api_key = Prompt.ask(
            f"输入 {env_var}",
            password=True,
        )

    if api_key and api_key != existing_key:
        _save_api_key(model_choice, api_key)
        console.print("  ✅ API Key 已保存")
    console.print()

    # ── Step 4: 设置工作目录 ──
    console.print("[bold yellow]📁 Step 3/3: 设置工作目录[/bold yellow]")
    console.print()

    current_dir = existing_config.get("work_dir", str(Path.cwd()))
    work_dir = Prompt.ask(
        "工作目录路径",
        default=current_dir,
    )
    console.print(f"  ✅ 工作目录: [bold green]{work_dir}[/bold green]")
    console.print()

    # ── Step 4: Sourcegraph 配置（可选）──
    console.print("[bold yellow]🔍 Step 4/4: Sourcegraph 搜索增强（可选）[/bold yellow]")
    console.print()

    sg_status = check_status()
    has_api = sg_status["api"]["available"]
    has_cli = sg_status["cli"]["available"]

    # 检查环境变量中是否已有配置
    existing_sg_key = os.getenv("SOURCEGRAPH_API_KEY", "")
    existing_sg_endpoint = os.getenv("SOURCEGRAPH_ENDPOINT", "https://sourcegraph.com")

    if has_api:
        console.print("  [green]✓[/green] Sourcegraph API 已配置")
        use_sg = Confirm.ask("是否启用 Sourcegraph 搜索增强？", default=True)
    elif has_cli:
        console.print("  [green]✓[/green] src CLI 已安装")
        use_sg = Confirm.ask(
            "是否启用 Sourcegraph 搜索增强？（已有 src CLI）",
            default=True,
        )
    else:
        console.print("  Sourcegraph 可以让你的需求分析 Agent 搜索公开代码库")
        console.print("  [dim]参考: https://sourcegraph.com 获取免费 API Key[/dim]")
        use_sg = Confirm.ask(
            "是否配置 Sourcegraph？",
            default=False,
        )

    if use_sg and not has_api:
        console.print()
        # 询问 API Endpoint
        sg_endpoint = Prompt.ask(
            "Sourcegraph API Endpoint",
            default=existing_sg_endpoint,
        )
        console.print(f"  使用 Endpoint: [cyan]{sg_endpoint}[/cyan]")

        # 询问 API Key
        if existing_sg_key:
            console.print("  检测到已有 [cyan]SOURCEGRAPH_API_KEY[/cyan]，按 Enter 保留")
            sg_api_key = Prompt.ask(
                "输入 Sourcegraph API Key",
                password=True,
                default="",
            )
            if sg_api_key == "":
                sg_api_key = existing_sg_key
                console.print("  ✅ 保留已有 Key")
        else:
            console.print("  环境变量: [cyan]SOURCEGRAPH_API_KEY[/cyan]")
            sg_api_key = Prompt.ask(
                "输入 Sourcegraph API Key",
                password=True,
            )

        if sg_api_key:
            # 保存 API Key 和 Endpoint
            env_file = _get_env_file()
            env_file.parent.mkdir(parents=True, exist_ok=True)

            lines: list[str] = []
            if env_file.exists():
                with open(env_file, encoding="utf-8") as f:
                    lines = f.readlines()

            # 更新或追加 SOURCEGRAPH_API_KEY
            found_key = False
            for i, line in enumerate(lines):
                if line.strip().startswith("SOURCEGRAPH_API_KEY="):
                    lines[i] = f"SOURCEGRAPH_API_KEY={sg_api_key}\n"
                    found_key = True
                    break
            if not found_key:
                lines.append(f"SOURCEGRAPH_API_KEY={sg_api_key}\n")

            # 更新或追加 SOURCEGRAPH_ENDPOINT（如果不是默认值）
            if sg_endpoint != "https://sourcegraph.com":
                found_endpoint = False
                for i, line in enumerate(lines):
                    if line.strip().startswith("SOURCEGRAPH_ENDPOINT="):
                        lines[i] = f"SOURCEGRAPH_ENDPOINT={sg_endpoint}\n"
                        found_endpoint = True
                        break
                if not found_endpoint:
                    lines.append(f"SOURCEGRAPH_ENDPOINT={sg_endpoint}\n")

            with open(env_file, "w", encoding="utf-8") as f:
                f.writelines(lines)

            console.print("  ✅ Sourcegraph 配置已保存")

    console.print()

    # ── Step 5: Monorepo 子项目配置（可选）──
    if monorepo_info is not None:
        console.print("[bold yellow]📦 Step 4/4: Monorepo 子项目[/bold yellow]")
        console.print()

        subprojects = list_subprojects(monorepo_info)
        if subprojects:
            from rich.table import Table as RichTable
            pkg_table = RichTable(show_header=True, header_style="bold cyan")
            pkg_table.add_column("#", style="dim", width=4)
            pkg_table.add_column("项目", style="green")
            pkg_table.add_column("语言", style="yellow")
            pkg_table.add_column("框架", style="cyan")
            pkg_table.add_column("Agent", style="dim")

            for i, sp in enumerate(subprojects, 1):
                agent_status = "✓" if sp.has_agent_config else "-"
                pkg_table.add_row(
                    str(i), sp.name, sp.language, sp.framework, agent_status
                )

            console.print(pkg_table)
            console.print()
            console.print(
                f"[dim]共 {len(subprojects)} 个子项目，"
                f"{sum(1 for sp in subprojects if sp.has_agent_config)} 个已配置 Agent[/dim]"
            )
            console.print()
        else:
            console.print("[dim]未检测到子项目[/dim]")
            console.print()

    # ── Step 6: 配置验证 ──
    console.print("[bold yellow]📋 确认配置[/bold yellow]")
    console.print()

    summary_table = Table.grid(padding=(0, 2))
    summary_table.add_column(style="bold", justify="right")
    summary_table.add_column()
    summary_table.add_row("默认模型:", f"[green]{model_choice}[/green]")
    summary_table.add_row(
        "API Key:", "[dim]已配置 ✓[/dim]" if api_key else "[yellow]未配置[/yellow]"
    )
    summary_table.add_row("工作目录:", work_dir)
    sg_configured = has_api or has_cli or (use_sg if 'use_sg' in locals() else False)
    summary_table.add_row("Sourcegraph:", "[dim]已配置 ✓[/dim]" if sg_configured else "[dim]未配置[/dim]")
    if monorepo_info is not None:
        summary_table.add_row("Monorepo:", f"[cyan]{monorepo_info.type}[/cyan]")
        summary_table.add_row("子项目:", str(len(monorepo_info.packages)))
    summary_table.add_row("配置文件:", str(CONFIG_FILE))

    console.print(Panel(summary_table, title="配置摘要", border_style="cyan"))
    console.print()

    if not Confirm.ask("确认以上配置？", default=True):
        console.print("[yellow]已取消，可重新运行 omc init[/yellow]")
        raise typer.Exit(0)

    # ── Step 7: 保存并完成 ──
    config = existing_config.copy()
    config["default_model"] = model_choice
    config["work_dir"] = work_dir
    config["initialized"] = True
    if monorepo_info is not None:
        config["monorepo"] = {
            "type": monorepo_info.type,
            "root": str(monorepo_info.root),
            "packages": [str(p) for p in monorepo_info.packages],
        }
    _save_config(config)

    console.print()
    success_msg = (
        "[bold green]✅ 配置完成！[/bold green]\n\n"
        "[bold]接下来试试：[/bold]\n"
        "  [cyan]omc agents list[/cyan]       查看可用 Agent\n"
        "  [cyan]omc model list[/cyan]        查看所有模型\n"
        "  [cyan]omc models --recommend[/cyan] 获取模型推荐\n"
        "  [cyan]omc run <任务>[/cyan]        开始编程\n"
    )
    if monorepo_info is not None:
        success_msg += (
            "  [cyan]omc agents list --monorepo[/cyan]  查看 Monorepo 子项目\n"
        )
    success_msg += (
        "\n[dim]配置文件: ~/.config/oh-my-coder/config.json[/dim]\n"
        "[dim]API Key: ~/.omc/.env[/dim]"
    )

    console.print(
        Panel.fit(
            success_msg,
            title="🎉 初始化成功",
            border_style="green",
        )
    )
