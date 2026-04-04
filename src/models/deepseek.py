"""
DeepSeek 模型适配器

DeepSeek API 文档：https://platform.deepseek.com/api-docs/

特点：
1. 完全兼容 OpenAI API 格式
2. 免费额度：每天 4000 万 token
3. 支持中文，质量接近 GPT-4
4. 价格极低（免费额度内）

模型：
- deepseek-chat：通用对话模型（对应 sonnet）
- deepseek-coder：代码专用模型（代码任务首选）
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


# DeepSeek 模型配置
DEEPSEEK_MODELS = {
    ModelTier.LOW: {
        "name": "deepseek-chat",
        "cost_per_1k_prompt": 0.0,      # 免费额度内
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.MEDIUM: {
        "name": "deepseek-chat",
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
    ModelTier.HIGH: {
        "name": "deepseek-chat",  # 暂时用 chat，后续可接入 DeepSeek-V3
        "cost_per_1k_prompt": 0.0,
        "cost_per_1k_completion": 0.0,
    },
}

# DeepSeek Coder 模型（代码专用）
DEEPSEEK_CODER = {
    "name": "deepseek-coder",
    "cost_per_1k_prompt": 0.0,
    "cost_per_1k_completion": 0.0,
}


class DeepSeekModel(BaseModel):
    """
    DeepSeek 模型适配器
    
    API 兼容 OpenAI 格式，使用 httpx 作为 HTTP 客户端
    """
    
    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
        use_coder: bool = False,
    ):
        """
        Args:
            config: 模型配置
            tier: 性能层级
            use_coder: 是否使用代码专用模型
        """
        # 设置 DeepSeek 特定配置
        if config.base_url is None:
            config.base_url = "https://api.deepseek.com/v1"
        
        # 设置成本
        if use_coder:
            config.cost_per_1k_prompt = DEEPSEEK_CODER["cost_per_1k_prompt"]
            config.cost_per_1k_completion = DEEPSEEK_CODER["cost_per_1k_completion"]
            self._use_coder = True
        else:
            model_info = DEEPSEEK_MODELS[tier]
            config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
            config.cost_per_1k_completion = model_info["cost_per_1k_completion"]
            self._use_coder = False
        
        super().__init__(config, tier)
        
        # HTTP 客户端（延迟初始化）
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.DEEPSEEK
    
    @property
    def model_name(self) -> str:
        if self._use_coder:
            return DEEPSEEK_CODER["name"]
        return DEEPSEEK_MODELS[self.tier]["name"]
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
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
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _format_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """将统一消息格式转换为 DeepSeek API 格式"""
        formatted = []
        for msg in messages:
            item = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            formatted.append(item)
        return formatted
    
    async def generate(
        self,
        messages: List[Message],
        **kwargs
    ) -> ModelResponse:
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
                },
            )
            
        except httpx.HTTPStatusError as e:
            # 处理 API 错误
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error", {}).get("message", str(e))
            except:
                error_detail = str(e)
            
            raise DeepSeekAPIError(
                f"DeepSeek API 错误 ({e.response.status_code}): {error_detail}"
            )
        except httpx.RequestError as e:
            raise DeepSeekAPIError(f"网络请求失败: {e}")
    
    async def stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[str]:
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
                error_detail = error_body.get("error", {}).get("message", str(e))
            except:
                error_detail = str(e)
            
            raise DeepSeekAPIError(
                f"DeepSeek API 错误 ({e.response.status_code}): {error_detail}"
            )
        except httpx.RequestError as e:
            raise DeepSeekAPIError(f"网络请求失败: {e}")


class DeepSeekAPIError(Exception):
    """DeepSeek API 错误"""
    pass
