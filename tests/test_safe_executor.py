"""
安全执行器测试

覆盖：
- 正常调用（不放重试）
- ReadTimeout 重试（指数退避）
- 非重试异常直接抛出
- timeout 保护
- 装饰器参数
"""

import asyncio
import pytest

from src.utils.safe_executor import (
    BlockedError,
    safe_execute,
    safe_execute_sync,
)


class TestSafeExecutorAsync:
    """异步 safe_execute 测试"""

    def test_success_no_retry(self) -> None:
        """成功调用不重试"""
        call_count = 0

        @safe_execute(max_attempts=3)
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = asyncio.run(succeed())
        assert result == "ok"
        assert call_count == 1

    def test_retryable_error_retries(self) -> None:
        """可重试错误触发重试"""
        call_count = 0

        @safe_execute(max_attempts=3, base_wait=0.01, max_wait=1.0)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("simulated timeout")
            return "ok"

        result = asyncio.run(flaky())
        assert result == "ok"
        assert call_count == 3

    def test_non_retryable_error_raises(self) -> None:
        """不可重试错误直接抛出"""
        call_count = 0

        @safe_execute(max_attempts=3)
        async def bad():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            asyncio.run(bad())

        assert call_count == 1  # 只调用一次，不重试

    def test_timeout_protection(self) -> None:
        """超时保护生效"""
        call_count = 0

        @safe_execute(max_attempts=1, timeout=0.1)
        async def slow():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(2.0)
            return "ok"

        with pytest.raises((TimeoutError, asyncio.TimeoutError)):
            asyncio.run(slow())

        assert call_count == 1


class TestSafeExecutorSync:
    """同步 safe_execute 测试"""

    def test_sync_success(self) -> None:
        """同步成功调用"""
        call_count = 0

        @safe_execute_sync(max_attempts=3)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeed()
        assert result == "ok"
        assert call_count == 1

    def test_sync_retry(self) -> None:
        """同步重试"""
        call_count = 0

        @safe_execute_sync(max_attempts=3, base_wait=0.01)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("retry me")
            return "done"

        result = flaky()
        assert result == "done"
        assert call_count == 2

    def test_sync_non_retryable(self) -> None:
        """同步不可重试"""
        call_count = 0

        @safe_execute_sync(max_attempts=3)
        def bad():
            nonlocal call_count
            call_count += 1
            raise ValueError("no retry")

        with pytest.raises(ValueError):
            bad()

        assert call_count == 1


class TestBlockedError:
    """BlockedError 测试"""

    def test_blocked_error_message(self) -> None:
        err = BlockedError("rm -rf /", "危险命令")
        assert "Blocked" in str(err)
        assert err.command == "rm -rf /"
        assert err.reason == "危险命令"
