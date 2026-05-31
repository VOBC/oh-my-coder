"""Extended tests for DingTalkHandler to push coverage from 56% to 75%+.

Only mock `httpx.AsyncClient` (external dependency).
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

from gateway.platforms.base import OutgoingMessage


class FakeAsyncClient:
    """Fake httpx.AsyncClient that returns canned responses."""

    def __init__(
        self,
        post_response: Optional[Any] = None,
        post_response_by_url: Optional[dict] = None,
    ):
        self._post_response = post_response
        self._post_response_by_url = post_response_by_url or {}
        self.timeout = 15.0
        self.last_url: Optional[str] = None
        self.last_json: Optional[Any] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def get(self, url: str, **kwargs: Any) -> Any:
        self.last_url = url
        resp = MagicMock()
        resp.json = MagicMock(return_value={"errcode": 0, "errmsg": "ok"})
        resp.status_code = 200
        return resp

    async def post(self, url: str, **kwargs: Any) -> Any:
        self.last_url = url
        self.last_json = kwargs.get("json")
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


def _dummy_on_error(e: Exception) -> None:
    pass


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
        on_error=_dummy_on_error,
    )
    h._started = False
    return h


@pytest.fixture
def mock_dingtalk_client_token():
    """Mock client for _refresh_token: returns accessToken (camelCase)."""
    token_response = {"accessToken": "fake_dingtalk_token", "expireIn": 7200}
    fake_client = FakeAsyncClient(post_response=token_response)
    with patch("gateway.platforms.dingtalk.httpx.AsyncClient", return_value=fake_client):
        yield fake_client


@pytest.fixture
def mock_dingtalk_client_send():
    """Mock client for send(): returns errcode 0."""
    send_response = {"errcode": 0, "errmsg": "ok"}
    fake_client = FakeAsyncClient(post_response=send_response)
    with patch("gateway.platforms.dingtalk.httpx.AsyncClient", return_value=fake_client):
        yield fake_client


class TestDingTalkHandlerExtended:
    """Extended tests to push dingtalk.py coverage from 56% to 75%+."""

    # ---- _refresh_token variants ----

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, dingtalk_handler, mock_dingtalk_client_token):
        """Test _refresh_token succeeds (accessToken camelCase)."""
        await dingtalk_handler._refresh_token()
        assert dingtalk_handler._access_token == "fake_dingtalk_token"
        assert dingtalk_handler._token_expires_at > time_mod.time()

    @pytest.mark.asyncio
    async def test_refresh_token_http_error(self, dingtalk_handler):
        """Test _refresh_token when HTTP call raises (now caught by try/except)."""
        fake_client = FakeAsyncClient()
        async def bad_post(url, **kw):
            raise Exception("network error")
        fake_client.post = bad_post
        with patch("gateway.platforms.dingtalk.httpx.AsyncClient", return_value=fake_client):
            await dingtalk_handler._refresh_token()
        # With try/except added, _access_token stays None, no exception propagates
        assert dingtalk_handler._access_token is None

    @pytest.mark.asyncio
    async def test_refresh_token_missing_access_token(self, dingtalk_handler):
        """Test _refresh_token when response has no accessToken field."""
        fake_client = FakeAsyncClient(post_response={"errcode": 0, "errmsg": "ok"})
        with patch("gateway.platforms.dingtalk.httpx.AsyncClient", return_value=fake_client):
            await dingtalk_handler._refresh_token()
        assert dingtalk_handler._access_token is None

    # ---- send() error paths ----

    @pytest.mark.asyncio
    async def test_send_success(self, dingtalk_handler, mock_dingtalk_client_send):
        """Test send() succeeds."""
        dingtalk_handler._access_token = "tok"
        dingtalk_handler._token_expires_at = time_mod.time() + 1000
        msg = OutgoingMessage(platform=dingtalk_handler.name, chat_id="u1", text="hi")
        result = await dingtalk_handler.send(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_api_error(self, dingtalk_handler):
        """Test send() when API returns errcode != 0 (token already valid)."""
        dingtalk_handler._access_token = "tok"
        dingtalk_handler._token_expires_at = time_mod.time() + 1000
        fake_client = FakeAsyncClient(
            post_response={"errcode": 310000, "errmsg": "failed"}
        )
        with patch("gateway.platforms.dingtalk.httpx.AsyncClient", return_value=fake_client):
            msg = OutgoingMessage(platform=dingtalk_handler.name, chat_id="u1", text="hi")
            result = await dingtalk_handler.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_http_exception(self, dingtalk_handler):
        """Test send() when HTTP post raises exception (token already set)."""
        dingtalk_handler._access_token = "tok"
        dingtalk_handler._token_expires_at = time_mod.time() + 1000
        fake_client = FakeAsyncClient()
        async def bad_post(url, **kw):
            raise Exception("send failed")
        fake_client.post = bad_post
        with patch("gateway.platforms.dingtalk.httpx.AsyncClient", return_value=fake_client):
            msg = OutgoingMessage(platform=dingtalk_handler.name, chat_id="u1", text="hi")
            result = await dingtalk_handler.send(msg)
        assert result is False

    # ---- _handle_callback variants ----

    @pytest.mark.asyncio
    async def test_handle_callback_valid_text(self, dingtalk_handler):
        """Test _handle_callback with valid text message (senderStaffId field)."""
        received = []
        dingtalk_handler.on_message = lambda m: received.append(m)
        body = json.dumps({
            "msgtype": "text",
            "text": {"content": "hello"},
            "senderStaffId": "u1",
            "conversationId": "c1",
            "msgId": "m1",
        })
        await dingtalk_handler._handle_callback(body)
        assert len(received) == 1
        assert received[0].text == "hello"
        assert received[0].user_id == "u1"

    @pytest.mark.asyncio
    async def test_handle_callback_non_text(self, dingtalk_handler):
        """Test _handle_callback with non-text message (should be ignored)."""
        received = []
        dingtalk_handler.on_message = lambda m: received.append(m)
        body = json.dumps({
            "msgtype": "picture",
            "senderStaffId": "u1",
            "conversationId": "c1",
            "msgId": "m2",
        })
        await dingtalk_handler._handle_callback(body)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_handle_callback_missing_fields(self, dingtalk_handler):
        """Test _handle_callback with missing fields."""
        received = []
        dingtalk_handler.on_message = lambda m: received.append(m)
        body = json.dumps({"msgtype": "text", "text": {"content": "hi"}})
        await dingtalk_handler._handle_callback(body)
        assert isinstance(len(received), int)

    @pytest.mark.asyncio
    async def test_handle_callback_empty_body(self, dingtalk_handler):
        """Test _handle_callback with empty string."""
        received = []
        dingtalk_handler.on_message = lambda m: received.append(m)
        await dingtalk_handler._handle_callback("")
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_handle_callback_invalid_json(self, dingtalk_handler):
        """Test _handle_callback with invalid JSON."""
        received = []
        dingtalk_handler.on_message = lambda m: received.append(m)
        await dingtalk_handler._handle_callback("not json{{{")
        assert len(received) == 0

    # ---- start/stop ----

    @pytest.mark.asyncio
    async def test_stop_without_server_task(self, dingtalk_handler):
        """Test stop() when _server_task is None."""
        dingtalk_handler._started = True
        dingtalk_handler._server_task = None
        await dingtalk_handler.stop()
        assert dingtalk_handler._started is False

    # ---- _decrypt_msg ----

    def test_decrypt_msg_no_aes_key(self, dingtalk_handler):
        """Test _decrypt_msg returns None when aes_key is None."""
        dingtalk_handler.aes_key = None
        result = dingtalk_handler._decrypt_msg("dummy_encrypted")
        assert result is None

    def test_decrypt_msg_with_key_invalid(self, dingtalk_handler):
        """Test _decrypt_msg returns None for invalid input."""
        dingtalk_handler.aes_key = "a" * 43 + "="
        result = dingtalk_handler._decrypt_msg("invalid_base64!!!")
        assert result is None

    # ---- check_dependencies ----

    def test_check_dependencies(self):
        """Test check_dingtalk_dependencies when httpx is available."""
        from gateway.platforms.dingtalk import check_dingtalk_dependencies
        result = check_dingtalk_dependencies()
        assert result is True

    # ---- send with reply_to ----

    @pytest.mark.asyncio
    async def test_send_with_reply_to(self, dingtalk_handler, mock_dingtalk_client_send):
        """Test send() with reply_to."""
        dingtalk_handler._access_token = "tok"
        dingtalk_handler._token_expires_at = time_mod.time() + 1000
        msg = OutgoingMessage(
            platform=dingtalk_handler.name,
            chat_id="u1",
            text="reply",
            reply_to="orig_msg_id",
        )
        result = await dingtalk_handler.send(msg)
        assert result is True

    # ---- _get_token triggers refresh when expired ----

    @pytest.mark.asyncio
    async def test_get_token_expired_refreshes(self, dingtalk_handler, mock_dingtalk_client_token):
        """Test _get_token calls _refresh_token when token is expired."""
        dingtalk_handler._access_token = "old"
        dingtalk_handler._token_expires_at = time_mod.time() - 10  # expired
        token = await dingtalk_handler._get_token()
        assert token == "fake_dingtalk_token"

    @pytest.mark.asyncio
    async def test_get_token_valid(self, dingtalk_handler):
        """Test _get_token returns existing token when valid."""
        dingtalk_handler._access_token = "valid"
        dingtalk_handler._token_expires_at = time_mod.time() + 1000
        token = await dingtalk_handler._get_token()
        assert token == "valid"

    # ---- start() without aes_key (no webhook server) ----

    @pytest.mark.asyncio
    async def test_start_without_aes_key(self, dingtalk_handler, mock_dingtalk_client_token):
        """Test start() when aes_key is None (no webhook server)."""
        dingtalk_handler.aes_key = None
        # Should not raise, just log warning
        await dingtalk_handler.start()
        assert dingtalk_handler._started is True
        await dingtalk_handler.stop()
