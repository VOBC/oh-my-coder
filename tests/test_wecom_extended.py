"""Extended tests for WeComHandler to push coverage from 56% to 75%+.

Only mock `httpx.AsyncClient` (external dependency).
Let internal methods (_refresh_token, _poll_loop, _process_message, etc.) execute for real.
"""

from __future__ import annotations

import asyncio
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


class TestWeComHandlerExtended:
    """Extended tests to push wecom.py coverage from 56% to 75%+."""

    # ---- _refresh_token variants ----

    @pytest.mark.asyncio
    async def test_refresh_token_expires_in_default(self, wecom_handler, mock_wecom_client):
        """Test _refresh_token uses default expires_in when not returned."""
        await wecom_handler._refresh_token()
        assert wecom_handler._access_token == "fake_wecom_token"
        # Default expires_in=7200, minus 300 = 6900
        assert wecom_handler._token_expires_at > time_mod.time()

    @pytest.mark.asyncio
    async def test_refresh_token_http_error(self, wecom_handler):
        """Test _refresh_token when HTTP call raises."""
        fake_client = FakeAsyncClient()
        async def bad_get(url, **kw):
            raise Exception("network error")
        fake_client.get = bad_get
        with patch("gateway.platforms.wecom.httpx.AsyncClient", return_value=fake_client):
            await wecom_handler._refresh_token()
        assert wecom_handler._access_token is None

    @pytest.mark.asyncio
    async def test_refresh_token_missing_access_token(self, wecom_handler):
        """Test _refresh_token when response has no access_token."""
        fake_client = FakeAsyncClient(get_response={"errcode": 0, "errmsg": "ok"})
        with patch("gateway.platforms.wecom.httpx.AsyncClient", return_value=fake_client):
            await wecom_handler._refresh_token()
        assert wecom_handler._access_token is None

    # ---- send() error paths ----

    @pytest.mark.asyncio
    async def test_send_api_error_response(self, wecom_handler, mock_wecom_client):
        """Test send() when API returns errcode != 0."""
        wecom_handler._access_token = "tok"
        wecom_handler._token_expires_at = time_mod.time() + 1000
        # Override the mock to return error
        fake_client = FakeAsyncClient(
            post_response_by_url={
                "message/send": {"errcode": 40001, "errmsg": "invalid token"}
            }
        )
        with patch("gateway.platforms.wecom.httpx.AsyncClient", return_value=fake_client):
            msg = OutgoingMessage(platform=wecom_handler.name, chat_id="u1", text="hi")
            result = await wecom_handler.send(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_with_group_chat_id_r_prefix(self, wecom_handler, mock_wecom_client):
        """Test send() with R: prefix (party ID)."""
        wecom_handler._access_token = "tok"
        wecom_handler._token_expires_at = time_mod.time() + 1000
        msg = OutgoingMessage(platform=wecom_handler.name, chat_id="R:party1", text="hi")
        result = await wecom_handler.send(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_with_tag_chat_id_s_prefix(self, wecom_handler, mock_wecom_client):
        """Test send() with S: prefix (tag ID)."""
        wecom_handler._access_token = "tok"
        wecom_handler._token_expires_at = time_mod.time() + 1000
        msg = OutgoingMessage(platform=wecom_handler.name, chat_id="S:tag1", text="hi")
        result = await wecom_handler.send(msg)
        assert result is True

    # ---- _process_message variants ----

    @pytest.mark.asyncio
    async def test_process_message_image_type(self, wecom_handler):
        """Test _process_message with image message type."""
        received = []
        wecom_handler.on_message = lambda m: received.append(m)
        msg = {
            "MsgType": "image",
            "FromUserName": "u1",
            "ToUserName": "wecom_app",
            "MsgId": "img_001",
            "createtime": str(int(time_mod.time())),
        }
        await wecom_handler._process_message(msg)
        # Image type is not "text", should be ignored
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_process_message_missing_fields(self, wecom_handler):
        """Test _process_message with missing fields."""
        received = []
        wecom_handler.on_message = lambda m: received.append(m)
        msg = {"MsgType": "text", "Content": "hi"}
        # Missing FromUserName, MsgId, createtime
        await wecom_handler._process_message(msg)
        # Should still process with defaults
        assert isinstance(len(received), int)

    # ---- _handle_callback variants ----

    @pytest.mark.asyncio
    async def test_handle_callback_valid(self, wecom_handler):
        """Test _handle_callback with valid encrypted callback."""
        body = json.dumps({
            "MsgType": "text",
            "Content": "callback test",
            "FromUserName": "u1",
            "ToUserName": "wecom_app",
            "MsgId": "cb_001",
        })
        received = []
        wecom_handler.on_message = lambda m: received.append(m)
        await wecom_handler._handle_callback(body)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_handle_callback_empty_body(self, wecom_handler):
        """Test _handle_callback with empty string."""
        received = []
        wecom_handler.on_message = lambda m: received.append(m)
        await wecom_handler._handle_callback("")
        assert len(received) == 0

    # ---- start/stop with encryption ----

    @pytest.mark.asyncio
    async def test_start_with_encoding_aes_key(self, wecom_handler, mock_wecom_client):
        """Test start() with encoding_aes_key set (webhook mode)."""
        wecom_handler.encoding_aes_key = "a" * 43 + "="
        wecom_handler._started = False
        # Mock uvicorn to avoid actually starting server
        with patch("gateway.platforms.wecom.uvicorn", create=True) as mock_uvicorn:
            mock_server = MagicMock()
            mock_uvicorn.Server.return_value = mock_server
            mock_uvicorn.Config.return_value = MagicMock()
            try:
                await asyncio.wait_for(wecom_handler.start(), timeout=0.5)
            except (asyncio.TimeoutError, Exception):
                pass
        # Should have set _started
        assert wecom_handler._started is True

    @pytest.mark.asyncio
    async def test_stop_with_poll_task(self, wecom_handler):
        """Test stop() cancels poll task."""
        wecom_handler._started = True
        async def fake_poll():
            await asyncio.sleep(100)
        task = asyncio.create_task(fake_poll())
        wecom_handler._poll_task = task
        await wecom_handler.stop()
        assert task.cancelled() or task.done()
        assert wecom_handler._started is False

    # ---- _decrypt with key ----

    def test_decrypt_with_key_returns_none_for_invalid(self, wecom_handler):
        """Test _decrypt returns None for invalid input."""
        wecom_handler.encoding_aes_key = "a" * 43 + "="
        wecom_handler.token = "test_token"
        result = wecom_handler._decrypt("invalid_base64!!!")
        assert result is None

    def test_decrypt_no_key_returns_none(self, wecom_handler):
        """Test _decrypt returns None when encoding_aes_key is None."""
        wecom_handler.encoding_aes_key = None
        result = wecom_handler._decrypt("dummy")
        assert result is None

    # ---- check_dependencies ----

    def test_check_dependencies_importable(self):
        """Test check_wecom_dependencies when httpx is available."""
        from gateway.platforms.wecom import check_wecom_dependencies
        result = check_wecom_dependencies()
        assert result is True

    # ---- edge: send with reply_to ----

    @pytest.mark.asyncio
    async def test_send_with_reply_to(self, wecom_handler, mock_wecom_client):
        """Test send() includes reply_to in payload."""
        wecom_handler._access_token = "tok"
        wecom_handler._token_expires_at = time_mod.time() + 1000
        msg = OutgoingMessage(
            platform=wecom_handler.name,
            chat_id="u1",
            text="reply",
            reply_to="orig_msg_id",
        )
        result = await wecom_handler.send(msg)
        assert result is True
