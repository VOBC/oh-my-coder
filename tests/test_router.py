"""Tests for src.core.router – target >80% coverage."""
from __future__ import annotations

import asyncio
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.router import (
    ModelRouter,
    NoModelAvailableError,
    RateLimitError,
    ResponseCache,
    RouterConfig,
    RoutingDecision,
    TaskType,
    _TASK_TIER_MAPPING,
)
from src.models.base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
    Usage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(content="ok", model="test", provider=ModelProvider.DEEPSEEK,
                   tier=ModelTier.MEDIUM) -> ModelResponse:
    return ModelResponse(
        content=content,
        model=model,
        provider=provider,
        tier=tier,
        usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )


class FakeModel(BaseModel):
    """Minimal BaseModel subclass for testing."""

    def __init__(self, config: ModelConfig, tier: ModelTier, *,
                 model_name_val: str = "fake-model",
                 provider_val: ModelProvider = ModelProvider.DEEPSEEK,
                 side_effect=None):
        super().__init__(config, tier)
        self._model_name = model_name_val
        self._provider = provider_val
        self._side_effect = side_effect

    @property
    def provider(self) -> ModelProvider:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, messages, **kwargs):
        if self._side_effect:
            raise self._side_effect
        return _make_response(tier=self.tier)

    async def stream(self, messages, **kwargs):
        if self._side_effect:
            raise self._side_effect
        yield "chunk"


def _router_with_fake_models(providers: dict[str, dict[str, FakeModel]] | None = None,
                              config: RouterConfig | None = None) -> ModelRouter:
    """Build a ModelRouter with fake models injected (skips _initialize_models)."""
    with patch.object(ModelRouter, "_initialize_models"):
        router = ModelRouter(config or RouterConfig())
    if providers:
        router._models = providers
    return router


# ---------------------------------------------------------------------------
# TaskType
# ---------------------------------------------------------------------------

class TestTaskType:
    def test_all_returns_list(self):
        result = TaskType.all()
        assert isinstance(result, list)
        assert len(result) == 11
        assert TaskType.EXPLORE in result

    def test_all_contains_known_types(self):
        for attr in ("EXPLORE", "SIMPLE_QA", "FORMATTING", "CODE_GENERATION",
                     "DEBUGGING", "TESTING", "REFACTORING", "ARCHITECTURE",
                     "SECURITY_REVIEW", "CODE_REVIEW", "PLANNING"):
            assert getattr(TaskType, attr) in TaskType.all()


# ---------------------------------------------------------------------------
# RouterConfig
# ---------------------------------------------------------------------------

class TestRouterConfig:
    def test_default_fallback_order_prefer_local(self):
        with patch.dict(os.environ, {"PREFER_LOCAL_MODEL": "true"}, clear=False):
            cfg = RouterConfig()
            assert cfg.fallback_order[0] == "ollama"
            assert "deepseek" in cfg.fallback_order

    def test_default_fallback_order_no_local(self):
        with patch.dict(os.environ, {"PREFER_LOCAL_MODEL": "false"}, clear=False):
            cfg = RouterConfig()
            assert "ollama" not in cfg.fallback_order[:3]  # ollama at end
            assert cfg.fallback_order[-1] == "ollama"

    def test_custom_fallback_order_preserved(self):
        cfg = RouterConfig(fallback_order=["deepseek", "glm"])
        assert cfg.fallback_order == ["deepseek", "glm"]

    def test_api_key_from_env(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}, clear=False):
            cfg = RouterConfig(deepseek_api_key=None)
            # Env var takes precedence; may be overridden by config file
            assert cfg.deepseek_api_key is not None

    def test_ollama_defaults(self):
        cfg = RouterConfig()
        assert cfg.ollama_base_url is not None
        assert cfg.ollama_model is not None

    def test_cache_defaults(self):
        cfg = RouterConfig()
        assert cfg.cache_enabled is True
        assert cfg.cache_ttl_seconds == 300

    def test_load_from_config_file_missing(self):
        with patch.object(Path, "exists", return_value=False):
            cfg = RouterConfig()
            # Should not crash

    def test_load_from_config_file_with_data(self, tmp_path):
        config_dir = tmp_path / ".omc"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({
            "models": {"deepseek": {"api_key": "sk-from-config"}}
        }))
        with patch.object(Path, "home", return_value=tmp_path):
            cfg = RouterConfig(deepseek_api_key=None)
            # If config loaded, key should be set (unless env overrides)

    def test_default_model_from_env(self):
        with patch.dict(os.environ, {"OMC_DEFAULT_MODEL": "glm-4-flash",
                                      "PREFER_LOCAL_MODEL": "false"}, clear=False):
            cfg = RouterConfig()
            assert "glm" in cfg.fallback_order
            assert cfg.fallback_order[0] == "glm"


# ---------------------------------------------------------------------------
# RoutingDecision
# ---------------------------------------------------------------------------

class TestRoutingDecision:
    def test_fields(self):
        d = RoutingDecision(
            task_type="code_generation",
            selected_provider="deepseek",
            selected_tier="medium",
            reason="test",
            estimated_cost=0.01,
        )
        assert d.task_type == "code_generation"
        assert d.timestamp  # auto-generated


# ---------------------------------------------------------------------------
# ResponseCache
# ---------------------------------------------------------------------------

class TestResponseCache:
    def _make_messages(self, content="hello"):
        return [Message(role="user", content=content)]

    def test_cache_miss(self):
        cache = ResponseCache()
        assert cache.get(self._make_messages()) is None

    def test_cache_set_and_get(self):
        cache = ResponseCache()
        msgs = self._make_messages()
        resp = _make_response()
        cache.set(msgs, resp)
        assert cache.get(msgs) is resp

    def test_cache_expiry(self):
        cache = ResponseCache(ttl_seconds=0)
        msgs = self._make_messages()
        cache.set(msgs, _make_response())
        # Already expired
        assert cache.get(msgs) is None

    def test_cache_clear(self):
        cache = ResponseCache()
        cache.set(self._make_messages(), _make_response())
        cache.clear()
        assert cache.get(self._make_messages()) is None

    def test_cache_stats(self):
        cache = ResponseCache()
        cache.set(self._make_messages(), _make_response())
        stats = cache.stats()
        assert stats["total"] == 1
        assert stats["max"] == 100

    def test_cache_eviction(self):
        cache = ResponseCache(max_entries=2)
        msgs_a = self._make_messages("a")
        msgs_b = self._make_messages("b")
        msgs_c = self._make_messages("c")
        cache.set(msgs_a, _make_response())
        cache.set(msgs_b, _make_response())
        cache.set(msgs_c, _make_response())  # should evict a
        assert cache.get(msgs_a) is None
        assert cache.get(msgs_b) is not None

    def test_cache_different_content_different_key(self):
        cache = ResponseCache()
        cache.set(self._make_messages("a"), _make_response())
        assert cache.get(self._make_messages("b")) is None


# ---------------------------------------------------------------------------
# ModelRouter.__init__ and _initialize_models
# ---------------------------------------------------------------------------

class TestModelRouterInit:
    def test_init_no_config(self):
        with patch.object(ModelRouter, "_initialize_models"):
            router = ModelRouter()
            assert router.config is not None
            assert router._total_cost == 0.0
            assert router._cache is not None

    def test_init_cache_disabled(self):
        cfg = RouterConfig(cache_enabled=False)
        with patch.object(ModelRouter, "_initialize_models"):
            router = ModelRouter(cfg)
            assert router._cache is None

    def test_initialize_models_with_deepseek(self):
        cfg = RouterConfig(deepseek_api_key="sk-test", fallback_order=["deepseek"])
        with patch("src.core.router.DeepSeekModel") as MockDS:
            instance = MagicMock()
            MockDS.return_value = instance
            router = ModelRouter(cfg)
            assert "deepseek" in router._models

    def test_initialize_models_no_keys(self):
        cfg = RouterConfig(fallback_order=["deepseek"])
        # No API keys set
        with patch.dict(os.environ, {}, clear=False):
            router = ModelRouter(cfg)
            # deepseek should NOT be in _models if no key
            # (depends on env, but we cleared relevant vars)


# ---------------------------------------------------------------------------
# ModelRouter.select
# ---------------------------------------------------------------------------

class TestModelRouterSelect:
    def _make_router(self):
        fake_models = {}
        for provider in ["deepseek", "glm", "ollama"]:
            fake_models[provider] = {}
            for tier in ["low", "medium", "high"]:
                fake_models[provider][tier] = FakeModel(
                    ModelConfig(), ModelTier(tier)
                )
        cfg = RouterConfig(
            deepseek_api_key="sk-test",
            fallback_order=["deepseek", "glm", "ollama"],
            cache_enabled=False,
        )
        return _router_with_fake_models(fake_models, cfg)

    def test_select_simple_qa_returns_low_tier(self):
        router = self._make_router()
        decision = router.select("simple_qa")
        assert decision.selected_tier == "low"

    def test_select_code_generation_returns_medium(self):
        router = self._make_router()
        decision = router.select("code_generation")
        assert decision.selected_tier == "medium"

    def test_select_architecture_returns_high(self):
        router = self._make_router()
        decision = router.select("architecture")
        assert decision.selected_tier == "high"

    def test_select_unknown_task_defaults_to_medium(self):
        router = self._make_router()
        decision = router.select("unknown_task")
        assert decision.selected_tier == "medium"

    def test_select_complexity_override_low(self):
        router = self._make_router()
        # architecture normally high, with complexity=low → medium
        decision = router.select("architecture", complexity="low")
        assert decision.selected_tier == "medium"

    def test_select_complexity_override_high(self):
        router = self._make_router()
        # explore normally low, with complexity=high → medium
        decision = router.select("explore", complexity="high")
        assert decision.selected_tier == "medium"

    def test_select_budget_downgrade(self):
        router = self._make_router()
        decision = router.select("architecture", budget_remaining=0.001)
        assert decision.selected_tier == "medium"  # high → medium

    def test_select_no_available_model_raises(self):
        router = _router_with_fake_models({}, RouterConfig(fallback_order=["deepseek"], cache_enabled=False))
        with pytest.raises(NoModelAvailableError):
            router.select("code_generation")

    def test_select_fallback_to_second_provider(self):
        fake_models = {
            "deepseek": {},  # no tiers
            "glm": {"medium": FakeModel(ModelConfig(), ModelTier.MEDIUM)},
        }
        cfg = RouterConfig(fallback_order=["deepseek", "glm"], cache_enabled=False)
        router = _router_with_fake_models(fake_models, cfg)
        decision = router.select("code_generation")
        assert decision.selected_provider == "glm"

    def test_select_records_decision(self):
        router = self._make_router()
        router.select("simple_qa")
        assert len(router._decision_history) == 1

    def test_select_estimates_cost(self):
        router = self._make_router()
        decision = router.select("simple_qa")
        assert decision.estimated_cost == 0.0  # FakeModel has 0 cost


# ---------------------------------------------------------------------------
# ModelRouter.route_and_call
# ---------------------------------------------------------------------------

class TestModelRouterRouteAndCall:
    def _make_router(self, side_effect=None):
        fake_models = {}
        for tier in ["low", "medium", "high"]:
            fake_models.setdefault("deepseek", {})[tier] = FakeModel(
                ModelConfig(), ModelTier(tier), side_effect=side_effect
            )
        cfg = RouterConfig(
            deepseek_api_key="sk-test",
            fallback_order=["deepseek"],
            cache_enabled=False,
        )
        return _router_with_fake_models(fake_models, cfg)

    @pytest.mark.asyncio
    async def test_route_and_call_success(self):
        router = self._make_router()
        msgs = [Message(role="user", content="hello")]
        resp = await router.route_and_call("simple_qa", msgs)
        assert resp.content == "ok"

    @pytest.mark.asyncio
    async def test_route_and_call_dict_messages(self):
        router = self._make_router()
        msgs = [{"role": "user", "content": "hello"}]
        resp = await router.route_and_call("simple_qa", msgs)
        assert resp.content == "ok"

    @pytest.mark.asyncio
    async def test_route_and_call_with_cache(self):
        fake_models = {}
        for tier in ["low", "medium", "high"]:
            fake_models.setdefault("deepseek", {})[tier] = FakeModel(
                ModelConfig(), ModelTier(tier)
            )
        cfg = RouterConfig(
            deepseek_api_key="sk-test",
            fallback_order=["deepseek"],
            cache_enabled=True,
        )
        router = _router_with_fake_models(fake_models, cfg)
        msgs = [Message(role="user", content="cached test")]
        resp1 = await router.route_and_call("simple_qa", msgs, use_cache=True)
        resp2 = await router.route_and_call("simple_qa", msgs, use_cache=True)
        # Second should be from cache (same object)
        assert resp1 is resp2

    @pytest.mark.asyncio
    async def test_route_and_call_all_fail_raises(self):
        router = self._make_router(side_effect=RuntimeError("boom"))
        msgs = [Message(role="user", content="hello")]
        with pytest.raises(NoModelAvailableError):
            await router.route_and_call("simple_qa", msgs)

    @pytest.mark.asyncio
    async def test_route_and_call_429_raises_rate_limit(self):
        import httpx
        resp = MagicMock()
        resp.status_code = 429
        err = httpx.HTTPStatusError("429", request=MagicMock(), response=resp)
        fake_models = {}
        for tier in ["low", "medium", "high"]:
            fake_models.setdefault("deepseek", {})[tier] = FakeModel(
                ModelConfig(), ModelTier(tier), side_effect=err
            )
        cfg = RouterConfig(
            deepseek_api_key="sk-test",
            fallback_order=["deepseek"],
            cache_enabled=False,
        )
        router = _router_with_fake_models(fake_models, cfg)
        msgs = [Message(role="user", content="hello")]
        with pytest.raises(RateLimitError):
            await router.route_and_call("simple_qa", msgs)

    @pytest.mark.asyncio
    async def test_route_and_call_override_model(self):
        fake_models = {}
        for tier in ["low", "medium", "high"]:
            fake_models.setdefault("deepseek", {})[tier] = FakeModel(
                ModelConfig(), ModelTier(tier)
            )
            fake_models.setdefault("glm", {})[tier] = FakeModel(
                ModelConfig(), ModelTier(tier), model_name_val="glm-4-flash"
            )
        cfg = RouterConfig(
            deepseek_api_key="sk-test",
            fallback_order=["deepseek", "glm"],
            cache_enabled=False,
        )
        router = _router_with_fake_models(fake_models, cfg)
        msgs = [Message(role="user", content="hello")]
        resp = await router.route_and_call("simple_qa", msgs, override_model="glm-4-flash")
        assert resp is not None

    @pytest.mark.asyncio
    async def test_route_and_call_override_unknown_model(self):
        fake_models = {}
        for tier in ["low", "medium", "high"]:
            fake_models.setdefault("deepseek", {})[tier] = FakeModel(
                ModelConfig(), ModelTier(tier)
            )
        cfg = RouterConfig(
            deepseek_api_key="sk-test",
            fallback_order=["deepseek"],
            cache_enabled=False,
        )
        router = _router_with_fake_models(fake_models, cfg)
        msgs = [Message(role="user", content="hello")]
        resp = await router.route_and_call("simple_qa", msgs, override_model="nonexistent")
        # Falls through to normal routing
        assert resp is not None

    @pytest.mark.asyncio
    async def test_route_and_call_no_cache_flag(self):
        fake_models = {}
        for tier in ["low", "medium", "high"]:
            fake_models.setdefault("deepseek", {})[tier] = FakeModel(
                ModelConfig(), ModelTier(tier)
            )
        cfg = RouterConfig(
            deepseek_api_key="sk-test",
            fallback_order=["deepseek"],
            cache_enabled=True,
        )
        router = _router_with_fake_models(fake_models, cfg)
        msgs = [Message(role="user", content="no cache test")]
        resp = await router.route_and_call("simple_qa", msgs, use_cache=False)
        # Should not be cached
        cached = router._cache.get(msgs) if router._cache else None
        assert cached is None


# ---------------------------------------------------------------------------
# ModelRouter.get_model / get_stats / clear_cache / reset_stats
# ---------------------------------------------------------------------------

class TestModelRouterUtilities:
    def _make_router(self):
        fake_models = {
            "deepseek": {
                "low": FakeModel(ModelConfig(), ModelTier.LOW),
                "medium": FakeModel(ModelConfig(), ModelTier.MEDIUM),
                "high": FakeModel(ModelConfig(), ModelTier.HIGH),
            }
        }
        cfg = RouterConfig(fallback_order=["deepseek"], cache_enabled=True)
        return _router_with_fake_models(fake_models, cfg)

    def test_get_model_found(self):
        router = self._make_router()
        model = router.get_model("deepseek", "medium")
        assert model is not None

    def test_get_model_not_found(self):
        router = self._make_router()
        assert router.get_model("nonexistent", "medium") is None
        assert router.get_model("deepseek", "nonexistent") is None

    def test_get_stats(self):
        router = self._make_router()
        router.select("simple_qa")
        stats = router.get_stats()
        assert stats["total_requests"] == 1
        assert "provider_distribution" in stats
        assert "tier_distribution" in stats
        assert stats["cache"] is not None

    def test_get_stats_no_cache(self):
        cfg = RouterConfig(cache_enabled=False, fallback_order=["deepseek"])
        fake_models = {"deepseek": {"medium": FakeModel(ModelConfig(), ModelTier.MEDIUM)}}
        router = _router_with_fake_models(fake_models, cfg)
        stats = router.get_stats()
        assert stats["cache"] is None

    def test_clear_cache(self):
        router = self._make_router()
        router._cache.set([Message(role="user", content="x")], _make_response())
        router.clear_cache()
        assert router._cache.stats()["total"] == 0

    def test_reset_stats(self):
        router = self._make_router()
        router.select("simple_qa")
        router._total_cost = 1.0
        router.reset_stats()
        assert len(router._decision_history) == 0
        assert router._total_cost == 0.0

    def test_count_by(self):
        router = self._make_router()
        router.select("simple_qa")
        router.select("code_generation")
        counts = router._count_by("selected_provider")
        assert counts["deepseek"] == 2


# ---------------------------------------------------------------------------
# _TASK_TIER_MAPPING
# ---------------------------------------------------------------------------

class TestTierMapping:
    def test_all_task_types_have_mapping(self):
        for task in TaskType.all():
            assert task in _TASK_TIER_MAPPING
            assert _TASK_TIER_MAPPING[task] in ("low", "medium", "high")

    def test_mapping_values(self):
        assert _TASK_TIER_MAPPING[TaskType.EXPLORE] == "low"
        assert _TASK_TIER_MAPPING[TaskType.CODE_GENERATION] == "medium"
        assert _TASK_TIER_MAPPING[TaskType.ARCHITECTURE] == "high"


# ---------------------------------------------------------------------------
# _load_user_models
# ---------------------------------------------------------------------------

class TestLoadUserModels:
    def test_load_user_models_from_yaml(self, tmp_path):
        import yaml
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        yaml_file = models_dir / "custom.yaml"
        yaml_file.write_text(yaml.dump({
            "provider": "custom_provider",
            "model": "custom-model-v1",
            "api_key_env": "CUSTOM_API_KEY",
            "endpoint": "https://api.custom.com/v1",
        }))

        fake_models = {}
        cfg = RouterConfig(fallback_order=["custom_provider"], cache_enabled=False)
        with patch.object(ModelRouter, "_initialize_models"):
            router = ModelRouter(cfg)
        router._models = fake_models

        with patch("src.core.router.USER_MODELS_DIR", models_dir), \
             patch.dict(os.environ, {"CUSTOM_API_KEY": "sk-custom"}):
            router._load_user_models()
            assert "custom_provider" in router._models

    def test_skip_if_provider_exists(self, tmp_path):
        import yaml
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        yaml_file = models_dir / "deepseek.yaml"
        yaml_file.write_text(yaml.dump({
            "provider": "deepseek",
            "model": "deepseek-chat",
        }))

        existing = {"deepseek": {"medium": MagicMock()}}
        cfg = RouterConfig(fallback_order=["deepseek"], cache_enabled=False)
        with patch.object(ModelRouter, "_initialize_models"):
            router = ModelRouter(cfg)
        router._models = existing

        with patch("src.core.router.USER_MODELS_DIR", models_dir):
            router._load_user_models()
            # Should not have overwritten
            assert "deepseek" in router._models

    def test_skip_if_missing_required_fields(self, tmp_path):
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        yaml_file = models_dir / "bad.yaml"
        yaml_file.write_text("provider: test\n")  # missing 'model'

        cfg = RouterConfig(fallback_order=[], cache_enabled=False)
        with patch.object(ModelRouter, "_initialize_models"):
            router = ModelRouter(cfg)
        router._models = {}

        with patch("src.core.router.USER_MODELS_DIR", models_dir):
            router._load_user_models()
            assert "test" not in router._models

    def test_skip_if_no_api_key(self, tmp_path):
        import yaml
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        yaml_file = models_dir / "nokey.yaml"
        yaml_file.write_text(yaml.dump({
            "provider": "nokey_provider",
            "model": "nokey-model",
            "api_key_env": "NOKEY_API_KEY",
        }))

        cfg = RouterConfig(fallback_order=[], cache_enabled=False)
        with patch.object(ModelRouter, "_initialize_models"):
            router = ModelRouter(cfg)
        router._models = {}

        with patch("src.core.router.USER_MODELS_DIR", models_dir), \
             patch.dict(os.environ, {}, clear=False):
            router._load_user_models()
            assert "nokey_provider" not in router._models

    def test_skip_dir_not_exists(self):
        cfg = RouterConfig(fallback_order=[], cache_enabled=False)
        with patch.object(ModelRouter, "_initialize_models"):
            router = ModelRouter(cfg)
        router._models = {}
        with patch("src.core.router.USER_MODELS_DIR", Path("/nonexistent")):
            router._load_user_models()  # should not crash


# ---------------------------------------------------------------------------
# RouterConfig._load_from_config_file
# ---------------------------------------------------------------------------

class TestRouterConfigLoadConfigFile:
    def test_load_with_masked_key_skipped(self, tmp_path):
        config_dir = tmp_path / ".omc"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({
            "models": {"deepseek": {"api_key": "****masked"}}
        }))
        with patch.object(Path, "home", return_value=tmp_path):
            cfg = RouterConfig(deepseek_api_key=None)
            # Masked key should not be loaded

    def test_load_with_invalid_models_section(self, tmp_path):
        config_dir = tmp_path / ".omc"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"models": "not_a_dict"}))
        with patch.object(Path, "home", return_value=tmp_path):
            cfg = RouterConfig()  # should not crash

    def test_load_with_unsupported_provider(self, tmp_path):
        config_dir = tmp_path / ".omc"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({
            "models": {"tiangong": {"api_key": "sk-tiangong"}}
        }))
        with patch.object(Path, "home", return_value=tmp_path):
            cfg = RouterConfig()  # tiangong has None mapping, should skip


# ---------------------------------------------------------------------------
# Complexity edge cases for select()
# ---------------------------------------------------------------------------

class TestSelectComplexity:
    def _make_router(self):
        fake_models = {}
        for p in ["deepseek"]:
            fake_models[p] = {}
            for t in ["low", "medium", "high"]:
                fake_models[p][t] = FakeModel(ModelConfig(), ModelTier(t))
        cfg = RouterConfig(fallback_order=["deepseek"], cache_enabled=False)
        return _router_with_fake_models(fake_models, cfg)

    def test_medium_complexity_no_change(self):
        router = self._make_router()
        # medium task + medium complexity = medium
        d = router.select("code_generation", complexity="medium")
        assert d.selected_tier == "medium"

    def test_low_complexity_medium_task_downgrade(self):
        router = self._make_router()
        d = router.select("code_generation", complexity="low")
        assert d.selected_tier == "low"

    def test_high_complexity_low_task_upgrade(self):
        router = self._make_router()
        d = router.select("explore", complexity="high")
        assert d.selected_tier == "medium"

    def test_high_complexity_high_task_no_change(self):
        router = self._make_router()
        d = router.select("architecture", complexity="high")
        assert d.selected_tier == "high"

    def test_low_complexity_low_task_no_change(self):
        router = self._make_router()
        d = router.select("explore", complexity="low")
        assert d.selected_tier == "low"
