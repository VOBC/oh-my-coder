"""Tests for cost_optimizer.py"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agents.cost_optimizer import (
    MODEL_PRICING,
    Complexity,
    CostEstimate,
    CostOptimizer,
    ModelRecommendation,
    calculate_cost,
    calculate_multi_model_cost,
    main,
)

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def optimizer():
    """Create a CostOptimizer instance."""
    return CostOptimizer()


@pytest.fixture
def optimizer_no_local():
    """Create a CostOptimizer that doesn't prefer local models."""
    return CostOptimizer(prefer_local=False)


# ── Complexity Enum ───────────────────────────────────────────────


class TestComplexityEnum:
    def test_values(self):
        assert Complexity.LOW.value == "low"
        assert Complexity.MEDIUM.value == "medium"
        assert Complexity.HIGH.value == "high"

    def test_members(self):
        members = list(Complexity)
        assert len(members) == 3
        assert Complexity.LOW in members
        assert Complexity.MEDIUM in members
        assert Complexity.HIGH in members


# ── ModelRecommendation ───────────────────────────────────────────


class TestModelRecommendation:
    def test_creation(self):
        rec = ModelRecommendation(
            model="gpt-4o",
            provider="openai",
            complexity=Complexity.HIGH,
            reason="Complex task",
            estimated_cost=10,
            alternatives=[{"model": "claude-3-opus", "reason": "Backup"}],
        )
        assert rec.model == "gpt-4o"
        assert rec.provider == "openai"
        assert rec.complexity == Complexity.HIGH
        assert rec.estimated_cost == 10
        assert len(rec.alternatives) == 1

    def test_defaults(self):
        rec = ModelRecommendation(
            model="test",
            provider="test",
            complexity=Complexity.LOW,
            reason="test",
            estimated_cost=1,
            alternatives=[],
        )
        assert rec.alternatives == []


# ── CostOptimizer Init ────────────────────────────────────────────


class TestCostOptimizerInit:
    def test_default_prefer_local(self):
        opt = CostOptimizer()
        assert opt.prefer_local is True

    def test_custom_prefer_local(self):
        opt = CostOptimizer(prefer_local=False)
        assert opt.prefer_local is False

    def test_models_defined(self):
        opt = CostOptimizer()
        assert len(opt.MODELS) > 0
        assert "gpt-4o" in opt.MODELS
        assert "deepseek-chat" in opt.MODELS
        assert "ollama/qwen2.5:7b" in opt.MODELS

    def test_complexity_keywords_defined(self):
        opt = CostOptimizer()
        assert Complexity.HIGH in opt.COMPLEXITY_KEYWORDS
        assert Complexity.MEDIUM in opt.COMPLEXITY_KEYWORDS
        assert "refactor" in opt.COMPLEXITY_KEYWORDS[Complexity.HIGH]
        assert "api" in opt.COMPLEXITY_KEYWORDS[Complexity.MEDIUM]


# ── analyze_task ──────────────────────────────────────────────────


class TestAnalyzeTask:
    def test_low_complexity_default(self, optimizer):
        result = optimizer.analyze_task("simple fix")
        assert result["complexity"] == Complexity.LOW
        assert result["high_score"] == 0
        assert result["medium_score"] == 0

    def test_high_complexity_keywords(self, optimizer):
        result = optimizer.analyze_task("refactor the architecture")
        assert result["complexity"] == Complexity.HIGH
        assert result["high_score"] >= 2

    def test_medium_complexity_keywords(self, optimizer):
        result = optimizer.analyze_task("add api and database endpoint")
        assert result["complexity"] == Complexity.MEDIUM
        assert result["medium_score"] >= 2

    def test_file_count_high(self, optimizer):
        result = optimizer.analyze_task("modify code", file_count=15)
        assert result["complexity"] == Complexity.HIGH
        assert result["high_score"] >= 3

    def test_file_count_medium(self, optimizer):
        result = optimizer.analyze_task("modify code", file_count=7)
        assert result["complexity"] == Complexity.MEDIUM
        assert result["medium_score"] >= 2

    def test_file_count_low(self, optimizer):
        result = optimizer.analyze_task("modify code", file_count=2)
        assert result["complexity"] == Complexity.LOW

    def test_new_files_api_service(self, optimizer):
        result = optimizer.analyze_task(
            "add feature", new_files=["user_api.py", "order_service.py"]
        )
        assert result["medium_score"] >= 2

    def test_new_files_app_main(self, optimizer):
        result = optimizer.analyze_task("new project", new_files=["app.py", "main.py"])
        assert result["high_score"] >= 2

    def test_mixed_scores(self, optimizer):
        """Both high and medium keywords present"""
        result = optimizer.analyze_task("refactor api and database")
        # refactor -> high, api/database -> medium
        assert result["high_score"] >= 1
        assert result["medium_score"] >= 2

    def test_case_insensitive(self, optimizer):
        result1 = optimizer.analyze_task("REFACTOR the code")
        result2 = optimizer.analyze_task("refactor the code")
        assert result1["high_score"] == result2["high_score"]

    def test_file_count_none(self, optimizer):
        result = optimizer.analyze_task("task", file_count=None)
        assert "file_count" in result
        assert result["file_count"] is None

    def test_new_files_none(self, optimizer):
        result = optimizer.analyze_task("task", new_files=None)
        assert result["new_files_count"] == 0

    def test_new_files_count(self, optimizer):
        result = optimizer.analyze_task("task", new_files=["a.py", "b.py", "c.py"])
        assert result["new_files_count"] == 3


# ── recommend ─────────────────────────────────────────────────────


class TestRecommend:
    def test_recommend_low_local(self, optimizer):
        rec = optimizer.recommend("fix typo")
        assert rec.complexity == Complexity.LOW
        assert rec.model == "ollama/qwen2.5:7b"
        assert rec.provider == "ollama"
        assert rec.estimated_cost == 1

    def test_recommend_low_no_local(self, optimizer_no_local):
        rec = optimizer_no_local.recommend("fix typo")
        assert rec.complexity == Complexity.LOW
        assert rec.model == "qwen-turbo"
        assert rec.provider == "qwen"

    def test_recommend_medium_local(self, optimizer):
        rec = optimizer.recommend("add api and database endpoint")
        assert rec.complexity == Complexity.MEDIUM
        assert rec.model == "ollama/qwen2.5:14b"
        assert rec.provider == "ollama"

    def test_recommend_medium_no_local(self, optimizer_no_local):
        rec = optimizer_no_local.recommend("add api and database endpoint")
        assert rec.complexity == Complexity.MEDIUM
        assert rec.model == "deepseek-chat"
        assert rec.provider == "deepseek"

    def test_recommend_high_local(self, optimizer):
        rec = optimizer.recommend("refactor architecture design")
        assert rec.complexity == Complexity.HIGH
        assert rec.model == "ollama/qwen2.5:14b"
        assert rec.estimated_cost == 2

    def test_recommend_high_no_local(self, optimizer_no_local):
        rec = optimizer_no_local.recommend("refactor architecture design")
        assert rec.complexity == Complexity.HIGH
        assert rec.model == "gpt-4o"
        assert rec.provider == "openai"
        assert rec.estimated_cost == 10

    def test_recommend_with_file_count(self, optimizer):
        rec = optimizer.recommend("modify", file_count=20)
        assert rec.complexity == Complexity.HIGH

    def test_recommend_with_new_files(self, optimizer):
        rec = optimizer.recommend("new feature", new_files=["service.py", "api.py"])
        assert rec.complexity in [Complexity.MEDIUM, Complexity.HIGH]

    def test_recommend_alternatives(self, optimizer):
        rec = optimizer.recommend("simple task")
        assert len(rec.alternatives) > 0
        assert all("model" in alt and "reason" in alt for alt in rec.alternatives)


# ── _recommend_low ────────────────────────────────────────────────


class TestRecommendLow:
    def test_local_preference(self, optimizer):
        analysis = {"complexity": Complexity.LOW}
        rec = optimizer._recommend_low(analysis)
        assert rec.model == "ollama/qwen2.5:7b"
        assert "本地" in rec.reason or "7B" in rec.reason

    def test_no_local_preference(self, optimizer_no_local):
        analysis = {"complexity": Complexity.LOW}
        rec = optimizer_no_local._recommend_low(analysis)
        assert rec.model == "qwen-turbo"
        assert "国产" in rec.reason or "性价比" in rec.reason


# ── _recommend_medium ─────────────────────────────────────────────


class TestRecommendMedium:
    def test_local_preference(self, optimizer):
        analysis = {"complexity": Complexity.MEDIUM}
        rec = optimizer._recommend_medium(analysis)
        assert rec.model == "ollama/qwen2.5:14b"
        assert "14B" in rec.reason or "本地" in rec.reason

    def test_no_local_preference(self, optimizer_no_local):
        analysis = {"complexity": Complexity.MEDIUM}
        rec = optimizer_no_local._recommend_medium(analysis)
        assert rec.model == "deepseek-chat"
        assert "DeepSeek" in rec.reason or "代码" in rec.reason


# ── _recommend_high ───────────────────────────────────────────────


class TestRecommendHigh:
    def test_local_preference(self, optimizer):
        analysis = {"complexity": Complexity.HIGH}
        rec = optimizer._recommend_high(analysis)
        assert rec.model == "ollama/qwen2.5:14b"
        assert rec.estimated_cost == 2

    def test_no_local_preference(self, optimizer_no_local):
        analysis = {"complexity": Complexity.HIGH}
        rec = optimizer_no_local._recommend_high(analysis)
        assert rec.model == "gpt-4o"
        assert rec.estimated_cost == 10


# ── get_all_models ────────────────────────────────────────────────


class TestGetAllModels:
    def test_returns_list(self, optimizer):
        models = optimizer.get_all_models()
        assert isinstance(models, list)
        assert len(models) > 0

    def test_sorted_by_cost(self, optimizer):
        models = optimizer.get_all_models()
        costs = [m["cost"] for m in models]
        assert costs == sorted(costs)

    def test_model_structure(self, optimizer):
        models = optimizer.get_all_models()
        for m in models:
            assert "model" in m
            assert "provider" in m
            assert "cost" in m
            assert "strengths" in m
            assert isinstance(m["strengths"], list)

    def test_includes_all_models(self, optimizer):
        models = optimizer.get_all_models()
        model_names = {m["model"] for m in models}
        assert "gpt-4o" in model_names
        assert "deepseek-chat" in model_names
        assert "ollama/qwen2.5:7b" in model_names


# ── calculate_cost ────────────────────────────────────────────────


class TestCalculateCost:
    def test_gpt4o(self):
        result = calculate_cost("gpt-4o", 1_000_000, 500_000)
        assert result.model == "gpt-4o"
        assert result.input_tokens == 1_000_000
        assert result.output_tokens == 500_000
        # input: 2.50, output: 10.00 per 1M
        assert result.input_cost == 2.50
        assert result.output_cost == 5.00
        assert result.total_cost == 7.50

    def test_deepseek(self):
        result = calculate_cost("deepseek-chat", 1_000_000, 1_000_000)
        # input: 0.14, output: 0.28 per 1M
        assert result.input_cost == 0.14
        assert result.output_cost == 0.28
        assert abs(result.total_cost - 0.42) < 0.0001

    def test_ollama_free(self):
        result = calculate_cost("ollama/qwen2.5:7b", 1_000_000, 1_000_000)
        assert result.input_cost == 0.0
        assert result.output_cost == 0.0
        assert result.total_cost == 0.0

    def test_zero_tokens(self):
        result = calculate_cost("gpt-4o", 0, 0)
        assert result.total_cost == 0.0

    def test_small_tokens(self):
        result = calculate_cost("gpt-4o-mini", 1000, 500)
        # input: 0.15, output: 0.60 per 1M
        expected_input = (1000 / 1_000_000) * 0.15
        expected_output = (500 / 1_000_000) * 0.60
        assert abs(result.input_cost - expected_input) < 0.0001
        assert abs(result.output_cost - expected_output) < 0.0001

    def test_invalid_model(self):
        with pytest.raises(ValueError) as exc_info:
            calculate_cost("nonexistent-model", 1000, 1000)
        assert "不在定价表中" in str(exc_info.value)

    def test_all_models_in_pricing(self):
        """Ensure all MODELS entries have pricing (or are intentionally excluded)"""
        optimizer = CostOptimizer()
        # moonshot-v1 is an alias, actual pricing uses moonshot-v1-8k/32k
        excluded = {"moonshot-v1"}
        for model in optimizer.MODELS:
            if model not in excluded:
                assert model in MODEL_PRICING, f"{model} missing from MODEL_PRICING"


# ── calculate_multi_model_cost ────────────────────────────────────


class TestCalculateMultiModelCost:
    def test_single_model(self):
        usages = [{"model": "gpt-4o", "input_tokens": 1000, "output_tokens": 500}]
        results = calculate_multi_model_cost(usages)
        assert len(results) == 1
        assert results[0].model == "gpt-4o"

    def test_multiple_models(self):
        usages = [
            {"model": "gpt-4o", "input_tokens": 1000, "output_tokens": 500},
            {"model": "deepseek-chat", "input_tokens": 2000, "output_tokens": 1000},
        ]
        results = calculate_multi_model_cost(usages)
        assert len(results) == 2
        assert results[0].model == "gpt-4o"
        assert results[1].model == "deepseek-chat"

    def test_empty_list(self):
        results = calculate_multi_model_cost([])
        assert results == []

    def test_total_cost_sum(self):
        usages = [
            {"model": "gpt-4o-mini", "input_tokens": 1_000_000, "output_tokens": 0},
            {"model": "gpt-4o-mini", "input_tokens": 0, "output_tokens": 1_000_000},
        ]
        results = calculate_multi_model_cost(usages)
        total = sum(r.total_cost for r in results)
        # input: 0.15, output: 0.60 per 1M
        assert abs(total - 0.75) < 0.0001


# ── CostEstimate ──────────────────────────────────────────────────


class TestCostEstimate:
    def test_creation(self):
        estimate = CostEstimate(
            model="test",
            input_tokens=100,
            output_tokens=50,
            input_cost=0.01,
            output_cost=0.02,
            total_cost=0.03,
        )
        assert estimate.model == "test"
        assert estimate.total_cost == 0.03


# ── CLI main ──────────────────────────────────────────────────────


class TestMain:
    def test_list_models(self, capsys):
        with patch("sys.argv", ["cost_optimizer", "--list"]):
            main()
        captured = capsys.readouterr()
        assert "可用模型" in captured.out
        assert "gpt-4o" in captured.out

    def test_no_task_prints_help(self, capsys):
        with patch("sys.argv", ["cost_optimizer"]):
            main()
        captured = capsys.readouterr()
        # argparse prints help to stdout when no args
        assert "任务描述" in captured.out or "usage" in captured.out

    def test_recommend_simple_task(self, capsys):
        with patch("sys.argv", ["cost_optimizer", "fix typo"]):
            main()
        captured = capsys.readouterr()
        assert "推荐模型" in captured.out
        assert "ollama/qwen2.5:7b" in captured.out

    def test_recommend_with_files(self, capsys):
        with patch("sys.argv", ["cost_optimizer", "refactor code", "--files", "15"]):
            main()
        captured = capsys.readouterr()
        assert "文件数" in captured.out
        assert "15" in captured.out

    def test_recommend_complex_task(self, capsys):
        with patch("sys.argv", ["cost_optimizer", "refactor architecture"]):
            main()
        captured = capsys.readouterr()
        assert "复杂度" in captured.out
        assert "high" in captured.out


# ── MODEL_PRICING Coverage ────────────────────────────────────────


class TestModelPricing:
    def test_all_pricing_entries(self):
        """Ensure all pricing entries have input and output keys"""
        for _model, pricing in MODEL_PRICING.items():
            assert "input" in pricing
            assert "output" in pricing
            assert isinstance(pricing["input"], (int, float))
            assert isinstance(pricing["output"], (int, float))
            assert pricing["input"] >= 0
            assert pricing["output"] >= 0

    def test_claude_models(self):
        assert "claude-3-opus" in MODEL_PRICING
        assert "claude-3-sonnet" in MODEL_PRICING
        assert "claude-3-haiku" in MODEL_PRICING
        assert "claude-3.5-sonnet" in MODEL_PRICING
        assert "claude-3.5-opus" in MODEL_PRICING

    def test_openai_models(self):
        assert "gpt-4o" in MODEL_PRICING
        assert "gpt-4o-mini" in MODEL_PRICING
        assert "gpt-4-turbo" in MODEL_PRICING

    def test_chinese_models(self):
        assert "deepseek-chat" in MODEL_PRICING
        assert "qwen-turbo" in MODEL_PRICING
        assert "qwen-plus" in MODEL_PRICING
        assert "glm-4" in MODEL_PRICING
        assert "moonshot-v1-8k" in MODEL_PRICING
        assert "moonshot-v1-32k" in MODEL_PRICING
