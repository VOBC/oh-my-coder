"""
成本优化 CLI - omc cost 命令

使用示例：
  omc cost "修复登录 bug"                    # 简单任务
  omc cost "重构用户模块"                    # 中等复杂度
  omc cost "设计新系统架构"                  # 复杂任务
  omc cost --files 15 "实现支付功能"         # 指定文件数
  omc cost --list                           # 列出所有可用模型
"""

from __future__ import annotations


import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="成本优化建议 - 根据任务复杂度推荐最优模型")
console = Console()


@app.command()
def cost(
    task: str = typer.Argument("", help="任务描述"),
    files: int = typer.Option(0, "--files", "-f", help="涉及文件数量"),
    list_models: bool = typer.Option(False, "--list", "-l", help="列出所有可用模型"),
    prefer_local: bool = typer.Option(
        True, "--prefer-local/--no-local", help="是否优先推荐本地模型"
    ),
):
    """根据任务复杂度推荐最优模型，节省成本"""
    from .agents.cost_optimizer import CostOptimizer

    optimizer = CostOptimizer(prefer_local=prefer_local)

    if list_models:
        _list_models(optimizer)
        return

    if not task:
        console.print("[yellow]请输入任务描述，例如:[/yellow]")
        console.print("  omc cost 修复登录 bug")
        console.print("  omc cost 设计新系统架构")
        console.print("  omc cost --files 15 实现支付功能")
        return

    # 推荐模型
    recommendation = optimizer.recommend(task, file_count=files if files > 0 else None)

    # 显示结果
    complexity_colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
    }

    cost_bars = "💰" * recommendation.estimated_cost

    complexity_color = complexity_colors.get(recommendation.complexity.value, "white")
    complexity_val = recommendation.complexity.value.upper()
    complexity_text = f"[{complexity_color}]{complexity_val}[/]"

    panel = Panel(
        f"**推荐模型**: [cyan]{recommendation.model}[/cyan]\n\n"
        f"**提供商**: {recommendation.provider}\n\n"
        f"**复杂度**: {complexity_text}\n\n"
        f"**估算成本**: {cost_bars}\n\n"
        f"**推荐理由**:\n{recommendation.reason}",
        title="🎯 模型推荐",
        border_style="cyan",
    )
    console.print(panel)

    # 显示备选
    if recommendation.alternatives:
        console.print("\n[dim]备选方案:[/dim]")
        for alt in recommendation.alternatives:
            console.print(f"  • {alt['model']}: {alt['reason']}")

    # 成本对比
    console.print("\n[dim]💡 小贴士:[/dim]")
    if recommendation.complexity.value == "low":
        console.print("  简单任务用本地模型可完全免费")
    elif recommendation.complexity.value == "medium":
        console.print("  国产模型性价比高，适合中等复杂度")
    else:
        console.print("  复杂任务建议先用本地模型验证思路")


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


if __name__ == "__main__":
    app()
