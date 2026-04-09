"""
系统通知工具 - 零依赖，使用 macOS 原生 osascript
"""

import subprocess
import sys
from typing import Optional


def send_notification(
    title: str,
    message: str,
    subtitle: Optional[str] = None,
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
            'display notification ""%s""' % message.replace('"', '\\"'),
        ]
        if subtitle:
            script_parts[0] = (
                'display notification "%s" with title "%s" subtitle "%s"'
                % (
                    message.replace('"', '\\"'),
                    title.replace('"', '\\"'),
                    subtitle.replace('"', '\\"'),
                )
            )
        else:
            script_parts[0] = 'display notification "%s" with title "%s"' % (
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
