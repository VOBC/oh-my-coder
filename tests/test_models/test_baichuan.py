"""
Tests for Baichuan (百川智能) model adapter.

Covers:
- Model initialization and configuration
- Client creation and management
- Message formatting
- generate() method (success, HTTP errors, request errors, tools, optional params)
- stream() method (success, errors, edge cases)
- close() method
- Usage tracking
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.models.base import (
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
)
from src.models.baichuan import BAICHUAN_MODELS, BaichuanAPIError, BaichuanModel


class TestBaichuanModel:
    """Test suite for BaichuanModel."""

    @pytest.fixture
    def config(self) -> ModelConfig:
        """Create a test configuration."""
        return ModelConfig(
            api_key="test-baichuan-api-key",
            base_url=None,
            timeout=30.0,
            max_tokens=4096,
            temperature=0.7,
        )

    @pytest.fixture
    def model(self, config: ModelConfig) -> BaichuanModel:
        """Create a BaichuanModel instance."""
        return BaichuanModel(config, tier=ModelTier.MEDIUM)

    # ===== Initialization Tests =====

    def test_init_sets_default_base_url(self, config: ModelConfig):
        """Test that default base URL is set when not provided."""
        BaichuanModel(config, tier=ModelTier.MEDIUM)
        assert config.base_url == "https://api.baichuan-ai.com/v1"

    def test_init_sets_cost_for_tier(self, config: ModelConfig):
        """Test that cost is set based on tier."""
        for tier in [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH]:
            cfg = ModelConfig(api_key="test")
            BaichuanModel(cfg, tier=tier)
            assert cfg.cost_per_1k_prompt == 0.0
            assert cfg.cost_per_1k_completion == 0.0

    def test_model_name_property(self, model: BaichuanModel):
        """Test model_name property returns correct model for tier."""
        assert model.model_name == "Baichuan4"

        config = ModelConfig(api_key="test")
        low_model = BaichuanModel(config, tier=ModelTier.LOW)
        assert low_model.model_name == "Baichuan4"

        high_model = BaichuanModel(config, tier=ModelTier.HIGH)
        assert high_model.model_name == "Baichuan4"

    def test_provider_property(self, model: BaichuanModel):
        """Test provider property returns BAICHUAN."""
        assert model.provider == ModelProvider.BAICHUAN

    def test_init_custom_base_url(self):
        """Test that custom base_url is preserved."""
        config = ModelConfig(
            api_key="test-key",
            base_url="https://custom.baichuan-ai.com/v1",
        )
        model = BaichuanModel(config, tier=ModelTier.MEDIUM)
        assert model.config.base_url == "https://custom.baichuan-ai.com/v1"

    # ===== Message Formatting Tests =====

    def test_format_messages_basic(self, model: BaichuanModel):
        """Test basic message formatting."""
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!"),
        ]
        formatted = model._format_messages(messages)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are a helpful assistant."
        assert formatted[1]["role"] == "user"
        assert formatted[1]["content"] == "Hello!"

    def test_format_messages_with_name(self, model: BaichuanModel):
        """Test message formatting with name field."""
        messages = [Message(role="user", content="Hello", name="Alice")]
        formatted = model._format_messages(messages)
        assert "name" in formatted[0]
        assert formatted[0]["name"] == "Alice"

    def test_format_messages_with_tool_calls(self, model: BaichuanModel):
        """Test message formatting with tool calls."""
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

    def test_format_messages_with_tool_call_id(self, model: BaichuanModel):
        """Test message formatting with tool call ID."""
        messages = [
            Message(role="tool", content="Result: 25°C", tool_call_id="call_123"),
        ]
        formatted = model._format_messages(messages)
        assert "tool_call_id" in formatted[0]
        assert formatted[0]["tool_call_id"] == "call_123"

    # ===== Client Management Tests =====

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self, model: BaichuanModel):
        """Test that _get_client creates a new client when none exists."""
        client = await model._get_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert str(client.base_url) == "https://api.baichuan-ai.com/v1/"
        assert client.headers["Authorization"] == "Bearer test-baichuan-api-key"
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing_client(self, model: BaichuanModel):
        """Test that _get_client reuses existing client."""
        client1 = await model._get_client()
        client2 = await model._get_client()
        assert client1 is client2
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_recreates_closed_client(self, model: BaichuanModel):
        """Test that _get_client creates new client when existing one is closed."""
        client1 = await model._get_client()
        await model.close()
        client2 = await model._get_client()
        assert client1 is not client2
        await model.close()

    @pytest.mark.asyncio
    async def test_close(self, model: BaichuanModel):
        """Test close method properly closes client."""
        client = await model._get_client()
        assert not client.is_closed
        await model.close()
        assert model._client is None

    # ===== generate() Method Tests =====

    @pytest.mark.asyncio
    async def test_generate_success(self, model: BaichuanModel):
        """Test successful generate call."""
        mock_response_data = {
            "id": "chatcmpl-baichuan-123",
            "choices": [
                {
                    "message": {
                        "content": "Hello! How can I help you?",
                        "role": "assistant",
                    },
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
            messages = [Message(role="user", content="Hello!")]
            response = await model.generate(messages)

        assert isinstance(response, ModelResponse)
        assert response.content == "Hello! How can I help you?"
        assert response.model == "Baichuan4"
        assert response.provider == ModelProvider.BAICHUAN
        assert response.tier == ModelTier.MEDIUM
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30
        assert response.finish_reason == "stop"
        assert response.metadata["response_id"] == "chatcmpl-baichuan-123"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/chat/completions"
        assert "json" in call_args[1]

    @pytest.mark.asyncio
    async def test_generate_with_tools(self, model: BaichuanModel):
        """Test generate with tools parameter."""
        mock_response_data = {
            "id": "chatcmpl-456",
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
                    "description": "Get weather information",
                    "parameters": {"type": "object", "properties": {"location": {"type": "string"}}},
                },
            }
        ]

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="What's the weather?")]
            await model.generate(messages, tools=tools, tool_choice="auto")

        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert "tools" in request_body
        assert request_body["tools"] == tools
        assert request_body["tool_choice"] == "auto"

    @pytest.mark.asyncio
    async def test_generate_with_optional_params(self, model: BaichuanModel):
        """Test generate with optional parameters (top_p, stop)."""
        mock_response_data = {
            "id": "chatcmpl-789",
            "choices": [
                {
                    "message": {"content": "Response with params", "role": "assistant"},
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
    async def test_generate_http_status_error(self, model: BaichuanModel):
        """Test generate handles HTTP status errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Too Many Requests", request=MagicMock(), response=mock_response
            )
        )
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello!")]
            with pytest.raises(BaichuanAPIError) as exc_info:
                await model.generate(messages)

        assert "百川智能 API 错误" in str(exc_info.value)
        assert "429" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_request_error(self, model: BaichuanModel):
        """Test generate handles request errors (network issues)."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Network error", request=MagicMock())
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello!")]
            with pytest.raises(BaichuanAPIError) as exc_info:
                await model.generate(messages)

        assert "网络请求失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_empty_content(self, model: BaichuanModel):
        """Test generate handles empty content in response."""
        mock_response_data = {
            "id": "chatcmpl-empty",
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
    async def test_generate_missing_usage(self, model: BaichuanModel):
        """Test generate handles missing usage field in response."""
        mock_response_data = {
            "id": "chatcmpl-no-usage",
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
    async def test_generate_latency_recorded(self, model: BaichuanModel):
        """Test that latency is recorded in response."""
        mock_response_data = {
            "id": "chatcmpl-latency",
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

    # ===== stream() Method Tests =====

    @pytest.mark.asyncio
    async def test_stream_success(self, model: BaichuanModel):
        """Test successful streaming response."""
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " world"}}]}',
            "data: [DONE]",
        ]

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_cm)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Say hello")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_with_comments_and_empty_lines(self, model: BaichuanModel):
        """Test streaming handles comments and empty lines."""
        sse_lines = [
            "",
            ": heartbeat",
            'data: {"choices": [{"delta": {"content": "Hi"}}]}',
            "data: [DONE]",
        ]

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_cm)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hi")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        assert chunks == ["Hi"]

    @pytest.mark.asyncio
    async def test_stream_json_decode_error(self, model: BaichuanModel):
        """Test streaming handles malformed JSON lines."""
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "OK"}}]}',
            "data: {invalid json}",
            'data: {"choices": [{"delta": {"content": "!"}}]}',
            "data: [DONE]",
        ]

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_cm)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        assert chunks == ["OK", "!"]

    @pytest.mark.asyncio
    async def test_stream_http_status_error(self, model: BaichuanModel):
        """Test stream handles HTTP status errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Internal Server Error", request=MagicMock(), response=mock_response
            )
        )

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_cm)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            with pytest.raises(BaichuanAPIError) as exc_info:
                async for _ in model.stream(messages):
                    pass

        assert "百川智能 API 错误" in str(exc_info.value)
        assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_request_error(self, model: BaichuanModel):
        """Test stream handles request errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.stream = MagicMock(
            side_effect=httpx.RequestError("Connection error", request=MagicMock())
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            with pytest.raises(BaichuanAPIError) as exc_info:
                async for _ in model.stream(messages):
                    pass

        assert "网络请求失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_no_content_delta(self, model: BaichuanModel):
        """Test streaming skips deltas without content."""
        sse_lines = [
            'data: {"choices": [{"delta": {}}]}',
            'data: {"choices": [{"delta": {"content": "Has content"}}]}',
            "data: [DONE]",
        ]

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_cm)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        assert chunks == ["Has content"]

    # ===== Usage Tracking Tests =====

    @pytest.mark.asyncio
    async def test_generate_updates_usage_stats(self, model: BaichuanModel):
        """Test that generate updates model usage statistics."""
        mock_response_data = {
            "id": "chatcmpl-usage",
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
    async def test_reset_usage(self, model: BaichuanModel):
        """Test reset_usage clears accumulated usage."""
        mock_response_data = {
            "id": "chatcmpl-reset",
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

    # ===== BAICHUAN_MODELS Configuration Tests =====

    def test_baichuan_models_configuration(self):
        """Test that BAICHUAN_MODELS has correct structure for all tiers."""
        for tier in [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH]:
            assert tier in BAICHUAN_MODELS
            assert "name" in BAICHUAN_MODELS[tier]
            assert "cost_per_1k_prompt" in BAICHUAN_MODELS[tier]
            assert "cost_per_1k_completion" in BAICHUAN_MODELS[tier]
            assert BAICHUAN_MODELS[tier]["name"] == "Baichuan4"
            assert BAICHUAN_MODELS[tier]["cost_per_1k_prompt"] == 0.0
            assert BAICHUAN_MODELS[tier]["cost_per_1k_completion"] == 0.0

    # ===== BaichuanAPIError Tests =====

    def test_baichuan_api_error_message(self):
        """Test BaichuanAPIError can be instantiated with a message."""
        error = BaichuanAPIError("Test error message")
        assert str(error) == "Test error message"

    def test_baichuan_api_error_is_exception(self):
        """Test BaichuanAPIError inherits from Exception."""
        error = BaichuanAPIError("test")
        assert isinstance(error, Exception)
