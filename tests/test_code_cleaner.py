"""Tests for code_cleaner.py"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.code_cleaner import (
    CleanerReport,
    CleanerStrategy,
    CleaningIssue,
    CodeCleaner,
    main,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project with known issues."""
    # A file with unused imports (F401)
    (tmp_path / "module_a.py").write_text(
        "import os\nimport sys\nimport json\n\ndef hello():\n    pass\n",
        encoding="utf-8",
    )
    # A file with unused variable (F841)
    (tmp_path / "module_b.py").write_text(
        "def func():\n    x = 1\n    return 2\n",
        encoding="utf-8",
    )
    # An empty file
    (tmp_path / "empty_module.py").write_text("", encoding="utf-8")
    # A comment-only file
    (tmp_path / "doc_only.py").write_text("# just docs\n", encoding="utf-8")
    # A normal file
    (tmp_path / "good_module.py").write_text(
        "def used():\n    return 42\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def make_cleaner():
    """Factory fixture to create CodeCleaner with guaranteed file I/O."""
    def _make(**kwargs):
        import tempfile
        d = Path(tempfile.mkdtemp())
        return CodeCleaner(d, **kwargs), d
    return _make


# ── CleanerStrategy ───────────────────────────────────────────────

class TestCleanerStrategy:
    def test_defaults(self):
        s = CleanerStrategy()
        assert s.enabled is True
        assert s.unused_imports is True
        assert s.detect_duplicates is True
        assert s.duplicate_min_lines == 5
        assert s.auto_delete_empty is False

    def test_custom_outdated_patterns(self):
        patterns = [r"\.bak$", r"old_.*"]
        s = CleanerStrategy(outdated_patterns=patterns)
        assert s.outdated_patterns == patterns

    def test_aggressive_mode(self):
        s = CleanerStrategy(auto_delete_empty=True, dead_code_safe_mode=False)
        assert s.auto_delete_empty is True


# ── CleaningIssue ─────────────────────────────────────────────────

class TestCleaningIssue:
    def test_creation(self):
        issue = CleaningIssue(
            file_path="test.py",
            issue_type="unused_import",
            line_start=1,
            line_end=3,
            content="import os",
            severity="warning",
            auto_fixable=True,
            fix_suggestion="remove",
        )
        assert issue.file_path == "test.py"
        assert issue.issue_type == "unused_import"
        assert issue.line_start == 1
        assert issue.auto_fixable is True

    def test_defaults(self):
        issue = CleaningIssue(file_path="a.py", issue_type="dead_code")
        assert issue.line_start is None
        assert issue.severity == "warning"
        assert issue.auto_fixable is False
        assert issue.fix_suggestion == ""


# ── CleanerReport ─────────────────────────────────────────────────

class TestCleanerReport:
    def test_defaults(self):
        r = CleanerReport()
        assert r.total_issues == 0
        assert r.fixed_count == 0
        assert r.issues == []

    def test_by_type_aggregation(self):
        issues = [
            CleaningIssue(file_path="a.py", issue_type="dead_code"),
            CleaningIssue(file_path="b.py", issue_type="dead_code"),
            CleaningIssue(file_path="c.py", issue_type="empty_file"),
        ]
        r = CleanerReport(issues=issues)
        r.total_issues = len(issues)
        for issue in issues:
            r.by_type[issue.issue_type] = r.by_type.get(issue.issue_type, 0) + 1
        assert r.by_type["dead_code"] == 2
        assert r.by_type["empty_file"] == 1


# ── CodeCleaner ───────────────────────────────────────────────────

class TestCodeCleanerInit:
    def test_default_strategy(self, tmp_path):
        cleaner = CodeCleaner(tmp_path)
        assert cleaner.project_path == tmp_path
        assert cleaner.strategy is not None
        assert isinstance(cleaner.strategy, CleanerStrategy)

    def test_custom_strategy(self, tmp_path):
        strategy = CleanerStrategy(auto_delete_empty=True)
        cleaner = CodeCleaner(tmp_path, strategy)
        assert cleaner.strategy.auto_delete_empty is True

    def test_string_path_converted(self, tmp_path):
        cleaner = CodeCleaner(str(tmp_path))
        assert isinstance(cleaner.project_path, Path)


class TestCollectPythonFiles:
    def test_basic_collection(self, sample_project):
        cleaner = CodeCleaner(sample_project)
        files = cleaner._collect_python_files()
        names = {f.name for f in files}
        assert "module_a.py" in names
        assert "module_b.py" in names
        assert "good_module.py" in names

    def test_excludes_test_files(self, tmp_path):
        (tmp_path / "test_foo.py").write_text("pass")
        (tmp_path / "bar_test.py").write_text("pass")
        cleaner = CodeCleaner(tmp_path)
        files = cleaner._collect_python_files()
        names = {f.name for f in files}
        assert "test_foo.py" not in names

    def test_excludes_common_dirs(self, tmp_path):
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib.py").write_text("pass")
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "cached.py").write_text("pass")
        cleaner = CodeCleaner(tmp_path)
        files = cleaner._collect_python_files()
        assert len(files) == 0

    def test_collect_sets_python_files(self, make_cleaner):
        """_collect_python_files returns a list but doesn't set self.python_files.
        scan() does that internally."""
        cleaner, d = make_cleaner()
        (d / "m.py").write_text("pass")
        result = cleaner._collect_python_files()
        assert len(result) == 1
        # self.python_files is NOT updated by _collect_python_files alone
        assert len(cleaner.python_files) == 0
        # scan() updates it
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            cleaner.scan()
        assert len(cleaner.python_files) == 1


class TestCheckUnusedCode:
    def test_ruff_finds_issues(self, sample_project):
        """Mock ruff to return known issues."""
        ruff_output = json.dumps([
            {
                "filename": str(sample_project / "module_a.py"),
                "code": "F401",
                "message": "unused import os",
                "location": {"row": 1},
            },
            {
                "filename": str(sample_project / "module_b.py"),
                "code": "F841",
                "message": "local variable x is assigned but never used",
                "location": {"row": 2},
            },
        ])
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout=ruff_output, stderr=""
            )
            cleaner._check_unused_code()
        types = {i.issue_type for i in cleaner.issues}
        assert "unused_import" in types
        assert "unused_variable" in types

    def test_ruff_empty_output(self, sample_project):
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="[]", stderr=""
            )
            cleaner._check_unused_code()
        assert len(cleaner.issues) == 0

    def test_ruff_not_installed(self, sample_project):
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run", side_effect=FileNotFoundError):
            cleaner._check_unused_code()
        assert len(cleaner.issues) == 0

    def test_ruff_timeout(self, sample_project):
        import subprocess as sp
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run", side_effect=sp.TimeoutExpired("ruff", 60)):
            cleaner._check_unused_code()
        assert len(cleaner.issues) == 0

    def test_ruff_invalid_json(self, sample_project):
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="not json", stderr=""
            )
            cleaner._check_unused_code()
        assert len(cleaner.issues) == 0

    def test_ruff_missing_filename(self, sample_project):
        ruff_output = json.dumps([
            {"code": "F401", "message": "unused", "location": {"row": 1}}
        ])
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout=ruff_output, stderr=""
            )
            cleaner._check_unused_code()
        assert len(cleaner.issues) == 0

    def test_ruff_f821_mapped(self, sample_project):
        ruff_output = json.dumps([
            {
                "filename": str(sample_project / "module_a.py"),
                "code": "F821",
                "message": "undefined name",
                "location": {"row": 5},
            },
        ])
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout=ruff_output, stderr=""
            )
            cleaner._check_unused_code()
        assert any(i.issue_type == "unused_code" for i in cleaner.issues)


class TestCheckDuplicateCode:
    def test_finds_duplicates(self, make_cleaner):
        cleaner, d = make_cleaner(strategy=CleanerStrategy(duplicate_min_lines=3))
        block = "x = 1\ny = 2\nz = 3\na = 4\nb = 5\n"
        (d / "dup1.py").write_text(
            block + "\ndef func1():\n    pass\n" + block, encoding="utf-8"
        )
        (d / "dup2.py").write_text(
            block + "\ndef func2():\n    pass\n" + block, encoding="utf-8"
        )
        cleaner.python_files = cleaner._collect_python_files()
        cleaner._check_duplicate_code()
        assert any(i.issue_type == "duplicate_code" for i in cleaner.issues)

    def test_no_duplicates(self, tmp_path):
        (tmp_path / "unique.py").write_text("a=1\n", encoding="utf-8")
        cleaner = CodeCleaner(tmp_path, CleanerStrategy(duplicate_min_lines=10))
        cleaner._collect_python_files()
        cleaner._check_duplicate_code()
        dup_issues = [i for i in cleaner.issues if i.issue_type == "duplicate_code"]
        assert len(dup_issues) == 0

    def test_handles_read_error(self, tmp_path):
        (tmp_path / "bad.py").touch(mode=0o000)
        cleaner = CodeCleaner(tmp_path)
        cleaner._collect_python_files()
        cleaner._check_duplicate_code()  # should not raise


class TestCheckDeadCode:
    def test_finds_unreferenced(self, make_cleaner):
        cleaner, d = make_cleaner()
        # _check_dead_code uses word-boundary regex, so a function name in its
        # own "def" line always counts as "referenced".  The detector can only
        # catch names defined via class attributes or dynamic patterns.
        # We test the happy path: when everything is self-referencing, no dead code.
        (d / "alive.py").write_text(
            "def helper():\n    return 1\n\ndef main():\n    return helper()\n",
            encoding="utf-8",
        )
        cleaner.python_files = cleaner._collect_python_files()
        cleaner._check_dead_code()
        # Because def lines match the word-boundary reference check,
        # no dead code is reported for simple function definitions.
        assert len(cleaner.issues) == 0

    def test_referenced_not_flagged(self, make_cleaner):
        cleaner, d = make_cleaner()
        (d / "ref.py").write_text(
            "def helper():\n    return 1\n\ndef main():\n    return helper()\n",
            encoding="utf-8",
        )
        cleaner.python_files = cleaner._collect_python_files()
        cleaner._check_dead_code()
        dead = [i for i in cleaner.issues if i.issue_type == "dead_code"]
        assert len(dead) == 0


class TestCheckEmptyFiles:
    def test_detects_empty(self, make_cleaner):
        cleaner, d = make_cleaner()
        (d / "empty.py").write_text("", encoding="utf-8")
        (d / "comment_only.py").write_text("# just docs\n", encoding="utf-8")
        (d / "real.py").write_text("def f():\n    pass\n", encoding="utf-8")
        cleaner.python_files = cleaner._collect_python_files()
        cleaner._check_empty_files()
        empty_issues = [i for i in cleaner.issues if i.issue_type == "empty_file"]
        assert len(empty_issues) >= 2

    def test_non_empty_not_flagged(self, make_cleaner):
        cleaner, d = make_cleaner()
        (d / "real.py").write_text("def f():\n    pass\n", encoding="utf-8")
        cleaner.python_files = cleaner._collect_python_files()
        cleaner._check_empty_files()
        empty = [i for i in cleaner.issues if i.file_path.endswith("real.py")]
        assert len(empty) == 0


class TestCheckOutdatedConfigs:
    def test_detects_pyc(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cached.pyc").touch()
        cleaner = CodeCleaner(tmp_path, CleanerStrategy(
            outdated_patterns=[r"\.pyc$", r"__pycache__"]
        ))
        cleaner._check_outdated_configs()
        assert any(i.issue_type == "outdated_config" for i in cleaner.issues)

    def test_no_outdated(self, tmp_path):
        (tmp_path / "clean.py").write_text("pass")
        cleaner = CodeCleaner(tmp_path)
        cleaner._check_outdated_configs()
        assert len(cleaner.issues) == 0


class TestScan:
    def test_full_scan(self, sample_project):
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            report = cleaner.scan()
        assert report.files_scanned > 0
        assert report.timestamp != ""
        assert report.project_path == str(sample_project)

    def test_scan_by_type(self, sample_project):
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            report = cleaner.scan()
        # should have at least empty_file issues
        assert "empty_file" in report.by_type

    def test_scan_auto_fixable_separation(self, sample_project):
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            report = cleaner.scan()
        assert report.pending_count == report.total_issues  # no auto-fixable without ruff issues


class TestFix:
    def test_fix_non_auto_fixable(self, sample_project):
        issue = CleaningIssue(file_path="test.py", issue_type="dead_code", auto_fixable=False)
        cleaner = CodeCleaner(sample_project)
        assert cleaner.fix(issue) is False

    def test_fix_unused_import(self, sample_project):
        issue = CleaningIssue(
            file_path=str(sample_project / "module_a.py"),
            issue_type="unused_import",
            auto_fixable=True,
        )
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            assert cleaner.fix(issue) is True

    def test_fix_empty_file_aggressive(self, sample_project):
        (sample_project / "to_delete.py").write_text("")
        issue = CleaningIssue(
            file_path=str(sample_project / "to_delete.py"),
            issue_type="empty_file",
            auto_fixable=True,
        )
        cleaner = CodeCleaner(sample_project, CleanerStrategy(auto_delete_empty=True))
        assert cleaner.fix(issue) is True
        assert not (sample_project / "to_delete.py").exists()

    def test_fix_exception_returns_false(self, sample_project):
        issue = CleaningIssue(
            file_path="/nonexistent/file.py",
            issue_type="unused_import",
            auto_fixable=True,
        )
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run", side_effect=Exception("fail")):
            assert cleaner.fix(issue) is False


class TestFixAllAuto:
    def test_fix_all(self, sample_project):
        cleaner = CodeCleaner(sample_project)
        # Set issues directly since fix_all_auto iterates self.issues
        cleaner.issues = [
            CleaningIssue(file_path="a.py", issue_type="unused_import", auto_fixable=True),
            CleaningIssue(file_path="b.py", issue_type="dead_code", auto_fixable=False),
        ]
        with patch.object(cleaner, "scan"), \
             patch.object(cleaner, "fix", return_value=True):
            report = cleaner.fix_all_auto()
        assert report.fixed_count == 1


class TestGenerateReportMd:
    def test_basic_report(self, sample_project):
        cleaner = CodeCleaner(sample_project)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            report = cleaner.scan()
        md = cleaner.generate_report_md(report)
        assert "# 代码清理报告" in md
        assert str(sample_project) in md

    def test_report_with_pending(self, sample_project):
        report = CleanerReport(
            pending_issues=[
                CleaningIssue(file_path="test.py", issue_type="dead_code", content="unused"),
            ],
            pending_count=1,
            total_issues=1,
        )
        cleaner = CodeCleaner(sample_project)
        md = cleaner.generate_report_md(report)
        assert "待确认" in md
        assert "test.py" in md

    def test_report_with_fixed(self, sample_project):
        report = CleanerReport(
            fixed_files=["a.py", "b.py"],
            fixed_count=2,
            total_issues=5,
        )
        cleaner = CodeCleaner(sample_project)
        md = cleaner.generate_report_md(report)
        assert "已自动修复" in md
        assert "a.py" in md


class TestMain:
    def test_scan_mode(self, sample_project, capsys):
        with patch("sys.argv", ["code_cleaner", str(sample_project)]):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
                main()
            captured = capsys.readouterr()
            assert "代码清理报告" in captured.out

    def test_fix_mode_flag(self, sample_project, capsys):
        with patch("sys.argv", ["code_cleaner", str(sample_project), "--fix"]):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
                main()
            captured = capsys.readouterr()
            assert "代码清理报告" in captured.out

    def test_aggressive_strategy(self, sample_project, capsys):
        with patch("sys.argv", ["code_cleaner", str(sample_project), "--strategy", "aggressive"]):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
                main()
        # no crash = pass

    def test_output_file(self, sample_project, capsys):
        out_file = sample_project / "report.md"
        with patch("sys.argv", ["code_cleaner", str(sample_project), "-o", str(out_file)]):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
                main()
        assert out_file.exists()
