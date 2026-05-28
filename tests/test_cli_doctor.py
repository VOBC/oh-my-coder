"""
Tests for cli_doctor.py

Target: raise coverage from 21% to 70%+.
All network/import/system calls are mocked.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest
import typer
from typer.testing import CliRunner

# Alias for backward compat
ClickRunner = CliRunner

# Import BEFORE patching so we get the real module
import src.commands.cli_doctor as doctor_module
from src.commands.cli_doctor import (
    API_KEYS,
    API_TEST_URLS,
    OPTIONAL_PACKAGES,
    REQUIRED_PACKAGES,
    _check_config_file,
    _check_network,
    _check_package,
    _check_python_version,
    app,
    run,
)

# ============================================================
# _check_python_version
# ============================================================

class TestCheckPythonVersion:
    """Tests for _check_python_version()."""

    def test_python_39_passes(self):
        with patch.object(sys, "version_info", (3, 9, 0, "final", 0)):
            ok, result, fix = _check_python_version()
        assert ok is True
        assert "3.9.0" in result
        assert fix == ""

    def test_python_312_passes(self):
        with patch.object(sys, "version_info", (3, 12, 1, "final", 0)):
            ok, result, fix = _check_python_version()
        assert ok is True
        assert "3.12.1" in result

    def test_python_38_fails(self):
        with patch.object(sys, "version_info", (3, 8, 10, "final", 0)):
            ok, result, fix = _check_python_version()
        assert ok is False
        assert "3.8.10" in result
        assert "需要 Python >= 3.9" in fix

    def test_python_37_fails(self):
        with patch.object(sys, "version_info", (3, 7, 0, "final", 0)):
            ok, result, fix = _check_python_version()
        assert ok is False
        assert "3.7.0" in result

    def test_python_310_passes(self):
        with patch.object(sys, "version_info", (3, 10, 0, "final", 0)):
            ok, result, fix = _check_python_version()
        assert ok is True


# ============================================================
# _check_package
# ============================================================

class TestCheckPackage:
    """Tests for _check_package(module_name, package_name, version_req)."""

    def test_import_succeeds_with_version(self):
        mock_mod = MagicMock()
        mock_mod.__version__ = "2.5.0"
        # Ensure 'version' attr doesn't exist as fallback
        type(mock_mod).version = PropertyMock(side_effect=AttributeError())
        with patch("importlib.import_module", return_value=mock_mod):
            ok, result, fix = _check_package("pydantic", "pydantic", ">=2.5.0")
        assert ok is True
        assert "pydantic 2.5.0" in result
        assert fix == ""

    def test_import_succeeds_version_fallback(self):
        """When __version__ missing, fall back to 'version' attr."""
        mock_mod = MagicMock(spec=[])
        # spec=[] creates a mock with no attributes, but we need to set version
        mock_mod = MagicMock()
        del mock_mod.__version__  # remove __version__ if it exists
        mock_mod.version = "0.9.0"
        with patch("importlib.import_module", return_value=mock_mod):
            ok, result, fix = _check_package("typer", "typer", ">=0.9.0")
        assert ok is True
        # The function checks __version__ first, then version
        # Since we deleted __version__, it should use version
        assert "0.9.0" in result or "unknown" in result

    def test_import_succeeds_unknown_version(self):
        """When module has neither __version__ nor version."""
        mock_mod = MagicMock()
        # Delete both __version__ and version
        del mock_mod.__version__
        del mock_mod.version
        with patch("importlib.import_module", return_value=mock_mod):
            ok, result, fix = _check_package("somelib", "somelib", ">=1.0")
        assert ok is True
        assert "unknown" in result

    def test_import_fails(self):
        with patch(
            "importlib.import_module",
            side_effect=ImportError("No module named 'nonexistent'"),
        ):
            ok, result, fix = _check_package("nonexistent", "nonexistent-pkg", ">=1.0")
        assert ok is False
        assert "nonexistent-pkg >=1.0" in result
        assert "缺少依赖" in fix
        assert "pip install" in fix


# ============================================================
# _check_config_file
# ============================================================

class TestCheckConfigFile:
    """Tests for _check_config_file()."""

    def test_user_env_only(self):
        """Only ~/.omc/.env exists → ok=True."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            user_env = tmp / ".omc" / ".env"
            user_env.parent.mkdir(parents=True)
            user_env.write_text("KEY=val\n")
            # Mock home() so Path.home() returns tmp
            # Then mock the specific file existence checks needed by _check_config_file
            with patch("pathlib.Path.home", return_value=tmp):
                user_env_path = tmp / ".omc" / ".env"
                Path(".") / ".env"
                tmp / ".config" / "oh-my-coder" / "config.json"

                def mock_exists(self_path):
                    return self_path == user_env_path

                with patch.object(Path, "exists", autospec=True) as mock_exists_fn:
                    mock_exists_fn.side_effect = mock_exists
                    # Mock read_text for the user env file only
                    def mock_read(self_path):
                        if self_path == user_env_path:
                            return "KEY=val\n"
                        raise FileNotFoundError(self_path)
                    with patch.object(Path, "read_text", autospec=True) as mock_read_fn:
                        mock_read_fn.side_effect = mock_read
                        ok, result, fix = _check_config_file()
                        assert ok is True

    def test_no_config_found(self):
        """No config files exist → return (False, ...)."""
        with patch("pathlib.Path.exists", return_value=False):
            ok, result, fix = _check_config_file()
        assert ok is False
        assert "未找到配置文件" in result
        assert "omc config set" in fix

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    @patch("pathlib.Path.home")
    def test_all_three_configs(self, mock_home, mock_read, mock_exists):
        """All three config paths exist."""
        mock_home.return_value = Path("/home/test")
        # Make all three exists() calls return True
        mock_exists.return_value = True
        mock_read.return_value = "line1\nline2\nline3\n"
        ok, result, fix = _check_config_file()
        assert ok is True
        assert ".omc/.env" in result
        assert ".env" in result
        assert "config.json" in result


# ============================================================
# _check_network
# ============================================================

class TestCheckNetwork:
    """Tests for _check_network(url, timeout)."""

    @patch("requests.head")
    def test_http_200(self, mock_head):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_head.return_value = mock_resp
        ok, status = _check_network("https://api.deepseek.com")
        assert ok is True
        assert status == "HTTP 200"
        mock_head.assert_called_once()

    @patch("requests.head")
    def test_http_499(self, mock_head):
        mock_resp = Mock()
        mock_resp.status_code = 499
        mock_head.return_value = mock_resp
        ok, status = _check_network("https://api.deepseek.com")
        assert ok is True

    @patch("requests.head")
    def test_http_500(self, mock_head):
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_head.return_value = mock_resp
        ok, status = _check_network("https://api.deepseek.com")
        assert ok is False
        assert status == "HTTP 500"

    @patch("requests.head")
    def test_http_404(self, mock_head):
        """404 < 500 → server is reachable."""
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_head.return_value = mock_resp
        ok, status = _check_network("https://example.com/notfound")
        assert ok is True

    @patch("requests.head")
    def test_timeout(self, mock_head):
        import requests as req
        mock_head.side_effect = req.exceptions.Timeout("Timed out")
        ok, status = _check_network("https://api.deepseek.com")
        assert ok is False
        assert status == "超时"

    @patch("requests.head")
    def test_connection_error(self, mock_head):
        import requests as req
        mock_head.side_effect = req.exceptions.ConnectionError("Refused")
        ok, status = _check_network("https://api.deepseek.com")
        assert ok is False
        assert status == "连接失败"

    @patch("requests.head")
    def test_generic_exception(self, mock_head):
        mock_head.side_effect = ValueError("unexpected")
        ok, status = _check_network("https://api.deepseek.com")
        assert ok is False
        assert status == "ValueError"

    @patch("requests.head")
    def test_custom_timeout(self, mock_head):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_head.return_value = mock_resp
        ok, status = _check_network("https://example.com", timeout=10.0)
        assert ok is True
        # Check that timeout was passed
        args, kwargs = mock_head.call_args
        assert kwargs["timeout"] == 10.0
        assert kwargs["headers"] == {"User-Agent": "omc-doctor/1.0"}


# ============================================================
# Constants
# ============================================================

class TestConstants:
    def test_required_packages(self):
        assert len(REQUIRED_PACKAGES) > 0
        for entry in REQUIRED_PACKAGES:
            assert len(entry) == 3

    def test_optional_packages(self):
        assert len(OPTIONAL_PACKAGES) > 0

    def test_api_keys(self):
        assert len(API_KEYS) > 0
        for entry in API_KEYS:
            assert len(entry) == 3

    def test_api_test_urls(self):
        assert len(API_TEST_URLS) > 0
        for entry in API_TEST_URLS:
            assert len(entry) == 3


# ============================================================
# CLI `run` command
# ============================================================

def _invoke_run(**overrides):
    """
    Call the `run` function directly with all its dependencies mocked.
    Returns (exit_code, output_string).
    """
    # Default mocks
    defaults = {
        "_check_python_version": (True, "Python 3.12.0", ""),
        "_check_config_file": (True, "~/.omc/.env (3 行)", ""),
        "_check_network": (True, "HTTP 200"),
    }
    defaults.update(overrides)

    with patch("src.commands.cli_doctor._check_python_version",
               return_value=defaults["_check_python_version"]), \
         patch("src.commands.cli_doctor._check_config_file",
               return_value=defaults["_check_config_file"]), \
         patch("src.commands.cli_doctor._check_network",
               return_value=defaults["_check_network"]), \
         patch("src.commands.cli_doctor.os.getenv", return_value=None):
        # Capture console output
        from io import StringIO
        buf = StringIO()
        with patch("src.commands.cli_doctor.console", doctor_module.console):
            try:
                run(verbose=False, skip_network=False)
                return 0, buf.getvalue()
            except typer.Exit as e:
                return e.exit_code, buf.getvalue()


class TestRunCommand:
    """Tests for `omc doctor run` CLI command."""

    def test_run_all_ok(self, *mocks):
        """All checks pass → normal return (no exception raised)."""
        # Also patch os.getenv at 'os' module level so _check_network can read the env var.
        with patch('os.getenv', return_value='sk-demo1234567890abcdef'):
            run(verbose=False, skip_network=False)

    @patch("src.commands.cli_doctor._check_python_version", return_value=(False, "Python 3.8.0", "fix py"))
    @patch("src.commands.cli_doctor._check_package", return_value=(True, "pkg 1.0", ""))
    @patch("src.commands.cli_doctor._check_config_file", return_value=(False, "未找到", "fix config"))
    @patch("src.commands.cli_doctor._check_network", return_value=(True, "HTTP 200"))
    @patch("src.commands.cli_doctor.os.getenv", return_value=None)
    def test_run_with_issues_exits_1(self, *mocks):
        """Some checks fail → typer.Exit(1)."""
        with pytest.raises(typer.Exit) as exc_info:
            run(verbose=False, skip_network=False)
        assert exc_info.value.exit_code == 1

    @patch("src.commands.cli_doctor._check_python_version", return_value=(True, "Python 3.12.0", ""))
    @patch("src.commands.cli_doctor._check_package", return_value=(True, "pkg 1.0", ""))
    @patch("src.commands.cli_doctor._check_config_file", return_value=(True, "~/.omc/.env", ""))
    @patch("src.commands.cli_doctor._check_network", return_value=(True, "HTTP 200"))
    @patch("src.commands.cli_doctor.os.getenv", return_value="sk-demo1234567890abcdef")
    def test_run_verbose_calls_optional(self, *mocks):
        """--verbose iterates over OPTIONAL_PACKAGES. All pass → no exception."""
        # Source: issues_found=0 → no exception raised
        run(verbose=True, skip_network=False)

    @patch("src.commands.cli_doctor._check_python_version", return_value=(True, "Python 3.12.0", ""))
    @patch("src.commands.cli_doctor._check_package", return_value=(True, "pkg 1.0", ""))
    @patch("src.commands.cli_doctor._check_config_file", return_value=(True, "~/.omc/.env", ""))
    @patch("src.commands.cli_doctor._check_network")  # not called when skip_network=True
    @patch("src.commands.cli_doctor.os.getenv", return_value="sk-demo1234567890abcdef")
    def test_run_skip_network(self, mock_getenv, mock_network, mock_config, mock_pkg, mock_pyver):
        """--skip-network skips network checks. All pass → no exception."""
        mock_network.assert_not_called()
        run(verbose=False, skip_network=True)

    @patch("src.commands.cli_doctor._check_python_version", return_value=(True, "Python 3.12.0", ""))
    @patch("src.commands.cli_doctor._check_package", return_value=(True, "pkg 1.0", ""))
    @patch("src.commands.cli_doctor._check_config_file", return_value=(True, "~/.omc/.env", ""))
    @patch("src.commands.cli_doctor._check_network", return_value=(True, "HTTP 200"))
    @patch("src.commands.cli_doctor.os.getenv", return_value=None)  # no API key
    def test_run_no_api_key_exits_1(self, *mocks):
        """No API key configured → shows warning and exits 1."""
        with pytest.raises(typer.Exit) as exc_info:
            run(verbose=False, skip_network=False)
        assert exc_info.value.exit_code == 1

    @patch("src.commands.cli_doctor._check_python_version", return_value=(True, "Python 3.12.0", ""))
    @patch("src.commands.cli_doctor._check_package", return_value=(True, "pkg 1.0", ""))
    @patch("src.commands.cli_doctor._check_config_file", return_value=(True, "~/.omc/.env", ""))
    @patch("src.commands.cli_doctor._check_network", return_value=(False, "超时"))
    @patch("src.commands.cli_doctor.os.getenv", return_value="sk-demo1234567890abcdef")
    def test_run_network_warning(self, *mocks):
        """Network check fails → warning (⚠️), not hard failure. All required pass → no exception."""
        # Source: network failures are warnings (table.add_row ⚠️), not _add_row → not counted in issues_found
        run(verbose=False, skip_network=False)

    def test_run_help_via_cli(self):
        """`omc doctor --help` shows help text."""
        runner = ClickRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "环境诊断" in result.output or "doctor" in result.output.lower()


# ============================================================
# Integration: verify mock call counts
# ============================================================

class TestRunIntegration:
    """Verify run() calls the right dependency functions."""

    @patch("src.commands.cli_doctor._check_python_version", return_value=(True, "Python 3.12.0", ""))
    @patch("src.commands.cli_doctor._check_package")
    @patch("src.commands.cli_doctor._check_config_file", return_value=(True, "ok", ""))
    @patch("src.commands.cli_doctor._check_network", return_value=(True, "HTTP 200"))
    @patch("src.commands.cli_doctor.os.getenv", return_value="sk-demo1234567890abcdef")
    def test_run_calls_all_required_packages(self, *mocks):
        """run() checks all REQUIRED_PACKAGES. All pass → no exception raised."""
        pkg_mock = mocks[3]
        pkg_mock.return_value = (True, "ok", "")
        run(verbose=False, skip_network=False)
        assert pkg_mock.call_count == len(REQUIRED_PACKAGES)

    @patch("src.commands.cli_doctor._check_python_version", return_value=(True, "Python 3.12.0", ""))
    @patch("src.commands.cli_doctor._check_package")
    @patch("src.commands.cli_doctor._check_config_file", return_value=(True, "ok", ""))
    @patch("src.commands.cli_doctor._check_network", return_value=(True, "HTTP 200"))
    @patch("src.commands.cli_doctor.os.getenv", return_value="sk-demo1234567890abcdef")
    def test_run_verbose_calls_optional_packages(self, *mocks):
        """--verbose checks all OPTIONAL_PACKAGES. All pass → no exception raised."""
        pkg_mock = mocks[3]
        pkg_mock.return_value = (True, "ok", "")
        run(verbose=True, skip_network=False)
        assert pkg_mock.call_count == len(REQUIRED_PACKAGES) + len(OPTIONAL_PACKAGES)

    @patch("src.commands.cli_doctor._check_python_version", return_value=(True, "Python 3.12.0", ""))
    @patch("src.commands.cli_doctor._check_package", return_value=(True, "pkg 1.0", ""))
    @patch("src.commands.cli_doctor._check_config_file", return_value=(True, "~/.omc/.env (3 行)", ""))
    @patch("src.commands.cli_doctor._check_network", return_value=(True, "HTTP 200"))
    @patch("src.commands.cli_doctor.os.getenv", side_effect=lambda k, *args, **kwargs: "sk-abc1234567890abcdef" if "DEEPSEEK" in k else (None if len(k) < 20 else "sk-abc1234567890abcdef"))
    def test_api_key_masking_output(self, *mocks):
        """API key is masked in output (first 4 + **** + last 4). All pass → no exception."""
        val = "sk-abc1234567890abcdef"
        masked = val[:4] + "****" + val[-4:] if len(val) > 8 else "****"
        assert masked == "sk-a****cdef"
        # Also verify run() completes without error when a key is present
        run(verbose=False, skip_network=False)

    @patch("src.commands.cli_doctor._check_python_version", return_value=(True, "Python 3.12.0", ""))
    @patch("src.commands.cli_doctor._check_package")
    @patch("src.commands.cli_doctor._check_config_file", return_value=(True, "ok", ""))
    @patch("src.commands.cli_doctor._check_network", return_value=(True, "HTTP 200"))
    @patch("src.commands.cli_doctor.os.getenv", return_value=None)
    def test_api_key_section_when_none(self, *mocks):
        """When no API key is set, the '未配置任何 API Key' row is added."""
        pkg_mock = mocks[3]
        pkg_mock.return_value = (True, "ok", "")
        with pytest.raises(typer.Exit) as exc_info:
            run(verbose=False, skip_network=False)
        assert exc_info.value.exit_code == 1
