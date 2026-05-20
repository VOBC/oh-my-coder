"""Tests for src/model_discovery.py"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.model_discovery import ModelDiscovery, get_discovery_summary


@pytest.fixture
def discovery(tmp_path):
    d = ModelDiscovery()
    d.cache_file = tmp_path / "discovered_models.json"
    return d


# ── _fetch_provider_models ──────────────────────────────────────

class TestFetchProviderModels:
    def test_skip_provider(self, discovery):
        config = {"skip": True, "reason": "no endpoint"}
        assert discovery._fetch_provider_models("wenxin", config) == []

    def test_no_url(self, discovery):
        assert discovery._fetch_provider_models("x", {}) == []

    def test_no_api_key(self, discovery, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        config = {"url": "http://example.com", "key_env": "DEEPSEEK_API_KEY", "format": "openai"}
        assert discovery._fetch_provider_models("deepseek", config) == []

    def test_openai_format_success(self, discovery, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-testkey")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"id": "deepseek-chat", "created": 123, "object": "model", "owned_by": "deepseek"},
                {"id": "deepseek-embedding", "created": 124, "object": "model", "owned_by": "deepseek"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            models = discovery._fetch_provider_models("deepseek", {
                "url": "https://api.deepseek.com/models",
                "key_env": "DEEPSEEK_API_KEY",
                "format": "openai",
            })
        assert len(models) == 1
        assert models[0]["id"] == "deepseek-chat"

    def test_filters_non_chat_models(self, discovery, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-testkey")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"id": "text-embedding-ada-002"},
                {"id": "tts-1"},
                {"id": "whisper-1"},
                {"id": "dall-e-3"},
                {"id": "my-image-model"},
                {"id": "audio-model"},
                {"id": "text-moderation"},
                {"id": "chat-model-ok"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            models = discovery._fetch_provider_models("openai", {
                "url": "https://api.openai.com/v1/models",
                "key_env": "OPENAI_API_KEY",
                "format": "openai",
            })
        assert len(models) == 1
        assert models[0]["id"] == "chat-model-ok"

    def test_timeout(self, discovery, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-testkey")
        with patch("requests.get", side_effect=requests.exceptions.Timeout("timeout")):
            assert discovery._fetch_provider_models("deepseek", {
                "url": "http://x.com", "key_env": "DEEPSEEK_API_KEY", "format": "openai"
            }) == []

    def test_request_exception(self, discovery, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-testkey")
        with patch("requests.get", side_effect=requests.exceptions.RequestException("err")):
            assert discovery._fetch_provider_models("deepseek", {
                "url": "http://x.com", "key_env": "DEEPSEEK_API_KEY", "format": "openai"
            }) == []

    def test_http_error(self, discovery, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-testkey")
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401")
        with patch("requests.get", return_value=mock_resp):
            assert discovery._fetch_provider_models("deepseek", {
                "url": "http://x.com", "key_env": "DEEPSEEK_API_KEY", "format": "openai"
            }) == []

    def test_empty_data(self, discovery, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-testkey")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            models = discovery._fetch_provider_models("deepseek", {
                "url": "http://x.com", "key_env": "DEEPSEEK_API_KEY", "format": "openai"
            })
        assert models == []


# ── discover_all ────────────────────────────────────────────────

class TestDiscoverAll:
    def test_returns_dict(self, discovery):
        with patch.object(discovery, "_fetch_provider_models", return_value=[]):
            result = discovery.discover_all()
        assert isinstance(result, dict)

    def test_skips_marked_providers(self, discovery):
        with patch.object(discovery, "_fetch_provider_models", return_value=[]) as mock:
            discovery.discover_all()
        called_providers = {call.args[0] for call in mock.call_args_list}
        assert "wenxin" not in called_providers
        assert "hunyuan" not in called_providers

    def test_includes_active_providers(self, discovery):
        with patch.object(discovery, "_fetch_provider_models", return_value=[]) as mock:
            discovery.discover_all()
        called_providers = {call.args[0] for call in mock.call_args_list}
        assert "deepseek" in called_providers
        assert "glm" in called_providers

    def test_collects_results(self, discovery):
        with patch.object(discovery, "_fetch_provider_models",
                          side_effect=lambda p, c, t=None: [{"id": f"{p}-model"}] if p == "deepseek" else []):
            result = discovery.discover_all()
        assert len(result.get("deepseek", [])) == 1


# ── get_cached / save_cache ─────────────────────────────────────

class TestCache:
    def test_no_cache_file(self, discovery):
        assert discovery.get_cached() is None

    def test_save_and_read(self, discovery):
        data = {"deepseek": [{"id": "deepseek-chat"}]}
        discovery.save_cache(data)
        cached = discovery.get_cached()
        assert cached is not None
        assert "deepseek" in cached.get("providers", {})

    def test_expired_cache(self, discovery):
        data = {"deepseek": [{"id": "x"}]}
        discovery.save_cache(data)
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        content = json.loads(discovery.cache_file.read_text())
        content["cached_at"] = old_time
        discovery.cache_file.write_text(json.dumps(content))
        assert discovery.get_cached() is None

    def test_invalid_json(self, discovery):
        discovery.cache_file.parent.mkdir(parents=True, exist_ok=True)
        discovery.cache_file.write_text("not json{")
        assert discovery.get_cached() is None

    def test_missing_cached_at(self, discovery):
        discovery.cache_file.parent.mkdir(parents=True, exist_ok=True)
        discovery.cache_file.write_text(json.dumps({"providers": {}}))
        assert discovery.get_cached() is None

    def test_invalid_cached_at(self, discovery):
        discovery.cache_file.parent.mkdir(parents=True, exist_ok=True)
        discovery.cache_file.write_text(json.dumps({"cached_at": "not-a-date", "providers": {}}))
        assert discovery.get_cached() is None


# ── compare_with_builtin ────────────────────────────────────────

class TestCompareWithBuiltin:
    def _make_builtin(self):
        return [
            {"provider": "deepseek", "model": "deepseek-chat", "name": "DeepSeek Chat"},
        ]

    def test_finds_new_models(self, discovery):
        builtin = self._make_builtin()
        discovered = {"deepseek": [{"id": "deepseek-new-model", "created": 123}]}
        result = discovery.compare_with_builtin(discovered, builtin)
        assert any(m["model_id"] == "deepseek-new-model" for m in result["new_models"])

    def test_finds_removed_models(self, discovery):
        builtin = [{"provider": "deepseek", "model": "deepseek-old", "name": "Old"}]
        discovered = {"deepseek": [{"id": "deepseek-chat"}]}
        result = discovery.compare_with_builtin(discovered, builtin)
        assert any(m["model_id"] == "deepseek-old" for m in result["removed_models"])

    def test_unchanged_models(self, discovery):
        builtin = [{"provider": "deepseek", "model": "deepseek-chat", "name": "Chat"}]
        discovered = {"deepseek": [{"id": "deepseek-chat"}]}
        result = discovery.compare_with_builtin(discovered, builtin)
        assert len(result["unchanged"]) == 1

    def test_empty_discovered(self, discovery):
        builtin = self._make_builtin()
        result = discovery.compare_with_builtin({}, builtin)
        assert result["new_models"] == []
        assert result["removed_models"] == []


# ── sync ────────────────────────────────────────────────────────

class TestSync:
    def test_uses_cache(self, discovery):
        discovery.save_cache({"deepseek": [{"id": "x"}]})
        result = discovery.sync(force=False)
        assert result["status"] == "cached"

    def test_force_refresh(self, discovery):
        discovery.save_cache({"deepseek": [{"id": "x"}]})
        with patch.object(discovery, "discover_all", return_value={"glm": [{"id": "glm-4"}]}):
            result = discovery.sync(force=True)
        assert result["status"] == "success"
        assert "glm" in result["data"]

    def test_no_cache(self, discovery):
        with patch.object(discovery, "discover_all", return_value={"deepseek": [{"id": "d1"}]}):
            result = discovery.sync(force=False)
        assert result["status"] == "success"


# ── get_discovery_summary ───────────────────────────────────────

class TestGetDiscoverySummary:
    def test_no_discovered(self, tmp_path):
        d = ModelDiscovery()
        d.cache_file = tmp_path / "none.json"
        with patch.object(d, "discover_all", return_value={}):
            result = get_discovery_summary([], d)
        assert result["has_new"] is False

    def test_with_new_models(self, tmp_path):
        d = ModelDiscovery()
        d.cache_file = tmp_path / "cache.json"
        d.save_cache({"deepseek": [{"id": "brand-new-model"}]})
        result = get_discovery_summary([], d)
        assert result["has_new"] is True
        assert result["is_cached"] is True
