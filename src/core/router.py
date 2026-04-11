"""
模型路由器 - 智能选择最优模型

核心功能：
1. 根据任务类型选择合适的模型层级
2. 根据成本预算选择提供商
3. 支持故障转移（fallback）
4. 记录路由决策用于优化
5. 响应缓存（避免重复请求）
6. 增强日志和错误处理

设计思路：
原项目使用 haiku/sonnet/opus 三层模型路由，节省 30-50% token。
我们扩展为多提供商路由，优先使用 DeepSeek（免费），必要时才调用付费模型。
"""

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelResponse,
    ModelTier,
    Usage,
)
from ..models.deepseek import DeepSeekModel

# ============================================================
# Logger
# ============================================================
logger = logging.getLogger("omc.router")


# ============================================================
# Task Type Enum
# ============================================================
class TaskType:
    """任务类型 - 用于路由决策（使用类避免 Enum 序列化问题）"""

    EXPLORE = "explore"
    SIMPLE_QA = "simple_qa"
    FORMATTING = "formatting"
    CODE_GENERATION = "code_generation"
    DEBUGGING = "debugging"
    TESTING = "testing"
    REFACTORING = "refactoring"
    ARCHITECTURE = "architecture"
    SECURITY_REVIEW = "security_review"
    CODE_REVIEW = "code_review"
    PLANNING = "planning"

    @classmethod
    def all(cls) -> List[str]:
        return [
            cls.EXPLORE,
            cls.SIMPLE_QA,
            cls.FORMATTING,
            cls.CODE_GENERATION,
            cls.DEBUGGING,
            cls.TESTING,
            cls.REFACTORING,
            cls.ARCHITECTURE,
            cls.SECURITY_REVIEW,
            cls.CODE_REVIEW,
            cls.PLANNING,
        ]


# ============================================================
# 任务类型到模型层级的映射
# ============================================================
_TASK_TIER_MAPPING: Dict[str, str] = {
    # LOW tier - 快速便宜
    TaskType.EXPLORE: "low",
    TaskType.SIMPLE_QA: "low",
    TaskType.FORMATTING: "low",
    # MEDIUM tier - 平衡
    TaskType.CODE_GENERATION: "medium",
    TaskType.DEBUGGING: "medium",
    TaskType.TESTING: "medium",
    TaskType.REFACTORING: "medium",
    # HIGH tier - 最高质量
    TaskType.ARCHITECTURE: "high",
    TaskType.SECURITY_REVIEW: "high",
    TaskType.CODE_REVIEW: "high",
    TaskType.PLANNING: "high",
}


# ============================================================
# Router Config
# ============================================================
@dataclass
class RouterConfig:
    """路由器配置"""

    # API Keys（从环境变量读取）
    deepseek_api_key: Optional[str] = None
    wenxin_api_key: Optional[str] = None
    tongyi_api_key: Optional[str] = None
    glm_api_key: Optional[str] = None
    minimax_api_key: Optional[str] = None
    kimi_api_key: Optional[str] = None
    hunyuan_api_key: Optional[str] = None
    doubao_api_key: Optional[str] = None

    # 成本预算（元）
    daily_budget: float = 10.0

    # 故障转移顺序
    fallback_order: List[str] = field(default_factory=list)

    # 缓存配置
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 分钟缓存
    cache_max_entries: int = 100

    def __post_init__(self):
        # 从环境变量加载 API Keys
        self.deepseek_api_key = self.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        self.wenxin_api_key = self.wenxin_api_key or os.getenv("WENXIN_API_KEY")
        self.tongyi_api_key = self.tongyi_api_key or os.getenv("TONGYI_API_KEY")
        self.glm_api_key = self.glm_api_key or os.getenv("GLM_API_KEY")
        self.minimax_api_key = self.minimax_api_key or os.getenv("MINIMAX_API_KEY")
        self.kimi_api_key = self.kimi_api_key or os.getenv("KIMI_API_KEY")
        self.hunyuan_api_key = self.hunyuan_api_key or os.getenv("HUNYUAN_API_KEY")
        self.doubao_api_key = self.doubao_api_key or os.getenv("DOUBAO_API_KEY")

        # 默认故障转移顺序（优先免费/便宜的）
        if not self.fallback_order:
            self.fallback_order = [
                "deepseek",  # 免费额度高
                "kimi",  # 长上下文
                "doubao",  # 性价比高
                "minimax",  # MiniMax
                "glm",  # 智谱
                "tongyi",  # 通义千问
                "wenxin",  # 文心一言
                "hunyuan",  # 混元
            ]


# ============================================================
# Routing Decision
# ============================================================
@dataclass
class RoutingDecision:
    """路由决策记录"""

    task_type: str
    selected_provider: str
    selected_tier: str  # "low" | "medium" | "high"
    reason: str
    estimated_cost: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# Response Cache
# ============================================================
class ResponseCache:
    """
    简单 LRU 缓存，按消息内容哈希存储响应

    适用场景：
    - 重复的探索请求
    - 相同的分析请求（项目结构未变时）
    - 相同问题的简单 QA
    """

    def __init__(self, max_entries: int = 100, ttl_seconds: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []  # 简单 FIFO（非真实 LRU，但够用）
        self._max_entries = max_entries
        self._ttl = ttl_seconds

    def _make_key(self, messages: List[Message]) -> str:
        """根据消息内容生成缓存 key"""
        content = "".join(m.content for m in messages)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, messages: List[Message]) -> Optional[ModelResponse]:
        """获取缓存的响应"""
        key = self._make_key(messages)
        entry = self._cache.get(key)

        if entry is None:
            return None

        # 检查是否过期
        age = (datetime.now() - entry["cached_at"]).total_seconds()
        if age > self._ttl:
            del self._cache[key]
            self._order.remove(key)
            return None

        logger.debug(f"Cache hit: {key[:8]}... (age={age:.1f}s)")
        return entry["response"]

    def set(self, messages: List[Message], response: ModelResponse) -> None:
        """缓存响应"""
        key = self._make_key(messages)

        # LRU 淘汰
        if len(self._cache) >= self._max_entries and key not in self._cache:
            oldest = self._order.pop(0)
            del self._cache[oldest]

        self._cache[key] = {
            "response": response,
            "cached_at": datetime.now(),
        }
        if key not in self._order:
            self._order.append(key)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._order.clear()

    def stats(self) -> Dict[str, int]:
        """缓存统计"""
        total = len(self._cache)
        expired = sum(
            1
            for e in self._cache.values()
            if (datetime.now() - e["cached_at"]).total_seconds() > self._ttl
        )
        return {
            "total": total,
            "active": total - expired,
            "max": self._max_entries,
            "ttl_seconds": self._ttl,
        }


# ============================================================
# Model Router
# ============================================================
class ModelRouter:
    """
    模型路由器

    核心方法：
    - select():       选择最优模型
    - route_and_call(): 路由并执行（带故障转移 + 缓存）
    - get_stats():    获取路由统计
    """

    def __init__(self, config: Optional[RouterConfig] = None):
        self.config = config or RouterConfig()
        self._models: Dict[str, Dict[str, BaseModel]] = {}
        self._decision_history: List[RoutingDecision] = []
        self._total_cost = 0.0
        self._cache = (
            ResponseCache(
                max_entries=self.config.cache_max_entries,
                ttl_seconds=self.config.cache_ttl_seconds,
            )
            if self.config.cache_enabled
            else None
        )

        self._initialize_models()

    def _initialize_models(self) -> None:
        """初始化所有可用模型（惰性初始化）"""
        # DeepSeek
        if self.config.deepseek_api_key:
            try:
                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.deepseek_api_key)
                    self._models.setdefault("deepseek", {})[tier] = DeepSeekModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("DeepSeek 模型已初始化")
            except Exception as e:
                logger.warning(f"DeepSeek 初始化失败: {e}")

        # 文心一言
        wenxin_secret = os.getenv("WENXIN_SECRET_KEY")
        if self.config.wenxin_api_key and wenxin_secret:
            try:
                from ..models.wenxin import WenxinModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.wenxin_api_key)
                    self._models.setdefault("wenxin", {})[tier] = WenxinModel(
                        cfg, ModelTier(tier), secret_key=wenxin_secret
                    )
                logger.info("文心一言模型已初始化")
            except Exception as e:
                logger.warning(f"文心一言初始化失败: {e}")

        # 通义千问
        if self.config.tongyi_api_key:
            try:
                from ..models.tongyi import TongyiModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.tongyi_api_key)
                    self._models.setdefault("tongyi", {})[tier] = TongyiModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("通义千问模型已初始化")
            except Exception as e:
                logger.warning(f"通义千问初始化失败: {e}")

        # 智谱 GLM
        if self.config.glm_api_key:
            try:
                from ..models.glm import GLMModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.glm_api_key)
                    self._models.setdefault("glm", {})[tier] = GLMModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("智谱 GLM 模型已初始化")
            except Exception as e:
                logger.warning(f"智谱 GLM 初始化失败: {e}")

        # MiniMax
        if self.config.minimax_api_key:
            try:
                from ..models.minimax import MiniMaxModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.minimax_api_key)
                    self._models.setdefault("minimax", {})[tier] = MiniMaxModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("MiniMax 模型已初始化")
            except Exception as e:
                logger.warning(f"MiniMax 初始化失败: {e}")

        # Kimi
        if self.config.kimi_api_key:
            try:
                from ..models.kimi import KimiModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.kimi_api_key)
                    self._models.setdefault("kimi", {})[tier] = KimiModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("Kimi 模型已初始化")
            except Exception as e:
                logger.warning(f"Kimi 初始化失败: {e}")

        # 腾讯混元
        if self.config.hunyuan_api_key:
            try:
                from ..models.hunyuan import HunyuanModel

                hunyuan_secret = os.getenv("HUNYUAN_SECRET_KEY")
                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.hunyuan_api_key)
                    self._models.setdefault("hunyuan", {})[tier] = HunyuanModel(
                        cfg, ModelTier(tier), secret_key=hunyuan_secret
                    )
                logger.info("腾讯混元模型已初始化")
            except Exception as e:
                logger.warning(f"腾讯混元初始化失败: {e}")

        # 字节豆包
        if self.config.doubao_api_key:
            try:
                from ..models.doubao import DoubaoModel

                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key=self.config.doubao_api_key)
                    self._models.setdefault("doubao", {})[tier] = DoubaoModel(
                        cfg, ModelTier(tier)
                    )
                logger.info("字节豆包模型已初始化")
            except Exception as e:
                logger.warning(f"字节豆包初始化失败: {e}")

        # 记录可用提供商
        available = list(self._models.keys())
        logger.info(f"可用模型提供商: {available or '无'}")

    def select(
        self,
        task_type: str,
        complexity: str = "medium",
        budget_remaining: Optional[float] = None,
    ) -> RoutingDecision:
        """
        选择最优模型

        Args:
            task_type: 任务类型
            complexity: 任务复杂度（low/medium/high，可覆盖默认层级）
            budget_remaining: 剩余预算（元）

        Returns:
            RoutingDecision: 路由决策
        """
        # 确定模型层级
        base_tier = _TASK_TIER_MAPPING.get(task_type, "medium")

        tier = base_tier
        # 层级升降
        if complexity == "low" and base_tier == "high":
            tier = "medium"
        elif complexity == "low" and base_tier == "medium":
            tier = "low"
        elif complexity == "high" and base_tier == "low":
            tier = "medium"
        elif complexity == "high" and base_tier == "medium":
            tier = "high"

        # 预算检查（如果设置了预算且不足，降级到便宜模型）
        if budget_remaining is not None and budget_remaining < 0.01 and tier == "high":
            tier = "medium"
            logger.info("预算不足，降级到 MEDIUM tier")

        # 选择提供商（优先 DeepSeek）
        selected_provider = None
        reason = ""

        for provider in self.config.fallback_order:
            provider_models = self._models.get(provider, {})
            if tier in provider_models:
                selected_provider = provider
                reason = (
                    "DeepSeek 免费额度优先"
                    if provider == "deepseek"
                    else f"{provider} 备用"
                )
                break

        if selected_provider is None:
            raise NoModelAvailableError(
                f"没有可用的模型处理 {task_type} 任务（tier={tier}，"
                f"可用提供商={[p for p in self._models.keys() if tier in self._models.get(p, {})]}"
            )

        # 估算成本
        model = self._models[selected_provider][tier]
        estimated_cost = model.get_cost(
            Usage(prompt_tokens=1000, completion_tokens=500)
        )

        decision = RoutingDecision(
            task_type=task_type,
            selected_provider=selected_provider,
            selected_tier=tier,
            reason=reason,
            estimated_cost=estimated_cost,
        )

        self._decision_history.append(decision)
        logger.debug(
            f"路由决策: {task_type} → {selected_provider}/{tier} "
            f"(reason={reason}, cost≈{estimated_cost:.4f})"
        )

        return decision

    async def route_and_call(
        self,
        task_type: str,
        messages: List[Message],
        complexity: str = "medium",
        use_cache: bool = True,
        **kwargs,
    ) -> ModelResponse:
        """
        路由并执行（带故障转移 + 缓存）

        优化点：
        1. 缓存相同消息的响应
        2. 故障转移：主模型失败自动切换备用
        3. 任务类型识别：自动降级/升级 tier
        """
        # 1. 检查缓存
        if use_cache and self._cache:
            cached = self._cache.get(messages)
            if cached:
                logger.info(f"使用缓存响应（task={task_type}）")
                return cached

        # 2. 选择模型
        decision = self.select(task_type, complexity)

        # 3. 获取模型实例
        model = self._models[decision.selected_provider][decision.selected_tier]

        # 4. 故障转移：按 fallback 顺序尝试
        fallback_order = [
            p
            for p in self.config.fallback_order
            if p in self._models and decision.selected_tier in self._models[p]
        ]
        # 确保当前选择的在最前
        if decision.selected_provider not in fallback_order:
            fallback_order.insert(0, decision.selected_provider)

        last_error: Optional[Exception] = None

        for provider in fallback_order:
            m = self._models[provider][decision.selected_tier]
            for attempt in range(3):
                try:
                    start = datetime.now()
                    response = await m.generate(messages, **kwargs)
                    elapsed = (datetime.now() - start).total_seconds() * 1000

                    # 更新成本统计
                    actual_cost = m.get_cost(response.usage)
                    self._total_cost += actual_cost
                    response.latency_ms = elapsed

                    logger.info(
                        f"请求成功: {provider}/{decision.selected_tier} "
                        f"(tokens={response.usage.total_tokens}, "
                        f"latency={elapsed:.0f}ms, cost={actual_cost:.6f})"
                    )

                    # 缓存响应
                    if use_cache and self._cache:
                        self._cache.set(messages, response)

                    return response

                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"请求失败（{provider}/{decision.selected_tier}, "
                        f"attempt={attempt + 1}/3）: {e}"
                    )
                    if attempt < 2:
                        await asyncio.sleep(2 * (attempt + 1))  # 递增等待

        # 所有尝试都失败
        logger.error(f"所有提供商均失败: {last_error}")
        raise NoModelAvailableError(
            f"所有模型均不可用（task={task_type}）: {last_error}"
        ) from last_error

    def get_model(
        self,
        provider: str,
        tier: str,
    ) -> Optional[BaseModel]:
        """直接获取指定模型"""
        return self._models.get(provider, {}).get(tier)

    def get_stats(self) -> Dict[str, Any]:
        """获取路由统计"""
        return {
            "total_requests": len(self._decision_history),
            "total_cost": self._total_cost,
            "provider_distribution": self._count_by("selected_provider"),
            "tier_distribution": self._count_by("selected_tier"),
            "cache": self._cache.stats() if self._cache else None,
        }

    def _count_by(self, field: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for d in self._decision_history:
            key = getattr(d, field)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def clear_cache(self) -> None:
        """清空响应缓存"""
        if self._cache:
            self._cache.clear()
            logger.info("响应缓存已清空")

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._decision_history.clear()
        self._total_cost = 0.0


# ============================================================
# Exception
# ============================================================
class NoModelAvailableError(Exception):
    """没有可用模型"""

    pass
