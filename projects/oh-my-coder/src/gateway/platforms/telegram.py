"""
Telegram Bot 平台处理器

使用 python-telegram-bot 库实现。
支持：消息接收、消息发送、命令处理、回复。
"""

from __future__ import annotations

import logging
from typing import Any

from ..base import IncomingMessage, OutgoingMessage, Platform, PlatformHandler

logger = logging.getLogger(__name__)

# 尝试导入 telegram 库
try:
    from telegram import Update
    from telegram.ext import (
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    _HAS_TELEGRAM = True
except ImportError:
    _HAS_TELEGRAM = False
    logger.warning("python-telegram-bot not installed. Telegram support disabled.")


class TelegramHandler(PlatformHandler):
    """
    Telegram Bot 处理器

    接收用户消息 → 转为 IncomingMessage → 传给 on_message
    """

    name = Platform.TELEGRAM

    def __init__(
        self,
        bot_token: str,
        allowed_user_ids: list[str] | None = None,
        **kwargs,
    ):
        """
        Args:
            bot_token: Telegram Bot Token（从 @BotFather 获取）
            allowed_user_ids: 白名单用户 ID（None = 不限制）
        """
        super().__init__(**kwargs)
        self.bot_token = bot_token
        self.allowed_user_ids = set(allowed_user_ids or [])
        self._app: Any = None
        self._dispatcher: Any = None

    # ---- PlatformHandler 实现 ----

    async def start(self) -> None:
        if not _HAS_TELEGRAM:
            raise RuntimeError(
                "python-telegram-bot 未安装。运行: pip install python-telegram-bot"
            )

        from telegram.ext import Application

        self._app = Application.builder().token(self.bot_token).build()

        # 注册处理器
        self._app.add_handler(CommandHandler("start", self._handle_start))
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text)
        )

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(allowed_updates=Update.ALL_UPDATE_TYPES)
        self._started = True
        logger.info("[telegram] Bot started successfully")

    async def stop(self) -> None:
        if self._app is not None:
            await self._app.stop()
            self._started = False
            logger.info("[telegram] Bot stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        if self._app is None:
            return False

        try:
            await self._app.bot.send_message(
                chat_id=message.chat_id,
                text=message.text,
                parse_mode=message.parse_mode.upper() if message.parse_mode else None,
                reply_to_message_id=message.reply_to,
            )
            return True
        except Exception as e:
            logger.exception(f"[telegram] Send failed: {e}")
            self.on_error(e)
            return False

    # ---- 内部处理器 ----

    async def _handle_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理 /start 命令"""
        await update.message.reply_text(
            "👋 欢迎使用 Oh My Coder！\n\n"
            "发送消息即可开始对话。\n"
            "输入 /help 查看可用命令。"
        )

    async def _handle_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理文本消息"""
        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)
        text = update.message.text or ""

        # 白名单检查
        if self.allowed_user_ids and user_id not in self.allowed_user_ids:
            logger.warning(
                f"[telegram] Rejected message from unauthorized user: {user_id}"
            )
            await update.message.reply_text("⚠️ 未授权的用户")
            return

        # 转为统一格式
        incoming = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id=user_id,
            chat_id=chat_id,
            text=text,
            raw={
                "message_id": update.message.message_id,
                "username": update.effective_user.username,
                "first_name": update.effective_user.first_name,
            },
            reply_to=str(update.message.message_id),
        )

        try:
            self.on_message(incoming)
        except Exception as e:
            logger.exception(f"[telegram] on_message error: {e}")
            self.on_error(e)
            await update.message.reply_text("⚠️ 处理消息时出错，请稍后重试。")


# ---- 依赖检查 ----


def check_telegram_dependencies() -> bool:
    """检查 Telegram 依赖是否满足"""
    if not _HAS_TELEGRAM:
        logger.error("python-telegram-bot 未安装")
        return False
    return True
