"""
多平台包管理器 - omc pkg

支持 Homebrew/npm/scoop/winget/AUR 等包管理器，
统一安装和管理开发工具。

Usage:
    omc pkg install <package>    # 安装包
    omc pkg search <query>      # 搜索包
    omc pkg list                # 列出已安装
    omc pkg update              # 更新包
"""

from __future__ import annotations

import platform
import subprocess
from enum import Enum

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="多平台包管理器 - 统一管理 Homebrew/npm/scoop/winget/AUR")
console = Console()


class Platform(Enum):
    """支持的平台"""

    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"


class PackageManager(Enum):
    """包管理器"""

    HOMEBREW = "homebrew"
    NPM = "npm"
    PIP = "pip"
    SCOOP = "scoop"
    WINGET = "winget"
    AUR = "aur"
    YARN = "yarn"
    PNPM = "pnpm"


def get_current_platform() -> Platform:
    """获取当前平台"""
    system = platform.system().lower()
    if system == "darwin":
        return Platform.MACOS
    if system == "linux":
        return Platform.LINUX
    if system == "windows":
        return Platform.WINDOWS
    return Platform.LINUX


def get_available_managers() -> list[PackageManager]:
    """获取可用的包管理器"""
    available = []
    system = get_current_platform()

    # 检查各包管理器是否可用
    managers = [
        (PackageManager.NPM, "npm"),
        (PackageManager.YARN, "yarn"),
        (PackageManager.PNPM, "pnpm"),
        (PackageManager.PIP, "pip3"),
    ]

    if system == Platform.MACOS:
        managers.extend(
            [
                (PackageManager.HOMEBREW, "brew"),
            ]
        )
    elif system == Platform.LINUX:
        managers.extend(
            [
                (PackageManager.AUR, "yay"),
            ]
        )
    elif system == Platform.WINDOWS:
        managers.extend(
            [
                (PackageManager.SCOOP, "scoop"),
                (PackageManager.WINGET, "winget"),
            ]
        )

    for manager, cmd in managers:
        if _is_command_available(cmd):
            available.append(manager)

    return available


def _is_command_available(cmd: str) -> bool:
    """检查命令是否可用"""
    try:
        result = subprocess.run(
            ["which", cmd] if platform.system() != "Windows" else ["where", cmd],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _run_command(cmd: list[str], capture: bool = True) -> tuple:
    """运行命令"""
    try:
        if capture:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0, result.stdout, result.stderr
        result = subprocess.run(cmd, timeout=60)
        return result.returncode == 0, "", ""
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception:
        return False, "", "unavailable"


# 常用开发工具推荐
RECOMMENDED_PACKAGES = {
    "cli": [
        {
            "name": "git",
            "desc": "版本控制",
            "managers": ["brew", "scoop", "winget", "aur"],
        },
        {"name": "gh", "desc": "GitHub CLI", "managers": ["brew", "scoop", "winget"]},
        {"name": "lazygit", "desc": "终端 Git 客户端", "managers": ["brew", "scoop"]},
        {"name": "delta", "desc": "Git 差异查看器", "managers": ["brew", "scoop"]},
        {"name": "fzf", "desc": "命令行模糊搜索", "managers": ["brew", "scoop", "aur"]},
        {
            "name": "ripgrep",
            "desc": "快速搜索工具",
            "managers": ["brew", "scoop", "winget"],
        },
        {"name": "fd", "desc": "快速文件查找", "managers": ["brew", "scoop"]},
        {"name": "bat", "desc": "cat 替代品", "managers": ["brew", "scoop", "winget"]},
        {"name": "exa", "desc": "ls 替代品", "managers": ["brew", "scoop"]},
        {"name": "htop", "desc": "系统监控", "managers": ["brew", "aur"]},
        {"name": "tldr", "desc": "简化 man 手册", "managers": ["brew", "scoop", "pip"]},
        {"name": "httpie", "desc": "HTTP 客户端", "managers": ["brew", "pip", "scoop"]},
        {
            "name": "jq",
            "desc": "JSON 处理",
            "managers": ["brew", "scoop", "winget", "aur"],
        },
        {"name": "yq", "desc": "YAML 处理", "managers": ["brew", "scoop"]},
        {"name": "tree", "desc": "目录树", "managers": ["brew", "scoop", "winget"]},
    ],
    "dev": [
        {"name": "node", "desc": "Node.js 运行时", "managers": ["brew"]},
        {"name": "python", "desc": "Python 解释器", "managers": ["brew"]},
        {"name": "go", "desc": "Go 编译器", "managers": ["brew", "scoop"]},
        {"name": "rustc", "desc": "Rust 编译器", "managers": ["brew", "scoop"]},
        {"name": "docker", "desc": "容器引擎", "managers": ["brew", "scoop", "winget"]},
        {"name": "kubectl", "desc": "Kubernetes CLI", "managers": ["brew", "scoop"]},
        {"name": "helm", "desc": "Kubernetes 包管理器", "managers": ["brew", "scoop"]},
        {"name": "terraform", "desc": "IaC 工具", "managers": ["brew", "scoop"]},
        {"name": "ansible", "desc": "自动化工具", "managers": ["pip"]},
    ],
}


@app.command()
def install(
    package: str = typer.Argument(..., help="包名称"),
    manager: str | None = typer.Option(None, "--manager", "-m", help="指定包管理器"),
    sudo: bool = typer.Option(False, "--sudo", "-s", help="使用 sudo 安装"),
):
    """
    安装包

    示例:
        omc pkg install git
        omc pkg install gh --manager brew
        omc pkg install node --sudo
    """
    console.print(f"\n[cyan]安装包: {package}[/cyan]")

    # 如果没有指定管理器，自动选择
    if not manager:
        manager = _select_best_manager(package)
        if not manager:
            console.print("[yellow]未找到合适的包管理器[/yellow]")
            console.print("[dim]请先安装 Homebrew 或其他包管理器[/dim]")
            return

    console.print(f"[dim]使用管理器: {manager}[/dim]\n")

    # 构建命令
    cmd = _build_install_command(manager, package, sudo)

    if not cmd:
        console.print(f"[red]不支持的包管理器: {manager}[/red]")
        return

    console.print(f"[yellow]执行: {' '.join(cmd)}[/yellow]\n")

    # 执行安装
    success, _stdout, stderr = _run_command(cmd, capture=False)

    if success:
        console.print(f"[green]✅ 安装成功: {package}[/green]")
    else:
        console.print("[red]❌ 安装失败[/red]")
        if stderr:
            console.print(f"[dim]{stderr}[/dim]")


def _select_best_manager(package: str) -> str | None:
    """选择最佳包管理器"""
    available = get_available_managers()

    # 根据包名推断
    npm_packages = ["node", "npm", "yarn", "pnpm", "typescript", "eslint", "prettier"]
    pip_packages = ["python", "pip", "ansible", "httpie", "tldr"]

    if package.lower() in npm_packages and PackageManager.NPM in available:
        return "npm"

    if package.lower() in pip_packages and PackageManager.PIP in available:
        return "pip"

    # 默认选择
    if PackageManager.HOMEBREW in available:
        return "brew"
    if PackageManager.NPM in available:
        return "npm"
    if PackageManager.SCOOP in available:
        return "scoop"
    if PackageManager.WINGET in available:
        return "winget"
    if PackageManager.AUR in available:
        return "aur"

    return None


def _build_install_command(manager: str, package: str, sudo: bool) -> list[str] | None:
    """构建安装命令"""
    cmd_prefix = ["sudo"] if sudo else []

    commands = {
        "brew": [*cmd_prefix, "brew", "install", package],
        "npm": ["npm", "install", "-g", package],
        "yarn": ["yarn", "global", "add", package],
        "pnpm": ["pnpm", "add", "-g", package],
        "pip": [*cmd_prefix, "pip3", "install", package],
        "scoop": ["scoop", "install", package],
        "winget": ["winget", "install", "--id", package, "--silent"],
        "aur": ["yay", "-S", package],
    }

    return commands.get(manager)


@app.command()
def search(
    query: str = typer.Argument(..., help="搜索关键词"),
    manager: str | None = typer.Option(None, "--manager", "-m", help="指定包管理器"),
):
    """
    搜索包

    示例:
        omc pkg search git
        omc pkg search node --manager npm
    """
    console.print(f"\n[cyan]搜索: {query}[/cyan]\n")

    if manager:
        _search_with_manager(manager, query)
    else:
        # 在所有可用管理器中搜索
        for mgr in get_available_managers():
            _search_with_manager(mgr.value, query)


def _search_with_manager(manager: str, query: str):
    """使用指定管理器搜索"""
    console.print(f"\n[bold]{manager.upper()}:[/bold]")

    commands = {
        "npm": ["npm", "search", query],
        "brew": ["brew", "search", query],
        "pip": ["pip", "search", query] if platform.system() != "Windows" else None,
    }

    cmd = commands.get(manager)
    if not cmd:
        console.print(f"[dim]管理器 {manager} 不支持搜索[/dim]")
        return

    success, stdout, _stderr = _run_command(cmd)

    if success and stdout:
        lines = stdout.strip().splitlines()[:10]  # 只显示前10个
        for line in lines:
            console.print(f"  {line}")
    else:
        console.print("[dim]未找到结果[/dim]")


@app.command()
def list_installed(
    manager: str | None = typer.Option(None, "--manager", "-m", help="指定包管理器"),
):
    """
    列出已安装的包

    示例:
        omc pkg list
        omc pkg list --manager npm
    """
    console.print("\n[cyan]已安装的包[/cyan]\n")

    if manager:
        _list_with_manager(manager)
    else:
        for mgr in get_available_managers():
            _list_with_manager(mgr.value)


def _list_with_manager(manager: str):
    """列出指定管理器的包"""
    console.print(f"\n[bold]{manager.upper()}:[/bold]")

    commands = {
        "npm": ["npm", "list", "-g", "--depth=0"],
        "brew": ["brew", "list"],
        "pip": ["pip", "list"],
        "yarn": ["yarn", "global", "list"],
    }

    cmd = commands.get(manager)
    if not cmd:
        console.print(f"[dim]管理器 {manager} 不支持列出[/dim]")
        return

    success, stdout, _stderr = _run_command(cmd)

    if success and stdout:
        lines = stdout.strip().splitlines()[:20]  # 只显示前20个
        for line in lines:
            console.print(f"  {line}")
    else:
        console.print("[dim]无[/dim]")


@app.command()
def update(
    package: str | None = typer.Argument(None, help="包名称（不指定则更新所有）"),
    manager: str | None = typer.Option(None, "--manager", "-m", help="指定包管理器"),
):
    """
    更新包

    示例:
        omc pkg update
        omc pkg update npm
        omc pkg update git --manager brew
    """
    console.print("\n[cyan]更新包[/cyan]\n")

    if not manager:
        manager = _select_best_manager(package or "npm")

    if not manager:
        console.print("[yellow]未找到可用的包管理器[/yellow]")
        return

    console.print(f"[dim]管理器: {manager}[/dim]")

    commands = {
        "npm": (
            ["npm", "update", "-g"] if not package else ["npm", "update", "-g", package]
        ),
        "brew": ["brew", "upgrade"] if not package else ["brew", "upgrade", package],
        "pip": ["pip", "install", "--upgrade"] + ([package] if package else ["pip"]),
    }

    cmd = commands.get(manager)
    if not cmd:
        console.print(f"[red]管理器 {manager} 不支持更新[/red]")
        return

    console.print(f"[yellow]执行: {' '.join(cmd)}[/yellow]\n")

    success, _stdout, stderr = _run_command(cmd, capture=False)

    if success:
        console.print("[green]✅ 更新成功[/green]")
    else:
        console.print(f"[red]❌ 更新失败: {stderr}[/red]")


@app.command("recommend")
def recommend():
    """显示推荐安装的开发工具"""
    console.print(
        Panel.fit(
            "[bold cyan]推荐开发工具[/bold cyan]\n[dim]快速安装常用命令行工具[/dim]",
            border_style="cyan",
        )
    )

    for category, packages in RECOMMENDED_PACKAGES.items():
        table = Table(title=f"[bold]{category.upper()}[/bold]")
        table.add_column("包名", style="cyan")
        table.add_column("描述", style="white")
        table.add_column("安装命令", style="dim")

        for pkg in packages:
            install_cmd = f"omc pkg install {pkg['name']}"
            table.add_row(pkg["name"], pkg["desc"], install_cmd)

        console.print(table)
        console.print()


@app.command("check")
def check():
    """检查可用的包管理器"""
    console.print("\n[cyan]包管理器状态[/cyan]\n")

    system = get_current_platform()
    console.print(f"平台: [yellow]{system.value}[/yellow]\n")

    all_managers = [
        ("brew", "Homebrew", "macOS/Linux"),
        ("npm", "npm", "全平台"),
        ("yarn", "Yarn", "全平台"),
        ("pnpm", "pnpm", "全平台"),
        ("pip", "pip", "全平台"),
        ("scoop", "Scoop", "Windows"),
        ("winget", "WinGet", "Windows"),
        ("yay", "Yay (AUR)", "Linux"),
    ]

    table = Table()
    table.add_column("命令", style="cyan")
    table.add_column("管理器", style="white")
    table.add_column("平台", style="dim")
    table.add_column("状态", style="green")

    available = [m.value for m in get_available_managers()]

    for cmd, name, platforms in all_managers:
        if cmd in available or (cmd == "brew" and system == Platform.MACOS):
            status = "✅ 已安装" if cmd in available else "❌ 未安装"
        else:
            if platforms.lower() == system.value.lower() or platforms == "全平台":
                status = "❌ 未安装"
            else:
                status = "⏭️ 不适用"

        table.add_row(cmd, name, platforms, status)

    console.print(table)


if __name__ == "__main__":
    app()
