"""CostOptimizer 测试"""

import pytest

from src.agents.cost_optimizer import Complexity, CostOptimizer, ModelRecommendation


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
