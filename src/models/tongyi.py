"""
通义千问 (Tongyi) 模型适配器

阿里云通义千问 API 文档：https://help.aliyun.com/zh/dashscope/

特点：
1. 阿里云出品，中文能力强
2. 支持多轮对话
3. 多种模型可选（qwen-max, qwen-plus, qwen-turbo）

模型：
- qwen-max：最强模型（对应 HIGH tier）
- qwen-plus：通用模型（对应 MEDIUM tier）
- qwen-turbo：快速模型（对应 LOW tier）
"""

import json
import time
from collections.abc import AsyncIterator

import httpx

from src.utils.safe_executor import safe_execute

from .base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
    Usage,
)

# 通义千问模型配置
TONGYI_MODELS = {
    ModelTier.LOW: {
        "name": "qwen-turbo",
        "cost_per_1k_prompt": 0.004,
        "cost_per_1k_completion": 0.012,
    },
    ModelTier.MEDIUM: {
        "name": "qwen-plus",
        "cost_per_1k_prompt": 0.008,
        "cost_per_1k_completion": 0.02,
    },
    ModelTier.HIGH: {
        "name": "qwen-max",
        "cost_per_1k_prompt": 0.04,
        "cost_per_1k_completion": 0.12,
    },
}

# 通义千问 API 端点
TONGYI_API_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
)


class TongyiModel(BaseModel):
    """
    通义千问模型适配器

    API 兼容 OpenAI 格式，使用 DashScope API
    """

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
    ):
        """
        Args:
            config: 模型配置（api_key 为 DashScope API Key）
            tier: 性能层级
        """
        # 设置通义千问特定配置
        model_info = TONGYI_MODELS[tier]
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]

        super().__init__(config, tier)

        self._client: httpx.AsyncClient | None = None

    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.TONGYI

    @property
    def model_name(self) -> str:
        return TONGYI_MODELS[self.tier]["name"]

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
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
        """将统一消息格式转换为通义千问 API 格式"""
        formatted = []
        for msg in messages:
            item = {"role": msg.role, "content": msg.content}
            formatted.append(item)
        return formatted

    @safe_execute(max_attempts=3, timeout=30.0)
    async def generate(self, messages: list[Message], **kwargs) -> ModelResponse:
        """非流式生成"""
        client = await self._get_client()

        # 构建请求体
        request_body = {
            "model": self.model_name,
            "input": {
                "messages": self._format_messages(messages),
            },
            "parameters": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            },
        }

        start_time = time.time()

        try:
            response = await client.post(
                TONGYI_API_URL,
                json=request_body,
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            # 解析响应
            output = data.get("output", {})
            content = output.get("text", "")
            finish_reason = output.get("finish_reason", "stop")

            # 使用统计
            usage_data = data.get("usage", {})
            usage = Usage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

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
                    "request_id": data.get("request_id"),
                },
            )

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("message", "HTTP error")
            except Exception:
                error_detail = f"HTTP {e.response.status_code}"

            raise TongyiAPIError(f"通义千问 API 错误: {error_detail}")
        except httpx.RequestError as e:
            raise TongyiAPIError(f"网络请求失败: {type(e).__name__}")

    @safe_execute(max_attempts=3, timeout=30.0)
    async def stream(self, messages: list[Message], **kwargs) -> AsyncIterator[str]:
        """流式生成"""
        client = await self._get_client()

        request_body = {
            "model": self.model_name,
            "input": {
                "messages": self._format_messages(messages),
            },
            "parameters": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "incremental_output": True,  # 增量输出
            },
        }

        try:
            async with client.stream(
                "POST",
                TONGYI_API_URL,
                json=request_body,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        output = data.get("output", {})
                        content = output.get("text", "")

                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("message", "HTTP error")
            except Exception:
                error_detail = f"HTTP {e.response.status_code}"

            raise TongyiAPIError(f"通义千问 API 错误: {error_detail}")
        except httpx.RequestError as e:
            raise TongyiAPIError(f"网络请求失败: {type(e).__name__}")


class TongyiAPIError(Exception):
    """通义千问 API 错误"""

    pass
