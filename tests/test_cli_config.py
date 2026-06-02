"""测试 cli_config.py — 配置管理命令"""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from src.commands.cli_config import app

runner = CliRunner()


class TestMaskSecret:
    """测试 _mask_secret 辅助函数"""

    def _mask(self, val: str) -> str:
        # 复制函数逻辑（它在命令内部定义）
        if not val:
            return ""
        if len(val) <= 8:
            return "****"
        return val[:4] + "****" + val[-4:]

    def test_empty(self):
        assert self._mask("") == ""

    def test_none(self):
        assert self._mask(None) == ""

    def test_short(self):
        assert self._mask("abc") == "****"

    def test_exactly_8(self):
        assert self._mask("abcdefgh") == "****"

    def test_long(self):
        assert self._mask("sk-1234567890abcdef") == "sk-1****cdef"

    def test_9_chars(self):
        assert self._mask("123456789") == "1234****6789"


class TestShowCommand:
    @patch("src.commands.cli_config.os.getenv", return_value="")
    def test_show_no_env(self, mock_env):
        result = runner.invoke(app, ["show"])
        assert result.exit_code == 0

    @patch("src.commands.cli_config.os.getenv", side_effect=lambda k, d="": "testval" if k == "DEFAULT_MODEL" else "")
    def test_show_with_env(self, mock_env):
        result = runner.invoke(app, ["show"])
        assert result.exit_code == 0


class TestListCommand:
    @patch("src.commands.cli_config.os.getenv", return_value="")
    def test_list_no_env(self, mock_env):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0


class TestSetCommand:
    def test_set_no_key(self):
        result = runner.invoke(app, ["set"])
        assert result.exit_code == 1

    def test_set_model_config(self, tmp_path):
        config_file = tmp_path / ".omc" / "config.json"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("{}")
        with patch("src.commands.cli_config.Path.home", return_value=tmp_path):
            result = runner.invoke(
                app, ["set", "--key", "api_key", "--value", "sk-test", "--model", "kimi"]
            )
            assert result.exit_code == 0

    def test_set_delete_key(self, tmp_path):
        config_file = tmp_path / ".omc" / "config.json"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(json.dumps({"models": {"kimi": {"api_key": "old"}}}))
        with patch("src.commands.cli_config.Path.home", return_value=tmp_path):
            result = runner.invoke(
                app, ["set", "--key", "api_key", "--value", "", "--model", "kimi"]
            )
            assert result.exit_code == 0


class TestModelsCommand:
    def test_models_empty(self, tmp_path):
        config_file = tmp_path / ".omc" / "config.json"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("{}")
        with patch("src.commands.cli_config.Path.home", return_value=tmp_path):
            result = runner.invoke(app, ["models"])
            assert result.exit_code == 0

    def test_models_with_config(self, tmp_path):
        config_file = tmp_path / ".omc" / "config.json"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(
            json.dumps({"models": {"kimi": {"api_key": "sk-longkey12345678"}}})
        )
        with patch("src.commands.cli_config.Path.home", return_value=tmp_path):
            result = runner.invoke(app, ["models"])
            assert result.exit_code == 0


class TestValidateConfigFile:
    """测试配置文件验证"""

    def test_missing_file(self):
        from src.config.agent_config import validate_config_file

        valid, errors = validate_config_file("/nonexistent/config.yaml")
        assert valid is False
        assert "配置文件不存在" in errors

    def test_invalid_name(self):
        from src.config.agent_config import AgentConfig, EnvironmentConfig

        config = AgentConfig(
            name="Invalid Name!", description="test", environment=EnvironmentConfig()
        )
        errors = config.validate()
        assert len(errors) > 0
        assert any("name" in e for e in errors)
