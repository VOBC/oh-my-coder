"""
测试 GLM 模型适配器（mock API）

运行: pytest tests/test_models/test_glm.py -v
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import pytest

sys.path.insert(0, "/Users/vobc/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder")

from src.models.base import Message, ModelConfig, ModelProvider, ModelTier
from src.models.glm import GLMAPIError, GLMModel


class TestGLMModelInit:
    """测试 GLM 模型初始化"""

    def test_default_base_url(self):
        config = ModelConfig(api_key="test_key")
        GLMModel(config)  # 初始化验证
        # 安全检查：使用 urlparse 验证域名，而非 in 操作符
        assert urlparse(config.base_url).netloc.endswith("bigmodel.cn")

    def test_all_tiers(self):
        config = ModelConfig(api_key="test_key")
        for tier in [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH]:
            model = GLMModel(config, tier=tier)
            assert model.tier == tier
            assert model.provider == ModelProvider.GLM


class TestGLMFormatMessages:
    """测试消息格式化"""

    def test_format_messages(self):
        config = ModelConfig(api_key="test_key")
        model = GLMModel(config)
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi"),
        ]
        formatted = model._format_messages(messages)
        assert len(formatted) == 3
        assert formatted[0]["role"] == "system"
        assert formatted[2]["role"] == "assistant"


class TestGLMGenerate:
    """测试 generate 方法"""

    def _mock_response(self, content: str, tokens: int = 30):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "id": "glm-test-001",
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
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    @pytest.mark.asyncio
    async def test_generate_success(self):
        model = GLMModel(ModelConfig(api_key="test_key"))
        mock_resp = self._mock_response("GLM response content")

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = client

            response = await model.generate([Message(role="user", content="Hello")])

        assert response.content == "GLM response content"
        assert response.provider == ModelProvider.GLM
        assert response.usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_generate_with_tools(self):
        model = GLMModel(ModelConfig(api_key="test_key"))
        mock_resp = self._mock_response("使用工具完成")

        tools = [{"type": "function", "function": {"name": "get_weather"}}]

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = client

            response = await model.generate(
                [Message(role="user", content="天气如何")],
                tools=tools,
            )
        assert response.provider == ModelProvider.GLM

    @pytest.mark.asyncio
    async def test_generate_http_error(self):
        model = GLMModel(ModelConfig(api_key="bad_key"))
        import httpx

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "403 Forbidden",
                    request=MagicMock(),
                    response=MagicMock(status_code=403),
                )
            )
            mock_get.return_value = client

            with pytest.raises(GLMAPIError):
                await model.generate([Message(role="user", content="Hello")])


class TestGLMStream:
    """测试流式生成"""

    @pytest.mark.asyncio
    async def test_stream(self):
        model = GLMModel(ModelConfig(api_key="test_key"))

        async def fake_lines():
            yield 'data: {"choices":[{"delta":{"content":"Chunk1"}}]}'
            yield 'data: {"choices":[{"delta":{"content":"Chunk2"}}]}'
            yield "data: [DONE]"

        mock_ctx = MagicMock()

        async def enter_async():
            mock_stream = MagicMock()
            mock_stream.raise_for_status = MagicMock()
            mock_stream.aiter_lines = fake_lines
            return mock_stream

        mock_ctx.__aenter__ = AsyncMock(side_effect=enter_async)

        with patch.object(model, "_get_client") as mock_get:
            client = AsyncMock()
            client.stream = MagicMock(return_value=mock_ctx)
            mock_get.return_value = client

            chunks = [
                c async for c in model.stream([Message(role="user", content="Hi")])
            ]

        assert "".join(chunks) == "Chunk1Chunk2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
