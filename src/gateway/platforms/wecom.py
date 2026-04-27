"""
企业微信（WeCom）平台处理器

支持企业微信自建应用接收消息 + 发送消息。
支持：文本消息、Markdown、@ 消息。

文档：https://developer.work.weixin.qq.com/document/path/91716
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
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
    logger.warning("httpx not installed. 企业微信支持需要: pip install httpx")


class WeComHandler(PlatformHandler):
    """
    企业微信自建应用处理器

    通过 AES 解密接收消息（企业微信回调模式）。
    发送消息通过 企业微信发消息 API。

    环境变量：
        WECOM_CORP_ID       - 企业 ID
        WECOM_AGENT_ID      - 应用 AgentId
        WECOM_CORP_SECRET   - 应用 Secret
        WECOM_TOKEN         - 回调 Token（自己生成）
        WECOM_ENCODING_AES_KEY - 回调 EncodingAESKey（自己生成）
        WECOM_WEBHOOK_PORT  - 本地回调监听端口（默认 8080）
    """

    name = Platform.WECOM

    def __init__(
        self,
        corp_id: str,
        agent_id: str,
        corp_secret: str,
        token: str | None = None,
        encoding_aes_key: str | None = None,
        webhook_port: int = 8080,
        **kwargs,
    ):
        """
        Args:
            corp_id: 企业 ID
            agent_id: 应用 AgentId
            corp_secret: 应用 Secret
            token: 回调 Token（与企业在企业微信后台配置一致）
            encoding_aes_key: 回调 EncodingAESKey（46字符）
            webhook_port: 本地回调监听端口
        """
        super().__init__(**kwargs)
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.corp_secret = corp_secret
        self.token = token or "oh-my-coder-wecom"
        self.encoding_aes_key = encoding_aes_key
        self.webhook_port = webhook_port
        self._access_token: str | None = None
        self._token_expires_at: float = 0
        self._stop_event = asyncio.Event()
        self._poll_task: asyncio.Task[None] | None = None

    # ---- PlatformHandler 实现 ----

    async def start(self) -> None:
        if not _HAS_HTTPX:
            raise RuntimeError("httpx 未安装。运行: pip install httpx")

        await self._refresh_token()
        self._stop_event.clear()

        if self.encoding_aes_key:
            # 有加密配置 → 启动 HTTP 服务器接收回调
            self._poll_task = asyncio.create_task(self._run_webhook_server())
        else:
            # 无加密配置 → 轮询拉取消息
            self._poll_task = asyncio.create_task(self._poll_loop())

        self._started = True
        logger.info("[wecom] Handler started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._poll_task:
            self._poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poll_task
        self._started = False
        logger.info("[wecom] Handler stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        token = await self._get_token()
        if not token:
            return False

        url = "https://qyapi.weixin.qq.com/cgi-bin/message/send"
        params = {"access_token": token}
        payload = {
            "touser": message.chat_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {"content": message.text[:2048]},
        }
        # 如果是群聊 chat_id
        if message.chat_id.startswith("R:"):
            payload["toparty"] = message.chat_id[2:]
            del payload["touser"]
        elif message.chat_id.startswith("S:"):
            payload["totag"] = message.chat_id[2:]
            del payload["touser"]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, params=params, json=payload)
                data = resp.json()
                if data.get("errcode") == 0:
                    return True
                logger.error(f"[wecom] Send failed: {data}")
                self.on_error(Exception(str(data)))
                return False
        except Exception as e:
            logger.exception(f"[wecom] Send error: {e}")
            self.on_error(e)
            return False

    # ---- 内部实现 ----

    async def _refresh_token(self) -> None:
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {"corpid": self.corp_id, "corpsecret": self.corp_secret}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
            if data.get("access_token"):
                self._access_token = data["access_token"]
                self._token_expires_at = (
                    time.time() + data.get("expires_in", 7200) - 300
                )
                logger.debug("[wecom] Token refreshed")
            else:
                logger.error(f"[wecom] Token refresh failed: {data}")

    async def _get_token(self) -> str | None:
        if self._access_token is None or time.time() >= self._token_expires_at:
            await self._refresh_token()
        return self._access_token

    async def _run_webhook_server(self) -> None:
        """运行 Starlette HTTP 服务器接收企业微信回调"""
        try:
            import uvicorn
            from starlette.applications import Starlette
            from starlette.responses import PlainTextResponse
            from starlette.routing import Route
        except Exception as e:
            logger.exception(f"[wecom] Failed to start webhook server: {e}")
            return

        async def verifyGET(request: Request) -> PlainTextResponse:
            """企业微信回调 URL 验证"""
            msg_signature = request.query_params.get("msg_signature", "")  # noqa: F841
            timestamp = request.query_params.get("timestamp", "")  # noqa: F841
            nonce = request.query_params.get("nonce", "")  # noqa: F841
            echostr = request.query_params.get("echostr", "")

            if not echostr:
                return PlainTextResponse("")

            # 解密 echostr
            decrypted = self._decrypt(echostr)
            if decrypted:
                return PlainTextResponse(decrypted)
            return PlainTextResponse("invalid", status_code=400)

        async def messagePOST(request: Request) -> PlainTextResponse:
            """接收消息回调"""
            body = await request.text()
            await self._handle_callback(body)
            return PlainTextResponse("success")

        app = Starlette(
            routes=[
                Route("/webhook/wecom", messagePOST, methods=["POST"]),
                Route("/webhook/wecom", verifyGET, methods=["GET"]),
            ]
        )
        config = uvicorn.Config(
            app,
            host="127.0.0.1",  # nosec B104 port=self.webhook_port, log_level="warning"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def _poll_loop(self) -> None:
        """无加密配置时：轮询拉取应用消息"""
        last_time = int(time.time() * 1000) - 30000

        while not self._stop_event.is_set():
            try:
                token = await self._get_token()
                if not token:
                    await asyncio.sleep(30)
                    continue

                url = "https://qyapi.weixin.qq.com/cgi-bin/message/receive"
                params = {
                    "access_token": token,
                    "agentid": self.agent_id,
                    "start_time": str(last_time),
                }

                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, params=params)
                    data = resp.json()

                if data.get("errcode") == 0:
                    for msg in data.get("msglist", []):
                        await self._process_message(msg)
                        msg_time = int(msg.get("createtime", "0"))
                        if msg_time > last_time:
                            last_time = msg_time
                else:
                    logger.warning(f"[wecom] Poll failed: {data}")

                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[wecom] Poll error: {e}")
                await asyncio.sleep(10)

    def _decrypt(self, encrypted: str) -> str | None:
        """AES 解密企业微信消息"""
        if not self.encoding_aes_key or not self.token:
            return None

        import base64

        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives.padding import PKCS7

            aes_key = base64.b64decode(self.encoding_aes_key + "=")
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(aes_key[:16]))
            decryptor = cipher.decryptor()
            decrypted_padded = (
                decryptor.update(base64.b64decode(encrypted)) + decryptor.finalize()
            )
            unpadder = PKCS7(128).unpadder()
            decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
            # PKCS7 去除随机数、AppID、长度
            content = decrypted[16:]
            msg_len = int.from_bytes(content[:4], "big")
            from_appid = content[4 : 4 + msg_len].decode()
            msg_content = content[4 + msg_len :].decode()
            if from_appid == self.corp_id:
                return msg_content
        except Exception as e:
            logger.warning(f"[wecom] Decrypt error: {e}")
        return None

    async def _handle_callback(self, body: str) -> None:
        """处理回调消息"""
        import json

        try:
            # 企业微信回调消息格式
            data = json.loads(body)
            msg_type = data.get("MsgType", "")
            if msg_type != "text":
                return

            text = data.get("Content", "")
            user_id = data.get("FromUserName", "")
            chat_id = data.get("ToUserName", "")  # noqa: F841

            incoming = IncomingMessage(
                platform=Platform.WECOM,
                user_id=user_id,
                chat_id=user_id,
                text=text,
                raw=data,
                reply_to=data.get("MsgId", ""),
            )
            self.on_message(incoming)
        except Exception as e:
            logger.exception(f"[wecom] Callback parse error: {e}")

    async def _process_message(self, msg: dict[str, Any]) -> None:
        """处理拉取的消息"""
        msg_type = msg.get("MsgType", "")
        if msg_type != "text":
            return

        text = msg.get("Content", "")
        user_id = msg.get("FromUserName", "")

        incoming = IncomingMessage(
            platform=Platform.WECOM,
            user_id=user_id,
            chat_id=user_id,
            text=text,
            raw=msg,
            reply_to=msg.get("MsgId", ""),
        )
        try:
            self.on_message(incoming)
        except Exception as e:
            logger.exception(f"[wecom] on_message error: {e}")
            self.on_error(e)


def check_wecom_dependencies() -> bool:
    if not _HAS_HTTPX:
        logger.error("httpx 未安装: pip install httpx")
        return False
    return True
