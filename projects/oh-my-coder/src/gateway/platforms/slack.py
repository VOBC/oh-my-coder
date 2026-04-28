"""
Slack 平台处理器

支持 Slack Bot（Events API + Web API）。
支持：文本消息、回复、块消息（Block Kit）、线程。

文档：https://api.slack.com/apis/connected
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from ..base import IncomingMessage, OutgoingMessage, Platform, PlatformHandler

if TYPE_CHECKING:
    from starlette.requests import Request

logger = logging.getLogger(__name__)

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    logger.warning("httpx not installed. Slack 支持需要: pip install httpx")


class SlackHandler(PlatformHandler):
    """
    Slack Bot 处理器

    通过 HTTP Webhook（Events API）接收消息。
    通过 Slack Web API 发送消息。

    环境变量：
        SLACK_BOT_TOKEN       - xoxb-... Bot User OAuth Token
        SLACK_SIGNING_SECRET  - Slack Signing Secret（用于验证请求来源）
        SLACK_APP_TOKEN       - xapp-... App-Level Token（需要 channels:history scope）
        SLACK_WEBHOOK_PORT    - 本地 Webhook 监听端口（默认 8080）

    需要在 Slack App 配置：
    1. Event Subscriptions → Enable Events → Request URL
    2. Bot Token Scopes: chat:write, channels:history, im:history, groups:history
    3. Subscribe to: message.im, message.channels, message.groups
    """

    name = Platform.SLACK

    def __init__(
        self,
        bot_token: str,
        signing_secret: str,
        app_token: str | None = None,
        webhook_port: int = 8080,
        **kwargs,
    ):
        """
        Args:
            bot_token: xoxb-... Bot User OAuth Token
            signing_secret: Slack Signing Secret（从 Basic Information 获取）
            app_token: xapp-... App-Level Token（Socket Mode 需要）
            webhook_port: 本地 Webhook 监听端口
        """
        super().__init__(**kwargs)
        self.bot_token = bot_token
        self.signing_secret = signing_secret
        self.app_token = app_token
        self.webhook_port = webhook_port
        self._server_task: asyncio.Task[None] | None = None

    # ---- PlatformHandler 实现 ----

    async def start(self) -> None:
        if not _HAS_HTTPX:
            raise RuntimeError("httpx 未安装。运行: pip install httpx")

        self._server_task = asyncio.create_task(self._run_webhook_server())
        self._started = True
        logger.info(
            f"[slack] Handler started. "
            f"Register webhook URL: http://<your-host>:{self.webhook_port}/webhook/slack"
        )

    async def stop(self) -> None:
        if self._server_task:
            self._server_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._server_task
        self._started = False
        logger.info("[slack] Handler stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        """发送消息到 Slack"""
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "channel": message.chat_id,
            "text": message.text[:3000],  # Slack 限制
        }

        if message.reply_to:
            payload["thread_ts"] = message.reply_to

        if message.parse_mode == "blocks":
            payload["blocks"] = message.extra.get("blocks", [])

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                data = resp.json()
                if data.get("ok"):
                    return True
                logger.error(f"[slack] Send failed: {data.get('error')}")
                self.on_error(Exception(data.get("error", "unknown")))
                return False
        except Exception as e:
            logger.exception(f"[slack] Send error: {e}")
            self.on_error(e)
            return False

    # ---- 内部实现 ----

    async def _run_webhook_server(self) -> None:
        """运行 HTTP 服务器接收 Slack 事件"""
        try:
            import uvicorn
            from starlette.applications import Starlette
            from starlette.responses import JSONResponse, PlainTextResponse
            from starlette.routing import Route
        except Exception as e:
            logger.exception(f"[slack] Failed to start webhook server: {e}")
            return

        async def eventsPOST(request: Request) -> JSONResponse:
            """接收 Slack 事件"""
            body = await request.json()
            await self._handle_event(body)
            return JSONResponse(content={"status": "ok"})

        async def oauthGET(request: Request) -> PlainTextResponse:
            """Slack URL 验证"""
            return PlainTextResponse("OK")

        app = Starlette(
            routes=[
                Route("/webhook/slack", eventsPOST, methods=["POST"]),
                Route("/webhook/slack", oauthGET, methods=["GET"]),
            ]
        )
        config = uvicorn.Config(
            app,
            host="127.0.0.1",  # nosec B104 port=self.webhook_port, log_level="warning"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def _handle_event(self, body: dict[str, Any]) -> None:
        """处理 Slack 事件"""
        # URL 验证
        if "challenge" in body:
            logger.debug("[slack] URL verification challenge received")
            return

        # 处理事件列表
        events = body.get("event", {})
        event_type = events.get("type", "")

        # 处理消息事件
        if event_type in ("message", "app_mention"):
            await self._process_message(events)

        # 处理事件回调（异步模式）
        for item in body.get("event_callbacks", []):
            evt = item.get("event", {})
            if evt.get("type") == "message":
                await self._process_message(evt)

    async def _process_message(self, event: dict[str, Any]) -> None:
        """处理 Slack 消息事件"""
        # 忽略机器人自己的消息
        if event.get("subtype") == "bot_message":
            return
        if event.get("bot_id"):
            return

        text = event.get("text", "")
        if not text:
            return

        user_id = event.get("user", "")
        chat_id = event.get("channel", "")
        thread_ts = event.get("thread_ts", "") or event.get("ts", "")

        incoming = IncomingMessage(
            platform=Platform.SLACK,
            user_id=user_id,
            chat_id=chat_id,
            text=text,
            raw={
                "event_ts": event.get("ts", ""),
                "thread_ts": thread_ts,
                "channel_type": event.get("channel_type", "channel"),
                "team": event.get("team", ""),
            },
            reply_to=thread_ts if thread_ts != event.get("ts", "") else None,
        )

        try:
            self.on_message(incoming)
        except Exception as e:
            logger.exception(f"[slack] on_message error: {e}")
            self.on_error(e)


def check_slack_dependencies() -> bool:
    if not _HAS_HTTPX:
        logger.error("httpx 未安装: pip install httpx")
        return False
    return True
