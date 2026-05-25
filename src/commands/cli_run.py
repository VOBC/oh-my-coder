from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.agents.cross_validation import CrossValidationLayer
from src.core.orchestrator import Orchestrator
from src.core.router import ModelRouter, RouterConfig
from src.wiki import WikiGenerator

console = Console()

# ============================================================
# 创建独立的 Typer app
# ============================================================
app = typer.Typer(
    name="run",
    help="任务执行相关命令",
    add_completion=False,
)

# ============================================================
# run — 任务执行
# ============================================================


@app.command()
def run(
    task: str = typer.Argument(..., help="任务描述"),
    project_path: Path = typer.Option(".", "--project", "-p", help="项目路径"),
    model: str = typer.Option("deepseek", "--model", "-m", help="模型选择"),
    workflow: str = typer.Option(
        "build",
        "--workflow",
        "-w",
        help=(
            "工作流名称：build（开发）/ review（审查）/ debug（调试）/ test（测试）"
            " / autopilot（自动路由）/ pair（结对编程）/ refactor（重构）"
            " / doc（文档生成）/ sequential（顺序执行编排）"
        ),
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览执行计划，不实际运行"),
    notify: bool = typer.Option(
        False, "--notify", "-n", help="完成后发送通知（桌面+钉钉）"
    ),
    no_checkpoint: bool = typer.Option(
        False, "--no-checkpoint", help="跳过自动快照（断点续传）"
    ),
    simple: bool = typer.Option(
        False, "--simple", "-s", help="简单模式：不经过工作流，直接执行（适合创建文件等快速任务）"
    ),
    cross_validate: bool = typer.Option(
        False,
        "--cross-validate",
        help="工作流结束后执行 Agent 交叉验证（独立视角审视产出）",
    ),
    use_sourcegraph: bool = typer.Option(
        False,
        "--use-sourcegraph",
        help="Analyst Agent 使用 Sourcegraph 搜索公开代码库增强分析",
    ),
):
    """执行编程任务"""
    # 前置检查
    if not _check_env():
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold green]Oh My Coder[/bold green]\n"
            f"任务: {task}\n"
            f"项目: {project_path}\n"
            f"工作流: {workflow}",
            title="🚀 启动",
        )
    )

    # Dry-run 模式：只展示计划
    if dry_run:
        console.print(
            Panel.fit(
                "[yellow]🔍 Dry-run 模式 — 仅展示执行计划[/yellow]\n\n"
                "[bold]工作流:[/bold] "
                + workflow
                + "\n[bold]任务:[/bold] "
                + task
                + "\n[bold]项目:[/bold] "
                + str(project_path.absolute())
                + "\n\n[dim]实际执行请去掉 --dry-run 参数[/dim]",
                title="📋 执行计划预览",
                border_style="yellow",
            )
        )
        raise typer.Exit(0)

    # 初始化路由器和编排器
    try:
        router = _init_router()
    except SystemExit:
        raise typer.Exit(1)

    # ---- 简单模式：不走工作流，直接调用模型生成命令执行 ----
    if simple:
        _run_simple_task(router, task)
        raise typer.Exit(0)

    orchestrator = Orchestrator(router, state_dir=project_path / ".omc" / "state")

    # 执行工作流
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # 进度回调：显示当前执行的 Agent
        main_task = progress.add_task("🚀 正在启动...", total=None)

        def _progress_callback(step_name: str, status: str):
            """更新进度显示"""
            nonlocal main_task
            if status == "started":
                progress.update(main_task, description=f"🔄 正在执行: {step_name}")
            elif status == "completed":
                progress.update(main_task, description=f"✅ 已完成: {step_name}")
            elif status == "failed":
                progress.update(main_task, description=f"❌ 失败: {step_name}")

        try:
            result = asyncio.run(
                orchestrator.execute_workflow(
                    workflow,
                    {
                        "project_path": str(project_path.absolute()),
                        "task": task,
                        "use_sourcegraph": use_sourcegraph,
                    },
                    skip_checkpoint=no_checkpoint,
                    progress_callback=_progress_callback,
                )
            )

            # 显示结果
            _display_result(result)

            # ---- 交叉验证：独立视角审视工作流产出 ----
            if cross_validate:
                cv_progress = progress.add_task("🔍 交叉验证...", total=None)
                try:
                    cv_layer = CrossValidationLayer(
                        model_router=router,
                        state_dir=project_path / ".omc" / "state",
                    )
                    cv_result = asyncio.run(
                        cv_layer.validate_workflow(result, workflow)
                    )
                    progress.remove_task(cv_progress)

                    # 显示验证摘要
                    _display_cross_validation_result(cv_result)

                    # 验证失败时以非零退出码结束
                    if cv_result.status.value in ("fail", "need_fix"):
                        console.print(
                            Panel.fit(
                                "[yellow]⚠️  交叉验证发现问题，建议修复后重试[/yellow]\n"
                                "[dim]验证报告已保存至 .omc/state/cross_validation/[/dim]",
                                title="⚠️  验证提醒",
                                border_style="yellow",
                            )
                        )
                except Exception as cv_err:
                    progress.remove_task(cv_progress)
                    console.print(
                        f"[yellow]⚠️  交叉验证出错（不影响主流程）: {cv_err}[/yellow]"
                    )

            # 发送通知
            if notify:
                from src.utils.notify import (
                    notify_workflow_complete,
                    notify_workflow_complete_dingtalk,
                )

                status = "completed" if result.success else "failed"
                steps = len(result.steps) if hasattr(result, "steps") else 1
                exec_time = getattr(result, "execution_time", 0.0)

                # 桌面通知
                notify_workflow_complete(workflow, status, steps, exec_time)
                # 钉钉通知
                notify_workflow_complete_dingtalk(
                    None, workflow, status, steps, exec_time, str(project_path)
                )

        except Exception as e:
            _print_fatal(
                f"工作流执行出错: {e}",
                hint="可尝试以下方法：\n"
                "  1. 检查网络连接\n"
                "  2. 确认 API Key 有效：omc status\n"
                "  3. 查看详细日志",
            )
            raise typer.Exit(1)


# ============================================================
# explore — 探索模式
# ============================================================


@app.command()
def explore(
    project_path: Path = typer.Argument(".", help="项目路径"),
):
    """探索代码库"""
    if not _check_env():
        raise typer.Exit(1)

    console.print(f"[bold]🔍 探索项目: {project_path}[/bold]")

    try:
        router = _init_router()
    except SystemExit:
        raise typer.Exit(1)

    orchestrator = Orchestrator(router)

    try:
        result = asyncio.run(
            orchestrator.execute_single_agent(
                "explore",
                {
                    "project_path": str(project_path.absolute()),
                    "task": "探索代码库并生成项目地图",
                },
            )
        )

        if result.result:
            console.print(Panel(result.result, title="项目地图"))
        else:
            _print_fatal(f"探索失败: {result.error}")

    except Exception as e:
        _print_fatal(f"探索出错: {e}", hint="确认项目路径存在且可读")
        raise typer.Exit(1)


# ============================================================
# wiki — Wiki 生成
# ============================================================


@app.command()
def wiki(
    project_path: Path = typer.Argument(".", help="项目路径"),
    output: Path = typer.Option(
        None, "--output", "-o", help="输出文件路径，默认 REPO_WIKI.md"
    ),
):
    """生成项目 Wiki 文档"""
    project_path = project_path.resolve()

    if not project_path.exists():
        _print_fatal(f"项目路径不存在: {project_path}")
        raise typer.Exit(1)

    # 确定输出路径
    if output is None:
        output = project_path / "REPO_WIKI.md"

    console.print(f"[bold]📝 生成 Wiki: {project_path}[/bold]")

    try:
        # 从 pyproject.toml 或目录名获取项目名
        project_name = _detect_project_name(project_path)

        # 生成 Wiki
        generator = WikiGenerator(
            project_name=project_name,
            project_path=project_path,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("解析代码...", total=None)
            generator.generate(output)

        console.print(
            Panel.fit(
                f"[green]✓ Wiki 已生成[/green]\n\n"
                f"文件: [cyan]{output}[/cyan]\n\n"
                f"[dim]使用 `omc wiki` 重新生成[/dim]",
                title="📚 Wiki",
            )
        )

    except Exception as e:
        _print_fatal(f"Wiki 生成失败: {e}")
        raise typer.Exit(1)


# ============================================================
# 辅助函数
# ============================================================


def _detect_project_name(project_path: Path) -> str:
    """检测项目名称"""
    # 尝试从 pyproject.toml 读取
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib

            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            if "project" in data and "name" in data["project"]:
                return data["project"]["name"]
        except Exception:
            pass

    # 尝试从 setup.py 读取
    setup_py = project_path / "setup.py"
    if setup_py.exists():
        try:
            content = setup_py.read_text()
            match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
        except Exception:
            pass

    # 默认使用目录名
    return project_path.name


def _load_config() -> dict:
    """从 ~/.omc/config.json 读取配置"""
    config_path = Path.home() / ".omc" / "config.json"
    if not config_path.exists():
        return {}
    import json
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def _resolve_default_model(config: dict) -> str:
    """解析默认模型：环境变量 > config.json > 第一个有 api_key 的模型 > deepseek"""
    env_model = os.getenv("OMC_DEFAULT_MODEL") or os.getenv("DEFAULT_MODEL")
    if env_model:
        return env_model
    cfg_model = config.get("defaults", {}).get("model") or config.get("default_model")
    if cfg_model:
        return cfg_model
    models = config.get("models", {})
    if isinstance(models, dict):
        for name, mcfg in models.items():
            if isinstance(mcfg, dict) and mcfg.get("api_key"):
                return name
    return "deepseek"


def _get_api_key(config: dict, model: str) -> str:
    """获取模型对应的 API Key：config.json > 环境变量"""
    # 1. 从 config.json 的 models 中读取
    models = config.get("models", {})
    if isinstance(models, dict):
        for name, mcfg in models.items():
            if isinstance(mcfg, dict) and mcfg.get("api_key") and name in (model, model.replace("-", "_"), model.replace("_", "-")):
                return mcfg["api_key"]
    # 2. 环境变量回退
    key_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "kimi": "KIMI_API_KEY",
        "doubao": "DOUBAO_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "glm": "ZHIPUAI_API_KEY",
        "tongyi": "DASHSCOPE_API_KEY",
        "wenxin": "ERNIE_API_KEY",
        "hunyuan": "HUNYUAN_API_KEY",
    }
    return os.getenv(key_map.get(model, f"{model.upper()}_API_KEY"), "")


def _run_simple_task(router: ModelRouter, task: str) -> None:
    """
    简单模式：不经过工作流，直接调用模型生成并执行 shell 命令。
    适合创建文件、运行命令等快速任务。
    """
    import json
    import subprocess

    from src.models.base import Message

    console.print(Panel.fit(
        f"[cyan]⚡ 简单模式 — 直接执行[/cyan]\n任务: {task}",
        title="🚀 启动",
        border_style="cyan",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("🤔 分析任务...", total=None)

        try:
            response = asyncio.run(
                router.route_and_call(
                    task_type="simple",
                    messages=[
                        Message(
                            role="system",
                            content=(
                                "你是一个任务执行助手。请将用户的任务描述转换为一条或多条 shell 命令。"
                                "只输出 JSON 数组格式，不要多余的文字。\n"
                                '格式: [{"cmd": "命令", "desc": "步骤说明"}, ...]\n'
                                "【严格规则 - 必须遵守】\n"
                                "1. 只做用户明确要求的事，不要自作主张添加额外步骤\n"
                                "2. 绝对不能执行 rm/del/remove/unlink 等任何删除操作\n"
                                "3. 绝对不能修改或覆盖用户已存在的文件\n"
                                "4. 如果是创建文件，用 echo 或 cat 命令\n"
                                "5. 路径用绝对路径（如 ~/Desktop/xxx）\n"
                                "6. 每个命令必须独立可执行\n"
                                '7. 如果任务不需要任何命令（如纯问答），输出 []'
                            ),
                        ),
                        Message(role="user", content=f"任务: {task}"),
                    ],
                    complexity="low",
                )
            )
        except Exception as e:
            _print_fatal(
                f"模型请求失败: {e}",
                hint="请检查网络连接和 API Key 配置。",
            )
            raise typer.Exit(1)

        progress.remove_task(progress.task_ids[0])

        # 第二步：解析命令
        raw = response.content.strip()
        # 去掉可能的 markdown 代码块标记
        if raw.startswith("```"):
            first_newline = raw.find("\n")
            if first_newline != -1:
                raw = raw[first_newline + 1:]
            end_marker = raw.rfind("```")
            if end_marker != -1:
                raw = raw[:end_marker].strip()

        try:
            commands = json.loads(raw)
        except json.JSONDecodeError:
            console.print("[red]模型返回结果解析失败[/red]")
            console.print(f"原始输出:\n{raw}")
            return

    # 安全过滤：阻止危险命令
    DANGEROUS_PREFIXES = ("rm ", "rm -rf", "rmdir ", "dd ", "> /dev/", ":(){ :|:& };:")
    for cmd_info in commands:
        cmd = cmd_info.get("cmd", "")
        if any(cmd.strip().startswith(p) for p in DANGEROUS_PREFIXES):
            console.print(f"[red]⛔ 安全拦截：检测到危险命令 — {cmd}[/red]")
            console.print(Panel.fit(
                "[yellow]已阻止执行，这是模型自主生成的命令，不是你要求的。\n"
                "如需执行危险操作，请直接在工作流模式下运行。[/yellow]",
                border_style="yellow",
            ))
            return

    # 执行命令
    if not commands:
        console.print("[yellow]⚠️ 没有需要执行的命令[/yellow]")
        console.print(f"\n模型回答:\n{response.content}")
        return

    console.print(f"[bold]📋 执行计划 — {len(commands)} 步[/bold]\n")
    for i, cmd_info in enumerate(commands, 1):
        desc = cmd_info.get("desc", "")
        cmd = cmd_info.get("cmd", "")
        console.print(f"  {i}. {desc}")
        console.print(f"     $ {cmd}\n")

    # 直接执行
    success_count = 0
    for cmd_info in commands:
        cmd = cmd_info.get("cmd", "")
        desc = cmd_info.get("desc", "")
        if not cmd:
            continue

        console.print(f"[cyan]▶ 执行: {desc}[/cyan]")
        console.print(f"   $ {cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                console.print("  [green]✓ 成功[/green]")
                if result.stdout.strip():
                    console.print(f"    {result.stdout.rstrip()}")
                success_count += 1
            else:
                console.print(f"  [red]✗ 失败 (exit {result.returncode})[/red]")
                if result.stderr.strip():
                    console.print(f"    [red]{result.stderr.rstrip()}[/red]")
        except subprocess.TimeoutExpired:
            console.print("  [red]✗ 超时 (30s)[/red]")
        except Exception as e:
            console.print(f"  [red]✗ 异常: {e}[/red]")

    console.print()
    if success_count == len(commands):
        console.print(Panel.fit(
            f"[green]✅ 全部完成 ({success_count}/{len(commands)} 步成功)[/green]",
            border_style="green",
        ))
    else:
        console.print(Panel.fit(
            f"[yellow]⚠️ 部分完成 ({success_count}/{len(commands)} 步成功)[/yellow]",
            border_style="yellow",
        ))


def _init_router() -> ModelRouter:
    """初始化模型路由器，失败时给出友好提示"""
    config = RouterConfig()
    user_config = _load_config()
    default_model = _resolve_default_model(user_config)

    # 检查 API Key 是否就绪
    api_key = _get_api_key(user_config, default_model)
    if not api_key:
        # 没有找到 key，给提示
        api_key_hint_map = {
            "deepseek": ("DEEPSEEK_API_KEY", "https://platform.deepseek.com/", "性价比最高，推荐配置"),
            "glm": ("ZHIPUAI_API_KEY", "https://www.zhipuai.cn/", "智谱 GLM 模型"),
            "kimi": ("KIMI_API_KEY", "https://platform.moonshot.cn/", "月之暗面 Kimi"),
            "doubao": ("DOUBAO_API_KEY", "https://console.volcengine.com/", "字节豆包"),
            "minimax": ("MINIMAX_API_KEY", "https://www.minimax.io/", "MiniMax"),
            "tongyi": ("DASHSCOPE_API_KEY", "https://dashscope.console.aliyun.com/", "通义千问"),
            "wenxin": ("ERNIE_API_KEY", "https://cloud.baidu.com/", "文心一言"),
            "hunyuan": ("HUNYUAN_API_KEY", "https://cloud.tencent.com/", "腾讯混元"),
        }
        hint = api_key_hint_map.get(default_model)
        if hint:
            _print_missing_key_hint(hint[0], hint[2], url=hint[1])
        else:
            _print_missing_key_hint(f"{default_model.upper()}_API_KEY", "")
        raise typer.Exit(1)

    try:
        return ModelRouter(config)
    except Exception as e:
        _print_fatal(f"路由器初始化失败: {e}")


def _print_missing_key_hint(key: str, reason: str = "", url: str = ""):
    """打印缺失 API Key 的友好提示"""

    console.print()
    hint_lines = (
        f"[dim]推荐:[/dim] {key.split('_')[0].title()} — {reason}\n\n" if reason else ""
    )
    url_line = f"[dim]获取地址:[/dim] {url}" if url else ""
    console.print(
        Panel(
            f"[bold red]✗ 未找到 {key}[/bold red]\n\n"
            f"[yellow]请先配置 API Key[/yellow]\n\n"
            f"{hint_lines}"
            f"[cyan]方法一:[/cyan] 设置环境变量\n"
            f"  [green]export {key}=your_key_here[green]\n\n"
            f"[cyan]方法二:[/cyan] 写入 .env 文件\n"
            f"  [green]echo '{key}=your_key_here' >> .env[green]\n\n"
            f"{url_line}",
            title="⚠️ 缺少 API Key",
            border_style="red",
        )
    )
    console.print()


def _print_fatal(msg: str, hint: str = ""):
    """打印致命错误并退出"""

    console.print()
    console.print(
        Panel(
            f"[bold red]✗ {msg}[/bold red]"
            + (f"\n\n[cyan]提示:[/cyan] {hint}" if hint else ""),
            title="❌ 执行失败",
            border_style="red",
        )
    )
    console.print()


def _check_env() -> bool:
    """检查当前默认模型的 API Key 是否就绪，返回 True 表示就绪"""
    user_config = _load_config()
    default_model = _resolve_default_model(user_config)
    api_key = _get_api_key(user_config, default_model)
    if not api_key:
        api_key_hint_map = {
            "deepseek": ("DEEPSEEK_API_KEY", "性价比最高，推荐配置"),
            "glm": ("ZHIPUAI_API_KEY", "智谱 GLM 模型"),
            "kimi": ("KIMI_API_KEY", "月之暗面 Kimi"),
            "doubao": ("DOUBAO_API_KEY", "字节豆包"),
            "minimax": ("MINIMAX_API_KEY", "MiniMax"),
            "tongyi": ("DASHSCOPE_API_KEY", "通义千问"),
            "wenxin": ("ERNIE_API_KEY", "文心一言"),
            "hunyuan": ("HUNYUAN_API_KEY", "腾讯混元"),
        }
        hint = api_key_hint_map.get(default_model)
        if hint:
            _print_missing_key_hint(hint[0], hint[1])
        else:
            _print_missing_key_hint(f"{default_model.upper()}_API_KEY", "")
        return False
    return True


def _display_result(result):
    """显示工作流结果"""
    console.print(f"\n[bold]工作流 {result.workflow_id}[/bold]")
    console.print(f"状态: {_status_color(result.status.value)}")
    console.print(f"执行时间: {result.execution_time:.2f}s")
    console.print(f"Token 使用: {result.total_tokens:,}")

    # 显示每个 Agent 的实际输出
    if result.outputs:
        for agent_name, output in result.outputs.items():
            if hasattr(output, 'result') and output.result:
                console.print(f"\n[bold]📋 {agent_name} 输出:[/bold]")
                # 使用 Panel 美化显示
                console.print(
                    Panel(
                        output.result[:2000] + ("..." if len(output.result) > 2000 else ""),
                        title=f"{agent_name} 结果",
                        border_style="cyan",
                    )
                )
                # 如果结果太长，提示查看完整文件
                if len(output.result) > 2000:
                    console.print(
                        f"[dim]💡 完整结果已保存至: .omc/state/workflow_{result.workflow_id}.json[/dim]"
                    )

    if result.steps_completed:
        console.print("\n[green]✓ 已完成步骤:[/green]")
        for step in result.steps_completed:
            console.print(f"  - {step}")

    if result.steps_failed:
        console.print("\n[red]✗ 失败步骤:[/red]")
        for step in result.steps_failed:
            console.print(f"  - {step}")

    if result.error:
        console.print(f"\n[red]错误: {result.error}[/red]")
        console.print(
            f"\n[cyan]💡 详细日志:[/cyan] .omc/state/workflow_{result.workflow_id}.json"
        )


def _display_cross_validation_result(result):
    """显示交叉验证结果"""

    status_color = {
        "pass": "green",
        "fail": "red",
        "need_fix": "yellow",
        "skipped": "dim",
    }.get(result.status.value, "white")

    status_icon = {
        "pass": "✅",
        "fail": "❌",
        "need_fix": "⚠️",
        "skipped": "⏭",
    }.get(result.status.value, "?")

    panel_color = {
        "pass": "green",
        "fail": "red",
        "need_fix": "yellow",
        "skipped": "dim",
    }.get(result.status.value, "white")

    lines = [
        f"**验证 ID**: `{result.validation_id}`",
        f"**工作流**: `{result.workflow_name}` (`{result.workflow_id}`)",
        f"**状态**: [{status_color}]{result.status.value.upper()}[/{status_color}]",
        f"**发现的问题**: {len(result.issues)} 个",
        f"**验证耗时**: {result.execution_time:.1f}s",
    ]

    if result.issues:
        lines.append("")
        lines.append("[bold]问题列表:[/bold]")
        for i, issue in enumerate(result.issues, 1):
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "⚪",
            }.get(issue.severity.value, "⚪")
            lines.append(
                f"{i}. {severity_icon} **[{issue.severity.value.upper()}]**"
                f"[{issue.category}] {issue.description}"
            )
            if issue.location:
                lines.append(f"   📍 {issue.location}")
            if issue.suggestion:
                lines.append(f"   💡 {issue.suggestion}")

    panel_title = f"{status_icon} 交叉验证结果"

    console.print(
        Panel.fit("\n".join(lines), title=panel_title, border_style=panel_color)
    )


def _status_color(status: str) -> str:
    """给状态上色"""
    colors = {
        "completed": "[green]已完成[/green]",
        "failed": "[red]失败[/red]",
        "running": "[yellow]运行中[/yellow]",
        "pending": "[dim]等待中[/dim]",
    }
    return colors.get(status, status)
