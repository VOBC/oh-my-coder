"""Tests for cli_self_config module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from src.commands.cli_self_config import (
    CONFIG_INTENTS,
    MODEL_PROVIDERS,
    _set_api_key,
    _set_default_model,
    _set_proxy,
    _set_temperature,
    app,
    detect_api_key_in_text,
    execute_config,
    parse_config_intent,
)

runner = CliRunner()


# ── parse_config_intent ──────────────────────────────────────────


class TestParseConfigIntent:
    def test_api_key_pattern(self):
        result = parse_config_intent("配置 GLM API KEY")
        assert result is not None
        assert result["intent"] == "api_key"
        assert result["action"] == "set_api_key"

    def test_set_api_key_pattern(self):
        result = parse_config_intent("设置 DeepSeek API Key")
        assert result is not None
        assert result["intent"] == "api_key"

    def test_model_pattern(self):
        result = parse_config_intent("切换到 DeepSeek 模型")
        assert result is not None
        assert result["intent"] == "model"
        assert result["action"] == "set_default_model"

    def test_proxy_pattern(self):
        result = parse_config_intent("配置 HTTP 代理")
        assert result is not None
        assert result["intent"] == "proxy"
        assert result["action"] == "set_proxy"

    def test_temperature_pattern(self):
        result = parse_config_intent("设置温度为 0.7")
        assert result is not None
        assert result["intent"] == "temperature"
        assert result["action"] == "set_temperature"

    def test_template_pattern(self):
        result = parse_config_intent("配置代码审查模板")
        assert result is not None
        assert result["intent"] == "template"
        assert result["action"] == "set_template"

    def test_provider_fallback(self):
        result = parse_config_intent("我要用 deepseek")
        assert result is not None
        assert result["intent"] == "api_key"
        assert result["provider"] == "deepseek"

    def test_provider_name_fallback(self):
        result = parse_config_intent("配置智谱 GLM")
        assert result is not None
        assert result["intent"] == "api_key"
        assert result["provider"] == "glm"

    def test_unknown_intent(self):
        result = parse_config_intent("hello world nothing here")
        assert result is None

    def test_case_insensitive(self):
        result = parse_config_intent("SET MODEL default")
        assert result is not None
        assert result["intent"] == "model"

    def test_raw_text_preserved(self):
        result = parse_config_intent("配置 GLM API KEY")
        assert result["raw_text"] == "配置 GLM API KEY"


# ── detect_api_key_in_text ───────────────────────────────────────


class TestDetectApiKeyInText:
    def test_openai_format(self):
        result = detect_api_key_in_text("key is sk-abc123def456ghi789jkl012mno345")
        assert result is not None
        assert result.startswith("sk-")

    def test_generic_long_key(self):
        result = detect_api_key_in_text("my key is abcdefghijklmnopqrstuvwxyz123456")
        assert result is not None

    def test_quoted_key(self):
        result = detect_api_key_in_text('key="abcdefghijklmnopqrstuvwxyz12345678"')
        assert result is not None

    def test_no_key(self):
        result = detect_api_key_in_text("hello world short")
        assert result is None

    def test_http_url_ignored(self):
        result = detect_api_key_in_text("https://api.example.com/v1/abcdef12345678901234")
        assert result is None

    def test_too_short(self):
        result = detect_api_key_in_text("sk-short12")
        assert result is None


# ── execute_config ───────────────────────────────────────────────


class TestExecuteConfig:
    @pytest.mark.asyncio
    async def test_unknown_action(self):
        result = await execute_config({"action": "nonexistent"})
        assert result is False

    @pytest.mark.asyncio
    async def test_set_api_key_action(self):
        config = {"action": "set_api_key", "provider": "glm", "raw_text": "glm"}
        with patch(
            "src.commands.cli_self_config._set_api_key", return_value=True
        ) as mock:
            result = await execute_config(config)
            assert result is True
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_default_model_action(self):
        config = {"action": "set_default_model"}
        with patch(
            "src.commands.cli_self_config._set_default_model", return_value=True
        ):
            result = await execute_config(config)
            assert result is True

    @pytest.mark.asyncio
    async def test_set_proxy_action(self):
        config = {"action": "set_proxy"}
        with patch(
            "src.commands.cli_self_config._set_proxy", return_value=True
        ):
            result = await execute_config(config)
            assert result is True

    @pytest.mark.asyncio
    async def test_set_temperature_action(self):
        config = {"action": "set_temperature"}
        with patch(
            "src.commands.cli_self_config._set_temperature", return_value=True
        ):
            result = await execute_config(config)
            assert result is True


# ── _set_api_key ─────────────────────────────────────────────────


class TestSetApiKey:
    @pytest.mark.asyncio
    async def test_with_provider_and_key(self, tmp_path):
        tmp_path / ".env"
        config = {"action": "set_api_key", "provider": "glm", "raw_text": "glm"}
        with patch("src.commands.cli_self_config.Path") as mock_path_cls:
            mock_home = tmp_path
            mock_path_cls.home.return_value = mock_home
            env_dir = mock_home / ".omc"
            env_dir.mkdir(parents=True, exist_ok=True)
            # Create real env file in tmp
            (tmp_path / ".omc").mkdir(exist_ok=True)
            # Patch the actual file operations via the Path constructor
            with patch("builtins.open", create=True):
                # We'll test via the real code by monkeypatching Path.home
                pass

        # Simpler approach: patch Path.home to return tmp_path
        with patch("src.commands.cli_self_config.Path") as mock_path_cls:
            # Make Path.home() return a real tmp path, but .parent.mkdir / read_text / open use real fs
            real_home = tmp_path
            mock_path_cls.home.return_value = real_home / ".omc" / ".."
            # Actually let's just use the real fs with tmp
            (tmp_path / ".omc").mkdir(exist_ok=True)

        # Cleanest: just monkeypatch Path.home
        with patch.object(Path, "home", return_value=tmp_path):
            result = await _set_api_key(config, api_key="sk-test12345678901234")
            assert result is True
            env_content = (tmp_path / ".omc" / ".env").read_text()
            assert "ZHIPUAI_API_KEY=sk-test12345678901234" in env_content

    @pytest.mark.asyncio
    async def test_preserves_existing_env_vars(self, tmp_path):
        (tmp_path / ".omc").mkdir(exist_ok=True)
        (tmp_path / ".omc" / ".env").write_text("EXISTING_VAR=keep_me\n")

        with patch.object(Path, "home", return_value=tmp_path):
            result = await _set_api_key(
                {"action": "set_api_key", "provider": "deepseek", "raw_text": ""},
                api_key="sk-deepseek12345678901234",
            )
            assert result is True
            content = (tmp_path / ".omc" / ".env").read_text()
            assert "EXISTING_VAR=keep_me" in content
            assert "DEEPSEEK_API_KEY=sk-deepseek12345678901234" in content

    @pytest.mark.asyncio
    async def test_no_provider_no_match(self):
        """No provider specified and no match in text → returns False."""
        config = {"action": "set_api_key", "provider": None, "raw_text": "设置密钥"}
        result = await _set_api_key(config, api_key="sk-somekey1234567890")
        assert result is False

    @pytest.mark.asyncio
    async def test_short_api_key_rejected(self, tmp_path):
        config = {"action": "set_api_key", "provider": "glm", "raw_text": "glm"}
        with patch.object(Path, "home", return_value=tmp_path):
            result = await _set_api_key(config, api_key="short")
            assert result is False

    @pytest.mark.asyncio
    async def test_provider_detected_from_text(self, tmp_path):
        """Provider detected from raw_text when not specified."""
        config = {
            "action": "set_api_key",
            "provider": None,
            "raw_text": "配置 qwen 的 key",
        }
        with patch.object(Path, "home", return_value=tmp_path):
            result = await _set_api_key(config, api_key="sk-qwen12345678901234")
            assert result is True
            content = (tmp_path / ".omc" / ".env").read_text()
            assert "DASHSCOPE_API_KEY=sk-qwen12345678901234" in content


# ── _set_default_model ───────────────────────────────────────────


class TestSetDefaultModel:
    @pytest.mark.asyncio
    async def test_sets_model(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path), patch(
            "src.commands.cli_self_config.Prompt.ask", return_value="deepseek"
        ):
            result = await _set_default_model({})
            assert result is True
            config_data = json.loads((tmp_path / ".omc" / "config.json").read_text())
            assert config_data["default_model"] == "deepseek"

    @pytest.mark.asyncio
    async def test_preserves_existing_config(self, tmp_path):
        (tmp_path / ".omc").mkdir(exist_ok=True)
        (tmp_path / ".omc" / "config.json").write_text(
            json.dumps({"other_setting": "keep"})
        )
        with patch.object(Path, "home", return_value=tmp_path), patch(
            "src.commands.cli_self_config.Prompt.ask", return_value="glm"
        ):
            result = await _set_default_model({})
            assert result is True
            config_data = json.loads(
                (tmp_path / ".omc" / "config.json").read_text()
            )
            assert config_data["other_setting"] == "keep"
            assert config_data["default_model"] == "glm"


# ── _set_proxy ───────────────────────────────────────────────────


class TestSetProxy:
    @pytest.mark.asyncio
    async def test_sets_proxy(self, tmp_path):
        (tmp_path / ".omc").mkdir(exist_ok=True)
        with patch.object(Path, "home", return_value=tmp_path), patch(
            "src.commands.cli_self_config.Prompt.ask", return_value="http://proxy:8080"
        ):
            result = await _set_proxy({})
            assert result is True
            content = (tmp_path / ".omc" / ".env").read_text()
            assert "HTTP_PROXY=http://proxy:8080" in content
            assert "HTTPS_PROXY=http://proxy:8080" in content

    @pytest.mark.asyncio
    async def test_adds_http_prefix(self, tmp_path):
        (tmp_path / ".omc").mkdir(exist_ok=True)
        with patch.object(Path, "home", return_value=tmp_path), patch(
            "src.commands.cli_self_config.Prompt.ask", return_value="127.0.0.1:8080"
        ):
            result = await _set_proxy({})
            assert result is True
            content = (tmp_path / ".omc" / ".env").read_text()
            assert "HTTP_PROXY=http://127.0.0.1:8080" in content


# ── _set_temperature ─────────────────────────────────────────────


class TestSetTemperature:
    @pytest.mark.asyncio
    async def test_valid_temperature(self, tmp_path):
        (tmp_path / ".omc").mkdir(exist_ok=True)
        with patch.object(Path, "home", return_value=tmp_path), patch(
            "src.commands.cli_self_config.Prompt.ask", return_value="0.9"
        ):
            result = await _set_temperature({})
            assert result is True
            config_data = json.loads(
                (tmp_path / ".omc" / "config.json").read_text()
            )
            assert config_data["temperature"] == 0.9

    @pytest.mark.asyncio
    async def test_invalid_temperature(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path), patch(
            "src.commands.cli_self_config.Prompt.ask", return_value="not_a_number"
        ):
            result = await _set_temperature({})
            assert result is False

    @pytest.mark.asyncio
    async def test_out_of_range_temperature_still_saves(self, tmp_path):
        """Out-of-range temperature prints warning but still saves."""
        (tmp_path / ".omc").mkdir(exist_ok=True)
        with patch.object(Path, "home", return_value=tmp_path), patch(
            "src.commands.cli_self_config.Prompt.ask", return_value="5.0"
        ):
            result = await _set_temperature({})
            assert result is True


# ── CLI commands ─────────────────────────────────────────────────


class TestCliCommands:
    def test_no_args_shows_help(self):
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "omc self-config" in result.output

    def test_list_configs_empty(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "未配置" in result.output

    def test_list_configs_with_keys(self, tmp_path):
        (tmp_path / ".omc").mkdir(exist_ok=True)
        (tmp_path / ".omc" / ".env").write_text(
            "ZHIPUAI_API_KEY=sk-test123\nDEEPSEEK_API_KEY=sk-deep\n"
        )
        (tmp_path / ".omc" / "config.json").write_text(
            json.dumps({"default_model": "glm", "temperature": 0.7})
        )
        with patch.object(Path, "home", return_value=tmp_path):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "ZHIPUAI_API_KEY" in result.output
            assert "智谱 GLM" in result.output
            assert "0.7" in result.output

    def test_list_configs_corrupt_json(self, tmp_path):
        (tmp_path / ".omc").mkdir(exist_ok=True)
        (tmp_path / ".omc" / "config.json").write_text("not json{{{")
        with patch.object(Path, "home", return_value=tmp_path):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0

    def test_config_with_intent_and_key(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path), patch(
            "src.commands.cli_self_config._set_api_key", return_value=True
        ):
            result = runner.invoke(
                app, ["config", "配置 GLM API KEY", "--key", "sk-glm12345678901234"]
            )
            assert result.exit_code == 0

    def test_config_with_key_provider_only(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path), patch(
            "src.commands.cli_self_config._set_api_key", return_value=True
        ):
            result = runner.invoke(
                app, ["config", "--key", "sk-test1234567890", "--provider", "glm"]
            )
            assert result.exit_code == 0

    def test_config_unknown_intent(self):
        result = runner.invoke(app, ["config", "xyzzy"])
        assert result.exit_code == 0
        assert "无法理解" in result.output

    def test_config_with_extracted_key(self, tmp_path):
        """Intent contains an API key pattern → should be detected."""
        with patch.object(Path, "home", return_value=tmp_path), patch(
            "src.commands.cli_self_config._set_api_key", return_value=True
        ):
            result = runner.invoke(
                app, ["config", "my key sk-abcdefghijklmnopqrstuvwxyz123456"]
            )
            assert result.exit_code == 0


# ── Constants ────────────────────────────────────────────────────


class TestConstants:
    def test_model_providers(self):
        assert "glm" in MODEL_PROVIDERS
        assert "deepseek" in MODEL_PROVIDERS
        assert "api_key_env" in MODEL_PROVIDERS["glm"]

    def test_config_intents(self):
        for _intent_id, info in CONFIG_INTENTS.items():
            assert "patterns" in info
            assert "action" in info
            assert len(info["patterns"]) > 0
