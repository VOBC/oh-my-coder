"""
Capsule - GEP 协议能力包系统

实现 EvoMap GEP 协议的数据结构和注册表，支持能力注册、发现和互通。
"""

from .capsule import Capsule as Capsule
from .gene import Gene as Gene
from .registry import GEPRegistry as GEPRegistry

__all__ = ["Capsule", "GEPRegistry", "Gene"]
