"""
Tests for src/commands/cli_clean.py.
"""
from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from src.commands.cli_clean import _display_report, app

runner = CliRunner()


def _make_report(**overrides):
    """Build a CleanerReport with sensible defaults."""
    from src.agents.code_cleaner import CleanerReport

    defaults = dict(
        timestamp="2026-01-01T00:00:00",
        project_path="/fake/project",
        total_issues=5,
        files_scanned=42,
        by_type={"unused_imports": 3, "dead_code": 2},
        issues=[],
        fixed_count=2,
        fixed_files=["a.py", "b.py"],
        pending_count=3,
        pending_issues=[],
        lines_removed=150,
        estimated_token_savings=5000,
    )
    defaults.update(overrides)
    return CleanerReport(**defaults)


def _make_issue(file_path="x.py", content="dead code", severity="warning",
                issue_type="dead_code", fix_suggestion="remove it"):
    from src.agents.code_cleaner import CleaningIssue
    return CleaningIssue(
        file_path=file_path, content=content, severity=severity,
        issue_type=issue_type, fix_suggestion=fix_suggestion,
    )


# ── CLI command tests ──────────────────────────────────────────────────
# The clean() function is @app.command() — invoke with runner.invoke(app, ['/path']).
# CodeCleaner is imported inside clean() from src.agents.code_cleaner.
# Use real temp dirs (tmp_path) to pass the exists() check.


def _invoke_clean(args, report=None, mock_method="scan"):
    """Helper: invoke clean with mocked CodeCleaner, using /tmp as path."""
    if report is None:
        report = _make_report()
    full_args = ["/tmp"] + list(args)
    with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
        instance = MockCleaner.return_value
        if mock_method == "scan":
            instance.scan.return_value = report
        else:
            instance.fix_all_auto.return_value = report
        instance.generate_report_md.return_value = "# Report"
        return runner.invoke(app, full_args)


class TestCleanCommand:
    """Tests for the `clean` CLI command."""

    def test_scan_default(self, tmp_path):
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.scan.return_value = report
            result = runner.invoke(app, [str(tmp_path)])
        assert result.exit_code == 0

    def test_scan_fix_flag(self, tmp_path):
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.fix_all_auto.return_value = report
            result = runner.invoke(app, [str(tmp_path), "--fix"])
        assert result.exit_code == 0
        instance.fix_all_auto.assert_called_once()

    def test_scan_fix_short_flag(self, tmp_path):
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.fix_all_auto.return_value = report
            result = runner.invoke(app, [str(tmp_path), "-f"])
        assert result.exit_code == 0
        instance.fix_all_auto.assert_called_once()

    def test_strategy_aggressive(self, tmp_path):
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.scan.return_value = report
            result = runner.invoke(
                app, [str(tmp_path), "--strategy", "aggressive"]
            )
        assert result.exit_code == 0

    def test_output_file_writes_report(self, tmp_path):
        out = tmp_path / "report.md"
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.scan.return_value = report
            instance.generate_report_md.return_value = "# Clean Report"
            result = runner.invoke(app, [str(tmp_path), "-o", str(out)])
        assert result.exit_code == 0
        assert out.read_text() == "# Clean Report"

    def test_verbose_flag(self, tmp_path):
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.scan.return_value = report
            result = runner.invoke(app, [str(tmp_path), "--verbose"])
        assert result.exit_code == 0

    def test_verbose_short_flag(self, tmp_path):
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.scan.return_value = report
            result = runner.invoke(app, [str(tmp_path), "-v"])
        assert result.exit_code == 0

    def test_path_not_exist_absolute(self):
        result = runner.invoke(app, ["/nonexistent/path/xyz"])
        assert result.exit_code == 1

    def test_path_not_exist_relative(self):
        result = runner.invoke(app, ["nonexistent_dir_abc123"])
        assert result.exit_code == 1

    def test_default_path_is_dot(self):
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.scan.return_value = report
            result = runner.invoke(app, [])
        assert result.exit_code == 0

    def test_output_message_in_result(self, tmp_path):
        out = tmp_path / "report.md"
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.scan.return_value = report
            instance.generate_report_md.return_value = "# Report"
            result = runner.invoke(app, [str(tmp_path), "-o", str(out)])
        assert result.exit_code == 0
        assert "报告已保存到" in result.stdout

    def test_scan_message_in_result(self, tmp_path):
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.scan.return_value = report
            result = runner.invoke(app, [str(tmp_path)])
        assert "扫描项目" in result.stdout

    def test_aggressive_message(self, tmp_path):
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.scan.return_value = report
            result = runner.invoke(
                app, [str(tmp_path), "--strategy", "aggressive"]
            )
        assert "激进模式" in result.stdout

    def test_safe_strategy_default(self, tmp_path):
        report = _make_report()
        with patch("src.agents.code_cleaner.CodeCleaner") as MockCleaner:
            instance = MockCleaner.return_value
            instance.scan.return_value = report
            result = runner.invoke(
                app, [str(tmp_path), "--strategy", "safe"]
            )
        # Activation banner NOT shown (hints section still mentions it)
        assert "激进模式：自动删除空文件" not in result.stdout


# ── _display_report tests ─────────────────────────────────────────────


class TestDisplayReport:
    """Tests for _display_report() function."""

    def test_stats_panel_shown(self):
        report = _make_report()
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(report)
        assert mock_console.print.call_count >= 2

    def test_stats_panel_contains_values(self):
        report = _make_report(
            files_scanned=10, total_issues=3, fixed_count=1,
            pending_count=2, lines_removed=50, estimated_token_savings=200,
        )
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(report)
        # Access Panel's renderable (the Markdown text inside)
        panel_call = mock_console.print.call_args_list[0]
        panel = panel_call[0][0]
        text = str(panel.renderable)
        assert "10" in text
        assert "3" in text
        assert "1" in text
        assert "2" in text
        assert "50" in text
        assert "200" in text

    def test_by_type_table_shown(self):
        report = _make_report(by_type={"unused": 5, "dead": 3})
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(report)
        # Console.print is called at least for panel + table + hints
        assert mock_console.print.call_count >= 3

    def test_by_type_empty_skipped(self):
        report = _make_report(by_type={})
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(report)
        from rich.table import Table
        for call in mock_console.print.call_args_list:
            args = call[0]
            if args and isinstance(args[0], Table):
                title = str(args[0].title or "")
                if "问题类型分布" in title:
                    pytest.fail("Table should not be shown for empty by_type")

    def test_fixed_files_list(self):
        report = _make_report(fixed_count=2, fixed_files=["a.py", "b.py"])
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(report)
        calls_str = str(mock_console.print.call_args_list)
        assert "a.py" in calls_str
        assert "b.py" in calls_str

    def test_fixed_files_truncation(self):
        files = [f"f{i}.py" for i in range(15)]
        report = _make_report(fixed_count=15, fixed_files=files)
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(report)
        calls_str = str(mock_console.print.call_args_list)
        assert "还有 5 个" in calls_str

    def test_fixed_files_empty_skipped(self):
        report = _make_report(fixed_count=0, fixed_files=[])
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(report)
        calls_str = str(mock_console.print.call_args_list)
        assert "已自动修复" not in calls_str

    def test_pending_issues_list(self):
        issue_report = _make_report(pending_count=1, pending_issues=[
            _make_issue(file_path="z.py", content="unused var x",
                        severity="warning", fix_suggestion="remove x")
        ])
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(issue_report)
        calls_str = str(mock_console.print.call_args_list)
        assert "z.py" in calls_str
        assert "unused var x" in calls_str

    def test_pending_issues_truncation(self):
        issues = [
            _make_issue(file_path=f"f{i}.py", content=f"issue {i}")
            for i in range(25)
        ]
        report = _make_report(pending_count=25, pending_issues=issues)
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(report)
        calls_str = str(mock_console.print.call_args_list)
        assert "还有 5 个" in calls_str

    def test_pending_issues_empty_skipped(self):
        report = _make_report(pending_count=0, pending_issues=[])
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(report)
        calls_str = str(mock_console.print.call_args_list)
        assert "待确认问题" not in calls_str

    def test_verbose_shows_full_details(self):
        issue_report = _make_report(pending_count=1, pending_issues=[
            _make_issue(file_path="a.py", content="dead code",
                        severity="error", fix_suggestion="delete it")
        ])
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(issue_report, verbose=True)
        calls_str = str(mock_console.print.call_args_list)
        assert "delete it" in calls_str

    def test_non_verbose_truncates_content(self):
        issue_report = _make_report(pending_count=1, pending_issues=[
            _make_issue(file_path="a.py", content="x" * 80,
                        severity="warning", fix_suggestion="fix")
        ])
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(issue_report, verbose=False)
        calls_str = str(mock_console.print.call_args_list)
        assert "x" * 80 not in calls_str

    def test_severity_emoji_mapping(self):
        for sev, expected_emoji in [("info", "ℹ"), ("warning", "⚠"), ("error", "❌")]:
            issue_report = _make_report(pending_count=1, pending_issues=[
                _make_issue(severity=sev)
            ])
            with patch("src.commands.cli_clean.console") as mock_console:
                _display_report(issue_report, verbose=True)
            calls_str = str(mock_console.print.call_args_list)
            assert expected_emoji in calls_str, f"Expected {expected_emoji} for {sev}"

    def test_unknown_severity_default_emoji(self):
        issue_report = _make_report(pending_count=1, pending_issues=[
            _make_issue(severity="unknown_type")
        ])
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(issue_report, verbose=True)
        calls_str = str(mock_console.print.call_args_list)
        assert "?" in calls_str

    def test_hints_always_shown(self):
        report = _make_report(by_type={}, fixed_files=[], pending_issues=[])
        with patch("src.commands.cli_clean.console") as mock_console:
            _display_report(report)
        calls_str = str(mock_console.print.call_args_list)
        assert "提示" in calls_str
        assert "--fix" in calls_str
        assert "--aggressive" in calls_str
        assert "-o" in calls_str
