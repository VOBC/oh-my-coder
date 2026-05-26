from __future__ import annotations

"""
Monorepo 工作区感知 CLI

支持 pnpm workspace、lerna、bazel 等 monorepo 结构
"""


from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Monorepo 工作区感知")
console = Console()

# Monorepo 配置文件
MONOREPO_CONFIGS = {
    "pnpm": ["pnpm-workspace.yaml"],
    "lerna": ["lerna.json"],
    "nx": ["nx.json", "workspace.json"],
    "turborepo": ["turbo.json"],
    "bazel": ["WORKSPACE", "WORKSPACE.bazel"],
    "rush": ["rush.json"],
}


@dataclass
class MonorepoInfo:
    """Monorepo 信息"""

    root: Path
    type: str  # pnpm, lerna, nx, etc.
    packages: list[Path]
    config_file: Path


def detect_monorepo(root: Path) -> Optional[MonorepoInfo]:
    """检测目录是否为 monorepo 根目录"""
    for repo_type, config_files in MONOREPO_CONFIGS.items():
        for config in config_files:
            config_path = root / config
            if config_path.exists():
                packages = _find_packages(root, repo_type)
                return MonorepoInfo(
                    root=root,
                    type=repo_type,
                    packages=packages,
                    config_file=config_path,
                )
    return None


def _find_packages(root: Path, repo_type: str) -> list[Path]:
    """根据 monorepo 类型查找 packages 目录"""
    packages = []

    if repo_type == "pnpm":
        # pnpm: packages/ 目录或 workspace 文件中声明的路径
        workspace_file = root / "pnpm-workspace.yaml"
        if workspace_file.exists():
            content = workspace_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("- ") or line.startswith("packages:"):
                    # 解析路径
                    if "packages/" in line:
                        pkg_dir = root / line.split("- ")[-1].strip()
                        if pkg_dir.is_dir():
                            packages.append(pkg_dir)
        # 常见位置
        if not packages:
            common = root / "packages"
            if common.is_dir():
                for sub in common.iterdir():
                    if sub.is_dir():
                        packages.append(sub)

    elif repo_type == "lerna":
        lerna_file = root / "lerna.json"
        if lerna_file.exists():
            import json
            from glob import glob

            data = json.loads(lerna_file.read_text(encoding="utf-8"))
            package_patterns = data.get("packages", ["packages/*"])
            for pattern in package_patterns:
                # Handle glob patterns
                matched_dirs = glob(str(root / pattern), recursive=True)
                for matched in matched_dirs:
                    pkg_path = Path(matched)
                    if pkg_path.is_dir():
                        packages.append(pkg_path)

    elif repo_type == "nx":
        # nx: packages/ 目录
        common = root / "packages"
        if common.is_dir():
            for sub in common.iterdir():
                if sub.is_dir():
                    packages.append(sub)

    return packages


@app.command("detect")
def detect(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="检测目录"),
) -> None:
    """检测是否为 monorepo 并显示信息"""
    info = detect_monorepo(path)

    if info is None:
        console.print(
            f"[yellow]⚠[/yellow] 目录 [cyan]{path}[/cyan] 不是已知的 monorepo 结构"
        )
        console.print(
            "[dim]支持: pnpm workspace, lerna, nx, turborepo, bazel, rush[/dim]"
        )
        return

    console.print(f"[green]✓[/green] 检测到 Monorepo: [bold]{info.type}[/bold]")
    console.print(f"[dim]根目录: {info.root}[/dim]")
    console.print(f"[dim]配置文件: {info.config_file}[/dim]")
    console.print(f"[dim]包数量: {len(info.packages)}[/dim]\n")

    table = Table(title=f"包列表 ({info.type})")
    table.add_column("序号", style="dim", width=4)
    table.add_column("包路径", style="cyan")
    table.add_column("语言", style="yellow")
    table.add_column("框架", style="green")

    for i, pkg in enumerate(sorted(info.packages), 1):
        # 简单检测语言
        lang = "?"
        if (pkg / "package.json").exists():
            lang = "Node/TS"
        elif (pkg / "pyproject.toml").exists():
            lang = "Python"
        elif (pkg / "Cargo.toml").exists():
            lang = "Rust"
        elif (pkg / "go.mod").exists():
            lang = "Go"
        elif (pkg / "pom.xml").exists():
            lang = "Java"
        elif (pkg / "build.gradle").exists():
            lang = "Java/Kotlin"

        rel = pkg.relative_to(info.root)
        table.add_row(str(i), str(rel), lang, "-")

    console.print(table)


@app.command("status")
def monorepo_status(
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="工作区路径"),
    show_dirty: bool = typer.Option(True, "--dirty/--no-dirty", help="显示有改动的包"),
) -> None:
    """显示所有包的 Git 状态"""
    info = detect_monorepo(path)

    if info is None:
        console.print("[red]✗[/red] 不是 monorepo 目录")
        raise typer.Exit(1)

    import subprocess

    table = Table(title=f"Monorepo 包状态 - {info.type}")
    table.add_column("包", style="cyan")
    table.add_column("状态", style="yellow")
    table.add_column("改动", style="red")

    for pkg in sorted(info.packages):
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=pkg,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
                count = len(lines)
                status_emoji = "📦" if count == 0 else "✏️"
                table.add_row(
                    pkg.name,
                    status_emoji,
                    f"{count} 个文件" if count else "干净",
                )
        except Exception:
            table.add_row(pkg.name, "❓", "无法获取")

    console.print(table)
    console.print(f"\n[dim]根目录: {info.root}[/dim]")


@app.command("run")
def monorepo_run(
    script: str = typer.Argument(..., help="要运行的脚本名称"),
    scope: str = typer.Option(None, "--scope", "-s", help="只运行指定包（模糊匹配）"),
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="工作区路径"),
    parallel: bool = typer.Option(False, "--parallel", help="并行运行"),
    dry_run: bool = typer.Option(False, "--dry-run", help="只显示将要运行的命令"),
) -> None:
    """在所有/指定包中运行脚本"""
    info = detect_monorepo(path)

    if info is None:
        console.print("[red]✗[/red] 不是 monorepo 目录")
        raise typer.Exit(1)

    packages = info.packages
    if scope:
        packages = [p for p in packages if scope.lower() in p.name.lower()]

    if not packages:
        console.print(f"[yellow]⚠[/yellow] 没有找到匹配的包 (scope: {scope})")
        return

    console.print(f"[cyan]将在 {len(packages)} 个包中运行: {script}[/cyan]\n")

    import subprocess

    results = []
    for pkg in packages:
        cmd = None
        if info.type == "pnpm":
            cmd = ["pnpm", "--filter", pkg.name, "run", script]
        elif info.type == "nx":
            cmd = ["npx", "nx", "run-many", "-t", script, "-p", pkg.name]
        elif info.type == "lerna":
            cmd = ["npx", "lerna", "run", script, "--scope", pkg.name]
        else:
            console.print(f"[yellow]⚠[/yellow] {info.type} 类型暂不支持 'run' 命令")
            return

        if dry_run:
            console.print(f"[dim]  cd {pkg} && {' '.join(cmd)}[/dim]")
        else:
            console.print(f"[cyan]→[/cyan] {pkg.name}...", end=" ")
            try:
                result = subprocess.run(
                    cmd, cwd=info.root, capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    console.print("[green]✓[/green]")
                    results.append((pkg, True, ""))
                else:
                    console.print("[red]✗[/red]")
                    results.append((pkg, False, result.stderr[:100]))
            except Exception as e:
                console.print(f"[red]✗ {e}[/red]")
                results.append((pkg, False, type(e).__name__))

    # 汇总
    passed = sum(1 for _, ok, _ in results if ok)
    console.print(f"\n[bold]完成: {passed}/{len(results)} 成功[/bold]")


if __name__ == "__main__":
    app()
