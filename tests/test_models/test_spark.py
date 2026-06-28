"""
Tests for Spark (讯飞星火) model adapter.

Covers:
- Model initialization and configuration
- Client creation and management
- Message formatting (including system->user conversion)
- generate() method (success, HTTP errors, request errors, tools, optional params)
- stream() method (character-by-character streaming)
- close() method
- Usage tracking
- SparkAPIError exception
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
from src.models.spark import SPARK_API_BASE, SPARK_MODELS, SparkAPIError, SparkModel


class TestSparkModel:
    """Test suite for SparkModel."""

    @pytest.fixture
    def config(self) -> ModelConfig:
        """Create a test configuration."""
        return ModelConfig(
            api_key="test-spark-api-key",
            base_url=None,
            timeout=30.0,
            max_tokens=4096,
            temperature=0.7,
        )

    @pytest.fixture
    def model(self, config: ModelConfig) -> SparkModel:
        """Create a SparkModel instance."""
        return SparkModel(
            config,
            tier=ModelTier.MEDIUM,
            app_id="test-app-id",
            secret_key="test-secret-key",
        )

    # ===== Initialization Tests =====

    def test_init_sets_default_base_url(self, config: ModelConfig):
        """Test that default base URL is set when not provided."""
        SparkModel(config, tier=ModelTier.MEDIUM, app_id="test", secret_key="test")
        assert config.base_url == "https://spark-api.xf-yun.com/v3.1/chat"

    def test_init_preserves_custom_base_url(self, config: ModelConfig):
        """Test that custom base_url is preserved."""
        config.base_url = "https://custom-spark-api.com/v1"
        model = SparkModel(
            config, tier=ModelTier.MEDIUM, app_id="test", secret_key="test"
        )
        assert model.config.base_url == "https://custom-spark-api.com/v1"

    def test_init_sets_cost_for_tier(self, config: ModelConfig):
        """Test that cost is set based on tier."""
        for tier in [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH]:
            cfg = ModelConfig(api_key="test")
            SparkModel(cfg, tier=tier, app_id="test", secret_key="test")
            assert cfg.cost_per_1k_prompt == 0.0
            assert cfg.cost_per_1k_completion == 0.0

    def test_init_stores_app_id_and_secret_key(self, config: ModelConfig):
        """Test that app_id and secret_key are stored."""
        model = SparkModel(
            config, tier=ModelTier.MEDIUM, app_id="my-app-id", secret_key="my-secret"
        )
        assert model.app_id == "my-app-id"
        assert model.secret_key == "my-secret"

    def test_init_without_app_id(self, config: ModelConfig):
        """Test initialization without app_id."""
        model = SparkModel(config, tier=ModelTier.MEDIUM)
        assert model.app_id is None
        assert model.secret_key is None

    def test_model_name_property(self, config: ModelConfig):
        """Test model_name property returns correct model for each tier."""
        # LOW tier
        cfg_low = ModelConfig(api_key="test")
        low_model = SparkModel(cfg_low, tier=ModelTier.LOW, app_id="test", secret_key="test")
        assert low_model.model_name == "generalv3"

        # MEDIUM tier
        cfg_med = ModelConfig(api_key="test")
        med_model = SparkModel(cfg_med, tier=ModelTier.MEDIUM, app_id="test", secret_key="test")
        assert med_model.model_name == "generalv3.5"

        # HIGH tier
        cfg_high = ModelConfig(api_key="test")
        high_model = SparkModel(cfg_high, tier=ModelTier.HIGH, app_id="test", secret_key="test")
        assert high_model.model_name == "4.0Ultra"

    def test_provider_property(self, model: SparkModel):
        """Test provider property returns SPARK."""
        assert model.provider == ModelProvider.SPARK

    # ===== SPARK_MODELS Configuration Tests =====

    def test_spark_models_configuration(self):
        """Test that SPARK_MODELS has correct structure for all tiers."""
        for tier in [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH]:
            assert tier in SPARK_MODELS
            assert "name" in SPARK_MODELS[tier]
            assert "cost_per_1k_prompt" in SPARK_MODELS[tier]
            assert "cost_per_1k_completion" in SPARK_MODELS[tier]

        assert SPARK_MODELS[ModelTier.LOW]["name"] == "generalv3"
        assert SPARK_MODELS[ModelTier.MEDIUM]["name"] == "generalv3.5"
        assert SPARK_MODELS[ModelTier.HIGH]["name"] == "4.0Ultra"

    def test_spark_api_base_constant(self):
        """Test SPARK_API_BASE constant."""
        assert SPARK_API_BASE == "https://spark-api.xf-yun.com"

    # ===== Message Formatting Tests =====

    def test_format_messages_system_converted_to_user(self, model: SparkModel):
        """Test that system messages are converted to user role (Spark API requirement)."""
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!"),
        ]
        formatted = model._format_messages(messages)
        assert len(formatted) == 2
        # System message should be converted to "user" role
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "You are a helpful assistant."
        # User message should remain unchanged
        assert formatted[1]["role"] == "user"
        assert formatted[1]["content"] == "Hello!"

    def test_format_messages_user_and_assistant(self, model: SparkModel):
        """Test formatting of user and assistant messages."""
        messages = [
            Message(role="user", content="Hello!"),
            Message(role="assistant", content="Hi there!"),
        ]
        formatted = model._format_messages(messages)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello!"
        assert formatted[1]["role"] == "assistant"
        assert formatted[1]["content"] == "Hi there!"

    def test_format_messages_with_tool_calls(self, model: SparkModel):
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

    def test_format_messages_with_tool_call_id(self, model: SparkModel):
        """Test message formatting with tool call ID."""
        messages = [
            Message(role="tool", content="Result: 25°C", tool_call_id="call_123"),
        ]
        formatted = model._format_messages(messages)
        assert "tool_call_id" in formatted[0]
        assert formatted[0]["tool_call_id"] == "call_123"

    def test_format_messages_empty_content(self, model: SparkModel):
        """Test formatting messages with empty content."""
        messages = [
            Message(role="user", content=""),
        ]
        formatted = model._format_messages(messages)
        assert len(formatted) == 1
        assert formatted[0]["content"] == ""

    # ===== Client Management Tests =====

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self, model: SparkModel):
        """Test that _get_client creates a new client when none exists."""
        client = await model._get_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert client.timeout.read == 30.0  # timeout is stored as float
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing_client(self, model: SparkModel):
        """Test that _get_client reuses existing client."""
        client1 = await model._get_client()
        client2 = await model._get_client()
        assert client1 is client2
        await model.close()

    @pytest.mark.asyncio
    async def test_get_client_recreates_closed_client(self, model: SparkModel):
        """Test that _get_client creates new client when existing one is closed."""
        client1 = await model._get_client()
        await model.close()
        assert model._client is None
        client2 = await model._get_client()
        assert client1 is not client2
        await model.close()

    @pytest.mark.asyncio
    async def test_close(self, model: SparkModel):
        """Test close method properly closes client."""
        client = await model._get_client()
        assert not client.is_closed
        await model.close()
        assert model._client is None

    @pytest.mark.asyncio
    async def test_close_when_no_client(self, config: ModelConfig):
        """Test close method when no client exists."""
        model = SparkModel(config, tier=ModelTier.MEDIUM, app_id="test", secret_key="test")
        assert model._client is None
        # Should not raise an error
        await model.close()
        assert model._client is None

    # ===== generate() Method Tests =====

    @pytest.mark.asyncio
    async def test_generate_success(self, model: SparkModel):
        """Test successful generate call."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success", "sid": "test-sid-123"},
            "payload": {
                "choices": {
                    "text": [
                        {"content": "Hello! How can I help you?", "role": "assistant"}
                    ]
                },
                "usage": {
                    "text": {
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                    }
                },
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
        assert response.model == "generalv3.5"
        assert response.provider == ModelProvider.SPARK
        assert response.tier == ModelTier.MEDIUM
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30
        assert response.finish_reason == "stop"
        assert response.metadata["app_id"] == "test-app-id"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_request_body_structure(self, model: SparkModel):
        """Test that request body has correct structure for Spark API."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "Test", "role": "assistant"}]},
                "usage": {"text": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}},
            },
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            await model.generate(messages, temperature=0.5, max_tokens=100)

        call_args = mock_client.post.call_args
        # Check URL
        assert "spark-api.xf-yun.com" in call_args[0][0]
        # Check request body structure
        request_body = call_args[1]["json"]
        assert "header" in request_body
        assert request_body["header"]["app_id"] == "test-app-id"
        assert "parameter" in request_body
        assert request_body["parameter"]["chat"]["domain"] == "generalv3.5"
        assert request_body["parameter"]["chat"]["temperature"] == 0.5
        assert request_body["parameter"]["chat"]["max_tokens"] == 100
        assert "payload" in request_body
        assert "message" in request_body["payload"]

    @pytest.mark.asyncio
    async def test_generate_with_tools(self, model: SparkModel):
        """Test generate with tools parameter."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "I'll help you.", "role": "assistant"}]},
                "usage": {"text": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}},
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
            await model.generate(messages, tools=tools)

        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert "tools" in request_body["payload"]
        assert request_body["payload"]["tools"] == tools

    @pytest.mark.asyncio
    async def test_generate_without_tools(self, model: SparkModel):
        """Test generate without tools parameter (should not include tools in request)."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "Response", "role": "assistant"}]},
                "usage": {"text": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}},
            },
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
        # Should not have "tools" in payload when not provided
        assert "tools" not in request_body["payload"]

    @pytest.mark.asyncio
    async def test_generate_empty_choices(self, model: SparkModel):
        """Test generate handles empty choices in response."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": []},
                "usage": {"text": {"prompt_tokens": 5, "completion_tokens": 0, "total_tokens": 5}},
            },
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
    async def test_generate_missing_usage(self, model: SparkModel):
        """Test generate handles missing usage field in response."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "Response without usage", "role": "assistant"}]},
            },
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
    async def test_generate_missing_payload(self, model: SparkModel):
        """Test generate handles missing payload field in response."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
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
        assert response.usage.prompt_tokens == 0

    @pytest.mark.asyncio
    async def test_generate_http_status_error(self, model: SparkModel):
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
            with pytest.raises(SparkAPIError) as exc_info:
                await model.generate(messages)

        assert "讯飞星火 API 错误" in str(exc_info.value)
        assert "429" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_request_error(self, model: SparkModel):
        """Test generate handles request errors (network issues)."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Network error", request=MagicMock())
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello!")]
            with pytest.raises(SparkAPIError) as exc_info:
                await model.generate(messages)

        assert "网络请求失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_latency_recorded(self, model: SparkModel):
        """Test that latency is recorded in response."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "Latency test", "role": "assistant"}]},
                "usage": {"text": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
            },
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
    async def test_generate_uses_kwargs_temperature(self, model: SparkModel):
        """Test that temperature from kwargs overrides config."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "Test", "role": "assistant"}]},
                "usage": {"text": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}},
            },
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            await model.generate(messages, temperature=0.9)

        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert request_body["parameter"]["chat"]["temperature"] == 0.9

    @pytest.mark.asyncio
    async def test_generate_uses_kwargs_max_tokens(self, model: SparkModel):
        """Test that max_tokens from kwargs overrides config."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "Test", "role": "assistant"}]},
                "usage": {"text": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}},
            },
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            await model.generate(messages, max_tokens=2048)

        call_args = mock_client.post.call_args
        request_body = call_args[1]["json"]
        assert request_body["parameter"]["chat"]["max_tokens"] == 2048

    # ===== stream() Method Tests =====

    @pytest.mark.asyncio
    async def test_stream_success(self, model: SparkModel):
        """Test successful streaming response (character-by-character)."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "Hello world!", "role": "assistant"}]},
                "usage": {"text": {"prompt_tokens": 10, "completion_tokens": 12, "total_tokens": 22}},
            },
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Say hello")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        # Stream yields each character individually
        assert chunks == ["H", "e", "l", "l", "o", " ", "w", "o", "r", "l", "d", "!"]

    @pytest.mark.asyncio
    async def test_stream_empty_content(self, model: SparkModel):
        """Test streaming with empty content."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "", "role": "assistant"}]},
                "usage": {"text": {"prompt_tokens": 5, "completion_tokens": 0, "total_tokens": 5}},
            },
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_stream_error_propagation(self, model: SparkModel):
        """Test that stream propagates errors from generate."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection error", request=MagicMock())
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Test")]
            with pytest.raises(SparkAPIError) as exc_info:
                async for _ in model.stream(messages):
                    pass

        assert "网络请求失败" in str(exc_info.value)

    # ===== Usage Tracking Tests =====

    @pytest.mark.asyncio
    async def test_generate_updates_usage_stats(self, model: SparkModel):
        """Test that generate updates model usage statistics."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "Test response", "role": "assistant"}]},
                "usage": {
                    "text": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150,
                    }
                },
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
    async def test_reset_usage(self, model: SparkModel):
        """Test reset_usage clears accumulated usage."""
        mock_response_data = {
            "header": {"code": 0, "message": "Success"},
            "payload": {
                "choices": {"text": [{"content": "Test", "role": "assistant"}]},
                "usage": {"text": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}},
            },
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

    # ===== SparkAPIError Tests =====

    def test_spark_api_error_message(self):
        """Test SparkAPIError can be instantiated with a message."""
        error = SparkAPIError("Test error message")
        assert str(error) == "Test error message"

    def test_spark_api_error_is_exception(self):
        """Test SparkAPIError inherits from Exception."""
        error = SparkAPIError("test")
        assert isinstance(error, Exception)

    def test_spark_api_error_raise(self):
        """Test SparkAPIError can be raised and caught."""
        with pytest.raises(SparkAPIError) as exc_info:
            raise SparkAPIError("Custom error")
        assert str(exc_info.value) == "Custom error"
