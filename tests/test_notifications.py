"""
Tests for src/quest/notifications.py

Coverage target: Increase from 32% to >90%
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.quest.notifications import (
    ConsoleNotificationChannel,
    DingTalkNotificationChannel,
    DiscordNotificationChannel,
    FeishuNotificationChannel,
    MacOSNotificationChannel,
    NotificationChannel,
    NotificationConfig,
    NotificationManager,
    PushPlusNotificationChannel,
    SlackNotificationChannel,
    TeamsNotificationChannel,
    TelegramNotificationChannel,
    WeComNotificationChannel,
    WindowsNotificationChannel,
    _escape_shell,
    create_notification_manager,
)


def _make_urlopen_mock(response_data=None, status=200):
    """Helper to create a properly configured urlopen mock"""
    mock_response = MagicMock()
    if response_data is not None:
        mock_response.read.return_value = response_data
    mock_response.status = status

    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_response)
    mock_cm.__exit__ = MagicMock(return_value=False)

    return mock_cm, mock_response


# ============================================================
# Helper Functions
# ============================================================


class TestEscapeShell:
    """Tests for _escape_shell function"""

    def test_escape_double_quote(self):
        """Test escaping double quotes"""
        result = _escape_shell('Hello "World"')
        # Should contain \" (escaped quote)
        assert '\\"' in result
        assert result == 'Hello \\"World\\"'

    def test_escape_backslash(self):
        """Test escaping backslashes"""
        result = _escape_shell("C:\\Path\\File")
        assert result == "C:\\\\Path\\\\File"

    def test_escape_newline(self):
        """Test escaping newlines"""
        result = _escape_shell("Line1\nLine2")
        assert result == "Line1 Line2"
        assert "\n" not in result

    def test_escape_mixed(self):
        """Test escaping mixed special characters"""
        text = 'He said "Hello\\World"\nEnd'
        result = _escape_shell(text)
        # Should not contain newline
        assert "\n" not in result
        # Should be a valid string
        assert isinstance(result, str)

    def test_no_special_chars(self):
        """Test text without special characters"""
        assert _escape_shell("Hello World") == "Hello World"

    def test_empty_string(self):
        """Test empty string"""
        assert _escape_shell("") == ""


# ============================================================
# NotificationChannel Base Class
# ============================================================


class TestNotificationChannel:
    """Tests for NotificationChannel base class"""

    def test_send_not_implemented(self):
        """Test that base class raises NotImplementedError"""
        channel = NotificationChannel()
        with pytest.raises(NotImplementedError):
            channel.send("title", "body")


# ============================================================
# MacOSNotificationChannel
# ============================================================


class TestMacOSNotificationChannel:
    """Tests for MacOSNotificationChannel"""

    @patch("src.quest.notifications.subprocess.run")
    def test_send_success(self, mock_run):
        """Test successful notification send"""
        mock_run.return_value = MagicMock(returncode=0)
        channel = MacOSNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is True
        mock_run.assert_called_once()

    @patch("src.quest.notifications.subprocess.run")
    def test_send_failure(self, mock_run):
        """Test failed notification send"""
        mock_run.return_value = MagicMock(returncode=1)
        channel = MacOSNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    @patch("src.quest.notifications.subprocess.run")
    def test_send_exception(self, mock_run):
        """Test exception during send"""
        mock_run.side_effect = Exception("Test exception")
        channel = MacOSNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_name_attribute(self):
        """Test channel name"""
        channel = MacOSNotificationChannel()
        assert channel.name == "macos"


# ============================================================
# WindowsNotificationChannel
# ============================================================


class TestWindowsNotificationChannel:
    """Tests for WindowsNotificationChannel"""

    @patch("src.quest.notifications.subprocess.run")
    def test_send_success(self, mock_run):
        """Test successful notification send"""
        mock_run.return_value = MagicMock(returncode=0)
        channel = WindowsNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is True

    @patch("src.quest.notifications.subprocess.run")
    def test_send_exception(self, mock_run):
        """Test exception during send"""
        mock_run.side_effect = Exception("Test exception")
        channel = WindowsNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_name_attribute(self):
        """Test channel name"""
        channel = WindowsNotificationChannel()
        assert channel.name == "windows"


# ============================================================
# DingTalkNotificationChannel
# ============================================================


class TestDingTalkNotificationChannel:
    """Tests for DingTalkNotificationChannel"""

    def test_init_with_params(self):
        """Test initialization with parameters"""
        channel = DingTalkNotificationChannel(
            webhook_url="https://oapi.dingtalk.com/test",
            secret="test_secret",
        )
        assert channel.webhook_url == "https://oapi.dingtalk.com/test"
        assert channel.secret == "test_secret"

    @patch.dict(os.environ, {"DINGTALK_WEBHOOK_URL": "https://env.url", "DINGTALK_SECRET": "env_secret"})
    def test_init_from_env(self):
        """Test initialization from environment variables"""
        channel = DingTalkNotificationChannel()
        assert channel.webhook_url == "https://env.url"
        assert channel.secret == "env_secret"

    def test_init_empty(self):
        """Test initialization with empty values"""
        channel = DingTalkNotificationChannel()
        assert channel.webhook_url == ""
        assert channel.secret == ""

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_with_secret(self, mock_urlopen):
        """Test send with secret (signature)"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"errcode": 0}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = DingTalkNotificationChannel(
            webhook_url="https://oapi.dingtalk.com/test",
            secret="test_secret",
        )
        result = channel.send("Test Title", "Test Body", level="info")
        assert result is True

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_without_secret(self, mock_urlopen):
        """Test send without secret"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"errcode": 0}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = DingTalkNotificationChannel(
            webhook_url="https://oapi.dingtalk.com/test",
        )
        result = channel.send("Test Title", "Test Body")
        assert result is True

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_failure_errcode(self, mock_urlopen):
        """Test send with errcode != 0"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"errcode": 1}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = DingTalkNotificationChannel(
            webhook_url="https://oapi.dingtalk.com/test",
        )
        result = channel.send("Test Title", "Test Body")
        assert result is False

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_exception(self, mock_urlopen):
        """Test exception during send"""
        mock_urlopen.side_effect = Exception("Test exception")
        channel = DingTalkNotificationChannel(
            webhook_url="https://oapi.dingtalk.com/test",
        )
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_send_no_webhook_url(self):
        """Test send without webhook URL"""
        channel = DingTalkNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_name_attribute(self):
        """Test channel name"""
        channel = DingTalkNotificationChannel()
        assert channel.name == "dingtalk"

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_different_levels(self, mock_urlopen):
        """Test send with different levels"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"errcode": 0}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = DingTalkNotificationChannel(
            webhook_url="https://oapi.dingtalk.com/test",
        )
        for level in ["info", "success", "warning", "error"]:
            result = channel.send("Title", "Body", level=level)
            assert result is True


# ============================================================
# TelegramNotificationChannel
# ============================================================


class TestTelegramNotificationChannel:
    """Tests for TelegramNotificationChannel"""

    def test_init_with_params(self):
        """Test initialization with parameters"""
        channel = TelegramNotificationChannel(
            bot_token="test_token",
            chat_id="test_chat_id",
        )
        assert channel.bot_token == "test_token"
        assert channel.chat_id == "test_chat_id"

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "env_token", "TELEGRAM_CHAT_ID": "env_chat"})
    def test_init_from_env(self):
        """Test initialization from environment variables"""
        channel = TelegramNotificationChannel()
        assert channel.bot_token == "env_token"
        assert channel.chat_id == "env_chat"

    def test_init_empty(self):
        """Test initialization with empty values"""
        channel = TelegramNotificationChannel()
        assert channel.bot_token == ""
        assert channel.chat_id == ""

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        """Test successful send"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"ok": True}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = TelegramNotificationChannel(
            bot_token="test_token",
            chat_id="test_chat_id",
        )
        result = channel.send("Test Title", "Test Body")
        assert result is True

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_failure(self, mock_urlopen):
        """Test failed send (ok != True)"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"ok": False}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = TelegramNotificationChannel(
            bot_token="test_token",
            chat_id="test_chat_id",
        )
        result = channel.send("Test Title", "Test Body")
        assert result is False

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_exception(self, mock_urlopen):
        """Test exception during send"""
        mock_urlopen.side_effect = Exception("Test exception")
        channel = TelegramNotificationChannel(
            bot_token="test_token",
            chat_id="test_chat_id",
        )
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_send_no_credentials(self):
        """Test send without credentials"""
        channel = TelegramNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_name_attribute(self):
        """Test channel name"""
        channel = TelegramNotificationChannel()
        assert channel.name == "telegram"


# ============================================================
# DiscordNotificationChannel
# ============================================================


class TestDiscordNotificationChannel:
    """Tests for DiscordNotificationChannel"""

    def test_init_with_params(self):
        """Test initialization with parameters"""
        channel = DiscordNotificationChannel(webhook_url="https://discord.com/test")
        assert channel.webhook_url == "https://discord.com/test"

    @patch.dict(os.environ, {"DISCORD_WEBHOOK": "https://discord.com/env"})
    def test_init_from_env(self):
        """Test initialization from environment variables"""
        channel = DiscordNotificationChannel()
        assert channel.webhook_url == "https://discord.com/env"

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_success_200(self, mock_urlopen):
        """Test successful send (200)"""
        mock_cm, _ = _make_urlopen_mock(status=200)
        mock_urlopen.return_value = mock_cm

        channel = DiscordNotificationChannel(webhook_url="https://discord.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is True

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_success_204(self, mock_urlopen):
        """Test successful send (204)"""
        mock_cm, _ = _make_urlopen_mock(status=204)
        mock_urlopen.return_value = mock_cm

        channel = DiscordNotificationChannel(webhook_url="https://discord.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is True

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_failure(self, mock_urlopen):
        """Test failed send"""
        mock_cm, _ = _make_urlopen_mock(status=400)
        mock_urlopen.return_value = mock_cm

        channel = DiscordNotificationChannel(webhook_url="https://discord.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_exception(self, mock_urlopen):
        """Test exception during send"""
        mock_urlopen.side_effect = Exception("Test exception")
        channel = DiscordNotificationChannel(webhook_url="https://discord.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_send_no_webhook_url(self):
        """Test send without webhook URL"""
        channel = DiscordNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_name_attribute(self):
        """Test channel name"""
        channel = DiscordNotificationChannel()
        assert channel.name == "discord"

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_color_mapping(self, mock_urlopen):
        """Test color mapping for different levels"""
        channel = DiscordNotificationChannel(webhook_url="https://discord.com/test")
        color_map = {
            "info": 3447003,
            "success": 3066993,
            "warning": 16761527,
            "error": 15158332,
        }
        for level, expected_color in color_map.items():
            mock_cm, mock_response = _make_urlopen_mock(status=200)
            mock_urlopen.return_value = mock_cm

            channel.send("Title", "Body", level=level)
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            payload = json.loads(request.data.decode("utf-8"))
            actual_color = payload["embeds"][0]["color"]
            assert actual_color == expected_color, f"Color mismatch for level {level}"


# ============================================================
# SlackNotificationChannel
# ============================================================


class TestSlackNotificationChannel:
    """Tests for SlackNotificationChannel"""

    def test_init_with_params(self):
        """Test initialization with parameters"""
        channel = SlackNotificationChannel(webhook_url="https://hooks.slack.com/test")
        assert channel.webhook_url == "https://hooks.slack.com/test"

    @patch.dict(os.environ, {"SLACK_WEBHOOK": "https://hooks.slack.com/env"})
    def test_init_from_env(self):
        """Test initialization from environment variables"""
        channel = SlackNotificationChannel()
        assert channel.webhook_url == "https://hooks.slack.com/env"

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        """Test successful send"""
        mock_cm, _ = _make_urlopen_mock(status=200)
        mock_urlopen.return_value = mock_cm

        channel = SlackNotificationChannel(webhook_url="https://hooks.slack.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is True

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_failure(self, mock_urlopen):
        """Test failed send"""
        mock_cm, _ = _make_urlopen_mock(status=400)
        mock_urlopen.return_value = mock_cm

        channel = SlackNotificationChannel(webhook_url="https://hooks.slack.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_exception(self, mock_urlopen):
        """Test exception during send"""
        mock_urlopen.side_effect = Exception("Test exception")
        channel = SlackNotificationChannel(webhook_url="https://hooks.slack.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_send_no_webhook_url(self):
        """Test send without webhook URL"""
        channel = SlackNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_name_attribute(self):
        """Test channel name"""
        channel = SlackNotificationChannel()
        assert channel.name == "slack"

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_blocks_structure(self, mock_urlopen):
        """Test payload blocks structure"""
        mock_cm, _ = _make_urlopen_mock(status=200)
        mock_urlopen.return_value = mock_cm

        channel = SlackNotificationChannel(webhook_url="https://hooks.slack.com/test")
        channel.send("Test Title", "Test Body")

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        payload = json.loads(request.data.decode("utf-8"))

        assert "blocks" in payload
        assert len(payload["blocks"]) == 3
        assert payload["blocks"][0]["type"] == "header"
        assert payload["blocks"][1]["type"] == "section"
        assert payload["blocks"][2]["type"] == "context"


# ============================================================
# TeamsNotificationChannel
# ============================================================


class TestTeamsNotificationChannel:
    """Tests for TeamsNotificationChannel"""

    def test_init_with_params(self):
        """Test initialization with parameters"""
        channel = TeamsNotificationChannel(webhook_url="https://outlook.office.com/test")
        assert channel.webhook_url == "https://outlook.office.com/test"

    @patch.dict(os.environ, {"TEAMS_WEBHOOK": "https://outlook.office.com/env"})
    def test_init_from_env(self):
        """Test initialization from environment variables"""
        channel = TeamsNotificationChannel()
        assert channel.webhook_url == "https://outlook.office.com/env"

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        """Test successful send"""
        mock_cm, _ = _make_urlopen_mock(status=200)
        mock_urlopen.return_value = mock_cm

        channel = TeamsNotificationChannel(webhook_url="https://outlook.office.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is True

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_failure(self, mock_urlopen):
        """Test failed send"""
        mock_cm, _ = _make_urlopen_mock(status=400)
        mock_urlopen.return_value = mock_cm

        channel = TeamsNotificationChannel(webhook_url="https://outlook.office.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_exception(self, mock_urlopen):
        """Test exception during send"""
        mock_urlopen.side_effect = Exception("Test exception")
        channel = TeamsNotificationChannel(webhook_url="https://outlook.office.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_send_no_webhook_url(self):
        """Test send without webhook URL"""
        channel = TeamsNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_name_attribute(self):
        """Test channel name"""
        channel = TeamsNotificationChannel()
        assert channel.name == "teams"

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_color_mapping(self, mock_urlopen):
        """Test color mapping for different levels"""
        color_map = {
            "info": "0078D4",
            "success": "107C10",
            "warning": "FF8C00",
            "error": "D13438",
        }
        for level, expected_color in color_map.items():
            mock_cm, mock_response = _make_urlopen_mock(status=200)
            mock_urlopen.return_value = mock_cm

            channel = TeamsNotificationChannel(webhook_url="https://outlook.office.com/test")
            channel.send("Title", "Body", level=level)
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            payload = json.loads(request.data.decode("utf-8"))
            actual_color = payload["attachments"][0]["content"]["body"][0]["style"]
            assert actual_color == expected_color, f"Color mismatch for level {level}"


# ============================================================
# FeishuNotificationChannel
# ============================================================


class TestFeishuNotificationChannel:
    """Tests for FeishuNotificationChannel"""

    def test_init_with_params(self):
        """Test initialization with parameters"""
        channel = FeishuNotificationChannel(webhook_url="https://open.feishu.cn/test")
        assert channel.webhook_url == "https://open.feishu.cn/test"

    @patch.dict(os.environ, {"FEISHU_WEBHOOK": "https://open.feishu.cn/env"})
    def test_init_from_env(self):
        """Test initialization from environment variables"""
        channel = FeishuNotificationChannel()
        assert channel.webhook_url == "https://open.feishu.cn/env"

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        """Test successful send (code == 0)"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"code": 0}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = FeishuNotificationChannel(webhook_url="https://open.feishu.cn/test")
        result = channel.send("Test Title", "Test Body")
        assert result is True

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_failure(self, mock_urlopen):
        """Test failed send (code != 0)"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"code": 1}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = FeishuNotificationChannel(webhook_url="https://open.feishu.cn/test")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_exception(self, mock_urlopen):
        """Test exception during send"""
        mock_urlopen.side_effect = Exception("Test exception")
        channel = FeishuNotificationChannel(webhook_url="https://open.feishu.cn/test")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_send_no_webhook_url(self):
        """Test send without webhook URL"""
        channel = FeishuNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_name_attribute(self):
        """Test channel name"""
        channel = FeishuNotificationChannel()
        assert channel.name == "feishu"


# ============================================================
# WeComNotificationChannel
# ============================================================


class TestWeComNotificationChannel:
    """Tests for WeComNotificationChannel"""

    def test_init_with_params(self):
        """Test initialization with parameters"""
        channel = WeComNotificationChannel(webhook_url="https://qyapi.weixin.qq.com/test")
        assert channel.webhook_url == "https://qyapi.weixin.qq.com/test"

    @patch.dict(os.environ, {"WECOM_WEBHOOK": "https://qyapi.weixin.qq.com/env"})
    def test_init_from_env(self):
        """Test initialization from environment variables"""
        channel = WeComNotificationChannel()
        assert channel.webhook_url == "https://qyapi.weixin.qq.com/env"

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        """Test successful send (errcode == 0)"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"errcode": 0}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = WeComNotificationChannel(webhook_url="https://qyapi.weixin.qq.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is True

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_failure(self, mock_urlopen):
        """Test failed send (errcode != 0)"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"errcode": 1}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = WeComNotificationChannel(webhook_url="https://qyapi.weixin.qq.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_exception(self, mock_urlopen):
        """Test exception during send"""
        mock_urlopen.side_effect = Exception("Test exception")
        channel = WeComNotificationChannel(webhook_url="https://qyapi.weixin.qq.com/test")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_send_no_webhook_url(self):
        """Test send without webhook URL"""
        channel = WeComNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_name_attribute(self):
        """Test channel name"""
        channel = WeComNotificationChannel()
        assert channel.name == "wecom"


# ============================================================
# PushPlusNotificationChannel
# ============================================================


class TestPushPlusNotificationChannel:
    """Tests for PushPlusNotificationChannel"""

    def test_init_with_params(self):
        """Test initialization with parameters"""
        channel = PushPlusNotificationChannel(token="test_token")
        assert channel.token == "test_token"

    @patch.dict(os.environ, {"PUSHPLUS_TOKEN": "env_token"})
    def test_init_from_env(self):
        """Test initialization from environment variables"""
        channel = PushPlusNotificationChannel()
        assert channel.token == "env_token"

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        """Test successful send (code == 200)"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"code": 200}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = PushPlusNotificationChannel(token="test_token")
        result = channel.send("Test Title", "Test Body")
        assert result is True

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_failure(self, mock_urlopen):
        """Test failed send (code != 200)"""
        mock_cm, _ = _make_urlopen_mock(json.dumps({"code": 400}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        channel = PushPlusNotificationChannel(token="test_token")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_send_exception(self, mock_urlopen):
        """Test exception during send"""
        mock_urlopen.side_effect = Exception("Test exception")
        channel = PushPlusNotificationChannel(token="test_token")
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_send_no_token(self):
        """Test send without token"""
        channel = PushPlusNotificationChannel()
        result = channel.send("Test Title", "Test Body")
        assert result is False

    def test_name_attribute(self):
        """Test channel name"""
        channel = PushPlusNotificationChannel()
        assert channel.name == "pushplus"


# ============================================================
# ConsoleNotificationChannel
# ============================================================


class TestConsoleNotificationChannel:
    """Tests for ConsoleNotificationChannel"""

    def test_init_with_callback(self):
        """Test initialization with callback"""
        callback = MagicMock()
        channel = ConsoleNotificationChannel(callback=callback)
        assert channel.callback == callback

    def test_init_without_callback(self):
        """Test initialization without callback"""
        channel = ConsoleNotificationChannel()
        assert channel.callback is None

    def test_send_with_callback(self):
        """Test send with callback"""
        callback = MagicMock()
        channel = ConsoleNotificationChannel(callback=callback)
        result = channel.send("Test Title", "Test Body", level="info")
        assert result is True
        callback.assert_called_once_with("Test Title", "Test Body", "info")

    def test_send_without_callback(self):
        """Test send without callback"""
        channel = ConsoleNotificationChannel()
        result = channel.send("Test Title", "Test Body", level="info")
        assert result is True

    def test_name_attribute(self):
        """Test channel name"""
        channel = ConsoleNotificationChannel()
        assert channel.name == "console"

    def test_send_different_levels(self):
        """Test send with different levels"""
        callback = MagicMock()
        channel = ConsoleNotificationChannel(callback=callback)
        for level in ["info", "success", "warning", "error"]:
            result = channel.send("Title", "Body", level=level)
            assert result is True
            callback.assert_called_with("Title", "Body", level)


# ============================================================
# NotificationConfig
# ============================================================


class TestNotificationConfig:
    """Tests for NotificationConfig dataclass"""

    def test_default_values(self):
        """Test default values"""
        config = NotificationConfig()
        assert config.desktop is True
        assert config.dingtalk_webhook is None
        assert config.dingtalk_secret is None
        assert config.telegram_bot_token is None
        assert config.telegram_chat_id is None
        assert config.discord_webhook is None
        assert config.slack_webhook is None
        assert config.teams_webhook is None
        assert config.feishu_webhook is None
        assert config.wecom_webhook is None
        assert config.pushplus_token is None
        assert config.console_callback is None

    def test_custom_values(self):
        """Test custom values"""
        callback = MagicMock()
        config = NotificationConfig(
            desktop=False,
            dingtalk_webhook="https://oapi.dingtalk.com/test",
            dingtalk_secret="secret",
            telegram_bot_token="token",
            telegram_chat_id="chat_id",
            discord_webhook="https://discord.com/test",
            slack_webhook="https://hooks.slack.com/test",
            teams_webhook="https://outlook.office.com/test",
            feishu_webhook="https://open.feishu.cn/test",
            wecom_webhook="https://qyapi.weixin.qq.com/test",
            pushplus_token="token",
            console_callback=callback,
        )
        assert config.desktop is False
        assert config.dingtalk_webhook == "https://oapi.dingtalk.com/test"
        assert config.dingtalk_secret == "secret"
        assert config.console_callback == callback

    def test_dataclass_fields(self):
        """Test that NotificationConfig is a dataclass"""
        import dataclasses

        assert dataclasses.is_dataclass(NotificationConfig)


# ============================================================
# NotificationManager
# ============================================================


class TestNotificationManager:
    """Tests for NotificationManager"""

    def test_init_with_desktop_macos(self):
        """Test initialization with desktop=True on macOS"""
        with patch("src.quest.notifications.sys.platform", "darwin"):
            config = NotificationConfig(desktop=True)
            manager = NotificationManager(config)
            assert len(manager._channels) >= 1
            assert any(isinstance(ch, MacOSNotificationChannel) for ch in manager._channels)

    def test_init_with_desktop_windows(self):
        """Test initialization with desktop=True on Windows"""
        with patch("src.quest.notifications.sys.platform", "win32"):
            config = NotificationConfig(desktop=True)
            manager = NotificationManager(config)
            assert len(manager._channels) >= 1
            assert any(isinstance(ch, WindowsNotificationChannel) for ch in manager._channels)

    def test_init_without_desktop(self):
        """Test initialization with desktop=False"""
        config = NotificationConfig(desktop=False)
        manager = NotificationManager(config)
        # Should not have desktop channels
        assert not any(
            isinstance(ch, (MacOSNotificationChannel, WindowsNotificationChannel))
            for ch in manager._channels
        )

    def test_init_with_dingtalk(self):
        """Test initialization with DingTalk webhook"""
        config = NotificationConfig(
            desktop=False,
            dingtalk_webhook="https://oapi.dingtalk.com/test",
            dingtalk_secret="secret",
        )
        manager = NotificationManager(config)
        assert any(isinstance(ch, DingTalkNotificationChannel) for ch in manager._channels)

    def test_init_with_telegram(self):
        """Test initialization with Telegram credentials"""
        config = NotificationConfig(
            desktop=False,
            telegram_bot_token="token",
            telegram_chat_id="chat_id",
        )
        manager = NotificationManager(config)
        assert any(isinstance(ch, TelegramNotificationChannel) for ch in manager._channels)

    def test_init_with_discord(self):
        """Test initialization with Discord webhook"""
        config = NotificationConfig(
            desktop=False,
            discord_webhook="https://discord.com/test",
        )
        manager = NotificationManager(config)
        assert any(isinstance(ch, DiscordNotificationChannel) for ch in manager._channels)

    def test_init_with_slack(self):
        """Test initialization with Slack webhook"""
        config = NotificationConfig(
            desktop=False,
            slack_webhook="https://hooks.slack.com/test",
        )
        manager = NotificationManager(config)
        assert any(isinstance(ch, SlackNotificationChannel) for ch in manager._channels)

    def test_init_with_teams(self):
        """Test initialization with Teams webhook"""
        config = NotificationConfig(
            desktop=False,
            teams_webhook="https://outlook.office.com/test",
        )
        manager = NotificationManager(config)
        assert any(isinstance(ch, TeamsNotificationChannel) for ch in manager._channels)

    def test_init_with_feishu(self):
        """Test initialization with Feishu webhook"""
        config = NotificationConfig(
            desktop=False,
            feishu_webhook="https://open.feishu.cn/test",
        )
        manager = NotificationManager(config)
        assert any(isinstance(ch, FeishuNotificationChannel) for ch in manager._channels)

    def test_init_with_wecom(self):
        """Test initialization with WeCom webhook"""
        config = NotificationConfig(
            desktop=False,
            wecom_webhook="https://qyapi.weixin.qq.com/test",
        )
        manager = NotificationManager(config)
        assert any(isinstance(ch, WeComNotificationChannel) for ch in manager._channels)

    def test_init_with_pushplus(self):
        """Test initialization with PushPlus token"""
        config = NotificationConfig(
            desktop=False,
            pushplus_token="token",
        )
        manager = NotificationManager(config)
        assert any(isinstance(ch, PushPlusNotificationChannel) for ch in manager._channels)

    def test_init_with_console_callback(self):
        """Test initialization with console callback"""
        callback = MagicMock()
        config = NotificationConfig(
            desktop=False,
            console_callback=callback,
        )
        manager = NotificationManager(config)
        assert any(isinstance(ch, ConsoleNotificationChannel) for ch in manager._channels)

    def test_init_no_channels_add_console(self):
        """Test that console channel is added when no other channels"""
        config = NotificationConfig(desktop=False)
        manager = NotificationManager(config)
        assert len(manager._channels) == 1
        assert isinstance(manager._channels[0], ConsoleNotificationChannel)

    def test_level_from_event(self):
        """Test _level_from_event method"""
        manager = NotificationManager(NotificationConfig(desktop=False))
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
        for event, expected_level in level_map.items():
            actual_level = manager._level_from_event(event)
            assert actual_level == expected_level, f"Level mismatch for event {event}"

    def test_level_from_event_default(self):
        """Test _level_from_event with unknown event"""
        manager = NotificationManager(NotificationConfig(desktop=False))
        assert manager._level_from_event("unknown_event") == "info"

    @patch.object(MacOSNotificationChannel, "send", return_value=True)
    def test_send_calls_all_channels(self, mock_send):
        """Test that send calls all channels"""
        with patch("src.quest.notifications.sys.platform", "darwin"):
            config = NotificationConfig(desktop=True)
            manager = NotificationManager(config)
            manager.send("Test Title", "Test Body")
            assert mock_send.call_count >= 1

    def test_send_with_event(self):
        """Test send with event parameter"""
        callback = MagicMock()
        config = NotificationConfig(desktop=False, console_callback=callback)
        manager = NotificationManager(config)
        manager.send("Test Title", "Test Body", event="completed", quest_id="test_123")
        callback.assert_called_once()

    def test_send_without_event(self):
        """Test send without event parameter (uses 'info')"""
        callback = MagicMock()
        config = NotificationConfig(desktop=False, console_callback=callback)
        manager = NotificationManager(config)
        manager.send("Test Title", "Test Body")
        callback.assert_called_once()

    # Convenience methods tests

    @patch.object(NotificationManager, "send")
    def test_notify_started(self, mock_send):
        """Test notify_started convenience method"""
        manager = NotificationManager(NotificationConfig(desktop=False))
        manager.notify_started("Test Quest", "quest_123")
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args.args[0] == "🧙 Quest 已启动"
        assert call_args.args[1] == "Test Quest"
        assert call_args.args[2] == "started"

    @patch.object(NotificationManager, "send")
    def test_notify_spec_ready(self, mock_send):
        """Test notify_spec_ready convenience method"""
        manager = NotificationManager(NotificationConfig(desktop=False))
        manager.notify_spec_ready("Test Quest", "quest_123")
        mock_send.assert_called_once()

    @patch.object(NotificationManager, "send")
    def test_notify_step_completed(self, mock_send):
        """Test notify_step_completed convenience method"""
        manager = NotificationManager(NotificationConfig(desktop=False))
        manager.notify_step_completed("Test Step", "quest_123")
        mock_send.assert_called_once()

    @patch.object(NotificationManager, "send")
    def test_notify_step_failed(self, mock_send):
        """Test notify_step_failed convenience method"""
        manager = NotificationManager(NotificationConfig(desktop=False))
        manager.notify_step_failed("Test Step", "Error message", "quest_123")
        mock_send.assert_called_once()

    @patch.object(NotificationManager, "send")
    def test_notify_completed(self, mock_send):
        """Test notify_completed convenience method"""
        manager = NotificationManager(NotificationConfig(desktop=False))
        manager.notify_completed("Test Quest", "Summary", "quest_123")
        mock_send.assert_called_once()

    @patch.object(NotificationManager, "send")
    def test_notify_failed(self, mock_send):
        """Test notify_failed convenience method"""
        manager = NotificationManager(NotificationConfig(desktop=False))
        manager.notify_failed("Test Quest", "Error", "quest_123")
        mock_send.assert_called_once()

    @patch.object(NotificationManager, "send")
    def test_notify_waiting_input(self, mock_send):
        """Test notify_waiting_input convenience method"""
        manager = NotificationManager(NotificationConfig(desktop=False))
        manager.notify_waiting_input("Test Quest", "Input message", "quest_123")
        mock_send.assert_called_once()

    @patch.object(NotificationManager, "send")
    def test_notify_paused(self, mock_send):
        """Test notify_paused convenience method"""
        manager = NotificationManager(NotificationConfig(desktop=False))
        manager.notify_paused("Test Quest", "quest_123")
        mock_send.assert_called_once()

    @patch.object(NotificationManager, "send")
    def test_notify_resumed(self, mock_send):
        """Test notify_resumed convenience method"""
        manager = NotificationManager(NotificationConfig(desktop=False))
        manager.notify_resumed("Test Quest", "quest_123")
        mock_send.assert_called_once()

    def test_send_exception_handling(self):
        """Test that exceptions in one channel don't affect others"""
        failing_channel = MagicMock()
        failing_channel.name = "failing"
        failing_channel.send.side_effect = Exception("Channel failed")

        success_channel = MagicMock()
        success_channel.name = "success"
        success_channel.send.return_value = True

        manager = NotificationManager(NotificationConfig(desktop=False))
        manager._channels = [failing_channel, success_channel]

        # Should not raise exception
        manager.send("Title", "Body")

        # Both channels should have been called
        failing_channel.send.assert_called_once()
        success_channel.send.assert_called_once()


# ============================================================
# create_notification_manager (Compatibility Function)
# ============================================================


class TestCreateNotificationManager:
    """Tests for create_notification_manager compatibility function"""

    def test_create_with_defaults(self):
        """Test creation with default parameters"""
        manager = create_notification_manager()
        assert isinstance(manager, NotificationManager)
        assert manager.config.desktop is True

    def test_create_with_desktop_false(self):
        """Test creation with desktop=False"""
        manager = create_notification_manager(desktop=False)
        assert manager.config.desktop is False

    def test_create_with_dingtalk(self):
        """Test creation with DingTalk parameters"""
        manager = create_notification_manager(
            dingtalk_webhook="https://oapi.dingtalk.com/test",
            dingtalk_secret="secret",
        )
        assert manager.config.dingtalk_webhook == "https://oapi.dingtalk.com/test"
        assert manager.config.dingtalk_secret == "secret"
        assert any(isinstance(ch, DingTalkNotificationChannel) for ch in manager._channels)

    def test_return_type(self):
        """Test that function returns NotificationManager instance"""
        manager = create_notification_manager()
        assert isinstance(manager, NotificationManager)


# ============================================================
# Integration Tests
# ============================================================


class TestIntegration:
    """Integration tests for notification system"""

    @patch("src.quest.notifications.sys.platform", "darwin")
    @patch("src.quest.notifications.subprocess.run")
    @patch("src.quest.notifications.urllib.request.urlopen")
    def test_multiple_channels_integration(self, mock_urlopen, mock_run):
        """Test that multiple channels work together"""
        # Mock macOS notification success
        mock_run.return_value = MagicMock(returncode=0)

        # Mock HTTP responses
        mock_cm, _ = _make_urlopen_mock(json.dumps({"errcode": 0}).encode("utf-8"))
        mock_urlopen.return_value = mock_cm

        config = NotificationConfig(
            desktop=True,
            dingtalk_webhook="https://oapi.dingtalk.com/test",
            discord_webhook="https://discord.com/test",
        )
        manager = NotificationManager(config)

        # Should have at least 2 channels (macOS + DingTalk + Discord)
        assert len(manager._channels) >= 2

        # Send notification
        manager.send("Integration Test", "Testing multiple channels")

        # All channels should have been called
        assert mock_run.call_count >= 1
        assert mock_urlopen.call_count >= 1

    def test_console_callback_integration(self):
        """Test console callback integration"""
        callback = MagicMock()
        config = NotificationConfig(desktop=False, console_callback=callback)
        manager = NotificationManager(config)

        manager.notify_started("Test Quest", "quest_123")
        callback.assert_called_once_with("🧙 Quest 已启动", "Test Quest", "info")
