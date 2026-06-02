"""
omc doc 命令 - 文档生成与管理

提供文档生成、验证、同步等功能：
- omc doc generate    # 生成 API 文档
- omc doc check       # 检查文档同步状态
- omc doc serve       # 启动文档本地服务器
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

app = typer.Typer(name="doc", help="文档管理 - 生成、验证、同步项目文档")
console = Console()

DOCS_DIR = Path("docs")
README_PATH = Path("README.md")


@app.command("generate")
def generate_docs(
    output: Path = typer.Option(Path("docs/api"), "--output", "-o", help="输出目录"),
    format: str = typer.Option(
        "markdown", "--format", "-f", help="输出格式: markdown, json"
    ),
):
    """自动生成 API 文档"""
    console.print("[bold blue]📚 生成 API 文档...[/bold blue]")

    output.mkdir(parents=True, exist_ok=True)

    # 收集 CLI 命令信息
    cli_info = _collect_cli_commands()

    # 收集 Web API 端点
    api_info = _collect_web_api()

    if format == "json":
        _write_json_docs(output, cli_info, api_info)
    else:
        _write_markdown_docs(output, cli_info, api_info)

    console.print(f"[green]✅ 文档已生成到 {output}[/green]")


@app.command("check")
def check_docs():
    """检查文档同步状态"""
    console.print("[bold blue]🔍 检查文档同步状态...[/bold blue]")

    issues = []

    # 检查 README 是否存在
    if not README_PATH.exists():
        issues.append("❌ README.md 不存在")

    # 检查 docs 目录结构
    expected_dirs = ["guide", "api", "features", "agents"]
    for d in expected_dirs:
        if not (DOCS_DIR / d).exists():
            issues.append(f"❌ docs/{d}/ 目录缺失")

    # 检查 CLI 命令是否有文档
    cli_commands = _collect_cli_commands()
    for cmd in cli_commands:
        doc_file = DOCS_DIR / "api" / f"{cmd['name']}.md"
        if not doc_file.exists():
            issues.append(f"⚠️ CLI 命令 '{cmd['name']}' 缺少文档")

    # 检查未引用的文档文件（TODO: 实现完整检查）

    if issues:
        console.print(
            Panel("\n".join(issues[:10]), title="发现的问题", border_style="yellow")
        )
        if len(issues) > 10:
            console.print(f"... 还有 {len(issues) - 10} 个问题")
    else:
        console.print("[green]✅ 文档状态良好[/green]")


@app.command("serve")
def serve_docs(
    port: int = typer.Option(8080, "--port", "-p", help="服务端口"),
):
    """启动文档本地预览服务器"""
    import http.server
    import socketserver

    docs_path = DOCS_DIR.resolve()
    if not docs_path.exists():
        console.print("[red]❌ docs/ 目录不存在[/red]")
        raise typer.Exit(1)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(docs_path), **kwargs)

    console.print(f"[green]📖 文档服务器启动: http://localhost:{port}[/green]")
    console.print(f"[dim]   根目录: {docs_path}[/dim]")

    with socketserver.TCPServer(("", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 服务器已停止[/yellow]")


@app.command("index")
def generate_index():
    """生成文档索引"""
    console.print("[bold blue]📑 生成文档索引...[/bold blue]")

    tree = Tree("📚 文档结构")

    for item in sorted(DOCS_DIR.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            branch = tree.add(f"📁 {item.name}/")
            for sub in sorted(item.iterdir()):
                if sub.is_file() and sub.suffix == ".md":
                    branch.add(f"📄 {sub.name}")
        elif item.suffix == ".md":
            tree.add(f"📄 {item.name}")

    console.print(tree)


# ===== 内部函数 =====


def _collect_cli_commands() -> list[dict]:
    """收集 CLI 命令信息"""
    commands = []

    # 从 cli.py 提取命令信息（简化版）
    cli_dir = Path(__file__).parent
    for py_file in cli_dir.glob("cli_*.py"):
        cmd_name = py_file.stem.replace("cli_", "")
        if cmd_name == "doc":
            continue

        # 读取文件提取 help 文本
        help_text = ""
        try:
            content = py_file.read_text(encoding="utf-8")
            # 简单提取 docstring
            if '"""' in content:
                start = content.find('"""') + 3
                end = content.find('"""', start)
                if end > start:
                    help_text = content[start:end].strip().split("\n")[0]
        except Exception:
            pass

        commands.append(
            {
                "name": cmd_name,
                "file": py_file.name,
                "help": help_text or f"{cmd_name} 命令",
            }
        )

    return sorted(commands, key=lambda x: x["name"])


def _collect_web_api() -> list[dict]:
    """收集 Web API 端点信息"""
    endpoints: list[dict] = []

    web_app = Path("src/web/app.py")
    if not web_app.exists():
        return endpoints

    try:
        content = web_app.read_text(encoding="utf-8")
        import re

        # 匹配 @app.get/post/put/delete 装饰器
        pattern = r'@app\.(get|post|put|delete)\(["\']([^"\']+)["\']'
        for match in re.finditer(pattern, content):
            method = match.group(1).upper()
            path = match.group(2)
            endpoints.append(
                {
                    "method": method,
                    "path": path,
                }
            )
    except Exception:
        pass

    return endpoints


def _write_markdown_docs(output: Path, cli_info: list, api_info: list):
    """写入 Markdown 格式文档"""
    # CLI 命令文档
    cli_md = output / "cli-commands.md"
    with cli_md.open("w", encoding="utf-8") as f:
        f.write("# CLI 命令参考\n\n")
        f.write("自动生成于 `omc doc generate`\n\n")
        f.write("| 命令 | 说明 | 文件 |\n")
        f.write("|------|------|------|\n")
        for cmd in cli_info:
            f.write(f"| `{cmd['name']}` | {cmd['help']} | `{cmd['file']}` |\n")

    # Web API 文档
    api_md = output / "web-api.md"
    with api_md.open("w", encoding="utf-8") as f:
        f.write("# Web API 参考\n\n")
        f.write("自动生成于 `omc doc generate`\n\n")
        f.write("| 方法 | 路径 |\n")
        f.write("|------|------|\n")
        for ep in api_info:
            f.write(f"| `{ep['method']}` | `{ep['path']}` |\n")

    console.print(f"  [dim]写入 {cli_md}[/dim]")
    console.print(f"  [dim]写入 {api_md}[/dim]")


def _write_json_docs(output: Path, cli_info: list, api_info: list):
    """写入 JSON 格式文档"""
    data = {
        "cli_commands": cli_info,
        "web_api": api_info,
        "generated_at": str(Path().cwd()),
    }

    json_path = output / "api-reference.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    console.print(f"  [dim]写入 {json_path}[/dim]")
