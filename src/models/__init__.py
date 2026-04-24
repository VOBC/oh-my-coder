"""
Oh My Coder - 模型模块

支持多种 LLM 提供商，统一接口，灵活切换。
"""

import json
from pathlib import Path
from typing import Literal

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
from .mimo import MimoAPIError, MimoModel
from .doubao import DoubaoAPIError, DoubaoModel
from .glm import GLMAPIError, GLMModel
from .hunyuan import HunyuanAPIError, HunyuanModel
from .kimi import KimiAPIError, KimiModel
from .minimax import MiniMaxAPIError, MiniMaxModel
from .spark import SparkAPIError, SparkModel
from .tiangong import TiangongAPIError, TiangongModel
from .tongyi import TongyiAPIError, TongyiModel
from .wenxin import WenxinAPIError, WenxinModel
from .ollama import OllamaModel, create_ollama_model

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
    # 小米 MiMo
    "MimoModel",
    "MimoAPIError",
    # Ollama 本地模型
    "OllamaModel",
    "create_ollama_model",
]

# ── Model Metadata ─────────────────────────────────────────────────────────────

ModelStatus = Literal["production", "beta", "deprecated"]

_MODEL_META: dict[str, dict] = {}
_MODEL_META_LOADED = False


def _load_model_metadata() -> dict[str, dict]:
    """Load model metadata from JSON file (cached)."""
    global _MODEL_META, _MODEL_META_LOADED
    if _MODEL_META_LOADED:
        return _MODEL_META
    try:
        path = Path(__file__).parent / "model_metadata.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        _MODEL_META = {k: v for k, v in raw.items()}
    except Exception:
        _MODEL_META = {}
    _MODEL_META_LOADED = True
    return _MODEL_META


def get_model_status(model_id: str) -> ModelStatus:
    """Get status for a model/provider: production, beta, or deprecated."""
    meta = _load_model_metadata()
    # Check model-level first
    if model_id in meta:
        return meta[model_id].get("status", "production")
    # Fall back to provider-level (_providers section)
    providers = meta.get("_providers", {})
    return providers.get(model_id, "production")  # default: production


def filter_by_status(
    models: list[dict],
    *,
    show_production: bool = True,
    show_beta: bool = False,
    show_deprecated: bool = False,
) -> list[dict]:
    """Filter model list by status.

    Default: only production models shown.
    Use show_beta=True to also include beta models.
    """
    meta = _load_model_metadata()
    result = []
    for m in models:
        mid = m.get("model") or m.get("id", "")
        status = meta.get(mid, {}).get("status", "beta")
        if status == "production" and show_production:
            result.append(m)
        elif status == "beta" and show_beta:
            result.append(m)
        elif status == "deprecated" and show_deprecated:
            result.append(m)
    return result


def enrich_with_status(models: list[dict]) -> list[dict]:
    """Add status field to each model dict from metadata."""
    meta = _load_model_metadata()
    return [
        {
            **m,
            "model_status": meta.get(m.get("model") or m.get("id", ""), {}).get(
                "status", "beta"
            ),
        }
        for m in models
    ]
