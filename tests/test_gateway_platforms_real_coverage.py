"""Real coverage tests for gateway/platforms

These tests actually execute real code by only mocking external dependencies.
This ensures actual coverage of the methods under test.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.gateway.base import IncomingMessage, OutgoingMessage, Platform


# ============================================================
# WeCom Handler - Real Coverage
# ============================================================


class TestWeComHandlerRealCoverage:
    """Tests that execute real code for coverage"""

    @pytest.fixture
    def handler(self):
        from src.gateway.platforms.wecom import WeComHandler

        h = WeComHandler(
            corp_id="ww123456789",
            agent_id="1000001",
            corp_secret="mock_secret",
            token="mock_token",
            encoding_aes_key="mock_aes_key_12345678901234567890",
            webhook_port=8080,
            on_message=MagicMock(),
            on_error=MagicMock(),
        )
        return h

    def test_init(self, handler):
        """Test __init__"""
        assert handler.name == Platform.WECOM
        assert handler.corp_id == "ww123456789"
        assert handler.agent_id == "1000001"
        assert not handler._started

    @pytest.mark.asyncio
    async def test_start_no_httpx(self, handler):
        """Test start() raises RuntimeError when httpx not installed"""
        with patch("src.gateway.platforms.wecom._HAS_HTTPX", False):
            with pytest.raises(RuntimeError, match="httpx 未安装"):
                await handler.start()

    @pytest.mark.asyncio
    async def test_start_with_httpx(self, handler):
        """Test start() with httpx installed"""
        with patch("src.gateway.platforms.wecom._HAS_HTTPX", True):
            # Mock _run_webhook_server to avoid actually starting a server
            with patch.object(handler, "_run_webhook_server", new_callable=AsyncMock):
                await handler.start()
                assert handler._started is True

    @pytest.mark.asyncio
    async def test_start_without_encryption(self, handler):
        """Test start() without encryption (starts poll loop)"""
        handler.encoding_aes_key = None
        with patch("src.gateway.platforms.wecom._HAS_HTTPX", True):
            # Mock _poll_loop to avoid actually polling
            with patch.object(handler, "_poll_loop", new_callable=AsyncMock):
                await handler.start()
                assert handler._started is True

    @pytest.mark.asyncio
    async def test_stop(self, handler):
        """Test stop()"""
        handler._started = True
        # Create a real asyncio task
        async def dummy_task():
            await asyncio.sleep(100)
        handler._poll_task = asyncio.create_task(dummy_task())

        await handler.stop()
        assert handler._started is False

    @pytest.mark.asyncio
    async def test_get_token_with_valid_token(self, handler):
        """Test _get_token() with valid token"""
        handler._access_token = "valid_token"
        handler._token_expires_at = time.time() + 3600  # Valid for 1 hour

        result = await handler._get_token()
        assert result == "valid_token"

    @pytest.mark.asyncio
    async def test_get_token_expired(self, handler):
        """Test _get_token() refreshes when expired"""
        handler._access_token = "old_token"
        handler._token_expires_at = time.time() - 100  # Expired

        # Mock httpx to simulate successful token refresh
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={
                "access_token": "new_token_123",
                "expires_in": 7200
            })
            mock_client_instance.get.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            result = await handler._get_token()
            assert result == "new_token_123"
            assert handler._access_token == "new_token_123"

    @pytest.mark.asyncio
    async def test_get_token_none(self, handler):
        """Test _get_token() refreshes when no token"""
        handler._access_token = None

        # Mock httpx to simulate successful token refresh
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={
                "access_token": "new_token_123",
                "expires_in": 7200
            })
            mock_client_instance.get.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            result = await handler._get_token()
            assert result == "new_token_123"

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, handler):
        """Test _refresh_token() success"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={
                "access_token": "new_token_123",
                "expires_in": 7200
            })
            mock_client_instance.get.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            await handler._refresh_token()
            assert handler._access_token == "new_token_123"
            assert handler._token_expires_at > time.time()

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, handler):
        """Test _refresh_token() failure"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={
                "errcode": 40013,
                "errmsg": "invalid corpid"
            })
            mock_client_instance.get.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            await handler._refresh_token()
            assert handler._access_token is None

    @pytest.mark.asyncio
    async def test_send_success(self, handler):
        """Test send() success"""
        # Set valid token
        handler._access_token = "mock_token"
        handler._token_expires_at = time.time() + 3600
        handler.agent_id = "1000001"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={"errcode": 0, "errmsg": "ok"})
            mock_client_instance.post.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            msg = OutgoingMessage(
                platform=Platform.WECOM,
                chat_id="User1",
                text="test message",
            )
            result = await handler.send(msg)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_failure(self, handler):
        """Test send() failure"""
        handler._access_token = "mock_token"
        handler._token_expires_at = time.time() + 3600
        handler.agent_id = "1000001"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={"errcode": 93000, "errmsg": "send limit"})
            mock_client_instance.post.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            msg = OutgoingMessage(
                platform=Platform.WECOM,
                chat_id="User1",
                text="test message",
            )
            result = await handler.send(msg)
            assert result is False

    @pytest.mark.asyncio
    async def test_process_message(self, handler):
        """Test _process_message()"""
        msg = {
            "MsgType": "text",
            "Content": "hello world",
            "FromUserName": "User1",
            "ToUserName": "ww123",
            "MsgId": "msg_123",
        }

        handler.on_message = MagicMock()
        await handler._process_message(msg)
        handler.on_message.assert_called_once()

        # Verify IncomingMessage was created correctly
        call_args = handler.on_message.call_args[0][0]
        assert isinstance(call_args, IncomingMessage)
        assert call_args.platform == Platform.WECOM
        assert call_args.text == "hello world"

    @pytest.mark.asyncio
    async def test_process_non_text_message(self, handler):
        """Test _process_message() ignores non-text"""
        msg = {
            "MsgType": "image",
            "FromUserName": "User1",
        }

        handler.on_message = MagicMock()
        await handler._process_message(msg)
        handler.on_message.assert_not_called()

    def test_check_dependencies_installed(self):
        """Test check_wecom_dependencies() when installed"""
        with patch("src.gateway.platforms.wecom._HAS_HTTPX", True):
            from src.gateway.platforms.wecom import check_wecom_dependencies
            assert check_wecom_dependencies() is True

    def test_check_dependencies_not_installed(self):
        """Test check_wecom_dependencies() when not installed"""
        with patch("src.gateway.platforms.wecom._HAS_HTTPX", False):
            from src.gateway.platforms.wecom import check_wecom_dependencies
            assert check_wecom_dependencies() is False


# ============================================================
# DingTalk Handler - Real Coverage
# ============================================================


class TestDingTalkHandlerRealCoverage:
    """Tests that execute real code for coverage"""

    @pytest.fixture
    def handler(self):
        from src.gateway.platforms.dingtalk import DingTalkHandler

        h = DingTalkHandler(
            app_key="ding1234567890",
            app_secret="mock_secret",
            token="mock_token",
            aes_key="mock_aes_key_1234567890123456789012",
            webhook_port=8080,
            on_message=MagicMock(),
            on_error=MagicMock(),
        )
        return h

    def test_init(self, handler):
        """Test __init__"""
        assert handler.name == Platform.DINGTALK
        assert handler.app_key == "ding1234567890"
        assert not handler._started

    @pytest.mark.asyncio
    async def test_start_no_httpx(self, handler):
        """Test start() raises RuntimeError when httpx not installed"""
        with patch("src.gateway.platforms.dingtalk._HAS_HTTPX", False):
            with pytest.raises(RuntimeError, match="httpx 未安装"):
                await handler.start()

    @pytest.mark.asyncio
    async def test_start_with_httpx(self, handler):
        """Test start() with httpx installed"""
        with patch("src.gateway.platforms.dingtalk._HAS_HTTPX", True):
            # Mock _run_webhook_server to avoid actually starting a server
            with patch.object(handler, "_run_webhook_server", new_callable=AsyncMock):
                await handler.start()
                assert handler._started is True

    @pytest.mark.asyncio
    async def test_start_without_aes(self, handler):
        """Test start() without AES key (logs warning)"""
        handler.aes_key = None
        with patch("src.gateway.platforms.dingtalk._HAS_HTTPX", True):
            with patch("src.gateway.platforms.dingtalk.logger") as mock_logger:
                await handler.start()
                assert handler._started is True
                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, handler):
        """Test stop()"""
        handler._started = True
        # Create a real asyncio task
        async def dummy_task():
            await asyncio.sleep(100)
        handler._server_task = asyncio.create_task(dummy_task())

        await handler.stop()
        assert handler._started is False

    @pytest.mark.asyncio
    async def test_get_token_with_valid_token(self, handler):
        """Test _get_token() with valid token"""
        handler._access_token = "valid_token"
        handler._token_expires_at = time.time() + 3600

        result = await handler._get_token()
        assert result == "valid_token"

    @pytest.mark.asyncio
    async def test_get_token_expired(self, handler):
        """Test _get_token() refreshes when expired"""
        handler._access_token = "old_token"
        handler._token_expires_at = time.time() - 100

        # Mock httpx to simulate successful token refresh
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={
                "accessToken": "new_token_123",
                "expireIn": 7200
            })
            mock_client_instance.post.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            result = await handler._get_token()
            assert result == "new_token_123"
            assert handler._access_token == "new_token_123"

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, handler):
        """Test _refresh_token() success"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={
                "accessToken": "new_token_123",
                "expireIn": 7200
            })
            mock_client_instance.post.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            await handler._refresh_token()
            assert handler._access_token == "new_token_123"

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, handler):
        """Test _refresh_token() failure"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={
                "code": "InvalidAppKey",
                "message": "invalid appkey"
            })
            mock_client_instance.post.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            await handler._refresh_token()
            assert handler._access_token is None

    @pytest.mark.asyncio
    async def test_send_success(self, handler):
        """Test send() success"""
        handler._access_token = "mock_token"
        handler._token_expires_at = time.time() + 3600

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={"errcode": 0, "errmsg": "ok", "task_id": 123})
            mock_client_instance.post.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            msg = OutgoingMessage(
                platform=Platform.DINGTALK,
                chat_id="user123",
                text="test message",
            )
            result = await handler.send(msg)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_failure(self, handler):
        """Test send() failure"""
        handler._access_token = "mock_token"
        handler._token_expires_at = time.time() + 3600

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={"errcode": 43001, "errmsg": "no permission"})
            mock_client_instance.post.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            msg = OutgoingMessage(
                platform=Platform.DINGTALK,
                chat_id="user123",
                text="test message",
            )
            result = await handler.send(msg)
            assert result is False

    @pytest.mark.asyncio
    async def test_handle_callback(self, handler):
        """Test _handle_callback()"""
        import json

        body = json.dumps({
            "msgtype": "text",
            "text": {"content": "hello dingtalk"},
            "senderStaffId": "user123",
            "conversationId": "cid123",
            "msgId": "msg_123"
        })

        handler.on_message = MagicMock()
        await handler._handle_callback(body)
        handler.on_message.assert_called_once()

        # Verify IncomingMessage was created correctly
        call_args = handler.on_message.call_args[0][0]
        assert isinstance(call_args, IncomingMessage)
        assert call_args.platform == Platform.DINGTALK
        assert call_args.text == "hello dingtalk"

    @pytest.mark.asyncio
    async def test_handle_callback_non_text(self, handler):
        """Test _handle_callback() ignores non-text"""
        import json

        body = json.dumps({
            "msgtype": "picture",
            "senderStaffId": "user123",
        })

        handler.on_message = MagicMock()
        await handler._handle_callback(body)
        handler.on_message.assert_not_called()

    def test_check_dependencies_installed(self):
        """Test check_dingtalk_dependencies() when installed"""
        with patch("src.gateway.platforms.dingtalk._HAS_HTTPX", True):
            from src.gateway.platforms.dingtalk import check_dingtalk_dependencies
            assert check_dingtalk_dependencies() is True

    def test_check_dependencies_not_installed(self):
        """Test check_dingtalk_dependencies() when not installed"""
        with patch("src.gateway.platforms.dingtalk._HAS_HTTPX", False):
            from src.gateway.platforms.dingtalk import check_dingtalk_dependencies
            assert check_dingtalk_dependencies() is False


# ============================================================
# Feishu Handler - Real Coverage
# ============================================================


class TestFeishuHandlerRealCoverage:
    """Tests that execute real code for coverage"""

    @pytest.fixture
    def handler(self):
        from src.gateway.platforms.feishu import FeishuHandler

        h = FeishuHandler(
            app_id="cli_abc123",
            app_secret="mock_secret",
            encrypt_key="mock_encrypt_key",
            verify_token="mock_verify_token",
            on_message=MagicMock(),
            on_error=MagicMock(),
        )
        return h

    def test_init(self, handler):
        """Test __init__"""
        assert handler.name == Platform.FEISHU
        assert handler.app_id == "cli_abc123"
        assert not handler._started

    @pytest.mark.asyncio
    async def test_start_no_httpx(self, handler):
        """Test start() raises RuntimeError when httpx not installed"""
        with patch("src.gateway.platforms.feishu._HAS_HTTPX", False):
            with pytest.raises(RuntimeError, match="httpx 未安装"):
                await handler.start()

    @pytest.mark.asyncio
    async def test_start_with_httpx(self, handler):
        """Test start() with httpx installed"""
        with patch("src.gateway.platforms.feishu._HAS_HTTPX", True):
            # Mock _long_poll_loop to avoid actually polling
            with patch.object(handler, "_long_poll_loop", new_callable=AsyncMock):
                await handler.start()
                assert handler._started is True

    @pytest.mark.asyncio
    async def test_stop(self, handler):
        """Test stop()"""
        handler._started = True
        # Create a real asyncio task
        async def dummy_task():
            await asyncio.sleep(100)
        handler._poll_task = asyncio.create_task(dummy_task())

        await handler.stop()
        assert handler._started is False

    @pytest.mark.asyncio
    async def test_get_token_with_valid_token(self, handler):
        """Test _get_token() with valid token"""
        handler._tenant_access_token = "valid_token"
        handler._token_expires_at = time.time() + 3600

        result = await handler._get_token()
        assert result == "valid_token"

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, handler):
        """Test _refresh_token() success"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={
                "code": 0,
                "tenant_access_token": "new_token_123",
                "expire": 7200
            })
            mock_client_instance.post.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            await handler._refresh_token()
            assert handler._tenant_access_token == "new_token_123"

    @pytest.mark.asyncio
    async def test_send_success(self, handler):
        """Test send() success"""
        handler._tenant_access_token = "mock_token"
        handler._token_expires_at = time.time() + 3600

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json = MagicMock(return_value={"code": 0, "msg": "success", "data": {}})
            mock_resp.status_code = 200
            mock_client_instance.post.return_value = mock_resp
            
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance
            mock_client_class.return_value.__aexit__.return_value = None

            msg = OutgoingMessage(
                platform=Platform.FEISHU,
                chat_id="ou_abc123",
                text="test message",
            )
            result = await handler.send(msg)
            assert result is True

    @pytest.mark.asyncio
    async def test_process_message(self, handler):
        """Test _process_message()"""
        msg = {
            "msg_type": "text",
            "body": {"content": '{"text": "hello feishu"}'},
            "sender": {"id": "ou_abc123"},
            "chat_id": "oc_chat123",
            "chat_type": "p2p",
            "message_id": "msg_123",
            "create_time": "1698765432",
        }

        handler.on_message = MagicMock()
        await handler._process_message(msg)
        handler.on_message.assert_called_once()

    def test_check_dependencies_installed(self):
        """Test check_feishu_dependencies() when installed"""
        with patch("src.gateway.platforms.feishu._HAS_HTTPX", True):
            from src.gateway.platforms.feishu import check_feishu_dependencies
            assert check_feishu_dependencies() is True

    def test_check_dependencies_not_installed(self):
        """Test check_feishu_dependencies() when not installed"""
        with patch("src.gateway.platforms.feishu._HAS_HTTPX", False):
            from src.gateway.platforms.feishu import check_feishu_dependencies
            assert check_feishu_dependencies() is False
