from __future__ import annotations
import hashlib
import hmac
import time
import urllib.parse
import urllib.request

"""
Quest 通知系统

支持桌面通知（macOS/Windows）和钉钉 Webhook。
"""

import json
import logging
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

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

    def __init__(self, webhook_url: str | None = None, secret: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("DINGTALK_WEBHOOK_URL", "")
        self.secret = secret or os.environ.get("DINGTALK_SECRET", "")

    def send(self, title: str, body: str, level: str = "info") -> bool:
        if not self.webhook_url:
            return False

        try:
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
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("errcode", 1) == 0
        except Exception as e:
            logger.warning(f"DingTalk notification failed: {e}")
            return False


class TelegramNotificationChannel(NotificationChannel):
    """Telegram Bot API 通知"""

    name = "telegram"

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

    def send(self, title: str, body: str, level: str = "info") -> bool:
        if not self.bot_token or not self.chat_id:
            return False

        try:
            emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "🚨"}.get(
                level, "ℹ️"
            )
            text = f"{emoji} **{title}**\n\n{body}\n\n_{datetime.now().strftime('%H:%M:%S')}_"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            data = json.dumps(payload).encode("utf-8")
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("ok", False) is True
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")
            return False


class DiscordNotificationChannel(NotificationChannel):
    """Discord Webhook 通知"""

    name = "discord"

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK", "")

    def send(self, title: str, body: str, level: str = "info") -> bool:
        if not self.webhook_url:
            return False

        try:
            color_map = {
                "info": 3447003,  # 蓝色
                "success": 3066993,  # 绿色
                "warning": 16761527,  # 橙色
                "error": 15158332,  # 红色
            }
            color = color_map.get(level, 3447003)
            payload = {
                "embeds": [
                    {
                        "title": title,
                        "description": body,
                        "color": color,
                        "footer": {
                            "text": f"Oh My Coder • {datetime.now().strftime('%H:%M:%S')}"
                        },
                    }
                ]
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                return resp.status == 200 or resp.status == 204
        except Exception as e:
            logger.warning(f"Discord notification failed: {e}")
            return False


class SlackNotificationChannel(NotificationChannel):
    """Slack Incoming Webhook 通知"""

    name = "slack"

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK", "")

    def send(self, title: str, body: str, level: str = "info") -> bool:
        if not self.webhook_url:
            return False

        try:
            emoji = {
                "info": ":information_source:",
                "success": ":white_check_mark:",
                "warning": ":warning:",
                "error": ":x:",
            }.get(level, ":information_source:")
            payload = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": emoji + " " + title,
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": body},
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"_Oh My Coder • {datetime.now().strftime('%H:%M:%S')}_",
                            },
                        ],
                    },
                ]
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                return resp.status == 200
        except Exception as e:
            logger.warning(f"Slack notification failed: {e}")
            return False


class TeamsNotificationChannel(NotificationChannel):
    """Microsoft Teams Incoming Webhook 通知"""

    name = "teams"

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("TEAMS_WEBHOOK", "")

    def send(self, title: str, body: str, level: str = "info") -> bool:
        if not self.webhook_url:
            return False

        try:
            color_map = {
                "info": "0078D4",
                "success": "107C10",
                "warning": "FF8C00",
                "error": "D13438",
            }
            color = color_map.get(level, "0078D4")
            payload = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                            "type": "AdaptiveCard",
                            "version": "1.4",
                            "body": [
                                {
                                    "type": "Container",
                                    "style": color,
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": title,
                                            "weight": "Bolder",
                                            "size": "Medium",
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": body,
                                            "wrap": True,
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": f"Oh My Coder • {datetime.now().strftime('%H:%M:%S')}",
                                            "size": "Small",
                                            "isSubtle": True,
                                        },
                                    ],
                                }
                            ],
                        },
                    }
                ],
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                return resp.status == 200
        except Exception as e:
            logger.warning(f"Teams notification failed: {e}")
            return False


class FeishuNotificationChannel(NotificationChannel):
    """飞书（Lark）自定义机器人 Webhook 通知"""

    name = "feishu"

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("FEISHU_WEBHOOK", "")

    def send(self, title: str, body: str, level: str = "info") -> bool:
        if not self.webhook_url:
            return False

        try:
            emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "🚨"}.get(
                level, "ℹ️"
            )
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "text": f"{emoji} {title}"},
                        "template": "blue",
                    },
                    "elements": [
                        {"tag": "div", "text": {"tag": "lark_md", "content": body}},
                        {
                            "tag": "note",
                            "elements": [
                                {
                                    "tag": "plain_text",
                                    "text": datetime.now().strftime("%H:%M:%S"),
                                }
                            ],
                        },
                    ],
                },
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("code", 1) == 0
        except Exception as e:
            logger.warning(f"Feishu notification failed: {e}")
            return False


class WeComNotificationChannel(NotificationChannel):
    """企业微信 Webhook 通知"""

    name = "wecom"

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.environ.get("WECOM_WEBHOOK", "")

    def send(self, title: str, body: str, level: str = "info") -> bool:
        if not self.webhook_url:
            return False

        try:
            emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "🚨"}.get(
                level, "ℹ️"
            )
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"{emoji} **{title}**\n\n{body}\n\n> Oh My Coder • {datetime.now().strftime('%H:%M:%S')}",
                },
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("errcode", 1) == 0
        except Exception as e:
            logger.warning(f"WeCom notification failed: {e}")
            return False


class PushPlusNotificationChannel(NotificationChannel):
    """PushPlus 微信公众号推送通知"""

    name = "pushplus"

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("PUSHPLUS_TOKEN", "")

    def send(self, title: str, body: str, level: str = "info") -> bool:
        if not self.token:
            return False

        try:
            text = f"**{title}**\n\n{body}\n\n_{datetime.now().strftime('%H:%M:%S')}_"
            encoded = urllib.parse.urlencode(
                {"token": self.token, "content": text, "type": "text"}
            )
            url = f"https://www.pushplus.plus/send?{encoded}"
            req = urllib.request.Request(
                url, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("code", 1) == 200
        except Exception as e:
            logger.warning(f"PushPlus notification failed: {e}")
            return False


class ConsoleNotificationChannel(NotificationChannel):
    """控制台通知（CLI 实时输出）"""

    name = "console"

    def __init__(self, callback: Callable[[str, str, str], None] | None = None):
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
    dingtalk_webhook: str | None = None
    dingtalk_secret: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_webhook: str | None = None
    slack_webhook: str | None = None
    teams_webhook: str | None = None
    feishu_webhook: str | None = None
    wecom_webhook: str | None = None
    pushplus_token: str | None = None
    console_callback: Callable[[str, str, str], None] | None = None


class NotificationManager:
    """
    Quest 通知管理器

    支持多渠道通知：桌面、钉钉、控制台回调。
    """

    def __init__(self, config: NotificationConfig | None = None):
        self.config = config or NotificationConfig()
        self._channels: list[NotificationChannel] = []

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

        # Telegram
        if self.config.telegram_bot_token and self.config.telegram_chat_id:
            self._channels.append(
                TelegramNotificationChannel(
                    bot_token=self.config.telegram_bot_token,
                    chat_id=self.config.telegram_chat_id,
                )
            )

        # Discord
        if self.config.discord_webhook:
            self._channels.append(
                DiscordNotificationChannel(webhook_url=self.config.discord_webhook)
            )

        # Slack
        if self.config.slack_webhook:
            self._channels.append(
                SlackNotificationChannel(webhook_url=self.config.slack_webhook)
            )

        # Microsoft Teams
        if self.config.teams_webhook:
            self._channels.append(
                TeamsNotificationChannel(webhook_url=self.config.teams_webhook)
            )

        # 飞书
        if self.config.feishu_webhook:
            self._channels.append(
                FeishuNotificationChannel(webhook_url=self.config.feishu_webhook)
            )

        # 企业微信
        if self.config.wecom_webhook:
            self._channels.append(
                WeComNotificationChannel(webhook_url=self.config.wecom_webhook)
            )

        # PushPlus
        if self.config.pushplus_token:
            self._channels.append(
                PushPlusNotificationChannel(token=self.config.pushplus_token)
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
        event: str | None = None,
        quest_id: str | None = None,
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
    dingtalk_webhook: str | None = None,
    dingtalk_secret: str | None = None,
) -> NotificationManager:
    """创建通知管理器（兼容旧 API）"""
    config = NotificationConfig(
        desktop=desktop,
        dingtalk_webhook=dingtalk_webhook,
        dingtalk_secret=dingtalk_secret,
    )
    return NotificationManager(config)
