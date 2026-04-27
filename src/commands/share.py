"""
omc share - 会话分享命令

功能：
1. 导出会话为 JSON（含配置+历史）
2. 生成分享链接（简短 ID）
3. 通过链接导入会话
4. 列出和删除分享
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

app = typer.Typer(
    name="share",
    help="会话分享 - 导出/导入/管理分享链接",
    add_completion=False,
)

# ========================================
# Share Storage
# ========================================

SHARE_DIR = Path.home() / ".omc" / "shares"


def _ensure_dir() -> None:
    """确保分享目录存在"""
    SHARE_DIR.mkdir(parents=True, exist_ok=True)


def _generate_share_id() -> str:
    """生成 8 位简短分享 ID"""
    return uuid.uuid4().hex[:8]


def _share_path(share_id: str) -> Path:
    """获取分享文件路径"""
    return SHARE_DIR / f"share_{share_id}.json"


# ========================================
# Core Functions
# ========================================


def export_session(
    task_id: Optional[str] = None,
    history_dir: Optional[Path] = None,
    include_config: bool = True,
    tags: Optional[List[str]] = None,
    expires_hours: int = 0,
) -> Dict[str, Any]:
    """
    导出会话为分享记录。

    Args:
        task_id: 指定任务 ID，为空则导出最近一次
        history_dir: 历史记录目录
        include_config: 是否包含配置信息
        tags: 标签
        expires_hours: 过期时间（小时），0 表示永不过期

    Returns:
        分享记录字典
    """
    _ensure_dir()

    h_dir = history_dir or Path(".omc/history")
    if not h_dir.exists():
        console.print("[red]❌ 历史记录目录不存在[/red]")
        return {}

    # 查找目标任务
    target_file = None
    if task_id:
        target_file = h_dir / f"{task_id}.json"
        if not target_file.exists():
            # 尝试 history_ 前缀
            target_file = h_dir / f"history_{task_id}.json"
        if not target_file.exists():
            console.print(f"[red]❌ 找不到任务: {task_id}[/red]")
            return {}
    else:
        # 找最近的
        json_files = sorted(
            h_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True
        )
        if not json_files:
            console.print("[red]❌ 没有历史记录[/red]")
            return {}
        target_file = json_files[0]

    # 读取历史数据
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]❌ 读取失败: {e}[/red]")
        return {}

    # 构建分享记录
    share_id = _generate_share_id()
    now = datetime.now().isoformat()

    share_record = {
        "share_id": share_id,
        "version": 1,
        "created_at": now,
        "expires_at": (
            datetime.fromtimestamp(
                datetime.now().timestamp() + expires_hours * 3600
            ).isoformat()
            if expires_hours > 0
            else None
        ),
        "tags": tags or [],
        "session": {
            "history": history_data,
        },
    }

    # 可选包含配置
    if include_config:
        config_path = Path.home() / ".omc" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                # 脱敏：移除 API Key
                safe_config = _sanitize_config(config)
                share_record["session"]["config"] = safe_config
            except (json.JSONDecodeError, OSError):
                pass

    # 保存分享文件
    share_file = _share_path(share_id)
    with open(share_file, "w", encoding="utf-8") as f:
        json.dump(share_record, f, ensure_ascii=False, indent=2)

    console.print("[green]✅ 分享已创建[/green]")
    console.print(f"  Share ID: [bold cyan]{share_id}[/bold cyan]")
    console.print(f"  文件: {share_file}")

    return share_record


def _sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """脱敏配置，移除 API Key"""
    safe = {}
    for key, value in config.items():
        if isinstance(value, dict):
            safe[key] = _sanitize_config(value)
        elif isinstance(value, str) and (
            "key" in key.lower()
            or "token" in key.lower()
            or "secret" in key.lower()
            or "password" in key.lower()
        ):
            # 保留前 4 位 + ****
            safe[key] = value[:4] + "****" if len(value) > 4 else "****"
        else:
            safe[key] = value
    return safe


def import_session(share_id: str, target_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    通过分享 ID 导入会话。

    Args:
        share_id: 分享 ID
        target_dir: 导入目标目录

    Returns:
        导入的会话数据
    """
    _ensure_dir()

    share_file = _share_path(share_id)
    if not share_file.exists():
        console.print(f"[red]❌ 分享不存在: {share_id}[/red]")
        return {}

    try:
        with open(share_file, "r", encoding="utf-8") as f:
            share_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]❌ 读取分享失败: {e}[/red]")
        return {}

    # 检查过期
    if share_data.get("expires_at"):
        expires = datetime.fromisoformat(share_data["expires_at"])
        if datetime.now() > expires:
            console.print("[red]❌ 分享已过期[/red]")
            return {}

    # 导入历史记录
    session = share_data.get("session", {})
    history_data = session.get("history", {})

    if not history_data:
        console.print("[red]❌ 分享中没有历史数据[/red]")
        return {}

    t_dir = target_dir or Path(".omc/history")
    t_dir.mkdir(parents=True, exist_ok=True)

    # 生成新的历史 ID
    history_id = history_data.get("history_id", str(uuid.uuid4())[:8])
    imported_id = f"{history_id}_imported_{share_id}"

    history_data["history_id"] = imported_id
    history_data["imported_from"] = share_id
    history_data["imported_at"] = datetime.now().isoformat()

    # 保存到目标目录
    target_file = t_dir / f"history_{imported_id}.json"
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

    console.print("[green]✅ 会话已导入[/green]")
    console.print(f"  History ID: [bold cyan]{imported_id}[/bold cyan]")
    console.print(f"  来源分享: {share_id}")
    console.print(f"  文件: {target_file}")

    return history_data


def list_shares() -> List[Dict[str, Any]]:
    """列出所有分享"""
    _ensure_dir()

    shares = []
    for f in SHARE_DIR.glob("share_*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # 只返回摘要
            shares.append(
                {
                    "share_id": data.get("share_id"),
                    "created_at": data.get("created_at"),
                    "expires_at": data.get("expires_at"),
                    "tags": data.get("tags", []),
                    "task": data.get("session", {})
                    .get("history", {})
                    .get("task_description", "-"),
                    "steps": len(
                        data.get("session", {}).get("history", {}).get("steps", [])
                    ),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue

    shares.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return shares


def delete_share(share_id: str) -> bool:
    """删除分享"""
    share_file = _share_path(share_id)
    if not share_file.exists():
        console.print(f"[red]❌ 分享不存在: {share_id}[/red]")
        return False

    share_file.unlink()
    console.print(f"[green]✅ 分享已删除: {share_id}[/green]")
    return True


def get_share(share_id: str) -> Optional[Dict[str, Any]]:
    """获取分享详情"""
    share_file = _share_path(share_id)
    if not share_file.exists():
        return None

    try:
        with open(share_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ========================================
# CLI Commands
# ========================================


@app.command("create")
def share_create(
    task_id: Optional[str] = typer.Option(
        None, "--task", "-t", help="指定任务 ID（空则导出最近一次）"
    ),
    tags: Optional[str] = typer.Option(None, "--tags", help="标签，逗号分隔"),
    no_config: bool = typer.Option(False, "--no-config", help="不包含配置信息"),
    expires: int = typer.Option(
        0, "--expires", "-e", help="过期时间（小时），0=永不过期"
    ),
) -> None:
    """导出会话并生成分享链接"""
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    result = export_session(
        task_id=task_id,
        include_config=not no_config,
        tags=tag_list,
        expires_hours=expires,
    )
    if result:
        console.print(
            Panel(
                f"Share ID: [bold cyan]{result['share_id']}[/bold cyan]\n"
                f"创建时间: {result['created_at']}\n"
                f"过期: {result.get('expires_at') or '永不过期'}\n"
                f"标签: {', '.join(result.get('tags', [])) or '无'}",
                title="📤 分享已创建",
                border_style="green",
            )
        )


@app.command("import")
def share_import(
    share_id: str = typer.Argument(..., help="分享 ID"),
) -> None:
    """通过分享 ID 导入会话"""
    result = import_session(share_id)
    if result:
        console.print(
            Panel(
                f"History ID: [bold cyan]{result.get('history_id')}[/bold cyan]\n"
                f"来源: {share_id}",
                title="📥 会话已导入",
                border_style="green",
            )
        )


@app.command("list")
def share_list() -> None:
    """列出所有分享"""
    shares = list_shares()
    if not shares:
        console.print("[dim]暂无分享记录[/dim]")
        return

    table = Table(title="📤 分享列表", show_lines=True)
    table.add_column("Share ID", style="cyan")
    table.add_column("任务描述", max_width=40)
    table.add_column("步骤数", justify="right")
    table.add_column("创建时间")
    table.add_column("过期")
    table.add_column("标签")

    for s in shares:
        expired = ""
        if s.get("expires_at"):
            exp = datetime.fromisoformat(s["expires_at"])
            expired = "❌ 已过期" if datetime.now() > exp else "✅ 有效"
        else:
            expired = "♾️ 永久"

        table.add_row(
            s["share_id"],
            s.get("task", "-")[:40],
            str(s.get("steps", 0)),
            (s.get("created_at") or "")[:19],
            expired,
            ", ".join(s.get("tags", [])) or "-",
        )

    console.print(table)


@app.command("delete")
def share_delete(
    share_id: str = typer.Argument(..., help="分享 ID"),
) -> None:
    """删除分享"""
    delete_share(share_id)


@app.command("show")
def share_show(
    share_id: str = typer.Argument(..., help="分享 ID"),
) -> None:
    """查看分享详情"""
    data = get_share(share_id)
    if not data:
        console.print(f"[red]❌ 分享不存在: {share_id}[/red]")
        return

    session = data.get("session", {})
    history = session.get("history", {})

    console.print(
        Panel(
            f"Share ID: [bold cyan]{data['share_id']}[/bold cyan]\n"
            f"版本: v{data.get('version', 1)}\n"
            f"创建: {data.get('created_at')}\n"
            f"过期: {data.get('expires_at') or '永不过期'}\n"
            f"标签: {', '.join(data.get('tags', [])) or '无'}\n"
            f"---\n"
            f"任务: {history.get('task_description', '-')}\n"
            f"工作流: {history.get('workflow_name', '-')}\n"
            f"步骤数: {len(history.get('steps', []))}\n"
            f"总 Token: {history.get('total_tokens', 0)}\n"
            f"总成本: ¥{history.get('total_cost', 0):.4f}\n"
            f"含配置: {'是' if 'config' in session else '否'}",
            title="📋 分享详情",
            border_style="cyan",
        )
    )
