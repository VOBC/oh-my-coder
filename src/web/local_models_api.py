from __future__ import annotations
"""
本地模型 API

提供 Ollama 本地模型的管理和查询功能。
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/local-models", tags=["local-models"])


class LocalModelInfo(BaseModel):
    """本地模型信息"""

    name: str
    size: str | None = None
    modified_at: str | None = None
    tier: str | None = None
    description: str | None = None
    available: bool = True


class OllamaStatus(BaseModel):
    """Ollama 服务状态"""

    available: bool
    base_url: str
    models: list[LocalModelInfo] = []
    error: str | None = None


@router.get("/status", response_model=OllamaStatus)
async def get_ollama_status() -> OllamaStatus:
    """
    获取 Ollama 服务状态和可用模型列表

    Returns:
        OllamaStatus: 服务状态和模型列表
    """
    import os

    from ..models.ollama import OLLAMA_DEFAULT_URL, OllamaModel

    base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)

    try:
        is_available = OllamaModel.is_available(base_url)

        if not is_available:
            return OllamaStatus(
                available=False,
                base_url=base_url,
                models=[],
                error="Ollama 服务未运行，请执行: ollama serve",
            )

        # 获取本地模型列表
        raw_models = OllamaModel.list_models(base_url)

        # 转换为 LocalModelInfo
        models = []
        for m in raw_models:
            # 推断 tier
            name = m.get("name", "")
            tier = "medium"  # 默认
            if ":1.5b" in name or ":7b" in name:
                tier = "low"
            elif ":70b" in name or ":72b" in name or ":33b" in name:
                tier = "high"

            # 格式化大小
            size_bytes = m.get("size", 0)
            if size_bytes:
                if size_bytes > 1e9:
                    size = f"{size_bytes / 1e9:.1f} GB"
                else:
                    size = f"{size_bytes / 1e6:.0f} MB"
            else:
                size = None

            models.append(
                LocalModelInfo(
                    name=name,
                    size=size,
                    modified_at=m.get("modified_at"),
                    tier=tier,
                    description=_get_model_description(name),
                    available=True,
                )
            )

        return OllamaStatus(
            available=True,
            base_url=base_url,
            models=models,
        )

    except Exception as e:
        return OllamaStatus(
            available=False, base_url=base_url, models=[], error=type(e).__name__
        )


@router.get("/models", response_model=list[LocalModelInfo])
async def list_local_models() -> list[LocalModelInfo]:
    """
    列出所有本地可用的模型

    Returns:
        List[LocalModelInfo]: 模型列表
    """
    import os

    from ..models.ollama import OLLAMA_DEFAULT_URL, OllamaModel

    base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)

    if not OllamaModel.is_available(base_url):
        return []

    raw_models = OllamaModel.list_models(base_url)
    models = []

    for m in raw_models:
        name = m.get("name", "")
        tier = "medium"
        if ":1.5b" in name or ":7b" in name:
            tier = "low"
        elif ":70b" in name or ":72b" in name or ":33b" in name:
            tier = "high"

        models.append(
            LocalModelInfo(
                name=name,
                size=m.get("size"),
                modified_at=m.get("modified_at"),
                tier=tier,
                description=_get_model_description(name),
                available=True,
            )
        )

    return models


@router.post("/pull/{model_name}")
async def pull_model(model_name: str) -> dict[str, Any]:
    """
    拉取模型到本地

    Args:
        model_name: 模型名称（如 qwen2:7b）

    Returns:
        拉取状态
    """
    from ..models.ollama import OllamaModel

    try:
        success = OllamaModel.pull_model(model_name)
        if success:
            return {
                "status": "success",
                "message": f"模型 {model_name} 已成功拉取",
            }
        return {
            "status": "failed",
            "message": f"模型 {model_name} 拉取失败",
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/recommended")
async def get_recommended_models() -> list[dict[str, Any]]:
    """
    获取推荐的本地模型列表

    Returns:
        推荐模型列表（按能力分级）
    """
    from ..models.ollama import OLLAMA_MODELS

    result = []
    for tier, models in OLLAMA_MODELS.items():
        for m in models:
            result.append(
                {
                    "name": m["name"],
                    "tier": tier.value,
                    "description": m["desc"],
                    "context_length": m["context"],
                    "installed": False,  # 需要实际检查
                }
            )

    return result


def _get_model_description(model_name: str) -> str:
    """获取模型描述"""
    descriptions = {
        "qwen2": "阿里通义千问2 - 中文能力强",
        "llama3": "Meta Llama 3 - 通用对话模型",
        "mistral": "Mistral AI - 平衡性好",
        "codellama": "Meta Code Llama - 代码生成专用",
        "deepseek-coder": "DeepSeek Coder - 代码生成",
        "gemma": "Google Gemma - 轻量级模型",
        "mixtral": "Mixtral MoE - 高质量输出",
        "phi3": "Microsoft Phi-3 - 小而强",
    }

    for key, desc in descriptions.items():
        if key in model_name.lower():
            return desc

    return "开源大语言模型"
