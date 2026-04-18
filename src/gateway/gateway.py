"""
Gateway - 多平台统一消息网关

职责：
1. 管理所有平台处理器（Telegram/Discord/WhatsApp）
2. 接收来自各平台的消息，统一转为 IncomingMessage
3. 转发给 Orchestrator 处理
4. 返回结果到对应平台

用法：
```python
gateway = Gateway(
    orchestrator=orch,
    telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
    discord_token=os.getenv("DISCORD_BOT_TOKEN"),
)

# 方式 1：命令行启动
await gateway.start_all()

# 方式 2：Flask/FastAPI 集成
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    await gateway.handle_telegram_update(await request.json())
```

CLI:
    omc gateway start --telegram <token>
    omc gateway start --discord <token>
    omc gateway status
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import (
    IncomingMessage,
    NoopHandler,
    OutgoingMessage,
    Platform,
    PlatformHandler,
)

logger = logging.getLogger(__name__)


class Gateway:
    """
    多平台消息网关

    生命周期：
    1. __init__: 配置各平台
    2. start_all(): 启动所有已配置平台
    3. on_platform_message(): 接收消息 → Orchestrator → 回复
    4. stop_all(): 停止所有平台
    """

    def __init__(
        self,
        orchestrator: Any = None,
        telegram_token: Optional[str] = None,
        discord_token: Optional[str] = None,
        whatsapp_phone_number_id: Optional[str] = None,
        whatsapp_access_token: Optional[str] = None,
        whatsapp_webhook_url: Optional[str] = None,
        whatsapp_verify_token: Optional[str] = None,
        feishu_app_id: Optional[str] = None,
        feishu_app_secret: Optional[str] = None,
        feishu_encrypt_key: Optional[str] = None,
        wecom_corp_id: Optional[str] = None,
        wecom_agent_id: Optional[str] = None,
        wecom_corp_secret: Optional[str] = None,
        wecom_token: Optional[str] = None,
        wecom_encoding_aes_key: Optional[str] = None,
        dingtalk_app_key: Optional[str] = None,
        dingtalk_app_secret: Optional[str] = None,
        dingtalk_token: Optional[str] = None,
        dingtalk_aes_key: Optional[str] = None,
        slack_bot_token: Optional[str] = None,
        slack_signing_secret: Optional[str] = None,
        allowed_user_ids: Optional[Dict[Platform, List[str]]] = None,
        plugins_dir: Optional[Path] = None,
    ):
        """
        Args:
            orchestrator: Orchestrator 实例（用于处理消息）
            telegram_token: Telegram Bot Token
            discord_token: Discord Bot Token
            allowed_user_ids: 各平台的白名单用户 ID
            plugins_dir: 插件目录（预留）
        """
        self.orchestrator = orchestrator
        self._handlers: Dict[Platform, PlatformHandler] = {}
        self._started_platforms: List[str] = []
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()

        allowed_user_ids = allowed_user_ids or {}

        # ---- Telegram ----
        if telegram_token:
            self._register_telegram(
                telegram_token, allowed_user_ids.get(Platform.TELEGRAM, [])
            )
        else:
            self._handlers[Platform.TELEGRAM] = NoopHandler(
                platform=Platform.TELEGRAM, on_message=self._noop_handler
            )

        # ---- Discord ----
        if discord_token:
            self._register_discord(
                discord_token, allowed_user_ids.get(Platform.DISCORD, [])
            )
        else:
            self._handlers[Platform.DISCORD] = NoopHandler(
                platform=Platform.DISCORD, on_message=self._noop_handler
            )

        # ---- WhatsApp ----
        if whatsapp_phone_number_id and whatsapp_access_token:
            self._register_whatsapp(
                whatsapp_phone_number_id,
                whatsapp_access_token,
                whatsapp_webhook_url or "",
                whatsapp_verify_token,
            )
        else:
            self._handlers[Platform.WHATSAPP] = NoopHandler(
                platform=Platform.WHATSAPP, on_message=self._noop_handler
            )

        # ---- 飞书 ----
        if feishu_app_id and feishu_app_secret:
            self._register_feishu(feishu_app_id, feishu_app_secret, feishu_encrypt_key)
        else:
            self._handlers[Platform.FEISHU] = NoopHandler(
                platform=Platform.FEISHU, on_message=self._noop_handler
            )

        # ---- 企业微信 ----
        if wecom_corp_id and wecom_agent_id and wecom_corp_secret:
            self._register_wecom(
                wecom_corp_id,
                wecom_agent_id,
                wecom_corp_secret,
                wecom_token,
                wecom_encoding_aes_key,
            )
        else:
            self._handlers[Platform.WECOM] = NoopHandler(
                platform=Platform.WECOM, on_message=self._noop_handler
            )

        # ---- 钉钉 ----
        if dingtalk_app_key and dingtalk_app_secret:
            self._register_dingtalk(
                dingtalk_app_key,
                dingtalk_app_secret,
                dingtalk_token,
                dingtalk_aes_key,
            )
        else:
            self._handlers[Platform.DINGTALK] = NoopHandler(
                platform=Platform.DINGTALK, on_message=self._noop_handler
            )

        # ---- Slack ----
        if slack_bot_token and slack_signing_secret:
            self._register_slack(slack_bot_token, slack_signing_secret)
        else:
            self._handlers[Platform.SLACK] = NoopHandler(
                platform=Platform.SLACK, on_message=self._noop_handler
            )

    # ---- 平台注册 ----

    def _register_telegram(self, token: str, allowed_user_ids: List[str]) -> None:
        from .platforms.telegram import TelegramHandler, check_telegram_dependencies

        if not check_telegram_dependencies():
            logger.warning("[gateway] Telegram 依赖缺失，跳过注册")
            return

        self._handlers[Platform.TELEGRAM] = TelegramHandler(
            bot_token=token,
            allowed_user_ids=allowed_user_ids,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/telegram] {e}"),
        )
        logger.info("[gateway] Telegram handler registered")

    def _register_discord(self, token: str, allowed_guild_ids: List[int]) -> None:
        from .platforms.discord import DiscordHandler, check_discord_dependencies

        if not check_discord_dependencies():
            logger.warning("[gateway] Discord 依赖缺失，跳过注册")
            return

        self._handlers[Platform.DISCORD] = DiscordHandler(
            bot_token=token,
            allowed_guild_ids=allowed_guild_ids,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/discord] {e}"),
        )
        logger.info("[gateway] Discord handler registered")

    def _register_whatsapp(
        self,
        phone_number_id: str,
        access_token: str,
        webhook_url: str,
        verify_token: Optional[str],
    ) -> None:
        from .platforms.whatsapp import WhatsAppHandler, check_whatsapp_dependencies

        if not check_whatsapp_dependencies():
            logger.warning("[gateway] WhatsApp 依赖缺失，跳过注册")
            return

        self._handlers[Platform.WHATSAPP] = WhatsAppHandler(
            phone_number_id=phone_number_id,
            access_token=access_token,
            webhook_url=webhook_url,
            verify_token=verify_token,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/whatsapp] {e}"),
        )
        logger.info("[gateway] WhatsApp handler registered")

    def _register_feishu(
        self, app_id: str, app_secret: str, encrypt_key: Optional[str]
    ) -> None:
        from .platforms.feishu import FeishuHandler, check_feishu_dependencies

        if not check_feishu_dependencies():
            logger.warning("[gateway] 飞书依赖缺失，跳过注册")
            return

        self._handlers[Platform.FEISHU] = FeishuHandler(
            app_id=app_id,
            app_secret=app_secret,
            encrypt_key=encrypt_key,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/feishu] {e}"),
        )
        logger.info("[gateway] 飞书 handler registered")

    def _register_wecom(
        self,
        corp_id: str,
        agent_id: str,
        corp_secret: str,
        token: Optional[str],
        encoding_aes_key: Optional[str],
    ) -> None:
        from .platforms.wecom import WeComHandler, check_wecom_dependencies

        if not check_wecom_dependencies():
            logger.warning("[gateway] 企业微信依赖缺失，跳过注册")
            return

        self._handlers[Platform.WECOM] = WeComHandler(
            corp_id=corp_id,
            agent_id=agent_id,
            corp_secret=corp_secret,
            token=token,
            encoding_aes_key=encoding_aes_key,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/wecom] {e}"),
        )
        logger.info("[gateway] 企业微信 handler registered")

    def _register_dingtalk(
        self,
        app_key: str,
        app_secret: str,
        token: Optional[str],
        aes_key: Optional[str],
    ) -> None:
        from .platforms.dingtalk import DingTalkHandler, check_dingtalk_dependencies

        if not check_dingtalk_dependencies():
            logger.warning("[gateway] 钉钉依赖缺失，跳过注册")
            return

        self._handlers[Platform.DINGTALK] = DingTalkHandler(
            app_key=app_key,
            app_secret=app_secret,
            token=token,
            aes_key=aes_key,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/dingtalk] {e}"),
        )
        logger.info("[gateway] 钉钉 handler registered")

    def _register_slack(self, bot_token: str, signing_secret: str) -> None:
        from .platforms.slack import SlackHandler, check_slack_dependencies

        if not check_slack_dependencies():
            logger.warning("[gateway] Slack 依赖缺失，跳过注册")
            return

        self._handlers[Platform.SLACK] = SlackHandler(
            bot_token=bot_token,
            signing_secret=signing_secret,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/slack] {e}"),
        )
        logger.info("[gateway] Slack handler registered")

    # ---- 消息处理 ----

    def on_platform_message(self, message: IncomingMessage) -> None:
        """
        收到各平台消息时的回调。

        默认实现：打印日志。
        子类/外部可覆盖此方法接入真实 Orchestrator。

        Args:
            message: 统一格式的收件消息
        """
        logger.info(
            f"[gateway] [{message.platform.value}] {message.user_id}: {message.text[:80]}"  # noqa: E501
        )

        if self.orchestrator is None:
            logger.debug("[gateway] No orchestrator configured, skipping processing")
            return

        # 异步处理（不阻塞平台回调）
        asyncio.create_task(self._process_message(message))

    async def _process_message(self, message: IncomingMessage) -> None:
        """处理消息 → Orchestrator → 回复"""
        try:
            if self.orchestrator is None:
                return

            # 构建 context
            context = {
                "task": message.text,
                "project_path": str(Path.cwd()),
                "_platform": message.platform.value,
                "_user_id": message.user_id,
                "_chat_id": message.chat_id,
            }

            # 执行工作流
            result = await self.orchestrator.execute_workflow(
                "autopilot",
                context,
            )

            # 提取结果文本
            response_text = self._extract_response(result)

            # 发回平台
            reply = OutgoingMessage(
                platform=message.platform,
                chat_id=message.chat_id,
                text=response_text,
                reply_to=message.reply_to,
            )
            handler = self._handlers.get(message.platform)
            if handler and handler.is_started:
                await handler.send(reply)

        except Exception as e:
            logger.error(f"[gateway] _process_message error: {e}")
            # 尝试发错误回复
            try:
                error_reply = OutgoingMessage(
                    platform=message.platform,
                    chat_id=message.chat_id,
                    text=f"⚠️ 处理失败: {type(e).__name__}",
                )
                handler = self._handlers.get(message.platform)
                if handler and handler.is_started:
                    await handler.send(error_reply)
            except Exception:
                pass

    @staticmethod
    def _extract_response(result: Any) -> str:
        """从 WorkflowResult 提取响应文本"""
        if result is None:
            return "（无结果）"

        # 尝试 outputs
        if hasattr(result, "outputs") and result.outputs:
            parts = []
            for agent_name, output in result.outputs.items():
                content = getattr(output, "result", None)
                if content:
                    parts.append(f"**[{agent_name}]**\n{content[:500]}")
            if parts:
                return "\n\n".join(parts)

        # 降级：直接 str
        return str(result)[:1000]

    # ---- 生命周期 ----

    async def start_all(self) -> None:
        """启动所有已配置的平台"""
        async with self._lock:
            tasks = []
            for platform, handler in self._handlers.items():
                if not handler.is_started:
                    tasks.append(self._start_platform(platform, handler))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        started = [p for p, h in self._handlers.items() if h.is_started]
        logger.info(f"[gateway] Started platforms: {[p.value for p in started]}")

    async def _start_platform(
        self, platform: Platform, handler: PlatformHandler
    ) -> None:
        try:
            await handler.start()
            self._started_platforms.append(platform.value)
        except Exception as e:
            logger.error(f"[gateway] Failed to start {platform.value}: {e}")

    async def stop_all(self) -> None:
        """停止所有平台"""
        async with self._lock:
            tasks = []
            for platform, handler in self._handlers.items():
                if handler.is_started:
                    tasks.append(self._stop_platform(platform, handler))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        self._stop_event.set()
        logger.info("[gateway] All platforms stopped")

    async def _stop_platform(
        self, platform: Platform, handler: PlatformHandler
    ) -> None:
        try:
            await handler.stop()
            if platform.value in self._started_platforms:
                self._started_platforms.remove(platform.value)
        except Exception as e:
            logger.error(f"[gateway] Error stopping {platform.value}: {e}")

    # ---- 状态查询 ----

    def status(self) -> Dict[str, Any]:
        """返回网关状态"""
        handlers_info = {
            platform.value: {
                "configured": handler.__class__ != NoopHandler,
                "started": handler.is_started,
                "type": handler.__class__.__name__,
            }
            for platform, handler in self._handlers.items()
        }
        return {
            "started_platforms": self._started_platforms,
            "handlers": handlers_info,
        }

    def get_handler(self, platform: Platform) -> Optional[PlatformHandler]:
        return self._handlers.get(platform)

    def _noop_handler(self, message: IncomingMessage) -> None:
        """NoopHandler 的 on_message 回调"""
        pass

    # ---- Webhook 支持（供 FastAPI 集成）----

    async def handle_telegram_update(self, update: Dict[str, Any]) -> None:
        """
        处理 Telegram Webhook 更新。

        用于 FastAPI 路由：
        @app.post("/webhook/telegram")
        async def telegram_webhook(request: Request):
            await gateway.handle_telegram_update(await request.json())
        """
        handler = self._handlers.get(Platform.TELEGRAM)
        if handler is None or isinstance(handler, NoopHandler):
            logger.warning("[gateway] Telegram not configured")
            return

        # Telegram Webhook 需要从 Update 提取 message
        message_data = update.get("message", {})
        if not message_data:
            return

        from .base import IncomingMessage

        incoming = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id=str(message_data.get("from", {}).get("id", "")),
            chat_id=str(message_data.get("chat", {}).get("id", "")),
            text=message_data.get("text", ""),
            raw=update,
            reply_to=str(message_data.get("message_id", "")),
        )
        self.on_platform_message(incoming)
