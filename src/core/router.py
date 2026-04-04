"""
模型路由器 - 智能选择最优模型

核心功能：
1. 根据任务类型选择合适的模型层级
2. 根据成本预算选择提供商
3. 支持故障转移（fallback）
4. 记录路由决策用于优化

设计思路：
原项目使用 haiku/sonnet/opus 三层模型路由，节省 30-50% token。
我们扩展为多提供商路由，优先使用 DeepSeek（免费），必要时才调用付费模型。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Type
from enum import Enum
import os

from ..models.base import (
    BaseModel,
    ModelConfig,
    ModelProvider,
    ModelTier,
    Message,
    ModelResponse,
    Usage,
)
from ..models.deepseek import DeepSeekModel


class TaskType(Enum):
    """任务类型 - 用于路由决策"""

    # 快速任务（LOW tier）
    EXPLORE = "explore"  # 代码库探索
    SIMPLE_QA = "simple_qa"  # 简单问答
    FORMATTING = "formatting"  # 格式化

    # 中等任务（MEDIUM tier）
    CODE_GENERATION = "code_generation"  # 代码生成
    DEBUGGING = "debugging"  # 调试
    TESTING = "testing"  # 测试
    REFACTORING = "refactoring"  # 重构

    # 复杂任务（HIGH tier）
    ARCHITECTURE = "architecture"  # 架构设计
    SECURITY_REVIEW = "security_review"  # 安全审查
    CODE_REVIEW = "code_review"  # 代码审查
    PLANNING = "planning"  # 战略规划


@dataclass
class RouterConfig:
    """路由器配置"""

    # API Keys（从环境变量读取）
    deepseek_api_key: Optional[str] = None
    wenxin_api_key: Optional[str] = None
    tongyi_api_key: Optional[str] = None
    glm_api_key: Optional[str] = None

    # 成本预算（元）
    daily_budget: float = 10.0

    # 故障转移顺序
    fallback_order: List[ModelProvider] = None

    def __post_init__(self):
        # 从环境变量加载 API Keys
        if self.deepseek_api_key is None:
            self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if self.wenxin_api_key is None:
            self.wenxin_api_key = os.getenv("WENXIN_API_KEY")
        if self.tongyi_api_key is None:
            self.tongyi_api_key = os.getenv("TONGYI_API_KEY")
        if self.glm_api_key is None:
            self.glm_api_key = os.getenv("GLM_API_KEY")

        # 默认故障转移顺序
        if self.fallback_order is None:
            self.fallback_order = [
                ModelProvider.DEEPSEEK,  # 优先使用免费
                ModelProvider.WENXIN,  # 文心备用
                ModelProvider.TONGYI,  # 通义备用
                ModelProvider.GLM,  # GLM 备用
            ]


@dataclass
class RoutingDecision:
    """路由决策记录"""

    task_type: TaskType
    selected_provider: ModelProvider
    selected_tier: ModelTier
    reason: str
    estimated_cost: float = 0.0


# 任务类型到模型层级的映射
TASK_TIER_MAPPING = {
    # LOW tier - 快速便宜
    TaskType.EXPLORE: ModelTier.LOW,
    TaskType.SIMPLE_QA: ModelTier.LOW,
    TaskType.FORMATTING: ModelTier.LOW,
    # MEDIUM tier - 平衡
    TaskType.CODE_GENERATION: ModelTier.MEDIUM,
    TaskType.DEBUGGING: ModelTier.MEDIUM,
    TaskType.TESTING: ModelTier.MEDIUM,
    TaskType.REFACTORING: ModelTier.MEDIUM,
    # HIGH tier - 最高质量
    TaskType.ARCHITECTURE: ModelTier.HIGH,
    TaskType.SECURITY_REVIEW: ModelTier.HIGH,
    TaskType.CODE_REVIEW: ModelTier.HIGH,
    TaskType.PLANNING: ModelTier.HIGH,
}


class ModelRouter:
    """
    模型路由器

    核心方法：
    - select(): 选择最优模型
    - route_and_call(): 路由并执行（带故障转移）
    - get_stats(): 获取路由统计
    """

    def __init__(self, config: RouterConfig):
        self.config = config
        self._models: Dict[ModelProvider, Dict[ModelTier, BaseModel]] = {}
        self._decision_history: List[RoutingDecision] = []
        self._total_cost = 0.0

        # 初始化可用模型
        self._initialize_models()

    def _initialize_models(self):
        """初始化所有可用模型"""
        # DeepSeek
        if self.config.deepseek_api_key:
            for tier in ModelTier:
                model_config = ModelConfig(
                    api_key=self.config.deepseek_api_key,
                )
                self._models.setdefault(ModelProvider.DEEPSEEK, {})[tier] = (
                    DeepSeekModel(model_config, tier)
                )

        # 文心一言
        wenxin_secret_key = os.getenv("WENXIN_SECRET_KEY")
        if self.config.wenxin_api_key and wenxin_secret_key:
            from ..models.wenxin import WenxinModel

            for tier in ModelTier:
                model_config = ModelConfig(
                    api_key=self.config.wenxin_api_key,
                )
                self._models.setdefault(ModelProvider.WENXIN, {})[tier] = WenxinModel(
                    model_config, tier, secret_key=wenxin_secret_key
                )

        # 通义千问
        if self.config.tongyi_api_key:
            from ..models.tongyi import TongyiModel

            for tier in ModelTier:
                model_config = ModelConfig(
                    api_key=self.config.tongyi_api_key,
                )
                self._models.setdefault(ModelProvider.TONGYI, {})[tier] = TongyiModel(
                    model_config, tier
                )

        # TODO: 添加其他提供商（GLM）

    def select(
        self,
        task_type: TaskType,
        complexity: str = "medium",  # low, medium, high
        budget_remaining: Optional[float] = None,
    ) -> RoutingDecision:
        """
        选择最优模型

        Args:
            task_type: 任务类型
            complexity: 任务复杂度（可覆盖默认层级）
            budget_remaining: 剩余预算

        Returns:
            RoutingDecision: 路由决策
        """
        # 确定模型层级
        base_tier = TASK_TIER_MAPPING.get(task_type, ModelTier.MEDIUM)

        # 根据复杂度调整层级
        tier = base_tier

        # 层级映射（用于升降级）
        tier_upgrades = {
            ModelTier.LOW: ModelTier.MEDIUM,
            ModelTier.MEDIUM: ModelTier.HIGH,
        }
        tier_downgrades = {
            ModelTier.HIGH: ModelTier.MEDIUM,
            ModelTier.MEDIUM: ModelTier.LOW,
        }

        if complexity == "low" and base_tier in tier_downgrades:
            tier = tier_downgrades[base_tier]  # 降一级
        elif complexity == "high" and base_tier in tier_upgrades:
            tier = tier_upgrades[base_tier]  # 升一级

        # 选择提供商（优先 DeepSeek）
        selected_provider = None
        reason = ""

        for provider in self.config.fallback_order:
            if provider in self._models and tier in self._models[provider]:
                selected_provider = provider
                if provider == ModelProvider.DEEPSEEK:
                    reason = "DeepSeek 免费额度优先"
                else:
                    reason = f"{provider.value} 备用"
                break

        if selected_provider is None:
            raise NoModelAvailableError(f"没有可用的模型处理 {task_type.value} 任务")

        # 估算成本
        model = self._models[selected_provider][tier]
        estimated_cost = model.config.cost_per_1k_prompt * 2  # 粗略估算

        decision = RoutingDecision(
            task_type=task_type,
            selected_provider=selected_provider,
            selected_tier=tier,
            reason=reason,
            estimated_cost=estimated_cost,
        )

        self._decision_history.append(decision)

        return decision

    async def route_and_call(
        self,
        task_type: TaskType,
        messages: List[Message],
        complexity: str = "medium",
        **kwargs,
    ) -> ModelResponse:
        """
        路由并执行（带故障转移）

        Args:
            task_type: 任务类型
            messages: 对话历史
            complexity: 任务复杂度
            **kwargs: 传递给模型的参数

        Returns:
            ModelResponse: 模型响应
        """
        decision = self.select(task_type, complexity)

        # 获取模型
        model = self._models[decision.selected_provider][decision.selected_tier]

        # 重试机制
        last_error = None
        for attempt in range(3):
            try:
                response = await model.generate(messages, **kwargs)

                # 更新成本统计
                actual_cost = model.get_cost(response.usage)
                self._total_cost += actual_cost

                return response

            except Exception as e:
                last_error = e
                if attempt < 2:  # 还有重试机会
                    import asyncio
                    import time

                    time.sleep(2)  # 等待 2 秒后重试

        # 所有重试都失败
        raise last_error

    def get_model(
        self,
        provider: ModelProvider,
        tier: ModelTier,
    ) -> Optional[BaseModel]:
        """直接获取指定模型"""
        return self._models.get(provider, {}).get(tier)

    def get_stats(self) -> Dict:
        """获取路由统计"""
        return {
            "total_requests": len(self._decision_history),
            "total_cost": self._total_cost,
            "provider_distribution": self._count_by_provider(),
            "tier_distribution": self._count_by_tier(),
        }

    def _count_by_provider(self) -> Dict[str, int]:
        """统计各提供商的使用次数"""
        counts = {}
        for decision in self._decision_history:
            provider = decision.selected_provider.value
            counts[provider] = counts.get(provider, 0) + 1
        return counts

    def _count_by_tier(self) -> Dict[str, int]:
        """统计各层级的使用次数"""
        counts = {}
        for decision in self._decision_history:
            tier = decision.selected_tier.value
            counts[tier] = counts.get(tier, 0) + 1
        return counts


class NoModelAvailableError(Exception):
    """没有可用模型"""

    pass
