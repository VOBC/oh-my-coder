"""Tests for gateway/platforms (wecom, dingtalk, feishu).

Only mock `httpx.AsyncClient` (external dependency).
Let internal methods (_refresh_token, send, _process_message, etc.) execute for real.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

pytest.importorskip("httpx")

from gateway.platforms.base import (
    IncomingMessage,
    OutgoingMessage,
    Platform,
    PlatformHandler,
)


class FakeAsyncClient:
    """Fake httpx.AsyncClient that returns canned responses."""

    def __init__(
        self,
        get_response: Optional[Any] = None,
        post_response: Optional[Any] = None,
        post_response_by_url: Optional[dict] = None,
    ):
        self._get_response = get_response
        self._post_response = post_response
        self._post_response_by_url = post_response_by_url or {}
        self.timeout = 15.0
        self.last_url: Optional[str] = None
        self.last_json: Optional[Any] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def get(self, url: str, params: Any = None, **kwargs: Any) -> Any:
        self.last_url = url
        resp = MagicMock()
        resp.json = MagicMock(return_value=self._get_response or {"errcode": 0, "errmsg": "ok"})
        resp.status_code = 200
        return resp

    async def post(self, url: str, params: Any = None, json: Any = None, headers: Any = None, **kwargs: Any) -> Any:
        self.last_url = url
        self.last_json = json
        resp = MagicMock()
        for key, val in self._post_response_by_url.items():
            if key in url:
                resp.json = MagicMock(return_value=val)
                resp.status_code = 200
                return resp
        resp.json = MagicMock(return_value=self._post_response or {"errcode": 0, "errmsg": "ok"})
        resp.status_code = 200
        return resp


def _dummy_on_message(msg: Any) -> None:
    pass


# ─────────────────────────── WeCom ───────────────────────────

@pytest.fixture
def wecom_handler():
    from gateway.platforms.wecom import WeComHandler
    h = WeComHandler(
        corp_id="test_corp",
        agent_id="1000002",
        corp_secret="test_secret",
        token="test_token",
        encoding_aes_key=None,
        webhook_port=19000,
        on_message=_dummy_on_message,
    )
    h._started = False
    return h


@pytest.fixture
def mock_wecom_client():
    token_response = {"access_token": "fake_wecom_token", "expires_in": 7200}
    send_response = {"errcode": 0, "errmsg": "ok"}
    fake_client = FakeAsyncClient(
        get_response=token_response,
        post_response=send_response,
    )
    with patch("gateway.platforms.wecom.httpx.AsyncClient", return_value=fake_client):
        yield fake_client


class TestWeComHandler:
    """Cover WeComHandler methods by letting them execute with mocked HTTP."""

    def test_import_and_init(self, wecom_handler):
        assert wecom_handler.corp_id == "test_corp"
        assert wecom_handler.agent_id == "1000002"
        assert wecom_handler.name.value == "wecom"

    def test_check_dependencies(self):
        from gateway.platforms.wecom import check_wecom_dependencies
        result = check_wecom_dependencies()
        assert result is True

    @pytest.mark.asyncio
    async def test_refresh_token(self, wecom_handler, mock_wecom_client):
        await wecom_handler._refresh_token()
        assert wecom_handler._access_token == "fake_wecom_token"
        assert wecom_handler._token_expires_at > 0

    @pytest.mark.asyncio
    async def test_get_token_refreshes_if_none(self, wecom_handler, mock_wecom_client):
        wecom_handler._access_token = None
        token = await wecom_handler._get_token()
        assert token == "fake_wecom_token"

    @pytest.mark.asyncio
    async def test_get_token_cached(self, wecom_handler):
        wecom_handler._access_token = "cached_token"
        wecom_handler._token_expires_at = time_mod.time() + 1000
        token = await wecom_handler._get_token()
        assert token == "cached_token"

    @pytest.mark.asyncio
    async def test_send_success(self, wecom_handler, mock_wecom_client):
        wecom_handler._access_token = "fake_wecom_token"
        wecom_handler._token_expires_at = time_mod.time() + 1000
        msg = OutgoingMessage(
            platform=wecom_handler.name,
            chat_id="user1",
            text="hello",
        )
        result = await wecom_handler.send(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_group_chat_id(self, wecom_handler, mock_wecom_client):
        wecom_handler._access_token = "fake_wecom_token"
        wecom_handler._token_expires_at = time_mod.time() + 1000
        msg = OutgoingMessage(
            platform=wecom_handler.name,
            chat_id="R:group1",
            text="hello group",
        )
        result = await wecom_handler.send(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_no_token(self, wecom_handler):
        wecom_handler._access_token = None
        wecom_handler._token_expires_at = 0
        msg = OutgoingMessage(platform=wecom_handler.name, chat_id="user1", text="hi")
        result = await wecom_handler.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_http_error(self, wecom_handler):
        wecom_handler._access_token = "fake_wecom_token"
        wecom_handler._token_expires_at = time_mod.time() + 1000
        fake_client = FakeAsyncClient()
        async def bad_post(url, **kwargs):
            raise Exception("network error")
        fake_client.post = bad_post
        with patch("gateway.platforms.wecom.httpx.AsyncClient", return_value=fake_client):
            msg = OutgoingMessage(platform=wecom_handler.name, chat_id="user1", text="hi")
            result = await wecom_handler.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, wecom_handler):
        error_response = {"errcode": 40013, "errmsg": "invalid corpid"}
        fake_client = FakeAsyncClient(get_response=error_response)
        with patch("gateway.platforms.wecom.httpx.AsyncClient", return_value=fake_client):
            await wecom_handler._refresh_token()
        assert wecom_handler._access_token is None

    @pytest.mark.asyncio
    async def test_process_message_text(self, wecom_handler):
        msg = {
            "MsgType": "text",
            "Content": "hello from poll",
            "FromUserName": "user1",
            "ToUserName": "wecom_app",
            "MsgId": "msg_001",
            "createtime": "1717000000",
        }
        received = []
        wecom_handler.on_message = lambda m: received.append(m)
        await wecom_handler._process_message(msg)
        assert len(received) == 1
        assert received[0].text == "hello from poll"

    @pytest.mark.asyncio
    async def test_process_message_non_text(self, wecom_handler):
        msg = {"MsgType": "image", "FromUserName": "user1"}
        received = []
        wecom_handler.on_message = lambda m: received.append(m)
        await wecom_handler._process_message(msg)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_handle_callback_text(self, wecom_handler):
        body = json.dumps({
            "MsgType": "text",
            "Content": "hello callback",
            "FromUserName": "user1",
            "ToUserName": "wecom_app",
            "MsgId": "cb_001",
        })
        received = []
        wecom_handler.on_message = lambda m: received.append(m)
        await wecom_handler._handle_callback(body)
        assert len(received) == 1
        assert received[0].text == "hello callback"

    @pytest.mark.asyncio
    async def test_handle_callback_non_text(self, wecom_handler):
        body = json.dumps({"MsgType": "image", "FromUserName": "user1"})
        received = []
        wecom_handler.on_message = lambda m: received.append(m)
        await wecom_handler._handle_callback(body)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_handle_callback_invalid_json(self, wecom_handler):
        received = []
        wecom_handler.on_message = lambda m: received.append(m)
        await wecom_handler._handle_callback("not json")
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_start_stop_no_webhook(self, wecom_handler, mock_wecom_client):
        wecom_handler.encoding_aes_key = None
        await wecom_handler.start()
        assert wecom_handler._started is True
        await wecom_handler.stop()
        assert wecom_handler._started is False

    @pytest.mark.asyncio
    async def test_decrypt_no_key(self, wecom_handler):
        result = wecom_handler._decrypt("dummy")
        assert result is None


# ─────────────────────────── DingTalk ───────────────────────────

@pytest.fixture
def dingtalk_handler():
    from gateway.platforms.dingtalk import DingTalkHandler
    h = DingTalkHandler(
        app_key="test_key",
        app_secret="test_secret",
        token="test_token",
        aes_key=None,
        webhook_port=19001,
        on_message=_dummy_on_message,
    )
    h._started = False
    return h


@pytest.fixture
def mock_dingtalk_client():
    token_response = {"accessToken": "fake_dingtalk_token", "expireIn": 7200}
    send_response = {"errcode": 0, "errmsg": "ok", "task_id": 123}
    fake_client = FakeAsyncClient()
    async def smart_post(url, **kwargs):
        resp = MagicMock()
        if "accessToken" in url or "gettoken" in url:
            resp.json = MagicMock(return_value=token_response)
        else:
            resp.json = MagicMock(return_value=send_response)
        resp.status_code = 200
        return resp
    fake_client.post = smart_post
    fake_client.get = smart_post
    with patch("gateway.platforms.dingtalk.httpx.AsyncClient", return_value=fake_client):
        yield fake_client


class TestDingTalkHandler:
    def test_import_and_init(self, dingtalk_handler):
        assert dingtalk_handler.app_key == "test_key"
        assert dingtalk_handler.name.value == "dingtalk"

    @pytest.mark.asyncio
    async def test_refresh_token(self, dingtalk_handler, mock_dingtalk_client):
        await dingtalk_handler._refresh_token()
        assert dingtalk_handler._access_token == "fake_dingtalk_token"
        assert dingtalk_handler._token_expires_at > 0

    @pytest.mark.asyncio
    async def test_send_success(self, dingtalk_handler, mock_dingtalk_client):
        dingtalk_handler._access_token = "fake_dingtalk_token"
        dingtalk_handler._token_expires_at = time_mod.time() + 1000
        msg = OutgoingMessage(
            platform=dingtalk_handler.name,
            chat_id="user1",
            text="hello dingtalk",
        )
        result = await dingtalk_handler.send(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_no_token(self, dingtalk_handler):
        dingtalk_handler._access_token = None
        msg = OutgoingMessage(platform=dingtalk_handler.name, chat_id="user1", text="hi")
        result = await dingtalk_handler.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_callback_text(self, dingtalk_handler):
        body = json.dumps({
            "msgtype": "text",
            "text": {"content": "hello from dingtalk"},
            "senderStaffId": "staff1",
            "msgId": "dt_001",
        })
        received = []
        dingtalk_handler.on_message = lambda m: received.append(m)
        await dingtalk_handler._handle_callback(body)
        assert len(received) == 1
        assert "hello from dingtalk" in received[0].text

    @pytest.mark.asyncio
    async def test_handle_callback_non_text(self, dingtalk_handler):
        body = json.dumps({"msgtype": "picture", "text": {}})
        received = []
        dingtalk_handler.on_message = lambda m: received.append(m)
        await dingtalk_handler._handle_callback(body)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_handle_callback_invalid_json(self, dingtalk_handler):
        received = []
        dingtalk_handler.on_message = lambda m: received.append(m)
        await dingtalk_handler._handle_callback("not json")
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_start_stop_no_webhook(self, dingtalk_handler):
        dingtalk_handler.aes_key = None
        await dingtalk_handler.start()
        assert dingtalk_handler._started is True
        await dingtalk_handler.stop()
        assert dingtalk_handler._started is False

    @pytest.mark.asyncio
    async def test_get_token_refreshes_if_none(self, dingtalk_handler, mock_dingtalk_client):
        dingtalk_handler._access_token = None
        token = await dingtalk_handler._get_token()
        assert token == "fake_dingtalk_token"

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, dingtalk_handler):
        error_response = {"errcode": 88, "errmsg": "invalid secret"}
        fake_client = FakeAsyncClient(post_response=error_response)
        with patch("gateway.platforms.dingtalk.httpx.AsyncClient", return_value=fake_client):
            await dingtalk_handler._refresh_token()
        assert dingtalk_handler._access_token is None

    @pytest.mark.asyncio
    async def test_send_http_error(self, dingtalk_handler):
        dingtalk_handler._access_token = "fake_dingtalk_token"
        dingtalk_handler._token_expires_at = time_mod.time() + 1000
        fake_client = FakeAsyncClient()
        async def bad_post(url, **kwargs):
            raise Exception("network error")
        fake_client.post = bad_post
        with patch("gateway.platforms.dingtalk.httpx.AsyncClient", return_value=fake_client):
            msg = OutgoingMessage(platform=dingtalk_handler.name, chat_id="user1", text="hi")
            result = await dingtalk_handler.send(msg)
        assert result is False


# ─────────────────────────── Feishu ───────────────────────────

@pytest.fixture
def feishu_handler():
    from gateway.platforms.feishu import FeishuHandler
    h = FeishuHandler(
        app_id="cli_test_app_id",
        app_secret="test_feishu_secret",
        verify_token="test_vtoken",
        encrypt_key=None,
        on_message=_dummy_on_message,
    )
    h._started = False
    return h


class TestFeishuHandler:
    def test_import_and_init(self, feishu_handler):
        assert feishu_handler.app_id == "cli_test_app_id"
        assert feishu_handler.name.value == "feishu"

    @pytest.mark.asyncio
    async def test_refresh_token(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        token_response = {"code": 0, "tenant_access_token": "fake_feishu_token", "expire": 7200}
        fake_client = FakeAsyncClient(post_response=token_response)
        with patch("gateway.platforms.feishu.httpx.AsyncClient", return_value=fake_client):
            await h._refresh_token()
        assert h._tenant_access_token == "fake_feishu_token"

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        error_response = {"code": 99999, "msg": "invalid_app"}
        fake_client = FakeAsyncClient(post_response=error_response)
        with patch("gateway.platforms.feishu.httpx.AsyncClient", return_value=fake_client):
            await h._refresh_token()
        assert h._tenant_access_token is None

    @pytest.mark.asyncio
    async def test_send_success(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        h._tenant_access_token = "fake_feishu_token"
        h._token_expires_at = time_mod.time() + 1000
        send_response = {"code": 0, "data": {"message_id": "msg_abc"}}
        token_response = {"code": 0, "tenant_access_token": "fake_feishu_token", "expire": 7200}
        fake_client = FakeAsyncClient(
            post_response_by_url={
                "tenant_access_token": token_response,
                "im/v1/messages": send_response,
            }
        )
        with patch("gateway.platforms.feishu.httpx.AsyncClient", return_value=fake_client):
            msg = OutgoingMessage(platform=h.name, chat_id="ou_abc", text="hello feishu")
            result = await h.send(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_no_token(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        h._tenant_access_token = None
        msg = OutgoingMessage(platform=h.name, chat_id="ou_abc", text="hi")
        result = await h.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_http_error(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        h._tenant_access_token = "fake_feishu_token"
        h._token_expires_at = time_mod.time() + 1000
        fake_client = FakeAsyncClient()
        async def bad_post(url, **kwargs):
            raise Exception("network error")
        fake_client.post = bad_post
        with patch("gateway.platforms.feishu.httpx.AsyncClient", return_value=fake_client):
            msg = OutgoingMessage(platform=h.name, chat_id="ou_abc", text="hi")
            result = await h.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_error_response(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        h._tenant_access_token = "token"
        h._token_expires_at = time_mod.time() + 1000
        error_response = {"code": 99999, "msg": "error"}
        fake_client = FakeAsyncClient(post_response=error_response)
        with patch("gateway.platforms.feishu.httpx.AsyncClient", return_value=fake_client):
            msg = OutgoingMessage(platform=h.name, chat_id="ou_abc", text="hi")
            result = await h.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_message_text_p2p(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        msg = {
            "msg_type": "text",
            "body": {"content": '{"text":"hello feishu"}'},
            "sender": {"id": "u1"},
            "chat_type": "p2p",
            "message_id": "f_001",
            "chat_id": "oc_abc",
            "create_time": str(int(time_mod.time())),
        }
        received = []
        h.on_message = lambda m: received.append(m)
        await h._process_message(msg)
        assert len(received) == 1
        assert "hello feishu" in received[0].text

    @pytest.mark.asyncio
    async def test_process_message_non_p2p_ignored(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        msg = {
            "msg_type": "text",
            "body": {"content": '{"text":"hi"}'},
            "sender": {"id": "u1"},
            "chat_type": "group",
            "message_id": "f_002",
        }
        received = []
        h.on_message = lambda m: received.append(m)
        await h._process_message(msg)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_process_message_non_text_ignored(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        msg = {
            "msg_type": "image",
            "body": {},
            "sender": {"id": "u1"},
            "chat_type": "p2p",
        }
        received = []
        h.on_message = lambda m: received.append(m)
        await h._process_message(msg)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_process_message_group(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        msg = {
            "msg_type": "text",
            "body": {"content": '{"text":"hi"}'},
            "sender": {"id": "u1"},
            "chat_type": "group",
            "message_id": "f_group",
        }
        received = []
        h.on_message = lambda m: received.append(m)
        await h._process_message(msg)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_process_message_missing_sender(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", on_message=_dummy_on_message)
        msg = {
            "msg_type": "text",
            "body": {"content": '{"text":"hi"}'},
            "chat_type": "p2p",
            "message_id": "f_nosender",
        }
        received = []
        h.on_message = lambda m: received.append(m)
        await h._process_message(msg)
        assert len(received) == 1
        assert received[0].user_id == ""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        from gateway.platforms.feishu import FeishuHandler
        h = FeishuHandler(app_id="id", app_secret="secret", encrypt_key=None, on_message=_dummy_on_message)
        h._started = False
        await h.start()
        assert h._started is True
        await h.stop()
        assert h._started is False


# ─────────────────────────── Base Classes ───────────────────────────

class TestBaseClasses:
    """Cover gateway/platforms/base.py classes."""

    def test_incoming_message_init(self):
        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="u1",
            chat_id="chat1",
            text="hello",
            raw={"MsgType": "text", "FromUserName": "u1"},
        )
        assert msg.platform == Platform.TELEGRAM
        assert msg.user_id == "u1"
        assert msg.text == "hello"
        assert msg.reply_to is None

    def test_incoming_message_reply_to(self):
        msg = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id="u1",
            chat_id="chat1",
            text="reply",
            raw={},
            reply_to="m_orig",
        )
        assert msg.reply_to == "m_orig"

    def test_outgoing_message_init(self):
        msg = OutgoingMessage(
            platform=Platform.TELEGRAM,
            chat_id="ou_abc",
            text="reply",
        )
        assert msg.platform == Platform.TELEGRAM
        assert msg.chat_id == "ou_abc"
        assert msg.reply_to is None
        assert msg.parse_mode == "markdown"

    def test_outgoing_message_reply(self):
        msg = OutgoingMessage(
            platform=Platform.TELEGRAM,
            chat_id="u1",
            text="reply",
            reply_to="m_orig",
        )
        assert msg.reply_to == "m_orig"

    def test_platform_enum(self):
        assert Platform.TELEGRAM.value == "telegram"
        assert Platform.DISCORD.value == "discord"
        assert Platform.WHATSAPP.value == "whatsapp"
        assert Platform.SLACK.value == "slack"
        assert Platform.WECHAT.value == "wechat"

    @pytest.mark.asyncio
    async def test_platform_handler_abstract(self):
        """PlatformHandler is abstract, cannot instantiate."""
        with pytest.raises(TypeError):
            PlatformHandler(on_message=_dummy_on_message)
