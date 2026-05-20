"""Tests for src/agents/smart_test.py"""

import subprocess
from unittest.mock import MagicMock, patch

from src.agents.smart_test import (
    GitDiff,
    SmartTestEnhancer,
    TestCase,
    TestReport,
)

# ── GitDiff ──────────────────────────────────────────────────────────────

class TestGitDiff:
    def test_defaults(self):
        d = GitDiff()
        assert d.commit_hash == ""
        assert d.changed_files == []
        assert d.diff_details == {}
        assert d.files_added == 0
        assert d.lines_added == 0

    def test_with_values(self):
        d = GitDiff(
            commit_hash="abc123",
            commit_message="fix: something",
            author="test",
            changed_files=["src/a.py"],
            lines_added=10,
            lines_deleted=5,
        )
        assert d.commit_hash == "abc123"
        assert d.lines_added == 10


# ── TestCase ─────────────────────────────────────────────────────────────

class TestTestCase:
    def test_defaults(self):
        tc = TestCase()
        assert tc.test_type == "unit"
        assert tc.priority == "medium"

    def test_with_values(self):
        tc = TestCase(name="test_foo", target_function="Foo", priority="high")
        assert tc.priority == "high"
        assert tc.test_type == "unit"


# ── TestReport ───────────────────────────────────────────────────────────

class TestSmartTestReport:
    def test_defaults(self):
        r = TestReport()
        assert r.new_tests == []
        assert r.failures == []
        assert r.diff is None
        assert r.coverage_before is None

    def test_with_values(self):
        r = TestReport(
            timestamp="2026-01-01 00:00:00",
            regression_tests_run=10,
            regression_tests_passed=8,
            regression_tests_failed=2,
        )
        assert r.regression_tests_run == 10
        assert r.regression_tests_failed == 2


# ── SmartTestEnhancer ────────────────────────────────────────────────────

class TestSmartTestEnhancer:
    def test_init(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        assert e.project_path == tmp_path

    # ── get_git_diff ──

    @patch("src.agents.smart_test.subprocess.run")
    def test_get_git_diff_success(self, mock_run, tmp_path):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc1234|fix stuff|bob|2026-01-01\n"),
            MagicMock(returncode=0, stdout=" src/a.py | 10 +++\n src/b.py | 5 ---\n"),
            MagicMock(returncode=0, stdout=(
                "diff --git a/src/a.py b/src/a.py\n"
                "+class Foo:\n"
                "+    def bar(self):\n"
                "-    old_line\n"
            )),
        ]
        e = SmartTestEnhancer(tmp_path)
        diff = e.get_git_diff()
        assert diff is not None
        assert diff.commit_hash == "abc1234"
        assert diff.commit_message == "fix stuff"
        assert len(diff.changed_files) == 2
        assert diff.lines_added == 2
        assert diff.lines_deleted == 1

    @patch("src.agents.smart_test.subprocess.run")
    def test_get_git_diff_log_failure(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        e = SmartTestEnhancer(tmp_path)
        assert e.get_git_diff() is None

    @patch("src.agents.smart_test.subprocess.run")
    def test_get_git_diff_timeout(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=30)
        e = SmartTestEnhancer(tmp_path)
        assert e.get_git_diff() is None

    @patch("src.agents.smart_test.subprocess.run")
    def test_get_git_diff_file_not_found(self, mock_run, tmp_path):
        mock_run.side_effect = FileNotFoundError("git not found")
        e = SmartTestEnhancer(tmp_path)
        assert e.get_git_diff() is None

    # ── _parse_diff_details ──

    def test_parse_diff_details(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff()
        output = (
            "diff --git a/src/a.py b/src/a.py\n"
            "+new_line\n"
            "-old_line\n"
            "diff --git a/src/b.py b/src/b.py\n"
            "+another_new\n"
        )
        e._parse_diff_details(diff, output)
        assert diff.lines_added == 2
        assert diff.lines_deleted == 1
        assert "a/src/a.py" in diff.diff_details
        assert "a/src/b.py" in diff.diff_details

    def test_parse_diff_details_empty(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff()
        e._parse_diff_details(diff, "")
        assert diff.lines_added == 0

    def test_parse_diff_details_ignores_meta_lines(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff()
        output = (
            "+++ b/src/a.py\n"
            "--- a/src/a.py\n"
            "+real_addition\n"
            "-real_removal\n"
        )
        e._parse_diff_details(diff, output)
        assert diff.lines_added == 1
        assert diff.lines_deleted == 1

    # ── analyze_impact ──

    def test_analyze_impact_python(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(changed_files=["src/core/router.py", "README.md"])
        result = e.analyze_impact(diff)
        assert "src.core.router" in result["impacted_modules"]
        assert result["risk_level"] == "low"

    def test_analyze_impact_init_file(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(changed_files=["src/core/__init__.py"])
        result = e.analyze_impact(diff)
        assert "src.core" in result["impacted_modules"]
        assert "src.core.__init__" in result["impacted_modules"]

    def test_analyze_impact_high_risk(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(changed_files=["src/main.py"])
        result = e.analyze_impact(diff)
        assert result["risk_level"] == "high"

    def test_analyze_impact_medium_risk(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(changed_files=["src/service/handler.py"])
        result = e.analyze_impact(diff)
        assert result["risk_level"] == "medium"

    # ── generate_targeted_tests ──

    def test_generate_targeted_tests_with_class(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(
            changed_files=["src/utils/helper.py"],
            diff_details={
                "src/utils/helper.py": [
                    {"line": "class Helper:", "type": "add"},
                    {"line": "    def run(self):", "type": "add"},
                ]
            },
        )
        tests = e.generate_targeted_tests(diff)
        assert len(tests) == 1
        assert tests[0].target_function == "Helper"
        assert "Helper" in tests[0].test_code

    def test_generate_targeted_tests_with_function(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(
            changed_files=["src/utils/helper.py"],
            diff_details={
                "src/utils/helper.py": [
                    {"line": "def process_data(x):", "type": "add"},
                ]
            },
        )
        tests = e.generate_targeted_tests(diff)
        assert len(tests) == 1
        assert tests[0].target_function == "process_data"

    def test_generate_targeted_tests_skips_test_files(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(changed_files=["tests/test_helper.py"])
        tests = e.generate_targeted_tests(diff)
        assert len(tests) == 0

    def test_generate_targeted_tests_skips_non_python(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(changed_files=["README.md"])
        tests = e.generate_targeted_tests(diff)
        assert len(tests) == 0

    def test_generate_targeted_tests_high_priority(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(
            changed_files=["src/main.py"],
            diff_details={
                "src/main.py": [
                    {"line": "class App:", "type": "add"},
                ]
            },
        )
        tests = e.generate_targeted_tests(diff)
        assert tests[0].priority == "high"

    # ── _extract_target_class ──

    def test_extract_target_class(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        changes = [{"line": "class MyClass:", "type": "add"}]
        assert e._extract_target_class(changes) == "MyClass"

    def test_extract_target_function(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        changes = [{"line": "def my_func(x):", "type": "add"}]
        assert e._extract_target_class(changes) == "my_func"

    def test_extract_target_none(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        assert e._extract_target_class([]) is None

    # ── _generate_test_code ──

    def test_generate_test_code_pytest(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        code = e._generate_test_code("Foo", "src.utils.foo", "pytest")
        assert "class TestFoo" in code
        assert "from src.utils.foo import Foo" in code

    def test_generate_test_code_unittest(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        code = e._generate_test_code("Foo", "src.utils.foo", "unittest")
        assert code == ""

    # ── run_regression_tests ──

    @patch("src.agents.smart_test.subprocess.run")
    def test_run_regression_success(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="10 passed\n", stderr="")
        e = SmartTestEnhancer(tmp_path)
        result = e.run_regression_tests()
        assert result["tests_passed"] == 10
        assert result["tests_run"] == 10
        assert result["tests_failed"] == 0

    @patch("src.agents.smart_test.subprocess.run")
    def test_run_regression_with_failures(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout=(
            "8 passed, 2 failed\n"
            "FAILED tests/test_a.py::test_foo - AssertionError\n"
        ), stderr="")
        e = SmartTestEnhancer(tmp_path)
        result = e.run_regression_tests()
        assert result["tests_passed"] == 8
        assert result["tests_failed"] == 2
        assert result["tests_run"] == 10
        assert len(result["failures"]) > 0

    @patch("src.agents.smart_test.subprocess.run")
    def test_run_regression_timeout(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=120)
        e = SmartTestEnhancer(tmp_path)
        result = e.run_regression_tests()
        assert "timeout" in result["failures"][0].lower() or "超时" in result["failures"][0]

    @patch("src.agents.smart_test.subprocess.run")
    def test_run_regression_no_pytest(self, mock_run, tmp_path):
        mock_run.side_effect = FileNotFoundError("pytest")
        e = SmartTestEnhancer(tmp_path)
        result = e.run_regression_tests()
        assert "pytest" in result["failures"][0]

    # ── generate_report ──

    def test_generate_report(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(commit_hash="abc123")
        tests = [TestCase(name="test_foo")]
        reg = {"tests_run": 10, "tests_passed": 8, "tests_failed": 2, "failures": []}
        report = e.generate_report(diff, tests, reg)
        assert report.diff is not None
        assert len(report.new_tests) == 1
        assert report.regression_tests_run == 10
        assert report.project_path == str(tmp_path)

    # ── generate_report_md ──

    def test_generate_report_md(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        diff = GitDiff(
            commit_hash="abc1234567890",
            commit_message="fix bug",
            author="bob",
            changed_files=["src/a.py", "src/b.py"],
            lines_added=10,
            lines_deleted=5,
        )
        report = TestReport(
            timestamp="2026-01-01 00:00:00",
            project_path="/tmp/proj",
            diff=diff,
            new_tests=[TestCase(name="test_foo", file_path="tests/test_a.py")],
            regression_tests_run=10,
            regression_tests_passed=8,
            regression_tests_failed=2,
            failures=["test_bar: AssertionError"],
        )
        md = e.generate_report_md(report)
        assert "# 测试报告" in md
        assert "abc12345" in md
        assert "fix bug" in md
        assert "test_foo" in md
        assert "test_bar: AssertionError" in md

    def test_generate_report_md_truncates_files(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        files = [f"src/file{i}.py" for i in range(25)]
        diff = GitDiff(changed_files=files, commit_hash="abc", commit_message="m", author="a")
        report = TestReport(diff=diff, timestamp="2026-01-01")
        md = e.generate_report_md(report)
        assert "还有 5 个" in md

    def test_generate_report_md_no_diff(self, tmp_path):
        e = SmartTestEnhancer(tmp_path)
        report = TestReport(timestamp="2026-01-01")
        md = e.generate_report_md(report)
        assert "# 测试报告" in md
        assert "回归测试" in md


# ── main ─────────────────────────────────────────────────────────────────

class TestMain:
    @patch("src.agents.smart_test.SmartTestEnhancer")
    @patch("sys.argv", ["smart_test", "--generate", "--regression"])
    def test_main_generate_regression(self, mock_cls):
        mock_inst = MagicMock()
        mock_inst.get_git_diff.return_value = GitDiff(
            commit_hash="abc12345",
            changed_files=["src/a.py"],
            lines_added=10,
            lines_deleted=5,
        )
        mock_inst.generate_targeted_tests.return_value = [
            TestCase(name="test_a", file_path="tests/test_a.py")
        ]
        mock_inst.run_regression_tests.return_value = {
            "tests_run": 10,
            "tests_passed": 10,
            "tests_failed": 0,
            "failures": [],
        }
        mock_cls.return_value = mock_inst
        from src.agents.smart_test import main
        main()

    @patch("src.agents.smart_test.SmartTestEnhancer")
    @patch("sys.argv", ["smart_test", "--generate"])
    def test_main_no_diff(self, mock_cls):
        mock_inst = MagicMock()
        mock_inst.get_git_diff.return_value = None
        mock_cls.return_value = mock_inst
        from src.agents.smart_test import main
        main()
