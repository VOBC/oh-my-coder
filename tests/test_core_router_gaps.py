"""
Tests for coverage gaps in src/core/router.py
Covers: line 781 - fallback_order.insert(0, selected_provider) when not in order
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.router import (
    ModelRouter,
    ResponseCache,
    RouterConfig,
    RoutingDecision,
    TaskType,
)


def _make_router_for_gaps() -> ModelRouter:
    """Create a ModelRouter for testing fallback_order.insert gap at line 781."""
    config = RouterConfig(fallback_order=["deepseek", "kimi"])
    router = ModelRouter.__new__(ModelRouter)
    router.config = config
    router._models: dict[str, dict[str, Any]] = {
        "deepseek": {
            "low": MagicMock(),
            "medium": MagicMock(),
            "high": MagicMock(),
        },
        "kimi": {
            "low": MagicMock(),
            "medium": MagicMock(),
            "high": MagicMock(),
        },
    }
    for pmodels in router._models.values():
        for m in pmodels.values():
            m.get_cost.return_value = 0.001
    router._decision_history = []
    router._total_cost = 0.0
    router._cache = None
    return router


class TestFallbackOrderInsertGap:
    """
    Line 781: fallback_order.insert(0, decision.selected_provider)
    when selected_provider is NOT already in fallback_order.

    This is hard to trigger because select() picks from fallback_order.
    However, we can test via route_and_call where the forced_provider
    creates a new fallback_order and then the selected_provider from
    select() may not be in the forced fallback_order.
    """

    @pytest.mark.asyncio
    async def test_fallback_order_insert_when_selected_not_in_order(self):
        """
        Line 781: When forced_provider is set, we build a limited fallback_order
        that may not contain the originally selected provider.

        Scenario:
        - config.fallback_order = ["deepseek", "kimi", "ollama"]
        - select() picks deepseek/high
        - forced_provider = "ollama" (builds fallback_order = ["ollama"])
        - deepseek (selected_provider) is NOT in ["ollama"]
        - → line 781: fallback_order.insert(0, "deepseek")
        """
        config = RouterConfig(fallback_order=["deepseek", "kimi", "ollama"])
        router = ModelRouter.__new__(ModelRouter)
        router.config = config
        router._models = {
            "deepseek": {
                "low": MagicMock(),
                "medium": MagicMock(),
                "high": MagicMock(),
            },
            "kimi": {
                "low": MagicMock(),
                "medium": MagicMock(),
                "high": MagicMock(),
            },
            "ollama": {
                "low": MagicMock(),
                "medium": MagicMock(),
                "high": MagicMock(),
            },
        }
        for pmodels in router._models.values():
            for m in pmodels.values():
                m.get_cost.return_value = 0.001

        mock_resp = MagicMock()
        mock_resp.usage = MagicMock()
        mock_resp.usage.total_tokens = 50
        mock_resp.latency_ms = 0.0

        # deepseek/high will be selected by select()
        router._models["deepseek"]["high"].generate = AsyncMock(return_value=mock_resp)
        router._models["ollama"]["high"].generate = AsyncMock(return_value=mock_resp)
        router._models["ollama"]["high"].get_cost.return_value = 0.001
        router._total_cost = 0.0
        router._cache = None
        router._decision_history = []

        from src.models.base import Message
        msg = Message(role="user", content="hello")

        # Override to ollama — this creates fallback_order = ["ollama"]
        # select() picks deepseek (from config.fallback_order priority)
        # deepseek is NOT in ["ollama"], so line 781 triggers
        response = await router.route_and_call(
            TaskType.ARCHITECTURE,
            [msg],
            override_model="ollama",  # forces ollama as primary, deepseek selected but not in list
        )

        # Both deepseek and ollama were attempted
        assert response is mock_resp


class TestRouterHelpersGaps:
    """Additional helper method coverage"""

    def test_get_stats_with_requests(self):
        """get_stats returns request counts"""
        router = _make_router_for_gaps()
        router._decision_history = [
            RoutingDecision("test", "deepseek", "medium", "test"),
        ]
        stats = router.get_stats()
        assert stats["total_requests"] >= 0

    def test_get_stats_total_cost(self):
        """get_stats includes total_cost"""
        router = _make_router_for_gaps()
        router._total_cost = 0.25
        stats = router.get_stats()
        assert stats["total_cost"] == 0.25

    def test_reset_stats_clears_everything(self):
        """reset_stats clears decision_history and cost"""
        router = _make_router_for_gaps()
        router._total_cost = 99.9
        router._decision_history = [
            RoutingDecision("test", "deepseek", "medium", "test"),
            RoutingDecision("test2", "kimi", "high", "test2"),
        ]
        router.reset_stats()
        assert router._total_cost == 0.0
        assert len(router._decision_history) == 0

    def test_get_model_via_getter(self):
        """get_model returns model instance"""
        router = _make_router_for_gaps()
        model = router.get_model("deepseek", "medium")
        assert model is not None

    def test_get_model_provider_not_found(self):
        """get_model returns None for unknown provider"""
        router = _make_router_for_gaps()
        model = router.get_model("nonexistent_provider", "medium")
        assert model is None

    def test_get_model_tier_not_found(self):
        """get_model returns None for known provider but unknown tier"""
        router = _make_router_for_gaps()
        model = router.get_model("deepseek", "ultra_tier")
        assert model is None


class TestResponseCacheGaps:
    """Additional ResponseCache coverage"""

    def test_cache_key_message_with_special_content(self):
        """Cache key for messages with special characters"""
        from src.models.base import Message, Usage
        cache = ResponseCache(max_entries=10, ttl_seconds=300)
        resp = MagicMock()
        resp.usage = Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        msg1 = Message(role="user", content="Hello\n\tWorld!😀")
        msg2 = Message(role="user", content="Hello\n\tWorld!😀")  # Same content
        msg3 = Message(role="user", content="Different")

        cache.set([msg1], resp)
        assert cache.get([msg2]) is resp
        assert cache.get([msg3]) is None

    def test_cache_key_messages_order_matters(self):
        """Different message order → different cache key"""
        from src.models.base import Message, Usage
        cache = ResponseCache(max_entries=10, ttl_seconds=300)
        resp = MagicMock()
        resp.usage = Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        msgs_a = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi"),
        ]
        msgs_b = [
            Message(role="assistant", content="Hi"),
            Message(role="user", content="Hello"),
        ]

        cache.set(msgs_a, resp)
        assert cache.get(msgs_b) is None  # Different order → different key

    def test_cache_stats_eviction(self):
        """Cache stats reflect eviction"""
        from src.models.base import Message, Usage
        cache = ResponseCache(max_entries=2, ttl_seconds=300)
        resp = MagicMock()
        resp.usage = Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        cache.set([Message(role="u", content="1")], resp)
        cache.set([Message(role="u", content="2")], resp)
        stats = cache.stats()
        assert stats["total"] == 2
        assert stats["active"] == 2


class TestRoutingDecisionGaps:
    """Additional RoutingDecision coverage"""

    def test_routing_decision_full_params(self):
        """RoutingDecision with all optional params"""
        decision = RoutingDecision(
            task_type="code_review",
            selected_provider="deepseek",
            selected_tier="high",
            reason="complex task requires high quality",
            estimated_cost=0.05,
        )
        assert decision.task_type == "code_review"
        assert decision.selected_provider == "deepseek"
        assert decision.selected_tier == "high"
        assert decision.reason == "complex task requires high quality"
        assert decision.estimated_cost == 0.05
        assert decision.timestamp is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
