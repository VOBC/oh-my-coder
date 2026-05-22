"""Tests for coverage_api.py"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.web.coverage_api import (
    CoverageSummary,
    FileCoverage,
    format_coverage_report,
    get_coverage_badge_color,
    run_coverage_analysis,
)


class TestFileCoverage:
    """Test FileCoverage dataclass"""

    def test_default_values(self):
        fc = FileCoverage(path="test.py")
        assert fc.path == "test.py"
        assert fc.statements == 0
        assert fc.missing == 0
        assert fc.branches == 0
        assert fc.partial_branches == 0
        assert fc.coverage == 0.0
        assert fc.missing_lines == []

    def test_custom_values(self):
        fc = FileCoverage(
            path="src/main.py",
            statements=100,
            missing=20,
            branches=10,
            partial_branches=5,
            coverage=80.0,
            missing_lines=[1, 5, 10],
        )
        assert fc.coverage == 80.0
        assert len(fc.missing_lines) == 3


class TestCoverageSummary:
    """Test CoverageSummary dataclass"""

    def test_default_values(self):
        summary = CoverageSummary()
        assert summary.total_files == 0
        assert summary.total_statements == 0
        assert summary.total_missing == 0
        assert summary.total_branches == 0
        assert summary.total_partial == 0
        assert summary.overall_coverage == 0.0
        assert summary.files == []
        assert summary.timestamp == ""

    def test_with_files(self):
        summary = CoverageSummary(
            total_files=2,
            total_statements=150,
            overall_coverage=85.5,
        )
        assert summary.total_files == 2
        assert summary.overall_coverage == 85.5


class TestGetCoverageBadgeColor:
    """Test get_coverage_badge_color function"""

    def test_green_for_high_coverage(self):
        assert get_coverage_badge_color(100) == "#22c55e"
        assert get_coverage_badge_color(80) == "#22c55e"
        assert get_coverage_badge_color(95.5) == "#22c55e"

    def test_yellow_for_medium_coverage(self):
        assert get_coverage_badge_color(79.9) == "#eab308"
        assert get_coverage_badge_color(60) == "#eab308"
        assert get_coverage_badge_color(70) == "#eab308"

    def test_orange_for_low_coverage(self):
        assert get_coverage_badge_color(59.9) == "#f97316"
        assert get_coverage_badge_color(40) == "#f97316"
        assert get_coverage_badge_color(50) == "#f97316"

    def test_red_for_very_low_coverage(self):
        assert get_coverage_badge_color(39.9) == "#ef4444"
        assert get_coverage_badge_color(0) == "#ef4444"
        assert get_coverage_badge_color(20) == "#ef4444"

    def test_negative_coverage(self):
        assert get_coverage_badge_color(-1.0) == "#ef4444"


class TestParseCoverageFromOutput:
    """Test _parse_coverage_from_output function"""

    def test_parse_valid_output(self):
        from src.web.coverage_api import _parse_coverage_from_output

        stdout = """
=================================== test session starts ===================================
collected 10 items

tests/test_foo.py ......                                              [100%]

----------- coverage: platform darwin, python 3.12.0 -----------
Name                Stmts   Miss  Cover   Missing
-----------------------------------------------
src/foo.py             50     10    80%   12-15, 20
TOTAL                 100     20    80%

======================== 10 passed in 0.5s =========================
"""
        result = _parse_coverage_from_output(stdout)
        assert result == 80.0

    def test_parse_no_total_line(self):
        from src.web.coverage_api import _parse_coverage_from_output

        stdout = "No coverage data available"
        result = _parse_coverage_from_output(stdout)
        assert result == 0.0

    def test_parse_total_without_percent(self):
        from src.web.coverage_api import _parse_coverage_from_output

        stdout = "TOTAL  100  20  80"  # No % sign
        result = _parse_coverage_from_output(stdout)
        assert result == 0.0

    def test_parse_multiple_percent_signs(self):
        from src.web.coverage_api import _parse_coverage_from_output

        stdout = "TOTAL  100  20  85.5%\nSome other 90%"
        result = _parse_coverage_from_output(stdout)
        assert result == 85.5


class TestParseCoverageJson:
    """Test _parse_coverage_json function"""

    def test_parse_valid_json(self):
        from src.web.coverage_api import _parse_coverage_json

        data = {
            "files": {
                "/project/src/foo.py": {
                    "summary": {
                        "num_statements": 50,
                        "missing_lines": 10,
                        "num_branches": 5,
                        "partial_branches": 2,
                        "percent_covered": 80.0,
                    },
                    "missing_lines": [1, 2, 3],
                },
                "/project/src/bar.py": {
                    "summary": {
                        "num_statements": 30,
                        "missing_lines": 5,
                        "num_branches": 3,
                        "partial_branches": 1,
                        "percent_covered": 83.33,
                    },
                    "missing_lines": [10],
                },
            },
            "totals": {
                "num_statements": 80,
                "missing_lines": 15,
                "num_branches": 8,
                "partial_branches": 3,
                "percent_covered": 81.25,
            },
        }

        project_root = Path("/project")
        summary = _parse_coverage_json(data, project_root)

        assert summary.total_files == 2
        assert summary.total_statements == 80
        assert summary.overall_coverage == 81.25
        assert len(summary.files) == 2

    def test_parse_json_excludes_non_src(self):
        from src.web.coverage_api import _parse_coverage_json

        data = {
            "files": {
                "/project/tests/test_foo.py": {
                    "summary": {
                        "num_statements": 50,
                        "percent_covered": 100.0,
                    },
                    "missing_lines": [],
                },
                "/project/src/foo.py": {
                    "summary": {
                        "num_statements": 50,
                        "percent_covered": 80.0,
                    },
                    "missing_lines": [],
                },
            },
            "totals": {
                "num_statements": 100,
                "percent_covered": 90.0,
            },
        }

        project_root = Path("/project")
        summary = _parse_coverage_json(data, project_root)

        # Should only include src/ files
        assert len(summary.files) == 1
        assert summary.files[0].path == "src/foo.py"

    def test_parse_json_empty_files(self):
        from src.web.coverage_api import _parse_coverage_json

        data = {
            "files": {},
            "totals": {
                "num_statements": 0,
                "percent_covered": 0.0,
            },
        }

        summary = _parse_coverage_json(data, Path("/project"))
        assert summary.total_files == 0
        assert len(summary.files) == 0


class TestFormatCoverageReport:
    """Test format_coverage_report function"""

    def test_format_basic(self):
        summary = CoverageSummary(
            total_files=2,
            total_statements=100,
            total_missing=20,
            total_branches=10,
            total_partial=5,
            overall_coverage=80.0,
        )
        summary.files = [
            FileCoverage(path="src/foo.py", statements=50, missing=10, coverage=80.0),
            FileCoverage(path="src/bar.py", statements=50, missing=5, coverage=90.0),
        ]

        report = format_coverage_report(summary)

        assert "overall" in report
        assert report["overall"]["coverage"] == 80.0
        assert report["overall"]["total_files"] == 2
        assert len(report["files"]) == 2

    def test_format_limits_missing_lines(self):
        summary = CoverageSummary()
        summary.files = [
            FileCoverage(
                path="src/foo.py",
                coverage=50.0,
                missing_lines=list(range(1, 100)),  # 99 missing lines
            )
        ]

        report = format_coverage_report(summary)
        # Should limit to 20
        assert len(report["files"][0]["missing_lines"]) == 20

    def test_format_empty_summary(self):
        summary = CoverageSummary()
        report = format_coverage_report(summary)

        assert report["overall"]["coverage"] == 0.0
        assert report["overall"]["total_files"] == 0
        assert report["files"] == []


class TestRunCoverageAnalysis:
    """Test run_coverage_analysis function"""

    @patch("subprocess.run")
    def test_successful_analysis(self, mock_run, tmp_path):
        """Test successful coverage analysis with JSON output"""
        # Create a mock coverage.json
        import json

        coverage_data = {
            "files": {
                str(tmp_path / "src" / "foo.py"): {
                    "summary": {"num_statements": 50, "percent_covered": 80.0},
                    "missing_lines": [],
                }
            },
            "totals": {"num_statements": 50, "percent_covered": 80.0},
        }

        coverage_json = tmp_path / "coverage.json"
        coverage_json.write_text(json.dumps(coverage_data), encoding="utf-8")

        # Mock subprocess result
        mock_result = MagicMock()
        mock_result.stdout = "TOTAL  50  10  80.0%"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value=json.dumps(coverage_data)):
                with patch.object(Path, "unlink"):
                    summary = run_coverage_analysis(tmp_path)

        assert summary.overall_coverage == 80.0

    @patch("subprocess.run")
    def test_timeout(self, mock_run, tmp_path):
        """Test subprocess timeout"""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["pytest"], timeout=300)

        summary = run_coverage_analysis(tmp_path)
        assert summary.overall_coverage == -1.0

    @patch("subprocess.run")
    def test_subprocess_exception(self, mock_run, tmp_path):
        """Test general subprocess exception"""
        mock_run.side_effect = Exception("Command failed")

        summary = run_coverage_analysis(tmp_path)
        assert summary.overall_coverage == -1.0

    @patch("subprocess.run")
    def test_no_json_file_fallback_to_stdout(self, mock_run, tmp_path):
        """Test fallback to stdout parsing when JSON doesn't exist"""
        mock_result = MagicMock()
        mock_result.stdout = "TOTAL  100  20  80.0%"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch.object(Path, "exists", return_value=False):
            summary = run_coverage_analysis(tmp_path)

        assert summary.overall_coverage == 80.0

    @patch("subprocess.run")
    def test_json_parse_exception_fallback(self, mock_run, tmp_path):
        """Test fallback to stdout when JSON parsing fails"""
        mock_result = MagicMock()
        mock_result.stdout = "TOTAL  100  20  75.0%"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        coverage_json = tmp_path / "coverage.json"
        coverage_json.write_text("{invalid json}", encoding="utf-8")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "read_text", return_value="{invalid"):
                with patch.object(Path, "unlink"):
                    summary = run_coverage_analysis(tmp_path)

        assert summary.overall_coverage == 75.0
