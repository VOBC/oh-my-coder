"""
测试 Agent 配置模块
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.config.agent_config import (
    AgentConfig,
    EnvironmentConfig,
    load_config_file,
    validate_config_file,
    list_configs_in_dir,
    _parse_value,
)


class TestAgentConfig:
    """AgentConfig 模型测试"""

    def test_from_dict_basic(self) -> None:
        data = {
            "name": "code-reviewer",
            "description": "代码审查助手",
            "model": "deepseek",
            "tools": ["git", "grep"],
            "permissions": {
                "allowed_patterns": ["git", "grep"],
                "denied_patterns": ["rm -rf /"],
            },
            "environment": {
                "max_tokens": 8000,
                "temperature": 0.7,
                "timeout": 60,
                "retry": 3,
            },
            "prompts": {
                "system": "你是一个专业的代码审查员",
            },
        }

        config = AgentConfig.from_dict(data)

        assert config.name == "code-reviewer"
        assert config.description == "代码审查助手"
        assert config.model == "deepseek"
        assert config.tools == ["git", "grep"]
        assert config.environment.max_tokens == 8000
        assert config.environment.temperature == 0.7
        assert config.get_system_prompt() == "你是一个专业的代码审查员"

    def test_to_dict_roundtrip(self) -> None:
        config = AgentConfig(
            name="test-agent",
            description="测试代理",
            model="kimi",
            tools=["shell", "file_read"],
            environment=EnvironmentConfig(max_tokens=4000, temperature=0.5),
            prompts={"system": "Test prompt"},
        )

        data = config.to_dict()
        restored = AgentConfig.from_dict(data)

        assert restored.name == config.name
        assert restored.model == config.model
        assert restored.environment.max_tokens == config.environment.max_tokens

    def test_render_template(self) -> None:
        config = AgentConfig(
            name="reviewer",
            description="",
            prompts={
                "review_template": "请审查以下代码变更：\n{{diff}}\n文件: {{file}}",
            },
        )

        rendered = config.render_template(
            "review_template", diff="@@ test", file="main.py"
        )
        assert "@@ test" in rendered
        assert "main.py" in rendered

    def test_validate_errors(self) -> None:
        # 无效 name
        config = AgentConfig(name="Invalid Name!", description="")
        errors = config.validate()
        assert any("name" in e for e in errors)

        # temperature 超范围
        config2 = AgentConfig(
            name="ok",
            description="",
            environment=EnvironmentConfig(temperature=5.0),
        )
        errors2 = config2.validate()
        assert any("temperature" in e for e in errors2)

        # 无效正则
        config3 = AgentConfig(
            name="ok",
            description="",
            permissions={"denied_patterns": ["[invalid("]},
        )
        errors3 = config3.validate()
        assert any("denied_patterns" in e for e in errors3)


class TestLoadConfigFile:
    """配置文件加载测试"""

    def test_load_json(self) -> None:
        data = {
            "name": "json-agent",
            "description": "JSON 配置测试",
            "model": "deepseek",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name

        try:
            config = load_config_file(path)
            assert config.name == "json-agent"
            assert config.description == "JSON 配置测试"
        finally:
            Path(path).unlink()

    def test_load_yaml_simple(self) -> None:
        """测试简单 YAML 解析（标准库 fallback）"""
        yaml_content = "name: yaml-agent\ndescription: YAML 测试\nmodel: kimi\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name

        try:
            config = load_config_file(path)
            assert config.name == "yaml-agent"
            assert config.model == "kimi"
        finally:
            Path(path).unlink()

    def test_load_yaml_with_list(self) -> None:
        """测试带列表的 YAML"""
        yaml_content = (
            "name: list-agent\n"
            "description: 列表测试\n"
            "tools:\n"
            "  - git\n"
            "  - grep\n"
            "  - shell\n"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name

        try:
            config = load_config_file(path)
            assert config.name == "list-agent"
            assert "git" in config.tools
        finally:
            Path(path).unlink()

    def test_load_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_config_file("/nonexistent/config.yaml")

    def test_load_unsupported_format(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("name: test\n")
            path = f.name

        try:
            with pytest.raises(ValueError, match="不支持"):
                load_config_file(path)
        finally:
            Path(path).unlink()

    def test_validate_config_file(self) -> None:
        """验证合法配置文件"""
        data = {"name": "valid-agent", "description": "合法"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name

        try:
            valid, errors = validate_config_file(path)
            assert valid is True
            assert errors == []
        finally:
            Path(path).unlink()


class TestListConfigs:
    """配置目录扫描测试"""

    def test_list_configs_in_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建几个配置文件
            (Path(tmpdir) / "a.json").write_text('{"name": "a"}')
            (Path(tmpdir) / "b.yaml").write_text("name: b\n")
            (Path(tmpdir) / "c.txt").write_text("ignore")

            paths = list_configs_in_dir(tmpdir)
            assert len(paths) == 2  # .txt 不算
            assert any("a.json" in p for p in paths)
            assert any("b.yaml" in p for p in paths)

    def test_list_configs_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = list_configs_in_dir(tmpdir)
            assert paths == []


class TestParseValue:
    """YAML 值解析测试"""

    def test_bool_values(self) -> None:
        assert _parse_value("true") is True
        assert _parse_value("false") is False

    def test_int_values(self) -> None:
        assert _parse_value("42") == 42
        assert _parse_value("-10") == -10

    def test_float_values(self) -> None:
        assert _parse_value("3.14") == 3.14

    def test_string_values(self) -> None:
        assert _parse_value("hello") == "hello"
        assert _parse_value('"quoted"') == "quoted"
        assert _parse_value("'single'") == "single"

    def test_null_value(self) -> None:
        assert _parse_value("null") is None
