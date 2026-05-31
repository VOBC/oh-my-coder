"""
Tests for WenxinModel (文心一言)

Coverage target: Increase from 25% to ~85%+
"""

import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.models.base import (
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
)
from src.models.wenxin import WenxinAPIError, WenxinModel


class TestWenxinModel:
    """Test suite for WenxinModel"""

    @pytest.fixture
    def config(self) -> ModelConfig:
        """Create a test configuration"""
        return ModelConfig(
            api_key="test-api-key",
            max_tokens=2048,
            temperature=0.7,
            timeout=30.0,
        )

    @pytest.fixture
    def model(self, config: ModelConfig) -> WenxinModel:
        """Create a WenxinModel instance"""
        return WenxinModel(
            config=config,
            tier=ModelTier.MEDIUM,
            secret_key="test-secret-key",
        )

    def test_provider_property(self, model: WenxinModel):
        """Test provider property returns WENXIN"""
        assert model.provider == ModelProvider.WENXIN

    def test_model_name_property(self, config: ModelConfig):
        """Test model_name property returns correct model for each tier"""
        # LOW tier
        model_low = WenxinModel(config, tier=ModelTier.LOW, secret_key="key")
        assert model_low.model_name == "eb-instant"

        # MEDIUM tier
        model_medium = WenxinModel(config, tier=ModelTier.MEDIUM, secret_key="key")
        assert model_medium.model_name == "completions_pro"

        # HIGH tier
        model_high = WenxinModel(config, tier=ModelTier.HIGH, secret_key="key")
        assert model_high.model_name == "completions"

    def test_init_sets_costs(self, config: ModelConfig):
        """Test that init sets correct costs based on tier"""
        model = WenxinModel(config, tier=ModelTier.LOW, secret_key="key")
        assert model.config.cost_per_1k_prompt == 0.004
        assert model.config.cost_per_1k_completion == 0.008

    def test_format_messages_with_system(self, model: WenxinModel):
        """Test _format_messages merges system message into first user message"""
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!"),
        ]
        formatted = model._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        assert "You are a helpful assistant." in formatted[0]["content"]
        assert "Hello!" in formatted[0]["content"]

    def test_format_messages_without_system(self, model: WenxinModel):
        """Test _format_messages without system message"""
        messages = [
            Message(role="user", content="Hello!"),
            Message(role="assistant", content="Hi there!"),
        ]
        formatted = model._format_messages(messages)

        assert len(formatted) == 2
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello!"
        assert formatted[1]["role"] == "assistant"

    def test_format_messages_with_tool_calls(self, model: WenxinModel):
        """Test _format_messages with tool calls"""
        messages = [
            Message(
                role="assistant",
                content="",
                tool_calls=[{"id": "call_123", "type": "function"}],
            ),
            Message(
                role="tool",
                content="Result",
                tool_call_id="call_123",
            ),
        ]
        formatted = model._format_messages(messages)

        assert len(formatted) == 2
        assert "tool_calls" in formatted[0]
        assert "tool_call_id" in formatted[1]

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self, model: WenxinModel):
        """Test _get_client creates a new client when none exists"""
        client = await model._get_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)

        # Should return the same client on subsequent calls
        client2 = await model._get_client()
        assert client is client2

    @pytest.mark.asyncio
    async def test_close(self, model: WenxinModel):
        """Test close method properly closes the client"""
        await model._get_client()
        assert model._client is not None

        await model.close()
        assert model._client is None

    @pytest.mark.asyncio
    async def test_get_access_token_cached(self, model: WenxinModel):
        """Test _get_access_token returns cached token when valid"""
        # Set up a fake cached token
        model._access_token = "cached-token"
        model._token_expire_time = time.time() + 3600  # Valid for 1 hour

        token = await model._get_access_token()
        assert token == "cached-token"

    @pytest.mark.asyncio
    async def test_get_access_token_refresh(self, model: WenxinModel):
        """Test _get_access_token fetches new token when expired"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "access_token": "new-token",
                "expires_in": 3600,
            }
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            token = await model._get_access_token()

        assert token == "new-token"
        assert model._access_token == "new-token"

    @pytest.mark.asyncio
    async def test_generate_success(self, model: WenxinModel):
        """Test generate method with successful response"""
        # Mock the access token
        model._access_token = "test-token"
        model._token_expire_time = time.time() + 3600

        # Mock response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "result": "Hello! How can I help you?",
                "finish_reason": "stop",
                "id": "test-id-123",
                "created": 1234567890,
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
            }
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello")]
            response = await model.generate(messages)

        assert isinstance(response, ModelResponse)
        assert response.content == "Hello! How can I help you?"
        assert response.model == model.model_name
        assert response.provider == ModelProvider.WENXIN
        assert response.finish_reason == "stop"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.metadata["id"] == "test-id-123"

    @pytest.mark.asyncio
    async def test_generate_with_optional_params(self, model: WenxinModel):
        """Test generate with optional parameters"""
        model._access_token = "test-token"
        model._token_expire_time = time.time() + 3600

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "result": "Response",
                "finish_reason": "stop",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        )

        mock_client = AsyncMock()
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.post = mock_post

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello")]
            await model.generate(
                messages,
                temperature=0.9,
                max_tokens=100,
                top_p=0.95,
                stop=["END"],
                tools=[{"type": "function"}],
                tool_choice="auto",
            )

        # Verify the request was made with correct parameters
        call_args = mock_post.call_args
        request_body = call_args[1].get("json")
        assert request_body["temperature"] == 0.9
        assert request_body["max_output_tokens"] == 100
        assert request_body["top_p"] == 0.95
        assert request_body["stop"] == ["END"]
        assert "tools" in request_body

    @pytest.mark.asyncio
    async def test_generate_http_error(self, model: WenxinModel):
        """Test generate handles HTTP errors"""
        model._access_token = "test-token"
        model._token_expire_time = time.time() + 3600

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json = Mock(return_value={"error_msg": "Invalid request"})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "400 Bad Request", request=Mock(), response=mock_response
            )
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello")]

            with pytest.raises(WenxinAPIError) as exc_info:
                await model.generate(messages)

            assert "文心一言 API 错误" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_request_error(self, model: WenxinModel):
        """Test generate handles network errors"""
        model._access_token = "test-token"
        model._token_expire_time = time.time() + 3600

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("Network error"))

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello")]

            with pytest.raises(WenxinAPIError) as exc_info:
                await model.generate(messages)

            assert "网络请求失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stream_success(self, model: WenxinModel):
        """Test stream method with successful streaming response"""
        model._access_token = "test-token"
        model._token_expire_time = time.time() + 3600

        # Create an async generator for aiter_lines
        async def mock_aiter_lines():
            yield 'data: {"result": "Hello", "is_end": false}'
            yield 'data: {"result": " world", "is_end": false}'
            yield 'data: {"result": "!", "is_end": true}'

        # Mock the response object
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_lines = mock_aiter_lines

        # Mock the context manager returned by client.stream()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.stream = Mock(return_value=mock_context_manager)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0] == "Hello"
        assert chunks[1] == " world"
        assert chunks[2] == "!"

    @pytest.mark.asyncio
    async def test_stream_handles_invalid_json(self, model: WenxinModel):
        """Test stream skips invalid JSON lines"""
        model._access_token = "test-token"
        model._token_expire_time = time.time() + 3600

        async def mock_aiter_lines():
            yield 'data: {"result": "Hello"}'
            yield "invalid json line"
            yield 'data: {"result": " world"}'

        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.stream = Mock(return_value=mock_context_manager)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        # Should only get valid chunks
        assert len(chunks) == 2
        assert chunks[0] == "Hello"
        assert chunks[1] == " world"

    @pytest.mark.asyncio
    async def test_stream_empty_result(self, model: WenxinModel):
        """Test stream skips chunks with empty result"""
        model._access_token = "test-token"
        model._token_expire_time = time.time() + 3600

        async def mock_aiter_lines():
            yield 'data: {"result": ""}'
            yield 'data: {"result": "Hello"}'

        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.stream = Mock(return_value=mock_context_manager)

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello")]
            chunks = []
            async for chunk in model.stream(messages):
                chunks.append(chunk)

        # Should skip empty result
        assert len(chunks) == 1
        assert chunks[0] == "Hello"

    @pytest.mark.asyncio
    async def test_stream_http_error(self, model: WenxinModel):
        """Test stream handles HTTP errors"""
        model._access_token = "test-token"
        model._token_expire_time = time.time() + 3600

        mock_response = Mock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.stream = Mock(
            side_effect=httpx.HTTPStatusError(
                "500 Internal Server Error", request=Mock(), response=mock_response
            )
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello")]

            with pytest.raises(WenxinAPIError):
                async for _ in model.stream(messages):
                    pass

    def test_wenxin_api_error_exception(self):
        """Test WenxinAPIError exception"""
        error = WenxinAPIError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


# Cleanup
@pytest.mark.asyncio
async def test_model_cleanup():
    """Test that model resources are properly cleaned up"""
    config = ModelConfig(api_key="test", timeout=30.0)
    model = WenxinModel(config, secret_key="key")

    await model._get_client()
    assert model._client is not None

    await model.close()
    assert model._client is None
