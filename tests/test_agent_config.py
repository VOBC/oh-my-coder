"""Tests for src/config/agent_config.py"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config.agent_config import (
    AgentConfig,
    EnvironmentConfig,
    ToolConfig,
    _load_yaml,
    _parse_value,
    list_configs_in_dir,
    load_config_dir,
    load_config_file,
    validate_config_file,
)


class TestToolConfig:
    def test_default_values(self):
        config = ToolConfig(name="test_tool")
        assert config.name == "test_tool"
        assert config.enabled is True
        assert config.options == {}

    def test_custom_values(self):
        config = ToolConfig(name="my_tool", enabled=False, options={"timeout": 30})
        assert config.name == "my_tool"
        assert config.enabled is False
        assert config.options == {"timeout": 30}


class TestEnvironmentConfig:
    def test_default_values(self):
        env = EnvironmentConfig()
        assert env.max_tokens == 8000
        assert env.temperature == 0.7
        assert env.timeout == 60
        assert env.retry == 3

    def test_custom_values(self):
        env = EnvironmentConfig(max_tokens=16000, temperature=0.5, timeout=120, retry=5)
        assert env.max_tokens == 16000
        assert env.temperature == 0.5
        assert env.timeout == 120
        assert env.retry == 5


class TestAgentConfig:
    def test_default_values(self):
        config = AgentConfig(name="test_agent", description="Test agent")
        assert config.name == "test_agent"
        assert config.description == "Test agent"
        assert config.model == "deepseek"
        assert config.tools == []
        assert config.permissions == {}
        assert config.prompts == {}
        assert config.metadata == {}

    def test_get_system_prompt_default(self):
        config = AgentConfig(name="reviewer", description="Code reviewer")
        assert config.get_system_prompt() == "你是一个专业的 reviewer Agent。"

    def test_get_system_prompt_custom(self):
        config = AgentConfig(
            name="reviewer",
            description="Code reviewer",
            prompts={"system": "You are a code reviewer."},
        )
        assert config.get_system_prompt() == "You are a code reviewer."

    def test_get_prompt_template(self):
        config = AgentConfig(
            name="test",
            description="test",
            prompts={"review": "Review this code: {{code}}"},
        )
        assert config.get_prompt_template("review") == "Review this code: {{code}}"
        assert config.get_prompt_template("nonexistent") == ""

    def test_render_template(self):
        config = AgentConfig(
            name="test",
            description="test",
            prompts={"greet": "Hello {{name}}, welcome to {{place}}!"},
        )
        result = config.render_template("greet", name="Alice", place="Wonderland")
        assert result == "Hello Alice, welcome to Wonderland!"

    def test_render_template_missing_key(self):
        config = AgentConfig(
            name="test",
            description="test",
            prompts={"greet": "Hello {{name}}!"},
        )
        result = config.render_template("greet", name="Bob")
        assert result == "Hello Bob!"

    def test_to_dict(self):
        config = AgentConfig(
            name="test_agent",
            description="Test description",
            model="gpt-4",
            tools=["tool1", "tool2"],
            permissions={"read": True},
            prompts={"system": "Be helpful"},
            metadata={"version": "1.0"},
        )
        data = config.to_dict()
        assert data["name"] == "test_agent"
        assert data["description"] == "Test description"
        assert data["model"] == "gpt-4"
        assert data["tools"] == ["tool1", "tool2"]
        assert data["permissions"] == {"read": True}
        assert data["environment"]["max_tokens"] == 8000
        assert data["prompts"] == {"system": "Be helpful"}
        assert data["metadata"] == {"version": "1.0"}

    def test_from_dict_minimal(self):
        data = {"name": "minimal_agent"}
        config = AgentConfig.from_dict(data)
        assert config.name == "minimal_agent"
        assert config.description == ""
        assert config.model == "deepseek"
        assert config.tools == []

    def test_from_dict_full(self):
        data = {
            "name": "full_agent",
            "description": "Full config",
            "model": "claude",
            "tools": ["tool_a"],
            "permissions": {"write": False},
            "environment": {
                "max_tokens": 4000,
                "temperature": 0.3,
                "timeout": 30,
                "retry": 2,
            },
            "prompts": {"system": "Custom prompt"},
            "metadata": {"author": "test"},
        }
        config = AgentConfig.from_dict(data)
        assert config.name == "full_agent"
        assert config.model == "claude"
        assert config.environment.max_tokens == 4000
        assert config.environment.temperature == 0.3
        assert config.environment.timeout == 30
        assert config.environment.retry == 2

    def test_validate_valid(self):
        config = AgentConfig(name="valid_agent", description="Valid")
        errors = config.validate()
        assert errors == []

    def test_validate_empty_name(self):
        config = AgentConfig(name="", description="Empty name")
        errors = config.validate()
        assert len(errors) > 0
        assert "name" in errors[0]

    def test_validate_invalid_name(self):
        config = AgentConfig(name="Invalid Name!", description="Invalid name")
        errors = config.validate()
        assert len(errors) > 0
        assert "name" in errors[0]

    def test_validate_low_max_tokens(self):
        config = AgentConfig(
            name="test",
            description="test",
            environment=EnvironmentConfig(max_tokens=50),
        )
        errors = config.validate()
        assert len(errors) > 0
        assert "max_tokens" in errors[0]

    def test_validate_invalid_temperature(self):
        config = AgentConfig(
            name="test",
            description="test",
            environment=EnvironmentConfig(temperature=3.0),
        )
        errors = config.validate()
        assert len(errors) > 0
        assert "temperature" in errors[0]

    def test_validate_denied_patterns_invalid_regex(self):
        config = AgentConfig(
            name="test",
            description="test",
            permissions={"denied_patterns": ["[invalid("]},
        )
        errors = config.validate()
        assert len(errors) > 0
        assert "denied_patterns" in errors[0]


class TestParseValue:
    def test_parse_bool_true(self):
        assert _parse_value("true") is True
        assert _parse_value("True") is True
        assert _parse_value("TRUE") is True

    def test_parse_bool_false(self):
        assert _parse_value("false") is False
        assert _parse_value("False") is False
        assert _parse_value("FALSE") is False

    def test_parse_null(self):
        assert _parse_value("null") is None
        assert _parse_value("Null") is None
        assert _parse_value("NULL") is None

    def test_parse_int(self):
        assert _parse_value("42") == 42
        assert _parse_value("0") == 0
        assert _parse_value("-10") == -10

    def test_parse_float(self):
        assert _parse_value("3.14") == 3.14
        assert _parse_value("0.5") == 0.5
        assert _parse_value("-2.5") == -2.5

    def test_parse_string(self):
        assert _parse_value("hello") == "hello"
        assert _parse_value('"quoted"') == "quoted"
        assert _parse_value("'single'") == "single"


class TestLoadYaml:
    def test_load_simple_key_value(self):
        result = _load_yaml("name: test\nmodel: gpt-4")
        assert result.get("name") == "test"
        assert result.get("model") == "gpt-4"

    def test_load_with_comments(self):
        result = _load_yaml("# comment\nname: test\n# another comment")
        assert result.get("name") == "test"

    def test_load_empty(self):
        result = _load_yaml("")
        assert result == {}

    def test_load_boolean_values(self):
        result = _load_yaml("enabled: true\ndisabled: false")
        assert result.get("enabled") is True
        assert result.get("disabled") is False


class TestLoadConfigFile:
    def test_load_json_file(self, tmp_path: Path):
        config_data = {
            "name": "json_agent",
            "description": "JSON config",
            "model": "gpt-4",
        }
        json_file = tmp_path / "agent.json"
        json_file.write_text(json.dumps(config_data))

        config = load_config_file(json_file)
        assert config.name == "json_agent"
        assert config.model == "gpt-4"

    def test_load_yaml_file(self, tmp_path: Path):
        yaml_content = "name: yaml_agent\ndescription: YAML config\nmodel: claude\n"
        yaml_file = tmp_path / "agent.yaml"
        yaml_file.write_text(yaml_content)

        config = load_config_file(yaml_file)
        assert config.name == "yaml_agent"
        assert config.model == "claude"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config_file("/nonexistent/path.yaml")

    def test_unsupported_format(self, tmp_path: Path):
        txt_file = tmp_path / "agent.txt"
        txt_file.write_text("name: test")

        with pytest.raises(ValueError, match="不支持的文件格式"):
            load_config_file(txt_file)


class TestLoadConfigDir:
    def test_load_multiple_configs(self, tmp_path: Path):
        config1 = {"name": "agent1", "description": "First"}
        config2 = {"name": "agent2", "description": "Second"}

        (tmp_path / "agent1.json").write_text(json.dumps(config1))
        (tmp_path / "agent2.yaml").write_text("name: agent2\ndescription: Second\n")

        configs = load_config_dir(tmp_path)
        assert len(configs) == 2
        names = [c.name for c in configs]
        assert "agent1" in names
        assert "agent2" in names

    def test_empty_dir(self, tmp_path: Path):
        configs = load_config_dir(tmp_path)
        assert configs == []

    def test_nonexistent_dir(self):
        configs = load_config_dir("/nonexistent/dir")
        assert configs == []

    def test_skip_invalid_files(self, tmp_path: Path):
        valid = {"name": "valid", "description": "Valid"}
        (tmp_path / "valid.json").write_text(json.dumps(valid))
        (tmp_path / "invalid.json").write_text("{ invalid json }")

        configs = load_config_dir(tmp_path)
        assert len(configs) == 1
        assert configs[0].name == "valid"


class TestValidateConfigFile:
    def test_valid_config(self, tmp_path: Path):
        config = {"name": "valid_agent", "description": "Valid"}
        config_file = tmp_path / "valid.json"
        config_file.write_text(json.dumps(config))

        is_valid, errors = validate_config_file(config_file)
        assert is_valid is True
        assert errors == []

    def test_invalid_config(self, tmp_path: Path):
        config = {"name": "Invalid Name!", "description": "Invalid name format"}
        config_file = tmp_path / "invalid.json"
        config_file.write_text(json.dumps(config))

        is_valid, errors = validate_config_file(config_file)
        assert is_valid is False
        assert len(errors) > 0

    def test_nonexistent_file(self):
        is_valid, errors = validate_config_file("/nonexistent.yaml")
        assert is_valid is False
        assert "不存在" in errors[0]

    def test_malformed_json(self, tmp_path: Path):
        config_file = tmp_path / "malformed.json"
        config_file.write_text("{ not valid json }")

        is_valid, errors = validate_config_file(config_file)
        assert is_valid is False


class TestListConfigsInDir:
    def test_list_configs(self, tmp_path: Path):
        (tmp_path / "agent1.yaml").write_text("name: a1")
        (tmp_path / "agent2.yml").write_text("name: a2")
        (tmp_path / "agent3.json").write_text('{"name": "a3"}')
        (tmp_path / "readme.txt").write_text("not a config")

        paths = list_configs_in_dir(tmp_path)
        assert len(paths) == 3
        assert all(str(p).endswith((".yaml", ".yml", ".json")) for p in paths)

    def test_empty_dir(self, tmp_path: Path):
        paths = list_configs_in_dir(tmp_path)
        assert paths == []

    def test_nonexistent_dir(self):
        paths = list_configs_in_dir("/nonexistent")
        assert paths == []

    def test_sorted_output(self, tmp_path: Path):
        (tmp_path / "z_agent.yaml").write_text("name: z")
        (tmp_path / "a_agent.yaml").write_text("name: a")
        (tmp_path / "m_agent.yaml").write_text("name: m")

        paths = list_configs_in_dir(tmp_path)
        names = [Path(p).name for p in paths]
        assert names == sorted(names)
