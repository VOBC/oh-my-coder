"""
测试 HTTP 错误处理：429 限流、401 认证失败、500 服务器错误

覆盖两个层级：
1. DeepSeekModel 适配器 - httpx 错误 → DeepSeekAPIError
2. ModelRouter 路由器 - HTTP 错误 → 重试 / failover / RateLimitError / NoModelAvailableError

运行: pytest tests/test_error_handling.py -v
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.router import (
    ModelRouter,
    NoModelAvailableError,
    RateLimitError,
    RouterConfig,
    TaskType,
)
from src.models.base import Message, ModelConfig, ModelResponse, ModelTier, Usage
from src.models.deepseek import DeepSeekAPIError, DeepSeekModel


# ============================================================
# Helpers
# ============================================================


def _make_http_error(status_code: int, msg: str = "") -> httpx.HTTPStatusError:
    """构造 httpx.HTTPStatusError"""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"error": {"message": msg or f"HTTP {status_code}"}}
    return httpx.HTTPStatusError(
        f"{status_code} Error",
        request=MagicMock(),
        response=mock_resp,
    )


def _make_success_response(content: str = "OK") -> ModelResponse:
    """构造成功的 ModelResponse"""
    return ModelResponse(
        content=content,
        model="deepseek-chat",
        provider="deepseek",
        tier=ModelTier.LOW,
        usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        finish_reason="stop",
    )


# ============================================================
# DeepSeekModel 适配器级错误处理
# ============================================================


class TestDeepSeekAdapterErrors:
    """测试 DeepSeek 模型适配器的 HTTP 错误处理"""

    @pytest.mark.asyncio
    async def test_401_raises_deepseek_api_error(self):
        """401 认证失败应抛 DeepSeekAPIError"""
        config = ModelConfig(api_key="invalid_key")
        model = DeepSeekModel(config, ModelTier.MEDIUM)

        http_error = _make_http_error(401, "Invalid API key")

        with patch.object(model, "_get_client") as mock_client:
            client = AsyncMock()
            # post 返回一个 raise_for_status 会抛 401 的 response
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = http_error
            mock_resp.json.return_value = {"error": {"message": "Invalid API key"}}
            client.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = client

            messages = [Message(role="user", content="test")]
            with pytest.raises(DeepSeekAPIError) as exc_info:
                await model.generate(messages)

            assert "401" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_500_raises_deepseek_api_error(self):
        """500 服务器错误应抛 DeepSeekAPIError"""
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config, ModelTier.LOW)

        http_error = _make_http_error(500, "Internal Server Error")

        with patch.object(model, "_get_client") as mock_client:
            client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = http_error
            mock_resp.json.return_value = {
                "error": {"message": "Internal Server Error"}
            }
            client.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = client

            messages = [Message(role="user", content="test")]
            with pytest.raises(DeepSeekAPIError) as exc_info:
                await model.generate(messages)

            assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_429_raises_deepseek_api_error(self):
        """429 限流在适配器层应抛 DeepSeekAPIError"""
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config, ModelTier.LOW)

        http_error = _make_http_error(429, "Rate limit exceeded")

        with patch.object(model, "_get_client") as mock_client:
            client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = http_error
            mock_resp.json.return_value = {"error": {"message": "Rate limit exceeded"}}
            client.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = client

            messages = [Message(role="user", content="test")]
            with pytest.raises(DeepSeekAPIError) as exc_info:
                await model.generate(messages)

            assert "429" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_network_error_raises_deepseek_api_error(self):
        """网络请求失败（如连接超时）应抛 DeepSeekAPIError"""
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config, ModelTier.LOW)

        with patch.object(model, "_get_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(
                side_effect=httpx.ConnectTimeout("Connection timed out")
            )
            mock_client.return_value = client

            messages = [Message(role="user", content="test")]
            with pytest.raises(DeepSeekAPIError) as exc_info:
                await model.generate(messages)

            assert "网络请求失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """API 返回非标准 JSON 格式时的容错处理"""
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config, ModelTier.LOW)

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        # 返回缺少 choices 的 JSON
        mock_resp.json.return_value = {"id": "test", "no_choices": True}

        with patch.object(model, "_get_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = client

            messages = [Message(role="user", content="test")]
            # 缺少 choices 应抛 KeyError，被外层捕获
            with pytest.raises((KeyError, DeepSeekAPIError)):
                await model.generate(messages)


# ============================================================
# Router 级别 HTTP 错误 failover
# ============================================================


class TestRouterHTTPErrorFailover:
    """测试路由器对 HTTP 错误的 failover 行为"""

    @pytest.mark.asyncio
    async def test_401_retries_3_times_then_failover(self):
        """401 应重试 3 次后 failover 到下一个 provider"""
        config = RouterConfig(
            deepseek_api_key="test_key",
            glm_api_key="test_glm_key",
        )
        router = ModelRouter(config)

        http_error_401 = _make_http_error(401, "Invalid API key")

        success_response = _make_success_response("GLM fallback OK")
        success_response.provider = "glm"
        success_response.model = "glm-4-flash"

        deepseek_model = router._models.get("deepseek", {}).get("low")
        glm_model = router._models.get("glm", {}).get("low")

        if deepseek_model and glm_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = http_error_401

                with patch.object(
                    glm_model, "generate", new_callable=AsyncMock
                ) as mock_glm:
                    mock_glm.return_value = success_response

                    messages = [Message(role="user", content="test")]
                    response = await router.route_and_call(TaskType.EXPLORE, messages)

                    # 401 应重试 3 次
                    assert mock_ds.call_count == 3
                    # failover 到 GLM
                    assert mock_glm.call_count == 1
                    assert response.content == "GLM fallback OK"

    @pytest.mark.asyncio
    async def test_500_retries_with_backoff_then_failover(self):
        """500 应重试 3 次（递增等待）后 failover"""
        config = RouterConfig(
            deepseek_api_key="test_key",
            glm_api_key="test_glm_key",
        )
        router = ModelRouter(config)

        http_error_500 = _make_http_error(500, "Internal Server Error")

        success_response = _make_success_response("GLM recovery")

        deepseek_model = router._models.get("deepseek", {}).get("low")
        glm_model = router._models.get("glm", {}).get("low")

        if deepseek_model and glm_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = http_error_500

                with patch.object(
                    glm_model, "generate", new_callable=AsyncMock
                ) as mock_glm:
                    mock_glm.return_value = success_response

                    messages = [Message(role="user", content="test")]
                    response = await router.route_and_call(TaskType.EXPLORE, messages)

                    assert mock_ds.call_count == 3
                    assert mock_glm.call_count == 1
                    assert "GLM" in response.content

    @pytest.mark.asyncio
    async def test_all_providers_401_raises_no_model_available(self):
        """所有 provider 都返回 401 应抛 NoModelAvailableError"""
        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        http_error_401 = _make_http_error(401, "Invalid API key")

        deepseek_model = router._models.get("deepseek", {}).get("low")
        if deepseek_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = http_error_401

                messages = [Message(role="user", content="test")]
                with pytest.raises(NoModelAvailableError) as exc_info:
                    await router.route_and_call(TaskType.EXPLORE, messages)

                assert "不可用" in str(exc_info.value) or "401" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_all_providers_500_raises_no_model_available(self):
        """所有 provider 都返回 500 应抛 NoModelAvailableError"""
        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        http_error_500 = _make_http_error(500, "Internal Server Error")

        deepseek_model = router._models.get("deepseek", {}).get("low")
        if deepseek_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = http_error_500

                messages = [Message(role="user", content="test")]
                with pytest.raises(NoModelAvailableError):
                    await router.route_and_call(TaskType.EXPLORE, messages)

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        """500 第一次失败、第二次成功应正常返回"""
        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        http_error_500 = _make_http_error(500, "Temporary Error")
        success_response = _make_success_response("Recovered")

        deepseek_model = router._models.get("deepseek", {}).get("low")
        if deepseek_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = [http_error_500, success_response]

                messages = [Message(role="user", content="test")]
                response = await router.route_and_call(TaskType.EXPLORE, messages)

                assert response.content == "Recovered"
                assert mock_ds.call_count == 2


# ============================================================
# 429 限流专项（补充 test_router.py 中的场景）
# ============================================================


class TestRateLimitDetailed:
    """429 限流的详细测试"""

    @pytest.mark.asyncio
    async def test_429_no_retry_immediate_failover(self):
        """429 后不应重试当前 provider，直接切换"""
        config = RouterConfig(
            deepseek_api_key="test_key",
            glm_api_key="test_glm_key",
        )
        router = ModelRouter(config)

        http_error_429 = _make_http_error(429, "Rate limit exceeded")
        success_response = _make_success_response("GLM OK")

        deepseek_model = router._models.get("deepseek", {}).get("low")
        glm_model = router._models.get("glm", {}).get("low")

        if deepseek_model and glm_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = http_error_429

                with patch.object(
                    glm_model, "generate", new_callable=AsyncMock
                ) as mock_glm:
                    mock_glm.return_value = success_response

                    messages = [Message(role="user", content="test")]
                    response = await router.route_and_call(TaskType.EXPLORE, messages)

                    # 429: 只调用 1 次（不重试）
                    assert mock_ds.call_count == 1
                    # failover 到 GLM
                    assert mock_glm.call_count == 1
                    assert response.content == "GLM OK"

    @pytest.mark.asyncio
    async def test_429_then_500_then_success(self):
        """429 failover 后遇到 500，再 failover 成功"""
        config = RouterConfig(
            deepseek_api_key="test_key",
            glm_api_key="test_glm_key",
        )
        router = ModelRouter(config)

        http_error_429 = _make_http_error(429, "Rate limited")
        http_error_500 = _make_http_error(500, "Server Error")
        success_response = _make_success_response("GLM OK")

        deepseek_model = router._models.get("deepseek", {}).get("low")
        glm_model = router._models.get("glm", {}).get("low")

        if deepseek_model and glm_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = http_error_429

                with patch.object(
                    glm_model, "generate", new_callable=AsyncMock
                ) as mock_glm:
                    # GLM 第一次 500，第二次成功
                    mock_glm.side_effect = [http_error_500, success_response]

                    messages = [Message(role="user", content="test")]
                    response = await router.route_and_call(TaskType.EXPLORE, messages)

                    # DeepSeek 429 → 1 次
                    assert mock_ds.call_count == 1
                    # GLM 500 → 重试后成功
                    assert mock_glm.call_count == 2
                    assert response.content == "GLM OK"

    @pytest.mark.asyncio
    async def test_all_providers_429_raises_rate_limit_error(self):
        """所有 provider 都 429 应抛 RateLimitError"""
        config = RouterConfig(
            deepseek_api_key="test_key",
            glm_api_key="test_glm_key",
        )
        router = ModelRouter(config)

        http_error_429 = _make_http_error(429, "Rate limited")

        deepseek_model = router._models.get("deepseek", {}).get("low")
        glm_model = router._models.get("glm", {}).get("low")

        if deepseek_model and glm_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = http_error_429

                with patch.object(
                    glm_model, "generate", new_callable=AsyncMock
                ) as mock_glm:
                    mock_glm.side_effect = http_error_429

                    messages = [Message(role="user", content="test")]
                    with pytest.raises(RateLimitError) as exc_info:
                        await router.route_and_call(TaskType.EXPLORE, messages)

                    # 错误信息包含限流建议
                    err_msg = str(exc_info.value)
                    assert "限流" in err_msg
                    # 每个 provider 只调用 1 次（429 不重试）
                    assert mock_ds.call_count == 1
                    assert mock_glm.call_count == 1


# ============================================================
# 边界场景
# ============================================================


class TestEdgeCases:
    """边界场景测试"""

    @pytest.mark.asyncio
    async def test_network_timeout_retries_3_times(self):
        """网络超时（非 HTTP 错误）应重试 3 次"""
        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        deepseek_model = router._models.get("deepseek", {}).get("low")
        if deepseek_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = httpx.ConnectTimeout("Connection timed out")

                messages = [Message(role="user", content="test")]
                with pytest.raises(NoModelAvailableError):
                    await router.route_and_call(TaskType.EXPLORE, messages)

                # 网络错误也应重试 3 次
                assert mock_ds.call_count == 3

    @pytest.mark.asyncio
    async def test_429_vs_500_retry_difference(self):
        """429 只调 1 次，500 重试 3 次 — 行为必须不同"""
        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        # === 429 场景 ===
        http_error_429 = _make_http_error(429, "Rate limit")
        deepseek_model = router._models.get("deepseek", {}).get("low")
        if deepseek_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds_429:
                mock_ds_429.side_effect = http_error_429

                messages = [Message(role="user", content="test")]
                with pytest.raises(RateLimitError):
                    await router.route_and_call(TaskType.EXPLORE, messages)

                calls_429 = mock_ds_429.call_count

        # === 500 场景 ===
        http_error_500 = _make_http_error(500, "Server Error")
        deepseek_model = router._models.get("deepseek", {}).get("low")
        if deepseek_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds_500:
                mock_ds_500.side_effect = http_error_500

                messages = [Message(role="user", content="test")]
                with pytest.raises(NoModelAvailableError):
                    await router.route_and_call(TaskType.EXPLORE, messages)

                calls_500 = mock_ds_500.call_count

        # 429 调用 1 次，500 调用 3 次
        if deepseek_model:
            assert calls_429 == 1, f"429 should call 1 time, got {calls_429}"
            assert calls_500 == 3, f"500 should call 3 times, got {calls_500}"

    @pytest.mark.asyncio
    async def test_empty_messages_still_routes(self):
        """空消息列表仍能正确路由（不 crash）"""
        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        success_response = _make_success_response("Empty OK")
        deepseek_model = router._models.get("deepseek", {}).get("low")
        if deepseek_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.return_value = success_response

                response = await router.route_and_call(TaskType.SIMPLE_QA, [])
                assert response.content == "Empty OK"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
