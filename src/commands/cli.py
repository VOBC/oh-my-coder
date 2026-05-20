from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Oh My Coder CLI - 命令行入口

使用 typer 构建友好的 CLI 界面。

主要命令：
- omc run <task>         # 执行任务
- omc explore            # 探索代码库
- omc wiki               # 生成项目 Wiki
- omc agents             # 列出所有 Agent
- omc status             # 查看状态
- omc --version          # 显示版本
- omc --help             # 帮助信息
"""


import os
from pathlib import Path

import typer

# ============================================================
# 启动时加载环境变量（优先级：用户级 > 项目级）
# ============================================================
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.capabilities import app as cap_app

from .cli_checkpoint import app as checkpoint_app
from .cli_commands import app as commands_app
from .cli_config import app as config_app
from .cli_config_ext import app as config_ext_app
# merged into cli_usage
# from .cli_context import context_app
from .cli_doctor import app as doctor_app
from .cli_lsp import app as lsp_app
from .cli_mcp import app as mcp_app
# merged into cli_usage
# from .cli_memory import app as memory_app
from .cli_migrate import app as migrate_app
from .cli_multiagent import app as multiagent_app
from .cli_package_manager import app as pkg_app
from .cli_profile import app as profile_app
from .cli_quality import app as quality_app
from .cli_review import app as review_app
from .cli_run import (
    _init_router,
    explore,
    run,
    wiki,
)
from .cli_search import app as search_app
from .cli_security import app as security_app
from .cli_self_config import app as self_config_app
from .cli_server import app as server_app
from .cli_skill import app as skill_app
from .cli_task import app as task_app
# merged into cli_usage
# from .cli_thought import app as thought_app
# merged into cli_usage
# from .cli_trace import app as trace_app
from .cli_tui import app as tui_app
from .cli_usage import app as usage_app

# 用户级配置 ~/.omc/.env（最高优先级）
_user_env = Path.home() / ".omc" / ".env"
if _user_env.exists():
    load_dotenv(_user_env, override=True)

# 项目级配置 .env（次优先级）
_project_env = Path(".env")
if _project_env.exists():
    load_dotenv(_project_env, override=True)

# 版本信息
__version__ = "0.2.0"
__author__ = "VOBC"
__repo__ = "https://github.com/VOBC/oh-my-coder"

app = typer.Typer(
    name="omc",
    help=f"Oh My Coder v{__version__} - 多智能体 AI 编程助手",
    add_completion=False,
    no_args_is_help=True,
)

# 注册子命令
# merged into usage
# app.add_typer(context_app, name="context")
app.add_typer(config_ext_app, name="agent-config")
app.add_typer(task_app, name="task")
app.add_typer(multiagent_app, name="multiagent")
app.add_typer(security_app, name="security")
app.add_typer(checkpoint_app, name="checkpoint")
app.add_typer(mcp_app, name="mcp")
app.add_typer(
    skill_app, name="skill", help="Skill 系统 - 内置和自定义 Skill 管理与执行"
)
# merged into usage
# app.add_typer(trace_app, name="trace", help="Trace 执行记录 - 查看 Agent 执行过程")
# merged into usage
# app.add_typer(memory_app, name="memory", help="分层记忆管理 - 查看核心/精选/完整记忆")
app.add_typer(usage_app, name="usage", help="用量统计与追踪 - stats/trace/memory")
app.add_typer(migrate_app, name="migrate", help="记忆迁移 - 从 Claude/Gemini 导入配置")
app.add_typer(tui_app, name="tui", help="TUI 交互界面 - 简易终端交互")
app.add_typer(
    self_config_app, name="self-config", help="自配置 - 自然语言配置 API Key/模型/代理"
)
app.add_typer(doctor_app, name="doctor", help="环境诊断 - 检查常见问题并给出修复建议")
app.add_typer(commands_app, name="cmd", help="命令系统 - 运行自定义 Markdown 命令")
app.add_typer(pkg_app, name="pkg", help="包管理器 - Homebrew/npm/scoop/winget/AUR")
app.add_typer(lsp_app, name="lsp", help="LSP 集成 - 读取代码诊断信息")
app.add_typer(search_app, name="search", help="代码搜索 - Sourcegraph 公开代码库搜索")
app.add_typer(review_app, name="review", help="代码审查 - 智能分析代码变更")
app.add_typer(quality_app, name="quality", help="代码质量检查 - ruff/black 集成")
app.add_typer(profile_app, name="profile", help="Profile 隔离 - 子 Agent 上下文管理")
app.add_typer(server_app, name="server", help="远程 Server - HTTP REST API 服务")
# merged into cli_usage
# app.add_typer(thought_app, name="thought", help="思维链 - 记录和可视化 Agent 推理过程")

# 代码清理命令
try:
    from .cli_clean import app as clean_app

    app.add_typer(clean_app, name="clean", help="代码清理 - 检测和清理冗余代码")
except Exception:
    pass

# 成本优化命令
try:
    from .cli_cost import app as cost_app

    app.add_typer(cost_app, name="cost", help="成本优化 - 根据任务推荐最优模型")
except Exception:
    pass

# 本地模型命令
try:
    from .cli_local_models import app as local_models_app

    app.add_typer(
        local_models_app, name="local", help="本地模型管理 - Ollama 零成本运行"
    )
except Exception:
    pass

# model 子命令
from .cli_model import app as model_app  # noqa: E402

app.add_typer(model_app, name="model", help="模型管理 - 查看/切换默认模型")

# models 子命令 - 模型配置分享
try:
    from .cli_models import app as models_app  # noqa: E402

    app.add_typer(models_app, name="models", help="模型配置分享 - 分享/浏览社区配置")
except Exception:
    pass

# gateway 子命令（懒导入，避免 gateway 依赖缺失时报错）
try:
    from .cli_gateway import app as gateway_app  # noqa: E402

    app.add_typer(gateway_app, name="gateway", help="多平台网关 - Telegram / Discord")
except Exception:
    pass  # gateway 依赖缺失时跳过

# doc 子命令 - 文档管理
try:
    from .cli_doc import app as doc_app  # noqa: E402

    app.add_typer(doc_app, name="doc", help="文档管理 - 生成、验证、同步项目文档")
except Exception:
    pass

# agent 子命令 - Agent 配置管理与自进化
try:
    from .cli_agent import app as agent_app  # noqa: E402

    app.add_typer(agent_app, name="agent", help="Agent 管理 - 导出/导入/进化")
except Exception:
    pass

# template 子命令 - 工作流模板
try:
    from .cli_template import app as template_app  # noqa: E402

    app.add_typer(template_app, name="template", help="工作流模板 - 列出/使用模板")
except Exception:
    pass

# monorepo 子命令 - 工作区感知
try:
    from .cli_monorepo import app as monorepo_app  # noqa: E402

    app.add_typer(
        monorepo_app, name="monorepo", help="Monorepo 支持 - pnpm/lerna/nx 工作区感知"
    )
except Exception:
    pass

# init 子命令 - 交互式初始化引导
try:
    from .cli_init import app as init_app  # noqa: E402

    app.add_typer(init_app, name="init", help="初始化引导 - 交互式配置 oh-my-coder")
except Exception:
    pass

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="显示版本信息",
        is_eager=True,
    ),
):
    """Oh My Coder - 多智能体 AI 编程助手"""
    if version:
        _print_version()
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                f"[bold cyan]Oh My Coder[/bold cyan] v{__version__}\n"
                f"[dim]多智能体 AI 编程助手[/dim]\n\n"
                f"[dim]使用 [bold]omc --help[/bold] 查看所有命令[/dim]\n"
                f"[dim]仓库: {__repo__}[/dim]",
                border_style="cyan",
            )
        )
        raise typer.Exit(0)


def _print_version():
    """打印版本信息"""
    console.print(
        f"[bold cyan]oh-my-coder[/bold cyan] version [green]{__version__}[/green]"
    )
    console.print(f"[dim]Author: {__author__}[/dim]")
    console.print(f"[dim]Repo: {__repo__}[/dim]")


# ============================================================
# 顶级命令（从 cli_run 导入）
# ============================================================
app.command()(run)
app.command()(explore)
app.command()(wiki)


# ============================================================
# Quest Mode 命令（从 cli_quest 导入）
# ============================================================
from src.commands.cli_quest import (
    quest,
    quest_cancel,
    quest_exec,
    quest_list,
    quest_notify,
    quest_pause,
    quest_resume,
    quest_status,
    quest_wait,
)

app.command()(quest)
app.command("quest-list")(quest_list)
app.command("quest-status")(quest_status)
app.command("quest-exec")(quest_exec)
app.command("quest-cancel")(quest_cancel)
app.command("quest-pause")(quest_pause)
app.command("quest-resume")(quest_resume)
app.command("quest-notify")(quest_notify)
app.command("quest-wait")(quest_wait)


@app.command()
def agents():
    """列出所有可用 Agent"""
    table = Table(title="可用智能体")
    table.add_column("名称", style="cyan")
    table.add_column("描述")
    table.add_column("层级", style="green")

    # 导入所有 Agent
    from src.agents import (
        AnalystAgent,
        APIAgent,
        ArchitectAgent,
        AuthAgent,
        CodeReviewerAgent,
        CodeSimplifierAgent,
        CriticAgent,
        DataAgent,
        DatabaseAgent,
        DebuggerAgent,
        DesignerAgent,
        DevOpsAgent,
        DocumentAgent,
        ExecutorAgent,
        ExploreAgent,
        GitMasterAgent,
        MigrationAgent,
        PerformanceAgent,
        PlannerAgent,
        PromptAgent,
        QATesterAgent,
        ScientistAgent,
        SecurityReviewerAgent,
        SelfImprovingAgent,
        SkillManageAgent,
        TestEngineerAgent,
        TracerAgent,
        UMLAgent,
        VerifierAgent,
        VisionAgent,
        WriterAgent,
    )

    agents_list = [
        ("explore", ExploreAgent.description, ExploreAgent.default_tier),
        ("analyst", AnalystAgent.description, AnalystAgent.default_tier),
        ("planner", PlannerAgent.description, PlannerAgent.default_tier),
        ("architect", ArchitectAgent.description, ArchitectAgent.default_tier),
        ("executor", ExecutorAgent.description, ExecutorAgent.default_tier),
        ("verifier", VerifierAgent.description, VerifierAgent.default_tier),
        (
            "test-engineer",
            TestEngineerAgent.description,
            TestEngineerAgent.default_tier,
        ),
        (
            "code-reviewer",
            CodeReviewerAgent.description,
            CodeReviewerAgent.default_tier,
        ),
        ("debugger", DebuggerAgent.description, DebuggerAgent.default_tier),
        ("tracer", TracerAgent.description, TracerAgent.default_tier),
        ("critic", CriticAgent.description, CriticAgent.default_tier),
        ("writer", WriterAgent.description, WriterAgent.default_tier),
        ("designer", DesignerAgent.description, DesignerAgent.default_tier),
        (
            "security-reviewer",
            SecurityReviewerAgent.description,
            SecurityReviewerAgent.default_tier,
        ),
        ("git-master", GitMasterAgent.description, GitMasterAgent.default_tier),
        (
            "code-simplifier",
            CodeSimplifierAgent.description,
            CodeSimplifierAgent.default_tier,
        ),
        ("scientist", ScientistAgent.description, ScientistAgent.default_tier),
        ("qa-tester", QATesterAgent.description, QATesterAgent.default_tier),
        ("database", DatabaseAgent.description, DatabaseAgent.default_tier),
        ("api", APIAgent.description, APIAgent.default_tier),
        ("devops", DevOpsAgent.description, DevOpsAgent.default_tier),
        ("uml", UMLAgent.description, UMLAgent.default_tier),
        ("performance", PerformanceAgent.description, PerformanceAgent.default_tier),
        ("migration", MigrationAgent.description, MigrationAgent.default_tier),
        ("prompt", PromptAgent.description, PromptAgent.default_tier),
        ("vision", VisionAgent.description, VisionAgent.default_tier),
        ("auth", AuthAgent.description, AuthAgent.default_tier),
        ("data", DataAgent.description, DataAgent.default_tier),
        (
            "self-improving",
            SelfImprovingAgent.description,
            SelfImprovingAgent.default_tier,
        ),
        (
            "skill-manage",
            SkillManageAgent.description,
            SkillManageAgent.default_tier,
        ),
        (
            "document",
            DocumentAgent.description,
            DocumentAgent.default_tier,
        ),
    ]

    for name, desc, tier in agents_list:
        table.add_row(name, desc, tier)

    console.print(table)

    console.print(f"\n[dim]共 {len(agents_list)} 个智能体[/dim]")


@app.command()
def status():
    """查看系统状态"""
    console.print("[bold]系统状态[/bold]\n")

    # 检查 API Key
    api_keys = {
        "DEEPSEEK_API_KEY": "🟢 生产就绪",
        "KIMI_API_KEY": "🟢 生产就绪",
        "DOUBAO_API_KEY": "🟢 生产就绪",
        "MINIMAX_API_KEY": "🟡 Beta",
        "ZHIPUAI_API_KEY": "🟡 Beta",
        "TONGYI_API_KEY": "🟡 Beta",
        "WENXIN_API_KEY": "🔴 待完善",
        "HUNYUAN_API_KEY": "🔴 待完善",
    }

    console.print("[bold]模型支持状态:[/bold]")
    for key, status_label in api_keys.items():
        value = os.getenv(key)
        if value:
            console.print(f"  {key}: [{status_label}] 已配置")
        else:
            console.print(f"  {key}: [red]✗ 未配置[/red]")

    # 检查路由器
    console.print()
    try:
        router = _init_router()
        stats = router.get_stats()
        console.print(
            Panel(
                f"[green]✓ 路由器就绪[/green]\n"
                f"总请求数: [cyan]{stats['total_requests']}[/cyan]\n"
                f"总成本:   [cyan]¥{stats['total_cost']:.4f}[/cyan]",
                title="路由器",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(
            Panel(
                f"[red]✗ 路由器初始化失败[/red]\n\n{e}",
                title="路由器",
                border_style="red",
            )
        )


def _mask_secret(value: str) -> str:
    """脱敏显示密钥"""
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


# 注册子命令
app.add_typer(cap_app, name="cap", help="能力包管理 - 导出、导入和分享 Agent 配置")
app.add_typer(config_app, name="config", help="⚙️ 配置管理")

if __name__ == "__main__":
    app()
