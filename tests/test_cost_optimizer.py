"""Tests for agents/cost_optimizer.py"""
from __future__ import annotations

import pytest

from src.agents.cost_optimizer import (
    Complexity,
    CostOptimizer,
    ModelRecommendation,
)


class TestComplexity:
    def test_enum_values(self):
        assert Complexity.LOW.value == "low"
        assert Complexity.MEDIUM.value == "medium"
        assert Complexity.HIGH.value == "high"


class TestModelRecommendation:
    def test_creation(self):
        rec = ModelRecommendation(
            model="deepseek-chat",
            provider="deepseek",
            complexity=Complexity.MEDIUM,
            reason="性价比高",
            estimated_cost=4,
            alternatives=[{"model": "qwen-turbo", "reason": "阿里系"}],
        )
        assert rec.model == "deepseek-chat"
        assert rec.provider == "deepseek"
        assert rec.complexity == Complexity.MEDIUM
        assert rec.reason == "性价比高"
        assert rec.estimated_cost == 4
        assert len(rec.alternatives) == 1

    def test_is_dataclass(self):
        rec = ModelRecommendation(
            model="gpt-4o",
            provider="openai",
            complexity=Complexity.HIGH,
            reason="顶级模型",
            estimated_cost=10,
            alternatives=[],
        )
        # Plain dataclass - accessible as attributes
        assert rec.model == "gpt-4o"
        assert rec.complexity == Complexity.HIGH
        assert rec.provider == "openai"


class TestCostOptimizer:
    def test_init_default(self):
        opt = CostOptimizer()
        assert opt.prefer_local is True

    def test_init_explicit(self):
        opt = CostOptimizer(prefer_local=False)
        assert opt.prefer_local is False

    # --- analyze_task ---

    def test_analyze_low_complexity_simple_task(self):
        opt = CostOptimizer()
        result = opt.analyze_task("fix a bug")
        assert result["complexity"] == Complexity.LOW

    def test_analyze_medium_complexity_api_task(self):
        opt = CostOptimizer()
        result = opt.analyze_task("add auth API endpoint")
        assert result["complexity"] == Complexity.MEDIUM

    def test_analyze_high_complexity_refactor(self):
        opt = CostOptimizer()
        result = opt.analyze_task("重构微服务架构")
        assert result["complexity"] == Complexity.HIGH

    def test_analyze_high_complexity_english_keywords(self):
        opt = CostOptimizer()
        result = opt.analyze_task("refactor architecture design")
        assert result["complexity"] == Complexity.HIGH

    def test_analyze_file_count_low(self):
        opt = CostOptimizer()
        result = opt.analyze_task("simple edit", file_count=2)
        assert result["complexity"] == Complexity.LOW
        assert result["file_count"] == 2

    def test_analyze_file_count_medium(self):
        opt = CostOptimizer()
        result = opt.analyze_task("update API", file_count=6)
        assert result["complexity"] == Complexity.MEDIUM
        assert result["file_count"] == 6

    def test_analyze_file_count_high(self):
        opt = CostOptimizer()
        result = opt.analyze_task("multiple changes", file_count=15)
        assert result["complexity"] == Complexity.HIGH
        assert result["file_count"] == 15

    def test_analyze_new_files_medium_keywords(self):
        opt = CostOptimizer()
        # Need 2 medium_score to reach MEDIUM
        result = opt.analyze_task(
            "api endpoint", new_files=["src/api/users.py"]
        )
        assert result["complexity"] == Complexity.MEDIUM

    def test_analyze_new_files_high_keywords(self):
        opt = CostOptimizer()
        # Need 2 high_score to reach HIGH
        result = opt.analyze_task(
            "new project", new_files=["src/main.py", "app/server.py"]
        )
        assert result["complexity"] == Complexity.HIGH

    def test_analyze_new_files_count(self):
        opt = CostOptimizer()
        result = opt.analyze_task("new project", new_files=["a.py", "b.py"])
        assert result["new_files_count"] == 2

    def test_analyze_combined_scores(self):
        opt = CostOptimizer()
        result = opt.analyze_task("refactor", file_count=15)
        assert result["complexity"] == Complexity.HIGH

    # --- recommend ---

    def test_recommend_low_prefer_local(self):
        opt = CostOptimizer(prefer_local=True)
        rec = opt.recommend("fix typo")
        assert rec.complexity == Complexity.LOW
        assert rec.model == "ollama/qwen2.5:7b"
        assert rec.provider == "ollama"
        assert len(rec.alternatives) == 2

    def test_recommend_low_no_prefer_local(self):
        opt = CostOptimizer(prefer_local=False)
        rec = opt.recommend("fix typo")
        assert rec.complexity == Complexity.LOW
        assert rec.model == "qwen-turbo"
        assert rec.provider == "qwen"

    def test_recommend_medium_prefer_local(self):
        opt = CostOptimizer(prefer_local=True)
        rec = opt.recommend("add user login API", file_count=5)
        assert rec.complexity == Complexity.MEDIUM
        assert rec.model == "ollama/qwen2.5:14b"
        assert rec.provider == "ollama"

    def test_recommend_medium_no_prefer_local(self):
        opt = CostOptimizer(prefer_local=False)
        rec = opt.recommend("add auth endpoint", file_count=4)
        assert rec.complexity == Complexity.MEDIUM
        assert rec.model == "deepseek-chat"
        assert rec.provider == "deepseek"

    def test_recommend_high_prefer_local(self):
        opt = CostOptimizer(prefer_local=True)
        rec = opt.recommend("重构系统架构", file_count=20)
        assert rec.complexity == Complexity.HIGH
        assert rec.model == "ollama/qwen2.5:14b"
        assert rec.estimated_cost == 2

    def test_recommend_high_no_prefer_local(self):
        opt = CostOptimizer(prefer_local=False)
        rec = opt.recommend("架构设计", file_count=15)
        assert rec.complexity == Complexity.HIGH
        assert rec.model == "gpt-4o"
        assert rec.provider == "openai"
        assert rec.estimated_cost == 10

    # --- get_all_models ---

    def test_get_all_models_returns_list(self):
        opt = CostOptimizer()
        models = opt.get_all_models()
        assert isinstance(models, list)
        assert len(models) > 0

    def test_get_all_models_structure(self):
        opt = CostOptimizer()
        models = opt.get_all_models()
        for m in models:
            assert "model" in m
            assert "provider" in m
            assert "cost" in m
            assert "strengths" in m

    def test_get_all_models_includes_ollama(self):
        opt = CostOptimizer()
        models = opt.get_all_models()
        names = [m["model"] for m in models]
        assert "ollama/qwen2.5:7b" in names
        assert "ollama/qwen2.5:14b" in names

    def test_get_all_models_includes_cloud(self):
        opt = CostOptimizer()
        models = opt.get_all_models()
        providers = {m["provider"] for m in models}
        assert "deepseek" in providers
        assert "qwen" in providers
        assert "openai" in providers
        assert "anthropic" in providers

    def test_get_all_models_cost_range(self):
        opt = CostOptimizer()
        models = opt.get_all_models()
        for m in models:
            assert 1 <= m["cost"] <= 10


class TestCalculateCost:
    def test_calculate_cost_basic(self):
        from src.agents.cost_optimizer import calculate_cost
        est = calculate_cost("gpt-4o-mini", input_tokens=1_000_000, output_tokens=500_000)
        assert est.model == "gpt-4o-mini"
        assert est.input_tokens == 1_000_000
        assert est.output_tokens == 500_000
        assert est.input_cost > 0
        assert est.output_cost > 0
        assert est.total_cost == est.input_cost + est.output_cost

    def test_calculate_cost_deepseek(self):
        from src.agents.cost_optimizer import calculate_cost
        est = calculate_cost("deepseek-chat", input_tokens=100_000, output_tokens=50_000)
        assert est.model == "deepseek-chat"
        assert est.total_cost > 0

    def test_calculate_cost_raises_on_unknown_model(self):
        from src.agents.cost_optimizer import calculate_cost
        with pytest.raises(ValueError, match="不在定价表中"):
            calculate_cost("unknown-model", 1000, 500)

    def test_calculate_multi_model_cost(self):
        from src.agents.cost_optimizer import calculate_multi_model_cost
        usages = [
            {"model": "gpt-4o-mini", "input_tokens": 1000, "output_tokens": 500},
            {"model": "deepseek-chat", "input_tokens": 2000, "output_tokens": 1000},
        ]
        results = calculate_multi_model_cost(usages)
        assert len(results) == 2
        assert results[0].model == "gpt-4o-mini"
        assert results[1].model == "deepseek-chat"

    def test_calculate_multi_model_cost_empty(self):
        from src.agents.cost_optimizer import calculate_multi_model_cost
        results = calculate_multi_model_cost([])
        assert results == []


class TestCostOptimizerMain:
    def test_main_list_flag(self, capsys):
        import sys

        from src.agents.cost_optimizer import main
        sys.argv = ["cost_optimizer", "--list"]
        main()
        out = capsys.readouterr().out
        assert "可用模型" in out
        assert "gpt-4o" in out

    def test_main_recommend_task(self, capsys):
        import sys

        from src.agents.cost_optimizer import main
        sys.argv = ["cost_optimizer", "重构微服务架构", "--files", "20"]
        main()
        out = capsys.readouterr().out
        assert "推荐模型" in out
