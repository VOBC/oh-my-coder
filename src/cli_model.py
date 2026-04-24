"""
Model CLI - 模型切换 + Catwalk 模型仓库

命令：
- omc model list [--extended]  # 列出模型（普通/详细）
- omc model current            # 显示当前模型
- omc model switch <name>      # 切换默认模型
- omc model catwalk            # 交互式浏览模型（Catwalk）
- omc model import <url>      # 从 URL 导入模型配置
- omc model export <name> [--yaml]  # 导出模型配置
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

# 导入模型发现模块
try:
    from model_discovery import ModelDiscovery, get_discovery_summary
except ImportError:
    try:
        from src.model_discovery import ModelDiscovery, get_discovery_summary
    except ImportError:
        ModelDiscovery = None
        get_discovery_summary = None

console = Console()

app = typer.Typer(
    name="model",
    help="模型管理 - 查看/切换默认模型，浏览社区模型仓库（Catwalk）",
    add_completion=False,
)

# 配置文件路径
CONFIG_DIR = Path.home() / ".config" / "oh-my-coder"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Catwalk 模型仓库目录（项目内嵌 + 用户扩展）
CATWALK_DIR = Path(__file__).parent.parent / "models"
USER_MODELS_DIR = Path.home() / ".omc" / "models"

# 内置模型信息（Tier 1 - 免费/低成本）
SUPPORTED_MODELS = {
    # 低成本/免费模型
    "deepseek": {"name": "DeepSeek", "tier": "low", "note": "高性价比，推荐"},
    "glm": {"name": "智谱 GLM", "tier": "low", "note": "GLM-4-Flash 免费使用"},
    # 主流模型
    "wenxin": {"name": "文心一言", "tier": "medium", "note": "百度"},
    "tongyi": {"name": "通义千问", "tier": "medium", "note": "阿里"},
    "minimax": {"name": "MiniMax", "tier": "medium", "note": ""},
    "kimi": {"name": "Kimi", "tier": "medium", "note": "月之暗面"},
    "hunyuan": {"name": "腾讯混元", "tier": "medium", "note": "腾讯"},
    "doubao": {"name": "字节豆包", "tier": "medium", "note": "字节跳动"},
    # 其他模型
    "tiangong": {"name": "天工 AI", "tier": "medium", "note": ""},
    "spark": {"name": "讯飞星火", "tier": "medium", "note": ""},
    "baichuan": {"name": "百川智能", "tier": "medium", "note": ""},
    "mimo": {"name": "小米 MiMo", "tier": "medium", "note": "小米"},
}


# =============================================================================
# 工具函数
# =============================================================================


def _ensure_config_dir() -> None:
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict) -> None:
    """保存配置文件"""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _get_current_model() -> str:
    """获取当前默认模型"""
    env_model = os.getenv("OMC_DEFAULT_MODEL")
    if env_model:
        return env_model
    config = _load_config()
    return config.get("default_model", "deepseek")


def _get_current_api_key(model_id: str) -> str | None:
    """获取当前模型的 API Key（从环境变量推断）"""
    key_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "glm": "ZHIPU_API_KEY",
        "wenxin": "ERNIE_API_KEY",
        "tongyi": "DASHSCOPE_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "kimi": "KIMI_API_KEY",
        "hunyuan": "HUNYUAN_API_KEY",
        "doubao": "DOUBAO_API_KEY",
        "tiangong": "TIANGONG_API_KEY",
        "spark": "SPARK_API_KEY",
        "baichuan": "BAICHUAN_API_KEY",
        "mimo": "MIMO_API_KEY",
    }
    env_var = key_map.get(model_id)
    if env_var:
        return os.getenv(env_var)
    return None


def _tier_style(tier: str) -> str:
    """根据 tier 返回颜色"""
    return {"free": "green", "low": "cyan", "medium": "yellow", "high": "red"}.get(
        tier, "white"
    )


# =============================================================================
# YAML 模型配置管理
# =============================================================================


def _list_yaml_configs() -> list[dict[str, Any]]:
    """扫描所有 YAML 模型配置文件"""
    configs: list[dict[str, Any]] = []

    for models_dir in [CATWALK_DIR, USER_MODELS_DIR]:
        if not models_dir.exists():
            continue
        for yaml_file in sorted(models_dir.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    data["_source"] = (
                        "user" if models_dir == USER_MODELS_DIR else "builtin"
                    )
                    data["_file"] = yaml_file.name
                    configs.append(data)
            except Exception:
                continue

    return configs


def _validate_model_config(data: dict) -> tuple[bool, str]:
    """验证模型配置是否合法"""
    required = ["name", "provider", "model"]
    for field in required:
        if field not in data:
            return False, f"缺少必填字段: {field}"

    valid_tiers = ["free", "low", "medium", "high"]
    tier = data.get("tier", "medium")
    if tier not in valid_tiers:
        return False, f"tier 必须是 {valid_tiers} 之一，当前: {tier}"

    valid_providers = [
        "deepseek",
        "glm",
        "wenxin",
        "tongyi",
        "minimax",
        "kimi",
        "hunyuan",
        "doubao",
        "baichuan",
        "tiangong",
        "spark",
        "mimo",
        "openai",
        "anthropic",
        "google",
    ]
    provider = data.get("provider", "")
    if provider not in valid_providers:
        return False, f"provider '{provider}' 不在支持列表中"

    return True, "OK"


def _save_model_config(data: dict) -> Path:
    """保存模型配置到用户目录，返回保存路径"""
    USER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    # 文件名：provider-model.yaml
    filename = f"{data['provider']}-{data['model'].replace('/', '-')}.yaml"
    filepath = USER_MODELS_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
    return filepath


# =============================================================================
# 内置 Catwalk 模型配置数据（10+ 个）
# =============================================================================

# 内嵌模型数据，避免依赖外部 models/ 目录
BUILTIN_CATWALK_MODELS: list[dict[str, Any]] = [
    {
        "name": "DeepSeek V3",
        "provider": "deepseek",
        "api_key_env": "DEEPSEEK_API_KEY",
        "endpoint": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "tier": "low",
        "pricing": {"input": 2, "output": 8},
        "context": 64000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "DeepSeek R1",
        "provider": "deepseek",
        "api_key_env": "DEEPSEEK_API_KEY",
        "endpoint": "https://api.deepseek.com",
        "model": "deepseek-reasoner",
        "tier": "low",
        "pricing": {"input": 16, "output": 60},
        "context": 64000,
        "features": ["reasoning", "function_call", "streaming"],
    },
    {
        "name": "GLM-4-Flash",
        "provider": "glm",
        "api_key_env": "ZHIPU_API_KEY",
        "endpoint": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "tier": "free",
        "pricing": {"input": 0, "output": 0},
        "context": 128000,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "GLM-4V-Flash",
        "provider": "glm",
        "api_key_env": "ZHIPU_API_KEY",
        "endpoint": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4v-flash",
        "tier": "free",
        "pricing": {"input": 0, "output": 0},
        "context": 128000,
        "features": ["vision", "streaming"],
    },
    {
        "name": "MiMo V2 Flash",
        "provider": "mimo",
        "api_key_env": "MIMO_API_KEY",
        "endpoint": "https://api.minimax.chat/v1",
        "model": "MiniMax-Text-01",
        "tier": "free",
        "pricing": {"input": 0, "output": 0},
        "context": 1000000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "文心一言 4.0",
        "provider": "wenxin",
        "api_key_env": "ERNIE_API_KEY",
        "endpoint": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1",
        "model": "ernie-4.0-8k-latest",
        "tier": "medium",
        "pricing": {"input": 120, "output": 120},
        "context": 8000,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "通义千问 2.5",
        "provider": "tongyi",
        "api_key_env": "DASHSCOPE_API_KEY",
        "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "tier": "medium",
        "pricing": {"input": 60, "output": 180},
        "context": 131072,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "Kimi 128K",
        "provider": "kimi",
        "api_key_env": "KIMI_API_KEY",
        "endpoint": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-128k",
        "tier": "medium",
        "pricing": {"input": 60, "output": 240},
        "context": 128000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "豆包 Doubao-Pro",
        "provider": "doubao",
        "api_key_env": "DOUBAO_API_KEY",
        "endpoint": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-pro-32k",
        "tier": "medium",
        "pricing": {"input": 30, "output": 30},
        "context": 32000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "混元 Turbo",
        "provider": "hunyuan",
        "api_key_env": "HUNYUAN_APP_ID",
        "endpoint": "https://hunyuan.cloud.tencent.com",
        "model": "hunyuan-turbo",
        "tier": "medium",
        "pricing": {"input": 100, "output": 100},
        "context": 128000,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "MiniMax text-01",
        "provider": "minimax",
        "api_key_env": "MINIMAX_API_KEY",
        "endpoint": "https://api.minimax.chat/v1",
        "model": "MiniMax-Text-01",
        "tier": "low",
        "pricing": {"input": 10, "output": 10},
        "context": 1000000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "天工 3.0",
        "provider": "tiangong",
        "api_key_env": "TIANGONG_API_KEY",
        "endpoint": "https://api.tiangong.cn/v1",
        "model": "tiangong-3",
        "tier": "medium",
        "pricing": {"input": 50, "output": 50},
        "context": 128000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "讯飞星火 4.0",
        "provider": "spark",
        "api_key_env": "SPARK_API_KEY",
        "endpoint": "https://spark-api.xf-yun.com/v4.0/chat",
        "model": "generalv4.0",
        "tier": "medium",
        "pricing": {"input": 80, "output": 80},
        "context": 128000,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "百川 4",
        "provider": "baichuan",
        "api_key_env": "BAICHUAN_API_KEY",
        "endpoint": "https://api.baichuan-ai.com/v1",
        "model": "Baichuan4",
        "tier": "medium",
        "pricing": {"input": 120, "output": 120},
        "context": 128000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "GPT-4o-mini",
        "provider": "openai",
        "api_key_env": "OPENAI_API_KEY",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "tier": "high",
        "pricing": {"input": 21, "output": 84},
        "context": 128000,
        "features": ["function_call", "vision", "streaming"],
    },
    {
        "name": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "api_key_env": "ANTHROPIC_API_KEY",
        "endpoint": "https://api.anthropic.com/v1",
        "model": "claude-3-5-haiku-20241022",
        "tier": "high",
        "pricing": {"input": 11, "output": 55},
        "context": 200000,
        "features": ["function_call", "streaming"],
    },
    {
        "name": "Gemini 2.0 Flash",
        "provider": "google",
        "api_key_env": "GOOGLE_API_KEY",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-2.0-flash",
        "tier": "low",
        "pricing": {"input": 0, "output": 0},
        "context": 1000000,
        "features": ["function_call", "vision", "streaming"],
    },
]


# =============================================================================
# 命令实现
# =============================================================================


@app.command("list")
def list_models(
    extended: bool = typer.Option(
        False, "--extended", "-e", help="显示完整 YAML 配置详情（Catwalk 模式）"
    ),
    tier: str = typer.Option(None, "--tier", help="按层级过滤: free/low/medium/high"),
    provider: str = typer.Option(None, "--provider", "-p", help="按供应商过滤"),
    status: str = typer.Option(
        None,
        "--status",
        help="按就绪状态过滤: production/beta/deprecated/all (默认 production)",
    ),
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="显示全部模型（含 beta/deprecated，等效于 --status all）",
    ),
    beta: bool = typer.Option(False, "--beta", "-b", help="显示 beta 模型"),
    json_output: bool = typer.Option(False, "--json", help="JSON 输出"),
    source: str = typer.Option(
        None, "--source", "-s", help="数据源: builtin(内置)/user(用户)/all"
    ),
) -> None:
    """列出所有可用模型（支持 Catwalk 详细视图）"""
    from src.models import (
        enrich_with_status,
        filter_by_status,
        get_model_status,
    )  # noqa: E402

    # Resolve effective status filter
    if all or status == "all":
        _show_prod, _show_beta, _show_dep = True, True, True
    elif beta or status == "beta":
        _show_prod, _show_beta, _show_dep = False, True, False
    elif status == "deprecated":
        _show_prod, _show_beta, _show_dep = False, False, True
    elif status in ("production", None):
        _show_prod, _show_beta, _show_dep = True, False, False
    else:
        _show_prod, _show_beta, _show_dep = True, False, False

    if extended or json_output:
        # Catwalk 详细模式
        all_configs: list[dict[str, Any]] = []

        # 内嵌数据
        for cfg in BUILTIN_CATWALK_MODELS:
            cfg_copy = dict(cfg)
            cfg_copy["_source"] = "builtin"
            all_configs.append(cfg_copy)

        # YAML 文件（用户自定义）
        for cfg in _list_yaml_configs():
            all_configs.append(cfg)

        # Enrich with status metadata
        all_configs = enrich_with_status(all_configs)

        # Filter
        if tier:
            all_configs = [c for c in all_configs if c.get("tier") == tier]
        if provider:
            all_configs = [c for c in all_configs if c.get("provider") == provider]
        if source:
            all_configs = [c for c in all_configs if c.get("_source") == source]

        # Apply status filter (not combined with source/tier/provider)
        if status or all or beta:
            all_configs = filter_by_status(
                all_configs,
                show_production=_show_prod,
                show_beta=_show_beta,
                show_deprecated=_show_dep,
            )
        else:
            # Default: production only
            all_configs = filter_by_status(
                all_configs,
                show_production=True,
                show_beta=False,
                show_deprecated=False,
            )

        if json_output:
            # JSON 输出（供 AI 消费）
            import json

            out = []
            for cfg in all_configs:
                out.append(
                    {
                        "name": cfg.get("name"),
                        "provider": cfg.get("provider"),
                        "model": cfg.get("model"),
                        "endpoint": cfg.get("endpoint"),
                        "tier": cfg.get("tier"),
                        "pricing": cfg.get("pricing", {}),
                        "context": cfg.get("context"),
                        "features": cfg.get("features", []),
                        "source": cfg.get("_source"),
                        "model_status": cfg.get("model_status", "beta"),
                    }
                )
            console.print_json(json.dumps(out, ensure_ascii=False, indent=2))
            return

        # 详细表格
        table = Table(
            title=f"Catwalk 模型仓库（共 {len(all_configs)} 个模型）",
            show_lines=True,
        )
        table.add_column("模型", style="cyan", no_wrap=False)
        table.add_column("供应商", style="blue")
        table.add_column("Tier", style="yellow", no_wrap=True)
        table.add_column("就绪", style="magenta", no_wrap=True)
        table.add_column("价格（元/百万token）", style="dim")
        table.add_column("上下文", style="green")
        table.add_column("来源", style="white")

        current = _get_current_model()

        for cfg in all_configs:
            pricing = cfg.get("pricing", {})
            in_p = pricing.get("input", "-")
            out_p = pricing.get("output", "-")
            price_str = f"{in_p}/{out_p}" if in_p != "-" else "-"

            features = ", ".join(cfg.get("features", [])[:3])
            tier_label = cfg.get("tier", "medium")
            source_label = cfg.get("_source", "builtin")

            # Status badge
            raw_status = cfg.get("model_status", "beta")
            status_badge = {
                "production": "✅生产",
                "beta": "🔶Beta",
                "deprecated": "⛔废弃",
            }.get(raw_status, raw_status)

            # 高亮当前模型
            provider_id = cfg.get("provider", "")
            is_current = "★" if provider_id == current else ""

            table.add_row(
                f"{cfg.get('name', '')} {is_current}",
                cfg.get("provider", ""),
                tier_label,
                status_badge,
                price_str,
                str(cfg.get("context", "-")),
                source_label,
            )

        console.print(table)
        console.print()
        console.print(
            f"[dim]内置: {len([c for c in all_configs if c.get('_source') == 'builtin'])} 个 | "
            f"用户: {len([c for c in all_configs if c.get('_source') == 'user'])} 个[/dim]"
        )
        console.print(f"[dim]内置模型目录: {CATWALK_DIR}（只读）[/dim]")
        console.print(f"[dim]用户模型目录: {USER_MODELS_DIR}[/dim]")
        console.print("[dim]提示: 使用 [cyan]omc model catwalk[/cyan] 交互式浏览[/dim]")
    else:
        # 简单模式
        table = Table(title="支持的模型列表")
        table.add_column("模型 ID", style="cyan")
        table.add_column("名称", style="green")
        table.add_column("层级", style="yellow")
        table.add_column("就绪", style="magenta")
        table.add_column("当前", style="white")

        current = _get_current_model()

        for model_id, info in SUPPORTED_MODELS.items():
            is_current = "★" if model_id == current else ""
            status_raw = get_model_status(model_id)
            status_map = {
                "production": "✅生产",
                "beta": "🔶Beta",
                "deprecated": "⛔废弃",
            }
            status_str = status_map.get(status_raw, status_raw)
            # Filtering logic:
            # --all: show all; --beta: show only beta; default: production only
            if beta:
                if status_raw != "beta" and status_raw != "deprecated":
                    continue
            elif not all:
                if status_raw != "production":
                    continue
            table.add_row(
                model_id,
                info["name"],
                info["tier"],
                status_str,
                is_current,
            )

        console.print(table)
        console.print()
        console.print(f"[dim]配置文件: {CONFIG_FILE}[/dim]")
        console.print(f"[dim]当前模型: {current}[/dim]")
        console.print("[dim]使用 [cyan]--extended[/cyan] 查看 Catwalk 详细模式[/dim]")

        # 检查新模型（非阻塞，使用缓存或快速发现）
        if get_discovery_summary and not json_output:
            try:
                summary = get_discovery_summary(BUILTIN_CATWALK_MODELS)
                if summary.get("has_new"):
                    new_models = summary.get("new_models", [])
                    if new_models:
                        # 只显示前3个新模型
                        display_models = new_models[:3]
                        model_names = ", ".join(
                            [
                                f"{m['model_id']} ({m['provider']})"
                                for m in display_models
                            ]
                        )
                        if len(new_models) > 3:
                            model_names += f" 等 {len(new_models)} 个"
                        console.print()
                        console.print(
                            f"[bold yellow]💡 发现新模型:[/] [cyan]{model_names}[/]"
                        )
                        console.print(
                            "[dim]   运行 [cyan]omc model sync[/cyan] 查看详情并同步[/dim]"
                        )
            except Exception:
                # 静默失败，不影响主功能
                pass


@app.command("catwalk")
def catwalk(
    tier: str = typer.Option(
        None, "--tier", "-t", help="按层级过滤: free/low/medium/high"
    ),
    provider: str = typer.Option(None, "--provider", "-p", help="按供应商过滤"),
    search: str = typer.Option(None, "--search", "-s", help="搜索模型名称/特性"),
) -> None:
    """交互式浏览 Catwalk 模型仓库（交互模式）"""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]🐱 Catwalk 模型仓库[/bold cyan] — 社区驱动的模型配置共享",
            border_style="cyan",
        )
    )
    console.print()

    # 过滤数据
    models = list(BUILTIN_CATWALK_MODELS)

    if tier:
        models = [m for m in models if m.get("tier") == tier]
    if provider:
        models = [m for m in models if m.get("provider") == provider]
    if search:
        q = search.lower()
        models = [
            m
            for m in models
            if q in m.get("name", "").lower()
            or q in m.get("provider", "").lower()
            or any(q in f.lower() for f in m.get("features", []))
        ]

    if not models:
        console.print("[red]没有找到匹配的模型[/red]")
        return

    # 显示列表
    table = Table(
        title=f"共 {len(models)} 个模型（输入编号选择）",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("模型名称", style="cyan")
    table.add_column("供应商", style="blue")
    table.add_column("Tier", style="yellow")
    table.add_column("输入价格", style="magenta")
    table.add_column("上下文", style="green")
    table.add_column("特性", style="dim")

    for i, cfg in enumerate(models, 1):
        pricing = cfg.get("pricing", {})
        price_str = f"{pricing.get('input', '-')}元/MTok"
        features = ", ".join(cfg.get("features", [])[:2])

        table.add_row(
            str(i),
            cfg.get("name", ""),
            cfg.get("provider", ""),
            cfg.get("tier", "medium"),
            price_str,
            str(cfg.get("context", "-")),
            features,
        )

    console.print(table)
    console.print()

    # 交互选择
    choices = [str(i) for i in range(1, len(models) + 1)]
    choice = Prompt.ask(
        "[bold]输入编号选择模型[/bold]（回车退出，l=列表，s=保存）",
        default="",
    )

    if not choice.strip():
        return

    if choice.strip().lower() == "l":
        list_models(extended=True)
        return

    if choice.strip().lower() == "s":
        # 批量保存所有过滤后的模型
        USER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        for cfg in models:
            _save_model_config(cfg)
        console.print(
            f"[green]✓ 已保存 {len(models)} 个模型配置到 {USER_MODELS_DIR}[/green]"
        )
        return

    if choice in choices:
        idx = int(choice) - 1
        cfg = models[idx]

        # 显示详细信息
        console.print()
        console.print(
            Panel.fit(
                f"[bold cyan]{cfg['name']}[/bold cyan]",
                border_style="cyan",
            )
        )
        console.print()
        console.print(f"  [dim]供应商:[/] {cfg.get('provider')}")
        console.print(f"  [dim]Tier:[/]   {cfg.get('tier')}")
        console.print(f"  [dim]模型 ID:[/] {cfg.get('model')}")
        console.print(f"  [dim]端点:[/]   {cfg.get('endpoint')}")
        console.print(f"  [dim]上下文:[/] {cfg.get('context')} tokens")
        pricing = cfg.get("pricing", {})
        console.print(
            f"  [dim]价格:[/]   输入 {pricing.get('input', '-')} / 输出 {pricing.get('output', '-')} 元/百万token"
        )
        console.print(f"  [dim]特性:[/]   {', '.join(cfg.get('features', []))}")
        console.print()

        # 操作
        do_save = Confirm.ask(
            f"[bold]保存 '{cfg['name']}' 到用户模型库？[/bold]", default=True
        )
        if do_save:
            path = _save_model_config(cfg)
            console.print(f"[green]✓ 已保存到 {path}[/green]")

        do_switch = Confirm.ask(f"[bold]切换到 '{cfg['name']}'？[/bold]", default=False)
        if do_switch:
            provider_id = cfg.get("provider", "")
            # 找到对应的简短 ID
            for mid, minfo in SUPPORTED_MODELS.items():
                if minfo["name"] in cfg["name"] or mid == provider_id:
                    # 直接内联切换逻辑（避免循环导入）
                    config = _load_config()
                    config["default_model"] = mid
                    _save_config(config)
                    console.print(f"[green]✓ 已切换默认模型为 {mid}[/green]")
                    break
    else:
        console.print(f"[red]无效选择: {choice}[/red]")


@app.command("import")
def import_model(
    url: str = typer.Argument(..., help="模型配置的 YAML URL 或本地文件路径"),
    name: str = typer.Option(
        None, "--name", "-n", help="保存时的名称（默认从 URL 推断）"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="覆盖已存在的同名配置"),
) -> None:
    """从 URL 或本地文件导入 YAML 模型配置"""
    console.print(f"[dim]正在获取配置: {url}[/dim]")

    # 获取 YAML 内容
    if url.startswith("http://") or url.startswith("https://"):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "oh-my-coder/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8")
        except Exception as e:
            console.print(f"[red]✗ 获取失败: {e}[/red]")
            raise typer.Exit(1)
    else:
        # 本地文件
        filepath = Path(url)
        if not filepath.exists():
            console.print(f"[red]✗ 文件不存在: {url}[/red]")
            raise typer.Exit(1)
        content = filepath.read_text(encoding="utf-8")

    # 解析 YAML
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        console.print(f"[red]✗ YAML 解析失败: {e}[/red]")
        raise typer.Exit(1)

    if not isinstance(data, dict):
        console.print("[red]✗ YAML 内容不是字典格式的模型配置[/red]")
        raise typer.Exit(1)

    # 验证
    valid, msg = _validate_model_config(data)
    if not valid:
        console.print(f"[red]✗ 配置验证失败: {msg}[/red]")
        raise typer.Exit(1)

    # 检查重复
    existing = _list_yaml_configs()
    provider_model = f"{data['provider']}/{data['model']}"
    for cfg in existing:
        pm = f"{cfg.get('provider')}/{cfg.get('model')}"
        if pm == provider_model and not force:
            console.print(
                "[yellow]⚠ 同名配置已存在，使用 [cyan]--force[/cyan] 覆盖[/yellow]"
            )
            raise typer.Exit(1)

    # 保存
    path = _save_model_config(data)
    console.print(f"[green]✓ 已导入: {data['name']}[/green]")
    console.print(f"[dim]保存路径: {path}[/dim]")


@app.command("export")
def export_model(
    name: str = typer.Argument(..., help="模型名称（完整名称，如 'DeepSeek V3'）"),
    yaml_out: bool = typer.Option(False, "--yaml", help="输出 YAML 格式（默认 JSON）"),
    copy: bool = typer.Option(False, "--copy", help="复制配置文本到剪贴板"),
) -> None:
    """导出模型配置（支持 YAML/JSON）"""
    # 搜索
    target = None
    # 先在内嵌数据中查找
    for cfg in BUILTIN_CATWALK_MODELS:
        if name.lower() in cfg["name"].lower():
            target = dict(cfg)
            break
    # 再在用户配置中查找
    if target is None:
        for cfg in _list_yaml_configs():
            if name.lower() in cfg.get("name", "").lower():
                target = dict(cfg)
                break

    if target is None:
        console.print(f"[red]✗ 未找到模型: {name}[/red]")
        console.print(
            "[dim]使用 [cyan]omc model list --extended[/cyan] 查看所有模型[/dim]"
        )
        raise typer.Exit(1)

    # 移除内部字段
    target.pop("_source", None)
    target.pop("_file", None)

    if yaml_out:
        output = yaml.dump(
            target, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
    else:
        output = json.dumps(target, ensure_ascii=False, indent=2)

    if copy:
        try:
            import pyperclip

            pyperclip.copy(output)
            console.print("[green]✓ 已复制到剪贴板[/green]")
        except Exception:
            console.print("[yellow]⚠ pyperclip 未安装，复制功能不可用[/yellow]")
            console.print("[dim]pip install pyperclip[/dim]")
    else:
        console.print(output)


@app.command("current")
def show_current() -> None:
    """显示当前默认模型"""
    current = _get_current_model()
    info = SUPPORTED_MODELS.get(current, {})

    console.print()
    console.print(f"[bold cyan]当前模型:[/] [green]{current}[/]")

    if info:
        console.print(f"[bold cyan]名称:[/] {info.get('name', '-')}")
        console.print(f"[bold cyan]层级:[/] {info.get('tier', '-')}")
        console.print(f"[bold cyan]备注:[/] [dim]{info.get('note', '-')}[/dim]")

    api_key = _get_current_api_key(current)
    if api_key:
        console.print("[bold cyan]API Key:[/] [green]✓ 已配置[/green]")
    else:
        console.print("[bold cyan]API Key:[/] [red]✗ 未配置（需设置环境变量）[/red]")
    console.print()


@app.command("switch")
def switch_model_cmd(
    model_name: str = typer.Argument(..., help="模型 ID（如 deepseek, glm）"),
) -> None:
    """切换默认模型（写入配置文件，无需重启）"""
    if model_name not in SUPPORTED_MODELS:
        console.print(f"[red]错误: 不支持的模型 '{model_name}'[/red]")
        console.print()
        console.print("支持的模型:")
        for model_id in SUPPORTED_MODELS:
            console.print(f"  - {model_id}")
        raise typer.Exit(1)

    config = _load_config()
    old_model = config.get("default_model", "未设置")
    config["default_model"] = model_name
    _save_config(config)

    info = SUPPORTED_MODELS[model_name]
    console.print()
    console.print("[bold green]✓ 模型切换成功[/]")
    console.print(f"  [dim]旧模型:[/] {old_model}")
    console.print(f"  [dim]新模型:[/] {info['name']} ({model_name})")
    console.print(f"  [dim]配置文件:[/] {CONFIG_FILE}")
    console.print()
    console.print("[dim]提示: 环境变量 OMC_DEFAULT_MODEL 会覆盖配置文件[/dim]")


@app.command("sync")
def sync_models(
    force: bool = typer.Option(False, "--force", "-f", help="强制刷新，忽略缓存"),
    timeout: int = typer.Option(5, "--timeout", "-t", help="请求超时时间（秒）"),
) -> None:
    """同步检查各厂商最新模型"""
    if ModelDiscovery is None:
        console.print("[red]✗ 模型发现模块未加载[/red]")
        raise typer.Exit(1)

    console.print()
    console.print("[bold cyan]🔍 正在检查各厂商最新模型...[/bold cyan]")
    console.print()

    discovery = ModelDiscovery()

    # 检查缓存状态
    if not force:
        cached = discovery.get_cached()
        if cached:
            cached_at = cached.get("cached_at", "未知")
            console.print(
                f"[dim]使用缓存数据（{cached_at}），使用 --force 强制刷新[/dim]"
            )
            console.print()

    # 执行同步
    result = discovery.sync(force=force, timeout=timeout)

    if result.get("status") == "cached":
        discovered = result.get("data", {})
        console.print("[yellow]⚠ 使用缓存数据，跳过实时检查[/yellow]")
    else:
        discovered = result.get("data", {})
        providers_stats = result.get("providers", {})

        # 显示各厂商状态
        for provider, count in providers_stats.items():
            if count > 0:
                console.print(f"  [green]✅[/] {provider}: 发现 {count} 个模型")
            else:
                # 检查是否有 API key
                config = discovery.PROVIDER_APIS.get(provider, {})
                if config.get("skip"):
                    reason = config.get("reason", "不支持动态发现")
                    console.print(f"  [dim]⏭️  {provider}: {reason}[/dim]")
                elif config.get("key_env") and not os.getenv(config["key_env"]):
                    console.print(f"  [yellow]⚠️[/] {provider}: API Key 未配置")
                else:
                    console.print(f"  [dim]⚪ {provider}: 无可用模型或请求失败[/dim]")

    # 对比内置模型
    comparison = discovery.compare_with_builtin(discovered, BUILTIN_CATWALK_MODELS)
    new_models = comparison.get("new_models", [])
    removed_models = comparison.get("removed_models", [])

    console.print()

    if new_models:
        console.print(f"[bold green]✨ 发现 {len(new_models)} 个新模型:[/bold green]")
        for m in new_models[:10]:  # 最多显示10个
            console.print(f"   • {m['model_id']} ({m['provider']})")
        if len(new_models) > 10:
            console.print(f"   ... 还有 {len(new_models) - 10} 个")
        console.print()
        console.print(
            "[dim]💡 提示: 使用 [cyan]omc model import <url>[/cyan] 添加新模型[/dim]"
        )
    else:
        console.print("[dim]未发现新模型[/dim]")

    if removed_models:
        console.print()
        console.print(f"[yellow]⚠️  {len(removed_models)} 个模型可能已下线:[/yellow]")
        for m in removed_models[:5]:
            console.print(f"   • {m['name']} ({m['model_id']})")

    console.print()
    console.print(f"[dim]缓存文件: {discovery.CACHE_FILE}[/dim]")


# 别名：支持 omc model switch 和 omc modelswitch
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """默认显示帮助"""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
