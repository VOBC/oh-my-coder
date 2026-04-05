"""
MiniMax 模型适配器

API: https://api.minimax.chat
文档: https://www.minimaxi.com/document

特点：
- 长上下文支持（最高 1M tokens）
- 中文理解能力强
- 价格适中
"""

import httpx
from typing import List, AsyncIterator, Dict, Any, Optional
import json
import time

from .base import (
    BaseModel,
    ModelConfig,
    ModelProvider,
    ModelTier,
    Message,
    ModelResponse,
    Usage,
)


# MiniMax 模型配置
MINIMAX_MODELS = {
    "low": {
        "name": "abab6-chat",
        "cost_per_1k_prompt": 0.01,
        "cost_per_1k_completion": 0.02,
    },
    "medium": {
        "name": "abab6.5s-chat",
        "cost_per_1k_prompt": 0.005,
        "cost_per_1k_completion": 0.015,
    },
    "high": {
        "name": "abab6.5g-chat",
        "cost_per_1k_prompt": 0.02,
        "cost_per_1k_completion": 0.05,
    },
}


class MiniMaxModel(BaseModel):
    """
    MiniMax 模型适配器

    API 格式为 MiniMax 私有格式，base URL: https://api.minimax.chat/v1
    """

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
    ):
        if config.base_url is None:
            config.base_url = "https://api.minimax.chat/v1"

        tier_key = tier.value
        model_info = MINIMAX_MODELS.get(tier_key, MINIMAX_MODELS["medium"])
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]

        super().__init__(config, tier)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.MINIMAX

    @property
    def model_name(self) -> str:
        return MINIMAX_MODELS[self.tier.value]["name"]

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _format_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        formatted = []
        for msg in messages:
            item: Dict[str, str] = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            formatted.append(item)
        return formatted

    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        client = await self._get_client()

        request_body = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        if "top_p" in kwargs:
            request_body["top_p"] = kwargs["top_p"]

        start_time = time.time()

        try:
            response = await client.post("/text/chatcompletion_v2", json=request_body)
            response.raise_for_status()
            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            choice = data["choices"][0]
            content = choice["messages"][-1]["content"]

            usage_data = data.get("usage", {})
            usage = Usage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )
            self.update_usage(usage)

            return ModelResponse(
                content=content,
                model=self.model_name,
                provider=self.provider,
                tier=self.tier,
                usage=usage,
                finish_reason=choice.get("finish_reason", "stop"),
                latency_ms=latency_ms,
            )

        except httpx.HTTPStatusError as e:
            raise MiniMaxAPIError(f"MiniMax API 错误 ({e.response.status_code}): {e}")
        except httpx.RequestError as e:
            raise MiniMaxAPIError(f"网络请求失败: {e}")


class MiniMaxAPIError(Exception):
    """MiniMax API 错误"""
    pass
