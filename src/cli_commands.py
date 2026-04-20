"""
Markdown 命令系统 - .omc/commands/

支持在 .omc/commands/ 目录存放命令文件，
使用 $参数 语法进行参数替换。

文件格式:
---
name: 命令名称
description: 命令描述
usage: omc cmd <arg1> <arg2>
---
#!/omc-command
echo "Hello $1"
echo "Project: $PROJECT"
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Markdown 命令系统 - 运行自定义命令")
console = Console()

# 命令目录
COMMANDS_DIR = Path.cwd() / ".omc" / "commands"


class Command:
    """命令定义"""

    def __init__(self, name: str, path: Path, content: str):
        self.name = name
        self.path = path
        self.content = content
        self.frontmatter = self._parse_frontmatter()
        self.script = self._extract_script()

    def _parse_frontmatter(self) -> Dict[str, str]:
        """解析 YAML frontmatter"""
        frontmatter = {}

        # 匹配 ---...--- 块
        match = re.match(r"^---\n(.*?)\n---", self.content, re.DOTALL)
        if match:
            yaml_content = match.group(1)
            for line in yaml_content.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip()

        return frontmatter

    def _extract_script(self) -> str:
        """提取命令脚本"""
        script = self.content

        # 移除 ---...--- 块
        script = re.sub(r"^---\n.*?\n---\n", "", script, flags=re.DOTALL)

        # 移除 shebang
        script = script.lstrip()
        if script.startswith("#!"):
            lines = script.splitlines()
            script = "\n".join(lines[1:])

        return script.strip()

    def description(self) -> str:
        return self.frontmatter.get("description", "")

    def usage(self) -> str:
        return self.frontmatter.get("usage", f"omc cmd {self.name}")

    def render_usage(self, args: List[str]) -> str:
        """渲染命令脚本，支持变量替换"""
        script = self.script

        # $1, $2, ... 位置参数
        for i, arg in enumerate(args):
            script = script.replace(f"${i + 1}", arg)

        # $@ 所有参数
        script = script.replace("$@", " ".join(args))

        # 环境变量
        env_vars = {
            "PROJECT": os.environ.get("PROJECT", Path.cwd().name),
            "CWD": os.getcwd(),
            "HOME": os.path.expanduser("~"),
            "DATE": os.popen("date '+%Y-%m-%d'").read().strip(),
            "TIME": os.popen("date '+%H:%M:%S'").read().strip(),
        }

        for var, value in env_vars.items():
            script = script.replace(f"${var}", value)

        return script


def load_commands() -> Dict[str, Command]:
    """加载所有命令"""
    commands = {}

    if not COMMANDS_DIR.exists():
        COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
        _create_example_commands()
        return commands

    for path in COMMANDS_DIR.glob("*.md"):
        try:
            content = path.read_text()
            name = path.stem
            commands[name] = Command(name, path, content)
        except Exception as e:
            console.print(f"[yellow]警告: 加载命令 {path.name} 失败: {e}[/yellow]")

    return commands


def _create_example_commands():
    """创建示例命令"""
    examples = {
        "hello": """---
name: hello
description: 简单的问候命令
usage: omc cmd hello <名字>
---
#!/omc-command
echo "Hello $1!"
echo "当前项目: $PROJECT"
echo "时间: $DATE $TIME"
""",
        "deploy": """---
name: deploy
description: 部署应用到服务器
usage: omc cmd deploy <环境>
---
#!/omc-command
echo "部署到 $1 环境..."
echo "项目: $PROJECT"
echo "目录: $CWD"

# 示例部署脚本
# git push origin main
# ./deploy.sh $1
""",
        "test": """---
name: test
description: 运行测试
usage: omc cmd test [选项]
---
#!/omc-command
echo "运行测试..."
echo "项目: $PROJECT"

# 运行 pytest
python3 -m pytest tests/ -v

# 或者运行单元测试
# python3 -m unittest discover -s tests
""",
        "clean": """---
name: clean
description: 清理项目
usage: omc cmd clean
---
#!/omc-command
echo "清理项目..."
echo "目录: $CWD"

# 清理 Python 缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null

# 清理 node_modules (可选)
# find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null

echo "清理完成!"
""",
    }

    for name, content in examples.items():
        path = COMMANDS_DIR / f"{name}.md"
        if not path.exists():
            path.write_text(content)

    console.print(f"[dim]已创建示例命令到 {COMMANDS_DIR}[/dim]")


@app.command()
def run(
    name: str = typer.Argument(..., help="命令名称"),
    args: Optional[List[str]] = typer.Argument(None, help="命令参数"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅显示将要执行的命令"),
):
    if args is None:
        args = []
    """
    运行自定义命令

    示例:
        omc cmd run hello 世界
        omc cmd run deploy production
        omc cmd run test --dry-run
    """
    commands = load_commands()

    if name not in commands:
        console.print(f"[red]命令未找到: {name}[/red]")
        console.print("\n可用命令:")
        for cmd_name, cmd in commands.items():
            console.print(f"  • {cmd_name}: {cmd.description()}")
        return

    cmd = commands[name]
    rendered = cmd.render_usage(args)

    if dry_run:
        console.print(
            Panel.fit(
                f"[cyan]命令:[/cyan] {name}\n"
                f"[cyan]参数:[/cyan] {' '.join(args)}\n\n"
                f"[cyan]将要执行:[/cyan]\n"
                f"[yellow]{rendered}[/yellow]",
                title="Dry Run",
                border_style="yellow",
            )
        )
        return

    # 执行脚本
    console.print(f"\n[cyan]执行命令: {name}[/cyan]")
    console.print(f"[dim]{' '.join(args)}[/dim]\n")

    try:
        result = subprocess.run(
            rendered,
            shell=True,
            cwd=os.getcwd(),
            capture_output=False,
            text=True,
        )

        if result.returncode != 0:
            console.print(f"\n[red]命令执行失败 (退出码: {result.returncode})[/red]")
    except Exception as e:
        console.print(f"[red]执行错误: {e}[/red]")


@app.command("list")
def list_commands():
    """列出所有可用命令"""
    commands = load_commands()

    if not commands:
        console.print("[yellow]没有找到任何命令[/yellow]")
        console.print(f"\n创建命令文件到: {COMMANDS_DIR}")
        console.print("[dim]示例: .omc/commands/hello.md[/dim]")
        return

    table = Table(title=f"自定义命令 (共 {len(commands)} 个)")
    table.add_column("名称", style="cyan")
    table.add_column("描述", style="white")
    table.add_column("用法", style="dim")

    for name, cmd in commands.items():
        table.add_row(name, cmd.description(), cmd.usage())

    console.print(table)
    console.print(f"\n[dim]命令目录: {COMMANDS_DIR}[/dim]")


@app.command("create")
def create_command(
    name: str = typer.Argument(..., help="命令名称"),
    description: str = typer.Option("", "--description", "-d", help="命令描述"),
):
    """创建新命令"""
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)

    path = COMMANDS_DIR / f"{name}.md"

    if path.exists():
        console.print(f"[red]命令已存在: {name}[/red]")
        return

    content = f"""---
name: {name}
description: {description or '自定义命令'}
usage: omc cmd run {name} <参数>
---
#!/omc-command
echo "执行 {name} 命令"
echo "参数: $@"
echo "项目: $PROJECT"
"""

    path.write_text(content)
    console.print(f"[green]✅ 已创建命令: {name}[/green]")
    console.print(f"[dim]文件: {path}[/dim]")


@app.command("edit")
def edit_command(
    name: str = typer.Argument(..., help="命令名称"),
):
    """编辑命令"""
    commands = load_commands()

    if name not in commands:
        console.print(f"[red]命令未找到: {name}[/red]")
        return

    cmd = commands[name]
    path = cmd.path

    console.print(f"[cyan]编辑命令: {name}[/cyan]")
    console.print(f"[dim]文件: {path}[/dim]")

    # 打开编辑器
    editor = os.environ.get("EDITOR", "vim")
    subprocess.run([editor, str(path)])


if __name__ == "__main__":
    app()
