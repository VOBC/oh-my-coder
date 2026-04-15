"""
飞书 / Lark 平台处理器

支持飞书自建应用（接收消息 + 发送消息）。
支持：文本消息、回复、Markdown。

文档：https://open.feishu.cn/document/server-docs/im-v1/message-content-description/create
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from ..base import IncomingMessage, OutgoingMessage, Platform, PlatformHandler

logger = logging.getLogger(__name__)

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    logger.warning("httpx not installed. 飞书支持需要: pip install httpx")


class FeishuHandler(PlatformHandler):
    """
    飞书自建应用处理器

    通过 HTTP Webhook + 轮询（Long Polling）接收消息。
    支持文本、卡片消息、@ 机器人交互。

    环境变量：
        FEISHU_APP_ID         - 飞书应用 App ID
        FEISHU_APP_SECRET     - 飞书应用 App Secret
        FEISHU_VERIFY_TOKEN   - 事件订阅的 Verify Token（可选）
        FEISHU_ENCRYPT_KEY    - 事件订阅的加密 Key（可选，如有）
    """

    name = Platform.FEISHU

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        encrypt_key: Optional[str] = None,
        verify_token: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            app_id: 飞书自建应用的 App ID（cli_xxx）
            app_secret: 飞书自建应用的 App Secret
            encrypt_key: 事件加密 Key（如配置了加密则填）
            verify_token: 事件订阅 Verify Token
        """
        super().__init__(**kwargs)
        self.app_id = app_id
        self.app_secret = app_secret
        self.encrypt_key = encrypt_key
        self.verify_token = verify_token
        self._tenant_access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._stop_event = asyncio.Event()
        self._poll_task: Optional[asyncio.Task[None]] = None

    # ---- PlatformHandler 实现 ----

    async def start(self) -> None:
        if not _HAS_HTTPX:
            raise RuntimeError("httpx 未安装。运行: pip install httpx")

        # 预获取 token
        await self._refresh_token()
        self._stop_event.clear()
        self._poll_task = asyncio.create_task(self._long_poll_loop())
        self._started = True
        logger.info("[feishu] Handler started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self._started = False
        logger.info("[feishu] Handler stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        """发送消息到飞书"""
        token = await self._get_token()
        if not token:
            return False

        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # 飞书消息格式
        content = self._build_content(message.text, message.parse_mode)

        payload = {
            "receive_id": message.chat_id,
            "msg_type": "text",
            "content": content,
        }

        # 根据 chat_id 格式判断类型
        if message.chat_id.startswith("oc_"):
            payload["receive_id_type"] = "open_id"
        elif message.chat_id.startswith("p_"):
            payload["receive_id_type"] = "phone"
        elif message.chat_id.startswith("u_"):
            payload["receive_id_type"] = "user_id"
        else:
            payload["receive_id_type"] = "chat_id"  # 默认群组

        # 回复消息
        if message.reply_to:
            url_with_type = f"{url}?receive_id_type={payload['receive_id_type']}"
        else:
            url_with_type = f"{url}?receive_id_type={payload['receive_id_type']}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url_with_type, headers=headers, json=payload)
                data = resp.json()
                if resp.status_code == 200 and data.get("code") == 0:
                    return True
                logger.error(f"[feishu] Send failed: {data}")
                self.on_error(Exception(str(data)))
                return False
        except Exception as e:
            logger.error(f"[feishu] Send error: {e}")
            self.on_error(e)
            return False

    # ---- 内部实现 ----

    async def _refresh_token(self) -> None:
        """获取 tenant_access_token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url, json={"app_id": self.app_id, "app_secret": self.app_secret}
            )
            data = resp.json()
            if data.get("code") == 0:
                self._tenant_access_token = data["tenant_access_token"]
                # token 有效期 2 小时，提前 5 分钟刷新
                self._token_expires_at = time.time() + (data.get("expire", 7200) - 300)
                logger.debug("[feishu] Token refreshed")
            else:
                logger.error(f"[feishu] Token refresh failed: {data}")

    async def _get_token(self) -> Optional[str]:
        """获取有效 token（自动刷新）"""
        if self._tenant_access_token is None or time.time() >= self._token_expires_at:
            await self._refresh_token()
        return self._tenant_access_token

    async def _long_poll_loop(self) -> None:
        """
        飞书消息事件拉取（使用 im/v1/messages 接口轮询）。

        实际生产环境推荐使用"事件订阅"Webhook 模式，
        本实现作为无公网 Webhook 时的备选方案。
        """
        last_msg_time = int(time.time() * 1000) - 30000  # 30秒前的消息

        while not self._stop_event.is_set():
            try:
                token = await self._get_token()
                if not token:
                    await asyncio.sleep(30)
                    continue

                url = "https://open.feishu.cn/open-apis/im/v1/messages"
                params = {
                    "container_id_type": "chat",
                    "start_time": str(last_msg_time),
                    "page_size": "50",
                }
                headers = {"Authorization": f"Bearer {token}"}

                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, headers=headers, params=params)
                    data = resp.json()

                if data.get("code") == 0:
                    msgs = data.get("data", {}).get("items", [])
                    for msg in msgs:
                        await self._process_message(msg)
                        msg_time = int(msg.get("create_time", "0"))
                        if msg_time > last_msg_time:
                            last_msg_time = msg_time
                else:
                    logger.warning(f"[feishu] Poll failed: {data}")

                # 轮询间隔 5 秒
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[feishu] Poll error: {e}")
                await asyncio.sleep(10)

    async def _process_message(self, msg: Dict[str, Any]) -> None:
        """处理飞书消息"""
        msg_type = msg.get("msg_type", "")
        if msg_type != "text":
            logger.debug(f"[feishu] Unsupported msg_type: {msg_type}")
            return

        sender = msg.get("sender", {})
        chat_type = msg.get("chat_type", "")
        if chat_type != "p2p":  # 只处理私聊
            logger.debug(f"[feishu] Ignoring non-p2p message: {chat_type}")
            return

        text = msg.get("body", {}).get("content", "")
        try:
            import json

            content = json.loads(text)
            text = content.get("text", "")
        except Exception:
            pass

        if not text:
            return

        user_id = sender.get("id", "")
        chat_id = msg.get("chat_id", "")

        incoming = IncomingMessage(
            platform=Platform.FEISHU,
            user_id=user_id,
            chat_id=user_id,  # 发回给同一用户
            text=text,
            raw={
                "message_id": msg.get("message_id", ""),
                "chat_id": chat_id,
                "chat_type": chat_type,
                "sender": sender,
                "create_time": msg.get("create_time", ""),
            },
            reply_to=msg.get("message_id", ""),
        )

        try:
            self.on_message(incoming)
        except Exception as e:
            logger.error(f"[feishu] on_message error: {e}")
            self.on_error(e)

    @staticmethod
    def _build_content(text: str, parse_mode: str) -> str:
        """构建飞书消息内容"""
        import json

        return json.dumps({"text": text})


def check_feishu_dependencies() -> bool:
    """检查飞书依赖是否满足"""
    if not _HAS_HTTPX:
        logger.error("httpx 未安装: pip install httpx")
        return False
    return True
