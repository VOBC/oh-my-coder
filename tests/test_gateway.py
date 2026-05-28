"""
Gateway 模块测试
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.gateway.base import (
    IncomingMessage,
    NoopHandler,
    OutgoingMessage,
    Platform,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator with execute_workflow."""
    orch = MagicMock()
    mock_result = MagicMock()
    mock_result.outputs = {}
    orch.execute_workflow = AsyncMock(return_value=mock_result)
    return orch


@pytest.fixture
def gateway_with_orch(mock_orchestrator):
    from src.gateway.gateway import Gateway

    return Gateway(orchestrator=mock_orchestrator)


@pytest.fixture
def gateway_no_orch():
    from src.gateway.gateway import Gateway

    return Gateway(orchestrator=None)


# ---------------------------------------------------------------------------
# IncomingMessage
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# OutgoingMessage
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# NoopHandler
# ---------------------------------------------------------------------------


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

    async def test_start_does_nothing(self, handler):
        await handler.start()
        assert not handler.is_started  # NoopHandler 仍不标记 started

    async def test_send_returns_true(self, handler):
        msg = OutgoingMessage(
            platform=Platform.WHATSAPP,
            chat_id="123",
            text="hello",
        )
        result = await handler.send(msg)
        assert result is True

    async def test_stop_does_nothing(self, handler):
        await handler.stop()  # 不抛异常


# ---------------------------------------------------------------------------
# Platform
# ---------------------------------------------------------------------------


class TestPlatformEnum:
    """测试 Platform 枚举"""

    def test_all_platforms(self):
        assert Platform.TELEGRAM.value == "telegram"
        assert Platform.DISCORD.value == "discord"
        assert Platform.WHATSAPP.value == "whatsapp"
        assert Platform.FEISHU.value == "feishu"
        assert Platform.WECOM.value == "wecom"
        assert Platform.DINGTALK.value == "dingtalk"
        assert Platform.SLACK.value == "slack"
        assert Platform.WECHAT.value == "wechat"

    def test_platform_comparison(self):
        assert Platform.TELEGRAM == Platform.TELEGRAM
        assert Platform.TELEGRAM != Platform.DISCORD


# ---------------------------------------------------------------------------
# Gateway — basic / status
# ---------------------------------------------------------------------------


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

    def test_get_handler_unknown_platform(self, gateway):
        handler = gateway.get_handler(Platform.WECHAT)
        assert handler is None

    async def test_on_platform_message_no_orch(self, gateway):
        """无 orchestrator 时 on_platform_message 不抛异常"""
        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="123",
            chat_id="456",
            text="/start",
        )
        gateway.on_platform_message(msg)  # 不抛异常

    def test_noop_handler_callback(self, gateway):
        """_noop_handler 被调用时不抛异常"""
        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="999",
            chat_id="888",
            text="hello",
        )
        gateway._noop_handler(msg)  # 不抛异常


# ---------------------------------------------------------------------------
# Gateway — lifecycle (start_all / stop_all)
# ---------------------------------------------------------------------------


class TestGatewayLifecycle:
    """测试 start_all / stop_all 生命周期"""

    async def test_start_all_noop_registers_started(self, gateway_no_orch):
        """NoopHandler.start() 被调用后 _started_platforms 被更新

        注意：_start_platform 在调用 handler.start() 后无条件 append，
        不依赖 handler.is_started 的返回值。
        """
        await gateway_no_orch.start_all()
        status = gateway_no_orch.status()
        # 所有 7 个平台均出现在 started_platforms（start() 被调用并 append）
        assert len(status["started_platforms"]) == 7

    async def test_stop_all_noop_no_started(self, gateway_no_orch):
        """无已启动平台时 stop_all 不抛异常"""
        await gateway_no_orch.stop_all()

    async def test_start_all_and_stop_all_with_mock_handler(
        self, gateway_no_orch
    ):
        """模拟一个真实 Handler 的启动/停止流程"""
        mock_handler = MagicMock()
        mock_handler.is_started = False
        mock_handler.start = AsyncMock()
        mock_handler.stop = AsyncMock()

        # 替换 telegram handler
        gateway_no_orch._handlers[Platform.TELEGRAM] = mock_handler

        await gateway_no_orch.start_all()

        # 验证 start 被调用（is_started=False 时 _start_platform 会调用它）
        mock_handler.start.assert_awaited_once()
        assert Platform.TELEGRAM.value in gateway_no_orch._started_platforms

        # stop_all 检查 handler.is_started，在 mock 上临时设为 True
        mock_handler.is_started = True
        await gateway_no_orch.stop_all()
        mock_handler.stop.assert_awaited_once()
        # telegram 已从列表移除；其他平台（未 mock，is_started=False）不在 _started_platforms
        assert 'telegram' not in gateway_no_orch._started_platforms

    async def test_start_all_idempotent(self, gateway_no_orch):
        """多次 start_all 不重复启动"""
        mock_handler = MagicMock()
        mock_handler.is_started = True  # 模拟已启动
        mock_handler.start = AsyncMock()
        gateway_no_orch._handlers[Platform.TELEGRAM] = mock_handler

        await gateway_no_orch.start_all()
        mock_handler.start.assert_not_called()  # 不重复调用

    async def test_start_platform_error_not_raise(self, gateway_no_orch):
        """_start_platform 异常被吞掉，不影响其他平台"""
        good_handler = MagicMock()
        good_handler.is_started = False
        good_handler.start = AsyncMock()
        good_handler.stop = AsyncMock()

        bad_handler = MagicMock()
        bad_handler.is_started = False
        bad_handler.start = AsyncMock(side_effect=RuntimeError("boom"))
        bad_handler.stop = AsyncMock()

        gateway_no_orch._handlers[Platform.TELEGRAM] = bad_handler
        gateway_no_orch._handlers[Platform.DISCORD] = good_handler

        # 不抛异常
        await gateway_no_orch.start_all()

        # 好 handler 仍然启动
        good_handler.start.assert_awaited_once()

    async def test_stop_platform_error_not_raise(self, gateway_no_orch):
        """_stop_platform 异常被吞掉"""
        mock_handler = MagicMock()
        mock_handler.is_started = True
        mock_handler.start = AsyncMock()
        mock_handler.stop = AsyncMock(side_effect=RuntimeError("boom"))

        gateway_no_orch._handlers[Platform.TELEGRAM] = mock_handler
        await gateway_no_orch.start_all()

        # 不抛异常
        await gateway_no_orch.stop_all()


# ---------------------------------------------------------------------------
# Gateway — on_platform_message with orchestrator
# ---------------------------------------------------------------------------


class TestGatewayOnPlatformMessage:
    """测试 on_platform_message + _process_message 路径"""

    async def test_on_platform_message_with_orch(
        self, gateway_with_orch, mock_orchestrator
    ):
        """有 orchestrator 时 on_platform_message 创建异步任务"""
        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="123",
            chat_id="456",
            text="/help",
        )
        gateway_with_orch.on_platform_message(msg)
        # 等待异步任务完成
        await asyncio.sleep(0.1)
        mock_orchestrator.execute_workflow.assert_awaited_once()

    async def test_process_message_no_orchestrator_returns(self, gateway_no_orch):
        """_process_message 在 orchestrator 为 None 时直接返回"""
        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="123",
            chat_id="456",
            text="hello",
        )
        # 不抛异常
        await gateway_no_orch._process_message(msg)

    async def test_process_message_success_sends_reply(
        self, gateway_with_orch, mock_orchestrator
    ):
        """_process_message 成功时调用 handler.send"""
        mock_handler = MagicMock()
        mock_handler.is_started = True
        mock_handler.send = AsyncMock(return_value=True)
        gateway_with_orch._handlers[Platform.TELEGRAM] = mock_handler

        mock_result = MagicMock()
        mock_result.outputs = {}
        mock_orchestrator.execute_workflow.return_value = mock_result

        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="123",
            chat_id="456",
            text="hello",
        )
        await gateway_with_orch._process_message(msg)

        mock_handler.send.assert_awaited_once()
        call_args = mock_handler.send.call_args[0][0]
        assert call_args.platform == Platform.TELEGRAM
        assert call_args.chat_id == "456"

    async def test_process_message_error_sends_error_reply(
        self, gateway_with_orch, mock_orchestrator
    ):
        """_process_message 异常时发送错误回复"""
        mock_handler = MagicMock()
        mock_handler.is_started = True
        mock_handler.send = AsyncMock(return_value=True)
        gateway_with_orch._handlers[Platform.TELEGRAM] = mock_handler

        mock_orchestrator.execute_workflow.side_effect = RuntimeError("fail")

        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="123",
            chat_id="456",
            text="boom",
        )
        await gateway_with_orch._process_message(msg)

        # 发送了错误回复
        assert mock_handler.send.awaited
        call_args = mock_handler.send.call_args[0][0]
        assert "fail" in call_args.text or "RuntimeError" in call_args.text

    async def test_process_message_handler_not_started(
        self, gateway_with_orch, mock_orchestrator
    ):
        """handler 未启动时 _process_message 不发送消息"""
        mock_handler = MagicMock()
        mock_handler.is_started = False
        mock_handler.send = AsyncMock()
        gateway_with_orch._handlers[Platform.TELEGRAM] = mock_handler

        await gateway_with_orch._process_message(
            IncomingMessage(
                platform=Platform.TELEGRAM,
                user_id="123",
                chat_id="456",
                text="hello",
            )
        )
        mock_handler.send.assert_not_called()


# ---------------------------------------------------------------------------
# Gateway — _extract_response
# ---------------------------------------------------------------------------


class TestGatewayExtractResponse:
    """测试 _extract_response"""

    def test_extract_response_none(self):
        from src.gateway.gateway import Gateway

        result = Gateway._extract_response(None)
        assert result == "（无结果）"

    def test_extract_response_str(self):
        from src.gateway.gateway import Gateway

        result = Gateway._extract_response("simple string")
        assert result == "simple string"

    def test_extract_response_object_no_outputs(self):
        from src.gateway.gateway import Gateway

        class FakeResult:
            status = "completed"
            outputs = {}

        result = Gateway._extract_response(FakeResult())
        assert result  # 不崩溃

    def test_extract_response_with_outputs(self):
        from src.gateway.gateway import Gateway

        class MockOutput:
            result = "hello from agent"

        mock_result = MagicMock()
        mock_result.outputs = {"agent1": MockOutput()}

        result = Gateway._extract_response(mock_result)
        assert "agent1" in result
        assert "hello from agent" in result

    def test_extract_response_outputs_truncated(self):
        from src.gateway.gateway import Gateway

        class MockOutput:
            result = "x" * 1000  # 超过 500 字符

        mock_result = MagicMock()
        mock_result.outputs = {"agent1": MockOutput()}

        result = Gateway._extract_response(mock_result)
        # 内容被截断到 500 字符
        assert len(result) <= 600  # **[{agent1}]**\n + 500 chars

    def test_extract_response_object_no_result_attr(self):
        from src.gateway.gateway import Gateway

        class NoResultAttr:
            outputs = {"a": MagicMock()}  # output.result is None

        result = Gateway._extract_response(NoResultAttr())
        # 没有 content 的 output 被跳过，回退到 str
        assert result  # 不崩溃


# ---------------------------------------------------------------------------
# Gateway — handle_telegram_update
# ---------------------------------------------------------------------------


class TestGatewayHandleTelegramUpdate:
    """测试 handle_telegram_update"""

    async def test_handle_telegram_update_no_handler(self, gateway_no_orch):
        """Telegram 未配置时 handle_telegram_update 直接返回"""
        await gateway_no_orch.handle_telegram_update(
            {"message": {"from": {"id": 123}, "chat": {"id": 456}, "text": "hi"}}
        )
        # 无异常

    async def test_handle_telegram_update_empty_message(self, gateway_no_orch):
        """无 message 字段时不崩溃"""
        await gateway_no_orch.handle_telegram_update({})

    async def test_handle_telegram_update_noop_handler(self, gateway_no_orch):
        """NoopHandler 时直接返回（不触发 on_platform_message）"""
        # NoopHandler 不抛异常
        await gateway_no_orch.handle_telegram_update(
            {"message": {"from": {"id": 1}, "chat": {"id": 2}, "text": "x"}}
        )

    async def test_handle_telegram_update_routes_to_on_platform_message(
        self, gateway_no_orch
    ):
        """handle_telegram_update 正确构造 IncomingMessage 并调用 on_platform_message"""
        messages = []

        def capture(msg):
            messages.append(msg)

        gateway_no_orch.on_platform_message = capture

        # 直接注入一个 NoopHandler 的 Telegram handler（不触发 __init__ 的 noop 路径）
        real_handler = MagicMock()
        real_handler.is_started = False
        real_handler.start = AsyncMock()
        real_handler.stop = AsyncMock()
        gateway_no_orch._handlers[Platform.TELEGRAM] = real_handler

        update = {
            "update_id": 12345,
            "message": {
                "from": {"id": 111},
                "chat": {"id": 222},
                "text": "/start",
                "message_id": 999,
            },
        }
        await gateway_no_orch.handle_telegram_update(update)

        assert len(messages) == 1
        msg = messages[0]
        assert msg.platform == Platform.TELEGRAM
        assert msg.user_id == "111"
        assert msg.chat_id == "222"
        assert msg.text == "/start"
        assert msg.reply_to == "999"


# ---------------------------------------------------------------------------
# Gateway — status table
# ---------------------------------------------------------------------------


class TestGatewayStatusTable:
    """测试 status 输出的数据结构"""

    def test_status_fields(self):
        from src.gateway.gateway import Gateway

        gw = Gateway(orchestrator=None)
        status = gw.status()

        assert "started_platforms" in status
        assert isinstance(status["started_platforms"], list)

        for info in status["handlers"].values():
            assert "configured" in info
            assert "started" in info
            assert "type" in info

    def test_status_handler_types(self):
        from src.gateway.gateway import Gateway

        gw = Gateway(orchestrator=None)
        status = gw.status()
        # 验证所有已知平台都在
        for p in ["telegram", "discord", "whatsapp", "feishu", "wecom", "dingtalk", "slack"]:
            assert p in status["handlers"]


# ---------------------------------------------------------------------------
# Gateway — _register_* paths (mocked dependencies)
# ---------------------------------------------------------------------------


class TestGatewayRegisterPlatforms:
    """测试各平台初始化路径（不依赖真实平台包）"""

    def test_register_whatsapp_partial_credentials(self):
        """仅有 phone_number_id 无 access_token 时使用 NoopHandler"""
        from src.gateway.gateway import Gateway

        gw = Gateway(whatsapp_phone_number_id="123")
        assert isinstance(gw.get_handler(Platform.WHATSAPP), NoopHandler)

    def test_allowed_user_ids(self):
        """allowed_user_ids 对各平台正确传递（不影响 handler 类型判断）"""
        from src.gateway.gateway import Gateway

        allowed = {Platform.TELEGRAM: ["user1", "user2"]}
        gw = Gateway(orchestrator=None, allowed_user_ids=allowed)
        status = gw.status()
        assert "telegram" in status["handlers"]

    def test_all_platforms_initialized_as_noop(self):
        """无任何 token 时所有平台都用 NoopHandler"""
        from src.gateway.gateway import Gateway

        gw = Gateway(orchestrator=None)
        # 除 WECHAT 外所有平台都有 NoopHandler 默认路径
        for p in [
            Platform.TELEGRAM,
            Platform.DISCORD,
            Platform.WHATSAPP,
            Platform.FEISHU,
            Platform.WECOM,
            Platform.DINGTALK,
            Platform.SLACK,
        ]:
            assert isinstance(gw.get_handler(p), NoopHandler), f"{p} should be NoopHandler"

    def test_wecom_partial_creds(self):
        """WECOM 缺少必填字段时用 NoopHandler"""
        from src.gateway.gateway import Gateway

        # 缺少 corp_secret
        gw = Gateway(wecom_corp_id="corp", wecom_agent_id="agent")
        assert isinstance(gw.get_handler(Platform.WECOM), NoopHandler)

    def test_dingtalk_partial_creds(self):
        """钉钉缺少必填字段时用 NoopHandler"""
        from src.gateway.gateway import Gateway

        gw = Gateway(dingtalk_app_key="key")  # 缺少 app_secret
        assert isinstance(gw.get_handler(Platform.DINGTALK), NoopHandler)

    def test_feishu_partial_creds(self):
        """飞书缺少必填字段时用 NoopHandler"""
        from src.gateway.gateway import Gateway

        gw = Gateway(feishu_app_id="app")  # 缺少 app_secret
        assert isinstance(gw.get_handler(Platform.FEISHU), NoopHandler)

    def test_slack_partial_creds(self):
        """Slack 缺少必填字段时用 NoopHandler"""
        from src.gateway.gateway import Gateway

        gw = Gateway(slack_bot_token="token")  # 缺少 signing_secret
        assert isinstance(gw.get_handler(Platform.SLACK), NoopHandler)


# ---------------------------------------------------------------------------
# Gateway — _process_message error reply fallback
# ---------------------------------------------------------------------------


class TestGatewayErrorHandling:
    """测试错误回复的 fallback"""

    async def test_error_reply_send_also_fails(self, gateway_with_orch, mock_orchestrator):
        """错误回复发送本身也失败时，不应再抛异常"""
        mock_handler = MagicMock()
        mock_handler.is_started = True
        mock_handler.send = AsyncMock(side_effect=[RuntimeError("reply fail"), Exception("double fail")])
        gateway_with_orch._handlers[Platform.TELEGRAM] = mock_handler

        mock_orchestrator.execute_workflow.side_effect = RuntimeError("workflow fail")

        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="123",
            chat_id="456",
            text="boom",
        )
        # 不抛异常（错误被吞掉）
        await gateway_with_orch._process_message(msg)
