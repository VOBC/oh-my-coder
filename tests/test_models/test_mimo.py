"""
Tests for Xiaomi MiMo model adapter.

Covers:
- Model initialization and configuration (all tiers, costs, base_url)
- Client creation and management (create, reuse, recreate on close)
- Message formatting (basic, name, tool_calls, tool_call_id)
- generate() method (success, HTTP errors, request errors, tools, optional params,
  empty content, missing usage, latency, usage tracking, reset)
- stream() method (success, comments, empty lines, JSON errors, no-content deltas,
  HTTP errors, request errors, tools)
- close() method
- MIMO_MODELS configuration
- MimoAPIError
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, "/Users/vobc/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder")

from src.models.base import (
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
)
from src.models.mimo import MIMO_MODELS, MimoAPIError, MimoModel

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def config() -> ModelConfig:
    """Create a test configuration."""
    return ModelConfig(
        api_key="test-mimo-api-key",
        base_url=None,
        timeout=30.0,
        max_tokens=4096,
        temperature=0.7,
    )


@pytest.fixture
def model(config: ModelConfig) -> MimoModel:
    """Create a MimoModel instance."""
    return MimoModel(config, tier=ModelTier.MEDIUM)


# =============================================================================
# Initialization Tests
# =============================================================================

class TestMimoModelInit:
    """Test suite for MiMo model initialization."""

    def test_default_base_url(self):
        """Test that default base URL is set when not provided."""
        config = ModelConfig(api_key="test_key")
        MimoModel(config)  # noqa: F841
        assert config.base_url == "https://api.xiaomimimo.com/v1"

    def test_custom_base_url(self):
        """Test that custom base_url is preserved."""
        config = ModelConfig(
            api_key="test_key", base_url="https://custom.api.com/v1"
        )
        MimoModel(config)  # noqa: F841
        assert config.base_url == "https://custom.api.com/v1"

    def test_tier_low(self):
        """Test LOW tier uses mimo-v2-flash."""
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config, ModelTier.LOW)
        assert model.model_name == "mimo-v2-flash"
        assert model.tier == ModelTier.LOW

    def test_tier_medium(self):
        """Test MEDIUM tier uses mimo-v2-flash."""
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config, ModelTier.MEDIUM)
        assert model.model_name == "mimo-v2-flash"
        assert model.tier == ModelTier.MEDIUM

    def test_tier_high(self):
        """Test HIGH tier uses mimo-v2-pro."""
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config, ModelTier.HIGH)
        assert model.model_name == "mimo-v2-pro"
        assert model.tier == ModelTier.HIGH

    def test_provider(self):
        """Test provider property returns MIMO."""
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config)
        assert model.provider == ModelProvider.MIMO

    def test_cost_per_tier_low(self):
        """Test cost is set correctly for LOW tier."""
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config, ModelTier.LOW)
        assert model.config.cost_per_1k_prompt == 0.0
        assert model.config.cost_per_1k_completion == 0.0

    def test_cost_per_tier_medium(self):
        """Test cost is set correctly for MEDIUM tier."""
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config, ModelTier.MEDIUM)
        assert model.config.cost_per_1k_prompt == 0.0
        assert model.config.cost_per_1k_completion == 0.0

    def test_cost_per_tier_high(self):
        """Test cost is set correctly for HIGH tier."""
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config, ModelTier.HIGH)
        assert model.config.cost_per_1k_prompt == 1.0
        assert model.config.cost_per_1k_completion == 3.0


# =============================================================================
# Message Formatting Tests
# =============================================================================

class TestMimoFormatMessages:
    """Test suite for message formatting."""

    def test_format_system_and_user(self):
        """Test basic message formatting."""
        model = MimoModel(ModelConfig(api_key="test_key"))
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
        ]
        formatted = model._format_messages(messages)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[1]["role"] == "user"
        assert formatted[0]["content"] == "You are helpful"

    def test_format_with_name(self):
        """Test message formatting with name field."""
        model = MimoModel(ModelConfig(api_key="test_key"))
        messages = [Message(role="user", content="Hi", name="Alice")]
        formatted = model._format_messages(messages)
        assert "name" in formatted[0]
        assert formatted[0]["name"] == "Alice"

    def test_format_multiple_messages(self):
        """Test formatting multiple messages of different roles."""
        model = MimoModel(ModelConfig(api_key="test_key"))
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]
        formatted = model._format_messages(messages)
        assert len(formatted) == 4
        assert formatted[2]["role"] == "assistant"

    def test_format_with_tool_calls(self):
        """Test message formatting with tool_calls."""
        model = MimoModel(ModelConfig(api_key="test_key"))
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "get_weather", "arguments": "{}"},
            }
        ]
        messages = [Message(role="assistant", content="", tool_calls=tool_calls)]
        formatted = model._format_messages(messages)
        assert "tool_calls" in formatted[0]
        assert formatted[0]["tool_calls"] == tool_calls

    def test_format_with_tool_call_id(self):
        """Test message formatting with tool_call_id."""
        model = MimoModel(ModelConfig(api_key="test_key"))
        messages = [Message(role="tool", content="Result: 25°C", tool_call_id="call_123")]
        formatted = model._format_messages(messages)
        assert "tool_call_id" in formatted[0]
        assert formatted[0]["tool_call_id"] == "call_123"


# =============================================================================
# Client Management Tests
# =============================================================================

class TestMimoClientManagement:
    """Test suite for HTTP client management."""

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self):
        """Test that _get_client creates a new client when none exists."""
        model = MimoModel(
            ModelConfig(api_key="test-key", timeout=30.0),
            tier=ModelTier.MEDIUM,
        )
        client = await model._get_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert str(client.base_url) == "https://api.xiaomimimo.com/v1/"
        assert client.headers["Authorization"] == "Bearer test-key"
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing_client(self):
        """Test that _get_client reuses existing client."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)
        client1 = await model._get_client()
        client2 = await model._get_client()
        assert client1 is client2
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_recreates_closed_client(self):
        """Test that _get_client creates new client when existing one is closed."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)
        client1 = await model._get_client()
        await model.close()
        client2 = await model._get_client()
        assert client1 is not client2
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_uses_env_var_overrides_config(self):
        """Test that MIMOAPIKEY env var overrides config.api_key."""
        model = MimoModel(
            ModelConfig(api_key="config-key"), tier=ModelTier.MEDIUM
        )
        with patch.dict(os.environ, {"MIMOAPIKEY": "env-secret-key"}, clear=False):
            client = await model._get_client()
            assert client.headers["Authorization"] == "Bearer env-secret-key"
        await model.close()

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method properly closes client."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)
        client = await model._get_client()
        assert not client.is_closed
        await model.close()
        assert model._client is None

    @pytest.mark.asyncio
    async def test_close_when_no_client(self):
        """Test close is safe when no client exists."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)
        # Should not raise
        await model.close()


# =============================================================================
# generate() Method Tests
# =============================================================================

class TestMimoGenerate:
    """Test suite for generate() method."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generate call."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_response_data = {
            "id": "mimo-chat-123",
            "choices": [
                {
                    "message": {"content": "Hello, I am MiMo!", "role": "assistant"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hi")]
            response = await model.generate(messages)

        assert isinstance(response, ModelResponse)
        assert response.content == "Hello, I am MiMo!"
        assert response.model == "mimo-v2-flash"
        assert response.provider == ModelProvider.MIMO
        assert response.tier == ModelTier.MEDIUM
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30
        assert response.finish_reason == "stop"
        assert response.metadata["response_id"] == "mimo-chat-123"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/chat/completions"

    @pytest.mark.asyncio
    async def test_generate_with_tools(self):
        """Test generate with tools parameter."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_response_data = {
            "id": "mimo-chat-456",
            "choices": [
                {
                    "message": {
                        "content": "",
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "Beijing"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 30,
                "total_tokens": 80,
            },
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                },
            }
        ]

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Weather?")]
            response = await model.generate(messages, tools=tools)

        assert response.metadata["tool_calls"] is not None
        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert "tools" in request_body

    @pytest.mark.asyncio
    async def test_generate_with_optional_params(self):
        """Test generate with optional parameters (top_p, stop)."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_response_data = {
            "id": "mimo-chat-789",
            "choices": [
                {
                    "message": {"content": "Response", "role": "assistant"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            await model.generate(messages, top_p=0.9, stop=["\n", "END"])

        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert request_body["top_p"] == 0.9
        assert request_body["stop"] == ["\n", "END"]

    @pytest.mark.asyncio
    async def test_generate_http_status_error(self):
        """Test generate handles HTTP status errors."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limited"}}

        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Too Many Requests",
                request=MagicMock(),
                response=mock_response,
            )
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hi")]
            with pytest.raises(MimoAPIError) as exc_info:
                await model.generate(messages)

        assert "MiMo API 错误" in str(exc_info.value)
        assert "429" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_http_status_error_json_fallback(self):
        """Test generate HTTP error when response body is not valid JSON."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("not json")

        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=mock_response,
            )
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hi")]
            with pytest.raises(MimoAPIError) as exc_info:
                await model.generate(messages)

        assert "MiMo API 错误" in str(exc_info.value)
        assert "500" in str(exc_info.value)
        assert "HTTP 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_request_error(self):
        """Test generate handles request errors (network issues)."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection error", request=MagicMock())
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hi")]
            with pytest.raises(MimoAPIError) as exc_info:
                await model.generate(messages)

        assert "网络请求失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_empty_content(self):
        """Test generate handles empty content in response."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_response_data = {
            "id": "mimo-empty",
            "choices": [
                {
                    "message": {"content": "", "role": "assistant"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 0, "total_tokens": 5},
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            response = await model.generate(messages)

        assert response.content == ""

    @pytest.mark.asyncio
    async def test_generate_missing_usage(self):
        """Test generate handles missing usage field in response."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_response_data = {
            "id": "mimo-no-usage",
            "choices": [
                {
                    "message": {"content": "Response without usage", "role": "assistant"},
                    "finish_reason": "stop",
                }
            ],
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            response = await model.generate(messages)

        assert response.usage.prompt_tokens == 0
        assert response.usage.completion_tokens == 0
        assert response.usage.total_tokens == 0

    @pytest.mark.asyncio
    async def test_generate_latency_recorded(self):
        """Test that latency is recorded in response."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_response_data = {
            "id": "mimo-latency",
            "choices": [
                {
                    "message": {"content": "Latency test", "role": "assistant"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            response = await model.generate(messages)

        assert response.latency_ms > 0

    @pytest.mark.asyncio
    async def test_generate_updates_usage_stats(self):
        """Test that generate updates model usage statistics."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_response_data = {
            "id": "mimo-usage",
            "choices": [
                {
                    "message": {"content": "Test response", "role": "assistant"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        initial_usage = model.get_total_usage()
        assert initial_usage.total_tokens == 0

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            await model.generate(messages)

        updated_usage = model.get_total_usage()
        assert updated_usage.prompt_tokens == 100
        assert updated_usage.completion_tokens == 50
        assert updated_usage.total_tokens == 150

    @pytest.mark.asyncio
    async def test_generate_cumulative_usage(self):
        """Test that generate accumulates usage across multiple calls."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": f"mimo-call-{call_count}",
                "choices": [
                    {
                        "message": {"content": f"Response {call_count}", "role": "assistant"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10 * call_count,
                    "completion_tokens": 5 * call_count,
                    "total_tokens": 15 * call_count,
                },
            }
            mock_response.raise_for_status = MagicMock()
            return mock_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=side_effect)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            await model.generate(messages)
            await model.generate(messages)

        usage = model.get_total_usage()
        # First call: 10 + 5 = 15, Second call: 20 + 10 = 30, total = 45
        assert usage.prompt_tokens == 30
        assert usage.completion_tokens == 15
        assert usage.total_tokens == 45

    @pytest.mark.asyncio
    async def test_reset_usage(self):
        """Test reset_usage clears accumulated usage."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_response_data = {
            "id": "mimo-reset",
            "choices": [
                {
                    "message": {"content": "Test", "role": "assistant"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            await model.generate(messages)

        assert model.get_total_usage().total_tokens == 20
        model.reset_usage()
        assert model.get_total_usage().total_tokens == 0


# =============================================================================
# stream() Method Tests
# =============================================================================

class TestMimoStream:
    """Test suite for stream() method."""

    @pytest.mark.asyncio
    async def test_stream_success(self):
        """Test successful streaming response."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        async def fake_lines():
            yield 'data: {"choices":[{"delta":{"content":"Hello"}}]}'
            yield 'data: {"choices":[{"delta":{"content":" MiMo"}}]}'
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

            assert "".join(chunks) == "Hello MiMo"

    @pytest.mark.asyncio
    async def test_stream_with_comments_and_empty_lines(self):
        """Test streaming skips comments and empty lines."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        async def fake_lines():
            yield ""  # empty line
            yield ": heartbeat comment"  # comment line
            yield 'data: {"choices":[{"delta":{"content":"Hi"}}]}'
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

            messages = [Message(role="user", content="Hi")]
            chunks = [c async for c in model.stream(messages)]

            assert chunks == ["Hi"]

    @pytest.mark.asyncio
    async def test_stream_json_decode_error(self):
        """Test streaming handles malformed JSON lines gracefully."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        async def fake_lines():
            yield 'data: {"choices":[{"delta":{"content":"OK"}}]}'
            yield "data: {invalid json here"
            yield 'data: {"choices":[{"delta":{"content":"!"}}]}'
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

            messages = [Message(role="user", content="Test")]
            chunks = [c async for c in model.stream(messages)]

            assert chunks == ["OK", "!"]

    @pytest.mark.asyncio
    async def test_stream_no_content_delta(self):
        """Test streaming skips deltas without content."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        async def fake_lines():
            yield 'data: {"choices":[{"delta":{}}]}'
            yield 'data: {"choices":[{"delta":{"content":"Has content"}}]}'
            yield 'data: {"choices":[{"delta":{}}]}'
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

            messages = [Message(role="user", content="Test")]
            chunks = [c async for c in model.stream(messages)]

            assert chunks == ["Has content"]

    @pytest.mark.asyncio
    async def test_stream_http_status_error(self):
        """Test stream handles HTTP status errors via raise_for_status."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        # Patch raise_for_status to raise HTTPStatusError directly
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Server error"}}

        def raise_for_status_raises():
            raise httpx.HTTPStatusError(
                "Internal Server Error",
                request=MagicMock(),
                response=mock_response,
            )

        mock_response.raise_for_status = raise_for_status_raises

        async def fake_lines():
            yield 'data: {"choices":[{"delta":{"content":"Hi"}}]}'
            yield "data: [DONE]"

        mock_response.aiter_lines = fake_lines

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.stream = MagicMock(return_value=mock_ctx)
            mock_get.return_value = client

            messages = [Message(role="user", content="Test")]
            with pytest.raises(MimoAPIError) as exc_info:
                async for _ in model.stream(messages):
                    pass

        assert "MiMo API 错误" in str(exc_info.value)
        assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_http_status_error_json_fallback(self):
        """Test stream HTTP error when response body is not valid JSON."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.json.side_effect = ValueError("not json")

        def raise_for_status_raises():
            raise httpx.HTTPStatusError(
                "Bad Gateway",
                request=MagicMock(),
                response=mock_response,
            )

        mock_response.raise_for_status = raise_for_status_raises

        async def fake_lines():
            yield 'data: {"choices":[{"delta":{"content":"Hi"}}]}'
            yield "data: [DONE]"

        mock_response.aiter_lines = fake_lines

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.stream = MagicMock(return_value=mock_ctx)
            mock_get.return_value = client

            messages = [Message(role="user", content="Test")]
            with pytest.raises(MimoAPIError) as exc_info:
                async for _ in model.stream(messages):
                    pass

        assert "MiMo API 错误" in str(exc_info.value)
        assert "502" in str(exc_info.value)
        assert "HTTP 502" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_request_error(self):
        """Test stream handles request errors."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.stream = MagicMock(
            side_effect=httpx.RequestError("Connection refused", request=MagicMock())
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            with pytest.raises(MimoAPIError) as exc_info:
                async for _ in model.stream(messages):
                    pass

        assert "网络请求失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_with_tools(self):
        """Test streaming with tools parameter."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        async def fake_lines():
            yield 'data: {"choices":[{"delta":{"content":"Using tool"}}]}'
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

            messages = [Message(role="user", content="Do it")]
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "do_something",
                        "description": "Does something",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ]
            chunks = [c async for c in model.stream(messages, tools=tools)]

            assert "".join(chunks) == "Using tool"
            call_args = client.stream.call_args
            assert "tools" in call_args[1]["json"]

    @pytest.mark.asyncio
    async def test_stream_with_optional_params(self):
        """Test streaming with optional parameters (top_p, stop)."""
        model = MimoModel(ModelConfig(api_key="test-key"), tier=ModelTier.MEDIUM)

        async def fake_lines():
            yield 'data: {"choices":[{"delta":{"content":"OK"}}]}'
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

            messages = [Message(role="user", content="Test")]
            # Consume the async generator
            async for _ in model.stream(messages, top_p=0.8, stop=["\n"]):
                pass

            call_args = client.stream.call_args
            request_body = call_args[1]["json"]
            assert request_body["top_p"] == 0.8
            assert request_body["stop"] == ["\n"]


# =============================================================================
# Configuration Tests
# =============================================================================

class TestMimoModelsConfig:
    """Test suite for MIMO_MODELS configuration."""

    def test_mimo_models_has_all_tiers(self):
        """Test that MIMO_MODELS has entries for all three tiers."""
        assert ModelTier.LOW in MIMO_MODELS
        assert ModelTier.MEDIUM in MIMO_MODELS
        assert ModelTier.HIGH in MIMO_MODELS

    def test_mimo_models_structure(self):
        """Test that each tier has required keys."""
        for tier in [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH]:
            info = MIMO_MODELS[tier]
            assert "name" in info
            assert "context_length" in info
            assert "cost_per_1k_prompt" in info
            assert "cost_per_1k_completion" in info

    def test_mimo_models_tier_low_and_medium_use_flash(self):
        """Test that LOW and MEDIUM tiers use mimo-v2-flash."""
        assert MIMO_MODELS[ModelTier.LOW]["name"] == "mimo-v2-flash"
        assert MIMO_MODELS[ModelTier.MEDIUM]["name"] == "mimo-v2-flash"
        assert MIMO_MODELS[ModelTier.LOW]["context_length"] == 256 * 1024
        assert MIMO_MODELS[ModelTier.MEDIUM]["context_length"] == 256 * 1024

    def test_mimo_models_tier_high_uses_pro(self):
        """Test that HIGH tier uses mimo-v2-pro."""
        assert MIMO_MODELS[ModelTier.HIGH]["name"] == "mimo-v2-pro"
        assert MIMO_MODELS[ModelTier.HIGH]["context_length"] == 1024 * 1024
        assert MIMO_MODELS[ModelTier.HIGH]["cost_per_1k_prompt"] == 1.0
        assert MIMO_MODELS[ModelTier.HIGH]["cost_per_1k_completion"] == 3.0

    def test_mimo_models_free_tiers(self):
        """Test that LOW and MEDIUM tiers are free."""
        for tier in [ModelTier.LOW, ModelTier.MEDIUM]:
            assert MIMO_MODELS[tier]["cost_per_1k_prompt"] == 0.0
            assert MIMO_MODELS[tier]["cost_per_1k_completion"] == 0.0


# =============================================================================
# MimoAPIError Tests
# =============================================================================

class TestMimoAPIError:
    """Test suite for MimoAPIError exception."""

    def test_error_message(self):
        """Test MimoAPIError can be instantiated with a message."""
        error = MimoAPIError("Test error message")
        assert str(error) == "Test error message"

    def test_error_is_exception(self):
        """Test MimoAPIError inherits from Exception."""
        error = MimoAPIError("test")
        assert isinstance(error, Exception)

    def test_error_with_format_string(self):
        """Test MimoAPIError formats correctly."""
        error = MimoAPIError("MiMo API 错误 (401): Invalid API key")
        assert "401" in str(error)
        assert "Invalid API key" in str(error)
