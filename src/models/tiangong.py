"""
天工AI (Tiangong) 模型适配器

API 地址：https://model-platform.tiangong.cn
文档：https://model-platform.tiangong.cn/document

特点：
- 昆仑万维出品
- 中文理解能力强
- 支持超长上下文
- 兼容 OpenAI 格式
"""

import json
import time
from collections.abc import AsyncIterator
from typing import Any

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

# 天工AI 模型配置
TIANGONG_MODELS = {
    ModelTier.LOW: {
        "name": "skywork-v1.0",
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.MEDIUM: {
        "name": "skywork-v1.0",
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.HIGH: {
        "name": "skywork-v1.0",
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
}


class TiangongModel(BaseModel):
    """天工AI 模型适配器，兼容 OpenAI 格式"""

    def __init__(self, config: ModelConfig, tier: ModelTier = ModelTier.MEDIUM):
        if config.base_url is None:
            config.base_url = "https://model-platform.tiangong.cn/v1"
        model_info = TIANGONG_MODELS[tier]
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]
        super().__init__(config, tier)
        self._client: httpx.AsyncClient | None = None

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.TIANGONG

    @property
    def model_name(self) -> str:
        return TIANGONG_MODELS[self.tier]["name"]

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
            item = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            formatted.append(item)
        return formatted

    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        client = await self._get_client()
        request_body: dict[str, Any] = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": False,
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
            raise TiangongAPIError(f"天工AI API 错误 ({e.response.status_code}): {e}")
        except httpx.RequestError as e:
            raise TiangongAPIError(f"网络请求失败: {e}")

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        client = await self._get_client()
        request_body: dict[str, Any] = {
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
                        content = data["choices"][0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
        except httpx.HTTPStatusError as e:
            raise TiangongAPIError(f"天工AI API 错误 ({e.response.status_code}): {e}")
        except httpx.RequestError as e:
            raise TiangongAPIError(f"网络请求失败: {e}")


class TiangongAPIError(Exception):
    """天工AI API 错误"""
