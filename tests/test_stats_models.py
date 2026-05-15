"""Tests for src/stats/models.py - FileStats and StatsResult data models."""

import importlib.util

import pytest

_spec = importlib.util.spec_from_file_location(
    "stats_models", "src/stats/models.py"
)
_stats_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_stats_mod)
FileStats = _stats_mod.FileStats
StatsResult = _stats_mod.StatsResult


class TestFileStats:
    """Tests for FileStats dataclass."""

    def test_default_values(self):
        """FileStats should initialize with all default values."""
        stats = FileStats()
        assert stats.count == 0
        assert stats.size == 0
        assert stats.files == []

    def test_custom_values(self):
        """FileStats should accept custom values."""
        stats = FileStats(count=5, size=1024, files=["a.py", "b.py"])
        assert stats.count == 5
        assert stats.size == 1024
        assert stats.files == ["a.py", "b.py"]

    def test_files_is_independent_copy(self):
        """Each FileStats instance should have its own files list."""
        s1 = FileStats()
        s2 = FileStats()
        s1.files.append("test.py")
        assert s2.files == []

    def test_increment_count(self):
        """FileStats count should be mutable."""
        stats = FileStats(count=1)
        stats.count += 10
        assert stats.count == 11


class TestStatsResultToDict:
    """Tests for StatsResult.to_dict()."""

    def test_empty_to_dict(self):
        """An empty StatsResult should produce a well-formed dict."""
        result = StatsResult()
        d = result.to_dict()

        assert d["total_files"] == 0
        assert d["total_dirs"] == 0
        assert d["total_size"] == 0
        assert d["total_size_human"] == "0.00 B"
        assert d["by_type"] == {}
        assert d["by_directory"] == {}
        assert d["errors"] == []
        assert d["root_path"] == ""

    def test_to_dict_with_data(self):
        """to_dict should include all data with human-readable sizes."""
        result = StatsResult(
            total_files=10,
            total_dirs=3,
            total_size=2048,
            by_type={
                ".py": FileStats(count=5, size=1024, files=["main.py", "util.py"]),
                ".md": FileStats(count=3, size=512, files=["readme.md"]),
            },
            by_directory={"/src": 5, "/docs": 3},
            errors=["permission denied: /secret"],
            root_path="/project",
        )
        d = result.to_dict()

        assert d["total_files"] == 10
        assert d["total_dirs"] == 3
        assert d["total_size"] == 2048
        assert d["total_size_human"] == "2.00 KB"
        assert d["root_path"] == "/project"
        assert len(d["by_type"]) == 2
        assert d["by_type"][".py"]["count"] == 5
        assert d["by_type"][".py"]["size"] == 1024
        assert d["by_type"][".py"]["size_human"] == "1.00 KB"
        assert d["by_type"][".py"]["files"] == ["main.py", "util.py"]
        assert d["by_type"][".md"]["files"] == ["readme.md"]
        assert d["by_directory"] == {"/src": 5, "/docs": 3}
        assert d["errors"] == ["permission denied: /secret"]

    def test_to_dict_preserves_empty_type_files(self):
        """Even empty files list should be preserved in to_dict."""
        result = StatsResult(by_type={".txt": FileStats(count=0, size=0, files=[])})
        d = result.to_dict()
        assert d["by_type"][".txt"]["files"] == []


class TestStatsResultFormatSize:
    """Tests for _format_size static method."""

    @pytest.mark.parametrize(
        ("bytes_input", "expected"),
        [
            (0, "0.00 B"),
            (1, "1.00 B"),
            (512, "512.00 B"),
            (1023, "1023.00 B"),
            (1024, "1.00 KB"),
            (2048, "2.00 KB"),
            (1536, "1.50 KB"),
            (1048576, "1.00 MB"),
            (1073741824, "1.00 GB"),
            (1099511627776, "1.00 TB"),
            (1125899906842624, "1.00 PB"),
        ],
    )
    def test_format_size(self, bytes_input, expected):
        assert StatsResult._format_size(bytes_input) == expected


class TestStatsResultStr:
    """Tests for StatsResult.__str__()."""

    def test_empty_str(self):
        """Empty StatsResult should produce basic report."""
        result = StatsResult()
        report = str(result)
        assert "项目文件统计" in report
        assert "0.00 B" in report
        assert "总文件数: 0" in report
        assert "总目录数: 0" in report

    def test_str_with_by_type(self):
        """__str__ should include by_type table."""
        result = StatsResult(
            total_files=5,
            total_dirs=2,
            total_size=1024,
            by_type={
                ".py": FileStats(count=3, size=512, files=["a.py"]),
                ".md": FileStats(count=2, size=512, files=["b.md"]),
            },
        )
        report = str(result)
        assert ".py" in report
        assert ".md" in report
        assert "3" in report  # count for .py... just verify some part
        # Should include both type rows (table uses space alignment, not |)
        assert ".py" in report and ".md" in report

    def test_str_with_by_directory(self):
        """__str__ should include by_directory table."""
        directories = {f"/dir{i}": i for i in range(5)}
        result = StatsResult(
            total_files=10, total_dirs=5, total_size=100, by_directory=directories
        )
        report = str(result)
        assert "/dir0" in report
        assert "/dir4" in report

    def test_str_by_directory_limit_20(self):
        """by_directory in __str__ should be capped at 20 entries."""
        directories = {f"/dir{i}": i for i in range(25)}
        result = StatsResult(by_directory=directories)
        report = str(result)
        assert "... (更多)" in report

    def test_str_with_errors(self):
        """__str__ should include error section."""
        result = StatsResult(
            errors=["error 1", "error 2", "error 3"],
        )
        report = str(result)
        assert "error 1" in report
        assert "error 2" in report
        assert "error 3" in report
        assert "⚠️" in report

    def test_str_with_many_errors_capped(self):
        """With >5 errors, should show first 5 + count of remaining."""
        result = StatsResult(errors=[f"err {i}" for i in range(10)])
        report = str(result)
        assert "err 0" in report
        assert "err 4" in report
        assert "还有 5 个错误" in report
        assert "err 9" not in report

    def test_str_without_errors(self):
        """No error section when no errors."""
        result = StatsResult()
        report = str(result)
        assert "错误" not in report
        assert "⚠️" not in report

    def test_str_without_by_type(self):
        """No by_type section when empty."""
        result = StatsResult()
        report = str(result)
        assert "按文件类型统计" not in report

    def test_str_without_by_directory(self):
        """No by_directory section when empty."""
        result = StatsResult()
        report = str(result)
        assert "按目录统计" not in report

    def test_str_structure(self):
        """Check overall structure markers."""
        result = StatsResult(
            total_files=42,
            total_dirs=7,
            total_size=1000000,
            root_path="/test",
            by_type={".py": FileStats(count=10, size=500000)},
            by_directory={"/src": 10},
            errors=["test error"],
        )
        report = str(result)
        assert report.startswith("=" * 50)
        assert "📊 项目文件统计报告" in report
        assert "根目录: /test" in report
        assert "📁 总目录数: 7" in report
        assert "📄 总文件数: 42" in report
        assert "💾 总大小:" in report
        assert report.endswith("=" * 50)


class TestStatsResultRoundTrip:
    """End-to-end tests: create, convert to dict, verify consistency."""

    def test_round_trip_dict_str_consistency(self):
        """to_dict() values should be consistent with __str__() output."""
        result = StatsResult(
            total_files=100,
            total_dirs=20,
            total_size=1048576,  # 1 MB
            by_type={
                ".py": FileStats(count=50, size=524288, files=["a.py"]),
                ".json": FileStats(count=50, size=524288, files=["b.json"]),
            },
            by_directory={"/src": 50, "/tests": 50},
            errors=[],
            root_path="/home/project",
        )
        d = result.to_dict()
        assert d["total_size_human"] == "1.00 MB"
        assert d["by_type"][".py"]["count"] == 50

        report = str(result)
        assert "1.00 MB" in report
        assert "/home/project" in report


class TestStatsResultEdgeCases:
    """Edge cases for StatsResult."""

    def test_large_size_values(self):
        """Very large size values should be handled."""
        result = StatsResult(total_size=2**80)  # huge
        d = result.to_dict()
        assert "PB" in d["total_size_human"]

    def test_by_directory_empty(self):
        """Empty by_directory should not cause issues."""
        result = StatsResult(total_files=0, by_directory={})
        assert result.to_dict()["by_directory"] == {}
        report = str(result)
        assert "按目录统计" not in report

    def test_by_type_order_preserved(self):
        """Dict ordering in by_type should be preserved (Python 3.7+)."""
        types = {".a": FileStats(count=1), ".b": FileStats(count=2), ".c": FileStats(count=3)}
        result = StatsResult(by_type=types)
        keys = list(result.to_dict()["by_type"].keys())
        assert keys == [".a", ".b", ".c"]
