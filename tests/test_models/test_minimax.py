"""
Tests for MiniMax model adapter.

Covers:
- Model initialization and configuration
- Client creation and management
- Message formatting
- generate() method (success, HTTP errors, request errors, tools, optional params)
- close() method
- Usage tracking
- MiniMaxAPIError exception
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
from src.models.minimax import MINIMAX_MODELS, MiniMaxAPIError, MiniMaxModel


class TestMiniMaxModel:
    """Test suite for MiniMaxModel."""

    @pytest.fixture
    def config(self) -> ModelConfig:
        """Create a test configuration."""
        return ModelConfig(
            api_key="test-minimax-api-key",
            base_url=None,  # Should be set to default
            timeout=30.0,
            max_tokens=4096,
            temperature=0.7,
        )

    @pytest.fixture
    def model(self, config: ModelConfig) -> MiniMaxModel:
        """Create a MiniMaxModel instance."""
        return MiniMaxModel(config, tier=ModelTier.MEDIUM)

    # ===== Initialization Tests =====

    def test_init_sets_default_base_url(self, config: ModelConfig):
        """Test that default base URL is set when not provided."""
        MiniMaxModel(config, tier=ModelTier.MEDIUM)
        assert config.base_url == "https://api.minimax.chat/v1"

    def test_init_sets_cost_for_tier(self, config: ModelConfig):
        """Test that cost is set based on tier."""
        # Low tier
        cfg_low = ModelConfig(api_key="test")
        MiniMaxModel(cfg_low, tier=ModelTier.LOW)
        assert cfg_low.cost_per_1k_prompt == 0.01
        assert cfg_low.cost_per_1k_completion == 0.02

        # Medium tier
        cfg_medium = ModelConfig(api_key="test")
        MiniMaxModel(cfg_medium, tier=ModelTier.MEDIUM)
        assert cfg_medium.cost_per_1k_prompt == 0.005
        assert cfg_medium.cost_per_1k_completion == 0.015

        # High tier
        cfg_high = ModelConfig(api_key="test")
        MiniMaxModel(cfg_high, tier=ModelTier.HIGH)
        assert cfg_high.cost_per_1k_prompt == 0.02
        assert cfg_high.cost_per_1k_completion == 0.05

    def test_model_name_property(self, model: MiniMaxModel):
        """Test model_name property returns correct model for tier."""
        assert model.model_name == "abab6.5s-chat"

        # Test other tiers
        config = ModelConfig(api_key="test")
        low_model = MiniMaxModel(config, tier=ModelTier.LOW)
        assert low_model.model_name == "abab6-chat"

        high_model = MiniMaxModel(config, tier=ModelTier.HIGH)
        assert high_model.model_name == "abab6.5g-chat"

    def test_provider_property(self, model: MiniMaxModel):
        """Test provider property returns MINIMAX."""
        assert model.provider == ModelProvider.MINIMAX

    def test_init_custom_base_url(self):
        """Test that custom base_url is preserved."""
        config = ModelConfig(
            api_key="test-key",
            base_url="https://custom.minimax.chat/v1",
        )
        model = MiniMaxModel(config, tier=ModelTier.MEDIUM)
        assert model.config.base_url == "https://custom.minimax.chat/v1"

    # ===== Message Formatting Tests =====

    def test_format_messages_basic(self, model: MiniMaxModel):
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

    def test_format_messages_with_name(self, model: MiniMaxModel):
        """Test message formatting with name field."""
        messages = [
            Message(role="user", content="Hello", name="Alice"),
        ]
        formatted = model._format_messages(messages)
        assert "name" in formatted[0]
        assert formatted[0]["name"] == "Alice"

    def test_format_messages_with_tool_calls(self, model: MiniMaxModel):
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

    def test_format_messages_with_tool_call_id(self, model: MiniMaxModel):
        """Test message formatting with tool call ID."""
        messages = [
            Message(role="tool", content="Result: 25°C", tool_call_id="call_123"),
        ]
        formatted = model._format_messages(messages)
        assert "tool_call_id" in formatted[0]
        assert formatted[0]["tool_call_id"] == "call_123"

    def test_format_messages_empty_content(self, model: MiniMaxModel):
        """Test message formatting with empty content."""
        messages = [
            Message(role="user", content=""),
        ]
        formatted = model._format_messages(messages)
        assert formatted[0]["content"] == ""

    # ===== Client Management Tests =====

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self, model: MiniMaxModel):
        """Test that _get_client creates a new client when none exists."""
        client = await model._get_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert str(client.base_url) == "https://api.minimax.chat/v1/"
        assert client.headers["Authorization"] == "Bearer test-minimax-api-key"
        assert client.headers["Content-Type"] == "application/json"
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing_client(self, model: MiniMaxModel):
        """Test that _get_client reuses existing client."""
        client1 = await model._get_client()
        client2 = await model._get_client()
        assert client1 is client2
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_recreates_closed_client(self, model: MiniMaxModel):
        """Test that _get_client creates new client when existing one is closed."""
        client1 = await model._get_client()
        await model.close()
        assert client1.is_closed
        client2 = await model._get_client()
        assert client1 is not client2
        await model.close()

    @pytest.mark.asyncio
    async def test_close(self, model: MiniMaxModel):
        """Test close method properly closes client."""
        client = await model._get_client()
        assert not client.is_closed
        await model.close()
        assert model._client is None

    @pytest.mark.asyncio
    async def test_close_when_no_client(self, model: MiniMaxModel):
        """Test close method when no client exists."""
        assert model._client is None
        await model.close()  # Should not raise
        assert model._client is None

    # ===== generate() Method Tests =====

    @pytest.mark.asyncio
    async def test_generate_success(self, model: MiniMaxModel):
        """Test successful generate call."""
        mock_response_data = {
            "id": "chatcmpl-minimax-123",
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Hello!"},
                        {"role": "assistant", "content": "Hello! How can I help you?"},
                    ],
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
        assert response.model == "abab6.5s-chat"
        assert response.provider == ModelProvider.MINIMAX
        assert response.tier == ModelTier.MEDIUM
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30
        assert response.finish_reason == "stop"
        assert response.latency_ms > 0

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/text/chatcompletion_v2"
        assert "json" in call_args[1]

    @pytest.mark.asyncio
    async def test_generate_with_tools(self, model: MiniMaxModel):
        """Test generate with tools parameter."""
        mock_response_data = {
            "id": "chatcmpl-minimax-456",
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "What's the weather?"},
                        {"role": "assistant", "content": ""},
                    ],
                    "finish_reason": "tool_calls",
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
                        "properties": {"location": {"type": "string"}},
                    },
                },
            }
        ]

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="What's the weather?")]
            response = await model.generate(messages, tools=tools, tool_choice="auto")

        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["function"]["name"] == "get_weather"

        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert "tools" in request_body
        assert request_body["tools"] == tools
        assert request_body["tool_choice"] == "auto"

    @pytest.mark.asyncio
    async def test_generate_with_tool_calls_in_response(self, model: MiniMaxModel):
        """Test generate properly extracts tool_calls from response."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Help me"},
                        {"role": "assistant", "content": "I'll help you"},
                    ],
                    "finish_reason": "tool_calls",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {"name": "search", "arguments": "{}"},
                        }
                    ],
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
            messages = [Message(role="user", content="Help me")]
            response = await model.generate(messages)

        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["id"] == "call_123"
        assert response.finish_reason == "tool_calls"

    @pytest.mark.asyncio
    async def test_generate_with_top_p(self, model: MiniMaxModel):
        """Test generate with top_p parameter."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Test"},
                        {"role": "assistant", "content": "Response with top_p"},
                    ],
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
            await model.generate(messages, top_p=0.9)

        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert request_body["top_p"] == 0.9

    @pytest.mark.asyncio
    async def test_generate_with_max_tokens_and_temperature(self, model: MiniMaxModel):
        """Test generate uses provided max_tokens and temperature."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Test"},
                        {"role": "assistant", "content": "Response"},
                    ],
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            await model.generate(messages, max_tokens=2048, temperature=0.5)

        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert request_body["max_tokens"] == 2048
        assert request_body["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_generate_http_status_error(self, model: MiniMaxModel):
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
            with pytest.raises(MiniMaxAPIError) as exc_info:
                await model.generate(messages)

        assert "MiniMax API 错误" in str(exc_info.value)
        assert "429" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_request_error(self, model: MiniMaxModel):
        """Test generate handles request errors (network issues)."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Network error", request=MagicMock())
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello!")]
            with pytest.raises(MiniMaxAPIError) as exc_info:
                await model.generate(messages)

        assert "网络请求失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_empty_content(self, model: MiniMaxModel):
        """Test generate handles empty content in response."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Test"},
                        {"role": "assistant", "content": ""},
                    ],
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
    async def test_generate_missing_usage(self, model: MiniMaxModel):
        """Test generate handles missing usage field in response."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Test"},
                        {"role": "assistant", "content": "Response without usage"},
                    ],
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
    async def test_generate_missing_finish_reason(self, model: MiniMaxModel):
        """Test generate handles missing finish_reason in response."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Test"},
                        {"role": "assistant", "content": "Response"},
                    ],
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
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

        assert response.finish_reason == "stop"  # Default value

    @pytest.mark.asyncio
    async def test_generate_latency_recorded(self, model: MiniMaxModel):
        """Test that latency is recorded in response."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Test"},
                        {"role": "assistant", "content": "Latency test"},
                    ],
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
    async def test_generate_request_body_structure(self, model: MiniMaxModel):
        """Test that request body has correct structure for MiniMax API."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Test"},
                        {"role": "assistant", "content": "OK"},
                    ],
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
            await model.generate(messages)

        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]

        # Verify MiniMax-specific request structure
        assert request_body["model"] == "abab6.5s-chat"
        assert "messages" in request_body
        assert "max_tokens" in request_body
        assert "temperature" in request_body
        assert call_args[0][0] == "/text/chatcompletion_v2"

    # ===== Usage Tracking Tests =====

    @pytest.mark.asyncio
    async def test_generate_updates_usage_stats(self, model: MiniMaxModel):
        """Test that generate updates model usage statistics."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Test"},
                        {"role": "assistant", "content": "Test response"},
                    ],
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
    async def test_reset_usage(self, model: MiniMaxModel):
        """Test reset_usage clears accumulated usage."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Test"},
                        {"role": "assistant", "content": "Test"},
                    ],
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

    # ===== MINIMAX_MODELS Configuration Tests =====

    def test_minimax_models_configuration(self):
        """Test that MINIMAX_MODELS has correct structure for all tiers."""
        for tier_key in ["low", "medium", "high"]:
            assert tier_key in MINIMAX_MODELS
            assert "name" in MINIMAX_MODELS[tier_key]
            assert "cost_per_1k_prompt" in MINIMAX_MODELS[tier_key]
            assert "cost_per_1k_completion" in MINIMAX_MODELS[tier_key]

        # Verify specific model names
        assert MINIMAX_MODELS["low"]["name"] == "abab6-chat"
        assert MINIMAX_MODELS["medium"]["name"] == "abab6.5s-chat"
        assert MINIMAX_MODELS["high"]["name"] == "abab6.5g-chat"

    def test_minimax_models_costs(self):
        """Test that MINIMAX_MODELS has correct cost configuration."""
        # Low tier - most expensive per token
        assert MINIMAX_MODELS["low"]["cost_per_1k_prompt"] == 0.01
        assert MINIMAX_MODELS["low"]["cost_per_1k_completion"] == 0.02

        # Medium tier - cheapest
        assert MINIMAX_MODELS["medium"]["cost_per_1k_prompt"] == 0.005
        assert MINIMAX_MODELS["medium"]["cost_per_1k_completion"] == 0.015

        # High tier - most powerful, more expensive
        assert MINIMAX_MODELS["high"]["cost_per_1k_prompt"] == 0.02
        assert MINIMAX_MODELS["high"]["cost_per_1k_completion"] == 0.05

    # ===== MiniMaxAPIError Tests =====

    def test_minimax_api_error_message(self):
        """Test MiniMaxAPIError can be instantiated with a message."""
        error = MiniMaxAPIError("Test error message")
        assert str(error) == "Test error message"

    def test_minimax_api_error_is_exception(self):
        """Test MiniMaxAPIError inherits from Exception."""
        error = MiniMaxAPIError("test")
        assert isinstance(error, Exception)

    @pytest.mark.asyncio
    async def test_generate_updates_usage_on_success(self, model: MiniMaxModel):
        """Test that usage is updated after successful generate call."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Track usage"},
                        {"role": "assistant", "content": "Tracking"},
                    ],
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 25,
                "completion_tokens": 35,
                "total_tokens": 60,
            },
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Track usage")]
            await model.generate(messages)

        usage = model.get_total_usage()
        assert usage.prompt_tokens == 25
        assert usage.completion_tokens == 35
        assert usage.total_tokens == 60

    @pytest.mark.asyncio
    async def test_generate_multiple_calls_accumulate_usage(self, model: MiniMaxModel):
        """Test that multiple generate calls accumulate usage statistics."""
        mock_response_data = {
            "choices": [
                {
                    "messages": [
                        {"role": "user", "content": "Test"},
                        {"role": "assistant", "content": "Response"},
                    ],
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
            for _ in range(3):
                messages = [Message(role="user", content="Test")]
                await model.generate(messages)

        usage = model.get_total_usage()
        assert usage.prompt_tokens == 30  # 10 * 3
        assert usage.completion_tokens == 60  # 20 * 3
        assert usage.total_tokens == 90  # 30 * 3

    # ===== stream() Method Tests =====

    @pytest.mark.asyncio
    async def test_stream_success(self, model: MiniMaxModel):
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
    async def test_stream_with_comments_and_empty_lines(self, model: MiniMaxModel):
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
    async def test_stream_json_decode_error(self, model: MiniMaxModel):
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
    async def test_stream_http_status_error(self, model: MiniMaxModel):
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
            with pytest.raises(MiniMaxAPIError) as exc_info:
                async for _ in model.stream(messages):
                    pass

        assert "MiniMax API 错误" in str(exc_info.value)
        assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_request_error(self, model: MiniMaxModel):
        """Test stream handles request errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.stream = MagicMock(
            side_effect=httpx.RequestError("Connection error", request=MagicMock())
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            with pytest.raises(MiniMaxAPIError) as exc_info:
                async for _ in model.stream(messages):
                    pass

        assert "网络请求失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_no_content_delta(self, model: MiniMaxModel):
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

    @pytest.mark.asyncio
    async def test_stream_with_tools(self, model: MiniMaxModel):
        """Test stream with tools parameter."""
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Let me help"}}]}',
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
            messages = [Message(role="user", content="Help me")]
            chunks = []
            async for chunk in model.stream(messages, tools=[{"type": "function"}]):
                chunks.append(chunk)

        assert chunks == ["Let me help"]
        call_args = mock_client.stream.call_args
        assert call_args is not None
