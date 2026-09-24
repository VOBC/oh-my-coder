"""配置管理命令"""

import json
import os
from pathlib import Path
from typing import Any, cast

import typer
from rich.console import Console

app = typer.Typer(name="config", help="⚙️ 配置管理")
console = Console()


@app.command()
def show(
    model: str = typer.Option(None, "--model", "-m", help="指定模型名称"),
):
    """查看当前配置"""
    CONFIG_DIR = Path.home() / ".omc"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    def _load() -> dict[str, Any]:
        if CONFIG_FILE.exists():
            try:
                return cast(dict[str, Any], json.loads(CONFIG_FILE.read_text()))
            except Exception:
                return {}
        return {}

    def _mask_secret(val: str) -> str:
        if not val:
            return ""
        if len(val) <= 8:
            return "****"
        return val[:4] + "****" + val[-4:]

    cfg = _load()
    console.print("[bold]⚙️ 当前配置[/bold]\n")

    # 全局配置（从 .env）
    console.print("[bold]全局配置：[/bold]")
    global_keys = [
        "DEFAULT_MODEL",
        "DEFAULT_WORKFLOW",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "KIMI_API_KEY",
        "DOUBAO_API_KEY",
        "ZHIPUAI_API_KEY",
        "GLM_API_KEY",  # 智谱 GLM 别名
        "MINIMAX_API_KEY",
        "DASHSCOPE_API_KEY",
        "ERNIE_API_KEY",
        "HUNYUAN_API_KEY",
    ]
    for k in global_keys:
        val = os.getenv(k, "")
        masked = _mask_secret(val)
        status = "[green]✓[/green]" if val else "[dim]—[/dim]"
        console.print(f"  {status} [cyan]{k}[/cyan] = {masked}")

    console.print()

    # 按模型配置
    models = cfg.get("models", {})
    if model:
        # 显示指定模型的配置
        if model in models:
            console.print(f"[bold]模型 {model} 配置：[/bold]")
            for k2, v2 in models[model].items():
                if k2 == "api_key":
                    v2 = _mask_secret(str(v2))
                console.print(f"  {k2}: {v2}")
        else:
            console.print(f"[dim]模型 {model} 尚未配置[/dim]")
    elif models:
        console.print(f"[bold]按模型配置（{len(models)} 个模型）：[/bold]")
        for name, opts in models.items():
            console.print(f"\n  [cyan]{name}[/cyan]")
            for k2, v2 in opts.items():
                if k2 == "api_key":
                    v2 = _mask_secret(str(v2))
                console.print(f"    {k2}: {v2}")
    else:
        console.print("[dim]无按模型配置，使用全局默认值[/dim]")

    console.print()
    console.print(
        "[dim]帮助: omc config --help   设置模型: omc config set -m <model> -k <key> -v <value>[/dim]"
    )


@app.command()
def list():
    """列出所有配置项"""

    def _mask_secret(val: str) -> str:
        if not val:
            return ""
        if len(val) <= 8:
            return "****"
        return val[:4] + "****" + val[-4:]

    console.print("[bold]可用全局配置项：[/bold]\n")
    items = [
        ("DEFAULT_MODEL", "默认模型（默认 deepseek）"),
        ("DEFAULT_WORKFLOW", "默认工作流（默认 build）"),
        ("DEEPSEEK_API_KEY", "DeepSeek API Key（推荐，性价比高）"),
        ("DEEPSEEK_BASE_URL", "DeepSeek API 地址（默认官方）"),
        ("KIMI_API_KEY", "KIMI API Key（Moonshot）"),
        ("DOUBAO_API_KEY", "豆包 API Key（字节）"),
        ("ZHIPUAI_API_KEY", "智谱 GLM API Key"),
        ("GLM_API_KEY", "智谱 GLM 别名（同 ZHIPUAI_API_KEY）"),
        ("MINIMAX_API_KEY", "MiniMax API Key"),
        ("DASHSCOPE_API_KEY", "阿里通义千问 DashScope API Key"),
        ("ERNIE_API_KEY", "百度文心一言 API Key"),
        ("HUNYUAN_API_KEY", "腾讯混元 API Key"),
    ]
    for k, desc in items:
        val = os.getenv(k, "")
        masked = _mask_secret(val)
        status = "[green]✓[/green]" if val else "[red]✗[/red]"
        console.print(f"  {status} [cyan]{k}[/cyan]  {desc}")
        if val:
            console.print(f"       当前: {masked}")
    console.print()
    console.print(
        "[bold]按模型配置：[/bold] omc config set -m <model> -k <key> -v <value>"
    )
    console.print(
        "[dim]模型可用 key: api_key / base_url / temperature / max_tokens / system_prompt[/dim]"
    )


@app.command()
def set(
    key: str = typer.Option(None, "--key", "-k", help="配置项名称"),
    value: str = typer.Option(None, "--value", "-v", help="配置值（留空则删除该 key）"),
    model: str = typer.Option(None, "--model", "-m", help="指定模型名称"),
):
    """设置配置项"""
    if not key:
        console.print("[red]❗ 需要 --key 参数[/red]")
        raise typer.Exit(1)

    CONFIG_DIR = Path.home() / ".omc"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _load() -> dict[str, Any]:
        if CONFIG_FILE.exists():
            try:
                return cast(dict[str, Any], json.loads(CONFIG_FILE.read_text()))
            except Exception:
                return {}
        return {}

    def _save(cfg: dict) -> None:
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")

    def _mask_secret(val: str) -> str:
        if not val:
            return ""
        if len(val) <= 8:
            return "****"
        return val[:4] + "****" + val[-4:]

    if model:
        # 按模型配置
        cfg = _load()
        if "models" not in cfg:
            cfg["models"] = {}
        if model not in cfg["models"]:
            cfg["models"][model] = {}

        if value is None or value == "":
            # 删除该 key
            cfg["models"][model].pop(key, None)
            console.print(f"[yellow]✓ 已移除[/yellow] [cyan]{model}[/cyan].{key}")
        else:
            cfg["models"][model][key] = value
            console.print(
                f"[green]✓ 已设置[/green] [cyan]{model}[/cyan].{key} = {value}"
            )
        _save(cfg)
        console.print(f"[dim]已保存到 {CONFIG_FILE}[/dim]")
    else:
        # 全局配置，写入 ~/.omc/.env（统一位置）
        CONFIG_DIR = Path.home() / ".omc"
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        env_path = CONFIG_DIR / ".env"
        env_vars: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line:
                    k2, v2 = line.split("=", 1)
                    env_vars[k2.strip()] = v2.strip()
        env_vars[key] = value
        env_path.write_text("\n".join(f"{k}={v}" for k, v in env_vars.items()) + "\n")
        console.print(
            f"[green]✓ 已设置（全局）[/green] [cyan]{key}[/cyan] = {_mask_secret(value)}"
        )
        console.print(f"[dim]已写入 {env_path}[/dim]")


@app.command()
def models():
    """列出已配置的模型"""
    CONFIG_DIR = Path.home() / ".omc"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    def _load() -> dict[str, Any]:
        if CONFIG_FILE.exists():
            try:
                return cast(dict[str, Any], json.loads(CONFIG_FILE.read_text()))
            except Exception:
                return {}
        return {}

    def _mask_secret(val: str) -> str:
        if not val:
            return ""
        if len(val) <= 8:
            return "****"
        return val[:4] + "****" + val[-4:]

    cfg = _load()
    models = cfg.get("models", {})
    if not models:
        console.print("[dim]尚未配置任何模型[/dim]")
        console.print(
            "\n[bold]快速开始：[/bold] omc config set -m kimi -k api_key -v <your-key>"
        )
    else:
        # 字段显示顺序：常用字段优先，其他未知字段按字母顺序追加
        preferred = ("api_key", "base_url", "temperature", "max_tokens", "system_prompt")
        console.print(f"[bold]已配置 {len(models)} 个模型：[/bold]\n")
        for name, opts in models.items():
            console.print(f"  [cyan]{name}[/cyan]")
            # 先输出 preferred 顺序里的字段（note: 模块顶层有 `set` 命令，
            # 内置 set 被覆盖，这里用 list 去重避免误调命令函数）
            shown: list[str] = []
            for k2 in preferred:
                if k2 in opts:
                    shown.append(k2)
                    v2 = opts[k2]
                    if k2 == "api_key":
                        v2 = _mask_secret(str(v2))
                    console.print(f"    {k2}: {v2}")
            # 再输出其他未知字段
            for k2 in sorted(opts.keys()):
                if k2 not in shown:
                    v2 = opts[k2]
                    if k2 == "api_key":
                        v2 = _mask_secret(str(v2))
                    console.print(f"    {k2}: {v2}")
            console.print()
