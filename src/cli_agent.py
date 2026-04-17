"""
Agent 配置 CLI - 导出/导入/管理 Agent 配置

命令：
- omc agent list              # 列出所有可用 Agent
- omc agent show <name>       # 显示 Agent 详细信息
- omc agent export <name>     # 导出 Agent 配置为 JSON
- omc agent import <file>     # 从文件导入 Agent 配置
- omc agent evolve <name>     # 触发 Agent 自进化
- omc agent stats <name>      # 显示 Agent 进化统计
"""

from __future__ import annotations

import json
import httpx
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help="Agent 配置管理")
console = Console()


@app.command("list")
def list_agents():
    """列出所有可用 Agent"""
    from .agents.base import list_all_agents

    agents = list_all_agents()

    table = Table(title="可用 Agent 列表")
    table.add_column("名称", style="cyan")
    table.add_column("描述", style="white")
    table.add_column("Lane", style="yellow")
    table.add_column("默认 Tier", style="green")

    for agent_info in agents:
        table.add_row(
            agent_info.get("name", ""),
            agent_info.get("description", "")[:50],
            agent_info.get("lane", ""),
            agent_info.get("default_tier", ""),
        )

    console.print(table)


@app.command("show")
def show_agent(
    name: str = typer.Argument(..., help="Agent 名称"),
    evolution: bool = typer.Option(False, "--evolution", "-e", help="显示进化信息"),
):
    """显示 Agent 详细信息"""
    from .agents.base import get_agent

    agent_class = get_agent(name)
    if not agent_class:
        console.print(f"[red]错误：未找到 Agent '{name}'[/red]")
        raise typer.Exit(1)

    # 创建实例获取信息
    agent = agent_class()

    lane_str = agent.lane.value if hasattr(agent.lane, "value") else str(agent.lane)
    info = Panel(
        f"[bold]名称:[/bold] {agent.name}\n"
        f"[bold]描述:[/bold] {agent.description}\n"
        f"[bold]Lane:[/bold] {lane_str}\n"
        f"[bold]默认 Tier:[/bold] {agent.default_tier}\n"
        f"[bold]图标:[/bold] {agent.icon}\n"
        f"[bold]工具:[/bold] {', '.join(agent.tools) if agent.tools else '无'}\n\n"
        f"[bold]System Prompt:[/bold]\n{agent.system_prompt[:500]}...",
        title=f"Agent: {name}",
        border_style="cyan",
    )
    console.print(info)

    if evolution:
        from .agents.self_improving import SelfImprovingAgent

        sia = SelfImprovingAgent()
        stats = sia.get_evolution_stats(name)

        evolution_info = Panel(
            f"[bold]当前代数:[/bold] {stats.get('current_generation', 1)}\n"
            f"[bold]总进化次数:[/bold] {stats.get('total_evolutions', 0)}\n"
            f"[bold]模式数:[/bold] {stats.get('total_patterns', 0)}\n"
            f"[bold]Prompt 版本:[/bold] {stats.get('prompt_version', 0)}\n"
            f"[bold]最后进化:[/bold] {stats.get('last_evolution', '尚未进化')}",
            title="进化信息",
            border_style="green",
        )
        console.print(evolution_info)


@app.command("export")
def export_agent(
    name: str = typer.Argument(..., help="Agent 名称"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出文件路径"),
    include_evolution: bool = typer.Option(
        False, "--evolution", "-e", help="包含进化历史"
    ),
    include_patterns: bool = typer.Option(
        False, "--patterns", "-p", help="包含成功模式库"
    ),
):
    """
    导出 Agent 配置为 JSON

    导出内容包含：
    - Agent 基础配置（system prompt、模型、温度等）
    - 进化历史（可选）
    - 成功模式库（可选）
    """
    from .agents.base import get_agent

    agent_class = get_agent(name)
    if not agent_class:
        console.print(f"[red]错误：未找到 Agent '{name}'[/red]")
        raise typer.Exit(1)

    agent = agent_class()

    # 构建配置
    config_data = {
        "name": agent.name,
        "description": agent.description,
        "model": getattr(agent, "model", "deepseek"),
        "tools": agent.tools,
        "lane": agent.lane.value if hasattr(agent.lane, "value") else str(agent.lane),
        "default_tier": agent.default_tier,
        "icon": agent.icon,
        "prompts": {
            "system": agent.system_prompt,
        },
        "environment": {
            "max_tokens": getattr(agent, "max_tokens", 8000),
            "temperature": getattr(agent, "temperature", 0.7),
            "timeout": getattr(agent, "timeout", 60),
        },
    }

    # 可选：包含进化历史
    if include_evolution:
        from .agents.evolution import EvolutionStore
        from pathlib import Path

        state_dir = Path.home() / ".omc" / "state"
        store = EvolutionStore(state_dir)
        history = store.load_evolution_history(name)
        config_data["evolution_history"] = [
            {
                "id": r.id,
                "timestamp": r.timestamp,
                "generation": r.generation,
                "changes": r.changes,
            }
            for r in history
        ]

    # 可选：包含成功模式库
    if include_patterns:
        from .agents.evolution import EvolutionStore
        from pathlib import Path

        state_dir = Path.home() / ".omc" / "state"
        store = EvolutionStore(state_dir)
        patterns = store.load_success_patterns(name)
        config_data["success_patterns"] = [
            {
                "id": p.id,
                "pattern_type": p.pattern_type,
                "description": p.description,
                "effectiveness_score": p.effectiveness_score,
            }
            for p in patterns
        ]

    # 确定输出路径
    if output is None:
        output = Path(f"{name}-agent-config.json")

    # 写入文件
    output.write_text(
        json.dumps(config_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green] Agent '{name}' 配置已导出到: {output}")
    console.print("  - 基础配置: ✓")
    if include_evolution:
        console.print("  - 进化历史: ✓")
    if include_patterns:
        console.print("  - 成功模式: ✓")


@app.command("import")
def import_agent(
    source: str = typer.Argument(..., help="配置文件路径或 URL"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="新 Agent 名称"),
):
    """
    从文件或 URL 导入 Agent 配置

    支持：
    - 本地 JSON 文件
    - GitHub raw URL
    - HTTP/HTTPS URL
    """
    source_path: Optional[Path] = None
    config_data: Dict[str, Any]

    # 判断是 URL 还是本地文件
    if source.startswith(("http://", "https://")):
        # 从 URL 下载
        console.print("[cyan]正在从 URL 下载配置...[/cyan]")
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(source)
                response.raise_for_status()
                config_data = response.json()
        except Exception as e:
            console.print(f"[red]下载失败: {e}[/red]")
            raise typer.Exit(1)
        console.print("[green]✓[/green] 配置下载成功")
    else:
        # 本地文件
        source_path = Path(source)
        if not source_path.exists():
            console.print(f"[red]错误：文件不存在 '{source}'[/red]")
            raise typer.Exit(1)

        try:
            config_data = json.loads(source_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            console.print(f"[red]JSON 解析失败: {e}[/red]")
            raise typer.Exit(1)

    # 验证配置格式
    required_fields = ["name", "description"]
    for field in required_fields:
        if field not in config_data:
            console.print(f"[red]错误：缺少必需字段 '{field}'[/red]")
            raise typer.Exit(1)

    # 确定最终名称
    final_name = name or config_data["name"]

    # 保存配置到 .omc/agents/ 目录
    agents_dir = Path.home() / ".omc" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    config_file = agents_dir / f"{final_name}.json"
    config_data["name"] = final_name  # 更新名称

    config_file.write_text(
        json.dumps(config_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green] Agent '{final_name}' 配置已导入")
    console.print(f"  位置: {config_file}")

    # 如果包含进化历史，也保存
    if "evolution_history" in config_data:
        from .agents.evolution import EvolutionStore, EvolutionRecord

        state_dir = Path.home() / ".omc" / "state"
        store = EvolutionStore(state_dir)

        for record_data in config_data["evolution_history"]:
            record = EvolutionRecord(
                id=record_data.get("id", ""),
                timestamp=record_data.get("timestamp", ""),
                agent_type=final_name,
                generation=record_data.get("generation", 1),
                trigger="imported",
                changes=record_data.get("changes", []),
            )
            store.save_evolution_record(record)

        console.print("  - 进化历史已导入")

    # 如果包含成功模式，也保存
    if "success_patterns" in config_data:
        from .agents.evolution import EvolutionStore

        state_dir = Path.home() / ".omc" / "state"
        store = EvolutionStore(state_dir)

        for pattern_data in config_data["success_patterns"]:
            store.add_success_pattern(
                agent_name=final_name,
                pattern_type=pattern_data.get("pattern_type", "imported"),
                description=pattern_data.get("description", ""),
                context=pattern_data.get("context", ""),
            )

        console.print("  - 成功模式已导入")


@app.command("evolve")
def evolve_agent(
    name: str = typer.Argument(..., help="Agent 名称"),
    trigger: str = typer.Option("manual", "--trigger", "-t", help="触发原因"),
):
    """手动触发 Agent 自进化"""
    from .agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    record = sia.evolve(name, trigger=trigger)

    if record:
        console.print(
            f"[green]✓[/green] Agent '{name}' 完成第 {record.generation} 代进化"
        )
        console.print(f"  进化 ID: {record.id}")
        console.print("  变更:")
        for change in record.changes:
            console.print(f"    - {change}")
    else:
        console.print("[yellow]未触发进化（样本不足或无需优化）[/yellow]")


@app.command("stats")
def agent_stats(
    name: str = typer.Argument(..., help="Agent 名称"),
):
    """显示 Agent 进化统计"""
    from .agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    stats = sia.get_evolution_stats(name)

    table = Table(title=f"Agent '{name}' 进化统计")
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green")

    table.add_row("当前代数", str(stats.get("current_generation", 1)))
    table.add_row("总进化次数", str(stats.get("total_evolutions", 0)))
    table.add_row("成功模式数", str(stats.get("total_patterns", 0)))
    table.add_row("Prompt 版本", str(stats.get("prompt_version", 0)))
    table.add_row("最后进化", stats.get("last_evolution", "尚未进化"))
    table.add_row("自进化启用", str(stats.get("config", {}).get("enabled", True)))
    table.add_row(
        "改进阈值", f"{stats.get('config', {}).get('improvement_threshold', 0.8):.0%}"
    )

    console.print(table)


# ------------------------------------------------------------------
# 版本迭代记忆 - 解决鬼打墙问题
# ------------------------------------------------------------------


@app.command("decisions")
def list_decisions(
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help="按类别过滤 (bug_fix/solution_choice/rejection/architecture)",
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="显示数量"),
):
    """列出历史决策记录"""
    from .agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    decisions = sia.list_decisions(category=category, limit=limit)

    if not decisions:
        console.print("[yellow]暂无决策记录[/yellow]")
        return

    table = Table(title="历史决策记录")
    table.add_column("ID", style="cyan", width=25)
    table.add_column("标题", style="white")
    table.add_column("类别", style="yellow")
    table.add_column("结果", style="green")
    table.add_column("问题", style="dim", width=40)

    for d in decisions:
        table.add_row(
            d["id"],
            d["title"],
            d["category"],
            d["result"],
            d["problem"],
        )

    console.print(table)
    console.print("\n[dim]使用 'omc agent decision <问题描述>' 检索相关决策[/dim]")


@app.command("decision")
def retrieve_decision(
    problem: str = typer.Argument(..., help="问题描述，用于检索相似决策"),
    limit: int = typer.Option(3, "--limit", "-n", help="返回数量"),
):
    """检索历史决策，避免重复踩坑"""
    from .agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    decisions = sia.retrieve_past_decisions(problem, limit=limit)

    if not decisions:
        console.print("[yellow]未找到相关决策记录[/yellow]")
        console.print("[dim]使用 'omc agent record-decision' 记录新决策[/dim]")
        return

    console.print(f"[cyan]找到 {len(decisions)} 条相关决策：[/cyan]\n")

    for i, d in enumerate(decisions, 1):
        panel = Panel(
            f"**问题**: {d['problem']}\n\n"
            f"**解决方案**: {d['chosen_solution']}\n\n"
            f"**结果**: {d['result']}\n\n"
            f"**效果**: {d.get('outcome', 'N/A')}\n\n"
            f"**适用场景**: {d.get('reusable_for', 'N/A')}\n\n"
            f"**关键词**: {', '.join(d.get('keywords', []))}",
            title=f"{i}. {d['title']}",
            border_style="cyan",
        )
        console.print(panel)


@app.command("record-decision")
def record_decision(
    title: str = typer.Option(..., "--title", "-t", help="决策标题"),
    problem: str = typer.Option(..., "--problem", "-p", help="遇到的问题"),
    solution: str = typer.Option(..., "--solution", "-s", help="选择的解决方案"),
    category: str = typer.Option(
        "solution_choice", "--category", "-c", help="决策类别"
    ),
    result: str = typer.Option(
        "success", "--result", "-r", help="结果 (success/failure)"
    ),
    outcome: str = typer.Option("", "--outcome", "-o", help="效果描述"),
    reusable_for: str = typer.Option("", "--reusable-for", help="适用场景"),
):
    """记录重要决策"""
    from .agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    decision_id = sia.record_decision(
        title=title,
        problem=problem,
        chosen_solution=solution,
        category=category,
        result=result,
        outcome=outcome,
        reusable_for=reusable_for,
    )

    console.print(f"[green]✓[/green] 决策已记录: {decision_id}")


@app.command("decision-stats")
def decision_stats():
    """显示决策记忆统计"""
    from .agents.self_improving import SelfImprovingAgent

    sia = SelfImprovingAgent()
    stats = sia.get_decision_stats()

    table = Table(title="决策记忆统计")
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green")

    table.add_row("总决策数", str(stats.get("total_decisions", 0)))
    table.add_row("最新决策", stats.get("latest_decision", "无"))

    category_data = stats.get("by_category", {})
    if category_data:
        table.add_row(
            "按类别", ", ".join(f"{k}: {v}" for k, v in category_data.items())
        )

    console.print(table)


if __name__ == "__main__":
    app()
