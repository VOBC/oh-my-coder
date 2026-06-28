from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
from typing import AsyncIterator, Optional

"""
MiniMax 模型适配器

API: https://api.minimax.chat
文档: https://www.minimaxi.com/document

特点：
- 长上下文支持（最高 1M tokens）
- 中文理解能力强
- 价格适中
"""

import time

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

    def _format_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        formatted = []
        for msg in messages:
            item: dict[str, str] = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            if msg.tool_calls:  # assistant 消息的工具调用
                item["tool_calls"] = msg.tool_calls  # type: ignore
            if msg.tool_call_id:  # tool 消息的工具调用 ID
                item["tool_call_id"] = msg.tool_call_id
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
        if "tools" in kwargs and kwargs["tools"]:
            request_body["tools"] = kwargs["tools"]
            request_body["tool_choice"] = kwargs.get("tool_choice", "auto")

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
            tool_calls = choice.get("tool_calls", [])

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
                tool_calls=tool_calls,
            )

        except httpx.HTTPStatusError as e:
            raise MiniMaxAPIError(f"MiniMax API 错误 ({e.response.status_code}): {e}")
        except httpx.RequestError as e:
            raise MiniMaxAPIError(f"网络请求失败: {e}")

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """
        流式生成（SSE）

        MiniMax API 支持流式输出，通过 SSE (Server-Sent Events) 格式返回。
        """
        client = await self._get_client()

        request_body = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }
        if "tools" in kwargs and kwargs["tools"]:
            request_body["tools"] = kwargs["tools"]
            request_body["tool_choice"] = kwargs.get("tool_choice", "auto")

        if "top_p" in kwargs:
            request_body["top_p"] = kwargs["top_p"]

        try:
            async with client.stream("POST", "/text/chatcompletion_v2", json=request_body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":") or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        try:
                            import json
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            raise MiniMaxAPIError(f"MiniMax API 错误 ({e.response.status_code}): {e}")
        except httpx.RequestError as e:
            raise MiniMaxAPIError(f"网络请求失败: {e}")


class MiniMaxAPIError(Exception):
    """MiniMax API 错误"""
