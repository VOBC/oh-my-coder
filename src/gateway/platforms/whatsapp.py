"""
WhatsApp Business Cloud API 平台处理器

支持 WhatsApp Business Cloud API（官方 API，无需第三方中间件）。
支持：消息接收（Webhook）、消息发送。

文档：https://developers.facebook.com/docs/whatsapp/cloud-api
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from ..base import IncomingMessage, OutgoingMessage, Platform, PlatformHandler

logger = logging.getLogger(__name__)

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    logger.warning("httpx not installed. WhatsApp support requires: pip install httpx")

try:
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse, PlainTextResponse
    from starlette.routing import Route

    _HAS_STARLETTE = True
except ImportError:
    _HAS_STARLETTE = False
    logger.warning(
        "starlette not installed. WhatsApp support requires: pip install starlette"
    )


# WhatsApp Cloud API 端点模板
_WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"


class WhatsAppHandler(PlatformHandler):
    """
    WhatsApp Business Cloud API 处理器

    接收 Webhook 事件 → 转为 IncomingMessage → 传给 on_message
    发送消息 → WhatsApp Send API

    环境变量配置：
        WHATSAPP_PHONE_NUMBER_ID   - 电话号码 ID（From 号码）
        WHATSAPP_WEBHOOK_URL       - Webhook 基础 URL（不含路径）
        WHATSAPP_WEBHOOK_PORT      - 本地监听端口（默认 8080）
        WHATSAPP_VERIFY_TOKEN      - 验证 Token（自己生成）
        WHATSAPP_ACCESS_TOKEN      - Long-lived Access Token

    本地运行后需将 http://<your-host>:<port>/webhook/whatsapp 注册到 Meta Webhook。
    """

    name = Platform.WHATSAPP

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        webhook_url: str,
        verify_token: Optional[str] = None,
        webhook_port: int = 8080,
        **kwargs,
    ):
        """
        Args:
            phone_number_id: WhatsApp 商业电话号码 ID（From 号码）
            access_token: Meta App Access Token（Long-lived）
            webhook_url: 你的服务器公网 URL（用于注册 Webhook）
            verify_token: Webhook 验证 Token（自己生成，用于校验 Meta 的验证请求）
            webhook_port: 本地 Webhook 监听端口
        """
        super().__init__(**kwargs)
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.webhook_url = webhook_url.rstrip("/")
        self.verify_token = verify_token or os.environ.get(
            "WHATSAPP_VERIFY_TOKEN", "oh-my-coder-verify"
        )
        self.webhook_port = webhook_port
        self._app: Any = None
        self._server_task: Optional[asyncio.Task[None]] = None

    # ---- PlatformHandler 实现 ----

    async def start(self) -> None:
        if not _HAS_STARLETTE:
            raise RuntimeError("starlette 未安装。运行: pip install starlette httpx")

        if not _HAS_HTTPX:
            raise RuntimeError("httpx 未安装。运行: pip install httpx")

        # 构建 Webhook 路由
        async def webhookGET(request: Request) -> PlainTextResponse:
            """Meta Webhook 验证（GET）"""
            mode = request.query_params.get("hub.mode")
            token = request.query_params.get("hub.verify_token")
            challenge = request.query_params.get("hub.challenge")

            if mode == "subscribe" and token == self.verify_token:
                logger.info("[whatsapp] Webhook verified successfully")
                return PlainTextResponse(content=challenge or "OK")
            logger.warning(
                f"[whatsapp] Webhook verify failed: mode={mode}, token={token}"
            )
            return PlainTextResponse(content="Invalid verify", status_code=403)

        async def webhookPOST(request: Request) -> JSONResponse:
            """接收 WhatsApp 消息事件"""
            body = await request.json()
            await self._handle_webhook_event(body)
            return JSONResponse(content={"status": "ok"})

        self._app = Starlette(
            routes=[
                Route("/webhook/whatsapp", webhookPOST, methods=["POST"]),
                Route("/webhook/whatsapp", webhookGET, methods=["GET"]),
            ]
        )

        # 启动后台 HTTP 服务器
        import uvicorn

        config = uvicorn.Config(
            self._app,
            host="127.0.0.1",  # nosec B104
            port=self.webhook_port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        self._server_task = asyncio.create_task(server.serve())
        self._started = True
        logger.info(
            f"[whatsapp] Handler started. "
            f"Register webhook URL: {self.webhook_url}/webhook/whatsapp"
        )
        logger.info(
            f"[whatsapp] Verify token: {self.verify_token} "
            f"(used when subscribing webhook in Meta Developer Console)"
        )

    async def stop(self) -> None:
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
        self._started = False
        logger.info("[whatsapp] Handler stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        """通过 WhatsApp Cloud API 发送消息"""
        if not _HAS_HTTPX:
            return False

        url = f"{_WHATSAPP_API_URL}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": message.chat_id,
            "type": "text",
            "text": {"body": message.text[:4096]},  # WhatsApp 限制 4096 字符
        }
        if message.reply_to:
            payload["context"] = {"message_id": message.reply_to}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    return True
                logger.error(f"[whatsapp] Send failed: {resp.status_code} {resp.text}")
                self.on_error(Exception(f"HTTP {resp.status_code}"))
                return False
        except Exception as e:
            logger.error(f"[whatsapp] Send error: {e}")
            self.on_error(e)
            return False

    # ---- 内部处理 ----

    async def _handle_webhook_event(self, body: Dict[str, Any]) -> None:
        """处理 WhatsApp Webhook 事件"""
        try:
            entries = body.get("entry", [])
            for entry in entries:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" not in value:
                        continue

                    for msg in value.get("messages", []):
                        await self._process_message(msg, value)

        except Exception as e:
            logger.error(f"[whatsapp] Webhook parse error: {e}")
            self.on_error(e)

    async def _process_message(
        self, msg: Dict[str, Any], value: Dict[str, Any]
    ) -> None:
        """处理单条消息"""
        msg_type = msg.get("type")
        if msg_type != "text":
            logger.debug(f"[whatsapp] Unsupported message type: {msg_type}")
            return

        text = msg.get("text", {}).get("body", "")
        if not text:
            return

        from_id = msg.get("from", "")
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id", "")

        incoming = IncomingMessage(
            platform=Platform.WHATSAPP,
            user_id=from_id,
            chat_id=from_id,  # WhatsApp 一对一/群组 ID
            text=text,
            raw={
                "message_id": msg.get("id", ""),
                "timestamp": msg.get("timestamp", ""),
                "from": from_id,
                "phone_number_id": phone_number_id,
                "profile_name": value.get("contacts", [{}])[0]
                .get("profile", {})
                .get("name", ""),
            },
            reply_to=msg.get("id", ""),
        )

        try:
            self.on_message(incoming)
        except Exception as e:
            logger.error(f"[whatsapp] on_message error: {e}")
            self.on_error(e)


def check_whatsapp_dependencies() -> bool:
    """检查 WhatsApp 依赖是否满足"""
    if not _HAS_HTTPX:
        logger.error("httpx 未安装: pip install httpx")
        return False
    if not _HAS_STARLETTE:
        logger.error("starlette 未安装: pip install starlette")
        return False
    return True
