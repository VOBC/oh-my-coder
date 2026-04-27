from __future__ import annotations
"""
性能优化模块

提供缓存、连接池、异步执行等优化功能。
"""

import asyncio
import functools
import hashlib
import time
from collections import OrderedDict
from collections.abc import Callable
from threading import Lock
from typing import Any


class LRUCache:
    """
    线程安全的 LRU 缓存

    Example:
        >>> cache = LRUCache(max_size=100)
        >>> cache.set("key", "value")
        >>> cache.get("key")
        'value'
    """

    def __init__(self, max_size: int = 1000):
        """
        初始化 LRU 缓存

        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回 None
        """
        with self._lock:
            if key in self._cache:
                # 移动到末尾（最近使用）
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    # 删除最旧的条目
                    self._cache.popitem(last=False)
            self._cache[key] = value

    def delete(self, key: str) -> bool:
        """
        删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict[str, int]:
        """
        获取缓存统计

        Returns:
            包含 hits, misses, size, hit_rate 的字典
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "hit_rate": round(hit_rate, 2),
        }


class AsyncExecutor:
    """
    异步任务执行器

    管理并发任务执行，限制最大并发数。

    Example:
        >>> executor = AsyncExecutor(max_concurrent=5)
        >>> results = await executor.run_all([task1, task2])
    """

    def __init__(self, max_concurrent: int = 10):
        """
        初始化执行器

        Args:
            max_concurrent: 最大并发数
        """
        self.max_concurrent = max_concurrent
        self._semaphore: asyncio.Semaphore | None = None

    async def run(self, coro: Any) -> Any:
        """
        执行单个协程

        Args:
            coro: 协程对象

        Returns:
            协程执行结果
        """
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)

        async with self._semaphore:
            return await coro

    async def run_all(
        self, coros: list[Any], fail_fast: bool = False
    ) -> list[tuple[bool, Any]]:
        """
        执行多个协程

        Args:
            coros: 协程列表
            fail_fast: 是否在第一个错误时停止

        Returns:
            (success, result) 元组列表
        """
        if not coros:
            return []

        results = []

        async def run_with_result(coro):
            try:
                result = await self.run(coro)
                return (True, result)
            except Exception as e:
                if fail_fast:
                    raise
                return (False, type(e).__name__)

        tasks = [run_with_result(c) for c in coros]
        results = await asyncio.gather(*tasks)
        return list(results)


def cache_result(ttl_seconds: int = 300):
    """
    函数结果缓存装饰器

    Args:
        ttl_seconds: 缓存过期时间（秒）

    Example:
        >>> @cache_result(ttl_seconds=60)
        ... def expensive_function(x):
        ...     return x * 2
    """

    def decorator(func: Callable) -> Callable:
        cache: dict[str, tuple[float, Any]] = {}
        lock = Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键（非密码用途）
            key = hashlib.sha256(
                f"{func.__name__}:{args}:{kwargs}".encode()
            ).hexdigest()[:32]

            current_time = time.time()

            with lock:
                if key in cache:
                    timestamp, value = cache[key]
                    if current_time - timestamp < ttl_seconds:
                        return value

                result = func(*args, **kwargs)
                cache[key] = (current_time, result)
                return result

        wrapper.cache_clear = cache.clear  # type: ignore
        return wrapper

    return decorator


def measure_time(func: Callable) -> Callable:
    """
    执行时间测量装饰器

    Example:
        >>> @measure_time
        ... def slow_function():
        ...     time.sleep(1)
        ...     return "done"
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} 执行耗时: {elapsed:.3f}s")
        return result

    return wrapper


class PerformanceMonitor:
    """
    性能监控器

    记录和分析函数执行时间。

    Example:
        >>> monitor = PerformanceMonitor()
        >>> monitor.record("api_call", 0.5)
        >>> monitor.get_stats("api_call")
    """

    def __init__(self):
        """初始化性能监控器"""
        self._records: dict[str, list[float]] = {}

    def record(self, name: str, duration: float) -> None:
        """
        记录执行时间

        Args:
            name: 操作名称
            duration: 执行时间（秒）
        """
        if name not in self._records:
            self._records[name] = []
        self._records[name].append(duration)

    def get_stats(self, name: str) -> dict[str, float]:
        """
        获取统计信息

        Args:
            name: 操作名称

        Returns:
            包含 min, max, avg, count 的字典
        """
        records = self._records.get(name, [])
        if not records:
            return {"min": 0, "max": 0, "avg": 0, "count": 0}

        return {
            "min": min(records),
            "max": max(records),
            "avg": sum(records) / len(records),
            "count": len(records),
        }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """
        获取所有操作的统计信息

        Returns:
            操作名到统计信息的映射
        """
        return {name: self.get_stats(name) for name in self._records}

    def clear(self) -> None:
        """清空所有记录"""
        self._records.clear()


# 全局实例
_cache = LRUCache()
_monitor = PerformanceMonitor()


def get_cache() -> LRUCache:
    """获取全局缓存实例"""
    return _cache


def get_monitor() -> PerformanceMonitor:
    """获取全局性能监控实例"""
    return _monitor
