"""
Gateway - 多平台消息网关

子模块：
- base: 基础类型（Platform, IncomingMessage, OutgoingMessage, PlatformHandler）
- platforms.telegram: Telegram Bot 处理器
- platforms.discord: Discord Bot 处理器
- gateway: 主 Gateway 类
"""

from .base import IncomingMessage  # noqa: F401
from .base import NoopHandler  # noqa: F401
from .base import OutgoingMessage  # noqa: F401
from .base import Platform  # noqa: F401
from .base import PlatformHandler  # noqa: F401
from .gateway import Gateway  # noqa: F401
