from __future__ import annotations

"""
omc doctor - 环境诊断命令

检查常见问题并给出修复建议：
- Python 版本 >= 3.9
- 依赖包完整性
- 配置文件完整性（API Key）
- 网络连通性（测试 API endpoint）
"""

import importlib
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

app = typer.Typer(
    name="doctor",
    help="环境诊断 - 检查常见问题并给出修复建议",
    add_completion=False,
    no_args_is_help=True,
)


# ============================================================
# 检查项定义
# ============================================================

REQUIRED_PACKAGES = [
    ("pydantic", "pydantic", ">=2.5.0"),
    ("typer", "typer", ">=0.9.0"),
    ("rich", "rich", ">=13.7.0"),
    ("httpx", "httpx", ">=0.25.0"),
    ("dotenv", "python-dotenv", ">=1.0.0"),
    ("tenacity", "tenacity", ">=8.0.0"),
]

OPTIONAL_PACKAGES = [
    ("fastapi", "fastapi", ">=0.104.0"),
    ("uvicorn", "uvicorn", ">=0.24.0"),
    ("jinja2", "jinja2", ">=3.0.0"),
    ("redis", "redis", ">=4.0.0"),
    ("websockets", "websockets", ">=10.0"),
    ("yaml", "pyyaml", ">=6.0"),
]

API_KEYS = [
    ("DEEPSEEK_API_KEY", "DeepSeek", "https://platform.deepseek.com/"),
    ("KIMI_API_KEY", "KIMI (Moonshot)", "https://platform.moonshot.cn/"),
    ("DOUBAO_API_KEY", "豆包 (Volcengine)", "https://console.volcengine.com/"),
    ("TONGYI_API_KEY", "通义千问", "https://dashscope.console.aliyun.com/"),
    ("GLM_API_KEY", "智谱 GLM", "https://open.bigmodel.cn/"),
    ("MINIMAX_API_KEY", "MiniMax", "https://www.minimaxi.com/"),
]

API_TEST_URLS = [
    ("DeepSeek API", "https://api.deepseek.com", "DeepSeek 模型服务"),
    ("KIMI API", "https://api.moonshot.cn", "KIMI 模型服务"),
    ("豆包 API", "https://ark.cn-beijing.volces.com", "豆包模型服务"),
]


def _check_python_version() -> tuple[bool, str, str]:
    """检查 Python 版本"""
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 9:
        return True, f"Python {major}.{minor}.{sys.version_info[2]}", ""
    return False, f"Python {major}.{minor}.{sys.version_info[2]}", (
        "oh-my-coder 需要 Python >= 3.9\n"
        f"  当前版本: {sys.version}\n"
        "  请升级 Python: https://www.python.org/downloads/"
    )


def _check_package(
    module_name: str, package_name: str, version_req: str
) -> tuple[bool, str, str]:
    """检查单个依赖包"""
    try:
        mod = importlib.import_module(module_name)
        ver = getattr(mod, "__version__", getattr(mod, "version", "unknown"))
        return True, f"{package_name} {ver}", ""
    except ImportError:
        return False, f"{package_name} {version_req}", (
            f"缺少依赖: {package_name} {version_req}\n"
            f"  安装: pip install '{package_name}{version_req}'"
        )


def _check_config_file() -> tuple[bool, str, str]:
    """检查配置文件"""
    paths = []
    # 用户级配置
    user_env = Path.home() / ".omc" / ".env"
    if user_env.exists():
        paths.append(f"~/.omc/.env ({len(user_env.read_text().splitlines())} 行)")

    # 项目级配置
    project_env = Path(".env")
    if project_env.exists():
        paths.append(f".env ({len(project_env.read_text().splitlines())} 行)")

    # 用户级 JSON 配置
    user_config = Path.home() / ".config" / "oh-my-coder" / "config.json"
    if user_config.exists():
        paths.append(f"~/.config/oh-my-coder/config.json")

    if paths:
        return True, " / ".join(paths), ""
    return False, "未找到配置文件", (
        "未找到任何配置文件\n"
        "  创建项目配置: omc config set -k DEEPSEEK_API_KEY -v <your-key>\n"
        "  或手动创建 ~/.omc/.env 文件"
    )


def _check_network(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    """测试网络连通性"""
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "omc-doctor/1.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 500, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        # 4xx 是连通的（只是未授权），5xx 才是服务问题
        return e.code < 500, f"HTTP {e.code}"
    except urllib.error.URLError:
        return False, "连接失败"
    except Exception as e:
        return False, str(e)


@app.command()
def run(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="显示详细信息（包含可选依赖和版本对比）"
    ),
    skip_network: bool = typer.Option(
        False, "--skip-network", help="跳过网络连通性检查"
    ),
):
    """
    🏥 运行环境诊断

    检查 Python 版本、依赖包、配置文件、API Key 和网络连通性，
    并给出修复建议。
    """
    issues_found = 0
    checks_passed = 0

    # 构建结果表
    table = Table(title="🏥 omc doctor — 环境诊断报告")
    table.add_column("状态", width=4)
    table.add_column("检查项", style="cyan", width=22)
    table.add_column("结果")
    table.add_column("修复建议", style="dim")

    def _add_row(ok: bool, name: str, result: str, fix: str = ""):
        nonlocal issues_found, checks_passed
        if ok:
            checks_passed += 1
            table.add_row("✅", name, f"[green]{result}[/green]", "")
        else:
            issues_found += 1
            table.add_row("❌", name, f"[red]{result}[/red]", fix)

    console.print()
    console.print(
        Panel.fit(
            "[bold]🏥 omc doctor[/bold] — 环境诊断中...\n"
            f"[dim]Python {sys.version_info[0]}.{sys.version_info[1]} | "
            f"{sys.platform}[/dim]",
            border_style="cyan",
        )
    )

    # ---- 1. Python 版本 ----
    ok, result, fix = _check_python_version()
    _add_row(ok, "Python 版本", result, fix)

    # ---- 2. 核心依赖 ----
    for module, package, ver in REQUIRED_PACKAGES:
        ok, result, fix = _check_package(module, package, ver)
        _add_row(ok, f"依赖: {package}", result, fix)

    # ---- 3. 可选依赖（verbose 模式）----
    if verbose:
        for module, package, ver in OPTIONAL_PACKAGES:
            ok, result, fix = _check_package(module, package, ver)
            if ok:
                table.add_row("✅", f"可选: {package}", f"[dim]{result}[/dim]", "")
            else:
                table.add_row(
                    "⚠️", f"可选: {package}", f"[yellow]{result}[/yellow]", fix
                )

    # ---- 4. 配置文件 ----
    ok, result, fix = _check_config_file()
    _add_row(ok, "配置文件", result, fix)

    # ---- 5. API Key 检查 ----
    any_key = False
    for env_key, display_name, url in API_KEYS:
        val = os.getenv(env_key, "")
        if val:
            if not any_key:
                any_key = True
            masked = val[:4] + "****" + val[-4:] if len(val) > 8 else "****"
            table.add_row("✅", f"Key: {display_name}", f"[green]{masked}[/green]", "")
        # 未配置的 Key 不显示（太多噪音），仅在 none 时提示

    if not any_key:
        _add_row(
            False,
            "API Key",
            "未配置任何 API Key",
            "至少配置一个 API Key:\n"
            "  omc config set -k DEEPSEEK_API_KEY -v <your-key>\n"
            "  推荐从 DeepSeek 获取: https://platform.deepseek.com/",
        )

    # ---- 6. 网络连通性 ----
    if not skip_network:
        for name, url, desc in API_TEST_URLS:
            ok, status = _check_network(url)
            if ok:
                table.add_row("✅", f"网络: {name}", f"[green]{status}[/green]", "")
            else:
                table.add_row(
                    "⚠️",
                    f"网络: {name}",
                    f"[yellow]{status}[/yellow]",
                    f"{desc} 不可达，检查网络或代理设置",
                )

    # ---- 输出结果 ----
    console.print()
    console.print(table)

    # 摘要
    total = checks_passed + issues_found
    if issues_found == 0:
        console.print(
            Panel.fit(
                f"[bold green]✅ 全部通过 ({checks_passed}/{total})[/bold green]\n"
                "[dim]环境状态良好，可以正常使用 omc[/dim]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"[bold yellow]⚠️ 发现 {issues_found} 个问题 "
                f"({checks_passed}/{total} 通过)[/bold yellow]\n"
                "[dim]请根据上方修复建议逐一解决[/dim]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
