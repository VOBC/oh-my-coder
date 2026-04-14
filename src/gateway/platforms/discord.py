"""
Discord Bot 平台处理器

使用 discord.py 库实现。
支持：消息接收、消息发送、回复。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..base import IncomingMessage, OutgoingMessage, Platform, PlatformHandler

logger = logging.getLogger(__name__)

# 尝试导入 discord.py
try:
    import discord

    _HAS_DISCORD = True
except ImportError:
    _HAS_DISCORD = False
    discord = None  # type: ignore
    logger.warning("discord.py not installed. Discord support disabled.")


def _get_discord_client():
    """延迟导入 discord.Client，避免模块级依赖"""
    if not _HAS_DISCORD:
        raise RuntimeError("discord.py 未安装")
    import discord

    return discord.Client


def _get_intents():
    if not _HAS_DISCORD:
        return None
    import discord

    intents = discord.Intents.default()
    intents.message_content = True
    return intents


class DiscordHandler(PlatformHandler):
    """
    Discord Bot 处理器
    """

    name = Platform.DISCORD

    def __init__(
        self,
        bot_token: str,
        allowed_guild_ids: Optional[list[int]] = None,
        **kwargs,
    ):
        """
        Args:
            bot_token: Discord Bot Token
            allowed_guild_ids: 允许的服务器 ID（None = 不限制）
        """
        super().__init__(**kwargs)
        self.bot_token = bot_token
        self.allowed_guild_ids = set(allowed_guild_ids or [])
        self._bot: Optional[Any] = None

    # ---- PlatformHandler 实现 ----

    async def start(self) -> None:
        if not _HAS_DISCORD:
            raise RuntimeError("discord.py 未安装。运行: pip install discord.py")

        import discord

        intents = discord.Intents.default()
        intents.message_content = True

        class _Bot(discord.Client):
            def __init__(inner_self):
                super().__init__(intents=intents)

            async def on_message(inner_self, message: Any) -> None:
                if message.author.bot:
                    return
                if not isinstance(message.channel, discord.TextChannel):
                    return
                if self.allowed_guild_ids and (
                    message.guild is None
                    or message.guild.id not in self.allowed_guild_ids
                ):
                    return

                incoming = IncomingMessage(
                    platform=Platform.DISCORD,
                    user_id=str(message.author.id),
                    chat_id=str(message.channel.id),
                    text=message.content,
                    raw={
                        "guild_id": str(message.guild.id) if message.guild else None,
                        "guild_name": message.guild.name if message.guild else None,
                        "channel_name": message.channel.name,
                        "username": str(message.author),
                        "message_id": str(message.id),
                    },
                    reply_to=str(message.id),
                )
                try:
                    self.on_message(incoming)
                except Exception as e:
                    logger.error(f"[discord] on_message error: {e}")
                    self.on_error(e)

        self._bot = _Bot()
        await self._bot.start(self.bot_token)
        self._started = True
        logger.info("[discord] Bot started successfully")

    async def stop(self) -> None:
        if self._bot is not None:
            await self._bot.close()
            self._started = False
            logger.info("[discord] Bot stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        if self._bot is None:
            return False

        try:

            channel = self._bot.get_channel(int(message.chat_id))
            if channel is None:
                logger.error(f"[discord] Channel not found: {message.chat_id}")
                return False

            reference = None
            if message.reply_to:
                try:
                    reference = await channel.fetch_message(int(message.reply_to))
                except Exception:
                    pass

            await channel.send(content=message.text, reference=reference)
            return True
        except Exception as e:
            logger.error(f"[discord] Send failed: {e}")
            self.on_error(e)
            return False


def check_discord_dependencies() -> bool:
    """检查 Discord 依赖是否满足"""
    if not _HAS_DISCORD:
        logger.error("discord.py 未安装")
        return False
    return True
