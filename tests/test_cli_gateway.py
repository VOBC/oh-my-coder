"""
Tests for cli_gateway.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commands.cli_gateway import app


class TestGatewayCLI:
    """Test suite for Gateway CLI commands"""

    @patch("src.commands.cli_gateway._load_gateway")
    def test_status_command(self, mock_load_gateway):
        """Test gateway status command"""
        runner = CliRunner()

        # Mock gateway instance
        mock_gateway = MagicMock()
        mock_gateway.status.return_value = {
            "started_platforms": ["telegram"],
            "handlers": {
                "telegram": {
                    "type": "TelegramHandler",
                    "configured": True,
                    "started": True,
                },
                "discord": {
                    "type": "NoopHandler",
                    "configured": False,
                    "started": False,
                },
            },
        }
        mock_load_gateway.return_value = mock_gateway

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "Gateway Status" in result.output
        mock_gateway.status.assert_called_once()

    @patch("src.commands.cli_gateway._load_gateway")
    def test_status_command_error(self, mock_load_gateway):
        """Test gateway status command when error occurs"""
        runner = CliRunner()

        mock_gateway = MagicMock()
        mock_gateway.status.side_effect = Exception("Connection error")
        mock_load_gateway.return_value = mock_gateway

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "错误" in result.output

    @patch("src.commands.cli_gateway._load_gateway")
    def test_status_no_platforms_started(self, mock_load_gateway):
        """Test gateway status when no platforms are started"""
        runner = CliRunner()

        mock_gateway = MagicMock()
        mock_gateway.status.return_value = {
            "started_platforms": [],
            "handlers": {
                "telegram": {
                    "type": "NoopHandler",
                    "configured": False,
                    "started": False,
                },
                "discord": {
                    "type": "NoopHandler",
                    "configured": False,
                    "started": False,
                },
            },
        }
        mock_load_gateway.return_value = mock_gateway

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "(none)" in result.output

    @patch("src.commands.cli_gateway._load_gateway")
    def test_status_multiple_platforms(self, mock_load_gateway):
        """Test gateway status with multiple platforms configured"""
        runner = CliRunner()

        mock_gateway = MagicMock()
        mock_gateway.status.return_value = {
            "started_platforms": ["telegram", "discord"],
            "handlers": {
                "telegram": {
                    "type": "TelegramHandler",
                    "configured": True,
                    "started": True,
                },
                "discord": {
                    "type": "DiscordHandler",
                    "configured": True,
                    "started": True,
                },
                "whatsapp": {
                    "type": "NoopHandler",
                    "configured": False,
                    "started": False,
                },
            },
        }
        mock_load_gateway.return_value = mock_gateway

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "telegram" in result.output.lower()
        assert "discord" in result.output.lower()

    @patch("src.gateway.gateway.Gateway")
    @patch("src.commands.cli_gateway.asyncio.run")
    def test_start_command_with_telegram_token(self, mock_asyncio_run, mock_gateway_class):
        """Test gateway start command with telegram token"""
        runner = CliRunner()

        mock_gateway_instance = MagicMock()
        mock_gateway_class.return_value = mock_gateway_instance

        result = runner.invoke(app, ["start", "--telegram", "fake-token"])

        assert result.exit_code == 0
        assert "启动网关" in result.output
        assert "Telegram: 已配置" in result.output
        mock_gateway_class.assert_called_once()

    @patch("src.gateway.gateway.Gateway")
    @patch("src.commands.cli_gateway.asyncio.run")
    def test_start_command_with_discord_token(self, mock_asyncio_run, mock_gateway_class):
        """Test gateway start command with discord token"""
        runner = CliRunner()

        mock_gateway_instance = MagicMock()
        mock_gateway_class.return_value = mock_gateway_instance

        result = runner.invoke(app, ["start", "--discord", "fake-discord-token"])

        assert result.exit_code == 0
        assert "启动网关" in result.output
        assert "Discord: 已配置" in result.output

    @patch("src.gateway.gateway.Gateway")
    @patch("src.commands.cli_gateway.asyncio.run")
    def test_start_command_with_both_tokens(self, mock_asyncio_run, mock_gateway_class):
        """Test gateway start command with both tokens"""
        runner = CliRunner()

        mock_gateway_instance = MagicMock()
        mock_gateway_class.return_value = mock_gateway_instance

        result = runner.invoke(
            app,
            ["start", "--telegram", "fake-token", "--discord", "fake-discord-token"],
        )

        assert result.exit_code == 0
        assert "Telegram: 已配置" in result.output
        assert "Discord: 已配置" in result.output

    @patch("src.gateway.gateway.Gateway")
    @patch("src.commands.cli_gateway.asyncio.run")
    def test_start_command_with_env_token(self, mock_asyncio_run, mock_gateway_class):
        """Test gateway start command using environment variable"""
        runner = CliRunner()

        mock_gateway_instance = MagicMock()
        mock_gateway_class.return_value = mock_gateway_instance

        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "env-token"}):
            result = runner.invoke(app, ["start"])

        assert result.exit_code == 0
        assert "Telegram: 已配置" in result.output

    def test_start_command_no_token(self):
        """Test gateway start command without any token"""
        runner = CliRunner()

        # Ensure no tokens in environment
        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["start"])

        assert result.exit_code == 1
        assert "未指定任何平台 Token" in result.output

    @patch("src.commands.cli_gateway.asyncio.run")
    def test_start_command_import_error(self, mock_asyncio_run):
        """Test gateway start command when import fails"""
        runner = CliRunner()

        # Mock the Gateway import to raise ImportError
        with patch.dict("sys.modules", {"src.gateway.gateway": None}):
            result = runner.invoke(app, ["start", "--telegram", "fake-token"])

        # The command should handle the error gracefully
        assert result.exit_code == 1

    @patch("src.gateway.gateway.Gateway")
    @patch("src.commands.cli_gateway.asyncio.run")
    def test_start_command_general_exception(self, mock_asyncio_run, mock_gateway_class):
        """Test gateway start command when general exception occurs"""
        runner = CliRunner()

        mock_gateway_instance = MagicMock()
        mock_gateway_class.return_value = mock_gateway_instance
        # Make asyncio.run raise an exception
        mock_asyncio_run.side_effect = Exception("Unexpected error")

        result = runner.invoke(app, ["start", "--telegram", "fake-token"])

        assert result.exit_code == 1
        assert "启动失败" in result.output

    def test_stop_command(self):
        """Test gateway stop command"""
        runner = CliRunner()

        result = runner.invoke(app, ["stop"])

        assert result.exit_code == 0
        assert "停止网关" in result.output

    def test_help_command(self):
        """Test gateway help command"""
        runner = CliRunner()

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "多平台消息网关" in result.output

    def test_start_help_command(self):
        """Test gateway start help command"""
        runner = CliRunner()

        result = runner.invoke(app, ["start", "--help"])

        assert result.exit_code == 0
        assert "启动网关" in result.output
        assert "--telegram" in result.output
        assert "--discord" in result.output


class TestLoadGateway:
    """Test the _load_gateway function"""

    @patch("src.gateway.gateway.Gateway")
    def test_load_gateway_with_tokens(self, mock_gateway_class):
        """Test _load_gateway returns Gateway instance with tokens"""
        from src.commands.cli_gateway import _load_gateway

        mock_instance = MagicMock()
        mock_gateway_class.return_value = mock_instance

        with patch.dict(
            "os.environ",
            {
                "TELEGRAM_BOT_TOKEN": "test-token",
                "DISCORD_BOT_TOKEN": "discord-token",
            },
        ):
            result = _load_gateway()

        assert result == mock_instance
        mock_gateway_class.assert_called_once_with(
            orchestrator=None,
            telegram_token="test-token",
            discord_token="discord-token",
        )

    @patch("src.gateway.gateway.Gateway")
    def test_load_gateway_without_tokens(self, mock_gateway_class):
        """Test _load_gateway returns Gateway instance without tokens"""
        from src.commands.cli_gateway import _load_gateway

        mock_instance = MagicMock()
        mock_gateway_class.return_value = mock_instance

        with patch.dict("os.environ", {}, clear=True):
            result = _load_gateway()

        assert result == mock_instance
        mock_gateway_class.assert_called_once_with(
            orchestrator=None,
            telegram_token=None,
            discord_token=None,
        )
