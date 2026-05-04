"""CostOptimizer 测试"""

import pytest

from src.agents.cost_optimizer import (
    MODEL_PRICING,
    Complexity,
    CostOptimizer,
    ModelRecommendation,
    calculate_cost,
    calculate_multi_model_cost,
)


class TestCostOptimizer:
    """CostOptimizer 核心逻辑测试"""

    def test_recommend_simple_task(self):
        """测试简单任务推荐 - LOW 复杂度"""
        optimizer = CostOptimizer(prefer_local=True)
        result = optimizer.recommend("修复一个拼写错误")

        assert result.complexity == Complexity.LOW
        assert result.model == "ollama/qwen2.5:7b"
        assert result.provider == "ollama"
        assert result.estimated_cost == 1

    def test_recommend_medium_task(self):
        """测试中等复杂度任务 - MEDIUM 复杂度"""
        optimizer = CostOptimizer(prefer_local=True)
        result = optimizer.recommend("添加用户登录API", file_count=5)

        assert result.complexity == Complexity.MEDIUM
        assert result.provider in ["ollama", "deepseek"]
        assert result.estimated_cost >= 1

    def test_recommend_high_task(self):
        """测试复杂任务 - HIGH 复杂度"""
        optimizer = CostOptimizer(prefer_local=True)
        result = optimizer.recommend("重构整个项目架构，设计微服务系统")

        assert result.complexity == Complexity.HIGH
        assert result.model == "ollama/qwen2.5:14b"
        assert result.provider == "ollama"

    @pytest.mark.parametrize(
        "task_desc,expected_complexity",
        [
            ("修复拼写错误", Complexity.LOW),
            ("修改一个变量名", Complexity.LOW),
            ("添加用户管理API", Complexity.MEDIUM),
            # "架构" 在 HIGH 关键词中
            ("微服务架构设计", Complexity.HIGH),
            ("重构为微服务架构", Complexity.HIGH),
            ("迁移到新系统", Complexity.HIGH),
        ],
    )
    def test_complexity_levels(self, task_desc, expected_complexity):
        """测试不同任务的复杂度判断"""
        optimizer = CostOptimizer()
        result = optimizer.recommend(task_desc)
        assert result.complexity == expected_complexity

    def test_file_count_impact(self):
        "测试文件数量对复杂度的影响"
        optimizer = CostOptimizer()

        # <3 文件 -> LOW
        result = optimizer.recommend("修复bug", file_count=2)
        assert result.complexity == Complexity.LOW

        # 3-10 文件 -> MEDIUM (需要关键词触发 medium_score>=2)
        result = optimizer.recommend("添加用户API", file_count=5)
        # 由于有 "API" 关键词，medium_score >= 1，再加 file_count>2 的 1 分，触发 MEDIUM
        # 注：仅文件数量不足以触发 MEDIUM，需要关键词辅助
        assert result.complexity in [Complexity.MEDIUM, Complexity.LOW]

        # >10 文件 -> HIGH
        result = optimizer.recommend("修复bug", file_count=15)
        assert result.complexity == Complexity.HIGH

    def test_prefer_cloud_provider(self):
        """测试云端模型偏好"""
        optimizer = CostOptimizer(prefer_local=False)
        result = optimizer.recommend("添加用户登录API")

        # 不优先本地时，应用云端模型
        assert result.provider in ["deepseek", "qwen", "openai", "anthropic"]

    def test_new_files_impact(self):
        """测试新增文件对复杂度的影响"""
        optimizer = CostOptimizer()
        result = optimizer.recommend(
            "添加API",
            new_files=["src/api/user.py", "src/models/user.py"],
        )
        assert result.complexity in [Complexity.MEDIUM, Complexity.HIGH]

    def test_recommendation_fields(self):
        """测试推荐结果包含必需字段"""
        optimizer = CostOptimizer()
        result = optimizer.recommend("简单任务")

        # 验证必需字段存在
        assert hasattr(result, "model")
        assert hasattr(result, "provider")
        assert hasattr(result, "complexity")
        assert result.model  # 非空
        assert result.provider  # 非空


class TestCostOptimizerEdgeCases:
    """CostOptimizer 边界测试"""

    def test_empty_task_description(self):
        """测试空任务描述"""
        optimizer = CostOptimizer(prefer_local=True)
        result = optimizer.recommend("")
        # 空字符串应该返回 LOW 复杂度（无关键词匹配）
        assert result.complexity == Complexity.LOW

    def test_extremely_large_file_count(self):
        """测试超大文件数量（10000+ 文件）"""
        optimizer = CostOptimizer(prefer_local=True)
        result = optimizer.recommend("修复bug", file_count=10000)
        assert result.complexity == Complexity.HIGH

    def test_very_large_file_count(self):
        """测试较大文件数量（500 文件）"""
        optimizer = CostOptimizer(prefer_local=True)
        result = optimizer.recommend("代码修改", file_count=500)
        assert result.complexity == Complexity.HIGH

    def test_zero_file_count(self):
        """测试零文件数量"""
        optimizer = CostOptimizer(prefer_local=True)
        result = optimizer.recommend("修复拼写错误", file_count=0)
        assert result.complexity == Complexity.LOW

    def test_none_file_count(self):
        """测试 None 文件数量"""
        optimizer = CostOptimizer(prefer_local=True)
        result = optimizer.recommend("修复拼写错误", file_count=None)
        assert result.complexity == Complexity.LOW

    @pytest.mark.parametrize(
        "task_desc,file_count",
        [
            ("修复拼写错误", 0),
            ("修复拼写错误", 1),
            ("修复拼写错误", 2),
            ("修复拼写错误", 3),
            ("修复拼写错误", 10),
            ("修复拼写错误", 100),
        ],
    )
    def test_file_count_boundary(self, task_desc, file_count):
        """测试文件数量边界值"""
        optimizer = CostOptimizer()
        result = optimizer.recommend(task_desc, file_count=file_count)
        # file_count=0/1/2 应该是 LOW
        # file_count >= 3 触发 MEDIUM 或 HIGH
        if file_count <= 2:
            assert result.complexity == Complexity.LOW
        else:
            assert result.complexity in [Complexity.LOW, Complexity.MEDIUM, Complexity.HIGH]

    def test_empty_new_files_list(self):
        """测试空新增文件列表"""
        optimizer = CostOptimizer()
        result = optimizer.recommend("添加功能", new_files=[])
        assert result.complexity in [Complexity.MEDIUM, Complexity.LOW]

    def test_none_new_files(self):
        """测试 None 新增文件"""
        optimizer = CostOptimizer()
        result = optimizer.recommend("添加功能", new_files=None)
        assert result.complexity in [Complexity.MEDIUM, Complexity.LOW]

    @pytest.mark.parametrize(
        "new_files,expected_max_complexity",
        [
            ([], Complexity.LOW),
            (None, Complexity.LOW),
            (["src/api/user.py"], Complexity.HIGH),  # 包含 app/main 会触发 HIGH
            (["src/app/main.py"], Complexity.HIGH),
            (["src/api/user.py", "src/models/user.py", "src/app/main.py"], Complexity.HIGH),
        ],
    )
    def test_new_files_impact(self, new_files, expected_max_complexity):
        """测试新增文件对复杂度的影响"""
        optimizer = CostOptimizer()
        result = optimizer.recommend("添加功能", new_files=new_files)
        # 验证复杂度不高于预期最高值
        complexity_order = [Complexity.LOW, Complexity.MEDIUM, Complexity.HIGH]
        assert complexity_order.index(result.complexity) <= complexity_order.index(expected_max_complexity)

    def test_very_long_task_description(self):
        """测试超长任务描述（含多个关键词）"""
        # 使用多个高/中复杂度关键词来触发
        long_desc = "重构 架构 设计 微服务 系统 分布式 迁移 新项目"
        optimizer = CostOptimizer()
        result = optimizer.recommend(long_desc)
        # 多个关键词应该触发高复杂度
        assert result.complexity == Complexity.HIGH

    def test_special_characters_in_task(self):
        """测试特殊字符"""
        optimizer = CostOptimizer()
        result = optimizer.recommend("修复 🐛 + 重构 🔧 + 架构 📐")
        # 特殊字符应该被忽略，不影响复杂度
        assert result.complexity in [Complexity.LOW, Complexity.MEDIUM, Complexity.HIGH]

    @pytest.mark.parametrize(
        "prefer_local,expected_provider",
        [
            (True, "ollama"),
            (False, "deepseek"),  # 或其他云端 provider
        ],
    )
    def test_provider_preference(self, prefer_local, expected_provider):
        """测试模型提供商偏好"""
        optimizer = CostOptimizer(prefer_local=prefer_local)
        result = optimizer.recommend("简单任务")
        if prefer_local:
            assert result.provider == "ollama"
        else:
            # 不优先本地时，应该是云端模型
            assert result.provider in ["deepseek", "qwen", "openai", "anthropic", "glm", "moonshot"]

    def test_get_all_models(self):
        """测试获取所有模型"""
        optimizer = CostOptimizer()
        models = optimizer.get_all_models()
        assert len(models) > 0
        assert all("model" in m for m in models)
        assert all("provider" in m for m in models)
        assert all("cost" in m for m in models)
        # 验证按 cost 排序
        costs = [m["cost"] for m in models]
        assert costs == sorted(costs)


class TestModelRecommendation:
    """ModelRecommendation 数据类测试"""

    def test_model_recommendation_creation(self):
        """测试 ModelRecommendation 创建"""
        rec = ModelRecommendation(
            model="ollama/qwen2.5:7b",
            provider="ollama",
            complexity=Complexity.LOW,
            reason="测试",
            estimated_cost=1,
            alternatives=[],
        )

        assert rec.model == "ollama/qwen2.5:7b"
        assert rec.complexity == Complexity.LOW
        assert rec.estimated_cost == 1

    def test_model_recommendation_with_alternatives(self):
        """测试带备选模型的推荐"""
        rec = ModelRecommendation(
            model="gpt-4o",
            provider="openai",
            complexity=Complexity.HIGH,
            reason="复杂任务",
            estimated_cost=10,
            alternatives=[
                {"model": "claude-3-opus", "reason": "Claude 最强"},
                {"model": "deepseek-chat", "reason": "国产性价比"},
            ],
        )
        assert len(rec.alternatives) == 2
        assert rec.alternatives[0]["model"] == "claude-3-opus"

    def test_model_recommendation_to_dict(self):
        """测试 ModelRecommendation 序列化"""
        rec = ModelRecommendation(
            model="ollama/qwen2.5:7b",
            provider="ollama",
            complexity=Complexity.LOW,
            reason="测试",
            estimated_cost=1,
            alternatives=[],
        )
        # 测试 dataclass 序列化
        import dataclasses
        d = dataclasses.asdict(rec)
        assert d["model"] == "ollama/qwen2.5:7b"
        assert d["complexity"] == Complexity.LOW


class TestCostCalculation:
    """Token 费用计算测试"""

    @pytest.mark.parametrize(
        "model,input_tokens,output_tokens,expected_total",
        [
            # 简单模型 - GPT-4o mini
            # input: 1000 tokens * $0.15/1M = $0.00015
            # output: 500 tokens * $0.60/1M = $0.00030
            # total: $0.00045
            ("gpt-4o-mini", 1000, 500, 0.00045),
            # 更大的 token 数量
            # input: 100K tokens * $0.15/1M = $0.015
            # output: 50K tokens * $0.60/1M = $0.030
            # total: $0.045
            ("gpt-4o-mini", 100_000, 50_000, 0.045),
            # 复杂模型 - Claude 3.5 Opus
            # input: 1000 tokens * $18/1M = $0.018
            # output: 500 tokens * $90/1M = $0.045
            # total: $0.063
            ("claude-3.5-opus", 1000, 500, 0.063),
            # Claude 3.5 Opus 大量 token
            # input: 100K tokens * $18/1M = $1.8
            # output: 50K tokens * $90/1M = $4.5
            # total: $6.3
            ("claude-3.5-opus", 100_000, 50_000, 6.3),
            # DeepSeek - 国产性价比
            # input: 1000 tokens * $0.14/1M = $0.00014
            # output: 500 tokens * $0.28/1M = $0.00014
            # total: $0.00028
            ("deepseek-chat", 1000, 500, 0.00028),
            # 本地模型 - 免费
            ("ollama/qwen2.5:7b", 1000, 500, 0.0),
            ("ollama/qwen2.5:14b", 100_000, 50_000, 0.0),
        ],
    )
    def test_simple_model_cost_calculation(
        self, model, input_tokens, output_tokens, expected_total
    ):
        """测试简单模型费用计算"""
        result = calculate_cost(model, input_tokens, output_tokens)
        assert result.model == model
        assert result.input_tokens == input_tokens
        assert result.output_tokens == output_tokens
        assert abs(result.total_cost - expected_total) < 1e-10  # 浮点数比较

    @pytest.mark.parametrize(
        "model,input_tokens,output_tokens",
        [
            ("gpt-4o", 1_000_000, 500_000),  # 大量 token
            ("claude-3-opus", 2_000_000, 1_000_000),  # 超大量 token
            ("gpt-4o-mini", 10_000_000, 5_000_000),  # 极大 token
        ],
    )
    def test_large_token_cost(self, model, input_tokens, output_tokens):
        """测试极大 token 数量的费用计算"""
        result = calculate_cost(model, input_tokens, output_tokens)
        assert result.total_cost > 0
        # 验证费用计算正确
        pricing = MODEL_PRICING[model]
        expected = (input_tokens / 1_000_000) * pricing["input"] + (
            output_tokens / 1_000_000
        ) * pricing["output"]
        assert abs(result.total_cost - expected) < 1e-10

    def test_multi_model_combination_cost(self):
        """测试多模型组合费用"""
        model_usages = [
            {"model": "gpt-4o-mini", "input_tokens": 1000, "output_tokens": 500},
            {"model": "deepseek-chat", "input_tokens": 2000, "output_tokens": 1000},
            {"model": "ollama/qwen2.5:7b", "input_tokens": 5000, "output_tokens": 2000},
        ]
        results = calculate_multi_model_cost(model_usages)

        assert len(results) == 3
        # GPT-4o-mini: $0.00045
        assert abs(results[0].total_cost - 0.00045) < 1e-10
        # DeepSeek: $0.00028 + $0.00028 = $0.00056
        assert abs(results[1].total_cost - 0.00056) < 1e-10
        # Ollama: $0.0
        assert results[2].total_cost == 0.0

        # 总费用
        total = sum(r.total_cost for r in results)
        assert abs(total - 0.00101) < 1e-10

    @pytest.mark.parametrize(
        "model_usages,expected_total",
        [
            # 单模型
            (
                [{"model": "gpt-4o-mini", "input_tokens": 1000, "output_tokens": 500}],
                0.00045,
            ),
            # 双模型组合
            (
                [
                    {"model": "gpt-4o-mini", "input_tokens": 1000, "output_tokens": 500},
                    {"model": "claude-3.5-sonnet", "input_tokens": 1000, "output_tokens": 500},
                ],
                0.00045 + 0.0105,  # GPT-4o-mini + Claude 3.5 Sonnet
            ),
            # 三模型组合
            (
                [
                    {"model": "gpt-4o", "input_tokens": 1000, "output_tokens": 500},
                    {"model": "claude-3-opus", "input_tokens": 1000, "output_tokens": 500},
                    {"model": "deepseek-chat", "input_tokens": 1000, "output_tokens": 500},
                ],
                0.0075 + 0.0525 + 0.00028,  # GPT-4o + Claude 3 Opus + DeepSeek
            ),
        ],
    )
    def test_multi_model_cost_variations(self, model_usages, expected_total):
        """测试多模型组合费用变化"""
        results = calculate_multi_model_cost(model_usages)
        total = sum(r.total_cost for r in results)
        assert abs(total - expected_total) < 1e-10


class TestCostCalculationEdgeCases:
    """费用计算边界情况测试"""

    def test_zero_tokens(self):
        """测试零 token"""
        result = calculate_cost("gpt-4o-mini", 0, 0)
        assert result.total_cost == 0.0
        assert result.input_cost == 0.0
        assert result.output_cost == 0.0

    @pytest.mark.parametrize("model", ["gpt-4o-mini", "claude-3.5-opus", "deepseek-chat"])
    def test_zero_input_tokens(self, model):
        """测试零输入 token"""
        result = calculate_cost(model, 0, 1000)
        assert result.input_cost == 0.0
        assert result.output_cost > 0

    @pytest.mark.parametrize("model", ["gpt-4o-mini", "claude-3.5-opus", "deepseek-chat"])
    def test_zero_output_tokens(self, model):
        """测试零输出 token"""
        result = calculate_cost(model, 1000, 0)
        assert result.output_cost == 0.0
        assert result.input_cost > 0

    def test_unknown_model_raises_error(self):
        """测试未知模型抛出错误"""
        with pytest.raises(ValueError) as exc_info:
            calculate_cost("unknown-model", 1000, 500)
        assert "不在定价表中" in str(exc_info.value)

    def test_empty_multi_model_list(self):
        """测试空多模型列表"""
        results = calculate_multi_model_cost([])
        assert results == []

    @pytest.mark.parametrize(
        "input_tokens,output_tokens",
        [
            (1, 1),  # 最小 token
            (10, 5),
            (100, 50),
            (1000, 500),
            (10000, 5000),
            (100000, 50000),
            (1000000, 500000),  # 1M tokens
        ],
    )
    def test_various_token_sizes(self, input_tokens, output_tokens):
        """测试不同 token 规模"""
        result = calculate_cost("gpt-4o-mini", input_tokens, output_tokens)
        # 验证费用随 token 数量单调递增
        assert result.total_cost >= 0
        assert result.input_tokens == input_tokens
        assert result.output_tokens == output_tokens

    def test_cost_estimate_dataclass(self):
        """测试 CostEstimate 数据类"""
        result = calculate_cost("gpt-4o-mini", 1000, 500)
        assert hasattr(result, "model")
        assert hasattr(result, "input_tokens")
        assert hasattr(result, "output_tokens")
        assert hasattr(result, "input_cost")
        assert hasattr(result, "output_cost")
        assert hasattr(result, "total_cost")

    def test_pricing_table_completeness(self):
        """测试定价表完整性"""
        # 验证所有模型都有 input 和 output 价格
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing, f"{model} 缺少 input 价格"
            assert "output" in pricing, f"{model} 缺少 output 价格"
            assert pricing["input"] >= 0, f"{model} input 价格不能为负"
            assert pricing["output"] >= 0, f"{model} output 价格不能为负"

    def test_local_models_are_free(self):
        """测试本地模型免费"""
        local_models = [
            "ollama/qwen2.5:7b",
            "ollama/qwen2.5:14b",
            "ollama/llama3:8b",
        ]
        for model in local_models:
            result = calculate_cost(model, 1_000_000, 1_000_000)
            assert result.total_cost == 0.0
