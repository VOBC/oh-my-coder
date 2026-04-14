"""
Gateway 模块测试
"""

import pytest

# Skip macOS asyncio event loop issue - run individually if needed
pytestmark = pytest.mark.skip(reason="asyncio event loop issue on macOS")

from src.gateway.base import (
    IncomingMessage,
    NoopHandler,
    OutgoingMessage,
    Platform,
)


class TestIncomingMessage:
    """测试统一收件消息格式"""

    def test_basic(self):
        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="123",
            chat_id="456",
            text="hello",
        )
        assert msg.platform == Platform.TELEGRAM
        assert msg.user_id == "123"
        assert msg.text == "hello"
        assert msg.timestamp  # 自动生成

    def test_with_raw(self):
        msg = IncomingMessage(
            platform=Platform.DISCORD,
            user_id="789",
            chat_id="000",
            text="/help",
            raw={"guild_id": "111", "command": "help"},
        )
        assert msg.raw["guild_id"] == "111"


class TestOutgoingMessage:
    """测试统一发件消息格式"""

    def test_basic(self):
        msg = OutgoingMessage(
            platform=Platform.TELEGRAM,
            chat_id="456",
            text="Hi there!",
        )
        assert msg.parse_mode == "markdown"
        assert msg.reply_to is None

    def test_reply(self):
        msg = OutgoingMessage(
            platform=Platform.DISCORD,
            chat_id="000",
            text="Replying",
            reply_to="12345",
            parse_mode="html",
        )
        assert msg.reply_to == "12345"
        assert msg.parse_mode == "html"


class TestNoopHandler:
    """测试空实现 Handler"""

    @pytest.fixture
    def handler(self):
        return NoopHandler(
            platform=Platform.WHATSAPP,
            on_message=lambda m: None,
        )

    def test_not_started_initially(self, handler):
        assert not handler.is_started

    @pytest.mark.asyncio
    async def test_start_does_nothing(self, handler):
        await handler.start()
        assert not handler.is_started  # NoopHandler 仍不标记 started

    @pytest.mark.asyncio
    async def test_send_returns_true(self, handler):
        msg = OutgoingMessage(
            platform=Platform.WHATSAPP,
            chat_id="123",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is True


class TestPlatformEnum:
    """测试 Platform 枚举"""

    def test_all_platforms(self):
        assert Platform.TELEGRAM.value == "telegram"
        assert Platform.DISCORD.value == "discord"
        assert Platform.WHATSAPP.value == "whatsapp"
        assert Platform.SLACK.value == "slack"
        assert Platform.WECHAT.value == "wechat"

    def test_platform_comparison(self):
        assert Platform.TELEGRAM == Platform.TELEGRAM
        assert Platform.TELEGRAM != Platform.DISCORD


class TestGatewayBasic:
    """测试 Gateway 基本功能（不含真实 Bot 连接）"""

    @pytest.fixture
    def gateway(self):
        from src.gateway.gateway import Gateway

        return Gateway(orchestrator=None)

    def test_init_no_tokens(self, gateway):
        """无 token 时不崩溃"""
        status = gateway.status()
        assert "handlers" in status
        assert "telegram" in status["handlers"]
        assert "discord" in status["handlers"]

    def test_status_shows_noop_handlers(self, gateway):
        status = gateway.status()
        # 无 token → NoopHandler
        assert status["handlers"]["telegram"]["configured"] is False
        assert status["handlers"]["discord"]["configured"] is False

    def test_get_handler(self, gateway):
        handler = gateway.get_handler(Platform.TELEGRAM)
        assert handler is not None
        assert isinstance(handler, NoopHandler)

    @pytest.mark.asyncio
    async def test_on_platform_message_noop(self, gateway):
        """无 orchestrator 时 on_platform_message 不抛异常"""
        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="123",
            chat_id="456",
            text="/start",
        )
        gateway.on_platform_message(msg)  # 不抛异常


class TestGatewayTelegramConfigured:
    """测试 Gateway 检测 Telegram token 后的行为（mock）"""

    @pytest.fixture
    def gateway_with_telegram(self, monkeypatch):
        """模拟已配置 Telegram token"""
        from src.gateway.gateway import Gateway

        # 模拟依赖检查通过但无真实 bot
        import src.gateway.platforms.telegram as tg_mod

        monkeypatch.setattr(tg_mod, "_HAS_TELEGRAM", True)

        gateway = Gateway(
            orchestrator=None,
            telegram_token="mock_token_for_test",
        )
        return gateway

    def test_status_telegram_configured(self, gateway_with_telegram):
        status = gateway_with_telegram.status()
        # token 传了，但未 start → configured=False（因为未注册）
        assert "telegram" in status["handlers"]

    def test_extract_response_empty(self):
        from src.gateway.gateway import Gateway

        result = Gateway._extract_response(None)
        assert result == "（无结果）"

    def test_extract_response_str(self):
        from src.gateway.gateway import Gateway

        result = Gateway._extract_response("simple string")
        assert result == "simple string"

    def test_extract_response_object(self):
        from src.gateway.gateway import Gateway

        class FakeResult:
            status = "completed"
            outputs = {}

        result = Gateway._extract_response(FakeResult())
        assert result  # 不崩溃


class TestGatewayStatusTable:
    """测试 status 输出的数据结构"""

    def test_status_fields(self):
        from src.gateway.gateway import Gateway

        gw = Gateway(orchestrator=None)
        status = gw.status()

        assert "started_platforms" in status
        assert isinstance(status["started_platforms"], list)

        for platform_name, info in status["handlers"].items():
            assert "configured" in info
            assert "started" in info
            assert "type" in info
