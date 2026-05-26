"""
Tests for src/commands/cli_server.py

Uses typer.testing.CliRunner and mock to isolate external dependencies.
Target coverage: ≥80%
"""

import os
import signal
import socket
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from src.commands.cli_server import (
    _find_free_port,
    _is_port_in_use,
    app,
)


@pytest.fixture
def runner():
    """Create a CliRunner instance for testing typer commands."""
    return CliRunner()


@pytest.fixture
def mock_pid_file(tmp_path):
    """Create a temporary PID file path."""
    pid_dir = tmp_path / ".omc"
    pid_dir.mkdir()
    pid_file = pid_dir / "server.pid"
    with patch("src.commands.cli_server.Path.home", return_value=tmp_path):
        yield pid_file


@pytest.fixture
def mock_log_file(tmp_path):
    """Create a temporary log file path."""
    log_dir = tmp_path / ".omc" / "logs"
    log_dir.mkdir(parents=True)
    log_file = log_dir / "server.log"
    with patch("src.commands.cli_server.Path.home", return_value=tmp_path):
        yield log_file


@pytest.fixture
def mock_env_file(tmp_path):
    """Create a temporary .env file path."""
    env_dir = tmp_path / ".omc"
    env_dir.mkdir()
    env_file = env_dir / ".env"
    with patch("src.commands.cli_server.Path.home", return_value=tmp_path):
        yield env_file


# ---------------------------------------------------------------------------
# Tests for helper functions
# ---------------------------------------------------------------------------


class TestFindFreePort:
    """Tests for _find_free_port function."""

    @patch("socket.socket.connect_ex", return_value=0)  # Port is in use
    @patch("socket.socket.__enter__", side_effect=socket.socket)
    @patch("socket.socket.__exit__", return_value=False)
    def test_port_in_use_finds_free_port(self, mock_exit, mock_enter, mock_connect):
        """Test that _find_free_port finds another port when default is in use."""
        # Make all ports appear in use
        mock_connect.return_value = 0
        result = _find_free_port(8080)
        # Should return a port different from 8080
        assert result != 8080

    @patch("socket.socket.connect_ex", return_value=1)  # Port is free
    def test_port_free_returns_same_port(self, mock_connect):
        """Test that _find_free_port returns same port when it's free."""
        result = _find_free_port(8080)
        assert result == 8080


class TestIsPortInUse:
    """Tests for _is_port_in_use function."""

    @patch("socket.socket.connect_ex", return_value=0)
    def test_port_in_use_returns_true(self, mock_connect):
        """Test that _is_port_in_use returns True when port is in use."""
        result = _is_port_in_use(8080)
        assert result is True

    @patch("socket.socket.connect_ex", return_value=1)
    def test_port_free_returns_false(self, mock_connect):
        """Test that _is_port_in_use returns False when port is free."""
        result = _is_port_in_use(8080)
        assert result is False


# ---------------------------------------------------------------------------
# Tests for start command
# ---------------------------------------------------------------------------


class TestStartCommand:
    """Tests for the 'start' command."""

    @patch("src.commands.cli_server._open_browser")
    @patch("src.commands.cli_server.asyncio.run")
    @patch("src.commands.cli_server.uvicorn.Server")
    @patch("src.commands.cli_server.signal.signal")
    @patch("src.commands.cli_server._is_port_in_use", return_value=False)
    @patch("src.commands.cli_server._load_api_key_from_config", return_value=None)
    def test_start_basic(
        self,
        mock_load_key,
        mock_port_check,
        mock_signal,
        mock_server,
        mock_asyncio,
        mock_browser,
        runner,
    ):
        """Test basic start command execution."""
        result = runner.invoke(app, ["start", "--no-open"])
        assert result.exit_code == 0

    @patch("src.commands.cli_server._open_browser")
    @patch("src.commands.cli_server.asyncio.run")
    @patch("src.commands.cli_server.uvicorn.Server")
    @patch("src.commands.cli_server.signal.signal")
    @patch("src.commands.cli_server._is_port_in_use", return_value=False)
    @patch("src.commands.cli_server._load_api_key_from_config", return_value=None)
    def test_start_with_custom_port(
        self,
        mock_load_key,
        mock_port_check,
        mock_signal,
        mock_server,
        mock_asyncio,
        mock_browser,
        runner,
    ):
        """Test start command with custom port."""
        result = runner.invoke(app, ["start", "--port", "9000", "--no-open"])
        assert result.exit_code == 0

    @patch("src.commands.cli_server._open_browser")
    @patch("src.commands.cli_server.asyncio.run")
    @patch("src.commands.cli_server.uvicorn.Server")
    @patch("src.commands.cli_server.signal.signal")
    @patch("src.commands.cli_server._is_port_in_use", return_value=False)
    @patch("src.commands.cli_server._load_api_key_from_config", return_value=None)
    def test_start_with_host(
        self,
        mock_load_key,
        mock_port_check,
        mock_signal,
        mock_server,
        mock_asyncio,
        mock_browser,
        runner,
    ):
        """Test start command with custom host."""
        result = runner.invoke(
            app, ["start", "--host", "127.0.0.1", "--no-open"]
        )
        assert result.exit_code == 0

    @patch("src.commands.cli_server._open_browser")
    @patch("src.commands.cli_server.asyncio.run")
    @patch("src.commands.cli_server.uvicorn.Server")
    @patch("src.commands.cli_server.signal.signal")
    @patch("src.commands.cli_server._is_port_in_use", return_value=False)
    @patch("src.commands.cli_server._load_api_key_from_config", return_value="test-key")
    def test_start_with_api_key(
        self,
        mock_load_key,
        mock_port_check,
        mock_signal,
        mock_server,
        mock_asyncio,
        mock_browser,
        runner,
    ):
        """Test start command with API key."""
        result = runner.invoke(app, ["start", "--no-open"])
        assert result.exit_code == 0

    @patch("src.commands.cli_server._open_browser")
    @patch("src.commands.cli_server.asyncio.run")
    @patch("src.commands.cli_server.uvicorn.Server")
    @patch("src.commands.cli_server.signal.signal")
    @patch("src.commands.cli_server._is_port_in_use", return_value=False)
    @patch("src.commands.cli_server._load_api_key_from_config", return_value=None)
    def test_start_with_no_auth(
        self,
        mock_load_key,
        mock_port_check,
        mock_signal,
        mock_server,
        mock_asyncio,
        mock_browser,
        runner,
    ):
        """Test start command with --no-auth flag."""
        result = runner.invoke(app, ["start", "--no-auth", "--no-open"])
        assert result.exit_code == 0

    def test_start_mutex_api_key_and_no_auth(self, runner):
        """Test that --api-key and --no-auth cannot be used together."""
        result = runner.invoke(
            app, ["start", "--api-key", "test", "--no-auth", "--no-open"]
        )
        assert result.exit_code == 1
        assert "--api-key 和 --no-auth 不能同时使用" in result.output

    @patch("src.commands.cli_server._find_free_port", return_value=8081)
    @patch("src.commands.cli_server._is_port_in_use", return_value=True)
    @patch("src.commands.cli_server._load_api_key_from_config", return_value=None)
    def test_start_port_in_use_switches_port(
        self, mock_load_key, mock_port_check, mock_find_port, runner
    ):
        """Test that start command switches port when default is in use."""
        with patch("src.commands.cli_server.asyncio.run"), patch(
            "src.commands.cli_server.uvicorn.Server"
        ), patch("src.commands.cli_server.signal.signal"), patch(
            "src.commands.cli_server._open_browser"
        ):
            result = runner.invoke(app, ["start", "--no-open"])
            assert result.exit_code == 0
            mock_find_port.assert_called_once_with(8080)

    @patch("src.commands.cli_server._is_port_in_use", return_value=True)
    @patch("src.commands.cli_server._load_api_key_from_config", return_value=None)
    def test_start_port_in_use_no_free_port(
        self, mock_load_key, mock_port_check, runner
    ):
        """Test start command when no free port is available."""
        with patch(
            "src.commands.cli_server._find_free_port", return_value=8080
        ):  # Same port means no free port found
            result = runner.invoke(app, ["start", "--no-open"])
            assert result.exit_code == 1
            assert "无法找到可用端口" in result.output


# ---------------------------------------------------------------------------
# Tests for stop command
# ---------------------------------------------------------------------------


class TestStopCommand:
    """Tests for the 'stop' command."""

    def test_stop_no_pid_file(self, runner, mock_pid_file):
        """Test stop command when PID file doesn't exist."""
        result = runner.invoke(app, ["stop"])
        assert result.exit_code == 1
        assert "找不到 PID 文件" in result.output

    def test_stop_success(self, runner, mock_pid_file):
        """Test successful stop command."""
        mock_pid_file.write_text("12345")
        with patch("os.kill") as mock_kill:
            result = runner.invoke(app, ["stop"])
            assert result.exit_code == 0
            assert "已停止" in result.output
            mock_kill.assert_called_once_with(12345, signal.SIGTERM)
            assert not mock_pid_file.exists()  # PID file should be deleted

    def test_stop_process_not_found(self, runner, mock_pid_file):
        """Test stop command when process doesn't exist."""
        mock_pid_file.write_text("99999")
        with patch("os.kill", side_effect=ProcessLookupError):
            result = runner.invoke(app, ["stop"])
            assert result.exit_code == 0
            assert "进程已不存在" in result.output
            assert not mock_pid_file.exists()  # PID file should be deleted

    def test_stop_exception(self, runner, mock_pid_file):
        """Test stop command when an exception occurs."""
        mock_pid_file.write_text("12345")
        with patch("os.kill", side_effect=OSError("Permission denied")):
            result = runner.invoke(app, ["stop"])
            assert result.exit_code == 1
            assert "停止失败" in result.output


# ---------------------------------------------------------------------------
# Tests for status command
# ---------------------------------------------------------------------------


class TestStatusCommand:
    """Tests for the 'status' command."""

    def test_status_not_running_no_pid_file(self, runner, mock_pid_file):
        """Test status command when server is not running (no PID file)."""
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "未运行" in result.output

    def test_status_running(self, runner, mock_pid_file):
        """Test status command when server is running."""
        mock_pid_file.write_text("12345")
        with patch("os.kill") as mock_kill:
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "运行中" in result.output
            mock_kill.assert_called_once_with(12345, 0)

    def test_status_pid_file_exists_but_process_dead(self, runner, mock_pid_file):
        """Test status command when PID file exists but process is dead."""
        mock_pid_file.write_text("99999")
        with patch("os.kill", side_effect=[ProcessLookupError, None]):
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "未运行" in result.output
            assert not mock_pid_file.exists()  # PID file should be deleted


# ---------------------------------------------------------------------------
# Tests for logs command
# ---------------------------------------------------------------------------


class TestLogsCommand:
    """Tests for the 'logs' command."""

    def test_logs_no_log_file(self, runner, mock_log_file):
        """Test logs command when log file doesn't exist."""
        result = runner.invoke(app, ["logs"])
        assert result.exit_code == 1
        assert "暂无日志文件" in result.output

    def test_logs_success(self, runner, mock_log_file):
        """Test successful logs command."""
        log_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        mock_log_file.write_text(log_content)
        result = runner.invoke(app, ["logs", "--lines", "3"])
        assert result.exit_code == 0
        assert "Line 3" in result.output
        assert "Line 4" in result.output
        assert "Line 5" in result.output

    def test_logs_default_lines(self, runner, mock_log_file):
        """Test logs command with default number of lines."""
        log_content = "\n".join(f"Line {i}" for i in range(1, 100))
        mock_log_file.write_text(log_content)
        result = runner.invoke(app, ["logs"])
        assert result.exit_code == 0
        # Should show last 50 lines
        assert "Line 99" in result.output


# ---------------------------------------------------------------------------
# Tests for _load_api_key_from_config
# ---------------------------------------------------------------------------


class TestLoadApiKeyFromConfig:
    """Tests for _load_api_key_from_config function."""

    def test_load_api_key_no_env_file(self, mock_env_file):
        """Test _load_api_key_from_config when .env file doesn't exist."""
        from src.commands.cli_server import _load_api_key_from_config

        result = _load_api_key_from_config()
        assert result is None

    def test_load_api_key_success(self, mock_env_file):
        """Test _load_api_key_from_config successfully reads API key."""
        from src.commands.cli_server import _load_api_key_from_config

        mock_env_file.write_text("OMC_SERVER_API_KEY=my-secret-key\nOTHER_VAR=test\n")
        result = _load_api_key_from_config()
        assert result == "my-secret-key"

    def test_load_api_key_no_matching_line(self, mock_env_file):
        """Test _load_api_key_from_config when no matching line exists."""
        from src.commands.cli_server import _load_api_key_from_config

        mock_env_file.write_text("OTHER_VAR=test\nANOTHER_VAR=value\n")
        result = _load_api_key_from_config()
        assert result is None


# ---------------------------------------------------------------------------
# Tests for _open_browser
# ---------------------------------------------------------------------------


class TestOpenBrowser:
    """Tests for _open_browser function."""

    @patch("platform.system", return_value="Darwin")
    @patch("subprocess.Popen")
    def test_open_browser_macos(self, mock_popen, mock_platform):
        """Test _open_browser on macOS."""
        from src.commands.cli_server import _open_browser

        _open_browser("http://localhost:8080")
        mock_popen.assert_called_once_with(["open", "http://localhost:8080"])

    @patch("platform.system", return_value="Windows")
    @patch("subprocess.Popen")
    def test_open_browser_windows(self, mock_popen, mock_platform):
        """Test _open_browser on Windows."""
        from src.commands.cli_server import _open_browser

        _open_browser("http://localhost:8080")
        mock_popen.assert_called_once_with(
            ["cmd", "/c", "start", "http://localhost:8080"]
        )

    @patch("platform.system", return_value="Linux")
    @patch("webbrowser.open")
    def test_open_browser_linux(self, mock_webbrowser, mock_platform):
        """Test _open_browser on Linux."""
        from src.commands.cli_server import _open_browser

        _open_browser("http://localhost:8080")
        mock_webbrowser.assert_called_once_with("http://localhost:8080")

    @patch("platform.system", return_value="Darwin")
    @patch("subprocess.Popen", side_effect=Exception("Failed to open"))
    def test_open_browser_exception_suppressed(self, mock_popen, mock_platform):
        """Test that _open_browser suppresses exceptions."""
        from src.commands.cli_server import _open_browser

        # Should not raise
        _open_browser("http://localhost:8080")


# ---------------------------------------------------------------------------
# Tests for main callback
# ---------------------------------------------------------------------------


class TestMainCallback:
    """Tests for the main callback."""

    def test_main_callback_no_subcommand(self, runner):
        """Test main callback when no subcommand is provided."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Usage:" in result.output or "start" in result.output

    def test_main_callback_help(self, runner):
        """Test main callback with --help flag."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "启动远程 AI 编程助手" in result.output
