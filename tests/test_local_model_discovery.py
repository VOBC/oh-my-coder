"""测试 local_model_discovery.py — 本地模型发现"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.local_model_discovery import (
    OllamaModelInfo,
    discover_ollama_models,
    discover_ollama_models_async,
    get_model_info,
    get_model_info_async,
    is_ollama_running,
    is_ollama_running_async,
)

# ===== OllamaModelInfo =====


class TestOllamaModelInfo:
    def test_size_gb(self):
        m = OllamaModelInfo(model_name="qwen2:7b", size=4_400_000_000)
        assert m.size_gb == 4.1

    def test_size_gb_zero(self):
        m = OllamaModelInfo(model_name="test", size=0)
        assert m.size_gb == 0.0

    def test_size_mb(self):
        m = OllamaModelInfo(model_name="test", size=1_000_000)
        assert m.size_mb > 0

    def test_size_mb_zero(self):
        m = OllamaModelInfo(model_name="test", size=-1)
        assert m.size_mb == 0.0

    def test_to_dict(self):
        m = OllamaModelInfo(
            model_name="qwen2:7b",
            size=100,
            quantization="q4_K_M",
            parameter_size="7B",
        )
        d = m.to_dict()
        assert d["model_name"] == "qwen2:7b"
        assert "raw" not in d
        assert d["size_gb"] == m.size_gb

    def test_defaults(self):
        m = OllamaModelInfo(model_name="test")
        assert m.size == 0
        assert m.quantization is None
        assert m.modified_at is None
        assert m.parameter_size is None
        assert m.template is None
        assert m.license is None
        assert m.system is None
        assert m.raw == {}

    def test_repr_no_raw(self):
        m = OllamaModelInfo(model_name="qwen2:7b", raw={"big": "data"})
        r = repr(m)
        assert "raw" not in r


# ===== is_ollama_running =====


def _mock_sync_client(method="get", status_code=200, json_data=None, side_effect=None):
    """Helper to create a mock sync httpx client."""
    mock_client = MagicMock()
    if side_effect:
        getattr(mock_client, method).side_effect = side_effect
    else:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        if json_data is not None:
            mock_response.json.return_value = json_data
        getattr(mock_client, method).return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


class TestIsOllamaRunning:
    @patch("src.core.local_model_discovery._make_client")
    def test_running(self, mock_make):
        mock_make.return_value = _mock_sync_client(status_code=200)
        assert is_ollama_running() is True

    @patch("src.core.local_model_discovery._make_client")
    def test_not_running(self, mock_make):
        mock_make.return_value = _mock_sync_client(status_code=503)
        assert is_ollama_running() is False

    @patch("src.core.local_model_discovery._make_client")
    def test_exception(self, mock_make):
        mock_make.return_value = _mock_sync_client(side_effect=Exception("timeout"))
        assert is_ollama_running() is False

    @patch("src.core.local_model_discovery._make_client")
    def test_custom_base_url(self, mock_make):
        mock_make.return_value = _mock_sync_client(status_code=200)
        assert is_ollama_running("http://custom:1234") is True
        mock_client = mock_make.return_value
        mock_client.get.assert_called_once_with("http://custom:1234/api/tags")


# ===== discover_ollama_models =====


class TestDiscoverOllamaModels:
    @patch("src.core.local_model_discovery._make_client")
    def test_success(self, mock_make):
        mock_make.return_value = _mock_sync_client(
            json_data={
                "models": [
                    {"name": "qwen2:7b", "size": 100, "modified_at": "2024-01-01"},
                    {"name": "llama3:8b", "size": 200, "modified_at": "2024-02-01"},
                ]
            }
        )
        models = discover_ollama_models()
        assert len(models) == 2
        assert models[0].model_name == "llama3:8b"

    @patch("src.core.local_model_discovery._make_client")
    def test_empty_name_filtered(self, mock_make):
        mock_make.return_value = _mock_sync_client(
            json_data={"models": [{"name": "", "size": 100}, {"name": "qwen2:7b", "size": 200}]}
        )
        assert len(discover_ollama_models()) == 1

    @patch("src.core.local_model_discovery._make_client")
    def test_non_200(self, mock_make):
        mock_make.return_value = _mock_sync_client(status_code=500)
        assert discover_ollama_models() == []

    @patch("src.core.local_model_discovery._make_client")
    def test_exception(self, mock_make):
        mock_make.return_value = _mock_sync_client(side_effect=Exception("err"))
        assert discover_ollama_models() == []

    @patch("src.core.local_model_discovery._make_client")
    def test_no_models_key(self, mock_make):
        mock_make.return_value = _mock_sync_client(json_data={})
        assert discover_ollama_models() == []

    @patch("src.core.local_model_discovery._make_client")
    def test_missing_fields(self, mock_make):
        mock_make.return_value = _mock_sync_client(
            json_data={"models": [{}]}  # no name key
        )
        # name defaults to "" which is filtered
        assert discover_ollama_models() == []


# ===== get_model_info =====


class TestGetModelInfo:
    def test_empty_name(self):
        assert get_model_info("") is None
        assert get_model_info("  ") is None

    @patch("src.core.local_model_discovery._make_client")
    def test_success(self, mock_make):
        mock_make.return_value = _mock_sync_client(
            method="post",
            status_code=200,
            json_data={
                "model_info": {"parameter_size": "7B", "quantization": "q4_K_M"},
                "template": "test template",
                "license": "MIT",
                "system": "You are helpful",
            },
        )
        info = get_model_info("qwen2:7b")
        assert info is not None
        assert info.parameter_size == "7B"
        assert info.quantization == "q4_K_M"
        assert info.template == "test template"
        assert info.license == "MIT"
        assert info.system == "You are helpful"

    @patch("src.core.local_model_discovery._make_client")
    def test_non_200(self, mock_make):
        mock_make.return_value = _mock_sync_client(method="post", status_code=404)
        assert get_model_info("nonexist") is None

    @patch("src.core.local_model_discovery._make_client")
    def test_exception(self, mock_make):
        mock_make.return_value = _mock_sync_client(method="post", side_effect=Exception("err"))
        assert get_model_info("test") is None

    @patch("src.core.local_model_discovery._make_client")
    def test_license_from_top_level(self, mock_make):
        mock_make.return_value = _mock_sync_client(
            method="post",
            json_data={"model_info": {}, "license": "Apache", "template": "tpl", "system": "sys"},
        )
        info = get_model_info("test")
        assert info.license == "Apache"

    @patch("src.core.local_model_discovery._make_client")
    def test_name_stripped(self, mock_make):
        mock_make.return_value = _mock_sync_client(
            method="post",
            json_data={"model_info": {}, "template": None, "license": None, "system": None},
        )
        info = get_model_info("  qwen2:7b  ")
        assert info.model_name == "qwen2:7b"


# ===== Async variants =====


def _mock_async_client(method="get", status_code=200, json_data=None, side_effect=None):
    """Helper to create a mock async httpx client."""
    mock_client = MagicMock()

    async_mock = AsyncMock()
    if side_effect:
        async_mock.side_effect = side_effect
    else:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        if json_data is not None:
            mock_response.json.return_value = json_data
        async_mock.return_value = mock_response

    setattr(mock_client, method, async_mock)
    mock_client.is_closed = False
    return mock_client


class TestIsOllamaRunningAsync:
    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_running(self, mock_get):
        mock_client = _mock_async_client(status_code=200)
        mock_get.return_value = mock_client
        assert await is_ollama_running_async() is True

    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_not_running(self, mock_get):
        mock_client = _mock_async_client(status_code=503)
        mock_get.return_value = mock_client
        assert await is_ollama_running_async() is False

    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_exception(self, mock_get):
        mock_client = _mock_async_client(side_effect=Exception("err"))
        mock_get.return_value = mock_client
        assert await is_ollama_running_async() is False


class TestDiscoverOllamaModelsAsync:
    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_success(self, mock_get):
        mock_client = _mock_async_client(
            json_data={
                "models": [
                    {"name": "qwen2:7b", "size": 100, "modified_at": "2024-01-01"},
                    {"name": "llama3:8b", "size": 200, "modified_at": "2024-02-01"},
                ]
            }
        )
        mock_get.return_value = mock_client
        models = await discover_ollama_models_async()
        assert len(models) == 2
        assert models[0].model_name == "llama3:8b"

    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_non_200(self, mock_get):
        mock_client = _mock_async_client(status_code=500)
        mock_get.return_value = mock_client
        assert await discover_ollama_models_async() == []

    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_exception(self, mock_get):
        mock_client = _mock_async_client(side_effect=Exception("err"))
        mock_get.return_value = mock_client
        assert await discover_ollama_models_async() == []

    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_empty_name_filtered(self, mock_get):
        mock_client = _mock_async_client(
            json_data={"models": [{"name": "", "size": 100}, {"name": "qwen2:7b", "size": 200}]}
        )
        mock_get.return_value = mock_client
        models = await discover_ollama_models_async()
        assert len(models) == 1


class TestGetModelInfoAsync:
    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_empty_name(self, mock_get):
        assert await get_model_info_async("") is None
        assert await get_model_info_async("  ") is None

    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_success(self, mock_get):
        mock_client = _mock_async_client(
            method="post",
            json_data={
                "model_info": {"parameter_size": "7B", "quantization": "q4_K_M"},
                "template": "tpl",
                "license": "MIT",
                "system": "sys",
            },
        )
        mock_get.return_value = mock_client
        info = await get_model_info_async("qwen2:7b")
        assert info is not None
        assert info.parameter_size == "7B"

    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_non_200(self, mock_get):
        mock_client = _mock_async_client(method="post", status_code=404)
        mock_get.return_value = mock_client
        assert await get_model_info_async("nonexist") is None

    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_exception(self, mock_get):
        mock_client = _mock_async_client(method="post", side_effect=Exception("err"))
        mock_get.return_value = mock_client
        assert await get_model_info_async("test") is None

    @pytest.mark.asyncio
    @patch("src.core.local_model_discovery._get_async_client")
    async def test_license_from_top_level(self, mock_get):
        mock_client = _mock_async_client(
            method="post",
            json_data={"model_info": {}, "license": "Apache", "template": "tpl", "system": "sys"},
        )
        mock_get.return_value = mock_client
        info = await get_model_info_async("test")
        assert info.license == "Apache"
