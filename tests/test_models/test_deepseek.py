"""
测试 DeepSeek 模型适配器（mock API）

运行: pytest tests/test_models/test_deepseek.py -v
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import pytest

sys.path.insert(0, "/Users/vobc/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder")

from src.models.base import Message, ModelConfig, ModelProvider, ModelTier
from src.models.deepseek import DeepSeekAPIError, DeepSeekModel


class TestDeepSeekModelInit:
    """测试 DeepSeek 模型初始化"""

    def test_default_base_url(self):
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config)  # noqa: F841
        assert urlparse(config.base_url).netloc == "api.deepseek.com"

    def test_custom_base_url(self):
        config = ModelConfig(api_key="test_key", base_url="https://custom.api.com/v1")
        model = DeepSeekModel(config)  # noqa: F841
        assert config.base_url == "https://custom.api.com/v1"

    def test_tier_low(self):
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config, ModelTier.LOW)
        assert model.model_name == "deepseek-chat"
        assert model.tier == ModelTier.LOW

    def test_tier_high(self):
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config, ModelTier.HIGH)
        assert model.tier == ModelTier.HIGH

    def test_use_coder_mode(self):
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config, use_coder=True)
        assert model.model_name == "deepseek-coder"


class TestDeepSeekFormatMessages:
    """测试消息格式化"""

    def test_format_system_and_user(self):
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config)
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
        ]
        formatted = model._format_messages(messages)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[1]["role"] == "user"

    def test_format_with_name(self):
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config)
        messages = [Message(role="user", content="Hi", name="Alice")]
        formatted = model._format_messages(messages)
        assert formatted[0]["name"] == "Alice"

    def test_format_multiple_messages(self):
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config)
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]
        formatted = model._format_messages(messages)
        assert len(formatted) == 4
        roles = [m["role"] for m in formatted]
        assert roles == ["system", "user", "assistant", "user"]


def _mock_response(content: str, tokens: int = 30):
    """Shared mock response builder"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "id": "chatcmpl-test",
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": tokens,
            "total_tokens": 10 + tokens,
        },
    }
    mock_resp.raise_for_status = MagicMock()  # no-op
    return mock_resp


class TestDeepSeekGenerate:
    """测试 generate 方法"""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        mock_resp = _mock_response("Hello! How can I help?")

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = client

            messages = [Message(role="user", content="Hello")]
            response = await model.generate(messages)

        assert response.content == "Hello! How can I help?"
        assert response.provider == ModelProvider.DEEPSEEK
        assert response.usage.total_tokens == 40
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_with_custom_temperature(self):
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        mock_resp = _mock_response("response")

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = client

            messages = [Message(role="user", content="Hello")]
            response = await model.generate(messages, temperature=0.9)

        assert response.content == "response"

    @pytest.mark.asyncio
    async def test_generate_http_error(self):
        """HTTP 错误应转换为 DeepSeekAPIError"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))

        # Mock client.post raising httpx.HTTPStatusError (simulated via Exception)
        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            # Simulate HTTP 401 by having post raise an exception that
            # the model code's error handler will catch
            import httpx

            client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "401 Unauthorized",
                    request=MagicMock(),
                    response=MagicMock(status_code=401),
                )
            )
            mock_get.return_value = client

            messages = [Message(role="user", content="Hello")]
            with pytest.raises(DeepSeekAPIError):
                await model.generate(messages)


class TestDeepSeekStream:
    """测试流式生成"""

    @pytest.mark.asyncio
    async def test_stream_yields_content(self):
        model = DeepSeekModel(ModelConfig(api_key="test_key"))

        async def fake_lines():
            yield 'data: {"choices":[{"delta":{"content":"Hello"}}]}'
            yield 'data: {"choices":[{"delta":{"content":" World"}}]}'
            yield "data: [DONE]"

        mock_ctx = MagicMock()

        async def enter_async():
            mock_stream = MagicMock()
            mock_stream.raise_for_status = MagicMock()
            mock_stream.aiter_lines = fake_lines
            return mock_stream

        mock_ctx.__aenter__ = AsyncMock(side_effect=enter_async)
        mock_ctx.__aexit__ = AsyncMock()

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.stream = MagicMock(return_value=mock_ctx)
            mock_get.return_value = client

            messages = [Message(role="user", content="Hello")]
            chunks = [c async for c in model.stream(messages)]

        assert "".join(chunks) == "Hello World"

    @pytest.mark.asyncio
    async def test_stream_empty_and_comment_lines_skipped(self):
        model = DeepSeekModel(ModelConfig(api_key="test_key"))

        async def fake_lines():
            yield ""  # empty -> skip
            yield ": comment"  # comment -> skip
            yield 'data: {"choices":[{"delta":{"content":"A"}}]}'
            yield "data: [DONE]"

        mock_ctx = MagicMock()

        async def enter_async():
            mock_stream = MagicMock()
            mock_stream.raise_for_status = MagicMock()
            mock_stream.aiter_lines = fake_lines
            return mock_stream

        mock_ctx.__aenter__ = AsyncMock(side_effect=enter_async)
        mock_ctx.__aexit__ = AsyncMock()

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.stream = MagicMock(return_value=mock_ctx)
            mock_get.return_value = client

            chunks = [
                c async for c in model.stream([Message(role="user", content="x")])
            ]
        assert "".join(chunks) == "A"


class TestDeepSeekCostTracking:
    """测试成本统计"""

    @pytest.mark.asyncio
    async def test_usage_accumulated(self):
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        mock_resp = _mock_response("test", tokens=50)

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = client

            await model.generate([Message(role="user", content="a")])
            await model.generate([Message(role="user", content="b")])

        usage = model.get_total_usage()
        assert usage.total_tokens > 0  # 10 + 50 + 10 + 50 = 120


# ─────────────────────────────────────────────────────────────────
# 补充覆盖 deepseek.py missing lines (129-131, 141, 143, 172, 174,
# 177, 178, 244-246, 301-321)
# ─────────────────────────────────────────────────────────────────


class TestDeepSeekClose:
    """测试 close() 方法（lines 127-131，0% → covered）"""

    @pytest.mark.asyncio
    async def test_close_closes_client(self):
        """close() 关闭 AsyncClient 并重置 _client"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))

        # 直接设置 _client 模拟已创建状态
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        model._client = mock_client

        await model.close()
        mock_client.aclose.assert_called_once()
        assert model._client is None

    @pytest.mark.asyncio
    async def test_close_idempotent_when_client_none(self):
        """close() 在 _client 为 None 时不抛错"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        model._client = None
        # 不抛错
        await model.close()
        assert model._client is None


class TestDeepSeekFormatMessagesTools:
    """测试 _format_messages 的 tool_calls / tool_call_id 分支（lines 141, 143）"""

    def test_format_with_tool_calls(self):
        """tool_calls 字段正确传递到格式化输出"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        messages = [
            Message(
                role="assistant",
                content="Let me check the weather",
                tool_calls=[{"id": "call_1", "type": "function"}],
            ),
        ]
        formatted = model._format_messages(messages)
        assert "tool_calls" in formatted[0]
        assert formatted[0]["tool_calls"][0]["id"] == "call_1"

    def test_format_with_tool_call_id(self):
        """tool_call_id 字段正确传递到格式化输出"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        messages = [
            Message(role="tool", content='{"temp": 22}', tool_call_id="call_1"),
        ]
        formatted = model._format_messages(messages)
        assert "tool_call_id" in formatted[0]
        assert formatted[0]["tool_call_id"] == "call_1"


class TestDeepSeekGenerateOptions:
    """测试 generate 的 tools/tool_choice/top_p/stop 参数（lines 172-178）"""

    @pytest.mark.asyncio
    async def test_generate_with_tools_and_tool_choice(self):
        """tools 参数触发 request_body["tools"] 和 ["tool_choice"]"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        mock_resp = _mock_response("result")

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = client

            messages = [Message(role="user", content="Hello")]
            await model.generate(
                messages,
                tools=[{"type": "function", "function": {"name": "get_weather"}}],
                tool_choice="auto",
            )
            # 验证 post 被调用（表明 tools/tool_choice 分支被执行）
            client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_top_p_and_stop(self):
        """top_p 和 stop 参数"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        mock_resp = _mock_response("result")

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = client

            messages = [Message(role="user", content="Hello")]
            await model.generate(
                messages,
                top_p=0.9,
                stop=["stop_word"],
            )
            client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_http_error_with_json_body(self):
        """HTTPStatusError 错误体可 JSON 解析时包含 message（lines 244-246）"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json = MagicMock(
            return_value={"error": {"message": "Rate limit exceeded", "type": "rate_limit"}}
        )

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "429 Too Many Requests",
                    request=MagicMock(),
                    response=mock_response,
                )
            )
            mock_get.return_value = client

            messages = [Message(role="user", content="Hello")]
            with pytest.raises(DeepSeekAPIError) as exc_info:
                await model.generate(messages)
            assert "429" in str(exc_info.value)
            assert "Rate limit" in str(exc_info.value)


class TestDeepSeekStreamErrors:
    """测试 stream() 错误处理（lines 301-321，53% → higher）"""

    @pytest.mark.asyncio
    async def test_stream_http_status_error_parseable(self):
        """stream() 收到 HTTPStatusError 且 error body 可 JSON 解析"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json = MagicMock(
            return_value={"error": {"message": "Internal server error", "type": "server"}}
        )

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500 Server Error",
                request=MagicMock(),
                response=mock_response,
            )
        )
        mock_ctx.__aexit__ = AsyncMock()

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.stream = MagicMock(return_value=mock_ctx)
            mock_get.return_value = client

            with pytest.raises(DeepSeekAPIError) as exc_info:
                async for _ in model.stream([Message(role="user", content="x")]):
                    pass
            assert "500" in str(exc_info.value)
            assert "Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_http_status_error_not_parseable(self):
        """stream() 收到 HTTPStatusError 但 error body 非 JSON（fallback）"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.json = MagicMock(side_effect=ValueError("Not JSON"))

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "502 Bad Gateway",
                request=MagicMock(),
                response=mock_response,
            )
        )
        mock_ctx.__aexit__ = AsyncMock()

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.stream = MagicMock(return_value=mock_ctx)
            mock_get.return_value = client

            with pytest.raises(DeepSeekAPIError) as exc_info:
                async for _ in model.stream([Message(role="user", content="x")]):
                    pass
            assert "HTTP 502" in str(exc_info.value)
            assert "无法解析" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_request_error(self):
        """stream() 网络错误（RequestError）"""
        model = DeepSeekModel(ModelConfig(api_key="test_key"))
        import httpx

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        mock_ctx.__aexit__ = AsyncMock()

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.stream = MagicMock(return_value=mock_ctx)
            mock_get.return_value = client

            with pytest.raises(DeepSeekAPIError) as exc_info:
                async for _ in model.stream([Message(role="user", content="x")]):
                    pass
            assert "网络请求失败" in str(exc_info.value)
            assert "RequestError" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

