"""
Ollama 本地模型适配器

支持 Ollama 本地部署的开源模型（如 Qwen2, Llama3, Mistral 等）。
零成本、隐私保护、离线可用。

使用方式：
1. 安装 Ollama: https://ollama.ai/
2. 拉取模型: ollama pull qwen2:7b
3. 运行: ollama serve (默认 http://localhost:11434)
4. 配置: export OLLAMA_BASE_URL=http://localhost:11434

支持的模型：
- qwen2:7b / qwen2:72b - 阿里通义千问2
- llama3:8b / llama3:70b - Meta Llama 3
- mistral:7b - Mistral AI
- codellama:7b - Meta Code Llama
- deepseek-coder:6.7b - DeepSeek 代码模型
"""

import json
import subprocess
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelResponse,
    ModelTier,
    Usage,
)

# Ollama 默认配置
OLLAMA_DEFAULT_URL = "http://localhost:11434"

# 常用本地模型列表（按能力分级）
OLLAMA_MODELS = {
    # LOW tier - 快速、轻量
    ModelTier.LOW: [
        {"name": "qwen2:1.5b", "desc": "通义千问 1.5B", "context": 32768},
        {"name": "llama3:8b", "desc": "Llama 3 8B", "context": 8192},
        {"name": "mistral:7b", "desc": "Mistral 7B", "context": 32768},
        {"name": "gemma:7b", "desc": "Google Gemma 7B", "context": 8192},
    ],
    # MEDIUM tier - 平衡
    ModelTier.MEDIUM: [
        {"name": "qwen2:7b", "desc": "通义千问 7B", "context": 32768},
        {"name": "llama3:8b-instruct", "desc": "Llama 3 8B Instruct", "context": 8192},
        {
            "name": "deepseek-coder:6.7b",
            "desc": "DeepSeek Coder 6.7B",
            "context": 16384,
        },
        {"name": "codellama:7b", "desc": "Code Llama 7B", "context": 16384},
    ],
    # HIGH tier - 高质量（需要更多显存）
    ModelTier.HIGH: [
        {"name": "qwen2:72b", "desc": "通义千问 72B", "context": 32768},
        {"name": "llama3:70b", "desc": "Llama 3 70B", "context": 8192},
        {"name": "deepseek-coder:33b", "desc": "DeepSeek Coder 33B", "context": 16384},
        {"name": "mixtral:8x7b", "desc": "Mixtral 8x7B MoE", "context": 32768},
    ],
}

# 模型到层级映射（动态生成）
_MODEL_TIER_MAP: dict[str, ModelTier] = {}
for tier, models in OLLAMA_MODELS.items():
    for m in models:
        _MODEL_TIER_MAP[m["name"]] = tier


class OllamaModel(BaseModel):
    """
    Ollama 本地模型适配器

    特点：
    - 零成本：完全本地运行，无 API 费用
    - 隐私保护：数据不出本地
    - 离线可用：无需网络连接
    - 支持多种开源模型
    """

    provider = "ollama"

    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
        model_name: str = "qwen2:7b",
    ):
        """
        Args:
            config: 模型配置
            tier: 性能层级
            model_name: Ollama 模型名称（如 qwen2:7b）
        """
        # 设置 Ollama 特定配置
        config.provider = "ollama"
        if config.base_url is None:
            config.base_url = OLLAMA_DEFAULT_URL

        self.model_name = model_name
        self.base_url = config.base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

        # 推断 tier
        if model_name in _MODEL_TIER_MAP:
            tier = _MODEL_TIER_MAP[model_name]

        super().__init__(config, tier)

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self._client

    async def _generate(
        self,
        messages: list[Message],
        stream: bool = False,
        **kwargs,
    ) -> ModelResponse:
        """
        调用 Ollama API 生成响应

        Ollama API 文档: https://github.com/ollama/ollama/blob/main/docs/api.md
        """
        client = await self._get_client()
        start_time = time.time()

        # 转换消息格式
        ollama_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        # 构建 Ollama API 请求
        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": stream,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "top_k": kwargs.get("top_k", 40),
                "num_ctx": kwargs.get("max_tokens", 4096),
            },
        }

        try:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # 解析响应
            content = data.get("message", {}).get("content", "")
            model = data.get("model", self.model_name)

            # Ollama 返回的 token 统计
            eval_count = data.get("eval_count", 0)  # 生成的 token 数
            prompt_eval_count = data.get("prompt_eval_count", 0)  # 输入的 token 数

            usage = Usage(
                prompt_tokens=prompt_eval_count,
                completion_tokens=eval_count,
                total_tokens=prompt_eval_count + eval_count,
            )

            latency_ms = (time.time() - start_time) * 1000

            return ModelResponse(
                content=content,
                model=model,
                provider=self.provider,
                tier=self.tier,
                usage=usage,
                finish_reason="stop",
                latency_ms=latency_ms,
                metadata={
                    "local": True,
                    "base_url": self.base_url,
                },
            )

        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Ollama API 错误: {e.response.status_code} - {e.response.text}"
            )
        except httpx.ConnectError:
            raise RuntimeError(
                f"无法连接到 Ollama 服务 ({self.base_url})，"
                "请确保 Ollama 已启动：ollama serve"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama 调用失败: {e}")

    async def _generate_stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式生成响应"""
        client = await self._get_client()

        # 转换消息格式
        ollama_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
            },
        }

        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.config.timeout,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.ConnectError:
            raise RuntimeError(f"无法连接到 Ollama 服务 ({self.base_url})")

    async def complete(
        self,
        messages: list[Message],
        **kwargs,
    ) -> ModelResponse:
        """完成对话（非流式）"""
        return await self._generate(messages, stream=False, **kwargs)

    async def stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式完成对话"""
        async for chunk in self._generate_stream(messages, **kwargs):
            yield chunk

    @staticmethod
    def is_available(base_url: str = OLLAMA_DEFAULT_URL) -> bool:
        """
        检查 Ollama 服务是否可用

        Args:
            base_url: Ollama API 地址

        Returns:
            bool: 服务是否可用
        """
        try:
            import httpx

            response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def list_models(base_url: str = OLLAMA_DEFAULT_URL) -> list[dict[str, Any]]:
        """
        列出本地可用的 Ollama 模型

        Args:
            base_url: Ollama API 地址

        Returns:
            模型列表，每个模型包含 name, size, modified_at 等信息
        """
        try:
            import httpx

            response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
            return []
        except Exception:
            return []

    @staticmethod
    def pull_model(model_name: str, base_url: str = OLLAMA_DEFAULT_URL) -> bool:
        """
        拉取模型到本地

        Args:
            model_name: 模型名称（如 qwen2:7b）
            base_url: Ollama API 地址

        Returns:
            bool: 是否成功
        """
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=600,  # 10 分钟超时
            )
            return result.returncode == 0
        except Exception:
            return False

    def __repr__(self) -> str:
        return (
            f"OllamaModel(model={self.model_name}, "
            f"tier={self.tier.value}, "
            f"base_url={self.base_url})"
        )


# Ollama Provider 标识符
OLLAMA_PROVIDER = "ollama"


def create_ollama_model(
    model_name: str = "qwen2:7b",
    base_url: str = OLLAMA_DEFAULT_URL,
    tier: ModelTier | None = None,
) -> OllamaModel:
    """
    创建 Ollama 模型实例的便捷函数

    Args:
        model_name: 模型名称
        base_url: Ollama API 地址
        tier: 性能层级（不指定则自动推断）

    Returns:
        OllamaModel 实例
    """
    config = ModelConfig(
        api_key="",  # Ollama 不需要 API Key
        base_url=base_url,
    )

    # 自动推断 tier
    if tier is None:
        tier = _MODEL_TIER_MAP.get(model_name, ModelTier.MEDIUM)

    return OllamaModel(config, tier=tier, model_name=model_name)
