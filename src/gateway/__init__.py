"""
Gateway - 多平台消息网关

子模块：
- base: 基础类型（Platform, IncomingMessage, OutgoingMessage, PlatformHandler）
- gateway: 主 Gateway 类（渠道实现已移除，平台默认 NoopHandler 占位）
"""

from .base import (
    IncomingMessage,  # noqa: F401
    NoopHandler,  # noqa: F401
    OutgoingMessage,  # noqa: F401
    Platform,  # noqa: F401
    PlatformHandler,  # noqa: F401
)
from .gateway import Gateway  # noqa: F401
