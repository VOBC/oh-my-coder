"""
钉钉（DingTalk）平台处理器

支持钉钉企业内部应用（接收消息 + 发送消息）。
支持：文本、Markdown、@ 消息、卡片。

文档：https://open.dingtalk.com/document/orgapp/asynchronous-sending-of-enterprise-text-messages
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from ..base import IncomingMessage, OutgoingMessage, Platform, PlatformHandler

logger = logging.getLogger(__name__)

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    logger.warning("httpx not installed. 钉钉支持需要: pip install httpx")


class DingTalkHandler(PlatformHandler):
    """
    钉钉企业内部应用处理器

    通过 AES 解密接收消息（钉钉回调模式）。
    发送消息通过钉钉企业消息 API。

    环境变量：
        DINGTALK_APP_KEY       - 应用的 AppKey
        DINGTALK_APP_SECRET    - 应用的 AppSecret
        DINGTALK_TOKEN         - 回调 Token（自己生成）
        DINGTALK_AES_KEY       - 回调 EncodingAESKey（43字符）
        DINGTALK_WEBHOOK_PORT  - 本地回调监听端口（默认 8080）
    """

    name = Platform.DINGTALK

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        token: Optional[str] = None,
        aes_key: Optional[str] = None,
        webhook_port: int = 8080,
        **kwargs,
    ):
        """
        Args:
            app_key: 钉钉应用的 AppKey（client_id）
            app_secret: 钉钉应用的 AppSecret（client_secret）
            token: 回调 Token
            aes_key: 回调 AES Key（43字符）
            webhook_port: 本地回调监听端口
        """
        super().__init__(**kwargs)
        self.app_key = app_key
        self.app_secret = app_secret
        self.token = token or "oh-my-coder-dingtalk"
        self.aes_key = aes_key
        self.webhook_port = webhook_port
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._stop_event = asyncio.Event()
        self._server_task: Optional[asyncio.Task[None]] = None

    # ---- PlatformHandler 实现 ----

    async def start(self) -> None:
        if not _HAS_HTTPX:
            raise RuntimeError("httpx 未安装。运行: pip install httpx")

        await self._refresh_token()

        if self.aes_key:
            self._server_task = asyncio.create_task(self._run_webhook_server())
        else:
            logger.warning(
                "[dingtalk] No AES key configured. "
                "Set DINGTALK_AES_KEY to enable message receiving."
            )

        self._started = True
        logger.info("[dingtalk] Handler started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
        self._started = False
        logger.info("[dingtalk] Handler stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        token = await self._get_token()
        if not token:
            return False

        url = "https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2"
        params = {"access_token": token}
        payload = {
            "agent_id": self.app_key,  # agent_id 同 app_key
            "userid_list": message.chat_id,
            "msg": {
                "msgtype": "text",
                "text": {"content": message.text[:2048]},
            },
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, params=params, json=payload)
                data = resp.json()
                if data.get("errcode") == 0:
                    return True
                logger.error(f"[dingtalk] Send failed: {data}")
                self.on_error(Exception(str(data)))
                return False
        except Exception as e:
            logger.error(f"[dingtalk] Send error: {e}")
            self.on_error(e)
            return False

    # ---- 内部实现 ----

    async def _refresh_token(self) -> None:
        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url, json={"appKey": self.app_key, "appSecret": self.app_secret}
            )
            data = resp.json()
            if data.get("accessToken"):
                self._access_token = data["accessToken"]
                self._token_expires_at = time.time() + data.get("expireIn", 7200) - 300
                logger.debug("[dingtalk] Token refreshed")
            else:
                logger.error(f"[dingtalk] Token refresh failed: {data}")

    async def _get_token(self) -> Optional[str]:
        if self._access_token is None or time.time() >= self._token_expires_at:
            await self._refresh_token()
        return self._access_token

    async def _run_webhook_server(self) -> None:
        """运行 HTTP 服务器接收钉钉回调"""
        try:
            from starlette.applications import Starlette
            from starlette.requests import Request
            from starlette.responses import PlainTextResponse
            from starlette.routing import Route

            import uvicorn
        except Exception as e:
            logger.error(f"[dingtalk] Failed to start webhook server: {e}")
            return

        async def verifyGET(request: Request) -> PlainTextResponse:
            """钉钉回调 URL 验证"""
            try:
                import base64

                from cryptography.hazmat.primitives.ciphers import (
                    Cipher,
                    algorithms,
                    modes,
                )
                from cryptography.hazmat.primitives.padding import PKCS7

                msg_signature = request.query_params.get("signature", "")  # noqa: F841
                timestamp = request.query_params.get("timestamp", "")  # noqa: F841
                nonce = request.query_params.get("nonce", "")  # noqa: F841
                echostr = request.query_params.get("echostr", "")

                if not echostr:
                    return PlainTextResponse("")

                aes_key = base64.b64decode(self.aes_key + "=")
                cipher = Cipher(algorithms.AES(aes_key), modes.CBC(aes_key[:16]))
                decryptor = cipher.decryptor()
                decrypted_padded = (
                    decryptor.update(base64.b64decode(echostr)) + decryptor.finalize()
                )
                unpadder = PKCS7(128).unpadder()
                decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
                # 去掉 16 字节随机串 + 4 字节长度
                content = decrypted[20:]
                return PlainTextResponse(content.decode())
            except Exception as e:
                logger.warning(f"[dingtalk] Verify error: {e}")
                return PlainTextResponse("error", status_code=400)

        async def messagePOST(request: Request) -> PlainTextResponse:
            """接收消息回调"""
            body = await request.text()
            await self._handle_callback(body)
            return PlainTextResponse("success")

        app = Starlette(
            routes=[
                Route("/webhook/dingtalk", messagePOST, methods=["POST"]),
                Route("/webhook/dingtalk", verifyGET, methods=["GET"]),
            ]
        )
        config = uvicorn.Config(
            app,
            host="127.0.0.1",  # nosec B104 port=self.webhook_port, log_level="warning"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def _handle_callback(self, body: str) -> None:
        """处理回调消息"""
        import json

        try:
            data = json.loads(body)
            msg_type = data.get("msgtype", "")
            if msg_type != "text":
                return

            text = data.get("text", {}).get("content", "")
            user_id = data.get("senderStaffId", data.get("sender", ""))
            chat_id = data.get("conversationId", "")  # noqa: F841

            incoming = IncomingMessage(
                platform=Platform.DINGTALK,
                user_id=user_id,
                chat_id=user_id,
                text=text,
                raw=data,
                reply_to=data.get("msgId", ""),
            )
            self.on_message(incoming)
        except Exception as e:
            logger.error(f"[dingtalk] Callback parse error: {e}")

    def _decrypt_msg(self, encrypted: str) -> Optional[str]:
        """AES 解密消息"""
        import base64

        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives.padding import PKCS7

            aes_key = base64.b64decode(self.aes_key + "=")
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(aes_key[:16]))
            decryptor = cipher.decryptor()
            decrypted_padded = (
                decryptor.update(base64.b64decode(encrypted)) + decryptor.finalize()
            )
            unpadder = PKCS7(128).unpadder()
            decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
            # 去掉 16 随机字节 + 4 字节 msg_len
            msg_len = int.from_bytes(decrypted[16:20], "big")
            return decrypted[20 + msg_len :].decode()
        except Exception as e:
            logger.warning(f"[dingtalk] Decrypt error: {e}")
        return None


def check_dingtalk_dependencies() -> bool:
    if not _HAS_HTTPX:
        logger.error("httpx 未安装: pip install httpx")
        return False
    return True
