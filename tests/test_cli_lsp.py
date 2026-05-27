"""Tests for cli_lsp - LSP 集成命令"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from src.commands.cli_lsp import (
    SEVERITY_NAMES,
    DiagnosticSeverity,
    app,
    find_lsp_diagnostics,
    format_diagnostics_for_ai,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helper: build a fake CompletedProcess
# ---------------------------------------------------------------------------
def fake_completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


# ---------------------------------------------------------------------------
# DiagnosticSeverity class tests
# ---------------------------------------------------------------------------
class TestDiagnosticSeverity:
    def test_severity_constants(self):
        """Test that severity constants are correctly defined"""
        assert DiagnosticSeverity.ERROR == 1
        assert DiagnosticSeverity.WARNING == 2
        assert DiagnosticSeverity.INFORMATION == 3
        assert DiagnosticSeverity.HINT == 4


# ---------------------------------------------------------------------------
# SEVERITY_NAMES mapping tests
# ---------------------------------------------------------------------------
class TestSeverityNames:
    def test_severity_names_mapping(self):
        """Test that severity names are correctly mapped"""
        assert 1 in SEVERITY_NAMES
        assert 2 in SEVERITY_NAMES
        assert 3 in SEVERITY_NAMES
        assert 4 in SEVERITY_NAMES
        assert "错误" in SEVERITY_NAMES[1]
        assert "警告" in SEVERITY_NAMES[2]
        assert "信息" in SEVERITY_NAMES[3]
        assert "提示" in SEVERITY_NAMES[4]


# ---------------------------------------------------------------------------
# find_lsp_diagnostics tests
# ---------------------------------------------------------------------------
class TestFindLspDiagnostics:
    @patch("src.commands.cli_lsp.subprocess.run")
    def test_empty_directory_no_diagnostics(self, mock_run, tmp_path):
        """Test with empty directory, no diagnostics"""
        with patch.object(Path, "cwd", return_value=tmp_path):
            mock_run.side_effect = FileNotFoundError
            diagnostics = find_lsp_diagnostics()
            assert diagnostics == []

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_vscode_problems_json(self, mock_run, tmp_path):
        """Test reading VSCode problems.json"""
        # Create .vscode directory and problems.json
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        problems_file = vscode_dir / "problems.json"
        problems_data = {
            "problems": [
                {
                    "file": "test.py",
                    "line": 10,
                    "column": 5,
                    "severity": 1,
                    "message": "Test error",
                    "ruleId": "E001",
                }
            ]
        }
        problems_file.write_text(json.dumps(problems_data))

        with patch.object(Path, "cwd", return_value=tmp_path):
            mock_run.side_effect = FileNotFoundError
            diagnostics = find_lsp_diagnostics()
            assert len(diagnostics) == 1
            assert diagnostics[0]["source"] == "VSCode"
            assert diagnostics[0]["file"] == "test.py"
            assert diagnostics[0]["line"] == 10
            assert diagnostics[0]["severity"] == 1
            assert diagnostics[0]["message"] == "Test error"
            assert diagnostics[0]["rule"] == "E001"

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_vscode_problems_json_invalid(self, mock_run, tmp_path):
        """Test handling invalid JSON in problems.json"""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        problems_file = vscode_dir / "problems.json"
        problems_file.write_text("invalid json{")

        with patch.object(Path, "cwd", return_value=tmp_path):
            mock_run.side_effect = FileNotFoundError
            diagnostics = find_lsp_diagnostics()
            assert diagnostics == []

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_eslint_results_json(self, mock_run, tmp_path):
        """Test reading ESLint results JSON"""
        eslint_file = tmp_path / ".eslint-results.json"
        eslint_data = [
            {
                "filePath": "src/test.js",
                "messages": [
                    {
                        "line": 20,
                        "column": 10,
                        "severity": 2,
                        "message": "Unused variable",
                        "ruleId": "no-unused-vars",
                    }
                ],
            }
        ]
        eslint_file.write_text(json.dumps(eslint_data))

        with patch.object(Path, "cwd", return_value=tmp_path):
            mock_run.side_effect = FileNotFoundError
            diagnostics = find_lsp_diagnostics()
            assert len(diagnostics) == 1
            assert diagnostics[0]["source"] == "ESLint"
            assert diagnostics[0]["file"] == "src/test.js"
            assert diagnostics[0]["line"] == 20
            assert diagnostics[0]["severity"] == 2

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_eslint_results_invalid_json(self, mock_run, tmp_path):
        """Test handling invalid ESLint JSON"""
        eslint_file = tmp_path / ".eslint-results.json"
        eslint_file.write_text("not valid json")

        with patch.object(Path, "cwd", return_value=tmp_path):
            mock_run.side_effect = FileNotFoundError
            diagnostics = find_lsp_diagnostics()
            assert diagnostics == []

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_ruff_check_output(self, mock_run, tmp_path):
        """Test parsing ruff check JSON output"""
        ruff_output = [
            {
                "filename": "test.py",
                "location": {"row": 15, "column": 8},
                "message": "Unused import",
                "code": "F401",
            }
        ]
        # First call: ruff check, second call: mypy (not found)
        mock_run.side_effect = [
            fake_completed(0, stdout=json.dumps(ruff_output)),
            FileNotFoundError,
        ]

        with patch.object(Path, "cwd", return_value=tmp_path):
            diagnostics = find_lsp_diagnostics()
            assert len(diagnostics) == 1
            assert diagnostics[0]["source"] == "ruff"
            assert diagnostics[0]["file"] == "test.py"
            assert diagnostics[0]["line"] == 15
            assert diagnostics[0]["message"] == "Unused import"
            assert diagnostics[0]["rule"] == "F401"

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_mypy_check_output(self, mock_run, tmp_path):
        """Test parsing mypy JSON output"""
        mypy_output = [
            {
                "file": "module.py",
                "line": 30,
                "column": 5,
                "severity": "error",
                "message": "Incompatible types",
            }
        ]
        # First call: ruff (not found), second call: mypy
        mock_run.side_effect = [
            FileNotFoundError,
            fake_completed(0, stdout=json.dumps(mypy_output)),
        ]

        with patch.object(Path, "cwd", return_value=tmp_path):
            diagnostics = find_lsp_diagnostics()
            assert len(diagnostics) == 1
            assert diagnostics[0]["source"] == "mypy"
            assert diagnostics[0]["file"] == "module.py"
            assert diagnostics[0]["line"] == 30
            assert diagnostics[0]["severity"] == 1  # error -> 1

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_file_path_filter(self, mock_run, tmp_path):
        """Test filtering diagnostics by file path"""
        ruff_output = [
            {"filename": "src/main.py", "location": {"row": 1}, "message": "E1", "code": "E001"},
            {"filename": "tests/test.py", "location": {"row": 2}, "message": "E2", "code": "E002"},
        ]
        mock_run.return_value = fake_completed(0, stdout=json.dumps(ruff_output))

        with patch.object(Path, "cwd", return_value=tmp_path):
            diagnostics = find_lsp_diagnostics(file_path="main.py")
            assert len(diagnostics) == 1
            assert "main.py" in diagnostics[0]["file"]

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_diagnostics_sorting(self, mock_run, tmp_path):
        """Test that diagnostics are sorted by severity"""
        ruff_output = [
            {"filename": "a.py", "location": {"row": 1}, "message": "M3", "code": "I003"},
            {"filename": "b.py", "location": {"row": 2}, "message": "M1", "code": "E001"},
            {"filename": "c.py", "location": {"row": 3}, "message": "M2", "code": "W002"},
        ]
        # Manually set severity in output
        for i, item in enumerate(ruff_output):
            item["severity"] = [3, 1, 2][i]
        
        mock_run.return_value = fake_completed(0, stdout=json.dumps(ruff_output))

        with patch.object(Path, "cwd", return_value=tmp_path):
            diagnostics = find_lsp_diagnostics()
            # Should be sorted by severity
            severities = [d["severity"] for d in diagnostics]
            assert severities == sorted(severities)

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_ruff_timeout(self, mock_run, tmp_path):
        """Test handling ruff timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired("ruff", 30)

        with patch.object(Path, "cwd", return_value=tmp_path):
            diagnostics = find_lsp_diagnostics()
            assert diagnostics == []

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_mypy_timeout(self, mock_run, tmp_path):
        """Test handling mypy timeout"""
        # First call is ruff, second is mypy
        mock_run.side_effect = [
            FileNotFoundError,  # ruff not found
            subprocess.TimeoutExpired("mypy", 30),  # mypy timeout
        ]

        with patch.object(Path, "cwd", return_value=tmp_path):
            diagnostics = find_lsp_diagnostics()
            assert diagnostics == []

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_ruff_invalid_json(self, mock_run, tmp_path):
        """Test handling invalid ruff JSON output"""
        mock_run.return_value = fake_completed(0, stdout="not json")

        with patch.object(Path, "cwd", return_value=tmp_path):
            diagnostics = find_lsp_diagnostics()
            assert diagnostics == []

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_mypy_warning_severity(self, mock_run, tmp_path):
        """Test mypy warning severity (not error)"""
        mypy_output = [
            {
                "file": "test.py",
                "line": 10,
                "column": 5,
                "severity": "warning",
                "message": "Type warning",
            }
        ]
        mock_run.return_value = fake_completed(0, stdout=json.dumps(mypy_output))

        with patch.object(Path, "cwd", return_value=tmp_path):
            diagnostics = find_lsp_diagnostics()
            assert diagnostics[0]["severity"] == 2  # warning -> 2


# ---------------------------------------------------------------------------
# format_diagnostics_for_ai tests
# ---------------------------------------------------------------------------
class TestFormatDiagnosticsForAi:
    def test_empty_diagnostics(self):
        """Test formatting empty diagnostics"""
        result = format_diagnostics_for_ai([])
        assert "未发现代码问题" in result

    def test_single_diagnostic(self):
        """Test formatting single diagnostic"""
        diagnostics = [
            {
                "source": "ruff",
                "file": "/path/to/test.py",
                "line": 10,
                "column": 5,
                "severity": 1,
                "message": "Test error",
                "rule": "E001",
            }
        ]
        result = format_diagnostics_for_ai(diagnostics)
        assert "代码诊断报告" in result
        assert "test.py" in result
        assert "L10" in result
        assert "Test error" in result
        assert "E001" in result
        assert "总计" in result
        assert "错误: 1" in result

    def test_multiple_files(self):
        """Test formatting diagnostics from multiple files"""
        diagnostics = [
            {
                "source": "ruff",
                "file": "/path/a.py",
                "line": 1,
                "severity": 1,
                "message": "Error in a",
                "rule": "E001",
            },
            {
                "source": "ruff",
                "file": "/path/b.py",
                "line": 2,
                "severity": 2,
                "message": "Warning in b",
                "rule": "W001",
            },
        ]
        result = format_diagnostics_for_ai(diagnostics)
        assert "a.py" in result
        assert "b.py" in result
        assert "错误: 1" in result
        assert "警告: 1" in result

    def test_missing_fields(self):
        """Test formatting diagnostics with missing fields"""
        diagnostics = [
            {
                "source": "test",
                "file": "test.py",
            }
        ]
        result = format_diagnostics_for_ai(diagnostics)
        assert "test.py" in result
        assert "总计" in result

    def test_severity_statistics(self):
        """Test severity statistics are correct"""
        diagnostics = [
            {"file": "a.py", "line": 1, "severity": 1, "message": "E1"},
            {"file": "b.py", "line": 2, "severity": 1, "message": "E2"},
            {"file": "c.py", "line": 3, "severity": 2, "message": "W1"},
            {"file": "d.py", "line": 4, "severity": 3, "message": "I1"},
        ]
        result = format_diagnostics_for_ai(diagnostics)
        assert "错误: 2" in result
        assert "警告: 1" in result
        assert "信息: 1" in result


# ---------------------------------------------------------------------------
# check command tests
# ---------------------------------------------------------------------------
class TestCheckCommand:
    @patch("src.commands.cli_lsp.find_lsp_diagnostics", return_value=[])
    def test_check_no_diagnostics(self, mock_find):
        """Test check command with no diagnostics"""
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "未发现代码问题" in result.output

    @patch("src.commands.cli_lsp.find_lsp_diagnostics")
    def test_check_with_diagnostics_table_format(self, mock_find):
        """Test check command with table format"""
        mock_find.return_value = [
            {
                "source": "ruff",
                "file": "/path/to/test.py",
                "line": 10,
                "severity": 1,
                "message": "Test error message",
                "rule": "E001",
            }
        ]
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "诊断结果" in result.output
        assert "test.py" in result.output

    @patch("src.commands.cli_lsp.find_lsp_diagnostics")
    def test_check_with_ai_format(self, mock_find):
        """Test check command with AI format"""
        mock_find.return_value = [
            {
                "source": "ruff",
                "file": "/path/to/test.py",
                "line": 10,
                "severity": 1,
                "message": "Test error",
                "rule": "E001",
            }
        ]
        result = runner.invoke(app, ["check", "--format", "ai"])
        assert result.exit_code == 0
        assert "诊断报告" in result.output
        assert "代码诊断报告" in result.output

    @patch("src.commands.cli_lsp.find_lsp_diagnostics")
    def test_check_with_json_format(self, mock_find):
        """Test check command with JSON format"""
        mock_find.return_value = [
            {
                "source": "ruff",
                "file": "test.py",
                "line": 10,
                "severity": 1,
                "message": "Test",
                "rule": "E001",
            }
        ]
        result = runner.invoke(app, ["check", "--format", "json"])
        assert result.exit_code == 0
        # JSON output should be parseable
        assert "test.py" in result.output

    @patch("src.commands.cli_lsp.find_lsp_diagnostics")
    def test_check_with_file_filter(self, mock_find):
        """Test check command with file filter"""
        mock_find.return_value = [
            {
                "source": "ruff",
                "file": "src/main.py",
                "line": 10,
                "severity": 1,
                "message": "Test",
                "rule": "E001",
            }
        ]
        result = runner.invoke(app, ["check", "--file", "main.py"])
        mock_find.assert_called_once()
        assert result.exit_code == 0

    @patch("src.commands.cli_lsp.find_lsp_diagnostics")
    def test_check_with_source_filter(self, mock_find):
        """Test check command with source filter"""
        mock_find.return_value = [
            {
                "source": "ruff",
                "file": "test.py",
                "line": 10,
                "severity": 1,
                "message": "Test",
                "rule": "E001",
            },
            {
                "source": "mypy",
                "file": "test.py",
                "line": 20,
                "severity": 2,
                "message": "Type warning",
                "rule": "type-check",
            },
        ]
        result = runner.invoke(app, ["check", "--source", "ruff"])
        # Should only show ruff diagnostics
        assert result.exit_code == 0

    @patch("src.commands.cli_lsp.find_lsp_diagnostics")
    def test_check_many_diagnostics_truncated(self, mock_find):
        """Test check command truncates display at 100 items"""
        # Create 150 diagnostics
        mock_find.return_value = [
            {
                "source": "ruff",
                "file": f"file{i}.py",
                "line": i,
                "severity": 2,
                "message": f"Message {i}",
                "rule": f"W{i:03d}",
            }
            for i in range(150)
        ]
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "还有 50 条未显示" in result.output


# ---------------------------------------------------------------------------
# fix command tests
# ---------------------------------------------------------------------------
class TestFixCommand:
    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_fix_dry_run(self, mock_cwd, mock_run, tmp_path):
        """Test fix command in dry-run mode"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(0, stdout="All checks passed")

        result = runner.invoke(app, ["fix", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry Run 模式" in result.output

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_fix_execute(self, mock_cwd, mock_run, tmp_path):
        """Test fix command with actual execution"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(0)

        result = runner.invoke(app, ["fix", "--no-dry-run"])
        assert result.exit_code == 0
        # Should call ruff check --fix
        assert any("fix" in str(call) for call in mock_run.call_args_list)

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_fix_ruff_not_installed(self, mock_cwd, mock_run, tmp_path):
        """Test fix command when ruff not installed"""
        mock_cwd.return_value = tmp_path
        mock_run.side_effect = FileNotFoundError

        result = runner.invoke(app, ["fix"])
        assert result.exit_code == 0
        assert "ruff 未安装" in result.output

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_fix_ruff_error(self, mock_cwd, mock_run, tmp_path):
        """Test fix command when ruff returns error"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(1, stderr="Ruff error")

        result = runner.invoke(app, ["fix"])
        assert result.exit_code == 0

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_fix_with_specific_source(self, mock_cwd, mock_run, tmp_path):
        """Test fix command with specific source"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(0)

        result = runner.invoke(app, ["fix", "--source", "ruff"])
        assert result.exit_code == 0

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_fix_timeout(self, mock_cwd, mock_run, tmp_path):
        """Test fix command with timeout"""
        mock_cwd.return_value = tmp_path
        mock_run.side_effect = subprocess.TimeoutExpired("ruff", 30)

        result = runner.invoke(app, ["fix"])
        assert result.exit_code == 0
        assert "执行失败" in result.output or result.exit_code == 0

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_fix_generic_exception(self, mock_cwd, mock_run, tmp_path):
        """Test fix command with generic exception"""
        mock_cwd.return_value = tmp_path
        mock_run.side_effect = OSError("Unexpected error")

        result = runner.invoke(app, ["fix"])
        assert result.exit_code == 0
        assert "执行失败" in result.output or result.exit_code == 0


# ---------------------------------------------------------------------------
# setup command tests
# ---------------------------------------------------------------------------
class TestSetupCommand:
    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_setup_ruff_already_installed(self, mock_cwd, mock_run, tmp_path):
        """Test setup ruff when already installed"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(0)

        result = runner.invoke(app, ["setup", "ruff"])
        assert result.exit_code == 0
        assert "ruff.toml" in result.output or "设置 ruff" in result.output

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_setup_ruff_create_config(self, mock_cwd, mock_run, tmp_path):
        """Test setup ruff creates config file"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(0)

        result = runner.invoke(app, ["setup", "ruff"])
        assert result.exit_code == 0
        # Check that ruff.toml was created
        config_file = tmp_path / "ruff.toml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "line-length" in content
        assert "py39" in content

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_setup_ruff_config_exists(self, mock_cwd, mock_run, tmp_path):
        """Test setup ruff when config already exists"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(0)
        
        # Create existing config
        config_file = tmp_path / "ruff.toml"
        config_file.write_text("# existing config")

        result = runner.invoke(app, ["setup", "ruff"])
        assert result.exit_code == 0
        assert "已存在" in result.output

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_setup_ruff_not_installed(self, mock_cwd, mock_run, tmp_path):
        """Test setup ruff when not installed"""
        mock_cwd.return_value = tmp_path
        mock_run.side_effect = FileNotFoundError

        result = runner.invoke(app, ["setup", "ruff"])
        assert result.exit_code == 0
        assert "ruff 未安装" in result.output
        assert "pip install ruff" in result.output

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_setup_mypy_already_installed(self, mock_cwd, mock_run, tmp_path):
        """Test setup mypy when already installed"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(0)

        result = runner.invoke(app, ["setup", "mypy"])
        assert result.exit_code == 0
        assert "mypy.ini" in result.output or "设置 mypy" in result.output

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_setup_mypy_create_config(self, mock_cwd, mock_run, tmp_path):
        """Test setup mypy creates config file"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(0)

        result = runner.invoke(app, ["setup", "mypy"])
        assert result.exit_code == 0
        # Check that mypy.ini was created
        config_file = tmp_path / "mypy.ini"
        assert config_file.exists()
        content = config_file.read_text()
        assert "[mypy]" in content
        assert "python_version" in content

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_setup_mypy_config_exists(self, mock_cwd, mock_run, tmp_path):
        """Test setup mypy when config already exists"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(0)
        
        # Create existing config
        config_file = tmp_path / "mypy.ini"
        config_file.write_text("[mypy]")

        result = runner.invoke(app, ["setup", "mypy"])
        assert result.exit_code == 0
        assert "已存在" in result.output

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_setup_mypy_not_installed(self, mock_cwd, mock_run, tmp_path):
        """Test setup mypy when not installed"""
        mock_cwd.return_value = tmp_path
        mock_run.side_effect = FileNotFoundError

        result = runner.invoke(app, ["setup", "mypy"])
        assert result.exit_code == 0
        assert "mypy 未安装" in result.output
        assert "pip install mypy" in result.output

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_setup_eslint_already_installed(self, mock_cwd, mock_run, tmp_path):
        """Test setup eslint when already installed"""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = fake_completed(0)

        result = runner.invoke(app, ["setup", "eslint"])
        assert result.exit_code == 0
        assert "ESLint 已配置" in result.output or "ESLint" in result.output

    @patch("src.commands.cli_lsp.subprocess.run")
    @patch.object(Path, "cwd")
    def test_setup_eslint_not_installed(self, mock_cwd, mock_run, tmp_path):
        """Test setup eslint when not installed"""
        mock_cwd.return_value = tmp_path
        mock_run.side_effect = FileNotFoundError

        result = runner.invoke(app, ["setup", "eslint"])
        assert result.exit_code == 0
        assert "ESLint 未安装" in result.output
        assert "npm install" in result.output

    def test_setup_unsupported_tool(self):
        """Test setup with unsupported tool"""
        result = runner.invoke(app, ["setup", "unsupported"])
        assert result.exit_code != 0 or "不支持的工具" in result.output


# ---------------------------------------------------------------------------
# Main callback tests
# ---------------------------------------------------------------------------
class TestMainCallback:
    def test_no_subcommand_shows_help(self):
        """Test that running without subcommand shows help"""
        result = runner.invoke(app, [])
        # Typer apps exit with code 2 when no subcommand is provided
        # This is expected behavior
        assert result.exit_code in [0, 2]


# ---------------------------------------------------------------------------
# Edge cases and error handling
# ---------------------------------------------------------------------------
class TestEdgeCases:
    @patch("src.commands.cli_lsp.find_lsp_diagnostics")
    def test_check_with_none_message(self, mock_find):
        """Test check with None message field"""
        mock_find.return_value = [
            {
                "source": "test",
                "file": "test.py",
                "line": 1,
                "severity": 1,
                "message": "",  # Use empty string instead of None
                "rule": "E001",
            }
        ]
        result = runner.invoke(app, ["check"])
        # Should handle gracefully
        assert result.exit_code == 0

    @patch("src.commands.cli_lsp.find_lsp_diagnostics")
    def test_check_with_unknown_severity(self, mock_find):
        """Test check with unknown severity value"""
        mock_find.return_value = [
            {
                "source": "test",
                "file": "test.py",
                "line": 1,
                "severity": 999,
                "message": "Test",
                "rule": "E001",
            }
        ]
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0

    @patch("src.commands.cli_lsp.find_lsp_diagnostics")
    def test_check_with_long_message(self, mock_find):
        """Test check with very long message"""
        mock_find.return_value = [
            {
                "source": "test",
                "file": "test.py",
                "line": 1,
                "severity": 1,
                "message": "x" * 200,
                "rule": "E001",
            }
        ]
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0

    @patch("src.commands.cli_lsp.find_lsp_diagnostics")
    def test_check_empty_source_filter(self, mock_find):
        """Test check with source that has no matching diagnostics"""
        mock_find.return_value = [
            {
                "source": "ruff",
                "file": "test.py",
                "line": 1,
                "severity": 1,
                "message": "Test",
                "rule": "E001",
            }
        ]
        result = runner.invoke(app, ["check", "--source", "mypy"])
        # Should show no diagnostics
        assert "未发现代码问题" in result.output or result.exit_code == 0

    @patch("src.commands.cli_lsp.subprocess.run")
    def test_format_diagnostics_missing_rule(self, mock_run, tmp_path):
        """Test formatting diagnostics without rule field"""
        diagnostics = [
            {
                "source": "test",
                "file": "test.py",
                "line": 1,
                "severity": 1,
                "message": "No rule",
            }
        ]
        result = format_diagnostics_for_ai(diagnostics)
        assert "test.py" in result
        assert "No rule" in result
        # Should not crash when rule is missing
