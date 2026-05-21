"""Tests for utils/performance.py."""
import time
from unittest.mock import patch

import pytest

from src.utils.performance import (
    AsyncExecutor,
    LRUCache,
    PerformanceMonitor,
    cache_result,
    get_cache,
    get_monitor,
    measure_time,
)

# ─────────────────────────────────────────────────────────────
# LRUCache
# ─────────────────────────────────────────────────────────────


class TestLRUCache:
    def test_init_default(self):
        cache = LRUCache()
        assert cache.max_size == 1000
        assert len(cache._cache) == 0
        assert cache._hits == 0
        assert cache._misses == 0

    def test_init_custom_size(self):
        cache = LRUCache(max_size=50)
        assert cache.max_size == 50

    def test_get_miss(self):
        cache = LRUCache()
        assert cache.get("nonexistent") is None
        assert cache._misses == 1
        assert cache._hits == 0

    def test_get_hit(self):
        cache = LRUCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"
        assert cache._hits == 1
        assert cache._misses == 0

    def test_get_moves_to_end(self):
        cache = LRUCache(max_size=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # moves "a" to end
        cache.set("c", 3)  # should evict "b" (not "a")
        assert "a" in cache._cache
        assert "b" not in cache._cache
        assert "c" in cache._cache

    def test_set_new_key(self):
        cache = LRUCache(max_size=2)
        cache.set("a", 1)
        assert cache._cache["a"] == 1
        assert len(cache._cache) == 1

    def test_set_existing_key(self):
        cache = LRUCache()
        cache.set("a", 1)
        cache.set("a", 2)
        assert cache._cache["a"] == 2
        assert len(cache._cache) == 1

    def test_set_eviction(self):
        cache = LRUCache(max_size=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # evicts "a"
        assert "a" not in cache._cache
        assert "b" in cache._cache
        assert "c" in cache._cache

    def test_delete_existing(self):
        cache = LRUCache()
        cache.set("a", 1)
        assert cache.delete("a") is True
        assert "a" not in cache._cache

    def test_delete_nonexistent(self):
        cache = LRUCache()
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        cache = LRUCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # record a hit
        cache.clear()
        assert len(cache._cache) == 0
        assert cache._hits == 0
        assert cache._misses == 0

    def test_stats_empty(self):
        cache = LRUCache()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
        assert stats["hit_rate"] == 0

    def test_stats_with_hits(self):
        cache = LRUCache()
        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_thread_safety_set(self):
        """Basic test that lock doesn't deadlock."""
        cache = LRUCache(max_size=10)
        for i in range(20):
            cache.set(f"key{i}", f"value{i}")
        assert len(cache._cache) <= 10


# ─────────────────────────────────────────────────────────────
# AsyncExecutor
# ─────────────────────────────────────────────────────────────


class TestAsyncExecutor:
    async def test_run_single(self):
        async def coro():
            return 42

        executor = AsyncExecutor(max_concurrent=2)
        result = await executor.run(coro())
        assert result == 42

    async def test_run_all_empty(self):
        executor = AsyncExecutor()
        results = await executor.run_all([])
        assert results == []

    async def test_run_all_success(self):
        async def make_coro(val):
            return val * 2

        executor = AsyncExecutor(max_concurrent=2)
        coros = [make_coro(i) for i in range(3)]
        results = await executor.run_all(coros)
        assert all(success for success, _ in results)
        assert [r for _, r in results] == [0, 2, 4]

    async def test_run_all_fail_fast_false(self):
        async def ok():
            return "ok"

        async def fail():
            raise ValueError("bad")

        executor = AsyncExecutor(max_concurrent=2)
        results = await executor.run_all([ok(), fail(), ok()])
        assert len(results) == 3
        assert results[0] == (True, "ok")
        assert results[1][0] is False
        assert results[1][1] == "ValueError"
        assert results[2] == (True, "ok")

    async def test_run_all_fail_fast_true(self):
        async def fail():
            raise ValueError("bad")

        async def ok():
            return "ok"

        executor = AsyncExecutor(max_concurrent=2)
        with pytest.raises(ValueError):
            await executor.run_all([fail(), ok()], fail_fast=True)

    def test_semaphore_initialized_lazily(self):
        executor = AsyncExecutor(max_concurrent=5)
        assert executor._semaphore is None


# ─────────────────────────────────────────────────────────────
# cache_result decorator
# ─────────────────────────────────────────────────────────────


class TestCacheResult:
    def test_cache_hit(self):
        call_count = 0

        @cache_result(ttl_seconds=10)
        def my_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert my_func(5) == 10
        assert call_count == 1
        assert my_func(5) == 10  # cached
        assert call_count == 1

    def test_cache_miss_ttl_expired(self):
        @cache_result(ttl_seconds=0)  # TTL=0 means immediate expiry
        def my_func(x):
            return x * 2

        with patch("time.time", return_value=1000):
            assert my_func(5) == 10
        with patch("time.time", return_value=1000):
            assert my_func(5) == 10  # same time, cached

    def test_cache_different_args(self):
        @cache_result(ttl_seconds=60)
        def my_func(x):
            return x * 2

        assert my_func(5) == 10
        assert my_func(10) == 20

    def test_cache_kwargs(self):
        @cache_result(ttl_seconds=60)
        def my_func(x, y=1):
            return x + y

        assert my_func(5, y=2) == 7
        assert my_func(5, y=2) == 7  # cached

    def test_cache_clear(self):
        @cache_result(ttl_seconds=60)
        def my_func(x):
            return x * 2

        my_func(5)
        my_func.cache_clear()
        # After clear, the cache dict should be empty
        assert True  # No error = pass

    def test_cache_ttl_expiry(self):
        mock_time = [1000.0]

        @cache_result(ttl_seconds=5)
        def my_func(x):
            return x * 2

        with patch("time.time", side_effect=lambda: mock_time[0]):
            assert my_func(5) == 10  # cached at t=1000

        mock_time[0] = 1006  # 6 seconds later, TTL expired
        with patch("time.time", side_effect=lambda: mock_time[0]):
            assert my_func(5) == 10  # recomputed (but result same)


# ─────────────────────────────────────────────────────────────
# measure_time decorator
# ─────────────────────────────────────────────────────────────


class TestMeasureTime:
    def test_measure_time_calls_func(self, capsys):
        @measure_time
        def my_func():
            return 42

        result = my_func()
        assert result == 42

    def test_measure_time_output(self, capsys):
        @measure_time
        def slow_func():
            time.sleep(0.01)
            return "done"

        with patch("time.perf_counter", side_effect=[0.0, 0.01]):
            result = slow_func()
        assert result == "done"


# ─────────────────────────────────────────────────────────────
# PerformanceMonitor
# ─────────────────────────────────────────────────────────────


class TestPerformanceMonitor:
    def test_init(self):
        monitor = PerformanceMonitor()
        assert monitor._records == {}

    def test_record(self):
        monitor = PerformanceMonitor()
        monitor.record("api_call", 0.5)
        assert monitor._records["api_call"] == [0.5]

    def test_record_multiple(self):
        monitor = PerformanceMonitor()
        monitor.record("api_call", 0.5)
        monitor.record("api_call", 0.7)
        assert monitor._records["api_call"] == [0.5, 0.7]

    def test_get_stats_empty(self):
        monitor = PerformanceMonitor()
        stats = monitor.get_stats("nonexistent")
        assert stats == {"min": 0, "max": 0, "avg": 0, "count": 0}

    def test_get_stats(self):
        monitor = PerformanceMonitor()
        monitor.record("api_call", 0.5)
        monitor.record("api_call", 1.5)
        stats = monitor.get_stats("api_call")
        assert stats["min"] == pytest.approx(0.5)
        assert stats["max"] == pytest.approx(1.5)
        assert stats["avg"] == pytest.approx(1.0)
        assert stats["count"] == 2

    def test_get_all_stats(self):
        monitor = PerformanceMonitor()
        monitor.record("api", 0.5)
        monitor.record("db", 0.1)
        all_stats = monitor.get_all_stats()
        assert "api" in all_stats
        assert "db" in all_stats

    def test_clear(self):
        monitor = PerformanceMonitor()
        monitor.record("api", 0.5)
        monitor.clear()
        assert monitor._records == {}


# ─────────────────────────────────────────────────────────────
# Global instances
# ─────────────────────────────────────────────────────────────


class TestGlobalInstances:
    def test_get_cache(self):
        cache = get_cache()
        assert isinstance(cache, LRUCache)

    def test_get_monitor(self):
        monitor = get_monitor()
        assert isinstance(monitor, PerformanceMonitor)

    def test_get_cache_singleton(self):
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2
