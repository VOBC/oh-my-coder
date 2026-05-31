"""
Tests for Tiangong (天工AI) model adapter.

Covers:
- Model initialization and configuration
- Client creation and management
- Message formatting
- generate() method (success, HTTP errors, request errors)
- stream() method (success, errors)
- close() method
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
from src.models.tiangong import TIANGONG_MODELS, TiangongAPIError, TiangongModel


class TestTiangongModel:
    """Test suite for TiangongModel."""

    @pytest.fixture
    def config(self) -> ModelConfig:
        """Create a test configuration."""
        return ModelConfig(
            api_key="test-tiangong-api-key",
            base_url=None,  # Should be set to default
            timeout=30.0,
            max_tokens=4096,
            temperature=0.7,
        )

    @pytest.fixture
    def model(self, config: ModelConfig) -> TiangongModel:
        """Create a TiangongModel instance."""
        return TiangongModel(config, tier=ModelTier.MEDIUM)

    # ===== Initialization Tests =====

    def test_init_sets_default_base_url(self, config: ModelConfig):
        """Test that default base URL is set when not provided."""
        TiangongModel(config, tier=ModelTier.MEDIUM)
        assert config.base_url == "https://model-platform.tiangong.cn/v1"

    def test_init_sets_cost_for_tier(self, config: ModelConfig):
        """Test that cost is set based on tier (currently all 0.0 for Tiangong)."""
        # Low tier
        TiangongModel(config, tier=ModelTier.LOW)
        assert config.cost_per_1k_prompt == 0.0
        assert config.cost_per_1k_completion == 0.0

        # Medium tier
        TiangongModel(config, tier=ModelTier.MEDIUM)
        assert config.cost_per_1k_prompt == 0.0
        assert config.cost_per_1k_completion == 0.0

        # High tier
        TiangongModel(config, tier=ModelTier.HIGH)
        assert config.cost_per_1k_prompt == 0.0
        assert config.cost_per_1k_completion == 0.0

    def test_model_name_property(self, model: TiangongModel):
        """Test model_name property returns correct model for tier."""
        assert model.model_name == "skywork-v1.0"

        # All tiers use the same model currently
        config = ModelConfig(api_key="test")
        low_model = TiangongModel(config, tier=ModelTier.LOW)
        assert low_model.model_name == "skywork-v1.0"

        high_model = TiangongModel(config, tier=ModelTier.HIGH)
        assert high_model.model_name == "skywork-v1.0"

    def test_provider_property(self, model: TiangongModel):
        """Test provider property returns TIANGONG."""
        assert model.provider == ModelProvider.TIANGONG

    # ===== Message Formatting Tests =====

    def test_format_messages_basic(self, model: TiangongModel):
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

    def test_format_messages_with_name(self, model: TiangongModel):
        """Test message formatting with name field."""
        messages = [
            Message(role="user", content="Hello", name="Alice"),
        ]
        formatted = model._format_messages(messages)
        assert "name" in formatted[0]
        assert formatted[0]["name"] == "Alice"

    def test_format_messages_with_tool_calls(self, model: TiangongModel):
        """Test message formatting with tool calls."""
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "get_weather", "arguments": "{}"},
            }
        ]
        messages = [
            Message(role="assistant", content="", tool_calls=tool_calls),
        ]
        formatted = model._format_messages(messages)
        assert "tool_calls" in formatted[0]
        assert formatted[0]["tool_calls"] == tool_calls

    def test_format_messages_with_tool_call_id(self, model: TiangongModel):
        """Test message formatting with tool call ID."""
        messages = [
            Message(role="tool", content="Result: 25°C", tool_call_id="call_123"),
        ]
        formatted = model._format_messages(messages)
        assert "tool_call_id" in formatted[0]
        assert formatted[0]["tool_call_id"] == "call_123"

    # ===== Client Management Tests =====

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self, model: TiangongModel):
        """Test that _get_client creates a new client when none exists."""
        client = await model._get_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert str(client.base_url) == "https://model-platform.tiangong.cn/v1/"
        assert client.headers["Authorization"] == "Bearer test-tiangong-api-key"
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing_client(self, model: TiangongModel):
        """Test that _get_client reuses existing client."""
        client1 = await model._get_client()
        client2 = await model._get_client()
        assert client1 is client2
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_recreates_closed_client(self, model: TiangongModel):
        """Test that _get_client creates new client when existing one is closed."""
        client1 = await model._get_client()
        await model.close()
        client2 = await model._get_client()
        assert client1 is not client2
        await model.close()

    @pytest.mark.asyncio
    async def test_close(self, model: TiangongModel):
        """Test close method properly closes client."""
        client = await model._get_client()
        assert not client.is_closed
        await model.close()
        assert model._client is None

    # ===== generate() Method Tests =====

    @pytest.mark.asyncio
    async def test_generate_success(self, model: TiangongModel):
        """Test successful generate call."""
        # Mock response data
        mock_response_data = {
            "id": "chatcmpl-123",
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

        # Create mock client
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello!")]
            response = await model.generate(messages)

        assert isinstance(response, ModelResponse)
        assert response.content == "Hello! How can I help you?"
        assert response.model == "skywork-v1.0"
        assert response.provider == ModelProvider.TIANGONG
        assert response.tier == ModelTier.MEDIUM
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30
        assert response.finish_reason == "stop"
        assert response.metadata["response_id"] == "chatcmpl-123"

        # Verify the request was made correctly
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/chat/completions"
        assert "json" in call_args[1]

    @pytest.mark.asyncio
    async def test_generate_with_tools(self, model: TiangongModel):
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
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        }
                    },
                },
            }
        ]

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="What's the weather?")]
            await model.generate(messages, tools=tools, tool_choice="auto")

        # Verify tools were included in request
        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert "tools" in request_body
        assert request_body["tools"] == tools
        assert request_body["tool_choice"] == "auto"

    @pytest.mark.asyncio
    async def test_generate_http_status_error(self, model: TiangongModel):
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

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello!")]
            with pytest.raises(TiangongAPIError) as exc_info:
                await model.generate(messages)

        assert "天工AI API 错误" in str(exc_info.value)
        assert "429" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_request_error(self, model: TiangongModel):
        """Test generate handles request errors (network issues)."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Network error", request=MagicMock())
        )

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello!")]
            with pytest.raises(TiangongAPIError) as exc_info:
                await model.generate(messages)

        assert "网络请求失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_with_optional_params(self, model: TiangongModel):
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

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            await model.generate(messages, top_p=0.9, stop=["\n", "END"])

        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert request_body["top_p"] == 0.9
        assert request_body["stop"] == ["\n", "END"]

    # ===== stream() Method Tests =====

    @pytest.mark.asyncio
    async def test_stream_success(self, model: TiangongModel):
        """Test successful streaming response."""
        # Simulate SSE stream
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " world"}}]}',
            "data: [DONE]",
        ]

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        # Mock the async iterator for aiter_lines
        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines

        # Create a proper async context manager mock
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_cm)

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Say hello")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_with_comments_and_empty_lines(self, model: TiangongModel):
        """Test streaming handles comments and empty lines."""
        sse_lines = [
            "",  # Empty line should be skipped
            ": heartbeat",  # Comment line should be skipped
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

        # Create a proper async context manager mock
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_cm)

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hi")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        assert chunks == ["Hi"]

    @pytest.mark.asyncio
    async def test_stream_json_decode_error(self, model: TiangongModel):
        """Test streaming handles malformed JSON lines."""
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "OK"}}]}',
            "data: {invalid json}",  # Should be skipped
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

        # Create a proper async context manager mock
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_cm)

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        # Should only get "OK" and "!", not the malformed line
        assert chunks == ["OK", "!"]

    @pytest.mark.asyncio
    async def test_stream_http_status_error(self, model: TiangongModel):
        """Test stream handles HTTP status errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Internal Server Error", request=MagicMock(), response=mock_response
            )
        )

        # Create a proper async context manager mock
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_stream_cm)

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            with pytest.raises(TiangongAPIError) as exc_info:
                async for _ in model.stream(messages):
                    pass

        assert "天工AI API 错误" in str(exc_info.value)
        assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_request_error(self, model: TiangongModel):
        """Test stream handles request errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.stream = MagicMock(
            side_effect=httpx.RequestError("Connection error", request=MagicMock())
        )

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            with pytest.raises(TiangongAPIError) as exc_info:
                async for _ in model.stream(messages):
                    pass

        assert "网络请求失败" in str(exc_info.value)

    # ===== Integration Tests =====

    @pytest.mark.asyncio
    async def test_generate_updates_usage_stats(self, model: TiangongModel):
        """Test that generate updates model usage statistics."""
        mock_response_data = {
            "id": "chatcmpl-999",
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

        # Check initial usage
        initial_usage = model.get_total_usage()
        assert initial_usage.total_tokens == 0

        # Patch _get_client to return mock client
        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            await model.generate(messages)

        # Check updated usage
        updated_usage = model.get_total_usage()
        assert updated_usage.prompt_tokens == 100
        assert updated_usage.completion_tokens == 50
        assert updated_usage.total_tokens == 150

    # ===== TIANGONG_MODELS Configuration Tests =====

    def test_tiangong_models_configuration(self):
        """Test that TIANGONG_MODELS has correct structure."""
        assert ModelTier.LOW in TIANGONG_MODELS
        assert ModelTier.MEDIUM in TIANGONG_MODELS
        assert ModelTier.HIGH in TIANGONG_MODELS

        for tier in [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH]:
            assert "name" in TIANGONG_MODELS[tier]
            assert "cost_per_1k_prompt" in TIANGONG_MODELS[tier]
            assert "cost_per_1k_completion" in TIANGONG_MODELS[tier]

    def test_tiangong_all_tiers_same_model(self):
        """Test that all tiers currently use the same model name."""
        assert TIANGONG_MODELS[ModelTier.LOW]["name"] == "skywork-v1.0"
        assert TIANGONG_MODELS[ModelTier.MEDIUM]["name"] == "skywork-v1.0"
        assert TIANGONG_MODELS[ModelTier.HIGH]["name"] == "skywork-v1.0"
