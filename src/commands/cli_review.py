from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
omc review - 代码审查命令

支持两种审查模式：
- omc review pr <url>    # 审查 GitHub PR
- omc review diff <file> # 审查本地 diff 文件
"""

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel

from ..core.router import ModelRouter, RouterConfig

app = typer.Typer(help="代码审查 - 智能分析代码变更")
console = Console()

# 系统提示词路径
SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "review_system.txt"


def _init_router() -> ModelRouter:
    """初始化模型路由器"""
    config = RouterConfig.from_env()
    return ModelRouter(config)


def _check_env() -> bool:
    """检查环境配置"""
    import os

    keys = [
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OLLAMA_BASE_URL",
        "DASHSCOPE_API_KEY",
        "QWEN_API_KEY",
        "XAI_API_KEY",
        "ZHIPUAI_API_KEY",
    ]
    if not any(os.getenv(k) for k in keys):
        console.print(
            "[red]❌ 未检测到任何 API Key，请先配置：[/red]\n"
            "  [cyan]omc self-config set deepseek.api_key sk-xxx[/cyan]"
        )
        return False
    return True


def _fetch_pr_diff(pr_url: str) -> tuple[bool, str]:
    """
    抓取 GitHub PR diff

    返回: (成功, diff内容或错误信息)
    """
    import re

    # 解析 PR URL
    # 格式: https://github.com/{owner}/{repo}/pull/{number}
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url.strip("/")
    )
    if not match:
        return False, f"无效的 GitHub PR URL: {pr_url}"

    owner, repo, pr_number = match.groups()

    # 使用 gh 命令获取 diff
    try:
        result = subprocess.run(
            ["gh", "pr", "diff", pr_number, "--repo", f"{owner}/{repo}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout:
            return True, result.stdout
        # 如果 gh 失败，尝试用 curl
        diff_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}.diff"
        
        resp = httpx.get(diff_url, timeout=15.0)
        if resp.status_code == 200:
            return True, resp.text
        return False, f"无法获取 PR diff: HTTP {resp.status_code}"
    except FileNotFoundError:
        # gh 未安装，直接用 HTTP
        diff_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}.diff"
        
        try:
            resp = httpx.get(diff_url, timeout=15.0)
            if resp.status_code == 200:
                return True, resp.text
            return False, f"无法获取 PR diff: HTTP {resp.status_code}"
        except Exception as e:
            return False, f"网络请求失败: {e}"
    except subprocess.TimeoutExpired:
        return False, "获取 PR diff 超时"
    except Exception as e:
        return False, f"获取失败: {e}"


def _read_local_diff(diff_file: str) -> tuple[bool, str]:
    """
    读取本地 diff 文件

    返回: (成功, diff内容或错误信息)
    """
    diff_path = Path(diff_file)
    
    # 如果是文件路径且存在，读取文件
    if diff_path.exists() and diff_path.is_file():
        try:
            content = diff_path.read_text(encoding="utf-8")
            return True, content
        except Exception as e:
            return False, f"读取文件失败: {e}"

    # 否则尝试作为 git diff 参数执行
    try:
        result = subprocess.run(
            ["git", "diff", diff_file],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, result.stdout
        # git diff 失败，返回错误信息
        return False, f"git diff 失败: {result.stderr}"
    except Exception as e:
        return False, f"执行 git diff 失败: {e}"


def _load_system_prompt() -> str:
    """加载系统提示词"""
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    # 兜底提示词
    return """你是一位资深的代码审查专家。请审查代码变更，按严重程度（高/中/低）分类问题，并提供修复建议。"""


async def _review_with_llm(diff_content: str, model_name: str = "deepseek") -> str:
    """
    使用 LLM 分析 diff 内容

    返回: 审查报告
    """
    router = _init_router()
    system_prompt = _load_system_prompt()

    # 构造消息
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"请审查以下代码变更：\n\n```\n{diff_content}\n```",
        },
    ]

    # 调用模型
    try:
        response = await router.complete(
            messages=messages,
            task_type="code_review",
            model_override=model_name,
        )
        return response.content
    except Exception as e:
        return f"❌ LLM 调用失败: {type(e).__name__}: {e}"


@app.command("pr")
def review_pr(
    pr_url: str = typer.Argument(..., help="GitHub PR URL"),
    model: str = typer.Option("deepseek", "--model", "-m", help="使用的模型"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="保存报告到文件"
    ),
) -> None:
    """
    审查 GitHub PR 内容

    Examples:
        omc review pr https://github.com/user/repo/pull/123
        omc review pr https://github.com/user/repo/pull/456 --model gpt4
    """
    if not _check_env():
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]🔍 代码审查[/bold cyan]\n"
            f"PR: [yellow]{pr_url}[/yellow]\n"
            f"模型: [dim]{model}[/dim]",
            title="📋 PR Review",
        )
    )

    # 获取 diff
    console.print("\n[bold]📥 获取 PR diff...[/bold]")
    success, diff = _fetch_pr_diff(pr_url)
    if not success:
        console.print(f"[red]❌ {diff}[/red]")
        raise typer.Exit(1)

    if not diff.strip():
        console.print("[yellow]⚠️ PR 无变更内容[/yellow]")
        raise typer.Exit(0)

    console.print(f"[green]✓ 获取到 {len(diff.splitlines())} 行 diff[/green]")

    # 调用 LLM 分析
    console.print("\n[bold]🤖 正在分析...[/bold]")

    try:
        report = asyncio.run(_review_with_llm(diff, model))
    except Exception as e:
        console.print(f"[red]❌ 分析失败: {e}[/red]")
        raise typer.Exit(1)

    # 输出报告
    console.print("\n" + "=" * 80)
    console.print(report)
    console.print("=" * 80)

    # 保存到文件
    if output:
        output.write_text(report, encoding="utf-8")
        console.print(f"\n[green]✓ 报告已保存到:[/green] [dim]{output}[/dim]")


@app.command("diff")
def review_diff(
    diff_file: str = typer.Argument(..., help="diff 文件路径或 git diff 参数"),
    model: str = typer.Option("deepseek", "--model", "-m", help="使用的模型"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="保存报告到文件"
    ),
) -> None:
    """
    审查本地代码 diff

    Examples:
        omc review diff changes.diff
        omc review diff HEAD~1
        omc review diff --cached
    """
    if not _check_env():
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]🔍 代码审查[/bold cyan]\n"
            f"Diff: [yellow]{diff_file}[/yellow]\n"
            f"模型: [dim]{model}[/dim]",
            title="📋 Diff Review",
        )
    )

    # 读取 diff
    console.print("\n[bold]📥 读取 diff...[/bold]")
    success, diff = _read_local_diff(diff_file)
    if not success:
        console.print(f"[red]❌ {diff}[/red]")
        raise typer.Exit(1)

    if not diff.strip():
        console.print("[yellow]⚠️ 无变更内容[/yellow]")
        raise typer.Exit(0)

    console.print(f"[green]✓ 读取到 {len(diff.splitlines())} 行 diff[/green]")

    # 调用 LLM 分析
    console.print("\n[bold]🤖 正在分析...[/bold]")

    try:
        report = asyncio.run(_review_with_llm(diff, model))
    except Exception as e:
        console.print(f"[red]❌ 分析失败: {e}[/red]")
        raise typer.Exit(1)

    # 输出报告
    console.print("\n" + "=" * 80)
    console.print(report)
    console.print("=" * 80)

    # 保存到文件
    if output:
        output.write_text(report, encoding="utf-8")
        console.print(f"\n[green]✓ 报告已保存到:[/green] [dim]{output}[/dim]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """默认显示帮助"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
