"""
Oh My Coder - 模型模块

支持多种 LLM 提供商，统一接口，灵活切换。
"""

from .base import (
    BaseModel,
    ModelConfig,
    ModelProvider,
    ModelTier,
    Message,
    ModelResponse,
    Usage,
)

# 导出所有模型适配器
from .deepseek import DeepSeekModel, DeepSeekAPIError
from .wenxin import WenxinModel, WenxinAPIError
from .tongyi import TongyiModel, TongyiAPIError
from .glm import GLMModel, GLMAPIError
from .minimax import MiniMaxModel, MiniMaxAPIError
from .kimi import KimiModel, KimiAPIError
from .hunyuan import HunyuanModel, HunyuanAPIError
from .doubao import DoubaoModel, DoubaoAPIError
from .tiangong import TiangongModel, TiangongAPIError
from .spark import SparkModel, SparkAPIError

__all__ = [
    # 基类
    "BaseModel",
    "ModelConfig",
    "ModelProvider",
    "ModelTier",
    "Message",
    "ModelResponse",
    "Usage",
    # DeepSeek
    "DeepSeekModel",
    "DeepSeekAPIError",
    # 文心一言
    "WenxinModel",
    "WenxinAPIError",
    # 通义千问
    "TongyiModel",
    "TongyiAPIError",
    # 智谱 GLM
    "GLMModel",
    "GLMAPIError",
    # MiniMax
    "MiniMaxModel",
    "MiniMaxAPIError",
    # Kimi
    "KimiModel",
    "KimiAPIError",
    # 腾讯混元
    "HunyuanModel",
    "HunyuanAPIError",
    # 字节豆包
    "DoubaoModel",
    "DoubaoAPIError",
    # 天工AI
    "TiangongModel",
    "TiangongAPIError",
    # 讯飞星火
    "SparkModel",
    "SparkAPIError",
]
