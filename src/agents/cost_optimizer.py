from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
成本优化建议模块 - Cost Optimization

根据任务复杂度推荐最优模型，节省成本。

模型分类：
- 本地 Ollama 模型 (ollama/)
- 国产云端模型 (deepseek/, qwen/, glm/, moonshot/)
- 顶级模型 (openai/, anthropic/)

复杂度评估：
- 低：<3 文件简单修改
- 中：3-10 文件改动
- 高：>10 文件 / 新架构 / 重构
"""


from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class Complexity(Enum):
    """任务复杂度"""

    LOW = "low"  # 简单任务，本地模型足够
    MEDIUM = "medium"  # 中等复杂度，国产性价比模型
    HIGH = "high"  # 复杂任务，需要顶级模型


@dataclass
class ModelRecommendation:
    """模型推荐结果"""

    model: str
    provider: str  # ollama/deepseek/openai/anthropic
    complexity: Complexity

    # 理由
    reason: str

    # 估算成本（相对值）
    estimated_cost: float  # 1-10, 10 最贵

    # 备选模型
    alternatives: list[dict[str, str]]


class CostOptimizer:
    """成本优化器

    根据任务特征评估复杂度，推荐最优模型。
    """

    # 模型定义
    MODELS = {
        # 本地模型
        "ollama/qwen2.5:7b": {
            "provider": "ollama",
            "cost": 1,
            "strengths": ["简单修改", "代码补全", "轻量任务"],
        },
        "ollama/qwen2.5:14b": {
            "provider": "ollama",
            "cost": 2,
            "strengths": ["中等复杂度", "代码理解", "本地优先"],
        },
        "ollama/llama3:8b": {
            "provider": "ollama",
            "cost": 2,
            "strengths": ["英文为主", "通用任务"],
        },
        # 国产云端模型
        "deepseek-chat": {
            "provider": "deepseek",
            "cost": 4,
            "strengths": ["代码能力强", "性价比高", "中文优化"],
        },
        "qwen-turbo": {
            "provider": "qwen",
            "cost": 3,
            "strengths": ["阿里系", "中文好", "速度快"],
        },
        "glm-4": {
            "provider": "glm",
            "cost": 4,
            "strengths": ["智谱清言", "中文优化"],
        },
        "moonshot-v1": {
            "provider": "moonshot",
            "cost": 4,
            "strengths": [" Kimi ", "长文本处理"],
        },
        # 顶级模型
        "gpt-4o": {
            "provider": "openai",
            "cost": 10,
            "strengths": ["顶级能力", "复杂推理", "架构设计"],
        },
        "gpt-4o-mini": {
            "provider": "openai",
            "cost": 6,
            "strengths": ["性价比", "快速任务"],
        },
        "claude-3-opus": {
            "provider": "anthropic",
            "cost": 10,
            "strengths": ["最强推理", "长文本", "分析"],
        },
        "claude-3-sonnet": {
            "provider": "anthropic",
            "cost": 7,
            "strengths": ["平衡", "写作能力强"],
        },
    }

    # 复杂度关键词
    COMPLEXITY_KEYWORDS = {
        Complexity.HIGH: [
            "重构",
            "refactor",
            "架构",
            "architecture",
            "设计",
            "design",
            "新项目",
            "new project",
            "迁移",
            "migrate",
            "拆分",
            "split",
            "重写",
            "rewrite",
            "复杂",
            "complex",
            "系统",
            "system",
            "微服务",
            "microservice",
            "分布式",
            "distributed",
        ],
        Complexity.MEDIUM: [
            "api",
            "接口",
            "数据库",
            "database",
            "认证",
            "auth",
            "登录",
            "login",
            "支付",
            "payment",
            "订单",
            "order",
            "用户",
            "user",
            "管理",
            "admin",
            "CRUD",
            "多个文件",
            "multiple files",
            "多模块",
        ],
    }

    def __init__(self, prefer_local: bool = True):
        """
        Args:
            prefer_local: 是否优先推荐本地模型
        """
        self.prefer_local = prefer_local

    def analyze_task(
        self,
        task_description: str,
        file_count: Optional[int] = None,
        new_files: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        分析任务特征

        Args:
            task_description: 任务描述
            file_count: 涉及文件数量
            new_files: 新增文件列表

        Returns:
            任务分析结果
        """
        task_lower = task_description.lower()

        # 1. 基于关键词评估
        high_keywords = self.COMPLEXITY_KEYWORDS[Complexity.HIGH]
        medium_keywords = self.COMPLEXITY_KEYWORDS[Complexity.MEDIUM]

        high_score = sum(1 for kw in high_keywords if kw in task_lower)
        medium_score = sum(1 for kw in medium_keywords if kw in task_lower)

        # 2. 基于文件数量
        if file_count is not None:
            if file_count > 10:
                high_score += 3
            elif file_count > 5:
                medium_score += 2
            elif file_count > 2:
                medium_score += 1

        # 3. 基于新增文件
        if new_files:
            for f in new_files:
                if any(x in f.lower() for x in ["api", "service", "model"]):
                    medium_score += 1
                if any(x in f.lower() for x in ["app", "main", "server"]):
                    high_score += 1

        # 4. 确定复杂度
        if high_score >= 2:
            complexity = Complexity.HIGH
        elif medium_score >= 2:
            complexity = Complexity.MEDIUM
        else:
            complexity = Complexity.LOW

        return {
            "complexity": complexity,
            "high_score": high_score,
            "medium_score": medium_score,
            "file_count": file_count,
            "new_files_count": len(new_files) if new_files else 0,
        }

    def recommend(
        self,
        task_description: str,
        file_count: Optional[int] = None,
        new_files: Optional[list[str]] = None,
    ) -> ModelRecommendation:
        """
        推荐最优模型

        Args:
            task_description: 任务描述
            file_count: 涉及文件数量
            new_files: 新增文件列表

        Returns:
            模型推荐结果
        """
        # 分析任务
        analysis = self.analyze_task(task_description, file_count, new_files)
        complexity = analysis["complexity"]

        # 根据复杂度和偏好推荐
        if complexity == Complexity.LOW:
            return self._recommend_low(analysis)
        if complexity == Complexity.MEDIUM:
            return self._recommend_medium(analysis)
        return self._recommend_high(analysis)

    def _recommend_low(self, analysis: dict[str, Any]) -> ModelRecommendation:
        """推荐低复杂度任务的模型"""
        if self.prefer_local:
            model = "ollama/qwen2.5:7b"
            reason = "简单修改任务，本地 7B 模型足够，速度快且免费"
        else:
            model = "qwen-turbo"
            reason = "简单任务，国产模型性价比高"

        return ModelRecommendation(
            model=model,
            provider=self.MODELS[model]["provider"],
            complexity=Complexity.LOW,
            reason=reason,
            estimated_cost=self.MODELS[model]["cost"],
            alternatives=[
                {"model": "ollama/qwen2.5:14b", "reason": "更强能力"},
                {"model": "gpt-4o-mini", "reason": "云端备选"},
            ],
        )

    def _recommend_medium(self, analysis: dict[str, Any]) -> ModelRecommendation:
        """推荐中等复杂度任务的模型"""
        if self.prefer_local:
            model = "ollama/qwen2.5:14b"
            reason = "中等复杂度任务，本地 14B 模型能力足够"
        else:
            model = "deepseek-chat"
            reason = "DeepSeek 代码能力强，国产性价比首选"

        return ModelRecommendation(
            model=model,
            provider=self.MODELS[model]["provider"],
            complexity=Complexity.MEDIUM,
            reason=reason,
            estimated_cost=self.MODELS[model]["cost"],
            alternatives=[
                {"model": "qwen-turbo", "reason": "阿里系备选"},
                {"model": "gpt-4o-mini", "reason": "OpenAI 备选"},
            ],
        )

    def _recommend_high(self, analysis: dict[str, Any]) -> ModelRecommendation:
        """推荐高复杂度任务的模型"""
        if self.prefer_local:
            model = "ollama/qwen2.5:14b"
            reason = "复杂任务，建议先用本地模型快速验证思路，如遇瓶颈再切换顶级模型"
            cost = 2
        else:
            model = "gpt-4o"
            reason = "复杂架构设计/重构任务，需要顶级模型能力"
            cost = 10

        return ModelRecommendation(
            model=model,
            provider=self.MODELS[model]["provider"],
            complexity=Complexity.HIGH,
            reason=reason,
            estimated_cost=cost,
            alternatives=[
                {"model": "gpt-4o", "reason": "OpenAI 顶级"},
                {"model": "claude-3-opus", "reason": "Claude 最强"},
                {"model": "deepseek-chat", "reason": "国产性价比"},
            ],
        )

    def get_all_models(self) -> list[dict[str, Any]]:
        """获取所有可用模型"""
        result = []
        for model, info in self.MODELS.items():
            result.append(
                {
                    "model": model,
                    "provider": info["provider"],
                    "cost": info["cost"],
                    "strengths": info["strengths"],
                }
            )
        return sorted(result, key=lambda x: x["cost"])


# ------------------------------------------------------------------
# Token 费用计算
# ------------------------------------------------------------------


# 模型定价表（美元 / 1M tokens）
# 数据来源：各模型官方定价页（2025-01）
MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    # Anthropic
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3.5-opus": {"input": 18.00, "output": 90.00},
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},

    # Qwen
    "qwen-turbo": {"input": 0.30, "output": 0.60},
    "qwen-plus": {"input": 0.80, "output": 2.00},
    # GLM
    "glm-4": {"input": 0.50, "output": 0.50},
    # Moonshot
    "moonshot-v1-8k": {"input": 0.50, "output": 0.50},
    "moonshot-v1-32k": {"input": 0.50, "output": 0.50},
    # Ollama (本地免费)
    "ollama/qwen2.5:7b": {"input": 0.0, "output": 0.0},
    "ollama/qwen2.5:14b": {"input": 0.0, "output": 0.0},
    "ollama/llama3:8b": {"input": 0.0, "output": 0.0},
}


@dataclass
class CostEstimate:
    """费用估算结果"""

    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float  # 美元
    output_cost: float  # 美元
    total_cost: float  # 美元


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> CostEstimate:
    """计算指定模型的 token 费用

    Args:
        model: 模型名称（如 "gpt-4o-mini", "claude-3.5-opus"）
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数

    Returns:
        CostEstimate: 费用估算结果

    Raises:
        ValueError: 模型不在定价表中
    """
    if model not in MODEL_PRICING:
        raise ValueError(f"模型 {model} 不在定价表中，可用模型: {list(MODEL_PRICING.keys())}")

    pricing = MODEL_PRICING[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    return CostEstimate(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost,
    )


def calculate_multi_model_cost(
    model_usages: list[dict[str, int]],
) -> list[CostEstimate]:
    """计算多模型组合费用

    Args:
        model_usages: 模型使用列表，每项包含 {"model": str, "input_tokens": int, "output_tokens": int}

    Returns:
        各模型的费用估算列表
    """
    results = []
    for usage in model_usages:
        estimate = calculate_cost(
            model=usage["model"],
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )
        results.append(estimate)
    return results


# ------------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------------


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="成本优化建议工具")
    parser.add_argument("task", nargs="?", help="任务描述")
    parser.add_argument("--files", "-f", type=int, help="涉及文件数量")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有模型")
    parser.add_argument("--prefer-local", action="store_true", default=True)

    args = parser.parse_args()

    optimizer = CostOptimizer(prefer_local=args.prefer_local)

    if args.list:
        print("可用模型：")
        print("-" * 60)
        for m in optimizer.get_all_models():
            cost_bars = "💰" * m["cost"]
            print(f"{m['model']:30s} [{m['provider']:10s}] {cost_bars}")
            print(f"    优势: {', '.join(m['strengths'])}")
            print()
        return

    if not args.task:
        parser.print_help()
        return

    # 推荐模型
    recommendation = optimizer.recommend(args.task, file_count=args.files)

    print("=" * 60)
    print(f"任务: {args.task}")
    if args.files:
        print(f"文件数: {args.files}")
    print("=" * 60)
    print()
    print(f"🎯 推荐模型: {recommendation.model}")
    print(f"📦 提供商: {recommendation.provider}")
    print(f"📊 复杂度: {recommendation.complexity.value}")
    print(f"💵 估算成本: {'$' * recommendation.estimated_cost}")
    print()
    print("💡 推荐理由:")
    print(f"   {recommendation.reason}")
    print()
    if recommendation.alternatives:
        print("🔄 备选方案:")
        for alt in recommendation.alternatives:
            print(f"   - {alt['model']}: {alt['reason']}")


if __name__ == "__main__":
    main()
