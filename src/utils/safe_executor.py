"""
安全执行器 - Safe Executor

为 API 调用提供重试 + 超时包装，解决高并发偶发超时问题。
基于 tenacity 库实现指数退避重试。

使用示例：
    @safe_execute(max_attempts=3, timeout=30)
    async def call_api():
        return await httpx_client.post(url, json=data)
"""

import asyncio
import functools
from collections.abc import Callable
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

# 需要重试的异常类型
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.ConnectError,
    httpx.HTTPError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def _default_retry_if(exc: Exception) -> bool:
    """默认重试条件：仅重试网络超时类错误"""
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


def safe_execute(
    max_attempts: int = 3,
    timeout: float | None = 30.0,
    base_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """
    安全执行装饰器（异步函数）

    指数退避重试（1s → 2s → 4s）+ 单次调用超时保护。

    Args:
        max_attempts: 最大重试次数
        timeout: 单次调用超时（秒）
        base_wait: 初始退避等待（秒），重试间隔 = base_wait * 2^n
        max_wait: 最大等待时间（秒）

    使用示例：
        @safe_execute(max_attempts=3, timeout=30)
        async def call_api():
            return await httpx_client.post(url, json=data)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 如果没配置超时，用 tenacity 自带的 wait_exponential
            # 如果有超时，用 asyncio.wait_for 包裹

            async for attempt_ctx in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=base_wait, max=max_wait),
                retry=retry_if_exception(_default_retry_if),
                reraise=True,
            ):
                with attempt_ctx:
                    if timeout is not None:
                        return await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=timeout,
                        )
                    return await func(*args, **kwargs)
            return None

        return wrapper

    return decorator


def safe_execute_sync(
    max_attempts: int = 3,
    timeout: float | None = 30.0,
    base_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """
    安全执行装饰器（同步函数）

    参数同 safe_execute。

    使用示例：
        @safe_execute_sync(max_attempts=3)
        def call_api():
            return requests.post(url, json=data)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if not _default_retry_if(exc):
                        raise
                    if attempt < max_attempts:
                        min(base_wait * (2 ** (attempt - 1)), max_wait)

            if last_exc is not None:
                raise last_exc
            return None

        return wrapper

    return decorator


class BlockedError(Exception):
    """命令被安全护栏拦截"""

    def __init__(self, command: str, reason: str):
        self.command = command
        self.reason = reason
        super().__init__(f"Blocked: {reason}\nCommand: {command}")
