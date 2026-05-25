"""Tests for src/models/ollama.py"""

import json
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.models.base import Message, ModelTier
from src.models.ollama import (
    _MODEL_TIER_MAP,
    OLLAMA_DEFAULT_URL,
    OLLAMA_MODELS,
    OllamaModel,
    create_ollama_model,
)

# ============================================================================
# 1. 模块级数据结构测试
# ============================================================================


def test_ollama_models_has_all_tiers():
    """验证 OLLAMA_MODELS 字典包含所有三个层级"""
    assert ModelTier.LOW in OLLAMA_MODELS
    assert ModelTier.MEDIUM in OLLAMA_MODELS
    assert ModelTier.HIGH in OLLAMA_MODELS


def test_ollama_models_each_tier_has_models():
    """验证每个层级都有模型列表"""
    for tier in [ModelTier.LOW, ModelTier.MEDIUM, ModelTier.HIGH]:
        models = OLLAMA_MODELS[tier]
        assert isinstance(models, list)
        assert len(models) > 0
        # 每个模型都应有 name, desc, context 字段
        for m in models:
            assert "name" in m
            assert "desc" in m
            assert "context" in m


def test_model_tier_map_key_models():
    """验证关键模型的 tier 映射正确"""
    # LOW tier
    assert _MODEL_TIER_MAP.get("llama3:8b") == ModelTier.LOW
    assert _MODEL_TIER_MAP.get("mistral:7b") == ModelTier.LOW

    # MEDIUM tier
    assert _MODEL_TIER_MAP.get("qwen2:7b") == ModelTier.MEDIUM
    assert _MODEL_TIER_MAP.get("deepseek-coder:6.7b") == ModelTier.MEDIUM

    # HIGH tier
    assert _MODEL_TIER_MAP.get("qwen2:72b") == ModelTier.HIGH
    assert _MODEL_TIER_MAP.get("llama3:70b") == ModelTier.HIGH
    assert _MODEL_TIER_MAP.get("mixtral:8x7b") == ModelTier.HIGH


def test_model_tier_map_consistency():
    """验证 _MODEL_TIER_MAP 与 OLLAMA_MODELS 一致"""
    total_models = sum(len(models) for models in OLLAMA_MODELS.values())
    assert len(_MODEL_TIER_MAP) == total_models


# ============================================================================
# 2. OllamaModel 类测试
# ============================================================================


def test_ollama_model_init_with_default_config():
    """测试默认配置初始化"""
    # 使用 create_ollama_model 工厂函数来避免抽象类实例化问题
    model = create_ollama_model(model_name="qwen2:7b")

    assert model.model_name == "qwen2:7b"
    assert model.base_url == OLLAMA_DEFAULT_URL
    assert model.config.provider == "ollama"
    assert model.tier == ModelTier.MEDIUM  # qwen2:7b 应映射到 MEDIUM


def test_ollama_model_init_auto_tier_inference():
    """测试 tier 自动推断"""
    # LOW tier 模型
    model_low = create_ollama_model(model_name="llama3:8b")
    assert model_low.tier == ModelTier.LOW

    # HIGH tier 模型
    model_high = create_ollama_model(model_name="qwen2:72b")
    assert model_high.tier == ModelTier.HIGH


def test_ollama_model_init_with_custom_base_url():
    """测试自定义 base_url"""
    model = create_ollama_model(
        model_name="qwen2:7b",
        base_url="http://192.168.1.100:11434"
    )

    assert model.base_url == "http://192.168.1.100:11434"


def test_ollama_model_init_base_url_trailing_slash():
    """测试 base_url 尾部斜杠处理"""
    model = create_ollama_model(
        model_name="qwen2:7b",
        base_url="http://localhost:11434/"
    )

    assert model.base_url == "http://localhost:11434"


@pytest.mark.asyncio
async def test_ollama_model_get_client():
    """测试 _get_client 返回正确的 client"""
    model = create_ollama_model(model_name="qwen2:7b")

    client = await model._get_client()

    assert isinstance(client, httpx.AsyncClient)
    assert not client.is_closed

    # 清理
    await model.close()


@pytest.mark.asyncio
async def test_ollama_model_get_client_reuse():
    """测试 _get_client 复用 client"""
    model = create_ollama_model(model_name="qwen2:7b")

    client1 = await model._get_client()
    client2 = await model._get_client()

    assert client1 is client2

    await model.close()


@pytest.mark.asyncio
async def test_ollama_model_complete():
    """测试 complete 方法"""
    model = create_ollama_model(model_name="qwen2:7b")

    messages = [Message(role="user", content="Hello")]

    # Mock _generate 方法
    with patch.object(
        model,
        "_generate",
        new_callable=AsyncMock,
    ) as mock_generate:
        from src.models.base import ModelResponse, Usage

        mock_response = ModelResponse(
            content="Hi there!",
            model="qwen2:7b",
            provider="ollama",
            tier=ModelTier.MEDIUM,
            usage=Usage(),
        )
        mock_generate.return_value = mock_response

        result = await model.complete(messages)

        mock_generate.assert_called_once_with(messages, stream=False)
        assert result.content == "Hi there!"


@pytest.mark.asyncio
async def test_ollama_model_stream():
    """测试 stream 方法"""
    model = create_ollama_model(model_name="qwen2:7b")

    messages = [Message(role="user", content="Hello")]

    # Mock _generate_stream 方法
    async def mock_stream(*args, **kwargs):
        yield "Hello"
        yield " "
        yield "there!"

    with patch.object(model, "_generate_stream", side_effect=mock_stream):
        chunks = []
        async for chunk in model.stream(messages):
            chunks.append(chunk)

        assert chunks == ["Hello", " ", "there!"]


def test_ollama_model_repr():
    """测试 __repr__ 方法"""
    model = create_ollama_model(model_name="qwen2:72b")

    repr_str = repr(model)

    assert "qwen2:72b" in repr_str
    assert "high" in repr_str
    assert "OllamaModel" in repr_str


# ============================================================================
# 3. 静态方法测试
# ============================================================================


@patch("httpx.get")
def test_is_available_returns_true_on_200(mock_get):
    """测试 is_available 返回 True（状态码 200）"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    result = OllamaModel.is_available("http://localhost:11434")

    assert result is True
    mock_get.assert_called_once()


@patch("httpx.get")
def test_is_available_returns_false_on_error(mock_get):
    """测试 is_available 返回 False（异常）"""
    mock_get.side_effect = httpx.ConnectError("Connection failed")

    result = OllamaModel.is_available("http://localhost:11434")

    assert result is False


@patch("httpx.get")
def test_is_available_returns_false_on_non_200(mock_get):
    """测试 is_available 返回 False（非 200 状态码）"""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response

    result = OllamaModel.is_available("http://localhost:11434")

    assert result is False


@patch("httpx.get")
def test_list_models_returns_models_on_success(mock_get):
    """测试 list_models 返回模型列表"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": "qwen2:7b", "size": 4000000000},
            {"name": "llama3:8b", "size": 5000000000},
        ]
    }
    mock_get.return_value = mock_response

    result = OllamaModel.list_models("http://localhost:11434")

    assert len(result) == 2
    assert result[0]["name"] == "qwen2:7b"


@patch("httpx.get")
def test_list_models_returns_empty_on_non_200(mock_get):
    """测试 list_models 返回空列表（非 200）"""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response

    result = OllamaModel.list_models("http://localhost:11434")

    assert result == []


@patch("httpx.get")
def test_list_models_returns_empty_on_error(mock_get):
    """测试 list_models 返回空列表（异常）"""
    mock_get.side_effect = Exception("Network error")

    result = OllamaModel.list_models("http://localhost:11434")

    assert result == []


@patch("subprocess.run")
def test_pull_model_returns_true_on_success(mock_run):
    """测试 pull_model 返回 True"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    result = OllamaModel.pull_model("qwen2:7b")

    assert result is True
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args == ["ollama", "pull", "qwen2:7b"]


@patch("subprocess.run")
def test_pull_model_returns_false_on_failure(mock_run):
    """测试 pull_model 返回 False（非零返回码）"""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_run.return_value = mock_result

    result = OllamaModel.pull_model("qwen2:7b")

    assert result is False


@patch("subprocess.run")
def test_pull_model_returns_false_on_timeout(mock_run):
    """测试 pull_model 返回 False（超时）"""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="ollama", timeout=600)

    result = OllamaModel.pull_model("qwen2:7b")

    assert result is False


@patch("subprocess.run")
def test_pull_model_returns_false_on_exception(mock_run):
    """测试 pull_model 返回 False（异常）"""
    mock_run.side_effect = Exception("Unexpected error")

    result = OllamaModel.pull_model("qwen2:7b")

    assert result is False


# ============================================================================
# 4. create_ollama_model 工厂函数测试
# ============================================================================


def test_create_ollama_model_auto_tier():
    """测试不传 tier 时自动推断"""
    model = create_ollama_model(model_name="qwen2:72b")

    assert isinstance(model, OllamaModel)
    assert model.model_name == "qwen2:72b"
    assert model.tier == ModelTier.HIGH


def test_create_ollama_model_explicit_tier():
    """测试显式传入 tier 覆盖自动推断"""
    # qwen2:72b 默认是 HIGH，显式传入 LOW 应覆盖
    model = create_ollama_model(
        model_name="qwen2:72b",
        tier=ModelTier.LOW
    )

    # 注意：OllamaModel.__init__ 只会在传入默认 MEDIUM 时才自动推断
    # 显式传入 LOW 时不会覆盖
    assert model.tier == ModelTier.LOW


def test_create_ollama_model_custom_base_url():
    """测试自定义 base_url"""
    model = create_ollama_model(
        model_name="qwen2:7b",
        base_url="http://192.168.1.100:11434"
    )

    assert model.base_url == "http://192.168.1.100:11434"


def test_create_ollama_model_unknown_model_defaults_to_medium():
    """测试未知模型默认为 MEDIUM tier"""
    model = create_ollama_model(model_name="unknown-model")

    assert model.tier == ModelTier.MEDIUM


# ============================================================================
# 5. _generate 和 _generate_stream 测试（带 mock）
# ============================================================================


@pytest.mark.asyncio
async def test_generate_success():
    """测试 _generate 成功调用"""
    model = create_ollama_model(model_name="qwen2:7b")

    messages = [Message(role="user", content="Hello")]

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": "Hi there!"},
        "model": "qwen2:7b",
        "eval_count": 10,
        "prompt_eval_count": 5,
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch.object(model, "_get_client", return_value=mock_client):
        result = await model._generate(messages, stream=False)

        assert result.content == "Hi there!"
        assert result.model == "qwen2:7b"
        assert result.usage.prompt_tokens == 5
        assert result.usage.completion_tokens == 10


@pytest.mark.asyncio
async def test_generate_stream_success():
    """测试 _generate_stream 成功调用"""
    model = create_ollama_model(model_name="qwen2:7b")

    messages = [Message(role="user", content="Hello")]

    # 模拟流式响应
    async def mock_aiter_lines():
        lines = [
            json.dumps({"message": {"content": "Hello"}}),
            json.dumps({"message": {"content": " there"}}),
            json.dumps({"message": {"content": "!"}}),
        ]
        for line in lines:
            yield line

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aiter_lines = mock_aiter_lines

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.stream = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_response)))

    with patch.object(model, "_get_client", return_value=mock_client):
        chunks = []
        async for chunk in model._generate_stream(messages):
            chunks.append(chunk)

        assert chunks == ["Hello", " there", "!"]
