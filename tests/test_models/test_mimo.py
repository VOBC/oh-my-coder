"""
测试 MiMo 模型适配器（mock API）

运行: pytest tests/test_models/test_mimo.py -v
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, "/Users/vobc/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder")

from src.models.base import Message, ModelConfig, ModelProvider, ModelTier
from src.models.mimo import MimoModel


class TestMimoModelInit:
    """测试 MiMo 模型初始化"""

    def test_default_base_url(self):
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config)
        assert "api.xiaomimimo.com" in config.base_url

    def test_custom_base_url(self):
        config = ModelConfig(api_key="test_key", base_url="https://custom.api.com/v1")
        model = MimoModel(config)
        assert config.base_url == "https://custom.api.com/v1"

    def test_tier_low(self):
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config, ModelTier.LOW)
        assert model.model_name == "mimo-v2-flash"
        assert model.tier == ModelTier.LOW

    def test_tier_medium(self):
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config, ModelTier.MEDIUM)
        assert model.model_name == "mimo-v2-flash"
        assert model.tier == ModelTier.MEDIUM

    def test_tier_high(self):
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config, ModelTier.HIGH)
        assert model.model_name == "mimo-v2-pro"
        assert model.tier == ModelTier.HIGH

    def test_provider(self):
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config)
        assert model.provider == ModelProvider.MIMO


class TestMimoFormatMessages:
    """测试消息格式化"""

    def test_format_system_and_user(self):
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config)
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
        model = MimoModel(config)
        messages = [Message(role="user", content="Hi", name="Alice")]
        formatted = model._format_messages(messages)
        assert formatted[0]["name"] == "Alice"

    def test_format_multiple_messages(self):
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config)
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]
        formatted = model._format_messages(messages)
        assert len(formatted) == 4


class TestMimoGenerate:
    """测试非流式生成"""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "mimo-test-123",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello, I am MiMo!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

        with patch.object(model, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            messages = [Message(role="user", content="Hi")]
            response = await model.generate(messages)

            assert response.content == "Hello, I am MiMo!"
            assert response.model == "mimo-v2-flash"
            assert response.provider == ModelProvider.MIMO

    @pytest.mark.asyncio
    async def test_generate_with_tools(self):
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "mimo-test-456",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "I'll use the tool for you.",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"city": "Beijing"}',
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

        with patch.object(model, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            messages = [Message(role="user", content="What's the weather in Beijing?")]
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather for a city",
                        "parameters": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                            "required": ["city"],
                        },
                    },
                }
            ]
            response = await model.generate(messages, tools=tools)

            assert "tool_calls" in response.metadata
            assert (
                response.metadata["tool_calls"][0]["function"]["name"] == "get_weather"
            )


class TestMimoStream:
    """测试流式生成"""

    @pytest.mark.asyncio
    async def test_stream_success(self):
        model = MimoModel(ModelConfig(api_key="test_key"))

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


class TestMimoError:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_api_error(self):
        config = ModelConfig(api_key="test_key")
        model = MimoModel(config)

        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Invalid API key"}}

        with patch.object(model, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("HTTP 401")
            mock_get_client.return_value = mock_client

            messages = [Message(role="user", content="Hi")]
            with pytest.raises(Exception):
                await model.generate(messages)
