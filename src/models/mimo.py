"""
小米 MiMo 模型适配器

MiMo API 文档：https://platform.xiaomimimo.com

特点：
1. 完全兼容 OpenAI API 格式
2. 模型：mimo-v2-flash（免费）, mimo-v2-pro
3. 上下文长度：mimo-v2-flash 256K，mimo-v2-pro 1M
4. 支持深度思考、流式输出、函数调用、结构化输出
"""

import json
import os
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

# MiMo 模型配置
MIMO_MODELS = {
    ModelTier.LOW: {
        "name": "mimo-v2-flash",
        "context_length": 256 * 1024,  # 256K
        "cost_per_1k_prompt": 0.0,  # 限时免费
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.MEDIUM: {
        "name": "mimo-v2-flash",
        "context_length": 256 * 1024,
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.HIGH: {
        "name": "mimo-v2-pro",
        "context_length": 1024 * 1024,  # 1M
        "cost_per_1k_prompt": 1.0,  # $1/M tokens
        "cost_per_1k_completion": 3.0,  # $3/M tokens
    },
}


class MimoModel(BaseModel):
    """
    小米 MiMo 模型适配器

    API 兼容 OpenAI 格式，使用 httpx 作为 HTTP 客户端
    """

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
    ):
        """
        Args:
            config: 模型配置
            tier: 性能层级
        """
        # 设置 MiMo 特定配置
        if config.base_url is None:
            config.base_url = "https://api.xiaomimimo.com/v1"

        # 设置成本
        model_info = MIMO_MODELS[tier]
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]

        super().__init__(config, tier)

        # HTTP 客户端（延迟初始化）
        self._client: httpx.AsyncClient | None = None

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.MIMO

    @property
    def model_name(self) -> str:
        return MIMO_MODELS[self.tier]["name"]

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            # 优先使用环境变量 MIMOAPIKEY
            api_key = os.environ.get("MIMOAPIKEY") or self.config.api_key
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _format_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        """将统一消息格式转换为 MiMo API 格式"""
        formatted = []
        for msg in messages:
            item = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            formatted.append(item)
        return formatted

    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        """
        非流式生成

        Args:
            messages: 对话历史
            **kwargs: 可选参数
                - temperature: 温度（0-2）
                - max_tokens: 最大生成 token 数
                - top_p: 核采样参数
                - stop: 停止词列表
        """
        client = await self._get_client()

        # 构建请求体
        request_body = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": False,
        }

        # 添加可选参数
        if "top_p" in kwargs:
            request_body["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            request_body["stop"] = kwargs["stop"]

        # 支持函数调用
        if "tools" in kwargs:
            request_body["tools"] = kwargs["tools"]

        start_time = time.time()

        try:
            response = await client.post(
                "/chat/completions",
                json=request_body,
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            # 解析响应
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "stop")

            # 处理函数调用
            tool_calls = choice["message"].get("tool_calls")

            # 使用统计
            usage_data = data.get("usage", {})
            usage = Usage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            # 更新累计使用量
            self.update_usage(usage)

            return ModelResponse(
                content=content,
                model=self.model_name,
                provider=self.provider,
                tier=self.tier,
                usage=usage,
                finish_reason=finish_reason,
                latency_ms=latency_ms,
                metadata={
                    "response_id": data.get("id"),
                    "created": data.get("created"),
                    "tool_calls": tool_calls,
                },
            )

        except httpx.HTTPStatusError as e:
            # 处理 API 错误
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error", {}).get("message", "HTTP error")
            except Exception:
                error_detail = f"HTTP {e.response.status_code}"

            raise MimoAPIError(
                f"MiMo API 错误 ({e.response.status_code}): {error_detail}"
            )
        except httpx.RequestError as e:
            raise MimoAPIError(f"网络请求失败: {type(e).__name__}")

    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """
        流式生成

        Yields:
            str: 每次生成的文本片段
        """
        client = await self._get_client()

        # 构建请求体
        request_body = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        # 添加可选参数
        if "top_p" in kwargs:
            request_body["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            request_body["stop"] = kwargs["stop"]
        if "tools" in kwargs:
            request_body["tools"] = kwargs["tools"]

        try:
            async with client.stream(
                "POST",
                "/chat/completions",
                json=request_body,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    # 跳过空行和注释
                    if not line or line.startswith(":"):
                        continue

                    # 移除 "data: " 前缀
                    if line.startswith("data: "):
                        line = line[6:]

                    # 结束标记
                    if line == "[DONE]":
                        break

                    # 解析 JSON
                    try:
                        data = json.loads(line)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")

                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error", {}).get("message", "HTTP error")
            except Exception:
                error_detail = f"HTTP {e.response.status_code}"

            raise MimoAPIError(
                f"MiMo API 错误 ({e.response.status_code}): {error_detail}"
            )
        except httpx.RequestError as e:
            raise MimoAPIError(f"网络请求失败: {type(e).__name__}")


class MimoAPIError(Exception):
    """MiMo API 错误"""
