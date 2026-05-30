"""Simplified comprehensive tests for gateway platform handlers

This version uses simpler mocking strategies to avoid complex async context manager issues.
"""

import time
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.gateway.base import (
    IncomingMessage,
    OutgoingMessage,
    Platform,
    PlatformHandler,
)


@pytest.fixture
def mock_on_message():
    """Mock callback for on_message"""
    return MagicMock()


@pytest.fixture
def mock_on_error():
    """Mock callback for on_error"""
    return MagicMock()


# ---- Base Class Tests ----


class TestBaseClasses:
    """Test base classes and dataclasses"""

    def test_incoming_message_creation(self):
        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="12345",
            chat_id="12345",
            text="hello",
            raw={"msg_id": "123"},
            reply_to="msg_123",
        )
        assert msg.platform == Platform.TELEGRAM
        assert msg.user_id == "12345"
        assert msg.text == "hello"
        assert msg.reply_to == "msg_123"

    def test_outgoing_message_creation(self):
        msg = OutgoingMessage(
            platform=Platform.DISCORD,
            chat_id="12345",
            text="hello",
            parse_mode="markdown",
            reply_to="msg_123",
            extra={"tts": True},
        )
        assert msg.platform == Platform.DISCORD
        assert msg.parse_mode == "markdown"
        assert msg.extra == {"tts": True}

    def test_platform_enum(self):
        assert Platform.TELEGRAM.value == "telegram"
        assert Platform.DISCORD.value == "discord"
        assert Platform.WHATSAPP.value == "whatsapp"
        assert Platform.SLACK.value == "slack"
        assert Platform.WECOM.value == "wecom"
        assert Platform.DINGTALK.value == "dingtalk"
        assert Platform.FEISHU.value == "feishu"

    def test_platform_handler_is_abstract(self):
        """Test that PlatformHandler cannot be instantiated"""
        with pytest.raises(TypeError):
            PlatformHandler(on_message=lambda m: None)  # noqa: E731


# ---- NoopHandler Tests ----


class TestNoopHandler:
    """Test NoopHandler"""

    def test_noop_handler_telegram(self, mock_on_message):
        from src.gateway.base import NoopHandler, Platform

        handler = NoopHandler(Platform.TELEGRAM, on_message=mock_on_message)
        assert handler.name == Platform.TELEGRAM
        assert not handler.is_started

    @pytest.mark.asyncio
    async def test_noop_start(self, mock_on_message):
        from src.gateway.base import NoopHandler, Platform

        handler = NoopHandler(Platform.DISCORD, on_message=mock_on_message)
        await handler.start()
        assert not handler.is_started  # Noop doesn't set _started

    @pytest.mark.asyncio
    async def test_noop_stop(self, mock_on_message):
        from src.gateway.base import NoopHandler, Platform

        handler = NoopHandler(Platform.SLACK, on_message=mock_on_message)
        await handler.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_noop_send(self, mock_on_message):
        from src.gateway.base import NoopHandler, Platform

        handler = NoopHandler(Platform.WHATSAPP, on_message=mock_on_message)
        msg = OutgoingMessage(
            platform=Platform.WHATSAPP,
            chat_id="12345",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is True


# ---- Telegram Handler Tests ----


class TestTelegramHandler:
    """Test TelegramHandler"""

    @pytest.fixture
    def handler(self, mock_on_message):
        from src.gateway.platforms.telegram import TelegramHandler

        with patch("src.gateway.platforms.telegram._HAS_TELEGRAM", True):
            handler = TelegramHandler(
                bot_token="mock_token",
                allowed_user_ids=["12345"],
                on_message=mock_on_message,
            )
            return handler

    def test_init(self, handler):
        assert handler.name == Platform.TELEGRAM
        assert handler.bot_token == "mock_token"
        assert "12345" in handler.allowed_user_ids
        assert not handler.is_started

    def test_check_dependencies(self):
        from src.gateway.platforms.telegram import check_telegram_dependencies

        with patch("src.gateway.platforms.telegram._HAS_TELEGRAM", True):
            assert check_telegram_dependencies() is True

        with patch("src.gateway.platforms.telegram._HAS_TELEGRAM", False):
            assert check_telegram_dependencies() is False

    @pytest.mark.asyncio
    async def test_start_no_telegram_lib(self, mock_on_message):
        """Test start fails when telegram lib not installed"""
        with patch("src.gateway.platforms.telegram._HAS_TELEGRAM", False):
            from src.gateway.platforms.telegram import TelegramHandler

            handler = TelegramHandler(
                bot_token="mock", on_message=mock_on_message
            )
            with pytest.raises(RuntimeError, match="python-telegram-bot 未安装"):
                await handler.start()

    @pytest.mark.asyncio
    async def test_send_not_started(self, handler):
        """Test send returns False when not started"""
        msg = OutgoingMessage(
            platform=Platform.TELEGRAM,
            chat_id="12345",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_success(self, handler):
        """Test successful send"""
        handler._started = True
        handler._app = MagicMock()
        handler._app.bot = MagicMock()
        handler._app.bot.send_message = AsyncMock(return_value=True)

        msg = OutgoingMessage(
            platform=Platform.TELEGRAM,
            chat_id="12345",
            text="hello",
            parse_mode="markdown",
            reply_to="msg_123",
        )
        result = await handler.send(msg)
        assert result is True
        handler._app.bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_without_parse_mode(self, handler):
        """Test send without parse_mode sends None"""
        handler._started = True
        handler._app = MagicMock()
        handler._app.bot = MagicMock()
        handler._app.bot.send_message = AsyncMock(return_value=True)

        msg = OutgoingMessage(
            platform=Platform.TELEGRAM,
            chat_id="12345",
            text="hello",
            parse_mode="",
        )
        result = await handler.send(msg)
        assert result is True
        call_args = handler._app.bot.send_message.call_args
        assert call_args[1]["parse_mode"] is None

    @pytest.mark.asyncio
    async def test_send_failure(self, handler, mock_on_error):
        """Test send handles exceptions"""
        handler._started = True
        handler._app = MagicMock()
        handler._app.bot = MagicMock()
        handler._app.bot.send_message = AsyncMock(
            side_effect=Exception("Send failed")
        )
        handler.on_error = mock_on_error

        msg = OutgoingMessage(
            platform=Platform.TELEGRAM,
            chat_id="12345",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is False
        mock_on_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, handler):
        """Test stop sets _started to False"""
        handler._started = True
        handler._app = MagicMock()
        handler._app.stop = AsyncMock()

        await handler.stop()
        assert handler._started is False


# ---- Discord Handler Tests ----


class TestDiscordHandler:
    """Test DiscordHandler"""

    @pytest.fixture
    def handler(self, mock_on_message):
        from src.gateway.platforms.discord import DiscordHandler

        with patch("src.gateway.platforms.discord._HAS_DISCORD", True):
            handler = DiscordHandler(
                bot_token="mock_token",
                allowed_guild_ids=[12345],
                on_message=mock_on_message,
            )
            return handler

    def test_init(self, handler):
        assert handler.name == Platform.DISCORD
        assert handler.bot_token == "mock_token"
        assert 12345 in handler.allowed_guild_ids
        assert not handler.is_started

    def test_check_dependencies(self):
        from src.gateway.platforms.discord import check_discord_dependencies

        with patch("src.gateway.platforms.discord._HAS_DISCORD", True):
            assert check_discord_dependencies() is True

        with patch("src.gateway.platforms.discord._HAS_DISCORD", False):
            assert check_discord_dependencies() is False

    @pytest.mark.asyncio
    async def test_start_no_discord_lib(self, mock_on_message):
        """Test start fails when discord.py not installed"""
        with patch("src.gateway.platforms.discord._HAS_DISCORD", False):
            from src.gateway.platforms.discord import DiscordHandler

            handler = DiscordHandler(
                bot_token="mock", on_message=mock_on_message
            )
            with pytest.raises(RuntimeError, match="discord.py 未安装"):
                await handler.start()

    @pytest.mark.asyncio
    async def test_send_not_started(self, handler):
        """Test send returns False when not started"""
        msg = OutgoingMessage(
            platform=Platform.DISCORD,
            chat_id="12345",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_channel_not_found(self, handler):
        """Test send returns False when channel not found"""
        handler._started = True
        handler._bot = MagicMock()
        handler._bot.get_channel = MagicMock(return_value=None)

        msg = OutgoingMessage(
            platform=Platform.DISCORD,
            chat_id="12345",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_success(self, handler):
        """Test successful send"""
        handler._started = True
        mock_channel = MagicMock()
        mock_channel.send = AsyncMock()
        handler._bot = MagicMock()
        handler._bot.get_channel = MagicMock(return_value=mock_channel)

        msg = OutgoingMessage(
            platform=Platform.DISCORD,
            chat_id="12345",
            text="hello",
            reply_to="msg_123",
        )
        result = await handler.send(msg)
        assert result is True
        mock_channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_without_reply(self, handler):
        """Test send without reply_to"""
        handler._started = True
        mock_channel = MagicMock()
        mock_channel.send = AsyncMock()
        handler._bot = MagicMock()
        handler._bot.get_channel = MagicMock(return_value=mock_channel)

        msg = OutgoingMessage(
            platform=Platform.DISCORD,
            chat_id="12345",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_failure(self, handler, mock_on_error):
        """Test send handles exceptions"""
        handler._started = True
        mock_channel = MagicMock()
        mock_channel.send = AsyncMock(side_effect=Exception("Send failed"))
        handler._bot = MagicMock()
        handler._bot.get_channel = MagicMock(return_value=mock_channel)
        handler.on_error = mock_on_error

        msg = OutgoingMessage(
            platform=Platform.DISCORD,
            chat_id="12345",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is False
        mock_on_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, handler):
        """Test stop"""
        handler._started = True
        handler._bot = MagicMock()
        handler._bot.close = AsyncMock()

        await handler.stop()
        assert handler._started is False
        handler._bot.close.assert_called_once()


# ---- WhatsApp Handler Tests ----


class TestWhatsAppHandler:
    """Test WhatsAppHandler"""

    @pytest.fixture
    def handler(self, mock_on_message):
        from src.gateway.platforms.whatsapp import WhatsAppHandler

        with patch("src.gateway.platforms.whatsapp._HAS_HTTPX", True), patch(
            "src.gateway.platforms.whatsapp._HAS_STARLETTE", True
        ):
            handler = WhatsAppHandler(
                phone_number_id="123456789",
                access_token="mock_token",
                webhook_url="https://example.com",
                verify_token="test_verify",
                on_message=mock_on_message,
            )
            return handler

    def test_init(self, handler):
        assert handler.name == Platform.WHATSAPP
        assert handler.phone_number_id == "123456789"
        assert handler.verify_token == "test_verify"
        assert not handler.is_started

    def test_check_dependencies(self):
        from src.gateway.platforms.whatsapp import check_whatsapp_dependencies

        with patch("src.gateway.platforms.whatsapp._HAS_HTTPX", True), patch(
            "src.gateway.platforms.whatsapp._HAS_STARLETTE", True
        ):
            assert check_whatsapp_dependencies() is True

        with patch("src.gateway.platforms.whatsapp._HAS_HTTPX", False):
            assert check_whatsapp_dependencies() is False

    @pytest.mark.asyncio
    async def test_start_no_dependencies(self, mock_on_message):
        """Test start fails when dependencies missing"""
        with patch("src.gateway.platforms.whatsapp._HAS_STARLETTE", False):
            from src.gateway.platforms.whatsapp import WhatsAppHandler

            handler = WhatsAppHandler(
                phone_number_id="123",
                access_token="mock",
                webhook_url="https://example.com",
                on_message=mock_on_message,
            )
            with pytest.raises(RuntimeError, match="starlette 未安装"):
                await handler.start()

    @pytest.mark.asyncio
    async def test_send_no_httpx(self, mock_on_message):
        """Test send returns False when httpx not installed"""
        with patch("src.gateway.platforms.whatsapp._HAS_HTTPX", False):
            from src.gateway.platforms.whatsapp import WhatsAppHandler

            handler = WhatsAppHandler(
                phone_number_id="123",
                access_token="mock",
                webhook_url="https://example.com",
                on_message=mock_on_message,
            )
            msg = OutgoingMessage(
                platform=Platform.WHATSAPP,
                chat_id="12345",
                text="hello",
            )
            result = await handler.send(msg)
            assert result is False

    @pytest.mark.asyncio
    async def test_process_message(self, handler, mock_on_message):
        """Test _process_message creates IncomingMessage"""
        msg_data = {
            "type": "text",
            "text": {"body": "hello whatsapp"},
            "id": "msg_123",
            "from": "1234567890",
            "timestamp": "1234567890",
        }
        value = {
            "metadata": {"phone_number_id": "123456789"},
            "contacts": [{"profile": {"name": "Test User"}}],
        }

        handler.on_message = mock_on_message
        await handler._process_message(msg_data, value)

        assert mock_on_message.called
        call_args = mock_on_message.call_args[0][0]
        assert isinstance(call_args, IncomingMessage)
        assert call_args.platform == Platform.WHATSAPP
        assert call_args.text == "hello whatsapp"
        assert call_args.user_id == "1234567890"

    @pytest.mark.asyncio
    async def test_process_non_text_message(self, handler, mock_on_message):
        """Test _process_message ignores non-text messages"""
        msg_data = {
            "type": "image",
            "id": "msg_123",
            "from": "1234567890",
        }
        value = {"metadata": {"phone_number_id": "123456789"}}

        handler.on_message = mock_on_message
        await handler._process_message(msg_data, value)

        assert not mock_on_message.called


# ---- WeCom Handler Tests ----


class TestWeComHandler:
    """Test WeComHandler"""

    @pytest.fixture
    def handler(self, mock_on_message):
        from src.gateway.platforms.wecom import WeComHandler

        with patch("src.gateway.platforms.wecom._HAS_HTTPX", True):
            handler = WeComHandler(
                corp_id="ww123456789",
                agent_id="1000001",
                corp_secret="mock_secret",
                on_message=mock_on_message,
            )
            return handler

    def test_init(self, handler):
        assert handler.name == Platform.WECOM
        assert handler.corp_id == "ww123456789"
        assert handler.agent_id == "1000001"
        assert not handler.is_started

    def test_check_dependencies(self):
        from src.gateway.platforms.wecom import check_wecom_dependencies

        with patch("src.gateway.platforms.wecom._HAS_HTTPX", True):
            assert check_wecom_dependencies() is True

        with patch("src.gateway.platforms.wecom._HAS_HTTPX", False):
            assert check_wecom_dependencies() is False

    @pytest.mark.asyncio
    async def test_send_no_httpx(self, mock_on_message):
        """Test send returns False when httpx not installed"""
        with patch("src.gateway.platforms.wecom._HAS_HTTPX", False):
            from src.gateway.platforms.wecom import WeComHandler

            handler = WeComHandler(
                corp_id="ww123",
                agent_id="100",
                corp_secret="mock",
                on_message=mock_on_message,
            )
            msg = OutgoingMessage(
                platform=Platform.WECOM,
                chat_id="user1",
                text="hello",
            )
            result = await handler.send(msg)
            assert result is False

    @pytest.mark.asyncio
    async def test_process_message(self, handler, mock_on_message):
        """Test _process_message creates IncomingMessage"""
        msg_data = {
            "MsgType": "text",
            "Content": "hello wecom",
            "FromUserName": "user1",
            "ToUserName": "ww123",
            "MsgId": "msg_123",
        }

        handler.on_message = mock_on_message
        await handler._process_message(msg_data)

        assert mock_on_message.called
        call_args = mock_on_message.call_args[0][0]
        assert isinstance(call_args, IncomingMessage)
        assert call_args.platform == Platform.WECOM
        assert call_args.text == "hello wecom"

    @pytest.mark.asyncio
    async def test_process_non_text_message(self, handler, mock_on_message):
        """Test _process_message ignores non-text"""
        msg_data = {
            "MsgType": "image",
            "FromUserName": "user1",
        }

        handler.on_message = mock_on_message
        await handler._process_message(msg_data)

        assert not mock_on_message.called


# ---- DingTalk Handler Tests ----


class TestDingTalkHandler:
    """Test DingTalkHandler"""

    @pytest.fixture
    def handler(self, mock_on_message):
        from src.gateway.platforms.dingtalk import DingTalkHandler

        with patch("src.gateway.platforms.dingtalk._HAS_HTTPX", True):
            handler = DingTalkHandler(
                app_key="ding1234567890",
                app_secret="mock_secret",
                on_message=mock_on_message,
            )
            return handler

    def test_init(self, handler):
        assert handler.name == Platform.DINGTALK
        assert handler.app_key == "ding1234567890"
        assert not handler.is_started

    def test_check_dependencies(self):
        from src.gateway.platforms.dingtalk import check_dingtalk_dependencies

        with patch("src.gateway.platforms.dingtalk._HAS_HTTPX", True):
            assert check_dingtalk_dependencies() is True

        with patch("src.gateway.platforms.dingtalk._HAS_HTTPX", False):
            assert check_dingtalk_dependencies() is False

    @pytest.mark.asyncio
    async def test_handle_callback(self, handler, mock_on_message):
        """Test _handle_callback processes message"""
        import json

        body = json.dumps({
            "msgtype": "text",
            "text": {"content": "hello dingtalk"},
            "senderStaffId": "user1",
            "conversationId": "cid1",
            "msgId": "msg_123",
        })

        handler.on_message = mock_on_message
        await handler._handle_callback(body)

        assert mock_on_message.called
        call_args = mock_on_message.call_args[0][0]
        assert isinstance(call_args, IncomingMessage)
        assert call_args.platform == Platform.DINGTALK
        assert call_args.text == "hello dingtalk"

    @pytest.mark.asyncio
    async def test_handle_callback_non_text(self, handler, mock_on_message):
        """Test _handle_callback ignores non-text"""
        import json

        body = json.dumps({
            "msgtype": "image",
            "senderStaffId": "user1",
        })

        handler.on_message = mock_on_message
        await handler._handle_callback(body)

        assert not mock_on_message.called


# ---- Feishu Handler Tests ----


class TestFeishuHandler:
    """Test FeishuHandler"""

    @pytest.fixture
    def handler(self, mock_on_message):
        from src.gateway.platforms.feishu import FeishuHandler

        with patch("src.gateway.platforms.feishu._HAS_HTTPX", True):
            handler = FeishuHandler(
                app_id="cli_abc123",
                app_secret="mock_secret",
                on_message=mock_on_message,
            )
            return handler

    def test_init(self, handler):
        assert handler.name == Platform.FEISHU
        assert handler.app_id == "cli_abc123"
        assert not handler.is_started

    def test_check_dependencies(self):
        from src.gateway.platforms.feishu import check_feishu_dependencies

        with patch("src.gateway.platforms.feishu._HAS_HTTPX", True):
            assert check_feishu_dependencies() is True

        with patch("src.gateway.platforms.feishu._HAS_HTTPX", False):
            assert check_feishu_dependencies() is False

    @pytest.mark.asyncio
    async def test_process_message(self, handler, mock_on_message):
        """Test _process_message creates IncomingMessage"""
        import json

        msg_data = {
            "msg_type": "text",
            "body": {"content": json.dumps({"text": "hello feishu"})},
            "sender": {"id": "ou_abc123"},
            "chat_id": "oc_abc123",
            "message_id": "msg_123",
            "chat_type": "p2p",
            "create_time": "1234567890",
        }

        handler.on_message = mock_on_message
        await handler._process_message(msg_data)

        assert mock_on_message.called
        call_args = mock_on_message.call_args[0][0]
        assert isinstance(call_args, IncomingMessage)
        assert call_args.platform == Platform.FEISHU
        assert call_args.text == "hello feishu"

    @pytest.mark.asyncio
    async def test_process_non_p2p_message(self, handler, mock_on_message):
        """Test _process_message ignores non-p2p messages"""
        msg_data = {
            "msg_type": "text",
            "body": {"content": '{"text": "hello"}'},
            "chat_type": "group",
        }

        handler.on_message = mock_on_message
        await handler._process_message(msg_data)

        assert not mock_on_message.called

    @pytest.mark.asyncio
    async def test_process_non_text_message(self, handler, mock_on_message):
        """Test _process_message ignores non-text messages"""
        msg_data = {
            "msg_type": "image",
            "chat_type": "p2p",
        }

        handler.on_message = mock_on_message
        await handler._process_message(msg_data)

        assert not mock_on_message.called

    def test_build_content(self):
        """Test _build_content"""
        from src.gateway.platforms.feishu import FeishuHandler

        result = FeishuHandler._build_content("hello", "markdown")
        import json

        assert json.loads(result) == {"text": "hello"}


# ---- Slack Handler Tests ----


class TestSlackHandler:
    """Test SlackHandler"""

    @pytest.fixture
    def handler(self, mock_on_message):
        from src.gateway.platforms.slack import SlackHandler

        with patch("src.gateway.platforms.slack._HAS_HTTPX", True):
            handler = SlackHandler(
                bot_token="xoxb-mock-token",
                signing_secret="mock_signing_secret",
                on_message=mock_on_message,
            )
            return handler

    def test_init(self, handler):
        assert handler.name == Platform.SLACK
        assert handler.bot_token == "xoxb-mock-token"
        assert not handler.is_started

    def test_check_dependencies(self):
        from src.gateway.platforms.slack import check_slack_dependencies

        with patch("src.gateway.platforms.slack._HAS_HTTPX", True):
            assert check_slack_dependencies() is True

        with patch("src.gateway.platforms.slack._HAS_HTTPX", False):
            assert check_slack_dependencies() is False

    @pytest.mark.asyncio
    async def test_send_no_httpx(self, mock_on_message):
        """Test send returns False when httpx not installed"""
        with patch("src.gateway.platforms.slack._HAS_HTTPX", False):
            from src.gateway.platforms.slack import SlackHandler

            handler = SlackHandler(
                bot_token="xoxb-mock",
                signing_secret="mock",
                on_message=mock_on_message,
            )
            msg = OutgoingMessage(
                platform=Platform.SLACK,
                chat_id="C12345",
                text="hello",
            )
            result = await handler.send(msg)
            assert result is False

    @pytest.mark.asyncio
    async def test_process_message(self, handler, mock_on_message):
        """Test _process_message creates IncomingMessage"""
        event = {
            "type": "message",
            "text": "hello slack",
            "user": "U12345",
            "channel": "C12345",
            "ts": "1234567890.123",
            "thread_ts": "1234567890.123",
        }

        handler.on_message = mock_on_message
        await handler._process_message(event)

        assert mock_on_message.called
        call_args = mock_on_message.call_args[0][0]
        assert isinstance(call_args, IncomingMessage)
        assert call_args.platform == Platform.SLACK
        assert call_args.text == "hello slack"
        assert call_args.user_id == "U12345"

    @pytest.mark.asyncio
    async def test_process_bot_message(self, handler, mock_on_message):
        """Test _process_message ignores bot messages"""
        event = {
            "type": "message",
            "subtype": "bot_message",
            "text": "bot message",
            "user": "U12345",
        }

        handler.on_message = mock_on_message
        await handler._process_message(event)

        assert not mock_on_message.called

    @pytest.mark.asyncio
    async def test_handle_event_message(self, handler, mock_on_message):
        """Test _handle_event processes message event"""
        body = {
            "event": {
                "type": "message",
                "text": "hello from event",
                "user": "U12345",
                "channel": "C12345",
                "ts": "1234567890.123",
            }
        }

        handler.on_message = mock_on_message
        await handler._handle_event(body)

        assert mock_on_message.called

    @pytest.mark.asyncio
    async def test_handle_event_app_mention(self, handler, mock_on_message):
        """Test _handle_event processes app_mention event"""
        body = {
            "event": {
                "type": "app_mention",
                "text": "<@U12345> hello",
                "user": "U12345",
                "channel": "C12345",
            }
        }

        handler.on_message = mock_on_message
        await handler._handle_event(body)

        assert mock_on_message.called

    @pytest.mark.asyncio
    async def test_handle_event_url_verification(self, handler):
        """Test _handle_event handles URL verification"""
        body = {"challenge": "mock_challenge"}
        await handler._handle_event(body)
        # Should not raise or call on_message
