"""
Oh My Coder - 模型模块

支持多种 LLM 提供商，统一接口，灵活切换。
"""

from .baichuan import BaichuanAPIError, BaichuanModel
from .base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
    Usage,
)

# 导出所有模型适配器
from .deepseek import DeepSeekAPIError, DeepSeekModel
from .doubao import DoubaoAPIError, DoubaoModel
from .glm import GLMAPIError, GLMModel
from .hunyuan import HunyuanAPIError, HunyuanModel
from .kimi import KimiAPIError, KimiModel
from .minimax import MiniMaxAPIError, MiniMaxModel
from .spark import SparkAPIError, SparkModel
from .tiangong import TiangongAPIError, TiangongModel
from .tongyi import TongyiAPIError, TongyiModel
from .wenxin import WenxinAPIError, WenxinModel

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
    # 百川智能
    "BaichuanModel",
    "BaichuanAPIError",
]
