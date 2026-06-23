"""
Targeted tests to push cli_config.py from 88% to 100% by covering
remaining branches in nested _load/_mask_secret functions.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from src.commands.cli_config import app

runner = CliRunner()


# ── Cover show's _load exception handler (lines 26-28) ────────────────


class TestShowCorruptConfig:
    def test_show_corrupt_config(self, tmp_path, monkeypatch):
        """Corrupt config.json triggers show's _load except handler."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.json").write_text("{not json[[[")
        with patch("src.commands.cli_config.os.getenv", return_value=""):
            result = runner.invoke(app, ["show"])
        assert result.exit_code == 0


# ── Cover list's _mask_secret short-value branch (line 95) ─────────────


class TestListMaskBranches:
    def test_list_short_value(self):
        """list with short env value (≤8 chars) triggers return '****'."""
        with patch(
            "src.commands.cli_config.os.getenv",
            side_effect=lambda k, d="": "abc" if k == "DEFAULT_MODEL" else "",
        ):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_list_long_value(self):
        """list with long env value verifies first4+****+last4 masking."""
        with patch(
            "src.commands.cli_config.os.getenv",
            side_effect=lambda k, d="": (
                "sk-key123456789" if k == "DEEPSEEK_API_KEY" else ""
            ),
        ):
            result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "sk-k****6789" in result.stdout


# ── Cover set's _load except (lines 142-144) ───────────────────────────


class TestSetCorruptConfig:
    def test_set_model_corrupt_config(self, tmp_path, monkeypatch):
        """Corrupt config triggers set's _load except handler."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.json").write_text("{corrupt json")
        result = runner.invoke(
            app, ["set", "--model", "m", "--key", "k", "--value", "v"]
        )
        assert result.exit_code == 0


# ── Cover set's _mask_secret empty-value branch (line 151) ─────────────


class TestSetMaskBranches:
    def test_set_global_empty_value(self, tmp_path, monkeypatch):
        """Empty value triggers _mask_secret("") → return ""."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["set", "--key", "SOME_VAR", "--value", ""]
        )
        assert result.exit_code == 0

    def test_set_global_long_value(self, tmp_path, monkeypatch):
        """Long value triggers val[:4]+****+val[-4:]."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["set", "--key", "API_KEY", "--value", "sk-verylongkey123"]
        )
        assert result.exit_code == 0
        assert "sk-v****y123" in result.stdout

    def test_set_global_short_value(self, tmp_path, monkeypatch):
        """Short value triggers return '****'."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["set", "--key", "SOME_KEY", "--value", "abc"]
        )
        assert result.exit_code == 0
        assert "****" in result.stdout


# ── Cover models' _load except (lines 202-204) and _mask_secret ───────


class TestModelsEdgeCases:
    def test_models_corrupt_config(self, tmp_path, monkeypatch):
        """Corrupt config triggers models' _load except."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.json").write_text("{{{bad")
        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "尚未配置" in result.stdout

    def test_models_empty_api_key(self, tmp_path, monkeypatch):
        """Empty api_key triggers models' _mask_secret empty branch."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = {"models": {"test-m": {"api_key": ""}}}
        (cfg_dir / "config.json").write_text(json.dumps(cfg))
        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0

    def test_models_short_api_key(self, tmp_path, monkeypatch):
        """Short api_key triggers models' _mask_secret len<=8."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = {"models": {"short": {"api_key": "k123"}}}
        (cfg_dir / "config.json").write_text(json.dumps(cfg))
        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "short" in result.stdout
        # mask_secret("k123") → 4 chars ≤ 8 → "****"
        assert "k123" not in result.stdout  # short keys should be fully masked


# ── Cover set's global env construction (lines 180-183, 208, 210) ──────


class TestSetGlobalEnvDetails:
    def test_set_global_with_existing_env(self, tmp_path, monkeypatch):
        """Set global when ~/.omc/.env already exists with some vars."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg_dir = tmp_path / ".omc"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.json").write_text("{}")
        # Now writes to ~/.omc/.env (consistent with omc run reading from there)
        (cfg_dir / ".env").write_text("EXISTING_VAR=oldvalue\nANOTHER=keep\n")
        result = runner.invoke(
            app, ["set", "--key", "NEW_KEY", "--value", "newval"]
        )
        assert result.exit_code == 0
        assert "已设置（全局）" in result.stdout
        # Writes to ~/.omc/.env, preserving existing vars
        content = (cfg_dir / ".env").read_text()
        assert "EXISTING_VAR=oldvalue" in content
        assert "NEW_KEY=newval" in content


# ── Cover _load() return {} when file doesn't exist ────────────────────


class TestLoadNoFile:
    def test_show_no_config_file(self, tmp_path, monkeypatch):
        """show when config.json doesn't exist → _load returns {}."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # No .omc directory at all
        with patch("src.commands.cli_config.os.getenv", return_value=""):
            result = runner.invoke(app, ["show"])
        assert result.exit_code == 0

    def test_set_model_no_config_file(self, tmp_path, monkeypatch):
        """set --model when config.json doesn't exist → _load returns {}."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # No .omc directory → set creates it and continues
        result = runner.invoke(
            app, ["set", "--model", "newmodel", "--key", "k", "--value", "v"]
        )
        assert result.exit_code == 0

    def test_models_no_config_file(self, tmp_path, monkeypatch):
        """models when config.json doesn't exist → _load returns {}."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # No .omc directory at all
        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "尚未配置" in result.stdout
