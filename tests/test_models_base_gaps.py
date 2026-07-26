"""Tests for coverage gaps in src/models/base.py"""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.models.base import (
    BaseModel,
    Message,
    ModelConfig,
    ModelProvider,
    ModelResponse,
    ModelTier,
    Usage,
)


class ConcreteModel(BaseModel):
    def __init__(self, config, tier):
        super().__init__(config, tier)
        self._provider = ModelProvider.DEEPSEEK
        self._model_name = "deepseek-chat"

    @property
    def provider(self):
        return self._provider

    @property
    def model_name(self):
        return self._model_name

    async def generate(self, messages, **kwargs):
        return ModelResponse(
            content="test response", model=self.model_name,
            provider=self.provider, tier=self.tier,
        )

    async def stream(self, messages, **kwargs):
        yield "chunk1"
        yield "chunk2"


@pytest.fixture
def model_config():
    return ModelConfig(
        api_key="sk-test", base_url="https://api.deepseek.com",
        model_name="deepseek-chat", timeout=30.0, max_retries=3, retry_delay=0.01,
    )


@pytest.fixture
def concrete_model(model_config):
    return ConcreteModel(model_config, ModelTier.MEDIUM)


# Lines 139-149: _get_client creates new client
class TestGetClient:
    @pytest.mark.asyncio
    async def test_creates_new(self, concrete_model):
        assert concrete_model._client is None
        client = await concrete_model._get_client()
        assert client is not None
        assert concrete_model._client is client

    @pytest.mark.asyncio
    async def test_reuses(self, concrete_model):
        client1 = await concrete_model._get_client()
        client2 = await concrete_model._get_client()
        assert client2 is client1

    @pytest.mark.asyncio
    async def test_headers(self, concrete_model):
        client = await concrete_model._get_client()
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer sk-test"




# Lines 238, 240, 242: usage tracking
class TestUsageTracking:
    def test_update(self, concrete_model):
        concrete_model.update_usage(Usage(prompt_tokens=100, completion_tokens=50))
        total = concrete_model.get_total_usage()
        assert total.prompt_tokens == 100

    def test_reset(self, concrete_model):
        concrete_model.update_usage(Usage(prompt_tokens=100))
        concrete_model.reset_usage()
        assert concrete_model.get_total_usage().total_tokens == 0


# Lines 248-250: _format_messages
class TestFormatMessages:
    def test_tool_calls(self, concrete_model):
        msg = Message(role="assistant", content="x",
                      tool_calls=[{"id": "c1", "type": "function",
                                   "function": {"name": "f", "arguments": "{}"}}])
        fmt = concrete_model._format_messages([msg])
        assert "tool_calls" in fmt[0]
        assert fmt[0]["tool_calls"][0]["id"] == "c1"

    def test_tool_call_id(self, concrete_model):
        msg = Message(role="tool", content="r", tool_call_id="c1")
        fmt = concrete_model._format_messages([msg])
        assert fmt[0]["tool_call_id"] == "c1"

    def test_name_field(self, concrete_model):
        msg = Message(role="user", content="hi", name="Alice")
        fmt = concrete_model._format_messages([msg])
        assert fmt[0]["name"] == "Alice"


# Lines 260-276, 269, 271: _build_request_body
class TestBuildRequestBody:
    def test_basic(self, concrete_model):
        msgs = [Message(role="user", content="hi")]
        body = concrete_model._build_request_body(msgs)
        assert body["model"] == "deepseek-chat"
        assert body["max_tokens"] == 4096

    def test_top_p(self, concrete_model):
        msgs = [Message(role="user", content="hi")]
        body = concrete_model._build_request_body(msgs, top_p=0.9)
        assert body["top_p"] == 0.9

    def test_stop(self, concrete_model):
        msgs = [Message(role="user", content="hi")]
        body = concrete_model._build_request_body(msgs, stop=["END"])
        assert body["stop"] == ["END"]

    def test_tools(self, concrete_model):
        msgs = [Message(role="user", content="hi")]
        tools = [{"type": "function", "function": {"name": "t", "parameters": {}}}]
        body = concrete_model._build_request_body(msgs, tools=tools)
        assert body["tools"] == tools
        assert body["tool_choice"] == "auto"

    def test_tools_custom_choice(self, concrete_model):
        msgs = [Message(role="user", content="hi")]
        tools = [{"type": "function", "function": {"name": "t", "parameters": {}}}]
        body = concrete_model._build_request_body(msgs, tools=tools, tool_choice="none")
        assert body["tool_choice"] == "none"

    def test_override_max_tokens(self, concrete_model):
        msgs = [Message(role="user", content="hi")]
        body = concrete_model._build_request_body(msgs, max_tokens=8000)
        assert body["max_tokens"] == 8000


# Lines 286-287: _parse_response
class TestParseResponse:
    @pytest.mark.asyncio
    async def test_success(self, concrete_model):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        result = await concrete_model._parse_response(mock_resp)
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_raises(self, concrete_model):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rate limited", request=MagicMock(), response=mock_resp
        )
        with pytest.raises(httpx.HTTPStatusError):
            await concrete_model._parse_response(mock_resp)


# Lines 294-330: _execute_with_retry
# Patch tenacity sleep to instant so retries don't hang tests
class TestExecuteWithRetry:
    @pytest.mark.asyncio
    async def test_first_success(self, concrete_model):
        mock_fn = AsyncMock(return_value="ok")
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await concrete_model._execute_with_retry(mock_fn)
        assert result == "ok"
        mock_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_then_success(self, concrete_model):
        mock_fn = AsyncMock(
            side_effect=[ConnectionError("e1"), ConnectionError("e2"), "ok"]
        )
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await concrete_model._execute_with_retry(mock_fn)
        assert result == "ok"
        assert mock_fn.call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_propagates(self, concrete_model):
        mock_fn = AsyncMock(side_effect=ValueError("bad"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ValueError):
                await concrete_model._execute_with_retry(mock_fn)
        assert mock_fn.call_count == 1

    @pytest.mark.asyncio
    async def test_read_timeout_retry(self, concrete_model):
        mock_fn = AsyncMock(side_effect=[httpx.ReadTimeout("read timeout"), "ok"])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            assert await concrete_model._execute_with_retry(mock_fn) == "ok"

    @pytest.mark.asyncio
    async def test_remote_protocol_error_retry(self, concrete_model):
        mock_fn = AsyncMock(side_effect=[httpx.RemoteProtocolError(message="p", request=None), "ok"])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            assert await concrete_model._execute_with_retry(mock_fn) == "ok"

    @pytest.mark.asyncio
    async def test_connect_error_retry(self, concrete_model):
        mock_fn = AsyncMock(side_effect=[httpx.ConnectError("c"), "ok"])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            assert await concrete_model._execute_with_retry(mock_fn) == "ok"

    @pytest.mark.asyncio
    async def test_oserror_retry(self, concrete_model):
        mock_fn = AsyncMock(side_effect=[OSError("o"), "ok"])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            assert await concrete_model._execute_with_retry(mock_fn) == "ok"

    @pytest.mark.asyncio
    async def test_timeout_error_retry(self, concrete_model):
        mock_fn = AsyncMock(side_effect=[TimeoutError("t"), "ok"])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            assert await concrete_model._execute_with_retry(mock_fn) == "ok"

    @pytest.mark.asyncio
    async def test_all_exhausted(self, concrete_model):
        mock_fn = AsyncMock(side_effect=httpx.ReadTimeout("read timeout"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.ReadTimeout):
                await concrete_model._execute_with_retry(mock_fn)
        assert mock_fn.call_count == 3


# Line 373: close
class TestClose:
    @pytest.mark.asyncio
    async def test_close_closes(self, concrete_model):
        client = await concrete_model._get_client()
        client.aclose = AsyncMock()
        await concrete_model.close()
        assert concrete_model._client is None

    @pytest.mark.asyncio
    async def test_close_no_client(self, concrete_model):
        assert concrete_model._client is None
        await concrete_model.close()
        assert concrete_model._client is None


# Additional dataclass coverage
class TestModelConfig:
    def test_defaults(self):
        c = ModelConfig()
        assert c.max_tokens == 4096
        assert c.timeout == 120.0
        assert c.max_retries == 5

    def test_cost(self):
        c = ModelConfig(cost_per_1k_prompt=0.001, cost_per_1k_completion=0.002)
        assert c.cost_per_1k_prompt == 0.001


class TestMessage:
    def test_all_fields(self):
        m = Message(role="a", content="b", name="n",
                    tool_calls=[{"id": "c1"}], tool_call_id="c1")
        assert m.name == "n"
        assert m.tool_calls[0]["id"] == "c1"
        assert m.tool_call_id == "c1"


class TestUsage:
    def test_add(self):
        u = Usage(prompt_tokens=100) + Usage(completion_tokens=50)
        assert u.prompt_tokens == 100
        assert u.completion_tokens == 50


class TestModelResponse:
    def test_all_fields(self):
        r = ModelResponse(
            content="c", model="m", provider=ModelProvider.OLLAMA, tier=ModelTier.HIGH,
            usage=Usage(100, 50), latency_ms=200.0, metadata={"k": "v"},
            tool_calls=[{"id": "c1"}]
        )
        assert r.latency_ms == 200.0
        assert r.metadata["k"] == "v"

    def test_defaults(self):
        r = ModelResponse(content="c", model="m",
                          provider=ModelProvider.OPENAI, tier=ModelTier.LOW)
        assert r.latency_ms == 0.0


class TestGetCost:
    def test_zero(self, concrete_model):
        assert concrete_model.get_cost(Usage(1000, 500)) == 0.0

    def test_with_costs(self, model_config):
        model_config.cost_per_1k_prompt = 0.001
        model_config.cost_per_1k_completion = 0.002
        model = ConcreteModel(model_config, ModelTier.MEDIUM)
        cost = model.get_cost(Usage(1000, 500))
        assert cost == 0.002


class TestBuildSystemPrompt:
    def test_with_content(self, concrete_model):
        msg = concrete_model._build_system_prompt("act as helpful")
        assert msg is not None
        assert msg.role == "system"

    def test_without_content(self, concrete_model):
        assert concrete_model._build_system_prompt(None) is None


class TestStream:
    @pytest.mark.asyncio
    async def test_stream(self, concrete_model):
        chunks = []
        async for c in concrete_model.stream([Message(role="u", content="hi")]):
            chunks.append(c)
        assert len(chunks) == 2


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate(self, concrete_model):
        r = await concrete_model.generate([Message(role="u", content="hi")])
        assert r.content == "test response"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
