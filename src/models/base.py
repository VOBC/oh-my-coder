"""
模型基类 - 定义所有 LLM 提供商的统一接口

设计原则：
1. 异步优先 - 所有 API 调用都是异步的
2. 流式支持 - 支持流式输出，提升用户体验
3. 统一错误处理 - 捕获各提供商的差异
4. Token 计数 - 标准化的 token 使用统计
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Optional, Dict, Any, List
import time


class ModelTier(Enum):
    """模型性能层级 - 对应原项目的 haiku/sonnet/opus 三层"""
    LOW = "low"       # 快速、便宜 - 对应 haiku
    MEDIUM = "medium" # 平衡 - 对应 sonnet
    HIGH = "high"     # 最高质量 - 对应 opus


class ModelProvider(Enum):
    """支持的模型提供商"""
    DEEPSEEK = "deepseek"
    WENXIN = "wenxin"      # 文心一言
    TONGYI = "tongyi"      # 通义千问
    GLM = "glm"            # ChatGLM
    OPENAI = "openai"      # 备用
    CLAUDE = "claude"      # 备用


@dataclass
class Message:
    """统一的消息格式"""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None  # 用于多轮对话中的角色标识


@dataclass
class Usage:
    """Token 使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class ModelResponse:
    """统一的响应格式"""
    content: str
    model: str
    provider: ModelProvider
    tier: ModelTier
    usage: Usage = field(default_factory=Usage)
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelConfig:
    """模型配置"""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 60.0
    
    # 重试策略
    max_retries: int = 5
    retry_delay: float = 2.0
    timeout: float = 120.0  # 增加超时时间到 120 秒
    
    # 成本控制
    cost_per_1k_prompt: float = 0.0    # 每 1k prompt token 的成本（元）
    cost_per_1k_completion: float = 0.0  # 每 1k completion token 的成本（元）


class BaseModel(ABC):
    """
    所有模型适配器的基类
    
    职责：
    1. 定义统一的 API 接口
    2. 提供通用的错误处理和重试逻辑
    3. 支持流式和非流式两种调用方式
    """
    
    def __init__(self, config: ModelConfig, tier: ModelTier):
        self.config = config
        self.tier = tier
        self._total_usage = Usage()
    
    @property
    @abstractmethod
    def provider(self) -> ModelProvider:
        """返回提供商标识"""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """返回实际使用的模型名称"""
        pass
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        **kwargs
    ) -> ModelResponse:
        """
        非流式生成
        
        Args:
            messages: 对话历史
            **kwargs: 模型特定参数
            
        Returns:
            ModelResponse: 统一格式的响应
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式生成
        
        Args:
            messages: 对话历史
            **kwargs: 模型特定参数
            
        Yields:
            str: 每次生成的文本片段
        """
        pass
    
    async def count_tokens(self, text: str) -> int:
        """
        计算 token 数量（子类可覆盖提供更精确的实现）
        
        默认实现：中文字符约 1.5 token，英文单词约 1 token
        """
        # 简化估算
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars / 4)
    
    def get_cost(self, usage: Usage) -> float:
        """计算本次调用的成本（元）"""
        prompt_cost = (usage.prompt_tokens / 1000) * self.config.cost_per_1k_prompt
        completion_cost = (usage.completion_tokens / 1000) * self.config.cost_per_1k_completion
        return prompt_cost + completion_cost
    
    def update_usage(self, usage: Usage):
        """更新累计使用量"""
        self._total_usage = self._total_usage + usage
    
    def get_total_usage(self) -> Usage:
        """获取累计使用量"""
        return self._total_usage
    
    def reset_usage(self):
        """重置使用统计"""
        self._total_usage = Usage()
    
    def _build_system_prompt(self, system: Optional[str] = None) -> Optional[Message]:
        """构建系统提示词"""
        if system:
            return Message(role="system", content=system)
        return None
    
    async def _execute_with_retry(
        self,
        func,
        *args,
        **kwargs
    ):
        """带重试的执行"""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
        
        raise last_error


# 导入 asyncio（用于重试逻辑）
import asyncio
