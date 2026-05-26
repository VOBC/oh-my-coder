"""Tests for cli_quality - 代码质量检查命令"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.commands.cli_quality import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helper: build a fake CompletedProcess
# ---------------------------------------------------------------------------
def fake_completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


# ---------------------------------------------------------------------------
# _check_* helpers
# ---------------------------------------------------------------------------
class TestCheckInstalled:
    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    def test_check_ruff_installed_true(self, mock_which):
        from src.commands.cli_quality import _check_ruff_installed

        assert _check_ruff_installed() is True

    @patch("src.commands.cli_quality.shutil.which", return_value=None)
    def test_check_ruff_installed_false(self, mock_which):
        from src.commands.cli_quality import _check_ruff_installed

        assert _check_ruff_installed() is False

    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(0),
    )
    def test_check_black_installed_true(self, mock_run):
        from src.commands.cli_quality import _check_black_installed

        assert _check_black_installed() is True

    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "black"),
    )
    def test_check_black_installed_calledprocesserror(self, mock_run):
        from src.commands.cli_quality import _check_black_installed

        assert _check_black_installed() is False

    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=FileNotFoundError,
    )
    def test_check_black_installed_filenotfound(self, mock_run):
        from src.commands.cli_quality import _check_black_installed

        assert _check_black_installed() is False

    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(0),
    )
    def test_check_mypy_installed_true(self, mock_run):
        from src.commands.cli_quality import _check_mypy_installed

        assert _check_mypy_installed() is True

    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "mypy"),
    )
    def test_check_mypy_installed_false(self, mock_run):
        from src.commands.cli_quality import _check_mypy_installed

        assert _check_mypy_installed() is False


# ---------------------------------------------------------------------------
# quality check
# ---------------------------------------------------------------------------
class TestQualityCheck:
    @patch("src.commands.cli_quality.shutil.which", return_value=None)
    def test_check_ruff_not_installed(self, _):
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 1
        assert "ruff 未安装" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(0),
    )
    def test_check_pass(self, mock_run, _):
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "ruff check passed" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(1, stdout="F401 unused\n", stderr=""),
    )
    def test_check_found_issues(self, mock_run, _):
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 1
        assert "发现" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(1, stdout="", stderr="some stderr"),
    )
    def test_check_with_stderr(self, mock_run, _):
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 1

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch("src.commands.cli_quality.subprocess.run", side_effect=FileNotFoundError)
    def test_check_filenotfound(self, mock_run, _):
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 1
        assert "未找到" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch("src.commands.cli_quality.subprocess.run", side_effect=OSError("boom"))
    def test_check_generic_exception(self, mock_run, _):
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 1
        assert "执行失败" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(0),
    )
    def test_check_custom_path(self, mock_run, _):
        result = runner.invoke(app, ["check", "my_code/"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# quality fix
# ---------------------------------------------------------------------------
class TestQualityFix:
    @patch("src.commands.cli_quality.shutil.which", return_value=None)
    def test_fix_ruff_not_installed(self, _):
        result = runner.invoke(app, ["fix"])
        assert result.exit_code == 1

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(0),
    )
    def test_fix_pass(self, mock_run, _):
        result = runner.invoke(app, ["fix"])
        assert result.exit_code == 0
        assert "已自动修复" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(2, stdout="E501 line too long\n", stderr=""),
    )
    def test_fix_partial(self, mock_run, _):
        result = runner.invoke(app, ["fix"])
        assert "部分问题" in result.output or "待手动处理" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch("src.commands.cli_quality.subprocess.run", side_effect=FileNotFoundError)
    def test_fix_filenotfound(self, mock_run, _):
        result = runner.invoke(app, ["fix"])
        assert result.exit_code == 1

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch("src.commands.cli_quality.subprocess.run", side_effect=OSError("err"))
    def test_fix_exception(self, mock_run, _):
        result = runner.invoke(app, ["fix"])
        assert result.exit_code == 1

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(1, stdout="", stderr="warn"),
    )
    def test_fix_with_stderr(self, mock_run, _):
        result = runner.invoke(app, ["fix"])
        # fix doesn't raise on non-zero, just prints warning
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# quality type
# ---------------------------------------------------------------------------
class TestQualityType:
    @patch("src.commands.cli_quality.subprocess.run", side_effect=FileNotFoundError)
    def test_type_mypy_not_installed(self, _):
        result = runner.invoke(app, ["type"])
        assert result.exit_code == 1
        assert "mypy 未安装" in result.output

    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(0),
    )
    def test_type_pass(self, mock_run):
        result = runner.invoke(app, ["type"])
        assert result.exit_code == 0
        assert "类型检查通过" in result.output

    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(
            1,
            stdout="file.py:10: error: Incompatible types\nfile.py:20: error: Missing attr\n",
            stderr="",
        ),
    )
    def test_type_errors(self, mock_run):
        result = runner.invoke(app, ["type"])
        assert result.exit_code == 1
        assert "2 个类型错误" in result.output

    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(
            1,
            stdout="\n".join(f"file.py:{i}: error: err" for i in range(15)),
            stderr="",
        ),
    )
    def test_type_many_errors_truncated(self, mock_run):
        result = runner.invoke(app, ["type"])
        assert "还有 5 个错误未显示" in result.output

    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(1, stdout="", stderr="file.py:1: error: bad\n"),
    )
    def test_type_errors_in_stderr(self, mock_run):
        result = runner.invoke(app, ["type"])
        assert result.exit_code == 1

    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=FileNotFoundError,
    )
    def test_type_filenotfound(self, mock_run):
        # This hits the inner FileNotFoundError, not the _check_mypy one
        # But _check_mypy_installed will also raise FileNotFoundError -> returns False
        result = runner.invoke(app, ["type"])
        assert result.exit_code == 1

    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=[fake_completed(0), OSError("boom")],
    )
    def test_type_generic_exception(self, mock_run):
        result = runner.invoke(app, ["type"])
        assert result.exit_code == 1
        assert "执行失败" in result.output


# ---------------------------------------------------------------------------
# quality all
# ---------------------------------------------------------------------------
class TestQualityAll:
    @patch("src.commands.cli_quality.shutil.which", return_value=None)
    def test_all_ruff_not_installed(self, _):
        result = runner.invoke(app, ["all"])
        assert result.exit_code == 1
        assert "ruff 未安装" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=FileNotFoundError,
    )
    def test_all_black_not_installed(self, _, __):
        result = runner.invoke(app, ["all"])
        assert result.exit_code == 1
        assert "black 未安装" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=[fake_completed(0), FileNotFoundError],
    )
    def test_all_mypy_not_installed(self, _, __):
        result = runner.invoke(app, ["all"])
        assert result.exit_code == 1
        assert "mypy 未安装" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(0),
    )
    def test_all_pass(self, mock_run, _):
        result = runner.invoke(app, ["all"])
        assert result.exit_code == 0
        assert "所有检查通过" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        return_value=fake_completed(1, stdout="E501\n", stderr=""),
    )
    def test_all_black_fails(self, mock_run, _):
        # black returns non-zero but 'all' continues past it
        # ruff check also returns 1 -> exit
        result = runner.invoke(app, ["all"])
        # black failure doesn't exit, ruff does
        assert result.exit_code != 0

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=[
            fake_completed(0),  # black --version check
            fake_completed(0),  # mypy --version check
            fake_completed(0),  # black format
            fake_completed(1, stdout="err\n", stderr=""),  # ruff check
        ],
    )
    def test_all_ruff_fails(self, mock_run, _):
        result = runner.invoke(app, ["all"])
        assert result.exit_code != 0

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=[
            fake_completed(0),  # black --version
            fake_completed(0),  # mypy --version
            fake_completed(0),  # black format
            fake_completed(0),  # ruff check
            fake_completed(1, stdout="f.py:1: error: bad\n", stderr=""),  # mypy
        ],
    )
    def test_all_mypy_fails(self, mock_run, _):
        result = runner.invoke(app, ["all"])
        assert result.exit_code != 0
        assert "类型错误" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=[
            fake_completed(0),  # black --version
            fake_completed(0),  # mypy --version
            OSError("black boom"),  # black format
        ],
    )
    def test_all_black_exception(self, mock_run, _):
        result = runner.invoke(app, ["all"])
        assert result.exit_code == 1
        assert "black 执行失败" in result.output

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=[
            fake_completed(0),  # black --version
            fake_completed(0),  # mypy --version
            fake_completed(0),  # black format
            FileNotFoundError,  # ruff check FileNotFoundError
        ],
    )
    def test_all_ruff_filenotfound(self, mock_run, _):
        result = runner.invoke(app, ["all"])
        assert result.exit_code == 1

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=[
            fake_completed(0),  # black --version
            fake_completed(0),  # mypy --version
            fake_completed(0),  # black format
            fake_completed(0),  # ruff check
            FileNotFoundError,  # mypy FileNotFoundError
        ],
    )
    def test_all_mypy_filenotfound(self, mock_run, _):
        result = runner.invoke(app, ["all"])
        assert result.exit_code == 1

    @patch("src.commands.cli_quality.shutil.which", return_value="/usr/bin/ruff")
    @patch(
        "src.commands.cli_quality.subprocess.run",
        side_effect=[
            fake_completed(0),  # black --version
            fake_completed(0),  # mypy --version
            fake_completed(0),  # black format
            fake_completed(0),  # ruff check
            OSError("mypy boom"),  # mypy exception
        ],
    )
    def test_all_mypy_exception(self, mock_run, _):
        result = runner.invoke(app, ["all"])
        assert result.exit_code == 1
        assert "mypy 执行失败" in result.output


# ---------------------------------------------------------------------------
# main callback (no subcommand)
# ---------------------------------------------------------------------------
class TestMainCallback:
    def test_no_subcommand_shows_help(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0

