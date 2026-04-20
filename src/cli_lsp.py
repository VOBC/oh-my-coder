"""
LSP 集成 - AI 可读取 diagnostics

支持从 VSCode ESLint/Pylance 等 Language Server 获取代码诊断信息。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="LSP 集成 - 读取代码诊断信息")
console = Console()


# LSP 诊断级别
class DiagnosticSeverity:
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


SEVERITY_NAMES = {
    1: "[red]错误[/red]",
    2: "[yellow]警告[/yellow]",
    3: "[blue]信息[/blue]",
    4: "[dim]提示[/dim]",
}


def find_lsp_diagnostics(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    查找 LSP 诊断信息

    支持的诊断来源:
    1. VSCode .vscode/problems.json
    2. ESLint JSON 格式输出
    3. Pylance/ruff 等工具的 JSON 输出
    """
    diagnostics = []
    root = Path.cwd()

    # 1. VSCode problems.json
    vscode_dir = root / ".vscode"
    if vscode_dir.exists():
        problems_file = vscode_dir / "problems.json"
        if problems_file.exists():
            try:
                problems = json.loads(problems_file.read_text())
                for problem in problems.get("problems", []):
                    diagnostics.append(
                        {
                            "source": "VSCode",
                            "file": problem.get("file", ""),
                            "line": problem.get("line", 0),
                            "column": problem.get("column", 0),
                            "severity": problem.get("severity", 2),
                            "message": problem.get("message", ""),
                            "rule": problem.get("ruleId", ""),
                        }
                    )
            except Exception:
                pass

    # 2. ESLint 检查结果
    eslint_output = root / ".eslint-results.json"
    if eslint_output.exists():
        try:
            eslint_results = json.loads(eslint_output.read_text())
            for result in eslint_results:
                file_name = result.get("filePath", "")
                for msg in result.get("messages", []):
                    diagnostics.append(
                        {
                            "source": "ESLint",
                            "file": file_name,
                            "line": msg.get("line", 0),
                            "column": msg.get("column", 0),
                            "severity": msg.get("severity", 1),
                            "message": msg.get("message", ""),
                            "rule": msg.get("ruleId", ""),
                        }
                    )
        except Exception:
            pass

    # 3. ruff 检查结果 (如果可用)
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", "."],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=root,
        )
        if result.stdout:
            ruff_results = json.loads(result.stdout)
            for issue in ruff_results:
                diagnostics.append(
                    {
                        "source": "ruff",
                        "file": issue.get("filename", ""),
                        "line": issue.get("location", {}).get("row", 0),
                        "column": issue.get("location", {}).get("column", 0),
                        "severity": 2,  # ruff 默认是 warning
                        "message": issue.get("message", ""),
                        "rule": issue.get("code", ""),
                    }
                )
    except Exception:
        pass

    # 4. mypy 检查结果 (如果可用)
    try:
        result = subprocess.run(
            ["mypy", "--output-format=json", "."],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=root,
        )
        if result.stdout:
            mypy_results = json.loads(result.stdout)
            for issue in mypy_results:
                diagnostics.append(
                    {
                        "source": "mypy",
                        "file": issue.get("file", ""),
                        "line": issue.get("line", 0),
                        "column": issue.get("column", 0),
                        "severity": 1 if issue.get("severity") == "error" else 2,
                        "message": issue.get("message", ""),
                        "rule": "type-error",
                    }
                )
    except Exception:
        pass

    # 过滤指定文件
    if file_path:
        diagnostics = [d for d in diagnostics if file_path in d.get("file", "")]

    # 按严重程度排序
    diagnostics.sort(key=lambda x: x.get("severity", 999))

    return diagnostics


def format_diagnostics_for_ai(diagnostics: List[Dict[str, Any]]) -> str:
    """格式化诊断信息为 AI 可读的格式"""
    if not diagnostics:
        return "✅ 未发现代码问题"

    lines = ["## 代码诊断报告\n"]

    # 按文件分组
    by_file: Dict[str, List[Dict]] = {}
    for d in diagnostics:
        file_name = os.path.basename(d.get("file", "unknown"))
        if file_name not in by_file:
            by_file[file_name] = []
        by_file[file_name].append(d)

    for file_name, issues in by_file.items():
        lines.append(f"\n### {file_name}\n")

        for issue in issues:
            severity = SEVERITY_NAMES.get(issue.get("severity", 2), "[dim]未知[/dim]")
            line = issue.get("line", 0)
            message = issue.get("message", "")
            rule = issue.get("rule", "")
            source = issue.get("source", "")

            lines.append(f"- {severity} **L{line}**: {message}")
            if rule:
                lines.append(f"  - 规则: `{rule}` ({source})")

    lines.append(f"\n---\n**总计**: {len(diagnostics)} 个问题")

    # 统计
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for d in diagnostics:
        counts[d.get("severity", 2)] = counts.get(d.get("severity", 2), 0) + 1

    lines.append(f"- 🔴 错误: {counts.get(1, 0)}")
    lines.append(f"- 🟡 警告: {counts.get(2, 0)}")
    lines.append(f"- 🔵 信息: {counts.get(3, 0)}")

    return "\n".join(lines)


@app.command()
def check(
    file: Optional[str] = typer.Option(None, "--file", "-f", help="指定文件"),
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="指定诊断来源 (ruff/mypy/eslint)"
    ),
    format: str = typer.Option(
        "table", "--format", "-o", help="输出格式 (table/ai/json)"
    ),
):
    """
    检查代码诊断信息

    示例:
        omc lsp check
        omc lsp check --file src/main.py
        omc lsp check --source ruff --format ai
    """
    console.print("\n[cyan]🔍 代码诊断检查[/cyan]\n")

    diagnostics = find_lsp_diagnostics(file)

    if source:
        diagnostics = [
            d for d in diagnostics if d.get("source", "").lower() == source.lower()
        ]

    if not diagnostics:
        console.print("[green]✅ 未发现代码问题[/green]")
        return

    if format == "ai":
        # AI 友好的格式
        output = format_diagnostics_for_ai(diagnostics)
        console.print(Panel.fit(output, title="诊断报告", border_style="cyan"))
    elif format == "json":
        # JSON 格式
        console.print_json(data=diagnostics)
    else:
        # 表格格式
        table = Table(title=f"诊断结果 (共 {len(diagnostics)} 项)")
        table.add_column("级别", style="cyan", width=10)
        table.add_column("文件", style="white")
        table.add_column("行", style="cyan", width=4)
        table.add_column("消息", style="white")
        table.add_column("规则", style="dim")

        for d in diagnostics[:100]:  # 限制显示100条
            severity = SEVERITY_NAMES.get(d.get("severity", 2), "未知")
            file_name = os.path.basename(d.get("file", ""))
            line = str(d.get("line", ""))
            message = d.get("message", "")[:60]
            rule = d.get("rule", "")

            table.add_row(severity, file_name, line, message, rule)

        console.print(table)

        if len(diagnostics) > 100:
            console.print(f"\n[dim]... 还有 {len(diagnostics) - 100} 条未显示[/dim]")

    # 统计
    console.print("\n[bold]统计:[/bold]")
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for d in diagnostics:
        sev = d.get("severity", 2)
        counts[sev] = counts.get(sev, 0) + 1

    console.print(f"  🔴 错误: {counts.get(1, 0)}")
    console.print(f"  🟡 警告: {counts.get(2, 0)}")
    console.print(f"  🔵 信息: {counts.get(3, 0)}")


@app.command()
def fix(
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run", help="是否仅显示修复建议"
    ),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="指定修复工具"),
):
    """
    自动修复代码问题

    示例:
        omc lsp fix                    # 仅显示修复建议
        omc lsp fix --no-dry-run       # 执行修复
        omc lsp fix --source ruff      # 使用 ruff 修复
    """
    console.print("\n[cyan]🔧 代码修复[/cyan]\n")

    if dry_run:
        console.print("[yellow]Dry Run 模式 - 仅显示修复建议[/yellow]\n")

    # ruff 自动修复
    if not source or source == "ruff":
        console.print("[cyan]运行 ruff 检查...[/cyan]")
        try:
            cmd = ["ruff", "check", "."]
            if dry_run:
                cmd.append("--preview")  # 预览模式

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path.cwd(),
            )

            if result.stdout:
                console.print(result.stdout)

            if not dry_run and result.returncode == 0:
                # 执行自动修复
                console.print("\n[cyan]执行自动修复...[/cyan]")
                fix_result = subprocess.run(
                    ["ruff", "check", "--fix", "."],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=Path.cwd(),
                )
                if fix_result.returncode == 0:
                    console.print("[green]✅ ruff 修复完成[/green]")
                else:
                    console.print(f"[red]修复失败: {fix_result.stderr}[/red]")
        except FileNotFoundError:
            console.print("[yellow]ruff 未安装，跳过[/yellow]")
        except Exception as e:
            console.print(f"[red]ruff 执行失败: {e}[/red]")


@app.command()
def setup(
    tool: str = typer.Argument(..., help="设置工具 (ruff/mypy/eslint)"),
):
    """
    快速设置 LSP 工具

    示例:
        omc lsp setup ruff
        omc lsp setup mypy
    """
    console.print(f"\n[cyan]设置 {tool}[/cyan]\n")

    if tool == "ruff":
        _setup_ruff()
    elif tool == "mypy":
        _setup_mypy()
    elif tool == "eslint":
        _setup_eslint()
    else:
        console.print(f"[red]不支持的工具: {tool}[/red]")


def _setup_ruff():
    """设置 ruff"""
    try:
        # 检查是否已安装
        subprocess.run(["ruff", "--version"], capture_output=True, check=True)

        # 创建 ruff.toml
        config_file = Path.cwd() / "ruff.toml"
        if config_file.exists():
            console.print("[yellow]ruff.toml 已存在[/yellow]")
        else:
            config_file.write_text(
                """
# Ruff - Python linter and formatter
line-length = 100
target-version = "py39"

[lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[lint.isort]
known-first-party = ["src"]
"""
            )
            console.print("[green]✅ 已创建 ruff.toml[/green]")

        console.print("\n[cyan]运行 ruff check --fix 自动修复...[/cyan]")
        subprocess.run(["ruff", "check", "--fix", "."], capture_output=True)
        console.print("[green]✅ ruff 设置完成[/green]")

    except FileNotFoundError:
        console.print("[red]ruff 未安装[/red]")
        console.print("安装方式:")
        console.print("  pip install ruff")
        console.print("  omc pkg install ruff")


def _setup_mypy():
    """设置 mypy"""
    try:
        subprocess.run(["mypy", "--version"], capture_output=True, check=True)

        config_file = Path.cwd() / "mypy.ini"
        if config_file.exists():
            console.print("[yellow]mypy.ini 已存在[/yellow]")
        else:
            config_file.write_text(
                """
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
"""
            )
            console.print("[green]✅ 已创建 mypy.ini[/green]")

    except FileNotFoundError:
        console.print("[red]mypy 未安装[/red]")
        console.print("安装方式:")
        console.print("  pip install mypy")
        console.print("  omc pkg install mypy")


def _setup_eslint():
    """设置 ESLint"""
    try:
        subprocess.run(["npx", "eslint", "--version"], capture_output=True, check=True)

        console.print("[green]✅ ESLint 已配置[/green]")
        console.print("\n运行 ESLint:")
        console.print("  npx eslint .")

    except FileNotFoundError:
        console.print("[red]ESLint 未安装[/red]")
        console.print("安装方式:")
        console.print("  npm install -g eslint")
        console.print("  omc pkg install eslint")


if __name__ == "__main__":
    app()
