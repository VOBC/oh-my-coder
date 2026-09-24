"""
Additional tests for cli_config.py covering remaining gaps:
- show with specific model (found/not found)
- show with multiple models (per-model view)
- show with no models configured
- list with env vars
- set global config (writes .env)
- set model config with value
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from src.commands.cli_config import app

runner = CliRunner()


# ── show command extras ────────────────────────────────────────────────


class TestShowExtras:
    def test_show_specific_model_found(self, tmp_path, monkeypatch):
        """When --model specifies an existing model, show its config."""
        cfg = {"models": {"gpt-4": {"api_key": "sk-1234567890abcdef"}}}
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text(json.dumps(cfg))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["show", "--model", "gpt-4"])
        assert result.exit_code == 0
        assert "gpt-4" in result.stdout
        assert "sk-1****cdef" in result.stdout  # masked

    def test_show_specific_model_not_found(self, tmp_path, monkeypatch):
        """When --model specifies a non-existent model, show dim message."""
        cfg = {"models": {"claude": {"api_key": "key"}}}
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text(json.dumps(cfg))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["show", "--model", "nonexistent"])
        assert result.exit_code == 0
        assert "尚未配置" in result.stdout

    def test_show_multiple_models(self, tmp_path, monkeypatch):
        """Without --model, show all per-model configs."""
        cfg = {
            "models": {
                "kimi": {"api_key": "sk-kimi-key-1234"},
                "doubao": {"api_key": "sk-doubao-key-5678", "temperature": 0.7},
            }
        }
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text(json.dumps(cfg))

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["show"])
        assert result.exit_code == 0
        assert "kimi" in result.stdout
        assert "doubao" in result.stdout
        assert "temperature" in result.stdout

    def test_show_no_models(self, tmp_path, monkeypatch):
        """When config has no models key, show dim message."""
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text("{}")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["show"])
        assert result.exit_code == 0
        assert "无按模型配置" in result.stdout

    def test_show_includes_all_provider_keys(self, tmp_path, monkeypatch):
        """Regression: show must list all supported provider API keys, not just
        deepseek/kimi/doubao. GLM (ZHIPUAI_API_KEY) was previously missing."""
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text("{}")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["show"])
        assert result.exit_code == 0
        # Every supported provider key must appear in show output
        for key in (
            "DEEPSEEK_API_KEY",
            "KIMI_API_KEY",
            "DOUBAO_API_KEY",
            "ZHIPUAI_API_KEY",
            "GLM_API_KEY",
            "MINIMAX_API_KEY",
            "DASHSCOPE_API_KEY",
            "ERNIE_API_KEY",
            "HUNYUAN_API_KEY",
        ):
            assert key in result.stdout, f"{key} missing from show output"


# ── list command extras ────────────────────────────────────────────────


class TestListExtras:
    def test_list_with_env_vars_set(self):
        """When env vars are set, show green ✓ and masked values."""
        with patch.dict(
            "os.environ",
            {
                "DEEPSEEK_API_KEY": "sk-abc123def456",
                "DEFAULT_MODEL": "deepseek-v3",
            },
        ):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "sk-a****f456" in result.stdout  # masked
        assert "deep****k-v3" in result.stdout  # masked: >8 chars, first 4 + last 4

    def test_list_with_none_set(self):
        """When no env vars, show red ✗."""
        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # Should show all items with ✗
        assert "DEEPSEEK_API_KEY" in result.stdout
        assert "✓" not in result.stdout or "✗" in result.stdout

    def test_list_includes_all_provider_keys(self):
        """Regression: list must advertise all supported provider API keys."""
        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        for key in (
            "DEEPSEEK_API_KEY",
            "KIMI_API_KEY",
            "DOUBAO_API_KEY",
            "ZHIPUAI_API_KEY",
            "GLM_API_KEY",
            "MINIMAX_API_KEY",
            "DASHSCOPE_API_KEY",
            "ERNIE_API_KEY",
            "HUNYUAN_API_KEY",
        ):
            assert key in result.stdout, f"{key} missing from list output"


# ── set command extras ─────────────────────────────────────────────────


class TestSetExtras:
    def test_set_global_env(self, tmp_path, monkeypatch):
        """Set a global config writes to .env file."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # Create .omc/config.json so the model check passes
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.json").write_text("{}")

        # Global config writes to ~/.omc/.env (unified location)
        env_file = tmp_path / ".omc" / ".env"
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app, ["set", "--key", "DEFAULT_MODEL", "--value", "gpt-4"]
        )
        assert result.exit_code == 0
        assert "已设置（全局）" in result.stdout
        assert env_file.exists()
        content = env_file.read_text()
        assert "DEFAULT_MODEL=gpt-4" in content

    def test_set_model_key_with_value(self, tmp_path, monkeypatch):
        """Set a model-specific key with a value."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = cfg_dir / "config.json"
        cfg_file.write_text('{"models": {"test-model": {}}}')

        result = runner.invoke(
            app,
            ["set", "--model", "test-model", "--key", "temperature", "--value", "0.8"],
        )
        assert result.exit_code == 0
        assert "已设置" in result.stdout
        saved = json.loads(cfg_file.read_text())
        assert saved["models"]["test-model"]["temperature"] == "0.8"

    def test_set_model_key_delete(self, tmp_path, monkeypatch):
        """Set a model key with empty value deletes it."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = cfg_dir / "config.json"
        cfg_file.write_text(
            '{"models": {"m": {"temperature": "0.5", "api_key": "key"}}}'
        )

        result = runner.invoke(
            app, ["set", "--model", "m", "--key", "temperature", "--value", ""]
        )
        assert result.exit_code == 0
        assert "已移除" in result.stdout
        saved = json.loads(cfg_file.read_text())
        assert "temperature" not in saved["models"]["m"]

    def test_set_new_model(self, tmp_path, monkeypatch):
        """Setting a key for a model that doesn't exist creates it."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = cfg_dir / "config.json"
        cfg_file.write_text("{}")

        result = runner.invoke(
            app, ["set", "--model", "new-model", "--key", "api_key", "--value", "sk-xyz"]
        )
        assert result.exit_code == 0
        saved = json.loads(cfg_file.read_text())
        assert saved["models"]["new-model"]["api_key"] == "sk-xyz"


# ── models command extras ──────────────────────────────────────────────


class TestModelsExtras:
    def test_models_with_temperature(self, tmp_path, monkeypatch):
        """Show model config including non-string values like temperature."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = {
            "models": {
                "kimi": {
                    "api_key": "sk-kimi-test-key-1234",
                    "base_url": "https://api.kimi.com",
                    "temperature": 0.3,
                }
            }
        }
        (cfg_dir / "config.json").write_text(json.dumps(cfg))

        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "kimi" in result.stdout
        assert "0.3" in result.stdout
        assert "https://api.kimi.com" in result.stdout

    def test_models_lists_max_tokens_and_system_prompt(self, tmp_path, monkeypatch):
        """Regression: models must display max_tokens and system_prompt when set.
        Previously only api_key/base_url/temperature were shown."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = {
            "models": {
                "glm": {
                    "api_key": "sk-glm-test-key-1234",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "system_prompt": "You are a helpful assistant.",
                }
            }
        }
        (cfg_dir / "config.json").write_text(json.dumps(cfg))

        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "glm" in result.stdout
        assert "max_tokens" in result.stdout
        assert "4096" in result.stdout
        assert "system_prompt" in result.stdout
        assert "You are a helpful assistant." in result.stdout
        # unknown keys are also surfaced (not silently dropped)

    def test_models_lists_unknown_fields(self, tmp_path, monkeypatch):
        """Any non-preferred key configured for a model is still displayed."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = {"models": {"custom": {"api_key": "sk-c-1234", "top_p": 0.9}}}
        (cfg_dir / "config.json").write_text(json.dumps(cfg))

        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "custom" in result.stdout
        assert "top_p" in result.stdout
        assert "0.9" in result.stdout
