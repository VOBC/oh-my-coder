from __future__ import annotations

from typing_extensions import Annotated  # noqa: UP035

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"

"""
omc cost 命令 - Token 用量统计与成本分析

用法：
    omc cost suggest [TASK]         — 根据任务推荐最优模型
    omc cost report [--days N]      — 显示 token 用量汇总（今日/本周/本月/累计）
    omc cost model [--days N]       — 按模型分组显示用量
    omc cost history [--limit N]    — 显示最近调用历史
    omc cost prices                 — 查看/编辑模型价格配置
    omc cost export                 — 导出原始使用记录为 JSON

数据存储：
    ~/.config/oh-my-coder/usage.json      — 每次 API 调用的使用记录
    ~/.config/oh-my-coder/model_prices.json — 模型价格配置（可编辑）
"""

import json
import os
import shlex
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ============================================================================
# 配置路径
# ============================================================================

console = Console()

_COST_CONFIG_DIR = Path.home() / ".config" / "oh-my-coder"
_COST_USAGE_FILE = _COST_CONFIG_DIR / "usage.json"
_COST_PRICES_FILE = _COST_CONFIG_DIR / "model_prices.json"

# 默认模型价格（元 / 1k tokens）
# 来源：各模型官方定价，免费模型设为 0
_DEFAULT_PRICES: dict[str, dict[str, float]] = {
    # DeepSeek
    "deepseek-chat": {"prompt": 0.001, "completion": 0.002},
    "deepseek-coder": {"prompt": 0.001, "completion": 0.002},
    "deepseek-reasoner": {"prompt": 0.004, "completion": 0.016},
    # OpenAI
    "gpt-4o": {"prompt": 0.036, "completion": 0.108},
    "gpt-4o-mini": {"prompt": 0.003, "completion": 0.012},
    "gpt-4.1": {"prompt": 0.030, "completion": 0.090},
    "gpt-4.1-mini": {"prompt": 0.008, "completion": 0.024},
    "gpt-5": {"prompt": 0.060, "completion": 0.180},
    # Anthropic
    "claude-3-opus": {"prompt": 0.105, "completion": 0.525},
    "claude-3-sonnet": {"prompt": 0.021, "completion": 0.105},
    "claude-3-haiku": {"prompt": 0.004, "completion": 0.020},
    "claude-3.5-sonnet": {"prompt": 0.030, "completion": 0.150},
    "claude-3.7-sonnet": {"prompt": 0.030, "completion": 0.150},
    "claude-4-opus": {"prompt": 0.075, "completion": 0.375},
    "claude-4-sonnet": {"prompt": 0.015, "completion": 0.075},
    "claude-sonnet-4-5": {"prompt": 0.015, "completion": 0.075},
    # Google
    "gemini-2.0-flash": {"prompt": 0.00025, "completion": 0.00075},
    "gemini-2.5-flash": {"prompt": 0.00015, "completion": 0.0006},
    "gemini-2.5-pro": {"prompt": 0.0035, "completion": 0.014},
    # 智谱
    "glm-4": {"prompt": 0.01, "completion": 0.01},
    "glm-4-flash": {"prompt": 0.0, "completion": 0.0},
    "glm-4.5": {"prompt": 0.005, "completion": 0.005},
    # 阿里云
    "qwen-turbo": {"prompt": 0.002, "completion": 0.006},
    "qwen-plus": {"prompt": 0.008, "completion": 0.020},
    "qwen-max": {"prompt": 0.160, "completion": 0.480},
    "qwen3-235b": {"prompt": 0.0015, "completion": 0.0015},
    # Moonshot
    "moonshot-v1": {"prompt": 0.006, "completion": 0.006},
    "kimi-k2": {"prompt": 0.004, "completion": 0.016},
    # 腾讯
    "hunyuan-lite": {"prompt": 0.0, "completion": 0.0},
    "hunyuan-standard": {"prompt": 0.0045, "completion": 0.005},
    "hunyuan-pro": {"prompt": 0.03, "completion": 0.10},
    "hunyuan-turbo": {"prompt": 0.015, "completion": 0.015},
    # 字节
    "doubao-lite": {"prompt": 0.0003, "completion": 0.0006},
    "doubao-pro": {"prompt": 0.0008, "completion": 0.002},
    "doubao-1.5-pro": {"prompt": 0.0005, "completion": 0.002},
    # MiniMax
    "minimax": {"prompt": 0.005, "completion": 0.005},
    "minimax-m1": {"prompt": 0.003, "completion": 0.003},
    # 讯飞
    "spark": {"prompt": 0.006, "completion": 0.006},
    # 百川
    "baichuan": {"prompt": 0.005, "completion": 0.005},
    # 天工
    "tiangong": {"prompt": 0.005, "completion": 0.005},
    # 小米
    "mimo": {"prompt": 0.002, "completion": 0.006},
    # 本地模型
    "ollama": {"prompt": 0.0, "completion": 0.0},
    "local": {"prompt": 0.0, "completion": 0.0},
}


# ============================================================================
# 数据加载
# ============================================================================

def _cost_ensure_config_dir() -> None:
    _COST_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _cost_load_prices() -> dict[str, dict[str, float]]:
    """加载模型价格配置（用户自定义优先级更高）"""
    _cost_ensure_config_dir()
    prices = dict(_DEFAULT_PRICES)
    if _COST_PRICES_FILE.exists():
        try:
            with open(_COST_PRICES_FILE, encoding="utf-8") as f:
                custom = json.load(f)
                prices.update(custom)
        except Exception:
            pass
    return prices


def _cost_save_prices(prices: dict[str, dict[str, float]]) -> None:
    _cost_ensure_config_dir()
    with open(_COST_PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)


def _cost_load_usage_data() -> list[dict[str, Any]]:
    """加载使用记录"""
    if _COST_USAGE_FILE.exists():
        try:
            with open(_COST_USAGE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _cost_record_usage(model: str, prompt_tokens: int, completion_tokens: int) -> None:
    """记录一次 API 调用（由 Router/Orchestrator 调用）"""
    _cost_ensure_config_dir()
    records = _cost_load_usage_data()
    records.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    })
    # 只保留最近 5000 条
    if len(records) > 5000:
        records = records[-5000:]
    with open(_COST_USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def _cost_calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """计算单次调用成本（元）"""
    prices = _cost_load_prices()
    model_key = model.lower()

    # 精确匹配
    if model_key in prices:
        p = prices[model_key]
        return (prompt_tokens / 1000) * p["prompt"] + (completion_tokens / 1000) * p["completion"]

    # 模糊匹配（前缀）
    for key, p in prices.items():
        if key in model_key or model_key.startswith(key):
            return (prompt_tokens / 1000) * p["prompt"] + (completion_tokens / 1000) * p["completion"]

    # 兜底：未知模型按 0.01/1k 估算
    return (prompt_tokens + completion_tokens) / 1000 * 0.01


def _cost_format_cost(cost: float) -> str:
    if cost == 0:
        return "[green]Free[/green]"
    elif cost < 0.01:
        return "< 0.01"
    else:
        return f"{cost:.4f}"


def _cost_format_datetime(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%m-%d %H:%M")
    except Exception:
        return iso_str[:16]


# ============================================================================
# 命令实现
# ============================================================================

app = typer.Typer(
    name="cost",
    help="Token 用量统计与成本分析",
    no_args_is_help=True,
)


@app.command("suggest")
def suggest(
    task: str = typer.Argument("", help="Task description (empty = list models only)"),
    files: int = typer.Option(0, "--files", "-f", help="Number of files involved"),
    list_models: bool = typer.Option(False, "--list", "-l", help="List all available models"),
    prefer_local: bool = typer.Option(True, "--prefer-local/--no-local", help="Prefer local models"),
) -> None:
    """
    Recommend optimal model based on task complexity
    """
    from src.agents.cost_optimizer import CostOptimizer

    # Extract real values from typer OptionInfo (for direct test calls)
    _files = files.default if hasattr(files, 'default') else files
    _list_models = list_models.default if hasattr(list_models, 'default') else list_models
    _prefer_local = prefer_local.default if hasattr(prefer_local, 'default') else prefer_local

    optimizer = CostOptimizer(prefer_local=_prefer_local)

    if _list_models:
        models = optimizer.get_all_models()
        by_provider: dict[str, list] = {}
        for m in models:
            by_provider.setdefault(m["provider"], []).append(m)
        for provider, ml in sorted(by_provider.items()):
            console.print(f"\n[bold]{provider.upper()}[/bold]")
            for m in ml:
                bar = "💰" * m["cost"]
                console.print(f"  {m['model']:30s} {bar}")
        return

    if not task:
        console.print("[yellow]Please enter a task description, e.g.:[/yellow]")
        console.print("  omc cost suggest 'fix login bug'")
        console.print("  omc cost suggest 'design system architecture' --files 20")
        raise typer.Exit(1)

    recommendation = optimizer.recommend(task, file_count=_files if _files > 0 else None)

    color_map = {"low": "green", "medium": "yellow", "high": "red"}
    complexity_color = color_map.get(recommendation.complexity.value, "white")
    cost_bars = "💰" * int(recommendation.estimated_cost)

    panel = Panel(
        f"[bold]Recommended Model[/bold]: [cyan]{recommendation.model}[/cyan]\n"
        f"[bold]Provider[/bold]: {recommendation.provider}\n"
        f"[bold]Complexity[/bold]: [{complexity_color}]{recommendation.complexity.value.upper()}[/{complexity_color}]\n"
        f"[bold]Est. Cost[/bold]: {cost_bars}\n\n"
        f"[bold]Reason[/bold]:\n{recommendation.reason}",
        title="🎯 Model Recommendation",
        border_style="cyan",
    )
    console.print(panel)

    if recommendation.alternatives:
        console.print("\n[dim]Alternatives:[/dim]")
        for alt in recommendation.alternatives:
            console.print(f"  • [cyan]{alt['model']}[/cyan]: {alt['reason']}")


@app.command("report")
def report(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to report"),
) -> None:
    """
    Show token usage summary (month/week/today)
    """
    usage_data = _cost_load_usage_data()
    prices = _cost_load_prices()

    if not usage_data:
        console.print(
            Panel(
                "[yellow]No usage records found[/yellow]\n\n"
                "运行任务后，用量会自动记录到：\n"
                f"  {_COST_USAGE_FILE}",
                title="📊 Cost Report",
                border_style="yellow",
            )
        )
        return

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    def _stats_in_range(start: Optional[datetime] = None) -> dict:
        result = {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0}
        for r in usage_data:
            try:
                ts = datetime.fromisoformat(r.get("timestamp", ""))
            except Exception:
                continue
            if start and ts < start:
                continue
            p = r.get("prompt_tokens", 0)
            c = r.get("completion_tokens", 0)
            result["calls"] += 1
            result["prompt"] += p
            result["completion"] += c
            result["cost"] += _cost_calculate_cost(r.get("model", ""), p, c)
        return result

    today_stats = _stats_in_range(today_start)
    week_stats = _stats_in_range(week_start)
    month_stats = _stats_in_range(month_start)
    total_stats = _stats_in_range()

    table = Table(title="📊 Token 用量汇总", show_header=True, header_style="bold cyan")
    table.add_column("Period", style="green")
    table.add_column("调用次数", justify="right")
    table.add_column("Prompt tokens", justify="right")
    table.add_column("Completion tokens", justify="right")
    table.add_column("总 tokens", justify="right")
    table.add_column("估算成本 (¥)", justify="right")

    for label, s in [
        ("Today", today_stats),
        ("This Week", week_stats),
        ("This Month", month_stats),
        ("Total", total_stats),
    ]:
        table.add_row(
            label,
            str(s["calls"]),
            f"{s['prompt']:,}",
            f"{s['completion']:,}",
            f"{s['prompt'] + s['completion']:,}",
            _cost_format_cost(s["cost"]),
        )

    console.print(table)
    console.print(f"\n[dim]数据来源: {_COST_USAGE_FILE}[/dim]")
    console.print(f"[dim]价格配置: {len(prices)} 个模型[/dim]")


@app.command("model")
def model_breakdown(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to report"),
) -> None:
    """
    Show usage and cost grouped by model
    """
    usage_data = _cost_load_usage_data()

    if not usage_data:
        console.print("[yellow]No usage records found[/yellow]")
        return

    cutoff = datetime.now() - timedelta(days=days)

    by_model: dict[str, dict] = {}
    for r in usage_data:
        try:
            ts = datetime.fromisoformat(r.get("timestamp", ""))
        except Exception:
            continue
        if ts < cutoff:
            continue
        model = r.get("model", "unknown")
        p = r.get("prompt_tokens", 0)
        c = r.get("completion_tokens", 0)
        if model not in by_model:
            by_model[model] = {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0}
        by_model[model]["calls"] += 1
        by_model[model]["prompt"] += p
        by_model[model]["completion"] += c
        by_model[model]["cost"] += _cost_calculate_cost(model, p, c)

    sorted_models = sorted(by_model.items(), key=lambda x: x[1]["cost"], reverse=True)

    table = Table(title=f"📈 模型用量（最近 {days} 天）", show_header=True, header_style="bold cyan")
    table.add_column("模型", style="green")
    table.add_column("调用", justify="right")
    table.add_column("Prompt", justify="right")
    table.add_column("Completion", justify="right")
    table.add_column("总计", justify="right")
    table.add_column("成本 (¥)", justify="right")

    total_cost = 0.0
    for model, s in sorted_models:
        total_cost += s["cost"]
        table.add_row(
            model,
            str(s["calls"]),
            f"{s['prompt']:,}",
            f"{s['completion']:,}",
            f"{s['prompt'] + s['completion']:,}",
            _cost_format_cost(s["cost"]),
        )

    table.add_row(
        "[bold]合计[/bold]",
        "",
        "",
        "",
        "",
        f"[bold]{_cost_format_cost(total_cost)}[/bold]",
    )
    console.print(table)


@app.command("history")
def history(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of records to show")] = 20,
    model: Annotated[str, typer.Option("--model", "-m", help="Filter by model")] = "",
) -> None:
    """
    显示最近 API 调用历史
    """
    usage_data = _cost_load_usage_data()

    if not usage_data:
        console.print("[yellow]No usage records found[/yellow]")
        return

    filtered = usage_data
    if model:
        filtered = [r for r in filtered if model.lower() in r.get("model", "").lower()]

    sorted_records = sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

    table = Table(title=f"📜 最近 {len(sorted_records)} 次调用", show_header=True, header_style="bold cyan")
    table.add_column("时间", style="dim", width=14)
    table.add_column("模型", style="green", width=25)
    table.add_column("Prompt", justify="right", width=10)
    table.add_column("Completion", justify="right", width=12)
    table.add_column("总计", justify="right", width=10)
    table.add_column("成本 (¥)", justify="right", width=10)

    for r in sorted_records:
        p = r.get("prompt_tokens", 0)
        c = r.get("completion_tokens", 0)
        cost = _cost_calculate_cost(r.get("model", ""), p, c)
        table.add_row(
            _cost_format_datetime(r.get("timestamp", "")),
            r.get("model", "")[:25],
            f"{p:,}",
            f"{c:,}",
            f"{p + c:,}",
            _cost_format_cost(cost),
        )

    console.print(table)
    if model:
        console.print(f"\n[dim]Filter by model: {model}[/dim]")


@app.command("prices")
def prices(
    edit: bool = typer.Option(False, "--edit", "-e", help="用 $EDITOR 打开价格配置文件"),
    reset: bool = typer.Option(False, "--reset", "-r", help="重置为默认价格"),
) -> None:
    """
    查看或编辑模型价格配置
    """
    if reset:
        _cost_save_prices(dict(_DEFAULT_PRICES))
        console.print("[green]✅ 已重置为默认价格[/green]")
        return

    if edit:
        editor = os.environ.get("EDITOR", "vim")
        _cost_ensure_config_dir()
        # 如果文件不存在，先写入当前价格
        if not _COST_PRICES_FILE.exists():
            _cost_save_prices(_cost_load_prices())
        cmd = f"{editor} {shlex.quote(str(_COST_PRICES_FILE))}"
        os.system(cmd)
        return

    prices = _cost_load_prices()
    table = Table(title="💰 模型价格配置（元/1k tokens）", show_header=True, header_style="bold cyan")
    table.add_column("模型", style="green")
    table.add_column("Prompt", justify="right")
    table.add_column("Completion", justify="right")
    table.add_column("来源", justify="center")

    defaults = set(_DEFAULT_PRICES.keys())
    for model, p in sorted(prices.items()):
        source = "默认" if model in defaults else "[yellow]自定义[/yellow]"
        table.add_row(model, f"{p['prompt']:.4f}", f"{p['completion']:.4f}", source)

    console.print(table)
    console.print(f"\n[dim]配置文件: {_COST_PRICES_FILE}[/dim]")
    console.print("[dim]编辑: omc cost prices --edit[/dim]")


@app.command("export")
def export(
    output: str = typer.Option("", "--output", "-o", help="输出文件路径（默认 stdout）"),
) -> None:
    """
    导出原始使用记录为 JSON
    """
    usage = _cost_load_usage_data()
    data = json.dumps(usage, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(data, encoding="utf-8")
        console.print(f"[green]✅ 已导出 {len(usage)} 条记录到 {output}[/green]")
    else:
        console.print(data)


# ============================================================================
# 公开 API：供 Router / Orchestrator 调用以记录用量
# ============================================================================

def record_usage(model: str, prompt_tokens: int, completion_tokens: int) -> None:
    """
    记录一次 API 调用的 token 用量。
    由 src.core.router 或 Orchestrator 在每次模型调用后调用。
    """
    _cost_record_usage(model, prompt_tokens, completion_tokens)


if __name__ == "__main__":
    app()


# ---------------------------------------------------------------------------
# Aliases for test_cli_usage.py (functions were originally in cli_usage.py)
# ---------------------------------------------------------------------------
cost_suggest = suggest
cost_report = report
cost_model = model_breakdown
cost_history = history
cost_prices = prices
cost_export = export
