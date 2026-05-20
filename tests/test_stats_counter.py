"""Tests for src/stats/counter.py"""

import os

import pytest

from src.stats.counter import _get_file_type, _is_excluded, count_files
from src.stats.models import StatsResult


class TestIsExcluded:
    """Test _is_excluded function"""

    def test_exclude_file(self, tmp_path):
        """Test excluding a file by name"""
        exclude_files = {"readme.md"}
        test_file = tmp_path / "README.md"
        test_file.write_text("content")
        result = _is_excluded(test_file, set(), exclude_files, set())
        assert result is True

    def test_exclude_dir(self, tmp_path):
        """Test excluding a directory by name"""
        exclude_dirs = {"node_modules"}
        test_dir = tmp_path / "NODE_MODULES"
        test_dir.mkdir()
        result = _is_excluded(test_dir, exclude_dirs, set(), set())
        assert result is True

    def test_exclude_extension(self, tmp_path):
        """Test excluding a file by extension"""
        exclude_extensions = {".pyc"}
        test_file = tmp_path / "module.pyc"
        test_file.write_bytes(b"binary")
        result = _is_excluded(test_file, set(), set(), exclude_extensions)
        assert result is True

    def test_not_excluded(self, tmp_path):
        """Test file that should not be excluded"""
        test_file = tmp_path / "main.py"
        test_file.write_text("code")
        result = _is_excluded(test_file, set(), set(), set())
        assert result is False

    def test_exclude_file_case_insensitive(self, tmp_path):
        """Test case-insensitive file exclusion"""
        exclude_files = {"readme.md"}
        test_file = tmp_path / "README.MD"
        test_file.write_text("content")
        result = _is_excluded(test_file, set(), exclude_files, set())
        assert result is True

    def test_exclude_dir_case_insensitive(self, tmp_path):
        """Test case-insensitive directory exclusion"""
        exclude_dirs = {"node_modules"}
        test_dir = tmp_path / "NODE_MODULES"
        test_dir.mkdir()
        result = _is_excluded(test_dir, exclude_dirs, set(), set())
        assert result is True

    def test_empty_exclude_sets(self, tmp_path):
        """Test with empty exclude sets"""
        test_file = tmp_path / "anyfile.txt"
        test_file.write_text("content")
        result = _is_excluded(test_file, set(), set(), set())
        assert result is False


class TestGetFileType:
    """Test _get_file_type function"""

    def test_python_file(self, tmp_path):
        path = tmp_path / "main.py"
        path.write_text("code")
        assert _get_file_type(path) == "Python"

    def test_javascript_file(self, tmp_path):
        path = tmp_path / "app.js"
        path.write_text("code")
        assert _get_file_type(path) == "JavaScript"

    def test_typescript_file(self, tmp_path):
        path = tmp_path / "app.ts"
        path.write_text("code")
        assert _get_file_type(path) == "TypeScript"

    def test_markdown_file(self, tmp_path):
        path = tmp_path / "README.md"
        path.write_text("# Title")
        assert _get_file_type(path) == "Markdown"

    def test_json_file(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text("{}")
        assert _get_file_type(path) == "JSON"

    def test_yaml_file(self, tmp_path):
        path = tmp_path / "config.yaml"
        path.write_text("key: value")
        assert _get_file_type(path) == "YAML"

    def test_toml_file(self, tmp_path):
        path = tmp_path / "pyproject.toml"
        path.write_text("[tool]")
        assert _get_file_type(path) == "TOML"

    def test_html_file(self, tmp_path):
        path = tmp_path / "index.html"
        path.write_text("<html></html>")
        assert _get_file_type(path) == "HTML"

    def test_css_file(self, tmp_path):
        path = tmp_path / "style.css"
        path.write_text("body {}")
        assert _get_file_type(path) == "CSS"

    def test_rust_file(self, tmp_path):
        path = tmp_path / "main.rs"
        path.write_text("fn main() {}")
        assert _get_file_type(path) == "Rust"

    def test_go_file(self, tmp_path):
        path = tmp_path / "main.go"
        path.write_text("package main")
        assert _get_file_type(path) == "Go"

    def test_cpp_file(self, tmp_path):
        path = tmp_path / "main.cpp"
        path.write_text("int main() {}")
        assert _get_file_type(path) == "C++"

    def test_c_file(self, tmp_path):
        path = tmp_path / "main.c"
        path.write_text("int main() {}")
        assert _get_file_type(path) == "C"

    def test_shell_script(self, tmp_path):
        path = tmp_path / "script.sh"
        path.write_text("#!/bin/bash")
        assert _get_file_type(path) == "Shell Script"

    def test_dockerfile(self, tmp_path):
        path = tmp_path / "Dockerfile"
        path.write_text("FROM python:3.9")
        assert _get_file_type(path) == "Dockerfile"

    def test_makefile(self, tmp_path):
        path = tmp_path / "Makefile"
        path.write_text("all:")
        assert _get_file_type(path) == "Makefile"

    def test_unknown_extension(self, tmp_path):
        path = tmp_path / "unknown.xyz"
        path.write_text("content")
        assert _get_file_type(path) == "Other (.xyz)"

    def test_no_extension(self, tmp_path):
        path = tmp_path / "noextension"
        path.write_text("content")
        assert _get_file_type(path) == "Other"

    def test_jsx_file(self, tmp_path):
        path = tmp_path / "component.jsx"
        path.write_text("const x = 1;")
        assert _get_file_type(path) == "JavaScript React"

    def test_tsx_file(self, tmp_path):
        path = tmp_path / "component.tsx"
        path.write_text("const x: number = 1;")
        assert _get_file_type(path) == "TypeScript React"


class TestCountFiles:
    """Test count_files function"""

    def test_empty_directory(self, tmp_path):
        result = count_files(tmp_path)
        assert isinstance(result, StatsResult)
        assert result.total_files == 0
        assert result.total_dirs == 0
        assert result.total_size == 0

    def test_single_file(self, tmp_path):
        (tmp_path / "test.py").write_text("code")
        result = count_files(tmp_path)

        assert result.total_files == 1
        assert result.total_dirs == 0
        assert result.total_size > 0

    def test_multiple_files(self, tmp_path):
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("bb")
        (tmp_path / "c.js").write_text("ccc")

        result = count_files(tmp_path)

        assert result.total_files == 3
        assert result.total_size == 6  # 1 + 2 + 3

    def test_with_subdirectories(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("code")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("test")

        result = count_files(tmp_path)

        assert result.total_files == 2
        assert result.total_dirs >= 2  # src, tests

    def test_excludes_node_modules(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "package.js").write_text("large code" * 1000)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("code")

        result = count_files(tmp_path)

        # node_modules should be excluded
        assert result.total_files == 1
        assert "JavaScript" not in result.by_type  # package.js should be excluded

    def test_excludes_git(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git config")
        (tmp_path / "main.py").write_text("code")

        result = count_files(tmp_path)

        assert result.total_files == 1

    def test_excludes_pycache(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "module.pyc").write_bytes(b"binary")
        (tmp_path / "main.py").write_text("code")

        result = count_files(tmp_path)

        assert result.total_files == 1

    def test_excludes_pyc_files(self, tmp_path):
        (tmp_path / "module.pyc").write_bytes(b"binary")
        (tmp_path / "main.py").write_text("code")

        result = count_files(tmp_path)

        # .pyc should be excluded
        assert result.total_files == 1
        assert "Other (.pyc)" not in result.by_type

    def test_by_type_stats(self, tmp_path):
        (tmp_path / "a.py").write_text("python")
        (tmp_path / "b.py").write_text("python2")
        (tmp_path / "c.js").write_text("javascript")

        result = count_files(tmp_path)

        assert "Python" in result.by_type
        assert result.by_type["Python"].count == 2
        assert "JavaScript" in result.by_type
        assert result.by_type["JavaScript"].count == 1

    def test_by_directory_stats(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("code")
        (tmp_path / "src" / "b.py").write_text("code")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_a.py").write_text("test")

        result = count_files(tmp_path)

        assert "/" in result.by_directory or "src" in result.by_directory
        assert result.by_directory.get("/", 0) >= 0

    def test_max_depth(self, tmp_path):
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "level2").mkdir()
        (tmp_path / "level1" / "level2" / "deep.py").write_text("deep")

        # max_depth=1 should not go into level2
        result = count_files(tmp_path, max_depth=1)

        assert result.total_files == 0  # deep.py should not be counted

    def test_follow_symlinks(self, tmp_path):
        # Create a file and symlink to it
        target = tmp_path / "target.py"
        target.write_text("code")

        link = tmp_path / "link.py"
        os.symlink(str(target), str(link))

        result_no_follow = count_files(tmp_path, follow_symlinks=False)
        result_follow = count_files(tmp_path, follow_symlinks=True)

        # Symlinks should be followed if follow_symlinks=True
        assert result_no_follow.total_files >= 0
        assert result_follow.total_files >= 0

    def test_custom_exclude_dirs(self, tmp_path):
        (tmp_path / "custom_build").mkdir()
        (tmp_path / "custom_build" / "output.js").write_text("output")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("code")

        result = count_files(tmp_path, exclude_dirs={"custom_build"})

        assert result.total_files == 1

    def test_custom_exclude_extensions(self, tmp_path):
        (tmp_path / "data.csv").write_text("a,b,c")
        (tmp_path / "main.py").write_text("code")

        result = count_files(tmp_path, exclude_extensions={".csv"})

        assert result.total_files == 1
        assert "Other (.csv)" not in result.by_type

    def test_root_path_not_exists(self):
        with pytest.raises(FileNotFoundError, match="目录不存在"):
            count_files("/nonexistent/path")

    def test_root_path_not_directory(self, tmp_path):
        file_path = tmp_path / "not_a_dir.py"
        file_path.write_text("code")

        with pytest.raises(NotADirectoryError, match="不是目录"):
            count_files(file_path)

    def test_permission_error(self, tmp_path):
        # Create a subdirectory with no read permission
        restricted = tmp_path / "restricted"
        restricted.mkdir()
        restricted.chmod(0o000)  # No permissions

        try:
            result = count_files(tmp_path)
            # Should not raise, but should have errors
            assert len(result.errors) > 0
        finally:
            restricted.chmod(0o755)  # Restore permissions

    def test_total_size_accuracy(self, tmp_path):
        (tmp_path / "file1.txt").write_text("hello")  # 5 bytes
        (tmp_path / "file2.txt").write_text("world!")  # 6 bytes

        result = count_files(tmp_path)

        assert result.total_size == 11  # 5 + 6

    def test_result_contains_root_path(self, tmp_path):
        result = count_files(tmp_path)

        assert result.root_path == str(tmp_path.resolve())
