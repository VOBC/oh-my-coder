"""
Tests for HunyuanModel (腾讯混元)

Coverage target: Increase from 22% to ~85%+
"""

import hashlib
import hmac
import json
import time
from typing import Any, Optional
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.models.base import (
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
    Usage,
)
from src.models.hunyuan import HunyuanModel, HunyuanAPIError


class TestHunyuanModel:
    """Test suite for HunyuanModel"""

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
    def model(self, config: ModelConfig) -> HunyuanModel:
        """Create a HunyuanModel instance"""
        model = HunyuanModel(
            config=config,
            tier=ModelTier.MEDIUM,
            secret_id="test-secret-id",
            secret_key="test-secret-key",
        )
        # Mock the abstract stream method to allow instantiation
        model.stream = AsyncMock(return_value=AsyncMock())
        return model

    def test_provider_property(self, model: HunyuanModel):
        """Test provider property returns HUNYUAN"""
        assert model.provider == ModelProvider.HUNYUAN

    def test_model_name_property(self, config: ModelConfig):
        """Test model_name property returns correct model for each tier"""
        # LOW tier
        model_low = HunyuanModel(config, tier=ModelTier.LOW, secret_id="id", secret_key="key")
        assert model_low.model_name == "hunyuan-standard"

        # MEDIUM tier
        model_medium = HunyuanModel(config, tier=ModelTier.MEDIUM, secret_id="id", secret_key="key")
        assert model_medium.model_name == "hunyuan-standard"

        # HIGH tier
        model_high = HunyuanModel(config, tier=ModelTier.HIGH, secret_id="id", secret_key="key")
        assert model_high.model_name == "hunyuan-pro"

    def test_init_sets_base_url(self, config: ModelConfig):
        """Test that init sets base_url if not provided"""
        config.base_url = None
        model = HunyuanModel(config, tier=ModelTier.MEDIUM, secret_id="id", secret_key="key")
        assert model.config.base_url == "https://api.hunyuan.cn"

    def test_init_sets_costs(self, config: ModelConfig):
        """Test that init sets correct costs based on tier"""
        model = HunyuanModel(config, tier=ModelTier.LOW, secret_id="id", secret_key="key")
        assert model.config.cost_per_1k_prompt == 0.0
        assert model.config.cost_per_1k_completion == 0.0

    def test_sign_tc3(self, model: HunyuanModel):
        """Test TC3-HMAC-SHA256 signature generation"""
        secret_key = "test-secret-key"
        date = "2025-01-15"
        service = "hunyuan"
        action = "ChatCompletions"
        payload = json.dumps({"model": "hunyuan-standard", "messages": []})

        signature = model._sign_tc3(secret_key, date, service, action, payload)

        # Verify signature format
        assert signature.startswith("TC3-HMAC-SHA256 ")
        assert "Credential=" in signature
        assert "SignedHeaders=" in signature
        assert "Signature=" in signature

        # Verify credential scope
        assert f"{date}/{service}/tc3_request" in signature

    def test_sign_tc3_creates_valid_hmac(self, model: HunyuanModel):
        """Test that _sign_tc3 creates a valid HMAC-SHA256 signature"""
        secret_key = "my-secret-key"
        date = "2025-01-15"
        service = "hunyuan"
        action = "ChatCompletions"
        payload = '{"test": "data"}'

        signature = model._sign_tc3(secret_key, date, service, action, payload)

        # Extract the signature from the Authorization header
        sig_part = [s for s in signature.split(", ") if s.startswith("Signature=")][0]
        sig_value = sig_part.split("=")[1]

        # Verify it's a valid hex string (64 chars for SHA256)
        assert len(sig_value) == 64
        int(sig_value, 16)  # Should not raise

    def test_format_messages(self, model: HunyuanModel):
        """Test _format_messages converts Message objects correctly"""
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!"),
            Message(role="assistant", content="Hi there!"),
            Message(role="tool", content="Result", tool_call_id="call_123"),
        ]
        formatted = model._format_messages(messages)

        assert len(formatted) == 4
        assert formatted[0]["role"] == "system"
        assert formatted[1]["role"] == "user"
        assert formatted[2]["role"] == "assistant"
        assert formatted[3]["role"] == "tool"

        # Check tool_call_id is included
        assert "tool_call_id" in formatted[3]
        assert formatted[3]["tool_call_id"] == "call_123"

    def test_format_messages_with_tool_calls(self, model: HunyuanModel):
        """Test _format_messages includes tool_calls for assistant messages"""
        messages = [
            Message(
                role="assistant",
                content="Let me check that.",
                tool_calls=[{"id": "call_123", "type": "function", "function": {"name": "get_weather"}}],
            ),
        ]
        formatted = model._format_messages(messages)

        assert len(formatted) == 1
        assert "tool_calls" in formatted[0]

    def test_format_messages_with_name(self, model: HunyuanModel):
        """Test _format_messages includes name when present"""
        messages = [
            Message(role="user", content="Hello", name="John"),
        ]
        formatted = model._format_messages(messages)

        assert len(formatted) == 1
        assert "name" in formatted[0]
        assert formatted[0]["name"] == "John"

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self, model: HunyuanModel):
        """Test _get_client creates a new client when none exists"""
        client = await model._get_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        assert client.base_url == "https://api.hunyuan.cn"

        # Should return the same client on subsequent calls
        client2 = await model._get_client()
        assert client is client2

    @pytest.mark.asyncio
    async def test_close(self, model: HunyuanModel):
        """Test close method properly closes the client"""
        await model._get_client()
        assert model._client is not None

        await model.close()
        assert model._client is None

    @pytest.mark.asyncio
    async def test_generate_success(self, model: HunyuanModel):
        """Test generate method with successful response"""
        # Mock response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "choices": [
                    {
                        "message": {"content": "Hello! How can I help you?"},
                        "finish_reason": "stop",
                    }
                ],
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
            with patch("time.time", return_value=1234567890):
                messages = [Message(role="user", content="Hello")]
                response = await model.generate(messages)

        assert isinstance(response, ModelResponse)
        assert response.content == "Hello! How can I help you?"
        assert response.model == model.model_name
        assert response.provider == ModelProvider.HUNYUAN
        assert response.finish_reason == "stop"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20

    @pytest.mark.asyncio
    async def test_generate_with_tools(self, model: HunyuanModel):
        """Test generate with tools parameter"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "choices": [{"message": {"content": ""}, "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        )

        mock_client = AsyncMock()
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.post = mock_post

        with patch.object(model, "_get_client", return_value=mock_client):
            with patch("time.time", return_value=1234567890):
                messages = [Message(role="user", content="Hello")]
                await model.generate(
                    messages,
                    tools=[{"type": "function", "function": {"name": "get_weather"}}],
                )

        # Verify the request was made with tools
        call_args = mock_post.call_args
        payload = json.loads(call_args[1].get("content") or "{}")
        assert "tools" in payload

    @pytest.mark.asyncio
    async def test_generate_without_auth_when_no_credentials(self, config: ModelConfig):
        """Test generate works without auth when no secret_id/key provided"""
        model = HunyuanModel(config, tier=ModelTier.MEDIUM, secret_id=None, secret_key=None)

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            with patch("time.time", return_value=1234567890):
                messages = [Message(role="user", content="Hello")]
                response = await model.generate(messages)

        assert response.content == "Hello"

    @pytest.mark.asyncio
    async def test_generate_http_error(self, model: HunyuanModel):
        """Test generate handles HTTP errors"""
        mock_response = Mock()
        mock_response.status_code = 400

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "400 Bad Request", request=Mock(), response=mock_response
            )
        )

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello")]

            with pytest.raises(HunyuanAPIError) as exc_info:
                await model.generate(messages)

            assert "混元 API 错误" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_request_error(self, model: HunyuanModel):
        """Test generate handles network errors"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("Network error"))

        with patch.object(model, "_get_client", return_value=mock_client):
            messages = [Message(role="user", content="Hello")]

            with pytest.raises(HunyuanAPIError) as exc_info:
                await model.generate(messages)

            assert "网络请求失败" in str(exc_info.value)

    def test_hunyuan_api_error_exception(self):
        """Test HunyuanAPIError exception"""
        error = HunyuanAPIError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    @pytest.mark.asyncio
    async def test_generate_updates_usage(self, model: HunyuanModel):
        """Test that generate updates model usage statistics"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
            }
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            with patch("time.time", return_value=1234567890):
                messages = [Message(role="user", content="Hello")]
                await model.generate(messages)

        # Check that usage was updated
        total_usage = model.get_total_usage()
        assert total_usage.prompt_tokens == 100
        assert total_usage.completion_tokens == 50
        assert total_usage.total_tokens == 150

    @pytest.mark.asyncio
    async def test_generate_with_tool_calls_in_response(self, model: HunyuanModel):
        """Test generate handles tool_calls in response"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(
            return_value={
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {"name": "get_weather", "arguments": "{}"},
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(model, "_get_client", return_value=mock_client):
            with patch("time.time", return_value=1234567890):
                messages = [Message(role="user", content="Hello")]
                response = await model.generate(messages)

        assert len(response.tool_calls) > 0
        assert response.tool_calls[0]["id"] == "call_123"


# Cleanup
async def test_model_cleanup():
    """Test that model resources are properly cleaned up"""
    config = ModelConfig(api_key="test", timeout=30.0)
    model = HunyuanModel(config, secret_id="id", secret_key="key")
    # Mock the abstract stream method
    model.stream = AsyncMock()

    await model._get_client()
    assert model._client is not None

    await model.close()
    assert model._client is None
