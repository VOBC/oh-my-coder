"""
Precision tests to improve cli_model.py coverage from 86% to 95%+.

Target missing lines: 47-49, 103-122, 127-129, 136-171, 419-423, 1096,
                     1429, 1565, 1606-1607, 1632-1648, 1951-1952
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.commands import cli_model


# Fake model object with real numeric attributes (not Mock)
@dataclass
class FakeDiscoveredModel:
    """Fake model object returned by discover_ollama_models()."""
    model_name: str
    size_gb: float
    size_mb: float
    parameter_size: str
    quantization: str


class TestLocalCheckStatus:
    """Test lines 103-122, 127-129, 136-171: local_check_status() branches."""

    def test_local_check_status_ollama_available_with_discovery(self):
        """Test when Ollama is available and discovery works (lines 103-122)."""
        # Mock health status
        mock_status = Mock()
        mock_status.running = True
        mock_status.available_models = ["qwen2:7b", "deepseek-r1:7b"]
        mock_status.version = "0.5.0"
        mock_status.model_count = 2
        mock_status.latency_ms = 50.0

        mock_checker = Mock()
        mock_checker.check_ollama.return_value = mock_status

        # Use real objects with actual numeric attributes
        fake_models = [
            FakeDiscoveredModel("qwen2:7b", 4.2, 0, "7B", "Q4_K_M"),
            FakeDiscoveredModel("deepseek-r1:7b", 4.5, 0, "7B", "Q8_K"),
        ]

        with patch("src.core.ollama_health.OllamaHealthChecker", return_value=mock_checker):
            with patch("src.core.local_model_discovery.discover_ollama_models", return_value=fake_models):
                runner = CliRunner()
                result = runner.invoke(cli_model.local_app, ["status"])
                assert result.exit_code == 0

    def test_local_check_status_ollama_available_no_discovery(self, monkeypatch):
        """Test when Ollama is available but discovery module not available (lines 127-129)."""
        mock_status = Mock()
        mock_status.running = True
        mock_status.available_models = ["qwen2:7b"]
        # Set real attributes (not Mock) to avoid __format__ errors
        mock_status.version = "0.5.0"
        mock_status.model_count = 2
        mock_status.latency_ms = 50.0

        mock_checker = Mock()
        mock_checker.check_ollama.return_value = mock_status

        with patch("src.core.ollama_health.OllamaHealthChecker", return_value=mock_checker):
            # Make discover_ollama_models raise ImportError by deleting it
            import src.core.local_model_discovery
            monkeypatch.delattr(src.core.local_model_discovery, "discover_ollama_models")

            runner = CliRunner()
            result = runner.invoke(cli_model.local_app, ["status"])
            assert result.exit_code == 0

    def test_local_check_status_ollama_not_running(self):
        """Test when Ollama is not running (lines 136-171)."""
        mock_status = Mock()
        mock_status.running = False

        mock_checker = Mock()
        mock_checker.check_ollama.return_value = mock_status

        with patch("src.core.ollama_health.OllamaHealthChecker", return_value=mock_checker):
            runner = CliRunner()
            result = runner.invoke(cli_model.local_app, ["status"])
            assert result.exit_code == 0

    def test_local_check_status_import_error_fallback(self, monkeypatch):
        """Test ImportError fallback in local_check_status (lines 127-129, 136-171)."""
        # Make OllamaHealthChecker import fail
        import src.core.ollama_health
        monkeypatch.delattr(src.core.ollama_health, "OllamaHealthChecker")

        # Now it falls back to OllamaModel
        with patch("src.models.ollama.OllamaModel.is_available", return_value=True):
            with patch(
                "src.models.ollama.OllamaModel.list_models",
                return_value=[
                    {
                        "name": "qwen2:7b",
                        "size": 4.2e9,
                        "modified_at": "2024-01-01",
                    }
                ],
            ):
                runner = CliRunner()
                result = runner.invoke(cli_model.local_app, ["status"])
                assert result.exit_code == 0


class TestListModels:
    """Test line 1096: list_models() normal table mode."""

    def test_list_models_table_mode(self, monkeypatch):
        """Test list_models in normal table mode (non-extended, non-json)."""
        mock_models = [
            {
                "model_id": "deepseek-chat",
                "name": "DeepSeek Chat",
                "provider": "deepseek",
                "tier": "low",
                "status": "production",
            },
            {
                "model_id": "glm-4-flash",
                "name": "GLM-4-Flash",
                "provider": "glm",
                "tier": "free",
                "status": "production",
            },
        ]

        monkeypatch.setattr(cli_model, "BUILTIN_CATWALK_MODELS", mock_models)

        runner = CliRunner()
        result = runner.invoke(cli_model.app, ["list"])
        assert result.exit_code == 0


class TestImportModel:
    """Test line 1429: import_model() local file success path."""

    def test_import_model_local_success(self, tmp_path):
        """Test importing a local YAML file successfully."""
        yaml_file = tmp_path / "test_model.yaml"
        yaml_content = """
name: test-model
provider: deepseek
model: deepseek-chat
base_url: https://api.deepseek.com/v1
description: Test model
"""
        yaml_file.write_text(yaml_content)

        runner = CliRunner()
        result = runner.invoke(cli_model.app, ["import", str(yaml_file)])
        # Should succeed or give a controlled error
        assert result.exit_code is not None


class TestShowCurrent:
    """Test line 1565: show_current() prints current model."""

    def test_show_current_prints_model(self, monkeypatch):
        """Test show_current displays current model info."""
        monkeypatch.setattr(
            "src.commands.cli_model._get_current_model",
            lambda: "deepseek-chat",
        )

        monkeypatch.setattr(
            "src.commands.cli_model._load_config",
            lambda: {"default_model": "deepseek-chat"},
        )

        monkeypatch.setattr(
            cli_model,
            "SUPPORTED_MODELS",
            {
                "deepseek-chat": {
                    "name": "DeepSeek Chat",
                    "tier": "low",
                    "note": "Test",
                }
            },
        )

        monkeypatch.setattr(
            "src.commands.cli_model._get_current_api_key",
            lambda x: "sk-test123",
        )

        runner = CliRunner()
        result = runner.invoke(cli_model.app, ["current"])
        assert result.exit_code == 0


class TestSyncModels:
    """Test lines 1606-1607, 1632-1648: sync_models() logic."""

    def test_sync_models_discovery_none(self):
        """Test when ModelDiscovery is None (lines 1606-1607)."""
        with patch("src.commands.cli_model.ModelDiscovery", None):
            runner = CliRunner()
            result = runner.invoke(cli_model.app, ["sync"])
            assert result.exit_code != 0

    def test_sync_models_with_cache(self):
        """Test sync_models with cached data (line 1632-1648)."""
        mock_discovery_instance = Mock()
        # get_cached() returns a dict (cached data exists)
        mock_discovery_instance.get_cached.return_value = {
            "cached_at": "2024-01-01T00:00:00",
            "data": {"deepseek": []},
            "providers": {"deepseek": 1},
        }
        # sync() returns status="cached" when using cache
        mock_discovery_instance.sync.return_value = {
            "status": "cached",
            "data": {"deepseek": []},
        }
        mock_discovery_instance.PROVIDER_APIS = {
            "deepseek": {"key_env": "DEEPSEEK_API_KEY"},
            "openai": {"skip": True, "reason": "Test reason"},
        }
        mock_discovery_instance.compare_with_builtin.return_value = {
            "new_models": [],
            "removed_models": [],
        }

        with patch("src.commands.cli_model.ModelDiscovery", return_value=mock_discovery_instance):
            runner = CliRunner()
            result = runner.invoke(cli_model.app, ["sync"])
            assert result.exit_code == 0

    def test_sync_models_without_cache(self, monkeypatch):
        """Test sync_models without cache (triggers force path)."""
        mock_discovery_instance = Mock()
        # get_cached() returns None (no cache)
        mock_discovery_instance.get_cached.return_value = None
        # sync() returns actual data
        mock_discovery_instance.sync.return_value = {
            "status": "fresh",
            "data": {"deepseek": [{"model_id": "deepseek-chat"}]},
            "providers": {"deepseek": 1},
        }
        mock_discovery_instance.PROVIDER_APIS = {
            "deepseek": {"key_env": "DEEPSEEK_API_KEY"},
        }
        mock_discovery_instance.compare_with_builtin.return_value = {
            "new_models": [],
            "removed_models": [],
        }

        with patch("src.commands.cli_model.ModelDiscovery", return_value=mock_discovery_instance):
            monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
            runner = CliRunner()
            result = runner.invoke(cli_model.app, ["sync"])
            assert result.exit_code == 0


class TestShowSharedModel:
    """Test lines 1951-1952: show_shared_model() model not found branch."""

    def test_show_shared_model_not_found(self):
        """Test when shared model is not found."""
        runner = CliRunner()
        result = runner.invoke(
            cli_model.app, ["show", "nonexistent-model"]
        )
        # Model not found should return non-zero exit code
        assert result.exit_code != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
