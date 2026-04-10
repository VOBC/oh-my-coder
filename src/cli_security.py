"""
安全/权限 CLI 命令

omc security check <command>  - 预检命令是否安全
omc security list             - 列出内置危险模式
omc security sandbox-test     - 测试沙箱路径限制
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .security.permissions import (
    PermissionGuard,
)
from .sandbox.sandbox import Sandbox

app = typer.Typer(
    name="security",
    help="安全检查 - 权限验证、危险命令拦截、沙箱测试",
    add_completion=False,
)
console = Console()


@app.command("check")
def security_check(
    command: str = typer.Argument(..., help="要检查的命令"),
    config_file: str = typer.Option(
        None,
        "--config",
        "-c",
        help="权限规则文件 (.yaml/.json)",
    ),
) -> None:
    """
    预检命令是否安全

    示例:
        omc security check "git status"
        omc security check "rm -rf /tmp/test"
        omc security check "dd if=/dev/zero of=/dev/sda"
    """
    guard: PermissionGuard | None = None

    if config_file:
        try:
            from .config.agent_config import load_config_file

            config = load_config_file(config_file)
            guard = PermissionGuard.from_agent_config(config.to_dict())
        except Exception as e:
            console.print(f"[yellow]加载配置失败，使用默认规则: {e}[/yellow]")
            guard = PermissionGuard()
    else:
        guard = PermissionGuard()

    result = guard.check(command)
    needs_appr = guard.needs_approval(command)

    if result.allowed:
        if needs_appr:
            console.print(
                Panel(
                    f"[yellow]⚠️  命令允许执行，但需要审批[/yellow]\n\n"
                    f"命令: [cyan]{command}[/cyan]\n"
                    f"原因: {result.reason or '匹配 require_approval 规则'}",
                    title="🔒 安全检查",
                    border_style="yellow",
                )
            )
        else:
            console.print(
                Panel.fit(
                    f"[green]✅ 命令安全[/green]\n\n" f"命令: [cyan]{command}[/cyan]",
                    title="🔒 安全检查",
                    border_style="green",
                )
            )
    else:
        console.print(
            Panel(
                f"[red]❌ 命令被拦截[/red]\n\n"
                f"命令: [cyan]{command}[/cyan]\n"
                f"原因: {result.reason}\n"
                f"匹配: [dim]{result.matched_pattern}[/dim]",
                title="🔒 安全检查",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command("list")
def security_list() -> None:
    """
    列出内置危险命令模式

    示例:
        omc security list
    """
    console.print(
        Panel.fit(
            "[bold]内置危险命令模式（即使未配置也会拦截）[/bold]\n",
            title="🔒 内置危险模式",
            border_style="red",
        )
    )

    patterns = [
        ("rm -rf /", "递归删除根目录"),
        ("rm -rf /{dir}", "递归删除系统目录"),
        ("Fork Bomb", "Fork 炸弹"),
        ("> /dev/sd[a-z]", "直接写磁盘设备"),
        ("dd if=... of=/dev/", "直接写设备文件"),
        ("mkfs", "格式化文件系统"),
        (":(){ :|:& };:", "Fork 炸弹变体"),
    ]

    table = Table()
    table.add_column("模式", style="red")
    table.add_column("说明", style="white")

    for pattern, desc in patterns:
        table.add_row(pattern, desc)

    console.print(table)


@app.command("sandbox-test")
def sandbox_test(
    path: str = typer.Argument(".", help="测试路径"),
) -> None:
    """
    测试沙箱路径限制

    示例:
        omc security sandbox-test "/tmp/test"
        omc security sandbox-test "~/.ssh/id_rsa"
        omc security sandbox-test "/etc/passwd"
    """
    sandbox = Sandbox()

    allowed = sandbox.validate_path(path)

    if allowed:
        console.print(
            Panel.fit(
                f"[green]✅ 路径在允许范围内[/green]\n\n路径: [cyan]{path}[/cyan]\n"
                f"允许目录: {', '.join(sandbox.get_allowed_dirs())}",
                title="🛡️ 沙箱测试",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]❌ 路径超出沙箱范围[/red]\n\n"
                f"路径: [cyan]{path}[/cyan]\n"
                f"允许目录: {', '.join(sandbox.get_allowed_dirs())}",
                title="🛡️ 沙箱测试",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command("run")
def security_run(
    command: str = typer.Argument(..., help="在沙箱中执行的命令"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="超时秒数"),
) -> None:
    """
    在沙箱中安全执行命令

    示例:
        omc security run "ls ~/.omc"
        omc security run "git status" -t 10
    """
    sandbox = Sandbox()

    console.print(f"[dim]在沙箱中执行: {command}[/dim]")

    try:
        result = sandbox.run_command(command, timeout=timeout)

        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")

        if result.returncode == 0:
            console.print(f"\n[green]✓ 执行成功（返回 {result.returncode}）[/green]")
        else:
            console.print(f"\n[yellow]执行完成（返回 {result.returncode}）[/yellow]")

    except PermissionError as e:
        console.print(f"[red]❌ 沙箱拒绝: {e}[/red]")
        raise typer.Exit(1)
    except TimeoutError:
        console.print(f"[red]❌ 命令执行超时（{timeout}秒）[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ 执行失败: {e}[/red]")
        raise typer.Exit(1)
