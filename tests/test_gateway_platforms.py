"""多平台 Handler 单元测试"""

import pytest

from src.gateway.base import (
    OutgoingMessage,
    Platform,
)

pytestmark = pytest.mark.skip(reason="asyncio event loop issue on macOS")


# ---- Platform 枚举测试 ----


class TestPlatformEnum:
    """验证所有新增平台在枚举中"""

    def test_feishu_platform(self):
        assert Platform.FEISHU.value == "feishu"

    def test_wecom_platform(self):
        assert Platform.WECOM.value == "wecom"

    def test_dingtalk_platform(self):
        assert Platform.DINGTALK.value == "dingtalk"

    def test_all_platforms_count(self):
        platforms = list(Platform)
        assert len(platforms) == 8


# ---- WhatsApp Handler 测试 ----


class TestWhatsAppHandler:
    """测试 WhatsAppHandler"""

    @pytest.fixture
    def handler(self):
        from src.gateway.platforms.whatsapp import WhatsAppHandler

        return WhatsAppHandler(
            phone_number_id="123456789",
            access_token="mock_token",
            webhook_url="https://example.com",
            verify_token="test_verify",
            on_message=lambda m: None,
        )

    def test_init(self, handler):
        assert handler.name == Platform.WHATSAPP
        assert handler.phone_number_id == "123456789"
        assert not handler.is_started

    @pytest.mark.asyncio
    async def test_send_noop_when_not_started(self, handler):
        """未启动时 send 返回 False"""
        msg = OutgoingMessage(
            platform=Platform.WHATSAPP,
            chat_id="15551234567",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is False


# ---- 飞书 Handler 测试 ----


class TestFeishuHandler:
    """测试 FeishuHandler"""

    @pytest.fixture
    def handler(self):
        from src.gateway.platforms.feishu import FeishuHandler

        return FeishuHandler(
            app_id="cli_abc123",
            app_secret="mock_secret",
            on_message=lambda m: None,
        )

    def test_init(self, handler):
        assert handler.name == Platform.FEISHU
        assert handler.app_id == "cli_abc123"
        assert not handler.is_started

    @pytest.mark.asyncio
    async def test_send_noop_when_no_token(self, handler):
        """无 token 时 send 返回 False"""
        handler._tenant_access_token = None
        msg = OutgoingMessage(
            platform=Platform.FEISHU,
            chat_id="ou_abc123",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is False


# ---- 企业微信 Handler 测试 ----


class TestWeComHandler:
    """测试 WeComHandler"""

    @pytest.fixture
    def handler(self):
        from src.gateway.platforms.wecom import WeComHandler

        return WeComHandler(
            corp_id="ww123456789",
            agent_id="1000001",
            corp_secret="mock_secret",
            on_message=lambda m: None,
        )

    def test_init(self, handler):
        assert handler.name == Platform.WECOM
        assert handler.corp_id == "ww123456789"
        assert not handler.is_started

    @pytest.mark.asyncio
    async def test_send_noop_when_no_token(self, handler):
        """无 token 时 send 返回 False"""
        handler._access_token = None
        msg = OutgoingMessage(
            platform=Platform.WECOM,
            chat_id="WangXiaoMing",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is False


# ---- 钉钉 Handler 测试 ----


class TestDingTalkHandler:
    """测试 DingTalkHandler"""

    @pytest.fixture
    def handler(self):
        from src.gateway.platforms.dingtalk import DingTalkHandler

        return DingTalkHandler(
            app_key="ding1234567890",
            app_secret="mock_secret",
            on_message=lambda m: None,
        )

    def test_init(self, handler):
        assert handler.name == Platform.DINGTALK
        assert handler.app_key == "ding1234567890"
        assert not handler.is_started

    @pytest.mark.asyncio
    async def test_send_noop_when_no_token(self, handler):
        """无 token 时 send 返回 False"""
        handler._access_token = None
        msg = OutgoingMessage(
            platform=Platform.DINGTALK,
            chat_id="user123",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is False


# ---- Slack Handler 测试 ----


class TestSlackHandler:
    """测试 SlackHandler"""

    @pytest.fixture
    def handler(self):
        from src.gateway.platforms.slack import SlackHandler

        return SlackHandler(
            bot_token="xoxb-mock-token",
            signing_secret="mock_signing_secret",
            on_message=lambda m: None,
        )

    def test_init(self, handler):
        assert handler.name == Platform.SLACK
        assert handler.bot_token == "xoxb-mock-token"
        assert not handler.is_started

    @pytest.mark.asyncio
    async def test_send_noop(self, handler):
        """无真实连接时 send 返回 False"""
        msg = OutgoingMessage(
            platform=Platform.SLACK,
            chat_id="C0123456789",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is False


# ---- Gateway 新平台注册测试 ----


class TestGatewayNewPlatforms:
    """测试 Gateway 对新平台的注册"""

    def test_gateway_with_whatsapp_config(self):
        from src.gateway.gateway import Gateway

        gw = Gateway(
            orchestrator=None,
            whatsapp_phone_number_id="123456789",
            whatsapp_access_token="mock_token",
            whatsapp_webhook_url="https://example.com",
        )
        status = gw.status()
        assert "whatsapp" in status["handlers"]
        handler = gw.get_handler(Platform.WHATSAPP)
        assert handler is not None

    def test_gateway_with_feishu_config(self):
        from src.gateway.gateway import Gateway

        gw = Gateway(
            orchestrator=None,
            feishu_app_id="cli_abc",
            feishu_app_secret="secret",
        )
        status = gw.status()
        assert "feishu" in status["handlers"]
        handler = gw.get_handler(Platform.FEISHU)
        assert handler is not None

    def test_gateway_with_wecom_config(self):
        from src.gateway.gateway import Gateway

        gw = Gateway(
            orchestrator=None,
            wecom_corp_id="ww123",
            wecom_agent_id="1000001",
            wecom_corp_secret="secret",
        )
        status = gw.status()
        assert "wecom" in status["handlers"]

    def test_gateway_with_dingtalk_config(self):
        from src.gateway.gateway import Gateway

        gw = Gateway(
            orchestrator=None,
            dingtalk_app_key="ding123",
            dingtalk_app_secret="secret",
        )
        status = gw.status()
        assert "dingtalk" in status["handlers"]

    def test_gateway_with_slack_config(self):
        from src.gateway.gateway import Gateway

        gw = Gateway(
            orchestrator=None,
            slack_bot_token="xoxb-mock",
            slack_signing_secret="signing_secret",
        )
        status = gw.status()
        assert "slack" in status["handlers"]

    def test_gateway_all_platforms_noop_when_unconfigured(self):
        from src.gateway.gateway import Gateway

        gw = Gateway(orchestrator=None)
        status = gw.status()

        for platform_name in ["whatsapp", "feishu", "wecom", "dingtalk", "slack"]:
            assert platform_name in status["handlers"], f"{platform_name} missing"
            assert status["handlers"][platform_name]["configured"] is False
            assert status["handlers"][platform_name]["started"] is False
