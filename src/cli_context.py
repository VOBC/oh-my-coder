from __future__ import annotations

"""
Context CLI - 工作目录上下文管理命令

子命令：
- omc context scan      # 扫描当前工作目录
- omc context summary  # 生成文件摘要
- omc context browser  # 获取浏览器上下文
- omc context tree     # 显示文件树
"""

import asyncio
from pathlib import Path

import typer

from .context import BrowserAwareness, FileNode, WorkspaceScanner

context_app = typer.Typer(
    name="context",
    help="工作目录上下文管理 — 扫描文件、获取摘要、感知浏览器",
    add_completion=False,
    no_args_is_help=True,
)


@context_app.command("scan")
def scan(
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="项目路径",
    ),
    depth: int = typer.Option(3, "--depth", "-d", help="扫描深度（最大递归层数）"),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="以 JSON 格式输出（便于程序解析）"
    ),
):
    """
    扫描当前工作目录，生成文件树结构

    示例：
        omc context scan
        omc context scan -p /path/to/project -d 2
        omc context scan --depth 5
        omc context scan --json
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    scanner = WorkspaceScanner(project_path.resolve())

    # 执行扫描
    tree = scanner.scan(max_depth=depth)
    stats = scanner._scan_stats

    if json_output:
        import json

        console.print(
            json.dumps(
                {
                    "tree": tree.to_dict(),
                    "stats": {
                        "files_scanned": stats["files_scanned"],
                        "dirs_scanned": stats["dirs_scanned"],
                        "bytes_scanned": stats["bytes_scanned"],
                        "errors": stats["errors"],
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # 渲染文件树
    lines = scanner._render_tree(tree, prefix="", is_last=True)
    tree_str = "\n".join(lines)

    # 格式化统计
    size_str = scanner._format_size(stats["bytes_scanned"])

    console.print(
        Panel(
            f"[bold cyan]{project_path.name}[/bold cyan] ({project_path})\n"
            f"[dim]深度: {depth} | "
            f"文件: {stats['files_scanned']} | "
            f"目录: {stats['dirs_scanned']} | "
            f"大小: {size_str}[/dim]",
            title="📁 工作目录扫描",
            border_style="cyan",
        )
    )

    console.print(f"\n[white]{tree_str}[/white]\n")

    # 错误提示
    if stats["errors"]:
        console.print(f"[yellow]⚠️  {len(stats['errors'])} 个错误[/yellow]")
        for err in stats["errors"][:5]:
            console.print(f"  [dim]{err}[/dim]")
        if len(stats["errors"]) > 5:
            console.print(f"  [dim]... 共 {len(stats['errors'])} 个[/dim]")


@context_app.command("summary")
def summary(
    path: str = typer.Argument(..., help="文件或目录路径"),
    max_lines: int = typer.Option(50, "--lines", "-n", help="最大读取行数"),
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="项目根目录（用于计算相对路径）",
    ),
):
    """
    生成文件摘要

    显示指定文件的内容摘要，包括：
    - 基本信息（大小、修改时间）
    - 代码结构（导入、类、函数）
    - 内容预览

    示例：
        omc context summary src/main.py
        omc context summary config.yaml -n 100
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax

    console = Console()
    scanner = WorkspaceScanner(project_path.resolve())

    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = project_path / file_path

    if not file_path.exists():
        console.print(f"[red]✗ 文件不存在: {file_path}[/red]")
        raise typer.Exit(1)

    result = scanner.get_file_summary(file_path, max_lines=max_lines)

    # 解析摘要结果
    lines = result.split("\n")
    header_lines = []
    content_lines = []
    in_content = False

    for line in lines:
        if line.startswith("---"):
            in_content = True
            continue
        if in_content:
            content_lines.append(line)
        else:
            header_lines.append(line)

    header = "\n".join(header_lines)
    content = "\n".join(content_lines)

    # 检测语言用于语法高亮
    lang = None
    for line in header_lines:
        if line.startswith("["):
            lang = line.split("]")[0][1:]
            break

    console.print(Panel(header, title=f"📄 {file_path.name}", border_style="green"))

    if content_lines:
        # 如果是代码，尝试语法高亮
        if lang and lang not in ("unknown", "markdown", "rst"):
            try:
                syntax = Syntax(content, lang, theme="monokai", line_numbers=True)
                console.print(syntax)
            except Exception:
                console.print(content)
        else:
            console.print(content)


@context_app.command("browser")
def browser_cmd(
    watch: bool = typer.Option(
        False, "--watch", "-w", help="持续监控浏览器变化（Ctrl+C 退出）"
    ),
    interval: int = typer.Option(5, "--interval", "-i", help="监控间隔（秒）"),
):
    """
    获取浏览器当前上下文

    读取当前浏览器标签页的标题、URL 和内容摘要。
    需要安装 Playwright 或 Selenium。

    示例：
        omc context browser
        omc context browser --watch
    """
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    awareness = BrowserAwareness()

    async def get_and_display():
        ctx = await awareness.get_current_tab()

        if not ctx.available:
            console.print(
                Panel(
                    "[yellow]浏览器上下文不可用[/yellow]\n\n"
                    "[dim]可能的原因：\n"
                    "  1. 未安装 Playwright 或 Selenium\n"
                    "  2. 没有活跃的浏览器标签页\n"
                    "  3. 浏览器拒绝了 CDP 连接[/dim]",
                    title="🌐 浏览器上下文",
                    border_style="yellow",
                )
            )
            return

        # 显示链接列表
        links_text = ""
        if ctx.links:
            links_text = "\n\n[cyan]链接预览:[/cyan]\n"
            for link in ctx.links[:10]:
                links_text += f"  • {link}\n"

        console.print(
            Panel(
                f"[bold]{ctx.title}[/bold]\n"
                f"[dim]{ctx.url}[/dim]\n\n"
                f"[green]内容摘要:[/green]\n"
                f"{ctx.content[:500]}"
                + ("..." if len(ctx.content) > 500 else "")
                + links_text,
                title="🌐 浏览器上下文",
                border_style="green",
            )
        )

    async def watch_loop():
        console.print("[dim]持续监控浏览器，按 Ctrl+C 退出...[/dim]\n")
        try:
            while True:
                console.clear()
                await get_and_display()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            console.print("\n[dim]监控已退出[/dim]")

    if watch:
        asyncio.run(watch_loop())
    else:
        asyncio.run(get_and_display())


@context_app.command("tree")
def tree(
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="项目路径",
    ),
    depth: int = typer.Option(3, "--depth", "-d", help="显示深度"),
    filter_ext: str = typer.Option(
        None, "--ext", "-e", help="只显示特定扩展名（如 py, js）"
    ),
):
    """
    显示文件树

    以树形结构显示项目目录，类似于 tree 命令。

    示例：
        omc context tree
        omc context tree -p src -d 2
        omc context tree --ext py
    """
    from rich.console import Console
    from rich.tree import Tree

    console = Console()

    scanner = WorkspaceScanner(project_path.resolve())
    tree_node = scanner.scan(max_depth=depth)

    def build_rich_tree(node: "FileNode", filter_ext: str | None = None) -> Tree:
        """构建 rich Tree"""
        label = f"[cyan]{node.name}[/cyan]"
        if node.language:
            label += f" [dim][[{node.language}]][/dim]"
        if node.size > 0 and not node.is_dir:
            label += f" [dim]({scanner._format_size(node.size)})[/dim]"

        t = Tree(label)

        if node.is_dir and node.children:
            for child in node.children:
                if filter_ext:
                    ext = filter_ext.lstrip(".").lower()
                    child_lang = scanner.LANGUAGE_EXTENSIONS.get(f".{ext}")
                    if child.is_dir or child.language == child_lang:
                        t.add(build_rich_tree(child, filter_ext))
                else:
                    t.add(build_rich_tree(child, filter_ext))

        return t

    console.print(
        build_rich_tree(tree_node, filter_ext),
        soft_wrap=True,
    )


@context_app.command("stats")
def stats(
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project",
        "-p",
        help="项目路径",
    ),
):
    """
    显示项目统计信息

    统计项目的文件数量、代码行数、各语言占比等信息。

    示例：
        omc context stats
        omc context stats -p /path/to/project
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    scanner = WorkspaceScanner(project_path.resolve())

    # 扫描两次（一次深度大，一次深度小）
    tree = scanner.scan(max_depth=10)

    # 统计各语言文件数和行数
    lang_stats: dict = {}

    def collect_stats(node: "FileNode"):
        if node.is_dir:
            for child in node.children:
                collect_stats(child)
        else:
            lang = node.language or "other"
            if lang not in lang_stats:
                lang_stats[lang] = {"files": 0, "lines": 0, "size": 0}

            lang_stats[lang]["files"] += 1
            lang_stats[lang]["size"] += node.size

            # 统计行数
            try:
                with open(node.path, encoding="utf-8", errors="replace") as f:
                    lang_stats[lang]["lines"] += sum(1 for _ in f if _.strip())
            except Exception:
                pass

    collect_stats(tree)

    # 按文件数排序
    sorted_langs = sorted(
        lang_stats.items(),
        key=lambda x: x[1]["files"],
        reverse=True,
    )

    # 统计表
    table = Table(title="语言统计")
    table.add_column("语言", style="cyan")
    table.add_column("文件", justify="right")
    table.add_column("行数", justify="right")
    table.add_column("大小", justify="right")

    total_files = sum(s["files"] for _, s in sorted_langs)
    total_lines = sum(s["lines"] for _, s in sorted_langs)
    total_size = sum(s["size"] for _, s in sorted_langs)

    for lang, s in sorted_langs[:15]:
        table.add_row(
            lang,
            str(s["files"]),
            f"{s['lines']:,}",
            scanner._format_size(s["size"]),
        )

    console.print(
        Panel(
            f"[cyan]项目:[/cyan] {project_path}\n"
            f"[cyan]文件:[/cyan] {total_files} 个\n"
            f"[cyan]代码行数:[/cyan] {total_lines:,} 行\n"
            f"[cyan]总大小:[/cyan] {scanner._format_size(total_size)}",
            title="📊 项目统计",
            border_style="green",
        )
    )
    console.print(table)
