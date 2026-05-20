"""测试 ollama_health.py — Ollama 健康检查"""

from datetime import datetime
from unittest.mock import MagicMock, patch

from src.core.ollama_health import (
    _CACHE_TTL_SECONDS,
    OllamaHealthChecker,
    OllamaHealthStatus,
)

# ===== OllamaHealthStatus =====


class TestOllamaHealthStatus:
    def test_defaults(self):
        s = OllamaHealthStatus()
        assert s.running is False
        assert s.version is None
        assert s.model_count == 0
        assert s.available_models == []

    def test_to_dict(self):
        s = OllamaHealthStatus(
            running=True,
            version="0.1.45",
            model_count=3,
            available_models=["qwen2:7b", "llama3:8b", "codellama"],
            latency_ms=50.123,
            last_check_time=datetime(2026, 1, 1, 12, 0),
        )
        d = s.to_dict()
        assert d["running"] is True
        assert d["version"] == "0.1.45"
        assert d["latency_ms"] == 50.12
        assert d["last_check_time"] == "2026-01-01T12:00:00"

    def test_to_dict_none_time(self):
        s = OllamaHealthStatus()
        d = s.to_dict()
        assert d["last_check_time"] is None


# ===== OllamaHealthChecker =====


class TestOllamaHealthChecker:
    def test_init_defaults(self):
        c = OllamaHealthChecker()
        assert c.cache_ttl == _CACHE_TTL_SECONDS

    def test_init_custom(self):
        c = OllamaHealthChecker(
            base_url="http://custom:1234",
            cache_ttl=60,
            connect_timeout=5,
            read_timeout=10,
        )
        assert c.base_url == "http://custom:1234"
        assert c.cache_ttl == 60

    def test_base_url_trailing_slash(self):
        c = OllamaHealthChecker(base_url="http://host:11434/")
        assert c.base_url == "http://host:11434"

    @patch("src.core.ollama_health.is_ollama_running", return_value=False)
    def test_check_not_running(self, mock_running):
        c = OllamaHealthChecker()
        status = c.check_ollama()
        assert status.running is False
        assert status.version is None

    @patch("src.core.ollama_health.discover_ollama_models", return_value=[])
    @patch("src.core.ollama_health.is_ollama_running", return_value=True)
    @patch.object(OllamaHealthChecker, "_fetch_version", return_value="0.1.45")
    def test_check_running(self, mock_version, mock_running, mock_discover):
        c = OllamaHealthChecker()
        status = c.check_ollama()
        assert status.running is True
        assert status.version == "0.1.45"
        assert status.model_count == 0

    def test_cache_hit(self):
        cached = OllamaHealthStatus(running=True, version="0.1.45")
        c = OllamaHealthChecker()
        c._cached_status = cached
        c._cache_timestamp = 0.0  # will expire, but let's set fresh
        import time
        c._cache_timestamp = time.monotonic()
        result = c.check_ollama()
        assert result.running is True
        assert result.version == "0.1.45"

    def test_clear_cache(self):
        c = OllamaHealthChecker()
        c._cached_status = OllamaHealthStatus(running=True)
        c._cache_timestamp = 100.0
        c.clear_cache()
        assert c._cached_status is None
        assert c._cache_timestamp == 0.0

    @patch("src.core.ollama_health.is_ollama_running", return_value=False)
    def test_check_model_available_not_running(self, mock_running):
        c = OllamaHealthChecker()
        assert not c.check_model_available("qwen2:7b")

    def test_check_model_available_empty_name(self):
        c = OllamaHealthChecker()
        c._cached_status = OllamaHealthStatus(running=True, available_models=["qwen2:7b"])
        import time
        c._cache_timestamp = time.monotonic()
        assert not c.check_model_available("")
        assert not c.check_model_available("   ")

    def test_check_model_available_found(self):
        c = OllamaHealthChecker()
        c._cached_status = OllamaHealthStatus(
            running=True, available_models=["qwen2:7b", "llama3:8b"]
        )
        import time
        c._cache_timestamp = time.monotonic()
        assert c.check_model_available("qwen2:7b")
        assert c.check_model_available("  llama3:8b  ")

    def test_check_model_available_not_found(self):
        c = OllamaHealthChecker()
        c._cached_status = OllamaHealthStatus(
            running=True, available_models=["qwen2:7b"]
        )
        import time
        c._cache_timestamp = time.monotonic()
        assert not c.check_model_available("gpt-4")

    def test_get_ollama_status(self):
        c = OllamaHealthChecker()
        c._cached_status = OllamaHealthStatus(
            running=True, version="0.1.45", model_count=2,
            available_models=["qwen2:7b", "llama3:8b"],
        )
        import time
        c._cache_timestamp = time.monotonic()
        d = c.get_ollama_status()
        assert d["running"] is True
        assert d["model_count"] == 2

    def test_fetch_version_success(self):
        c = OllamaHealthChecker()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "0.5.0"}
        with patch.object(c, "_get_client") as mock_client_get:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_get.return_value = mock_client
            version = c._fetch_version()
            assert version == "0.5.0"

    def test_fetch_version_failure(self):
        c = OllamaHealthChecker()
        mock_response = MagicMock()
        mock_response.status_code = 500
        with patch.object(c, "_get_client") as mock_client_get:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_get.return_value = mock_client
            assert c._fetch_version() is None

    def test_fetch_version_exception(self):
        c = OllamaHealthChecker()
        with patch.object(c, "_get_client") as mock_client_get:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("connection failed")
            mock_client_get.return_value = mock_client
            assert c._fetch_version() is None

    def test_get_client_creates_new(self):
        c = OllamaHealthChecker()
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.is_closed = False
            mock_client_cls.return_value = mock_client
            client = c._get_client()
            assert client is mock_client

    def test_context_manager(self):
        with OllamaHealthChecker() as c:
            assert c is not None
        # client should be closed after exit

    def test_close(self):
        c = OllamaHealthChecker()
        mock_client = MagicMock()
        mock_client.is_closed = False
        c._client = mock_client
        c.close()
        assert c._client is None

    def test_close_no_client(self):
        c = OllamaHealthChecker()
        c.close()  # should not error
