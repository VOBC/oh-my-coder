from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


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
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件，确保 DEFAULT_MODEL 等配置能正确读取
load_dotenv(Path.home() / ".omc" / ".env", override=False)
load_dotenv(Path(".env"), override=False)

from typing import Any, Optional

import httpx
import yaml

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
# 用户自定义模型目录
# ============================================================
USER_MODELS_DIR = Path.home() / ".omc" / "models"

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
    def all(cls) -> list[str]:
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
_TASK_TIER_MAPPING: dict[str, str] = {
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

    # Ollama 本地模型配置
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None  # 如 qwen2:7b
    prefer_local: bool = True  # 优先使用本地模型

    # 成本预算（元）
    daily_budget: float = 10.0

    # 故障转移顺序
    fallback_order: list[str] = field(default_factory=list)

    # 缓存配置
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 分钟缓存
    cache_max_entries: int = 100

    def __post_init__(self):
        # 1) 从 ~/.omc/config.json 加载 API Keys（Web UI 设置页写入）
        self._load_from_config_file()

        # 2) 环境变量覆盖（优先级最高）
        self.deepseek_api_key = self.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        self.wenxin_api_key = self.wenxin_api_key or os.getenv("WENXIN_API_KEY")
        self.tongyi_api_key = self.tongyi_api_key or os.getenv("TONGYI_API_KEY")
        self.glm_api_key = self.glm_api_key or os.getenv("GLM_API_KEY")
        self.minimax_api_key = self.minimax_api_key or os.getenv("MINIMAX_API_KEY")
        self.kimi_api_key = self.kimi_api_key or os.getenv("KIMI_API_KEY")
        self.hunyuan_api_key = self.hunyuan_api_key or os.getenv("HUNYUAN_API_KEY")
        self.doubao_api_key = self.doubao_api_key or os.getenv("DOUBAO_API_KEY")

        # 3) Ollama 配置
        self.ollama_base_url = self.ollama_base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.ollama_model = self.ollama_model or os.getenv("OLLAMA_MODEL", "qwen2:7b")
        self.prefer_local = os.getenv("PREFER_LOCAL_MODEL", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        # 3b) 读取用户配置的默认模型（优先级高于硬编码 fallback_order）
        # 兼容 OMC_DEFAULT_MODEL（环境变量）和 DEFAULT_MODEL（.env / omc config set）
        default_model = os.getenv("OMC_DEFAULT_MODEL") or os.getenv("DEFAULT_MODEL", "")

        # 4) 默认故障转移顺序（优先本地模型，然后免费/便宜的云端）
        # 用户配置的默认模型永远排在第一位，而不是硬编码 deepseek
        if not self.fallback_order:
            prefer_local = self.prefer_local

            # 通用云端备选列表（不含ollama和用户默认模型）
            cloud_fallback = [
                "deepseek",  # 免费额度高
                "kimi",  # 长上下文
                "doubao",  # 性价比高
                "minimax",  # MiniMax
                "glm",  # 智谱
                "tongyi",  # 通义千问
                "wenxin",  # 文心一言
                "hunyuan",  # 混元
            ]

            if default_model and default_model != "ollama":
                # 模型 ID → provider 名的映射（前端传的是 glm-4-flash 等模型 ID）
                _MODEL_ID_TO_PROVIDER = {
                    "deepseek-chat": "deepseek",
                    "glm-4-flash": "glm",
                    "glm-4": "glm",
                    "glm-4-plus": "glm",
                    "MiniMax-Text-01": "minimax",
                    "moonshot-v1-128k": "kimi",
                    "moonshot-v1-8k": "kimi",
                    "moonshot-v1-32k": "kimi",
                    "doubao-pro-32k": "doubao",
                    "ernie-4.0-8k-latest": "wenxin",
                    "qwen-plus": "tongyi",
                    "qwen-turbo": "tongyi",
                    "qwen-max": "tongyi",
                    "hunyuan-turbo": "hunyuan",
                    "hunyuan-pro": "hunyuan",
                }
                # 如果 default_model 是模型 ID，转换为 provider 名
                default_provider = _MODEL_ID_TO_PROVIDER.get(default_model, default_model)
                # 用户配置的默认模型（如 glm、kimi 等）插入到第一位
                if default_provider in cloud_fallback:
                    cloud_fallback.remove(default_provider)
                cloud_fallback.insert(0, default_provider)

            if prefer_local:
                self.fallback_order = ["ollama"] + cloud_fallback
            else:
                self.fallback_order = cloud_fallback + ["ollama"]  # 本地模型作为后备

    def _load_from_config_file(self) -> None:
        """从 ~/.omc/config.json 读取 API Keys（Web UI 设置保存的目标文件）"""
        config_path = Path.home() / ".omc" / "config.json"
        if not config_path.exists():
            return
        try:
            import json
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            models = data.get("models", {})
            if not isinstance(models, dict):
                return
            # provider name → RouterConfig field 映射
            _key_map = {
                "deepseek": "deepseek_api_key",
                "glm":      "glm_api_key",
                "minimax":  "minimax_api_key",   # mimo 也映射到 minimax
                "mimo":     "minimax_api_key",
                "kimi":     "kimi_api_key",
                "doubao":   "doubao_api_key",
                "tongyi":   "tongyi_api_key",
                "wenxin":   "wenxin_api_key",
                "hunyuan":  "hunyuan_api_key",
                "tiangong": None,    # 暂无对应字段
                "baichuan": None,    # 暂无对应字段
            }
            for provider, field_name in _key_map.items():
                if not field_name:
                    continue
                entry = models.get(provider, {})
                if not isinstance(entry, dict):
                    continue
                key_val = entry.get("api_key", "")
                if key_val and isinstance(key_val, str) and not key_val.startswith("*"):
                    current = getattr(self, field_name, None)
                    if not current:
                        setattr(self, field_name, key_val)
                        logger.debug(f"从 config.json 加载 {provider} API Key")
        except Exception as e:
            logger.warning(f"读取 ~/.omc/config.json 失败: {e}")


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
        self._cache: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []  # 简单 FIFO（非真实 LRU，但够用）
        self._max_entries = max_entries
        self._ttl = ttl_seconds

    def _make_key(self, messages: list[Message]) -> str:
        """根据消息内容生成缓存 key"""
        content = "".join(m.content for m in messages)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, messages: list[Message]) -> Optional[ModelResponse]:
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

    def set(self, messages: list[Message], response: ModelResponse) -> None:
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

    def stats(self) -> dict[str, int]:
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
        self._models: dict[str, dict[str, BaseModel]] = {}
        self._decision_history: list[RoutingDecision] = []
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
        # Ollama 本地模型（优先检测）
        try:
            from ..models.ollama import OLLAMA_DEFAULT_URL, OllamaModel

            base_url = self.config.ollama_base_url or OLLAMA_DEFAULT_URL
            if OllamaModel.is_available(base_url):
                model_name = self.config.ollama_model or "qwen2:7b"
                for tier in ["low", "medium", "high"]:
                    cfg = ModelConfig(api_key="", base_url=base_url)
                    self._models.setdefault("ollama", {})[tier] = OllamaModel(
                        cfg, ModelTier(tier), model_name=model_name
                    )
                logger.info(f"Ollama 本地模型已初始化 ({model_name})")

                # 列出可用模型
                available = OllamaModel.list_models(base_url)
                if available:
                    logger.info(f"本地可用模型: {[m['name'] for m in available[:5]]}")
            else:
                logger.debug(f"Ollama 服务不可用 ({base_url})")
        except Exception as e:
            logger.debug(f"Ollama 初始化跳过: {e}")

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

        # ============================================================
        # 加载用户自定义模型配置 (~/.omc/models/*.yaml)
        # ============================================================
        if USER_MODELS_DIR.exists():
            self._load_user_models()

        # 记录可用提供商
        available = list(self._models.keys())
        logger.info(f"可用模型提供商: {available or '无'}")

    def _load_user_models(self) -> None:
        """
        加载用户自定义模型配置 (~/.omc/models/*.yaml)

        支持用户添加任意 OpenAI 兼容的模型提供商。
        配置文件格式见：examples/model-config.yaml
        """
        if not USER_MODELS_DIR.exists():
            return

        loaded_count = 0
        for yaml_file in USER_MODELS_DIR.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)

                if not cfg or not isinstance(cfg, dict):
                    continue

                # 校验必要字段
                required = ["provider", "model"]
                if not all(k in cfg for k in required):
                    logger.warning(f"跳过 {yaml_file.name}: 缺少必要字段")
                    continue

                provider = cfg["provider"]
                model_name = cfg["model"]

                # 如果该 provider 已有内置模型，跳过
                if provider in self._models:
                    logger.debug(f"跳过 {provider}: 已有内置模型")
                    continue

                # 获取 API Key
                api_key_env = cfg.get("api_key_env", f"{provider.upper()}_API_KEY")
                api_key = os.getenv(api_key_env)

                if not api_key:
                    logger.debug(f"跳过 {provider}: 环境变量 {api_key_env} 未设置")
                    continue

                # 使用 OpenAI 兼容接口（DeepSeekModel）初始化
                base_url = cfg.get("endpoint")

                for tier in ["low", "medium", "high"]:
                    model_cfg = ModelConfig(
                        api_key=api_key,
                        base_url=base_url,
                        model_name=model_name,
                    )
                    # 复用 DeepSeek 模型（OpenAI 兼容）
                    self._models.setdefault(provider, {})[tier] = DeepSeekModel(
                        model_cfg, ModelTier(tier)
                    )

                loaded_count += 1
                logger.info(f"用户模型已加载: {provider}/{model_name}")

            except Exception as e:
                logger.warning(f"加载 {yaml_file.name} 失败: {e}")

        if loaded_count > 0:
            logger.info(f"已加载 {loaded_count} 个用户自定义模型")

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
                f"可用提供商={list(self._models.keys())}"
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
        messages: list[Message],
        complexity: str = "medium",
        use_cache: bool = True,
        override_model: Optional[str] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        路由并执行（带故障转移 + 缓存）

        优化点：
        1. 缓存相同消息的响应
        2. 故障转移：主模型失败自动切换备用
        3. 任务类型识别：自动降级/升级 tier
        4. override_model：用户指定模型时直接使用，忽略自动选择
        """
        # 0. 处理用户指定的模型覆盖
        forced_provider: Optional[str] = None
        forced_tier: Optional[str] = None
        if override_model:
            mapped = self._MODEL_ID_TO_PROVIDER.get(override_model)
            if mapped:
                # 自定义模型或已知模型 ID → 映射到 provider
                forced_provider = mapped
                forced_tier = "high"  # 自定义/指定模型统一用 high tier
                logger.info(f"使用用户指定模型: {override_model} → {forced_provider}")
            else:
                # 完全未知的模型 ID → 尝试直接作为 provider 名
                if override_model in self._models:
                    forced_provider = override_model
                    forced_tier = "high"
                    logger.info(f"使用用户指定 provider: {override_model}")
                else:
                    logger.warning(f"未知的 override_model: {override_model}，忽略")

        # 1. 检查缓存（不区分 override，相同消息返回相同响应）
        if use_cache and self._cache:
            cached = self._cache.get(messages)
            if cached:
                logger.info(f"使用缓存响应（task={task_type}）")
                return cached

        # 2. 选择模型（用户指定时跳过自动选择）
        if forced_provider and forced_tier:
            decision = RoutingDecision(
                task_type=task_type,
                selected_provider=forced_provider,
                selected_tier=forced_tier,
                reason=f"用户指定模型: {override_model}",
                estimated_cost=0.0,
            )
        else:
            decision = self.select(task_type, complexity)

        # 3. 故障转移：按 fallback 顺序尝试（仅已初始化的 provider）
        # 用户指定模型时，优先使用该模型，失败后自动降级到默认 fallback
        if forced_provider:
            fallback_order = [forced_provider] if forced_provider in self._models else []
            # 添加默认 fallback 作为降级选项（排除已添加的）
            for p in self.config.fallback_order:
                if p not in fallback_order and p in self._models and decision.selected_tier in self._models[p]:
                    fallback_order.append(p)
        else:
            fallback_order = [
                p
                for p in self.config.fallback_order
                if p in self._models and decision.selected_tier in self._models[p]
            ]
            # 确保当前选择的在最前
            if decision.selected_provider not in fallback_order:
                fallback_order.insert(0, decision.selected_provider)

        last_error: Optional[Exception] = None
        rate_limited_providers: list[str] = []
        attempted_providers: list[str] = []

        for provider in fallback_order:
            m = self._models[provider][decision.selected_tier]
            attempted_providers.append(provider)
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
                    # 429 限流：不重试当前 provider，failover 到下一个
                    if (
                        isinstance(e, httpx.HTTPStatusError)
                        and e.response.status_code == 429
                    ):
                        logger.warning(
                            f"429 限流（{provider}/{decision.selected_tier}），"
                            f"跳过该 provider，尝试下一个"
                        )
                        rate_limited_providers.append(provider)
                        break  # 不重试当前 provider，切换下一个

                    logger.warning(
                        f"请求失败（{provider}/{decision.selected_tier}, "
                        f"attempt={attempt + 1}/3）: {e}"
                    )
                    if attempt < 2:
                        await asyncio.sleep(2 * (attempt + 1))  # 递增等待

        # 所有尝试都失败
        # 只有当所有实际尝试过的 provider 都是 429 时才抛 RateLimitError
        if rate_limited_providers and set(rate_limited_providers) == set(
            attempted_providers
        ):
            logger.error("所有 provider 均 429 限流")
            raise RateLimitError(
                f"所有模型均触发限流（429）：{rate_limited_providers}。"
                f"建议稍后重试或配置更多 API Key。"
            ) from last_error

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

    def get_stats(self) -> dict[str, Any]:
        """获取路由统计"""
        return {
            "total_requests": len(self._decision_history),
            "total_cost": self._total_cost,
            "provider_distribution": self._count_by("selected_provider"),
            "tier_distribution": self._count_by("selected_tier"),
            "cache": self._cache.stats() if self._cache else None,
        }

    def _count_by(self, field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
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


    # 模型 ID → 路由器内部 provider 名称的映射
    # 前端下拉菜单传的是模型 ID（如 "glm-4-flash"），需要映射到 provider（如 "glm"）
    _MODEL_ID_TO_PROVIDER: dict[str, str] = {
        # DeepSeek
        "deepseek-chat": "deepseek",
        # 智谱 GLM
        "glm-4-flash": "glm",
        # MiniMax / MiMo
        "MiniMax-Text-01": "minimax",
        # Kimi / Moonshot
        "moonshot-v1-128k": "kimi",
        # 豆包 / Volcengine
        "doubao-pro-32k": "doubao",
        # 天工
        "tiangong-3": None,  # 路由器暂不支持 tiangong provider
        # 百川
        "Baichuan4": None,  # 路由器暂不支持 baichuan provider
        # 文心
        "ernie-4.0-8k-latest": "wenxin",
        # 通义
        "qwen-plus": "tongyi",
        # 混元
        "hunyuan-turbo": "hunyuan",
    }

class RateLimitError(Exception):
    """429 限流错误，不重试"""

    pass


class NoModelAvailableError(Exception):
    """没有可用模型"""

    pass
