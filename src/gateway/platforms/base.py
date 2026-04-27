"""
Gateway - 多平台消息网关

支持 Telegram / Discord / WhatsApp 接入。
接收消息后统一转发给 Orchestrator 处理。

设计：
- Gateway: 总管理器，持有所有平台实例，统一消息路由
- PlatformHandler: 各平台适配器（Telegram/Discord/WhatsApp）
- 消息格式统一：{ platform, user_id, chat_id, text, raw }
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Platform(Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    WECHAT = "wechat"


@dataclass
class IncomingMessage:
    """统一收件消息格式"""

    platform: Platform
    user_id: str
    chat_id: str
    text: str
    raw: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    reply_to: str | None = None  # 消息 ID（用于回复）


@dataclass
class OutgoingMessage:
    """统一发件消息格式"""

    platform: Platform
    chat_id: str
    text: str
    reply_to: str | None = None  # 回复某条消息
    parse_mode: str = "markdown"  # 或 "html"
    extra: dict[str, Any] = field(default_factory=dict)


# ---- PlatformHandler 基类 ----


class PlatformHandler(ABC):
    """
    平台处理器基类。

    子类实现：
    - start(): 启动平台连接/Bot
    - stop(): 优雅停止
    - send(message: OutgoingMessage): 发送消息
    - _register_callback(): 注册上行消息回调
    """

    name: Platform = Platform.TELEGRAM  # 子类覆盖

    def __init__(
        self,
        on_message: Callable[[IncomingMessage], Any],
        on_error: Callable[[Exception], None] | None = None,
    ):
        """
        Args:
            on_message: 收到消息时的回调
            on_error: 出错时的回调
        """
        self.on_message = on_message
        self.on_error = on_error or self._default_error_handler
        self._started = False
        self._stop_event = asyncio.Event()

    def _default_error_handler(self, err: Exception) -> None:
        logger.error(f"[{self.name.value}] Platform error: {err}")

    @abstractmethod
    async def start(self) -> None:
        """启动平台连接"""
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        """停止平台连接"""
        raise NotImplementedError

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> bool:
        """发送消息"""
        raise NotImplementedError

    @property
    def is_started(self) -> bool:
        return self._started


class NoopHandler(PlatformHandler):
    """
    空实现 Handler（平台未配置时使用）。

    记录日志但不实际连接。
    """

    name = Platform.TELEGRAM  # 占位

    def __init__(self, platform: Platform, **kwargs):
        self.name = platform
        super().__init__(**kwargs)

    async def start(self) -> None:
        logger.info(
            f"[{self.name.value}] NoopHandler: platform not configured, skipping"
        )

    async def stop(self) -> None:
        pass

    async def send(self, message: OutgoingMessage) -> bool:
        logger.debug(f"[{self.name.value}] NoopHandler.send: {message.text[:50]}")
        return True
