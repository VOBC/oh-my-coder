"""Tests for src/commands/cli_run.py helper functions."""

import os

# Import helpers under test
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from commands.cli_run import (  # noqa: E402
    _check_env,
    _detect_project_name,
    _get_api_key,
    _load_config,
    _resolve_default_model,
    _status_color,
)

# ─────────────────────────────────────────────
# _detect_project_name
# ─────────────────────────────────────────────

class TestDetectProjectName:
    def test_from_pyproject_toml(self, tmp_path):
        pytest.importorskip("tomllib")

        toml_content = '[project]\nname = "my-cool-project"\nversion = "0.1.0"\n'
        (tmp_path / "pyproject.toml").write_text(toml_content)
        assert _detect_project_name(tmp_path) == "my-cool-project"

    def test_from_setup_py(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("")  # empty, should skip
        setup_content = 'from setuptools import setup\nsetup(name="setup-py-project")'
        (tmp_path / "setup.py").write_text(setup_content)
        assert _detect_project_name(tmp_path) == "setup-py-project"

    def test_pyproject_takes_precedence(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[tool.black]\nline-length = 88\n')
        assert _detect_project_name(tmp_path) == tmp_path.name

    def test_fallback_to_dirname(self, tmp_path):
        assert _detect_project_name(tmp_path) == tmp_path.name

    def test_pyproject_parse_error_falls_back(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("this is not valid toml [[[")
        (tmp_path / "setup.py").write_text('setup(name="from-setup")')
        assert _detect_project_name(tmp_path) == "from-setup"

    def test_setup_py_missing_name(self, tmp_path):
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()")
        assert _detect_project_name(tmp_path) == tmp_path.name


# ─────────────────────────────────────────────
# _load_config
# ─────────────────────────────────────────────

class TestLoadConfig:
    def test_no_config_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        result = _load_config()
        assert result == {}

    def test_valid_config(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".omc"
        config_dir.mkdir()
        (config_dir / "config.json").write_text('{"models": {"deepseek": {"api_key": "sk-test"}}}')
        monkeypatch.setenv("HOME", str(tmp_path))
        result = _load_config()
        assert result == {"models": {"deepseek": {"api_key": "sk-test"}}}

    def test_invalid_json(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".omc"
        config_dir.mkdir()
        (config_dir / "config.json").write_text("{invalid json}")
        monkeypatch.setenv("HOME", str(tmp_path))
        result = _load_config()
        assert result == {}


# ─────────────────────────────────────────────
# _resolve_default_model
# ─────────────────────────────────────────────

class TestResolveDefaultModel:
    def test_env_model_first(self):
        config = {}
        with patch.dict(os.environ, {"OMC_DEFAULT_MODEL": "glm", "DEFAULT_MODEL": "kimi"}, clear=False):
            result = _resolve_default_model(config)
            assert result == "glm"

    def test_default_model_env_fallback(self):
        config = {}
        with patch.dict(os.environ, {}, clear=False):
            # Remove OMC_DEFAULT_MODEL if present
            os.environ.pop("OMC_DEFAULT_MODEL", None)
            with patch.dict(os.environ, {"DEFAULT_MODEL": "kimi"}, clear=False):
                result = _resolve_default_model(config)
                assert result == "kimi"

    def test_config_defaults_model(self):
        config = {"defaults": {"model": "deepseek"}}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMC_DEFAULT_MODEL", None)
            os.environ.pop("DEFAULT_MODEL", None)
            result = _resolve_default_model(config)
            assert result == "deepseek"

    def test_config_default_model_fallback(self):
        config = {"default_model": "glm"}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMC_DEFAULT_MODEL", None)
            os.environ.pop("DEFAULT_MODEL", None)
            result = _resolve_default_model(config)
            assert result == "glm"

    def test_first_model_with_api_key(self):
        config = {
            "models": {
                "deepseek": {"api_key": ""},
                "glm": {"api_key": "sk-glm"},
                "kimi": {"api_key": ""},
            }
        }
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMC_DEFAULT_MODEL", None)
            os.environ.pop("DEFAULT_MODEL", None)
            result = _resolve_default_model(config)
            assert result == "glm"

    def test_fallback_to_deepseek(self):
        config = {"models": {}}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMC_DEFAULT_MODEL", None)
            os.environ.pop("DEFAULT_MODEL", None)
            result = _resolve_default_model(config)
            assert result == "deepseek"


# ─────────────────────────────────────────────
# _get_api_key
# ─────────────────────────────────────────────

class TestGetApiKey:
    def test_from_config_json(self):
        config = {"models": {"deepseek": {"api_key": "sk-from-config"}}}
        result = _get_api_key(config, "deepseek")
        assert result == "sk-from-config"

    def test_model_name_variants(self):
        config = {"models": {"deepseek-chat": {"api_key": "sk-variant"}}}
        result = _get_api_key(config, "deepseek_chat")
        assert result == "sk-variant"

    def test_env_var_fallback(self):
        config = {}
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-env"}, clear=False):
            result = _get_api_key(config, "deepseek")
            assert result == "sk-env"

    def test_env_var_not_in_map(self):
        config = {}
        with patch.dict(os.environ, {"CUSTOM-MODEL_API_KEY": "sk-custom"}, clear=False):
            result = _get_api_key(config, "custom-model")
            assert result == "sk-custom"

    def test_config_over_env(self):
        config = {"models": {"deepseek": {"api_key": "sk-config"}}}
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-env"}, clear=False):
            result = _get_api_key(config, "deepseek")
            assert result == "sk-config"

    def test_empty_if_no_key(self):
        config = {}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEEPSEEK_API_KEY", None)
            result = _get_api_key(config, "deepseek")
            assert result == ""

    def test_glm_uses_zhipuai_key(self):
        config = {}
        with patch.dict(os.environ, {"ZHIPUAI_API_KEY": "sk-zhipu"}, clear=False):
            result = _get_api_key(config, "glm")
            assert result == "sk-zhipu"


# ─────────────────────────────────────────────
# _check_env
# ─────────────────────────────────────────────

class TestCheckEnv:
    def test_returns_true_when_key_present(self, monkeypatch):
        monkeypatch.setattr(
            "commands.cli_run._load_config",
            lambda: {"models": {"deepseek": {"api_key": "sk-test"}}},
        )
        monkeypatch.setattr(
            "commands.cli_run._get_api_key",
            lambda config, model: "sk-test",
        )
        monkeypatch.setattr(
            "commands.cli_run._resolve_default_model",
            lambda config: "deepseek",
        )
        assert _check_env() is True

    def test_returns_false_when_no_key(self, monkeypatch):
        monkeypatch.setattr(
            "commands.cli_run._load_config",
            lambda: {},
        )
        monkeypatch.setattr(
            "commands.cli_run._get_api_key",
            lambda config, model: "",
        )
        monkeypatch.setattr(
            "commands.cli_run._resolve_default_model",
            lambda config: "deepseek",
        )
        assert _check_env() is False


# ─────────────────────────────────────────────
# _status_color
# ─────────────────────────────────────────────

class TestStatusColor:
    def test_completed(self):
        assert _status_color("completed") == "[green]已完成[/green]"

    def test_failed(self):
        assert _status_color("failed") == "[red]失败[/red]"

    def test_running(self):
        assert _status_color("running") == "[yellow]运行中[/yellow]"

    def test_pending(self):
        assert _status_color("pending") == "[dim]等待中[/dim]"

    def test_unknown_status(self):
        assert _status_color("whatever") == "whatever"
