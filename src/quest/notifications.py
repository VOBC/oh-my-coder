"""
Quest 通知系统

支持桌面通知（macOS/Windows）和钉钉 Webhook。
"""

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


# ============================================================
# 通知渠道抽象
# ============================================================


class NotificationChannel:
    """通知渠道基类"""

    name: str = "base"

    def send(self, title: str, body: str, level: str = "info") -> bool:
        """发送通知，返回是否成功"""
        raise NotImplementedError


class MacOSNotificationChannel(NotificationChannel):
    """macOS 桌面通知（使用 osascript）"""

    name = "macos"

    def send(self, title: str, body: str, level: str = "info") -> bool:
        try:
            # macOS notification via osascript
            script = f'display notification "{_escape_shell(body)}" with title "{_escape_shell(title)}"'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"macOS notification failed: {e}")
            return False


class WindowsNotificationChannel(NotificationChannel):
    """Windows 桌面通知（使用 PowerShell）"""

    name = "windows"

    def send(self, title: str, body: str, level: str = "info") -> bool:
        try:
            script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
            $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
            $text = $xml.GetElementsByTagName("text")
            $text[0].AppendChild($xml.CreateTextNode("{_escape_shell(title)}")) | Out-Null
            $text[1].AppendChild($xml.CreateTextNode("{_escape_shell(body)}")) | Out-Null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("oh-my-coder").Show($toast)
            """
            subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True,
                timeout=10,
            )
            return True
        except Exception as e:
            logger.warning(f"Windows notification failed: {e}")
            return False


class DingTalkNotificationChannel(NotificationChannel):
    """钉钉自定义机器人 Webhook"""

    name = "dingtalk"

    def __init__(self, webhook_url: Optional[str] = None, secret: Optional[str] = None):
        self.webhook_url = webhook_url or os.environ.get("DINGTALK_WEBHOOK_URL", "")
        self.secret = secret or os.environ.get("DINGTALK_SECRET", "")

    def send(self, title: str, body: str, level: str = "info") -> bool:
        if not self.webhook_url:
            return False

        try:
            import hashlib
            import hmac
            import time
            import urllib.parse
            import urllib.request

            # 钉钉签名
            if self.secret:
                timestamp = str(round(time.time() * 1000))
                secret_enc = self.secret.encode("utf-8")
                string_to_sign = f"{timestamp}\n{self.secret}"
                string_to_sign_enc = string_to_sign.encode("utf-8")
                hmac_code = hmac.new(
                    secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
                ).digest()
                sign = urllib.parse.quote_plus(
                    hmac.b64encode(hmac_code).decode("utf-8")
                )
                url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
            else:
                url = self.webhook_url

            # Markdown 格式
            emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "🚨"}.get(
                level, "ℹ️"
            )
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"{emoji} {title}",
                    "text": f"### {emoji} **{title}**\n\n{body}\n\n_{datetime.now().strftime('%H:%M:%S')}_",
                },
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("errcode", 1) == 0
        except Exception as e:
            logger.warning(f"DingTalk notification failed: {e}")
            return False


class ConsoleNotificationChannel(NotificationChannel):
    """控制台通知（CLI 实时输出）"""

    name = "console"

    def __init__(self, callback: Optional[Callable[[str, str, str], None]] = None):
        self.callback = callback

    def send(self, title: str, body: str, level: str = "info") -> bool:
        if self.callback:
            self.callback(title, body, level)
        return True


# ============================================================
# 通知管理器
# ============================================================


@dataclass
class NotificationConfig:
    """通知配置"""

    desktop: bool = True  # 桌面通知
    dingtalk_webhook: Optional[str] = None
    dingtalk_secret: Optional[str] = None
    console_callback: Optional[Callable[[str, str, str], None]] = None


class NotificationManager:
    """
    Quest 通知管理器

    支持多渠道通知：桌面、钉钉、控制台回调。
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self._channels: List[NotificationChannel] = []

        # 自动检测平台并初始化桌面通知
        if self.config.desktop:
            self._init_desktop_channel()

        # 钉钉
        if self.config.dingtalk_webhook:
            self._channels.append(
                DingTalkNotificationChannel(
                    webhook_url=self.config.dingtalk_webhook,
                    secret=self.config.dingtalk_secret,
                )
            )

        # 控制台
        if self.config.console_callback:
            self._channels.append(
                ConsoleNotificationChannel(callback=self.config.console_callback)
            )

        # 如果没有任何渠道，至少加一个 console channel
        if not self._channels:
            self._channels.append(ConsoleNotificationChannel())

    def _init_desktop_channel(self) -> None:
        """根据操作系统初始化桌面通知"""
        if sys.platform == "darwin":
            self._channels.append(MacOSNotificationChannel())
        elif sys.platform == "win32":
            self._channels.append(WindowsNotificationChannel())
        # Linux 可以扩展（notify-send 等）

    def _level_from_event(self, event: str) -> str:
        """从事件类型判断通知级别"""
        level_map = {
            "started": "info",
            "spec_ready": "info",
            "step_completed": "info",
            "paused": "warning",
            "resumed": "info",
            "waiting_input": "warning",
            "completed": "success",
            "failed": "error",
            "cancelled": "warning",
        }
        return level_map.get(event, "info")

    def send(
        self,
        title: str,
        body: str,
        event: Optional[str] = None,
        quest_id: Optional[str] = None,
    ) -> None:
        """发送通知到所有已配置的渠道"""
        level = self._level_from_event(event) if event else "info"

        for channel in self._channels:
            try:
                channel.send(title, body, level)
            except Exception as e:
                logger.warning(f"Channel {channel.name} failed: {e}")

    # ============================================================
    # 便捷方法
    # ============================================================

    def notify_started(self, quest_title: str, quest_id: str) -> None:
        self.send("🧙 Quest 已启动", quest_title, "started", quest_id)

    def notify_spec_ready(self, quest_title: str, quest_id: str) -> None:
        self.send(
            "📋 SPEC 已生成",
            f"Quest [{quest_id[:8]}] {quest_title}\n请审查并确认执行",
            "spec_ready",
            quest_id,
        )

    def notify_step_completed(self, step_title: str, quest_id: str) -> None:
        self.send("✅ 步骤完成", step_title, "step_completed", quest_id)

    def notify_step_failed(self, step_title: str, error: str, quest_id: str) -> None:
        self.send("⚠️ 步骤失败", f"{step_title}\n{error}", "failed", quest_id)

    def notify_completed(self, quest_title: str, summary: str, quest_id: str) -> None:
        self.send("🎉 Quest 完成！", f"{quest_title}\n{summary}", "completed", quest_id)

    def notify_failed(self, quest_title: str, error: str, quest_id: str) -> None:
        self.send("❌ Quest 失败", f"{quest_title}\n{error}", "failed", quest_id)

    def notify_waiting_input(
        self, quest_title: str, message: str, quest_id: str
    ) -> None:
        self.send("⏸️ 等待输入", f"{quest_title}\n{message}", "waiting_input", quest_id)

    def notify_paused(self, quest_title: str, quest_id: str) -> None:
        self.send("⏸️ Quest 已暂停", quest_title, "paused", quest_id)

    def notify_resumed(self, quest_title: str, quest_id: str) -> None:
        self.send("▶️ Quest 已恢复", quest_title, "resumed", quest_id)


# ============================================================
# 辅助函数
# ============================================================


def _escape_shell(text: str) -> str:
    """转义 shell 特殊字符"""
    return text.replace('"', '\\"').replace("\\", "\\\\").replace("\n", " ")


def create_notification_manager(
    desktop: bool = True,
    dingtalk_webhook: Optional[str] = None,
    dingtalk_secret: Optional[str] = None,
) -> NotificationManager:
    """创建通知管理器（兼容旧 API）"""
    config = NotificationConfig(
        desktop=desktop,
        dingtalk_webhook=dingtalk_webhook,
        dingtalk_secret=dingtalk_secret,
    )
    return NotificationManager(config)
