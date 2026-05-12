"""
思维链 CLI - omc thought 命令

记录和可视化 Agent 思维链。
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from src.core.chain_of_thought import (
    ChainOfThoughtRecorder,
    ConfidenceLevel,
    ReasoningStepType,
    visualize_chain,
)

app = typer.Typer(help="思维链 - 记录和可视化 Agent 推理过程")
console = Console()


@app.command("start")
def start_chain(
    task: str = typer.Argument(..., help="任务描述"),
    agent: str = typer.Option("assistant", "--agent", "-a", help="Agent 名称"),
):
    """开始记录思维链"""
    recorder = ChainOfThoughtRecorder()
    chain = recorder.start_chain(task, agent)

    console.print("[green]✅ 思维链已启动[/green]")
    console.print(f"[dim]ID: {chain.chain_id}[/dim]")
    console.print(f"任务: {chain.task_description}")
    console.print("\n[dim]使用以下命令添加步骤:[/dim]")
    console.print(f"  omc thought step {chain.chain_id} -t analysis -d '分析...'")


@app.command("step")
def add_step(
    chain_id: str = typer.Argument(..., help="思维链 ID"),
    step_type: str = typer.Option("analysis", "--type", "-t", help="步骤类型"),
    description: str = typer.Option(..., "--desc", "-d", help="步骤描述"),
    reasoning: str = typer.Option("", "--reasoning", "-r", help="推理过程"),
    conclusion: str = typer.Option("", "--conclusion", "-c", help="结论"),
    confidence: str = typer.Option("medium", "--confidence", help="置信度"),
):
    """添加推理步骤"""
    recorder = ChainOfThoughtRecorder()

    try:
        st = ReasoningStepType(step_type)
    except ValueError:
        console.print(f"[red]无效步骤类型: {step_type}[/red]")
        console.print(f"可用: {[t.value for t in ReasoningStepType]}")
        raise typer.Exit(1)

    try:
        conf = ConfidenceLevel(confidence)
    except ValueError:
        conf = ConfidenceLevel.MEDIUM

    step = recorder.add_step(
        chain_id=chain_id,
        step_type=st,
        description=description,
        reasoning=reasoning or description,
        conclusion=conclusion,
        confidence=conf,
    )

    if step:
        console.print(f"[green]✅ 步骤已添加[/green] [{step.step_id}]")
    else:
        console.print(f"[red]思维链不存在: {chain_id}[/red]")
        raise typer.Exit(1)


@app.command("complete")
def complete_chain(
    chain_id: str = typer.Argument(..., help="思维链 ID"),
    conclusion: str = typer.Option("", "--conclusion", "-c", help="最终结论"),
):
    """完成思维链"""
    recorder = ChainOfThoughtRecorder()
    recorder.complete_chain(chain_id, conclusion)
    console.print(f"[green]✅ 思维链已完成[/green] {chain_id}")


@app.command("show")
def show_chain(
    chain_id: str = typer.Argument(..., help="思维链 ID"),
    format: str = typer.Option("text", "--format", "-f", help="格式: text/html/mermaid"),
):
    """查看思维链"""
    recorder = ChainOfThoughtRecorder()
    chain = recorder.get_chain(chain_id)

    if not chain:
        console.print(f"[red]思维链不存在: {chain_id}[/red]")
        raise typer.Exit(1)

    output = visualize_chain(chain, format)

    if format == "html":
        # 保存到文件
        output_path = f"/tmp/chain_{chain_id}.html"
        with open(output_path, "w") as f:
            f.write(output)
        console.print(f"[green]HTML 已保存:[/green] {output_path}")
    else:
        console.print(output)


@app.command("list")
def list_chains(
    agent: str = typer.Option(None, "--agent", "-a", help="按 Agent 过滤"),
):
    """列出思维链"""
    recorder = ChainOfThoughtRecorder()
    chains = recorder.list_chains(agent)

    if not chains:
        console.print("[dim]没有思维链[/dim]")
        return

    table = Table(title="思维链列表")
    table.add_column("ID", style="cyan")
    table.add_column("任务", style="green")
    table.add_column("Agent", style="blue")
    table.add_column("步骤数", justify="right")
    table.add_column("状态", style="yellow")

    for c in chains:
        table.add_row(
            c.chain_id,
            c.task_description[:40],
            c.agent_name,
            str(len(c.steps)),
            c.status,
        )

    console.print(table)


if __name__ == "__main__":
    app()
