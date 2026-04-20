"""
omc self-config 命令 - 自配置 Skill

基于自然语言理解，自动完成配置任务。
用户说"配置 GLM API"，AI 自动完成配置。

使用 LLM 理解用户意图，调用相应的配置 API。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

try:
    from ..core.router import ModelRouter  # noqa: F401
    from ..core.config_manager import ConfigManager  # noqa: F401

    HAS_CORE = True
except ImportError:
    HAS_CORE = False

app = typer.Typer(help="自配置命令 - 用自然语言配置一切")
console = Console()


# 配置意图识别规则
CONFIG_INTENTS = {
    # 模型配置
    "api_key": {
        "patterns": [
            r"配置.*API.*KEY",
            r"设置.*API.*KEY",
            r"api.?key",
            r"api_key",
            r"配置.*密钥",
        ],
        "action": "set_api_key",
        "examples": ["配置 GLM API KEY", "设置 DeepSeek API Key"],
    },
    "model": {
        "patterns": [
            r"切换.*模型",
            r"使用.*模型",
            r"set.*model",
            r"default.*model",
            r"模型.*默认",
        ],
        "action": "set_default_model",
        "examples": ["切换到 DeepSeek 模型", "使用 GLM 作为默认模型"],
    },
    "proxy": {
        "patterns": [
            r"配置.*代理",
            r"设置.*代理",
            r"proxy",
            r"http.proxy",
        ],
        "action": "set_proxy",
        "examples": ["配置 HTTP 代理", "设置代理为 127.0.0.1:4780"],
    },
    "temperature": {
        "patterns": [
            r"温度",
            r"temperature",
            r"创意.*设置",
        ],
        "action": "set_temperature",
        "examples": ["设置温度为 0.7", "调高创意温度"],
    },
    "template": {
        "patterns": [
            r"模板",
            r"template",
            r"工作流.*配置",
        ],
        "action": "set_template",
        "examples": ["配置代码审查模板", "设置默认工作流"],
    },
}

# 模型提供商列表
MODEL_PROVIDERS = {
    "glm": {
        "name": "智谱 GLM",
        "api_key_env": "GLM_API_KEY",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "free_quota": "200万 Tokens",
    },
    "deepseek": {
        "name": "DeepSeek",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/",
        "free_quota": "60元",
    },
    "mimo": {
        "name": "MiMo",
        "api_key_env": "MIMOX_API_KEY",
        "base_url": "https://api.minimax.chat/v1",
        "free_quota": "无限",
    },
    "qwen": {
        "name": "通义千问",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "free_quota": "有免费额度",
    },
    "wenxin": {
        "name": "文心一言",
        "api_key_env": "ERNIE_API_KEY",
        "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1",
        "free_quota": "有免费额度",
    },
}


def parse_config_intent(text: str) -> Optional[Dict[str, Any]]:
    """解析配置意图"""
    text_lower = text.lower()

    for intent_id, intent_info in CONFIG_INTENTS.items():
        for pattern in intent_info["patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return {
                    "intent": intent_id,
                    "action": intent_info["action"],
                    "raw_text": text,
                }

    # 尝试识别模型提供商
    for provider_id, provider_info in MODEL_PROVIDERS.items():
        if provider_id in text_lower or provider_info["name"] in text:
            return {
                "intent": "api_key",
                "action": "set_api_key",
                "provider": provider_id,
                "raw_text": text,
            }

    return None


def detect_api_key_in_text(text: str) -> Optional[str]:
    """从文本中提取 API Key"""
    # 常见的 API Key 格式
    patterns = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI 格式
        r"[a-zA-Z0-9]{32,}",  # 通用格式
        r'["\']([a-zA-Z0-9_-]{20,})["\']',  # 带引号
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            key = match.group(0).strip("'\"")
            # 过滤掉明显的非 key 内容
            if not key.startswith("http") and len(key) > 20:
                return key

    return None


async def execute_config(config: Dict[str, Any], api_key: Optional[str] = None) -> bool:
    """执行配置"""
    action = config.get("action")

    if action == "set_api_key":
        return await _set_api_key(config, api_key)
    elif action == "set_default_model":
        return await _set_default_model(config)
    elif action == "set_proxy":
        return await _set_proxy(config)
    elif action == "set_temperature":
        return await _set_temperature(config)
    else:
        console.print(f"[yellow]未知配置动作: {action}[/yellow]")
        return False


async def _set_api_key(config: Dict[str, Any], api_key: Optional[str] = None) -> bool:
    """设置 API Key"""
    provider = config.get("provider")
    raw_text = config.get("raw_text", "")

    if not provider:
        # 尝试从文本中识别提供商
        for pid, pinfo in MODEL_PROVIDERS.items():
            if pid in raw_text.lower() or pinfo["name"] in raw_text:
                provider = pid
                break

    if not provider:
        console.print("[yellow]无法识别模型提供商，请明确指定：[/yellow]")
        for pid, pinfo in MODEL_PROVIDERS.items():
            console.print(f"  • {pinfo['name']} ({pid})")
        return False

    provider_info = MODEL_PROVIDERS[provider]

    # 如果没有提供 API Key，提示用户输入
    if not api_key:
        console.print(f"\n[cyan]配置 {provider_info['name']} API Key[/cyan]")
        console.print(f"[dim]免费额度: {provider_info['free_quota']}[/dim]")
        api_key = Prompt.ask(
            f"请输入 {provider_info['name']} API Key",
            password=True,
        )

    if not api_key or len(api_key) < 10:
        console.print("[red]API Key 无效[/red]")
        return False

    # 写入环境变量文件
    env_file = Path.home() / ".omc" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)

    # 读取现有配置
    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    # 更新配置
    env_vars[provider_info["api_key_env"]] = api_key

    # 写入文件
    with open(env_file, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    console.print(f"[green]✅ 已保存 {provider_info['name']} API Key[/green]")
    console.print(f"[dim]配置文件: {env_file}[/dim]")

    return True


async def _set_default_model(config: Dict[str, Any]) -> bool:
    """设置默认模型"""
    console.print("\n[cyan]设置默认模型[/cyan]\n")

    # 显示可用模型
    table = Table(title="可用模型")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="white")
    table.add_column("免费额度", style="dim")

    for pid, pinfo in MODEL_PROVIDERS.items():
        table.add_row(pid, pinfo["name"], pinfo["free_quota"])

    console.print(table)

    model_id = Prompt.ask(
        "\n请选择模型 ID",
        default="glm",
        choices=list(MODEL_PROVIDERS.keys()),
    )

    # 更新配置文件
    config_file = Path.home() / ".omc" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    config_data = {}
    if config_file.exists():
        try:
            config_data = json.loads(config_file.read_text())
        except Exception:
            pass

    config_data["default_model"] = model_id

    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    console.print(
        f"[green]✅ 默认模型已设置为 {MODEL_PROVIDERS[model_id]['name']}[/green]"
    )
    return True


async def _set_proxy(config: Dict[str, Any]) -> bool:
    """设置代理"""
    console.print("\n[cyan]配置 HTTP 代理[/cyan]")

    proxy = Prompt.ask("请输入代理地址", default="http://127.0.0.1:4780")

    if not proxy.startswith("http"):
        proxy = f"http://{proxy}"

    # 更新环境变量
    env_file = Path.home() / ".omc" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)

    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    env_vars["HTTP_PROXY"] = proxy
    env_vars["HTTPS_PROXY"] = proxy

    with open(env_file, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    console.print(f"[green]✅ 代理已设置为 {proxy}[/green]")
    return True


async def _set_temperature(config: Dict[str, Any]) -> bool:
    """设置温度参数"""
    console.print("\n[cyan]设置模型温度[/cyan]")

    temp = Prompt.ask("请输入温度值", default="0.7")

    try:
        temp_float = float(temp)
        if not 0 <= temp_float <= 2:
            console.print("[yellow]温度建议在 0-2 之间[/yellow]")
    except ValueError:
        console.print("[red]无效的温度值[/red]")
        return False

    # 更新配置文件
    config_file = Path.home() / ".omc" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)

    config_data = {}
    if config_file.exists():
        try:
            config_data = json.loads(config_file.read_text())
        except Exception:
            pass

    config_data["temperature"] = temp_float

    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    console.print(f"[green]✅ 温度已设置为 {temp_float}[/green]")
    return True


@app.command()
def config(
    intent: str = typer.Argument(
        None, help="配置意图，如'配置 GLM API KEY'或'切换到 DeepSeek 模型'"
    ),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="直接提供 API Key"),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="指定模型提供商"
    ),
    non_interactive: bool = typer.Option(
        False, "--yes", "-y", help="非交互模式，使用默认值"
    ),
):
    """
    自配置命令 - 用自然语言配置一切

    示例:
        omc self-config "配置 GLM API KEY"
        omc self-config "切换到 DeepSeek 模型"
        omc self-config --key sk-xxx --provider glm
        omc self-config "设置代理为 http://127.0.0.1:8080"
    """
    if not intent and not key:
        console.print(
            Panel.fit(
                "[bold cyan]omc self-config[/bold cyan] - 自然语言配置助手\n\n"
                "支持的配置类型:\n"
                '  • API Key: [cyan]omc self-config "配置 GLM API KEY"[/cyan]\n'
                '  • 模型切换: [cyan]omc self-config "切换到 DeepSeek 模型"[/cyan]\n'
                '  • 代理设置: [cyan]omc self-config "设置代理"[/cyan]\n'
                '  • 温度参数: [cyan]omc self-config "设置温度为 0.7"[/cyan]\n\n'
                "[dim]也可直接指定: omc self-config --key YOUR_KEY --provider glm[/dim]",
                border_style="cyan",
            )
        )
        return

    # 解析意图
    config_info = None

    if intent:
        config_info = parse_config_intent(intent)

        # 如果没有匹配，尝试从文本中提取 API Key
        if not config_info:
            extracted_key = detect_api_key_in_text(intent)
            if extracted_key:
                config_info = {
                    "intent": "api_key",
                    "action": "set_api_key",
                    "raw_text": intent,
                }
                if key:
                    extracted_key = key

    # 处理直接提供的 key
    if key:
        config_info = {
            "intent": "api_key",
            "action": "set_api_key",
            "provider": provider,
            "raw_text": intent or "",
        }

    if not config_info:
        console.print("[yellow]无法理解配置意图，请尝试更明确的描述[/yellow]")
        return

    # 执行配置
    import asyncio

    result = asyncio.run(execute_config(config_info, key if not intent else None))

    if result:
        console.print("\n[green]✅ 配置完成！[/green]")
    else:
        console.print("\n[red]❌ 配置失败[/red]")


@app.command("list")
def list_configs():
    """列出当前配置"""
    console.print("\n[cyan]当前配置状态[/cyan]\n")

    # 检查 API Keys
    env_file = Path.home() / ".omc" / ".env"
    configured_keys = []

    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "API_KEY" in line and "=" in line:
                key_name = line.split("=")[0].strip()
                configured_keys.append(key_name)

    if configured_keys:
        console.print("[bold]已配置的 API Keys:[/bold]")
        for key in configured_keys:
            console.print(f"  ✅ {key}")
    else:
        console.print("[dim]未配置任何 API Key[/dim]")

    # 检查默认模型
    config_file = Path.home() / ".omc" / "config.json"
    if config_file.exists():
        try:
            config_data = json.loads(config_file.read_text())
            if "default_model" in config_data:
                model_id = config_data["default_model"]
                model_name = MODEL_PROVIDERS.get(model_id, {}).get("name", model_id)
                console.print(f"\n[bold]默认模型:[/bold] {model_name} ({model_id})")

            if "temperature" in config_data:
                console.print(f"[bold]温度设置:[/bold] {config_data['temperature']}")
        except Exception:
            pass

    console.print()


if __name__ == "__main__":
    app()
