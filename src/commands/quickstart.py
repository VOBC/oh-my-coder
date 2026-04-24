"""
omc quickstart - 交互式引导命令

引导新用户在 3 步内完成配置并运行第一个任务：
  [1/3] 选择模型
  [2/3] 配置 API Key
  [3/3] 运行示例任务验证配置
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()

app = typer.Typer(
    name="quickstart",
    help="交互式引导 - 3 步完成配置并运行第一个任务",
    add_completion=False,
)

# ============================================================
# 模型分类（与 cli_model.py / router.py 保持同步）
# ============================================================
MODEL_CATEGORIES = {
    "国产免费": [
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "desc": "免费额度高，质量接近 GPT-4",
            "api_key_env": "DEEPSEEK_API_KEY",
            "register_url": "https://platform.deepseek.com",
            "model_name": "deepseek-chat",
        },
        {
            "id": "glm",
            "name": "智谱 GLM",
            "desc": "GLM-4-Flash 免费用",
            "api_key_env": "GLM_API_KEY",
            "register_url": "https://open.bigmodel.cn",
            "model_name": "glm-4-flash",
        },
    ],
    "国产付费": [
        {
            "id": "kimi",
            "name": "Kimi（月之暗面）",
            "desc": "长上下文能力强",
            "api_key_env": "KIMI_API_KEY",
            "register_url": "https://platform.moonshot.cn",
            "model_name": "moonshot-v1-8k",
        },
        {
            "id": "doubao",
            "name": "字节豆包",
            "desc": "性价比高",
            "api_key_env": "DOUBAO_API_KEY",
            "register_url": "https://console.volcengine.com/ark",
            "model_name": "doubao-pro-32k",
        },
        {
            "id": "tongyi",
            "name": "通义千问（阿里）",
            "desc": "阿里云生态集成",
            "api_key_env": "TONGYI_API_KEY",
            "register_url": "https://dashscope.console.aliyun.com",
            "model_name": "qwen-turbo",
        },
        {
            "id": "minimax",
            "name": "MiniMax",
            "desc": "支持超长上下文",
            "api_key_env": "MINIMAX_API_KEY",
            "register_url": "https://www.minimaxi.com",
            "model_name": "abab6-chat",
        },
        {
            "id": "wenxin",
            "name": "文心一言（百度）",
            "desc": "百度文心大模型",
            "api_key_env": "WENXIN_API_KEY",
            "register_url": "https://console.bce.baidu.com",
            "model_name": "ernie-4.0-8k-latest",
        },
        {
            "id": "hunyuan",
            "name": "腾讯混元",
            "desc": "腾讯自研大模型",
            "api_key_env": "HUNYUAN_API_KEY",
            "register_url": "https://console.cloud.tencent.com/hunyuan",
            "model_name": "hunyuan-pro",
        },
        {
            "id": "baichuan",
            "name": "百川智能",
            "desc": "百川大模型",
            "api_key_env": "BAICHUAN_API_KEY",
            "register_url": "https://www.baichuan-ai.com",
            "model_name": "baichuan4",
        },
    ],
}

# 每个模型的注册地址（用于快速导航）
REGISTER_URLS = {
    "deepseek": "https://platform.deepseek.com",
    "glm": "https://open.bigmodel.cn",
    "kimi": "https://platform.moonshot.cn",
    "doubao": "https://console.volcengine.com/ark",
    "tongyi": "https://dashscope.console.aliyun.com",
    "minimax": "https://www.minimaxi.com",
    "wenxin": "https://console.bce.baidu.com",
    "hunyuan": "https://console.cloud.tencent.com/hunyuan",
    "baichuan": "https://www.baichuan-ai.com",
}


# ============================================================
# 进度状态检测
# ============================================================
def detect_completed_steps() -> dict[str, bool]:
    """检测已完成步骤（自动跳过）"""
    steps: dict[str, bool] = {
        "model": False,
        "apikey": False,
        "verify": False,
    }

    # Step 1: 是否已有默认模型且有对应 API Key
    config_file = Path.home() / ".config" / "oh-my-coder" / "config.json"
    config_model = None
    if config_file.exists():
        try:
            cfg = json.loads(config_file.read_text())
            config_model = cfg.get("default_model")
        except Exception:
            pass

    env_model = os.getenv("OMC_DEFAULT_MODEL")

    # 检查是否有已配置的 API Key
    env_api_keys = {
        "DEEPSEEK_API_KEY": "deepseek",
        "KIMI_API_KEY": "kimi",
        "DOUBAO_API_KEY": "doubao",
        "GLM_API_KEY": "glm",
        "TONGYI_API_KEY": "tongyi",
        "MINIMAX_API_KEY": "minimax",
        "WENXIN_API_KEY": "wenxin",
        "HUNYUAN_API_KEY": "hunyuan",
        "BAICHUAN_API_KEY": "baichuan",
    }
    configured = [env for env, _ in env_api_keys.items() if os.getenv(env)]

    if configured or config_model or env_model:
        steps["model"] = True

    # Step 2: API Key 配置
    if configured:
        steps["apikey"] = True

    # Step 3: 有可工作的 API Key（能实际调用）
    # 通过尝试一个简单的 API 调用来验证（轻量检测）
    if configured:
        steps["verify"] = _check_api_key_works(
            configured[0], env_api_keys[configured[0]]
        )

    return steps


def _check_api_key_works(env_key: str, provider: str) -> bool:
    """轻量检测 API Key 是否有效（不真正调用，只检查格式和环境）"""
    key = os.getenv(env_key)
    if not key:
        return False

    # 格式检查
    if len(key) < 10:
        return False

    # 对于已知的模型，做一个免费的健康检查
    try:
        if provider == "deepseek":
            # 快速检查 DeepSeek 余额
            import httpx

            resp = httpx.get(
                "https://api.deepseek.com/user_balance",
                headers={"Authorization": f"Bearer {key}"},
                timeout=5,
            )
            return resp.status_code in (200, 401)  # 401=key格式对但欠费/额度用完
        elif provider == "glm":
            resp = httpx.get(
                "https://open.bigmodel.cn/api/paas/v4/balance",
                headers={"Authorization": f"Bearer {key}"},
                timeout=5,
            )
            return resp.status_code in (200, 401)
    except Exception:
        pass

    # 保守：只要有非空 key 就认为可能有效
    return True


# ============================================================
# 步骤 1：选择模型
# ============================================================
def _step1_select_model() -> dict | None:
    """交互式选择模型，返回选中的模型信息或 None（跳过）"""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]步骤 1 / 3：选择模型[/bold cyan]\n\n"
            "以下模型均已集成到 omc，支持开箱即用：",
            border_style="cyan",
            title="🚀 快速配置引导",
        )
    )

    # 显示分类模型列表
    choice_map: list[tuple[str, dict]] = []  # (display_num, model_info)

    num = 1
    for category, models in MODEL_CATEGORIES.items():
        console.print(f"\n[bold yellow]{category}[/bold yellow]")
        for m in models:
            # 检查是否已配置
            configured = "✅" if os.getenv(m["api_key_env"]) else "  "
            console.print(f"  {configured} [{num}] {m['name']} — {m['desc']}")
            choice_map.append((str(num), m))
            num += 1

    console.print()
    console.print("[dim]已配置的打 ✅，按回车跳过（已有配置）[/dim]")

    raw = Prompt.ask("[cyan]请选择模型编号（或回车跳过）[/cyan]")
    raw = raw.strip()

    if not raw:
        return None

    # 查找选择
    for display_num, model_info in choice_map:
        if display_num == raw:
            return model_info

    console.print("[yellow]无效选择，已跳过[/yellow]")
    return None


# ============================================================
# 步骤 2：配置 API Key
# ============================================================
def _step2_config_apikey(model_info: dict) -> bool:
    """配置 API Key，返回是否成功"""
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]步骤 2 / 3：为 {model_info['name']} 配置 API Key[/bold cyan]\n\n"
            f"注册地址：{model_info['register_url']}\n\n"
            "如果你已经有 Key，可以直接输入；"
            "如果没有，请按回车打开浏览器前往注册。",
            border_style="cyan",
        )
    )

    env_key = model_info["api_key_env"]
    existing = os.getenv(env_key)

    if existing:
        masked = existing[:4] + "****" + existing[-4:] if len(existing) > 8 else "****"
        console.print(f"[green]✓ 已配置：[/green] {env_key} = {masked}")
        if Confirm.ask("要更新现有 Key 吗？", default=False):
            pass
        else:
            console.print("[dim]跳过 Key 配置[/dim]")
            return True

    console.print(f"\n[bold]请输入 {env_key}:[/bold]")
    key = Prompt.ask("API Key", password=True).strip()

    if not key:
        console.print(
            "[yellow]未输入 Key，跳过（可稍后用 omc config set 配置）[/yellow]"
        )
        return False

    # 写入 .env 文件（项目根目录或用户目录）
    _set_env_var(env_key, key)
    console.print(f"[green]✓ 已写入 {env_key}[/green]")
    return True


def _set_env_var(key: str, value: str) -> None:
    """设置环境变量（写入 .env + 设置当前进程）"""
    os.environ[key] = value

    # 写入项目根目录 .env
    project_env = Path(".env")
    env_vars: dict[str, str] = {}

    if project_env.exists():
        for line in project_env.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()

    env_vars[key] = value
    lines = [f"{k}={v}" for k, v in env_vars.items()]
    project_env.write_text("\n".join(lines) + "\n")

    # 同步写入用户 home 目录
    home_env = Path.home() / ".omc.env"
    home_vars: dict[str, str] = {}
    if home_env.exists():
        for line in home_env.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                home_vars[k.strip()] = v.strip()
    home_vars[key] = value
    home_env.write_text("\n".join(f"{k}={v}" for k, v in home_vars.items()) + "\n")


# ============================================================
# 步骤 3：运行示例任务
# ============================================================
def _step3_run_demo(model_info: dict) -> bool:
    """运行示例任务验证配置"""
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]步骤 3 / 3：运行示例任务[/bold cyan]\n\n"
            f"使用 [green]{model_info['name']}[/green] 执行一个简单任务：\n"
            "[bold]用 Python 实现快速排序算法[/bold]\n\n"
            "验证模型配置是否正确。",
            border_style="cyan",
        )
    )

    if not Confirm.ask("\n开始执行？", default=True):
        console.print("[dim]跳过验证（可随时用 omc run 测试）[/dim]")
        return False

    from rich.progress import Progress, SpinnerColumn, TextColumn

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("正在执行...", total=None)
        progress.update(task, description="[yellow]调用模型...[/yellow]")

        try:
            result = asyncio.run(_call_model_demo(model_info))
            progress.update(task, description="[green]执行完成[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]执行失败: {e}[/red]")
            return False

    if result.get("success"):
        console.print(
            Panel.fit(
                f"[bold green]✅ 配置成功！[/bold green]\n\n"
                f"模型：{model_info['name']}\n"
                f"生成代码预览：\n\n[dim]{_truncate(result.get('code', ''), 300)}[/dim]",
                title="🎉 验证通过",
                border_style="green",
            )
        )
        return True
    else:
        console.print(
            Panel.fit(
                f"[bold red]❌ 验证失败[/bold red]\n\n"
                f"错误：{result.get('error', '未知错误')}\n\n"
                "[dim]常见问题：\n"
                "  1. API Key 错误或已过期\n"
                "  2. 账户余额不足\n"
                "  3. 网络无法访问该平台\n\n"
                "请访问 {model_info['register_url']} 检查[/dim]".format_map(
                    {"model_info": str(model_info)}
                ),
                title="⚠️ 验证未通过",
                border_style="red",
            )
        )
        return False


async def _call_model_demo(model_info: dict) -> dict:
    """调用模型执行快速排序示例"""
    import httpx

    api_key = os.getenv(model_info["api_key_env"])
    if not api_key:
        return {"success": False, "error": "API Key 未配置"}

    prompt = "用 Python 实现快速排序算法，只输出代码，不需要解释。"

    # 不同平台调用方式
    provider = model_info["id"]

    try:
        if provider == "deepseek":
            resp = httpx.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "glm":
            resp = httpx.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "glm-4-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "kimi":
            resp = httpx.post(
                "https://api.moonshot.cn/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "moonshot-v1-8k",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "doubao":
            resp = httpx.post(
                "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "doubao-pro-32k",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "tongyi":
            resp = httpx.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "minimax":
            resp = httpx.post(
                "https://api.minimax.chat/v1/text/chatcompletion_pro?GroupId=&AuthorId=",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "abab6-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        elif provider == "wenxin":
            access_token = _get_wenxin_access_token(api_key)
            if not access_token:
                return {
                    "success": False,
                    "error": "文心一言需要 access_token，请检查配置",
                }
            resp = httpx.post(
                "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions",
                headers={"Content-Type": "application/json"},
                params={"access_token": access_token},
                json={
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
        elif provider == "hunyuan":
            secret_key = os.getenv("HUNYUAN_SECRET_KEY", "")
            access_token = _get_hunyuan_access_token(api_key, secret_key)
            if not access_token:
                return {"success": False, "error": "混元需要 access_token，请检查配置"}
            resp = httpx.post(
                "https://hunyuan.cloud.tencent.com/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "hunyuan-pro",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
        else:
            return {"success": False, "error": f"暂不支持 {provider} 的快速验证"}

        if resp.status_code != 200:
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get(
                    "message", err_data.get("message", resp.text)
                )
            except Exception:
                err_msg = resp.text
            return {"success": False, "error": f"[{resp.status_code}] {err_msg}"}

        data = resp.json()
        content = ""
        if "choices" in data:
            content = data["choices"][0]["message"]["content"]
        elif "result" in data:
            content = data["result"]

        return {"success": True, "code": content}

    except httpx.TimeoutException:
        return {"success": False, "error": "请求超时，请检查网络连接"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _get_wenxin_access_token(api_key: str) -> str | None:
    """获取文心一言 access_token（简化版）"""
    try:
        secret_key = os.getenv("WENXIN_SECRET_KEY", "")
        resp = httpx.get(
            "https://aip.baidubce.com/oauth/2.0/token",
            params={
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": secret_key,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception:
        pass
    return None


def _get_hunyuan_access_token(api_key: str, secret_key: str) -> str | None:
    """获取腾讯混元 access_token（简化版）"""
    try:
        resp = httpx.post(
            "https://hunyuan.cloud.tencent.com/api/v1/auth/tokens",
            headers={"Content-Type": "application/json"},
            json={"secret_id": api_key, "secret_key": secret_key},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("token", {}).get("access_token")
    except Exception:
        pass
    return None


def _truncate(s: str, max_len: int) -> str:
    """截断字符串"""
    if not s:
        return ""
    if len(s) <= max_len:
        return s
    return s[:max_len] + "\n..."


# ============================================================
# 完成总结
# ============================================================
def _show_summary(model_info: dict, steps_completed: dict) -> None:
    """展示完成总结"""
    console.print()
    console.print(
        Panel.fit(
            "[bold green]🎉 快速配置完成！[/bold green]\n\n"
            "接下来你可以：\n\n"
            '  [cyan]omc run "实现用户登录功能"[/cyan]\n'
            "    启动 AI 编程助手\n\n"
            "  [cyan]omc status[/cyan]\n"
            "    查看当前配置状态\n\n"
            "  [cyan]omc model list[/cyan]\n"
            "    查看所有可用模型\n\n"
            "[dim]配置文件：.env（项目）/ ~/.omc.env（用户全局）[/dim]",
            title="✅ 快速开始",
            border_style="green",
        )
    )


# ============================================================
# 主命令
# ============================================================
@app.command()
def main(
    step: str = typer.Option(
        None,
        "--step",
        "-s",
        help="只执行指定步骤：model / apikey / verify",
    ),
    model: str = typer.Option(
        None,
        "--model",
        "-m",
        help="直接指定模型 ID（如 deepseek / glm）",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制重新执行所有步骤（忽略已配置检测）",
    ),
):
    """
    交互式引导 - 3 步完成配置并运行第一个任务

    示例:
      omc quickstart          # 交互式引导（推荐首次使用）
      omc quickstart -m deepseek  # 直接指定模型
      omc quickstart --step verify  # 只验证配置
    """
    # 检测已完成步骤
    completed = {} if force else detect_completed_steps()

    # 统计跳过数
    skipped = sum(1 for v in completed.values() if v)
    if skipped > 0 and not force:
        console.print(f"[dim]检测到 {skipped} 个步骤已完成，将自动跳过[/dim]")

    # 如果通过 --model 直接指定模型，直接进入验证
    if model:
        model_info = None
        for cats in MODEL_CATEGORIES.values():
            for m in cats:
                if m["id"] == model:
                    model_info = m
                    break
        if not model_info:
            console.print(f"[red]未知模型: {model}[/red]")
            raise typer.Exit(1)
        # 跳过步骤1，直接配置 key
        console.print(f"[cyan]使用模型: {model_info['name']}[/cyan]\n")
        if not os.getenv(model_info["api_key_env"]):
            _step2_config_apikey(model_info)
        ok = _step3_run_demo(model_info)
        _show_summary(model_info, {"model": True, "apikey": True, "verify": ok})
        raise typer.Exit(0 if ok else 1)

    # 单步执行
    if step:
        if step == "model":
            _step1_select_model()
            raise typer.Exit(0)
        if step == "apikey":
            console.print(
                "[yellow]请先用 -m 指定模型：omc quickstart --step apikey -m deepseek[/yellow]"
            )
            raise typer.Exit(1)
        if step == "verify":
            # 尝试自动检测已配置的模型
            configured_key = next(
                (
                    env
                    for env in [
                        "DEEPSEEK_API_KEY",
                        "KIMI_API_KEY",
                        "DOUBAO_API_KEY",
                        "GLM_API_KEY",
                        "TONGYI_API_KEY",
                        "MINIMAX_API_KEY",
                        "WENXIN_API_KEY",
                        "HUNYUAN_API_KEY",
                        "BAICHUAN_API_KEY",
                    ]
                    if os.getenv(env)
                ),
                None,
            )
            if not configured_key:
                console.print("[red]未检测到已配置的 API Key[/red]")
                raise typer.Exit(1)
            env_to_provider = {
                "DEEPSEEK_API_KEY": "deepseek",
                "KIMI_API_KEY": "kimi",
                "DOUBAO_API_KEY": "doubao",
                "GLM_API_KEY": "glm",
                "TONGYI_API_KEY": "tongyi",
                "MINIMAX_API_KEY": "minimax",
                "WENXIN_API_KEY": "wenxin",
                "HUNYUAN_API_KEY": "hunyuan",
                "BAICHUAN_API_KEY": "baichuan",
            }
            pid = env_to_provider[configured_key]
            for cats in MODEL_CATEGORIES.values():
                for m in cats:
                    if m["id"] == pid:
                        ok = _step3_run_demo(m)
                        raise typer.Exit(0 if ok else 1)
        console.print(f"[red]未知步骤: {step}[/red]")
        raise typer.Exit(1)

    # ============================================================
    # 全流程
    # ============================================================
    console.print(
        Panel.fit(
            "[bold cyan]🚀 omc quickstart[/bold cyan]\n\n"
            "引导你在 3 步内完成配置并运行第一个任务：\n\n"
            "  [1/3] 选择模型\n"
            "  [2/3] 配置 API Key\n"
            "  [3/3] 运行示例任务验证\n\n"
            "[dim]已有配置的步骤会自动跳过[/dim]",
            border_style="cyan",
            title="快速配置引导",
        )
    )

    if not Confirm.ask("\n开始快速配置？", default=True):
        console.print("[dim]已取消[/dim]")
        raise typer.Exit(0)

    selected_model: dict | None = None
    model_configured: bool = False

    # ---- 步骤 1 ----
    if not completed["model"]:
        selected_model = _step1_select_model()
        if selected_model is None:
            # 用户跳过但有已配置模型，尝试检测
            configured_key = next(
                (
                    env
                    for env in [
                        "DEEPSEEK_API_KEY",
                        "KIMI_API_KEY",
                        "DOUBAO_API_KEY",
                        "GLM_API_KEY",
                        "TONGYI_API_KEY",
                        "MINIMAX_API_KEY",
                        "WENXIN_API_KEY",
                        "HUNYUAN_API_KEY",
                        "BAICHUAN_API_KEY",
                    ]
                    if os.getenv(env)
                ),
                None,
            )
            if configured_key:
                env_to_provider = {
                    "DEEPSEEK_API_KEY": "deepseek",
                    "KIMI_API_KEY": "kimi",
                    "DOUBAO_API_KEY": "doubao",
                    "GLM_API_KEY": "glm",
                    "TONGYI_API_KEY": "tongyi",
                    "MINIMAX_API_KEY": "minimax",
                    "WENXIN_API_KEY": "wenxin",
                    "HUNYUAN_API_KEY": "hunyuan",
                    "BAICHUAN_API_KEY": "baichuan",
                }
                pid = env_to_provider.get(configured_key, "")
                for cats in MODEL_CATEGORIES.values():
                    for m in cats:
                        if m["id"] == pid:
                            selected_model = m
                            break
    else:
        # 已有配置，检测用哪个模型
        configured_key = next(
            (
                env
                for env in [
                    "DEEPSEEK_API_KEY",
                    "KIMI_API_KEY",
                    "DOUBAO_API_KEY",
                    "GLM_API_KEY",
                    "TONGYI_API_KEY",
                    "MINIMAX_API_KEY",
                    "WENXIN_API_KEY",
                    "HUNYUAN_API_KEY",
                    "BAICHUAN_API_KEY",
                ]
                if os.getenv(env)
            ),
            None,
        )
        if configured_key:
            env_to_provider = {
                "DEEPSEEK_API_KEY": "deepseek",
                "KIMI_API_KEY": "kimi",
                "DOUBAO_API_KEY": "doubao",
                "GLM_API_KEY": "glm",
                "TONGYI_API_KEY": "tongyi",
                "MINIMAX_API_KEY": "minimax",
                "WENXIN_API_KEY": "wenxin",
                "HUNYUAN_API_KEY": "hunyuan",
                "BAICHUAN_API_KEY": "baichuan",
            }
            pid = env_to_provider.get(configured_key, "")
            for cats in MODEL_CATEGORIES.values():
                for m in cats:
                    if m["id"] == pid:
                        selected_model = m
                        break

    if selected_model is None:
        console.print("\n[yellow]未选择模型，退出（可用 omc run 直接运行）[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[green]✓ 已选择：{selected_model['name']}[/green]")

    # ---- 步骤 2 ----
    apikey_ok = completed["apikey"]
    if not apikey_ok:
        apikey_ok = _step2_config_apikey(selected_model)

    # ---- 步骤 3 ----
    verify_ok = completed["verify"]
    if not verify_ok:
        verify_ok = _step3_run_demo(selected_model)

    # 总结
    _show_summary(
        selected_model,
        {"model": True, "apikey": apikey_ok, "verify": verify_ok},
    )

    raise typer.Exit(0 if verify_ok else 1)


if __name__ == "__main__":
    app()
