"""
Tests for src/commands/cli_security.py.
Covers check, list, sandbox-test, run commands.
"""
from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from src.commands.cli_security import app

runner = CliRunner()


def _mock_check_result(allowed=True, reason="ok", matched_pattern=""):
    """Build a mock check result."""
    result = Mock()
    result.allowed = allowed
    result.reason = reason
    result.matched_pattern = matched_pattern
    return result


def _mock_sandbox(allowed_dirs=None):
    """Build a mock Sandbox."""
    sb = Mock()
    sb.validate_path = Mock(return_value=True)
    sb.get_allowed_dirs = Mock(return_value=allowed_dirs or ["/tmp", "/home/user/.omc"])
    sb.run_command = Mock()
    return sb


# ── check command ──────────────────────────────────────────────────────


class TestSecurityCheck:
    def test_check_allowed(self):
        with patch("src.commands.cli_security.PermissionGuard") as MockGuard:
            guard = MockGuard.return_value
            guard.check.return_value = _mock_check_result(allowed=True)
            guard.needs_approval.return_value = False
            result = runner.invoke(app, ["check", "git status"])
        assert result.exit_code == 0
        assert "命令安全" in result.stdout

    def test_check_allowed_needs_approval(self):
        with patch("src.commands.cli_security.PermissionGuard") as MockGuard:
            guard = MockGuard.return_value
            guard.check.return_value = _mock_check_result(allowed=True)
            guard.needs_approval.return_value = True
            result = runner.invoke(app, ["check", "git commit"])
        assert result.exit_code == 0
        assert "需要审批" in result.stdout

    def test_check_denied(self):
        with patch("src.commands.cli_security.PermissionGuard") as MockGuard:
            guard = MockGuard.return_value
            guard.check.return_value = _mock_check_result(
                allowed=False, reason="rm -rf root", matched_pattern="rm -rf /"
            )
            guard.needs_approval.return_value = False
            result = runner.invoke(app, ["check", "rm -rf /"])
        assert result.exit_code == 1
        assert "命令被拦截" in result.stdout
        assert "rm -rf root" in result.stdout

    def test_check_with_config_file(self):
        with patch("src.config.agent_config.load_config_file") as mock_load:
            mock_config = Mock()
            mock_config.to_dict.return_value = {"permissions": {}}
            mock_load.return_value = mock_config
            with patch("src.commands.cli_security.PermissionGuard") as MockGuard:
                guard = MockGuard.return_value
                guard.check.return_value = _mock_check_result(allowed=True)
                guard.needs_approval.return_value = False
                result = runner.invoke(app, ["check", "echo", "--config", "rules.yaml"])
        assert result.exit_code == 0

    def test_check_config_load_fails(self):
        with patch("src.config.agent_config.load_config_file",
                   side_effect=ValueError("bad config")):
            with patch("src.commands.cli_security.PermissionGuard") as MockGuard:
                guard = MockGuard.return_value
                guard.check.return_value = _mock_check_result(allowed=True)
                guard.needs_approval.return_value = False
                result = runner.invoke(app, ["check", "echo", "--config", "bad.yaml"])
        assert result.exit_code == 0
        assert "加载配置失败" in result.stdout


# ── list command ───────────────────────────────────────────────────────


class TestSecurityList:
    def test_list_builtin_patterns(self):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "rm -rf /" in result.stdout
        assert "Fork 炸弹" in result.stdout
        assert "mkfs" in result.stdout


# ── sandbox-test command ───────────────────────────────────────────────


class TestSandboxTest:
    def test_sandbox_test_allowed(self):
        with patch("src.commands.cli_security.Sandbox") as MockSB:
            MockSB.return_value = _mock_sandbox()
            result = runner.invoke(app, ["sandbox-test", "/tmp/test"])
        assert result.exit_code == 0
        assert "路径在允许范围内" in result.stdout

    def test_sandbox_test_denied(self):
        with patch("src.commands.cli_security.Sandbox") as MockSB:
            sb = _mock_sandbox()
            sb.validate_path.return_value = False
            MockSB.return_value = sb
            result = runner.invoke(app, ["sandbox-test", "/etc/passwd"])
        assert result.exit_code == 1
        assert "路径超出沙箱范围" in result.stdout

    def test_sandbox_test_default_path(self):
        with patch("src.commands.cli_security.Sandbox") as MockSB:
            MockSB.return_value = _mock_sandbox()
            result = runner.invoke(app, ["sandbox-test"])
        assert result.exit_code == 0


# ── run command ────────────────────────────────────────────────────────


class TestSecurityRun:
    def test_run_success(self):
        sb = _mock_sandbox()
        cmd_result = Mock(stdout="file1.py\nfile2.py\n", stderr="", returncode=0)
        sb.run_command.return_value = cmd_result

        with patch("src.commands.cli_security.Sandbox", return_value=sb):
            result = runner.invoke(app, ["run", "ls /tmp"])
        assert result.exit_code == 0
        assert "file1.py" in result.stdout
        assert "执行成功" in result.stdout

    def test_run_nonzero_exit(self):
        sb = _mock_sandbox()
        cmd_result = Mock(stdout="", stderr="error msg", returncode=1)
        sb.run_command.return_value = cmd_result

        with patch("src.commands.cli_security.Sandbox", return_value=sb):
            result = runner.invoke(app, ["run", "failing command"])
        assert result.exit_code == 0
        assert "error msg" in result.stdout
        assert "执行完成" in result.stdout

    def test_run_with_timeout_option(self):
        sb = _mock_sandbox()
        cmd_result = Mock(stdout="ok", stderr="", returncode=0)
        sb.run_command.return_value = cmd_result

        with patch("src.commands.cli_security.Sandbox", return_value=sb):
            result = runner.invoke(app, ["run", "sleep 5", "--timeout", "10"])
        assert result.exit_code == 0
        sb.run_command.assert_called_with("sleep 5", timeout=10)

    def test_run_default_timeout(self):
        sb = _mock_sandbox()
        cmd_result = Mock(stdout="ok", stderr="", returncode=0)
        sb.run_command.return_value = cmd_result

        with patch("src.commands.cli_security.Sandbox", return_value=sb):
            result = runner.invoke(app, ["run", "echo hello"])
        assert result.exit_code == 0
        sb.run_command.assert_called_with("echo hello", timeout=30)

    def test_run_permission_denied(self):
        sb = _mock_sandbox()
        sb.run_command.side_effect = PermissionError("access denied")

        with patch("src.commands.cli_security.Sandbox", return_value=sb):
            result = runner.invoke(app, ["run", "rm /etc/hosts"])
        assert result.exit_code == 1
        assert "沙箱拒绝" in result.stdout

    def test_run_timeout(self):
        sb = _mock_sandbox()
        sb.run_command.side_effect = TimeoutError("timed out")

        with patch("src.commands.cli_security.Sandbox", return_value=sb):
            result = runner.invoke(app, ["run", "sleep 999"])
        assert result.exit_code == 1
        assert "执行超时" in result.stdout

    def test_run_other_exception(self):
        sb = _mock_sandbox()
        sb.run_command.side_effect = RuntimeError("crash")

        with patch("src.commands.cli_security.Sandbox", return_value=sb):
            result = runner.invoke(app, ["run", "bad"])
        assert result.exit_code == 1
        assert "执行失败" in result.stdout
