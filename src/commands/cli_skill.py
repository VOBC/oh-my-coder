from __future__ import annotations

from typing import Optional

"""
Skill CLI - omc skill 命令

用法：
    omc skill list                      # 列出所有可用 Skill
    omc skill run <name> [--code <path>]  # 执行指定 Skill
    omc skill info <name>               # 查看 Skill 详情
"""


from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from src.skills import get_registry

app = typer.Typer(help="Skill 管理 - 列出和执行 Skill")
console = Console()


@app.command("list")
def list_skills(
    builtin_only: bool = typer.Option(False, "--builtin", help="仅显示内置 Skill"),
    custom_only: bool = typer.Option(False, "--custom", help="仅显示自定义 Skill"),
) -> None:
    """列出所有可用 Skill"""
    registry = get_registry()

    if builtin_only:
        skills = registry.list_builtin()
    elif custom_only:
        skills = registry.list_custom()
    else:
        skills = registry.list_all()

    if not skills:
        console.print("[dim]No skills found.[/dim]")
        return

    registry.display_list()


@app.command("info")
def skill_info(name: str) -> None:
    """查看 Skill 详细信息"""
    registry = get_registry()
    skill = registry.get(name)

    if skill is None:
        console.print(f"[red]Skill '{name}' not found[/red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold cyan]/{skill.name}[/bold cyan]\n"
            f"[dim]Source:[/dim] {skill.source}\n"
            f"[dim]File:[/dim] {skill.file_path or 'builtin'}\n\n"
            f"{skill.description or 'No description'}",
            title="Skill Info",
            expand=False,
        )
    )

    if skill.file_path:
        console.print(f"[dim]Defined in:[/dim] {skill.file_path}")


@app.command("run")
def run_skill(
    name: str = typer.Argument(..., help="Skill 名称（不含 /）"),
    code: Optional[Path] = typer.Option(
        None, "--code", "-c", help="代码文件路径（留空则从 stdin 读取）"
    ),
    output_file: Optional[Path] = typer.Option(
        None, "--output", "-o", help="输出结果到文件"
    ),
) -> None:
    """执行指定 Skill"""
    registry = get_registry()

    # 读取代码
    if code is not None:
        if not code.is_file():
            console.print(f"[red]File not found: {code}[/red]")
            raise typer.Exit(1)
        code_content = code.read_text()
        ctx = {"file_path": str(code), "module_name": code.stem}
    else:
        # 从 stdin 读取
        console.print("[dim]Paste or pipe your code (Ctrl+D to finish):[/dim]")
        code_content = ""
        try:
            import sys

            code_content = sys.stdin.read()
        except Exception:
            pass

    if not code_content.strip():
        console.print("[yellow]No code provided. Use --code or pipe input.[/yellow]")
        raise typer.Exit(1)

    ctx = {"file_path": str(code) if code else ""}
    result = registry.run(name, code_content, ctx)

    if not result.success:
        console.print(f"[red]✗ Skill failed:[/red] {result.error}")
        raise typer.Exit(1)

    console.print(f"[green]✓ Skill executed in {result.duration_ms:.1f}ms[/green]")
    console.print()

    # 输出结果
    if output_file:
        output_file.write_text(result.output)
        console.print(f"[dim]Output written to {output_file}[/dim]")
    else:
        if result.output:
            syntax = Syntax(result.output, "python", theme="monokai", line_numbers=True)
            console.print(syntax)

    # 元数据
    if result.metadata:
        console.print(f"\n[dim]Metadata:[/dim] {result.metadata}")


@app.command("init")
def init_custom_skills() -> None:
    """初始化自定义 Skill 目录"""
    skill_dir = Path.home() / ".omc" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)

    example_file = skill_dir / "example_skill.py"
    if not example_file.exists():
        example_file.write_text(
            '''"""示例自定义 Skill"""

from src.skills import Skill, SkillResult


def skill_custom_analysis(code: str, context: dict) -> SkillResult:
    """自定义代码分析 Skill"""
    lines = code.splitlines()
    return SkillResult(
        success=True,
        output=f"Analyzed {len(lines)} lines of code",
        metadata={"lines": len(lines)},
    )


# 注册
SKILL = Skill(
    name="custom_analysis",
    description="自定义代码分析 - 分析代码行数和结构",
    func=skill_custom_analysis,
    source="custom",
)
'''
        )
        console.print(f"[green]✓ Created example skill:[/green] {example_file}")
        console.print(
            "[dim]Edit it to create your own skills, then run 'omc skill list'.[/dim]"
        )
    else:
        console.print(f"[dim]Custom skills dir already exists:[/dim] {skill_dir}")


# ===== Skill 沉淀闭环 =====

@app.command("propose")
def propose_skill(
    task: str = typer.Argument(..., help="任务描述"),
    steps: str = typer.Option("", "--steps", "-s", help="执行步骤（逗号分隔）"),
    reflections: str = typer.Option(
        "", "--reflections", "-r", help="反思记录（逗号分隔）"
    ),
):
    """从任务中提取 Skill 提议"""
    from src.core.skill_extractor import (
        extract_skill_from_task,
        save_proposal,
    )

    steps_list = [s.strip() for s in steps.split(",") if s.strip()]
    reflections_list = [r.strip() for r in reflections.split(",") if r.strip()]

    proposal = extract_skill_from_task(task, steps_list, reflections_list)

    if not proposal:
        console.print(
            "[yellow]⚠️ 不值得提取（步骤太少或不够通用）[/yellow]"
        )
        raise typer.Exit(0)

    filepath = save_proposal(proposal)

    console.print("[green]✅ Skill 提议已生成[/green]")
    console.print(f"[dim]ID: {proposal.id}[/dim]")
    console.print(f"[bold]{proposal.title}[/bold]")
    console.print(f"触发: {proposal.trigger}")
    console.print("\n步骤:")
    for i, step in enumerate(proposal.steps, 1):
        console.print(f"  {i}. {step}")
    console.print(f"\n[dim]保存到: {filepath}[/dim]")
    console.print("[dim]运行 'omc skill review' 查看待处理提议[/dim]")


@app.command("review")
def review_proposals():
    """查看待处理的 Skill 提议"""
    from src.core.skill_extractor import list_proposals

    proposals = list_proposals()
    pending = [p for p in proposals if p.status == "pending"]

    if not pending:
        console.print("[dim]没有待处理的 Skill 提议[/dim]")
        return

    console.print(f"[bold]📋 待处理的 Skill 提议 ({len(pending)})\n[/bold]")

    for i, p in enumerate(pending, 1):
        console.print(
            Panel(
                f"[bold]{i}. {p.title}[/bold]\n"
                f"[dim]ID: {p.id}[/dim]\n"
                f"触发: {p.trigger}\n"
                f"步骤数: {len(p.steps)}\n"
                f"来源: {p.source_task[:60]}...",
                expand=False,
            )
        )

    console.print("\n[dim]使用以下命令处理:[/dim]")
    console.print("  omc skill accept <id>  # 接受并生成 SKILL.md")
    console.print("  omc skill reject <id>  # 拒绝")


@app.command("accept")
def accept_skill_proposal(proposal_id: str):
    """接受 Skill 提议"""
    from src.core.skill_extractor import accept_proposal

    skill_path = accept_proposal(proposal_id)
    if skill_path:
        console.print("[green]✅ Skill 已接受[/green]")
        console.print(f"[dim]生成文件: {skill_path}[/dim]")
    else:
        console.print(f"[red]❌ 未找到提议: {proposal_id}[/red]")
        raise typer.Exit(1)


@app.command("reject")
def reject_skill_proposal(proposal_id: str):
    """拒绝 Skill 提议"""
    from src.core.skill_extractor import reject_proposal

    if reject_proposal(proposal_id):
        console.print(f"[green]✅ 已拒绝提议: {proposal_id}[/green]")
    else:
        console.print(f"[red]❌ 未找到提议: {proposal_id}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
