from __future__ import annotations

"""
成本 CLI - omc cost 命令

包含两个功能模块：
1. 成本建议 - 根据任务复杂度推荐最优模型
2. 成本报告 - 查看历史 token 消耗和预估费用

使用示例：
  # 成本建议
  omc cost suggest "修复登录 bug"                    # 简单任务
  omc cost suggest "重构用户模块"                    # 中等复杂度
  omc cost suggest --files 15 "实现支付功能"         # 指定文件数
  omc cost suggest --list                            # 列出所有可用模型

  # 成本报告
  omc cost report                                    # 本月/本周/今日汇总
  omc cost model                                     # 按模型分组显示消耗
  omc cost history --limit 20                        # 最近 N 次调用明细
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="成本优化 - 模型推荐与使用报告")
console = Console()

# 配置路径
CONFIG_DIR = Path.home() / ".config" / "oh-my-coder"
USAGE_FILE = CONFIG_DIR / "usage.json"
PRICES_FILE = CONFIG_DIR / "model_prices.json"

# 默认模型价格（元/1k tokens）
DEFAULT_PRICES = {
    "deepseek-chat": {"prompt": 0.001, "completion": 0.002},
    "deepseek-coder": {"prompt": 0.001, "completion": 0.002},
    "deepseek-reasoner": {"prompt": 0.004, "completion": 0.016},
    "gpt-4o": {"prompt": 0.036, "completion": 0.108},
    "gpt-4o-mini": {"prompt": 0.003, "completion": 0.012},
    "claude-3-opus": {"prompt": 0.105, "completion": 0.525},
    "claude-3-sonnet": {"prompt": 0.021, "completion": 0.105},
    "claude-3-haiku": {"prompt": 0.004, "completion": 0.02},
    "glm-4": {"prompt": 0.01, "completion": 0.01},
    "glm-4-flash": {"prompt": 0.0, "completion": 0.0},
    "qwen-turbo": {"prompt": 0.002, "completion": 0.006},
    "qwen-plus": {"prompt": 0.008, "completion": 0.02},
    "moonshot-v1": {"prompt": 0.006, "completion": 0.006},
    "hunyuan-lite": {"prompt": 0.0, "completion": 0.0},
    "hunyuan-standard": {"prompt": 0.0045, "completion": 0.005},
    "doubao-lite": {"prompt": 0.0003, "completion": 0.0006},
    "doubao-pro": {"prompt": 0.0008, "completion": 0.002},
    "minimax": {"prompt": 0.005, "completion": 0.005},
    "spark": {"prompt": 0.006, "completion": 0.006},
    "baichuan": {"prompt": 0.005, "completion": 0.005},
    "tiangong": {"prompt": 0.005, "completion": 0.005},
    "mimo": {"prompt": 0.002, "completion": 0.006},
    "ollama": {"prompt": 0.0, "completion": 0.0},
}


# =============================================================================
# 工具函数
# =============================================================================


def _load_prices() -> dict[str, dict[str, float]]:
    """加载模型价格配置"""
    if PRICES_FILE.exists():
        try:
            with open(PRICES_FILE, encoding="utf-8") as f:
                custom_prices = json.load(f)
                # 合并默认价格和自定义价格
                return {**DEFAULT_PRICES, **custom_prices}
        except Exception:
            pass
    return DEFAULT_PRICES


def _load_usage_data() -> list[dict[str, Any]]:
    """加载使用记录"""
    if USAGE_FILE.exists():
        try:
            with open(USAGE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """计算单次调用成本"""
    prices = _load_prices()
    model_lower = model.lower()

    # 尝试精确匹配
    if model_lower in prices:
        p = prices[model_lower]
        return (
            (prompt_tokens / 1000) * p["prompt"]
            + (completion_tokens / 1000) * p["completion"]
        )

    # 尝试前缀匹配
    for key, p in prices.items():
        if model_lower.startswith(key) or key in model_lower:
            return (
                (prompt_tokens / 1000) * p["prompt"]
                + (completion_tokens / 1000) * p["completion"]
            )

    # 默认价格
    return (prompt_tokens + completion_tokens) / 1000 * 0.01


def _format_datetime(dt_str: str) -> str:
    """格式化日期时间"""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str


def _format_cost(cost: float) -> str:
    """格式化成本显示"""
    if cost == 0:
        return "Free"
    elif cost < 0.01:
        return "< 0.01"
    else:
        return f"{cost:.3f}"


# =============================================================================
# 子命令: suggest (原有的成本建议)
# =============================================================================


@app.command("suggest")
def suggest(
    task: str = typer.Argument("", help="Task description"),
    files: int = typer.Option(0, "--files", "-f", help="Number of files involved"),
    list_models: bool = typer.Option(False, "--list", "-l", help="List all available models"),
    prefer_local: bool = typer.Option(
        True, "--prefer-local/--no-local", help="Prefer local models"
    ),
):
    """Recommend optimal model based on task complexity"""
    from src.agents.cost_optimizer import CostOptimizer

    optimizer = CostOptimizer(prefer_local=prefer_local)

    if list_models:
        _list_models(optimizer)
        return

    if not task:
        console.print("[yellow]Please enter a task description, e.g.:[/yellow]")
        console.print("  omc cost suggest 'fix login bug'")
        console.print("  omc cost suggest 'design new system architecture'")
        console.print("  omc cost suggest --files 15 'implement payment'")
        return

    # 推荐模型
    recommendation = optimizer.recommend(task, file_count=files if files > 0 else None)

    # 显示结果
    complexity_colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
    }

    cost_bars = "💰" * int(recommendation.estimated_cost)

    complexity_color = complexity_colors.get(recommendation.complexity.value, "white")
    complexity_val = recommendation.complexity.value.upper()
    complexity_text = f"[{complexity_color}]{complexity_val}[/]"

    panel = Panel(
        f"**Recommended Model**: [cyan]{recommendation.model}[/cyan]\n\n"
        f"**Provider**: {recommendation.provider}\n\n"
        f"**Complexity**: {complexity_text}\n\n"
        f"**Est. Cost**: {cost_bars}\n\n"
        f"**Reason**:\n{recommendation.reason}",
        title="🎯 Model Recommendation",
        border_style="cyan",
    )
    console.print(panel)

    # 显示备选
    if recommendation.alternatives:
        console.print("\n[dim]Alternatives:[/dim]")
        for alt in recommendation.alternatives:
            console.print(f"  • {alt['model']}: {alt['reason']}")

    # 成本对比
    console.print("\n[dim]💡 Tips:[/dim]")
    if recommendation.complexity.value == "low":
        console.print("  Use local model for simple tasks - completely free")
    elif recommendation.complexity.value == "medium":
        console.print("  Chinese models offer great value for medium complexity")
    else:
        console.print("  For complex tasks, try local model first to validate ideas")


def _list_models(optimizer):
    """列出所有可用模型"""
    models = optimizer.get_all_models()

    # 按提供商分组
    by_provider: dict = {}
    for m in models:
        provider = m["provider"]
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(m)

    for provider, model_list in by_provider.items():
        console.print(f"\n### {provider.upper()}")

        for m in model_list:
            cost_bars = "💰" * m["cost"]
            console.print(f"  {m['model']:30s} {cost_bars}")


# =============================================================================
# 子命令: report
# =============================================================================


@app.command("report")
def report(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to report"),
):
    """Show token usage summary (month/week/today)"""
    usage_data = _load_usage_data()

    if not usage_data:
        console.print(
            Panel.fit(
                "[yellow]No usage records found[/yellow]\n\n"
                "Usage data will be recorded automatically when you run tasks.",
                title="📊 Cost Report",
                border_style="yellow",
            )
        )
        return

    # 计算时间范围
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    # 统计
    stats = {
        "today": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
        "week": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
        "month": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
        "total": {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0},
    }

    for record in usage_data:
        try:
            record_time = datetime.fromisoformat(record.get("timestamp", ""))
        except Exception:
            continue

        prompt = record.get("prompt_tokens", 0)
        completion = record.get("completion_tokens", 0)
        model = record.get("model", "unknown")
        cost = _calculate_cost(model, prompt, completion)

        # 累计总计
        stats["total"]["calls"] += 1
        stats["total"]["prompt"] += prompt
        stats["total"]["completion"] += completion
        stats["total"]["cost"] += cost

        # 按月统计
        if record_time >= month_start:
            stats["month"]["calls"] += 1
            stats["month"]["prompt"] += prompt
            stats["month"]["completion"] += completion
            stats["month"]["cost"] += cost

            # 按周统计
            if record_time >= week_start:
                stats["week"]["calls"] += 1
                stats["week"]["prompt"] += prompt
                stats["week"]["completion"] += completion
                stats["week"]["cost"] += cost

                # 按日统计
                if record_time >= today_start:
                    stats["today"]["calls"] += 1
                    stats["today"]["prompt"] += prompt
                    stats["today"]["completion"] += completion
                    stats["today"]["cost"] += cost

    # 显示汇总表
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]📊 Token Usage Summary[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Period", style="green")
    table.add_column("Calls", justify="right")
    table.add_column("Prompt Tokens", justify="right")
    table.add_column("Completion Tokens", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Est. Cost (CNY)", justify="right")

    table.add_row(
        "Today",
        str(stats["today"]["calls"]),
        f"{stats['today']['prompt']:,}",
        f"{stats['today']['completion']:,}",
        f"{stats['today']['prompt'] + stats['today']['completion']:,}",
        f"[green]{_format_cost(stats['today']['cost'])}[/green]",
    )
    table.add_row(
        "This Week",
        str(stats["week"]["calls"]),
        f"{stats['week']['prompt']:,}",
        f"{stats['week']['completion']:,}",
        f"{stats['week']['prompt'] + stats['week']['completion']:,}",
        f"[green]{_format_cost(stats['week']['cost'])}[/green]",
    )
    table.add_row(
        "This Month",
        str(stats["month"]["calls"]),
        f"{stats['month']['prompt']:,}",
        f"{stats['month']['completion']:,}",
        f"{stats['month']['prompt'] + stats['month']['completion']:,}",
        f"[green]{_format_cost(stats['month']['cost'])}[/green]",
    )
    table.add_row(
        "Total",
        str(stats["total"]["calls"]),
        f"{stats['total']['prompt']:,}",
        f"{stats['total']['completion']:,}",
        f"{stats['total']['prompt'] + stats['total']['completion']:,}",
        f"[bold green]{_format_cost(stats['total']['cost'])}[/bold green]",
    )

    console.print(table)
    console.print()
    console.print(f"[dim]Data source: {USAGE_FILE}[/dim]")
    console.print(f"[dim]Prices configured: {len(_load_prices())} models[/dim]")


# =============================================================================
# 子命令: model
# =============================================================================


@app.command("model")
def model_summary(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to report"),
):
    """Show usage grouped by model"""
    usage_data = _load_usage_data()

    if not usage_data:
        console.print(
            Panel.fit(
                "[yellow]No usage records found[/yellow]\n\n"
                "Usage data will be recorded automatically when you run tasks.",
                title="📈 Model Usage",
                border_style="yellow",
            )
        )
        return

    # 按模型分组统计
    model_stats: dict[str, dict[str, Any]] = {}

    for record in usage_data:
        model = record.get("model", "unknown")
        prompt = record.get("prompt_tokens", 0)
        completion = record.get("completion_tokens", 0)
        cost = _calculate_cost(model, prompt, completion)

        if model not in model_stats:
            model_stats[model] = {
                "calls": 0,
                "prompt": 0,
                "completion": 0,
                "cost": 0.0,
            }

        model_stats[model]["calls"] += 1
        model_stats[model]["prompt"] += prompt
        model_stats[model]["completion"] += completion
        model_stats[model]["cost"] += cost

    # 按调用次数排序
    sorted_models = sorted(
        model_stats.items(), key=lambda x: x[1]["calls"], reverse=True
    )

    # 显示表格
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]📈 Usage by Model[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Model", style="green")
    table.add_column("Calls", justify="right")
    table.add_column("Prompt Tokens", justify="right")
    table.add_column("Completion Tokens", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Est. Cost (CNY)", justify="right")

    for model, stats in sorted_models:
        total_tokens = stats["prompt"] + stats["completion"]
        table.add_row(
            model,
            str(stats["calls"]),
            f"{stats['prompt']:,}",
            f"{stats['completion']:,}",
            f"{total_tokens:,}",
            f"[green]{_format_cost(stats['cost'])}[/green]",
        )

    # 添加总计行
    total_calls = sum(s["calls"] for _, s in sorted_models)
    total_prompt = sum(s["prompt"] for _, s in sorted_models)
    total_completion = sum(s["completion"] for _, s in sorted_models)
    total_cost = sum(s["cost"] for _, s in sorted_models)

    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_calls}[/bold]",
        f"[bold]{total_prompt:,}[/bold]",
        f"[bold]{total_completion:,}[/bold]",
        f"[bold]{total_prompt + total_completion:,}[/bold]",
        f"[bold green]{_format_cost(total_cost)}[/bold green]",
    )

    console.print(table)


# =============================================================================
# 子命令: history
# =============================================================================


@app.command("history")
def history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to show"),
    model: str = typer.Option(None, "--model", "-m", help="Filter by model"),
):
    """Show recent call history"""
    usage_data = _load_usage_data()

    if not usage_data:
        console.print(
            Panel.fit(
                "[yellow]No usage records found[/yellow]\n\n"
                "Usage data will be recorded automatically when you run tasks.",
                title="📜 Call History",
                border_style="yellow",
            )
        )
        return

    # 过滤和排序
    filtered = usage_data
    if model:
        filtered = [r for r in filtered if model.lower() in r.get("model", "").lower()]

    # 按时间倒序
    sorted_records = sorted(
        filtered,
        key=lambda x: x.get("timestamp", ""),
        reverse=True,
    )[:limit]

    # 显示表格
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]📜 Recent Calls (last {len(sorted_records)})[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Time", style="dim", width=16)
    table.add_column("Model", style="green")
    table.add_column("Prompt", justify="right", width=10)
    table.add_column("Completion", justify="right", width=12)
    table.add_column("Total", justify="right", width=10)
    table.add_column("Cost", justify="right", width=10)

    for record in sorted_records:
        ts = _format_datetime(record.get("timestamp", ""))
        m = record.get("model", "unknown")
        prompt = record.get("prompt_tokens", 0)
        completion = record.get("completion_tokens", 0)
        total = prompt + completion
        cost = _calculate_cost(m, prompt, completion)

        table.add_row(
            ts,
            m[:30],
            f"{prompt:,}",
            f"{completion:,}",
            f"{total:,}",
            f"[green]{_format_cost(cost)}[/green]",
        )

    console.print(table)

    if model:
        console.print(f"\n[dim]Filtered by model: {model}[/dim]")


# =============================================================================
# 主命令 (默认显示帮助)
# =============================================================================


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Default show help"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        console.print()
        console.print("[bold]Examples:[/bold]")
        console.print("  [cyan]omc cost suggest 'fix login bug'[/cyan]      # Get model recommendation")
        console.print("  [cyan]omc cost report[/cyan]                        # View usage summary")
        console.print("  [cyan]omc cost model[/cyan]                         # Usage by model")
        console.print("  [cyan]omc cost history --limit 10[/cyan]            # Recent calls")


if __name__ == "__main__":
    app()
