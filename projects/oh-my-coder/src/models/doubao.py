from __future__ import annotations

"""
字节豆包 (Doubao) 模型适配器

API: https://ark.cn-beijing.volces.com/api/v3
文档: https://www.volcengine.com/docs/82379/1263482

特点：
- 字节跳动自研大模型
- 性价比高
- 支持长上下文
"""

import json
import time
from collections.abc import AsyncIterator

import httpx

from .base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
    Usage,
)

# 豆包模型配置
DOUBAO_MODELS = {
    "low": {
        "name": "doubao-pro-4k",
        "cost_per_1k_prompt": 0.003,
        "cost_per_1k_completion": 0.009,
    },
    "medium": {
        "name": "doubao-pro-32k",
        "cost_per_1k_prompt": 0.006,
        "cost_per_1k_completion": 0.018,
    },
    "high": {
        "name": "doubao-pro-128k",
        "cost_per_1k_prompt": 0.012,
        "cost_per_1k_completion": 0.036,
    },
}


class DoubaoModel(BaseModel):
    """
    字节豆包 (Doubao) 模型适配器

    兼容 OpenAI 格式，base URL: https://ark.cn-beijing.volces.com/api/v3
    """

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
    ):
        if config.base_url is None:
            config.base_url = "https://ark.cn-beijing.volces.com/api/v3"

        tier_key = tier.value
        model_info = DOUBAO_MODELS.get(tier_key, DOUBAO_MODELS["medium"])
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]

        super().__init__(config, tier)
        self._client: httpx.AsyncClient | None = None

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.DOUBAO

    @property
    def model_name(self) -> str:
        return DOUBAO_MODELS[self.tier.value]["name"]

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

    def _format_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        formatted = []
        for msg in messages:
            item: dict[str, str] = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            formatted.append(item)
        return formatted

    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        client = await self._get_client()

        request_body = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }

        if "top_p" in kwargs:
            request_body["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            request_body["stop"] = kwargs["stop"]

        start_time = time.time()

        try:
            response = await client.post("/chat/completions", json=request_body)
            response.raise_for_status()
            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            choice = data["choices"][0]
            content = choice["message"]["content"]

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
                metadata={"response_id": data.get("id")},
            )

        except httpx.HTTPStatusError as e:
            raise DoubaoAPIError(f"豆包 API 错误 ({e.response.status_code}): {e}")
        except httpx.RequestError as e:
            raise DoubaoAPIError(f"网络请求失败: {e}")

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        client = await self._get_client()

        request_body = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        try:
            async with client.stream(
                "POST", "/chat/completions", json=request_body
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPStatusError as e:
            raise DoubaoAPIError(f"豆包 API 错误 ({e.response.status_code}): {e}")
        except httpx.RequestError as e:
            raise DoubaoAPIError(f"网络请求失败: {e}")


class DoubaoAPIError(Exception):
    """字节豆包 API 错误"""
