"""
代码清理 CLI - omc clean 命令

使用示例：
  omc clean                    # 扫描当前目录
  omc clean .                  # 扫描当前目录
  omc clean /path/to/project  # 扫描指定目录
  omc clean --fix             # 扫描并自动修复
  omc clean --aggressive      # 激进模式（自动删除空文件）
  omc clean -o report.md      # 输出报告到文件
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="代码清理工具 - 自动检测和清理冗余代码")
console = Console()


@app.command()
def clean(
    path: str = typer.Argument(".", help="项目路径"),
    fix: bool = typer.Option(False, "--fix", "-f", help="自动修复可修复的问题"),
    strategy: str = typer.Option(
        "safe", "--strategy", "-s", help="策略: safe/aggressive"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="报告输出文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
):
    """
    扫描并清理项目中的冗余代码

    清理策略：
    - 未使用的 import/函数/变量
    - 重复代码片段（>5行）
    - 死代码（无引用）
    - 空文件
    - 过时配置文件
    """
    from .agents.code_cleaner import CleanerStrategy

    project_path = Path(path).resolve()

    if not project_path.exists():
        console.print(f"[red]错误：路径不存在 '{path}'[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]扫描项目: {project_path}[/cyan]")

    # 策略配置
    strategy_obj = CleanerStrategy()
    if strategy == "aggressive":
        console.print("[yellow]激进模式：自动删除空文件[/yellow]")
        strategy_obj.auto_delete_empty = True
        strategy_obj.dead_code_safe_mode = False

    # 导入清理器
    from .agents.code_cleaner import CodeCleaner

    cleaner = CodeCleaner(project_path, strategy_obj)

    # 执行清理
    with console.status("[bold green]扫描中..."):
        report = cleaner.fix_all_auto() if fix else cleaner.scan()

    # 显示报告
    _display_report(report, verbose)

    # 保存报告
    if output:
        report_md = cleaner.generate_report_md(report)
        Path(output).write_text(report_md, encoding="utf-8")
        console.print(f"\n[green]✓[/green] 报告已保存到: {output}")


def _display_report(report, verbose: bool = False):
    """显示清理报告"""
    # 统计信息
    stats_panel = Panel(
        f"**扫描文件**: {report.files_scanned}\n"
        f"**问题总数**: {report.total_issues}\n"
        f"**已修复**: {report.fixed_count}\n"
        f"**待确认**: {report.pending_count}\n"
        f"**预计减少行数**: {report.lines_removed}\n"
        f"**预计节省 Token**: ~{report.estimated_token_savings}",
        title="📊 扫描结果",
        border_style="cyan",
    )
    console.print(stats_panel)

    # 问题类型分布
    if report.by_type:
        table = Table(title="问题类型分布")
        table.add_column("类型", style="yellow")
        table.add_column("数量", style="cyan")

        for issue_type, count in sorted(report.by_type.items(), key=lambda x: -x[1]):
            table.add_row(issue_type, str(count))

        console.print(table)

    # 已修复的文件
    if report.fixed_files:
        console.print("\n[green]✓ 已自动修复:[/green]")
        for f in report.fixed_files[:10]:
            console.print(f"  - {f}")
        if len(report.fixed_files) > 10:
            console.print(f"  ... 还有 {len(report.fixed_files) - 10} 个")

    # 待确认的问题
    if report.pending_issues:
        console.print(f"\n[yellow]⚠ 待确认问题 ({report.pending_count} 个):[/yellow]")
        for issue in report.pending_issues[:20]:
            severity_emoji = {
                "info": "ℹ",
                "warning": "⚠",
                "error": "❌",
            }.get(issue.severity, "?")

            if verbose:
                console.print(
                    f"  {severity_emoji} [{issue.severity}] {issue.file_path}"
                )
                console.print(f"     {issue.content}")
                console.print(f"     → {issue.fix_suggestion}")
            else:
                console.print(
                    f"  {severity_emoji} {issue.file_path}: {issue.content[:60]}"
                )

        if len(report.pending_issues) > 20:
            console.print(f"  ... 还有 {len(report.pending_issues) - 20} 个")

    # 提示
    console.print("\n[dim]提示:[/dim]")
    console.print("  - 使用 --fix 自动修复可修复的问题")
    console.print("  - 使用 --aggressive 激进模式（自动删除空文件）")
    console.print("  - 使用 -o report.md 保存报告")


if __name__ == "__main__":
    app()
