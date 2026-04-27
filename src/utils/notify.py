from __future__ import annotations
"""
系统通知工具 - 零依赖，使用 macOS 原生 osascript + 钉钉 webhook
"""

import json
import os
import subprocess
import sys
import urllib.request


def send_notification(
    title: str,
    message: str,
    subtitle: str | None = None,
    sound: bool = True,
) -> bool:
    """
    发送系统通知（macOS）。

    Args:
        title: 通知标题
        message: 通知内容
        subtitle: 副标题（可选）
        sound: 是否播放提示音

    Returns:
        True 发送成功，False 失败
    """
    if sys.platform != "darwin":
        return False

    try:
        script_parts = [
            'display notification ""{}""'.format(message.replace('"', '\\"')),
        ]
        if subtitle:
            script_parts[0] = (
                'display notification "{}" with title "{}" subtitle "{}"'.format(
                    message.replace('"', '\\"'),
                    title.replace('"', '\\"'),
                    subtitle.replace('"', '\\"'),
                )
            )
        else:
            script_parts[0] = 'display notification "{}" with title "{}"'.format(
                message.replace('"', '\\"'),
                title.replace('"', '\\"'),
            )

        if not sound:
            script_parts[0] += ' sound name ""'

        script = " ".join(script_parts)
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def notify_workflow_complete(
    workflow: str,
    status: str,
    steps_completed: int,
    execution_time: float,
) -> bool:
    """通知工作流完成"""
    status_icon = "✅" if status == "completed" else "❌"
    return send_notification(
        title=f"Oh My Coder {status_icon} 工作流完成",
        message=f"{workflow}: {steps_completed} 步骤，{execution_time:.1f}s",
        subtitle=f"状态: {status}",
    )


def notify_quest_update(quest_name: str, message: str) -> bool:
    """通知 Quest 更新（用于异步任务）"""
    return send_notification(
        title=f"📋 Quest: {quest_name}",
        message=message,
    )


# ============================================================
# 钉钉通知
# ============================================================


def send_dingtalk_notification(
    webhook_url: str,
    title: str,
    message: str,
    at_all: bool = False,
) -> bool:
    """
    发送钉钉群机器人通知。

    Args:
        webhook_url: 钉钉机器人 webhook URL
        title: 消息标题
        message: 消息内容
        at_all: 是否 @所有人

    Returns:
        True 发送成功，False 失败
    """
    try:
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"### {title}\n\n{message}",
            },
            "at": {
                "isAtAll": at_all,
            },
        }

        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("errcode") == 0

    except Exception:
        return False


def notify_workflow_complete_dingtalk(
    webhook_url: str | None,
    workflow: str,
    status: str,
    steps_completed: int,
    execution_time: float,
    project_path: str = "",
) -> bool:
    """通过钉钉通知工作流完成"""
    if not webhook_url:
        webhook_url = os.environ.get("DINGTALK_WEBHOOK")

    if not webhook_url:
        return False

    status_icon = "✅" if status == "completed" else "❌"
    status_text = "成功" if status == "completed" else "失败"

    message = f"""**工作流**: {workflow}
**状态**: {status_text} {status_icon}
**完成步骤**: {steps_completed}
**执行时间**: {execution_time:.1f}s
"""
    if project_path:
        message += f"**项目路径**: `{project_path}`"

    return send_dingtalk_notification(
        webhook_url=webhook_url,
        title="Oh My Coder - 工作流完成通知",
        message=message,
    )


def notify_quest_update_dingtalk(
    webhook_url: str | None,
    quest_name: str,
    message: str,
    status: str = "running",
) -> bool:
    """通过钉钉通知 Quest 更新"""
    if not webhook_url:
        webhook_url = os.environ.get("DINGTALK_WEBHOOK")

    if not webhook_url:
        return False

    status_icons = {
        "completed": "✅",
        "failed": "❌",
        "running": "⏳",
        "pending_review": "👀",
    }
    icon = status_icons.get(status, "📋")

    return send_dingtalk_notification(
        webhook_url=webhook_url,
        title=f"{icon} Quest: {quest_name}",
        message=message,
    )
