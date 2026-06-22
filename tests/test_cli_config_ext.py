"""
Tests for src/commands/cli_config_ext.py.
Covers load/validate/list/create commands and their error paths.
"""
from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from src.commands.cli_config_ext import app

runner = CliRunner()


def _make_config(name="test-agent", description="Test agent", model="deepseek",
                 tools=None, permissions=None, environment=None):
    """Build a mock AgentConfig."""
    from src.config.agent_config import AgentConfig, EnvironmentConfig
    return AgentConfig(
        name=name,
        description=description,
        model=model,
        tools=tools or ["tool_a", "tool_b"],
        permissions=permissions or {"allowed_patterns": ["*.py"]},
        environment=environment or EnvironmentConfig(max_tokens=4096, temperature=0.7, timeout=30),
    )


# ── load command ───────────────────────────────────────────────────────


class TestLoadConfig:
    """Tests for the `load` command."""

    def test_load_success(self):
        config = _make_config()
        with patch("src.commands.cli_config_ext.load_config_file", return_value=config):
            result = runner.invoke(app, ["load", "test.yaml"])
        assert result.exit_code == 0
        assert "配置加载成功" in result.stdout
        assert "test-agent" in result.stdout

    def test_load_success_verbose(self):
        config = _make_config()
        with patch("src.commands.cli_config_ext.load_config_file", return_value=config):
            result = runner.invoke(app, ["load", "test.yaml", "--verbose"])
        assert result.exit_code == 0
        assert "配置加载成功" in result.stdout
        assert "工具" in result.stdout
        assert "tool_a" in result.stdout
        assert "环境配置" in result.stdout
        assert "4096" in result.stdout
        assert "0.7" in result.stdout
        assert "30" in result.stdout
        assert "权限规则" in result.stdout
        assert "allowed_patterns" in result.stdout

    def test_load_file_not_found(self):
        with patch("src.commands.cli_config_ext.load_config_file",
                   side_effect=FileNotFoundError("no file")):
            result = runner.invoke(app, ["load", "missing.yaml"])
        assert result.exit_code == 1
        assert "配置文件不存在" in result.stdout

    def test_load_other_exception(self):
        with patch("src.commands.cli_config_ext.load_config_file",
                   side_effect=ValueError("bad yaml")):
            result = runner.invoke(app, ["load", "bad.yaml"])
        assert result.exit_code == 1
        assert "加载失败" in result.stdout

    def test_load_json_file(self):
        config = _make_config(name="json-agent")
        with patch("src.commands.cli_config_ext.load_config_file", return_value=config):
            result = runner.invoke(app, ["load", "config.json"])
        assert result.exit_code == 0
        assert "json-agent" in result.stdout

    def test_load_no_description(self):
        config = _make_config(description="")
        with patch("src.commands.cli_config_ext.load_config_file", return_value=config):
            result = runner.invoke(app, ["load", "test.yaml"])
        assert result.exit_code == 0
        assert "无" in result.stdout


# ── validate command ───────────────────────────────────────────────────


class TestValidateConfig:
    """Tests for the `validate` command."""

    def test_validate_valid(self):
        with patch("src.commands.cli_config_ext.validate_config_file",
                   return_value=(True, [])):
            result = runner.invoke(app, ["validate", "valid.yaml"])
        assert result.exit_code == 0
        assert "配置文件合法" in result.stdout

    def test_validate_invalid(self):
        errors = ["name is required", "model not supported"]
        with patch("src.commands.cli_config_ext.validate_config_file",
                   return_value=(False, errors)):
            result = runner.invoke(app, ["validate", "bad.yaml"])
        assert result.exit_code == 1
        assert "配置文件有误" in result.stdout
        assert "name is required" in result.stdout
        assert "model not supported" in result.stdout


# ── list command ───────────────────────────────────────────────────────


class TestListConfigs:
    """Tests for the `list` command."""

    def test_list_with_configs(self, tmp_path):
        config = _make_config()
        with patch("src.commands.cli_config_ext.list_configs_in_dir",
                   return_value=[str(tmp_path / "a.yaml"),
                                 str(tmp_path / "b.json")]):
            with patch("src.commands.cli_config_ext.load_config_file",
                       return_value=config):
                result = runner.invoke(app, ["list", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "a.yaml" in result.stdout
        assert "b.json" in result.stdout
        assert "test-agent" in result.stdout

    def test_list_empty_dir(self, tmp_path):
        with patch("src.commands.cli_config_ext.list_configs_in_dir",
                   return_value=[]):
            result = runner.invoke(app, ["list", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "目录下没有配置文件" in result.stdout

    def test_list_default_dir(self):
        config = _make_config()
        with patch("src.commands.cli_config_ext.list_configs_in_dir",
                   return_value=["/home/user/.omc/agents/a.yaml"]):
            with patch("src.commands.cli_config_ext.load_config_file",
                       return_value=config):
                result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "a.yaml" in result.stdout

    def test_list_parse_failure(self, tmp_path):
        with patch("src.commands.cli_config_ext.list_configs_in_dir",
                   return_value=[str(tmp_path / "broken.yaml")]):
            with patch("src.commands.cli_config_ext.load_config_file",
                       side_effect=ValueError("bad")):
                result = runner.invoke(app, ["list", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "解析失败" in result.stdout


# ── create command ─────────────────────────────────────────────────────


class TestCreateConfig:
    """Tests for the `create` command."""

    def test_create_to_console(self):
        config = _make_config()
        with patch("src.commands.cli_config_ext.load_config_file", return_value=config):
            result = runner.invoke(app, ["create", "test.yaml"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["name"] == "test-agent"
        assert data["model"] == "deepseek"
        assert "tool_a" in data["tools"]

    def test_create_to_file(self, tmp_path):
        out = tmp_path / "output.json"
        config = _make_config()
        with patch("src.commands.cli_config_ext.load_config_file", return_value=config):
            result = runner.invoke(app, ["create", "test.yaml", "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["name"] == "test-agent"

    def test_create_file_not_found(self):
        with patch("src.commands.cli_config_ext.load_config_file",
                   side_effect=FileNotFoundError("no file")):
            result = runner.invoke(app, ["create", "missing.yaml"])
        assert result.exit_code == 1
        assert "配置文件不存在" in result.stdout

    def test_create_other_exception(self):
        with patch("src.commands.cli_config_ext.load_config_file",
                   side_effect=RuntimeError("crash")):
            result = runner.invoke(app, ["create", "bad.yaml"])
        assert result.exit_code == 1
        assert "创建失败" in result.stdout
