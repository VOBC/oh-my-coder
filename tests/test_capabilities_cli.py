"""
测试 capabilities CLI 命令

测试 src/capabilities/__init__.py 中的 Typer 命令。
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.capabilities import app
from src.capabilities.package import CapabilityPackage, CapabilityPackageManager


@pytest.fixture
def runner():
    """CLI 测试运行器"""
    return CliRunner()


@pytest.fixture
def mock_manager():
    """模拟 CapabilityPackageManager"""
    manager = MagicMock(spec=CapabilityPackageManager)
    manager._get_package_path = MagicMock(return_value=Path("/tmp/test.cap"))
    return manager


class TestExportCommand:
    """测试 export 命令"""

    @patch("src.capabilities._get_manager")
    @patch("src.capabilities._load_current_config")
    @patch("src.capabilities.Prompt")
    @patch("src.capabilities.Console")
    def test_export_success(self, mock_console, mock_prompt, mock_load_config, mock_get_manager, runner):
        """测试成功导出能力包"""
        mock_manager = MagicMock()
        mock_package = MagicMock()
        mock_package.name = "test-cap"
        mock_package.version = "1.0.0"
        mock_package.description = "Test description"
        mock_package.author = "tester"
        mock_package.tags = ["test"]
        mock_package.validate.return_value = []
        mock_manager.export_from_config.return_value = mock_package
        mock_get_manager.return_value = mock_manager

        mock_load_config.return_value = (
            {"agent1": {"tier": "medium"}},
            {"temperature": 0.7},
            ["tool1"],
            {"system": "You are helpful"},
        )

        result = runner.invoke(app, ["export", "test-cap", "--description", "Test desc", "--author", "tester"])

        assert result.exit_code == 0
        mock_manager.export_from_config.assert_called_once()

    @patch("src.capabilities._get_manager")
    @patch("src.capabilities._load_current_config")
    @patch("src.capabilities.Prompt")
    def test_export_with_interactive_prompts(self, mock_prompt, mock_load_config, mock_get_manager, runner):
        """测试交互式输入"""
        mock_manager = MagicMock()
        mock_package = MagicMock()
        mock_package.validate.return_value = []
        mock_manager.export_from_config.return_value = mock_package
        mock_get_manager.return_value = mock_manager

        mock_prompt.ask.side_effect = ["Auto description", "auto-author"]

        mock_load_config.return_value = ({}, {}, [], {})

        result = runner.invoke(app, ["export", "test-cap"])

        assert result.exit_code == 0
        assert mock_prompt.ask.call_count >= 2

    @patch("src.capabilities._get_manager")
    @patch("src.capabilities._load_current_config")
    def test_export_validation_failure(self, mock_load_config, mock_get_manager, runner):
        """测试验证失败"""
        mock_manager = MagicMock()
        mock_package = MagicMock()
        mock_package.validate.return_value = ["名称不能为空", "版本格式错误"]
        mock_manager.export_from_config.return_value = mock_package
        mock_get_manager.return_value = mock_manager

        mock_load_config.return_value = ({}, {}, [], {})

        result = runner.invoke(app, ["export", "test-cap", "--description", "Test", "--author", "tester"])

        assert result.exit_code != 0

    @patch("src.capabilities._get_manager")
    @patch("src.capabilities._load_current_config")
    @patch("src.capabilities.Prompt")
    def test_export_with_tags(self, mock_prompt, mock_load_config, mock_get_manager, runner):
        """测试带标签导出"""
        mock_manager = MagicMock()
        mock_package = MagicMock()
        mock_package.validate.return_value = []
        mock_manager.export_from_config.return_value = mock_package
        mock_get_manager.return_value = mock_manager

        mock_load_config.return_value = ({}, {}, [], {})
        mock_prompt.ask.side_effect = ["Auto description", "auto-author"]

        result = runner.invoke(app, ["export", "test-cap", "-t", "python,web,ai"])

        assert result.exit_code == 0
        call_args = mock_manager.export_from_config.call_args
        assert call_args[1]["tags"] == ["python", "web", "ai"]


class TestListCommand:
    """测试 list 命令"""

    @patch("src.capabilities._get_manager")
    def test_list_empty(self, mock_get_manager, runner):
        """测试空列表"""
        mock_manager = MagicMock()
        mock_manager.list_packages.return_value = []
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "暂无能力包" in result.output

    @patch("src.capabilities._get_manager")
    def test_list_with_packages(self, mock_get_manager, runner):
        """测试显示能力包列表"""
        mock_manager = MagicMock()
        mock_packages = [
            CapabilityPackage(
                name="pkg1",
                version="1.0.0",
                description="Package 1",
                author="author1",
                created_at="2024-01-01T00:00:00",
                tags=["test"],
            ),
            CapabilityPackage(
                name="pkg2",
                version="2.0.0",
                description="Package 2",
                author="author2",
                created_at="2024-01-02T00:00:00",
            ),
        ]
        mock_manager.list_packages.return_value = mock_packages
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0

    @patch("src.capabilities._get_manager")
    def test_list_verbose(self, mock_get_manager, runner):
        """测试详细列表"""
        mock_manager = MagicMock()
        mock_packages = [
            CapabilityPackage(
                name="pkg1",
                version="1.0.0",
                description="Package 1",
                author="author1",
                created_at="2024-01-01T00:00:00",
                tags=["test", "demo"],
            ),
        ]
        mock_manager.list_packages.return_value = mock_packages
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["list", "--verbose"])

        assert result.exit_code == 0


class TestApplyCommand:
    """测试 apply 命令"""

    @patch("src.capabilities._get_manager")
    @patch("src.capabilities._load_config_file")
    @patch("src.capabilities._save_config_file")
    @patch("src.capabilities.Confirm")
    def test_apply_success(self, mock_confirm, mock_save, mock_load, mock_get_manager, runner):
        """测试成功应用能力包"""
        mock_manager = MagicMock()
        mock_package = CapabilityPackage(
            name="test-cap",
            version="1.0.0",
            description="Test",
            author="tester",
            created_at="2024-01-01T00:00:00",
            agents={"agent1": {"tier": "high"}},
            model_config={"temperature": 0.7},
            tools=["tool1"],
            prompts={"system": "Hello"},
        )
        mock_manager.get_package.return_value = mock_package
        mock_manager.apply_package.return_value = {
            "agents": {"agent1": {"tier": "high"}},
            "model_config": {"temperature": 0.7},
            "tools": ["tool1"],
            "prompts": {"system": "Hello"},
        }
        mock_get_manager.return_value = mock_manager
        mock_load.return_value = {}

        mock_confirm.ask.return_value = True

        result = runner.invoke(app, ["apply", "test-cap"])

        assert result.exit_code == 0
        mock_manager.apply_package.assert_called_once()
        mock_save.assert_called_once()

    @patch("src.capabilities._get_manager")
    def test_apply_nonexistent(self, mock_get_manager, runner):
        """测试应用不存在的能力包"""
        mock_manager = MagicMock()
        mock_manager.get_package.return_value = None
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["apply", "nonexistent"])

        assert result.exit_code != 0

    @patch("src.capabilities._get_manager")
    @patch("src.capabilities.Confirm")
    def test_apply_dry_run(self, mock_confirm, mock_get_manager, runner):
        """测试 dry-run 模式"""
        mock_manager = MagicMock()
        mock_package = CapabilityPackage(
            name="test-cap",
            version="1.0.0",
            description="Test",
            author="tester",
            created_at="2024-01-01T00:00:00",
            agents={"agent1": {}},
        )
        mock_manager.get_package.return_value = mock_package
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["apply", "test-cap", "--dry-run"])

        assert result.exit_code == 0
        assert "Dry-run" in result.output
        mock_manager.apply_package.assert_not_called()

    @patch("src.capabilities._get_manager")
    @patch("src.capabilities._load_config_file")
    @patch("src.capabilities._save_config_file")
    @patch("src.capabilities.Confirm")
    def test_apply_cancelled(self, mock_confirm, mock_save, mock_load, mock_get_manager, runner):
        """测试取消应用"""
        mock_manager = MagicMock()
        mock_package = CapabilityPackage(
            name="test-cap",
            version="1.0.0",
            description="Test",
            author="tester",
            created_at="2024-01-01T00:00:00",
        )
        mock_manager.get_package.return_value = mock_package
        mock_get_manager.return_value = mock_manager
        mock_load.return_value = {}

        mock_confirm.ask.return_value = False

        result = runner.invoke(app, ["apply", "test-cap"])

        assert result.exit_code == 0
        mock_manager.apply_package.assert_not_called()
        mock_save.assert_not_called()

    @patch("src.capabilities._get_manager")
    @patch("src.capabilities._load_config_file")
    @patch("src.capabilities._save_config_file")
    def test_apply_force(self, mock_save, mock_load, mock_get_manager, runner):
        """测试强制应用（无需确认）"""
        mock_manager = MagicMock()
        mock_package = CapabilityPackage(
            name="test-cap",
            version="1.0.0",
            description="Test",
            author="tester",
            created_at="2024-01-01T00:00:00",
            agents={"agent1": {}},
        )
        mock_manager.get_package.return_value = mock_package
        mock_manager.apply_package.return_value = {"agents": {}}
        mock_get_manager.return_value = mock_manager
        mock_load.return_value = {}

        result = runner.invoke(app, ["apply", "test-cap", "--force"])

        assert result.exit_code == 0
        mock_manager.apply_package.assert_called_once()


class TestPublishCommand:
    """测试 publish 命令"""

    def test_publish_not_implemented(self, runner):
        """测试发布功能（开发中）"""
        result = runner.invoke(app, ["publish", "test-cap"])

        assert result.exit_code == 0
        assert "开发中" in result.output


class TestShowCommand:
    """测试 show 命令"""

    @patch("src.capabilities._get_manager")
    def test_show_success(self, mock_get_manager, runner):
        """测试成功显示能力包详情"""
        mock_manager = MagicMock()
        mock_package = CapabilityPackage(
            name="test-cap",
            version="1.0.0",
            description="Test description",
            author="tester",
            created_at="2024-01-01T00:00:00",
            tags=["test", "demo"],
            agents={"agent1": {"tier": "medium"}},
            tools=["tool1", "tool2"],
            examples=[{"input": "test", "output": "result"}],
            readme="# Test\n\nThis is a test.",
        )
        mock_manager.get_package.return_value = mock_package
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["show", "test-cap"])

        assert result.exit_code == 0
        assert "test-cap" in result.output
        assert "Test description" in result.output

    @patch("src.capabilities._get_manager")
    def test_show_nonexistent(self, mock_get_manager, runner):
        """测试显示不存在的能力包"""
        mock_manager = MagicMock()
        mock_manager.get_package.return_value = None
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["show", "nonexistent"])

        assert result.exit_code != 0


class TestDeleteCommand:
    """测试 delete 命令"""

    @patch("src.capabilities._get_manager")
    @patch("src.capabilities.Confirm")
    def test_delete_success(self, mock_confirm, mock_get_manager, runner):
        """测试成功删除能力包"""
        mock_manager = MagicMock()
        mock_package = CapabilityPackage(
            name="test-cap",
            version="1.0.0",
            description="Test",
            author="tester",
            created_at="2024-01-01T00:00:00",
        )
        mock_manager.get_package.return_value = mock_package
        mock_manager.delete_package.return_value = True
        mock_get_manager.return_value = mock_manager

        mock_confirm.ask.return_value = True

        result = runner.invoke(app, ["delete", "test-cap"])

        assert result.exit_code == 0
        mock_manager.delete_package.assert_called_once_with("test-cap")

    @patch("src.capabilities._get_manager")
    def test_delete_nonexistent(self, mock_get_manager, runner):
        """测试删除不存在的能力包"""
        mock_manager = MagicMock()
        mock_manager.get_package.return_value = None
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["delete", "nonexistent"])

        assert result.exit_code != 0

    @patch("src.capabilities._get_manager")
    @patch("src.capabilities.Confirm")
    def test_delete_cancelled(self, mock_confirm, mock_get_manager, runner):
        """测试取消删除"""
        mock_manager = MagicMock()
        mock_package = CapabilityPackage(
            name="test-cap",
            version="1.0.0",
            description="Test",
            author="tester",
            created_at="2024-01-01T00:00:00",
        )
        mock_manager.get_package.return_value = mock_package
        mock_get_manager.return_value = mock_manager

        mock_confirm.ask.return_value = False

        result = runner.invoke(app, ["delete", "test-cap"])

        assert result.exit_code == 0
        mock_manager.delete_package.assert_not_called()

    @patch("src.capabilities._get_manager")
    def test_delete_force(self, mock_get_manager, runner):
        """测试强制删除（无需确认）"""
        mock_manager = MagicMock()
        mock_package = CapabilityPackage(
            name="test-cap",
            version="1.0.0",
            description="Test",
            author="tester",
            created_at="2024-01-01T00:00:00",
        )
        mock_manager.get_package.return_value = mock_package
        mock_manager.delete_package.return_value = True
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["delete", "test-cap", "--force"])

        assert result.exit_code == 0
        mock_manager.delete_package.assert_called_once()


class TestHelperFunctions:
    """测试辅助函数"""

    @patch("src.capabilities.get_manager")
    def test_get_manager(self, mock_get_manager):
        """测试 _get_manager 函数"""
        from src.capabilities import _get_manager

        mock_instance = MagicMock()
        mock_get_manager.return_value = mock_instance

        result = _get_manager()

        assert result == mock_instance
        mock_get_manager.assert_called_once()

    def test_load_current_config_with_path(self, tmp_path):
        """测试从指定路径加载配置"""
        from src.capabilities import _load_current_config

        config_file = tmp_path / "config.json"
        config_file.write_text(
            '{"agents": {"agent1": {}}, "model_config": {"temperature": 0.7}, "tools": ["tool1"], "prompts": {"system": "Hello"}}'
        )

        agents, model_config, tools, prompts = _load_current_config(config_path=config_file)

        assert "agent1" in agents
        assert model_config["temperature"] == 0.7
        assert "tool1" in tools
        assert "system" in prompts

    def test_load_current_config_defaults(self):
        """测试加载默认配置"""
        from src.capabilities import _load_current_config

        agents, model_config, tools, prompts = _load_current_config()

        assert "explore" in agents
        assert "analyst" in agents
        assert model_config["default_model"] == "deepseek"
        assert "file_read" in tools
        assert "system" in prompts

    @patch("pathlib.Path.exists")
    def test_load_config_file(self, mock_exists):
        """测试加载配置文件"""
        from src.capabilities import _load_config_file

        mock_exists.return_value = True

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = '{"agents": {}}'

            result = _load_config_file()

            assert result is not None
            assert "agents" in result

    def test_save_config_file(self, tmp_path):
        """测试保存配置文件"""
        from src.capabilities import _save_config_file

        config = {
            "agents": {"agent1": {"tier": "high"}},
            "model_config": {"temperature": 0.7},
            "tools": ["tool1"],
            "prompts": {"system": "Hello"},
        }

        with patch("pathlib.Path.mkdir"):
            with patch("builtins.open", create=True) as mock_open:
                _save_config_file(config)

                mock_open.assert_called_once()
