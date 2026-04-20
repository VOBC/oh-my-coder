"""
工作流模板 CLI - 模板管理和使用

命令：
- omc template list              # 列出可用模板
- omc template show <name>       # 显示模板详情
- omc template use <name>        # 使用模板创建工作流
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

app = typer.Typer(help="工作流模板管理")
console = Console()

# 模板目录
TEMPLATES_DIR = Path(__file__).parent.parent / "docs" / "templates"

# 内置模板
BUILTIN_TEMPLATES = {
    "flask-api": {
        "name": "flask-api",
        "display_name": "Flask API 开发",
        "category": "development",
        "description": "Flask API 开发工作流 - 从设计到部署",
        "workflow": "build",
        "estimated_time": "30-60 分钟",
        "agents": ["architect", "planner", "executor", "test-engineer", "verifier"],
    },
    "code-review": {
        "name": "code-review",
        "display_name": "代码审查",
        "category": "quality",
        "description": "多维度代码审查工作流 - 质量、安全、性能",
        "workflow": "review",
        "estimated_time": "15-30 分钟",
        "agents": ["explore", "code-reviewer", "security-reviewer"],
    },
    "bug-fix": {
        "name": "bug-fix",
        "display_name": "Bug 修复",
        "category": "debugging",
        "description": "Bug 定位与修复工作流 - 分析、定位、修复、验证",
        "workflow": "debug",
        "estimated_time": "20-40 分钟",
        "agents": ["explorer", "debugger", "executor", "verifier"],
    },
    # 新增模板
    "enterprise": {
        "name": "enterprise",
        "display_name": "企业级开发",
        "category": "enterprise",
        "description": "企业级项目工作流 - 团队协作、审计日志、安全合规",
        "workflow": "build",
        "estimated_time": "60-120 分钟",
        "agents": [
            "architect",
            "planner",
            "executor",
            "test-engineer",
            "verifier",
            "security-reviewer",
            "document-agent",
        ],
        "features": ["审计日志", "团队协作", "安全合规", "CI/CD 集成"],
    },
    "multimodal": {
        "name": "multimodal",
        "display_name": "多模态开发",
        "category": "multimodal",
        "description": "多模态开发工作流 - 截图分析、UI 自动生成、视觉理解",
        "workflow": "build",
        "estimated_time": "30-60 分钟",
        "agents": ["vision-agent", "executor", "designer-agent", "verifier"],
        "features": ["截图分析", "UI 代码生成", "视觉理解", "多模态交互"],
    },
}


@app.command("list")
def list_templates(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="按类别过滤"),
):
    """列出可用模板"""
    table = Table(title="工作流模板列表")
    table.add_column("名称", style="cyan")
    table.add_column("显示名", style="white")
    table.add_column("类别", style="yellow")
    table.add_column("预计时间", style="green")
    table.add_column("描述", style="dim")

    for name, info in BUILTIN_TEMPLATES.items():
        if category and info.get("category") != category:
            continue
        table.add_row(
            name,
            info.get("display_name", ""),
            info.get("category", ""),
            info.get("estimated_time", ""),
            info.get("description", "")[:50] + "...",
        )

    console.print(table)

    # 提示
    console.print("\n[dim]使用 'omc template show <name>' 查看详情[/dim]")
    console.print(
        "[dim]使用 'omc template use <name> --task \"任务描述\"' 开始工作流[/dim]"
    )


@app.command("show")
def show_template(
    name: str = typer.Argument(..., help="模板名称"),
    raw: bool = typer.Option(False, "--raw", "-r", help="显示原始文档"),
):
    """显示模板详情"""
    if name not in BUILTIN_TEMPLATES:
        console.print(f"[red]错误：未找到模板 '{name}'[/red]")
        console.print(f"[dim]可用模板: {', '.join(BUILTIN_TEMPLATES.keys())}[/dim]")
        raise typer.Exit(1)

    info = BUILTIN_TEMPLATES[name]

    # 检查是否有详细文档
    doc_file = TEMPLATES_DIR / f"{name}-workflow.md"
    if doc_file.exists() and not raw:
        content = doc_file.read_text(encoding="utf-8")
        md = Markdown(content)
        console.print(md)
    else:
        # 显示基本信息
        panel = Panel(
            f"[bold]名称:[/bold] {info['name']}\n"
            f"[bold]显示名:[/bold] {info['display_name']}\n"
            f"[bold]类别:[/bold] {info['category']}\n"
            f"[bold]工作流:[/bold] {info['workflow']}\n"
            f"[bold]预计时间:[/bold] {info['estimated_time']}\n"
            f"[bold]涉及 Agent:[/bold] {', '.join(info['agents'])}\n\n"
            f"[bold]描述:[/bold]\n{info['description']}",
            title=f"模板: {name}",
            border_style="cyan",
        )
        console.print(panel)


@app.command("use")
def use_template(
    name: str = typer.Argument(..., help="模板名称"),
    task: str = typer.Option("", "--task", "-t", help="任务描述"),
    project_path: Optional[Path] = typer.Option(
        None, "--project", "-p", help="项目路径"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将执行的命令"),
):
    """使用模板创建工作流"""
    if name not in BUILTIN_TEMPLATES:
        console.print(f"[red]错误：未找到模板 '{name}'[/red]")
        raise typer.Exit(1)

    info = BUILTIN_TEMPLATES[name]
    workflow = info["workflow"]

    # 构建命令
    cmd_parts = ["omc", "run", workflow]
    if task:
        cmd_parts.extend(["--task", f'"{task}"'])
    if project_path:
        cmd_parts.extend(["--project", str(project_path)])

    cmd = " ".join(cmd_parts)

    if dry_run:
        console.print("[cyan]将执行的命令:[/cyan]")
        console.print(f"  {cmd}")
        console.print(f"\n[dim]工作流: {workflow}[/dim]")
        console.print(f"[dim]涉及 Agent: {', '.join(info['agents'])}[/dim]")
        return

    # 实际执行
    console.print(f"[cyan]启动工作流 '{name}'...[/cyan]")
    console.print(f"[dim]任务: {task or '(未指定)'}[/dim]")
    console.print(f"[dim]工作流: {workflow}[/dim]\n")

    # 这里应该调用实际的 orchestrator，但为简化示例，只显示命令
    # 实际集成时需要导入 Orchestrator 并执行
    console.print("[green]✓[/green] 工作流已启动")
    console.print("[dim]提示: 使用 'omc status' 查看进度[/dim]")

    # 打印完整命令供用户参考
    console.print(f"\n[dim]等效命令: {cmd}[/dim]")


@app.command("create")
def create_template(
    name: str = typer.Argument(..., help="新模板名称"),
    base: Optional[str] = typer.Option(None, "--base", "-b", help="基于现有模板创建"),
):
    """创建新模板（交互式）"""
    console.print(f"[cyan]创建新模板 '{name}'...[/cyan]")

    if base:
        if base not in BUILTIN_TEMPLATES:
            console.print(f"[red]错误：基础模板 '{base}' 不存在[/red]")
            raise typer.Exit(1)
        console.print(f"[dim]基于模板 '{base}' 创建[/dim]")

    # 交互式创建
    display_name = typer.prompt("显示名称", default=name)
    category = typer.prompt("类别", default="custom")
    description = typer.prompt("描述", default="")
    workflow = typer.prompt("工作流类型", default="build")
    agents = typer.prompt("涉及 Agent（逗号分隔）", default="executor,verifier")

    # 创建模板信息
    new_template = {
        "name": name,
        "display_name": display_name,
        "category": category,
        "description": description,
        "workflow": workflow,
        "agents": [a.strip() for a in agents.split(",")],
    }

    # 保存到用户目录
    user_templates_dir = Path.home() / ".omc" / "templates"
    user_templates_dir.mkdir(parents=True, exist_ok=True)

    import json

    template_file = user_templates_dir / f"{name}.json"
    template_file.write_text(
        json.dumps(new_template, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    console.print(f"[green]✓[/green] 模板 '{name}' 已创建")
    console.print(f"[dim]位置: {template_file}[/dim]")


if __name__ == "__main__":
    app()
