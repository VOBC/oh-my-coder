"""
文心一言 (Wenxin) 模型适配器

百度文心一言 API 文档：https://cloud.baidu.com/doc/WENXINWORKSHOP/index.html

特点：
1. 百度出品，中文能力强
2. 支持多轮对话
3. 多种模型可选（ERNIE-Bot-4, ERNIE-Bot, ERNIE-Bot-turbo）

模型：
- ERNIE-Bot-4：最强模型（对应 HIGH tier）
- ERNIE-Bot：通用模型（对应 MEDIUM tier）
- ERNIE-Bot-turbo：快速模型（对应 LOW tier）
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


# 文心一言模型配置
WENXIN_MODELS = {
    ModelTier.LOW: {
        "name": "eb-instant",  # ERNIE-Bot-turbo
        "cost_per_1k_prompt": 0.004,
        "cost_per_1k_completion": 0.008,
    },
    ModelTier.MEDIUM: {
        "name": "completions_pro",  # ERNIE-Bot
        "cost_per_1k_prompt": 0.012,
        "cost_per_1k_completion": 0.012,
    },
    ModelTier.HIGH: {
        "name": "completions",  # ERNIE-Bot-4
        "cost_per_1k_prompt": 0.12,
        "cost_per_1k_completion": 0.12,
    },
}

# 文心一言 API 端点
WENXIN_API_URL = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat"


class WenxinModel(BaseModel):
    """
    文心一言模型适配器
    
    注意：文心一言 API 需要 Access Token，通过 API Key 和 Secret Key 获取
    """
    
    def __init__(
        self,
        config: ModelConfig,
        tier: ModelTier = ModelTier.MEDIUM,
        secret_key: Optional[str] = None,
    ):
        """
        Args:
            config: 模型配置（api_key 为 API Key）
            tier: 性能层级
            secret_key: Secret Key（用于获取 Access Token）
        """
        # 设置文心一言特定配置
        model_info = WENXIN_MODELS[tier]
        config.cost_per_1k_prompt = model_info["cost_per_1k_prompt"]
        config.cost_per_1k_completion = model_info["cost_per_1k_completion"]
        
        super().__init__(config, tier)
        
        self.secret_key = secret_key
        self._access_token: Optional[str] = None
        self._token_expire_time: float = 0
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider(self) -> ModelProvider:
        return ModelProvider.WENXIN
    
    @property
    def model_name(self) -> str:
        return WENXIN_MODELS[self.tier]["name"]
    
    async def _get_access_token(self) -> str:
        """获取 Access Token（有缓存）"""
        # 检查缓存是否有效
        if self._access_token and time.time() < self._token_expire_time:
            return self._access_token
        
        # 获取新的 Access Token
        client = await self._get_client()
        
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.config.api_key}&client_secret={self.secret_key}"
        
        response = await client.post(url)
        response.raise_for_status()
        
        data = response.json()
        self._access_token = data["access_token"]
        self._token_expire_time = time.time() + data["expires_in"] - 300  # 提前 5 分钟过期
        
        return self._access_token
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
            )
        return self._client
    
    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _format_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """
        将统一消息格式转换为文心一言 API 格式
        
        注意：文心一言不支持 system role，需要合并到第一条 user 消息
        """
        formatted = []
        system_content = ""
        
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                item = {"role": msg.role, "content": msg.content}
                formatted.append(item)
        
        # 如果有 system 内容，合并到第一条 user 消息
        if system_content and formatted and formatted[0]["role"] == "user":
            formatted[0]["content"] = f"{system_content}\n\n{formatted[0]['content']}"
        
        return formatted
    
    async def generate(
        self,
        messages: List[Message],
        **kwargs
    ) -> ModelResponse:
        """非流式生成"""
        client = await self._get_client()
        access_token = await self._get_access_token()
        
        # 构建请求体
        request_body = {
            "messages": self._format_messages(messages),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }
        
        # 添加可选参数
        if "max_tokens" in kwargs:
            request_body["max_output_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            request_body["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            request_body["stop"] = kwargs["stop"]
        
        url = f"{WENXIN_API_URL}/{self.model_name}?access_token={access_token}"
        
        start_time = time.time()
        
        try:
            response = await client.post(url, json=request_body)
            response.raise_for_status()
            
            data = response.json()
            latency_ms = (time.time() - start_time) * 1000
            
            # 解析响应
            content = data.get("result", "")
            finish_reason = data.get("finish_reason", "stop")
            
            # 使用统计
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
                finish_reason=finish_reason,
                latency_ms=latency_ms,
                metadata={
                    "id": data.get("id"),
                    "created": data.get("created"),
                },
            )
            
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error_msg", str(e))
            except:
                error_detail = str(e)
            
            raise WenxinAPIError(f"文心一言 API 错误: {error_detail}")
        except httpx.RequestError as e:
            raise WenxinAPIError(f"网络请求失败: {e}")
    
    async def stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[str]:
        """流式生成"""
        client = await self._get_client()
        access_token = await self._get_access_token()
        
        request_body = {
            "messages": self._format_messages(messages),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }
        
        url = f"{WENXIN_API_URL}/{self.model_name}?access_token={access_token}"
        
        try:
            async with client.stream("POST", url, json=request_body) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    # 解析 SSE 数据
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    try:
                        data = json.loads(line)
                        result = data.get("result", "")
                        if result:
                            yield result
                    except json.JSONDecodeError:
                        continue
                        
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get("error_msg", str(e))
            except:
                error_detail = str(e)
            
            raise WenxinAPIError(f"文心一言 API 错误: {error_detail}")
        except httpx.RequestError as e:
            raise WenxinAPIError(f"网络请求失败: {e}")


class WenxinAPIError(Exception):
    """文心一言 API 错误"""
    pass
