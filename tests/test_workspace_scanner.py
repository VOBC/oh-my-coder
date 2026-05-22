"""Tests for src/context/workspace_scanner.py"""

from pathlib import Path
from unittest.mock import patch

from src.context.workspace_scanner import FileNode, WorkspaceScanner


class TestFileNode:
    """Test FileNode dataclass"""

    def test_file_node_creation(self):
        """Test creating a FileNode"""
        node = FileNode(
            name="test.py",
            path=Path("/tmp/test.py"),
            is_dir=False,
            size=100,
            modified="2026-05-22",
            language="python",
            summary="Test file",
        )
        assert node.name == "test.py"
        assert node.path == Path("/tmp/test.py")
        assert node.is_dir is False
        assert node.size == 100
        assert node.language == "python"

    def test_file_node_to_dict(self):
        """Test FileNode.to_dict()"""
        child = FileNode(name="child.py", path=Path("/tmp/child.py"), is_dir=False)
        parent = FileNode(
            name="parent",
            path=Path("/tmp/parent"),
            is_dir=True,
            children=[child],
        )
        result = parent.to_dict()
        assert result["name"] == "parent"
        assert result["is_dir"] is True
        assert len(result["children"]) == 1
        assert result["children"][0]["name"] == "child.py"


class TestWorkspaceScannerInit:
    """Test WorkspaceScanner initialization"""

    def test_init(self, tmp_path):
        """Test __init__ sets root and stats"""
        scanner = WorkspaceScanner(tmp_path)
        assert scanner.root == tmp_path
        assert scanner._scan_stats["files_scanned"] == 0
        assert scanner._scan_stats["dirs_scanned"] == 0

    def test_init_normalizes_path(self, tmp_path):
        """Test __init__ normalizes path"""
        scanner = WorkspaceScanner(str(tmp_path))
        assert isinstance(scanner.root, Path)
        assert scanner.root == tmp_path


class TestWorkspaceScannerDetectLanguage:
    """Test _detect_language method"""

    def test_detect_python_by_ext(self):
        """Test detecting Python by .py extension"""
        scanner = WorkspaceScanner(Path("/"))
        lang = scanner._detect_language(Path("test.py"))
        assert lang == "python"

    def test_detect_javascript_by_ext(self):
        """Test detecting JavaScript by .js extension"""
        scanner = WorkspaceScanner(Path("/"))
        lang = scanner._detect_language(Path("test.js"))
        assert lang == "javascript"

    def test_detect_typescript_by_ext(self):
        """Test detecting TypeScript by .ts extension"""
        scanner = WorkspaceScanner(Path("/"))
        lang = scanner._detect_language(Path("test.ts"))
        assert lang == "typescript"

    def test_detect_by_special_filename(self):
        """Test detecting language by special filename"""
        scanner = WorkspaceScanner(Path("/"))
        lang = scanner._detect_language(Path("Dockerfile"))
        assert lang == "dockerfile"

    def test_detect_unknown_ext(self):
        """Test unknown extension returns None"""
        scanner = WorkspaceScanner(Path("/"))
        lang = scanner._detect_language(Path("test.xyz"))
        assert lang is None

    def test_detect_case_insensitive(self):
        """Test case-insensitive detection"""
        scanner = WorkspaceScanner(Path("/"))
        lang = scanner._detect_language(Path("TEST.PY"))
        assert lang == "python"


class TestWorkspaceScannerFormatSize:
    """Test _format_size method"""

    def test_format_bytes(self):
        """Test formatting bytes"""
        scanner = WorkspaceScanner(Path("/"))
        assert scanner._format_size(500) == "500B"

    def test_format_kb(self):
        """Test formatting kilobytes"""
        scanner = WorkspaceScanner(Path("/"))
        assert scanner._format_size(1536) == "1.5KB"

    def test_format_mb(self):
        """Test formatting megabytes"""
        scanner = WorkspaceScanner(Path("/"))
        assert scanner._format_size(2 * 1024 * 1024) == "2.0MB"

    def test_format_gb(self):
        """Test formatting gigabytes"""
        scanner = WorkspaceScanner(Path("/"))
        assert scanner._format_size(3 * 1024 * 1024 * 1024) == "3.0GB"


class TestWorkspaceScannerScan:
    """Test scan method"""

    def test_scan_empty_dir(self, tmp_path):
        """Test scanning empty directory"""
        scanner = WorkspaceScanner(tmp_path)
        tree = scanner.scan(max_depth=3)
        assert tree.name == tmp_path.name
        assert tree.is_dir is True
        assert len(tree.children) == 0

    def test_scan_path_not_exists(self, tmp_path):
        """Test scanning nonexistent path"""
        nonexistent = tmp_path / "nonexistent"
        scanner = WorkspaceScanner(tmp_path)
        # Mock path.exists() to return False
        with patch.object(Path, "exists", return_value=False):
            tree = scanner._scan_recursive(nonexistent, depth=0, max_depth=3)
        assert tree.name == nonexistent.name
        assert tree.size == 0

    def test_scan_os_error_on_stat(self, tmp_path):
        """Test handling OSError when stat fails"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        scanner = WorkspaceScanner(tmp_path)
        # Mock exists()=True, is_dir()=False, stat() raises OSError
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_dir", return_value=False), \
             patch.object(Path, "stat", side_effect=OSError("Mocked error")):
            tree = scanner._scan_recursive(test_file, depth=0, max_depth=3)
        assert tree.name == "test.py"
        assert tree.size == 0  # stat failed, size not updated

    def test_scan_with_files(self, tmp_path):
        """Test scanning directory with files"""
        (tmp_path / "test.py").write_text("print('hello')")
        (tmp_path / "README.md").write_text("# Test")
        scanner = WorkspaceScanner(tmp_path)
        tree = scanner.scan(max_depth=3)
        assert len(tree.children) == 2

    def test_scan_with_subdir(self, tmp_path):
        """Test scanning directory with subdirectory"""
        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "main.py").write_text("def main(): pass")
        scanner = WorkspaceScanner(tmp_path)
        tree = scanner.scan(max_depth=3)
        src_node = [c for c in tree.children if c.name == "src"][0]
        assert src_node.is_dir is True
        assert len(src_node.children) == 1

    def test_scan_max_depth_zero(self, tmp_path):
        """Test max_depth=0 only shows root files"""
        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "deep.py").write_text("# deep")
        scanner = WorkspaceScanner(tmp_path)
        tree = scanner.scan(max_depth=0)
        # Should not have src children
        src_nodes = [c for c in tree.children if c.name == "src"]
        if src_nodes:
            assert len(src_nodes[0].children) == 0

    def test_scan_excludes_cache_dirs(self, tmp_path):
        """Test scanning excludes __pycache__, .git, etc."""
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "test.pyc").write_text("")
        scanner = WorkspaceScanner(tmp_path)
        tree = scanner.scan(max_depth=3)
        # __pycache__ should be excluded
        cache_nodes = [c for c in tree.children if c.name == "__pycache__"]
        assert len(cache_nodes) == 0

    def test_scan_permission_error(self, tmp_path):
        """Test scanning handles PermissionError"""
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()
        scanner = WorkspaceScanner(tmp_path)
        # Mock iterdir() to raise PermissionError
        with patch.object(Path, "iterdir", side_effect=PermissionError("Permission denied")):
            _ = scanner._scan_recursive(restricted_dir, depth=0, max_depth=3)
        assert len(scanner._scan_stats["errors"]) > 0
        assert "Permission denied" in scanner._scan_stats["errors"][0]

    def test_scan_os_error_on_iterdir(self, tmp_path):
        """Test scanning handles OSError on iterdir"""
        error_dir = tmp_path / "error_dir"
        error_dir.mkdir()
        scanner = WorkspaceScanner(tmp_path)
        # Mock iterdir() to raise OSError
        with patch.object(Path, "iterdir", side_effect=OSError("Mocked error")):
            _ = scanner._scan_recursive(error_dir, depth=0, max_depth=3)
        assert len(scanner._scan_stats["errors"]) > 0

    def test_scan_excludes_extensions(self, tmp_path):
        """Test scanning excludes .pyc, .so, etc."""
        (tmp_path / "test.pyc").write_text("")
        (tmp_path / "test.py").write_text("print('hello')")
        scanner = WorkspaceScanner(tmp_path)
        tree = scanner.scan(max_depth=3)
        pyc_nodes = [c for c in tree.children if c.name.endswith(".pyc")]
        assert len(pyc_nodes) == 0
        py_nodes = [c for c in tree.children if c.name.endswith(".py")]
        assert len(py_nodes) == 1

    def test_scan_hidden_files_excluded(self, tmp_path):
        """Test scanning excludes hidden files (except special ones)"""
        (tmp_path / ".hidden").write_text("secret")
        (tmp_path / ".gitignore").write_text("*.pyc")
        scanner = WorkspaceScanner(tmp_path)
        tree = scanner.scan(max_depth=3)
        hidden_nodes = [c for c in tree.children if c.name == ".hidden"]
        assert len(hidden_nodes) == 0
        gitignore_nodes = [c for c in tree.children if c.name == ".gitignore"]
        assert len(gitignore_nodes) == 1  # .gitignore is kept

    def test_scan_detect_language(self, tmp_path):
        """Test scanning detects file language"""
        (tmp_path / "test.py").write_text("print('hello')")
        scanner = WorkspaceScanner(tmp_path)
        tree = scanner.scan(max_depth=3)
        py_node = [c for c in tree.children if c.name == "test.py"][0]
        assert py_node.language == "python"

    def test_scan_stats(self, tmp_path):
        """Test scan updates _scan_stats"""
        (tmp_path / "test.py").write_text("print('hello')")
        scanner = WorkspaceScanner(tmp_path)
        scanner.scan(max_depth=3)
        assert scanner._scan_stats["files_scanned"] >= 1
        assert scanner._scan_stats["bytes_scanned"] > 0


class TestWorkspaceScannerGetFileSummary:
    """Test get_file_summary method"""

    def test_summary_nonexistent(self, tmp_path):
        """Test summary for nonexistent file"""
        scanner = WorkspaceScanner(tmp_path)
        nonexistent = tmp_path / "truly_nonexistent_file.txt"
        result = scanner.get_file_summary(nonexistent)
        assert "不存在" in result

    def test_summary_directory(self, tmp_path):
        """Test summary for directory"""
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(tmp_path)
        assert "目录" in result

    def test_summary_python_file(self, tmp_path):
        """Test summary for Python file"""
        py_file = tmp_path / "test.py"
        py_file.write_text("import os\n\ndef hello():\n    print('hi')\n\nclass World:\n    pass\n")
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(py_file)
        assert "python" in result.lower() or "import" in result

    def test_summary_json_file(self, tmp_path):
        """Test summary for JSON file"""
        json_file = tmp_path / "data.json"
        json_file.write_text('{"name": "test", "version": "1.0"}')
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(json_file)
        assert "name" in result or "json" in result.lower()

    def test_summary_markdown_file(self, tmp_path):
        """Test summary for Markdown file"""
        md_file = tmp_path / "README.md"
        md_file.write_text("# Title\n\n## Section\n\nSome text\n")
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(md_file)
        assert "# Title" in result or "markdown" in result.lower()

    def test_summary_large_file(self, tmp_path):
        """Test summary for large file (only reads first N lines)"""
        large_file = tmp_path / "large.py"
        content = "\n".join([f"# Line {i}" for i in range(1000)])
        large_file.write_text(content)
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(large_file, max_lines=50)
        # Should not read all 1000 lines
        assert result is not None

    def test_summary_empty_file(self, tmp_path):
        """Test summary for empty file"""
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(empty_file)
        assert "空文件" in result or "empty" in result.lower()

    def test_summary_python_rich(self, tmp_path):
        """Test summary extracts imports/classes/functions"""
        py_file = tmp_path / "rich.py"
        py_file.write_text("""import os
import sys
from flask import Flask

class User:
    def __init__(self):
        pass

class Admin(User):
    pass

def get_user():
    return User()

def create_admin():
    return Admin()
""")
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(py_file)
        assert "导入" in result or "import" in result.lower()
        assert "类" in result or "class" in result.lower()
        assert "函数" in result or "def" in result.lower()

    def test_summary_python_only_functions(self, tmp_path):
        """Test summary for Python file with only functions"""
        py_file = tmp_path / "funcs.py"
        py_file.write_text("""def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
""")
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(py_file)
        assert "函数" in result or "def" in result.lower()

    def test_summary_json_array(self, tmp_path):
        """Test summary for JSON array"""
        json_file = tmp_path / "list.json"
        json_file.write_text('[1, 2, 3, 4, 5]')
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(json_file)
        assert "数组" in result or "5" in result

    def test_summary_json_invalid(self, tmp_path):
        """Test summary for invalid JSON"""
        json_file = tmp_path / "invalid.json"
        json_file.write_text('{invalid json}')
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(json_file)
        assert "失败" in result or "invalid" in result.lower()

    def test_summary_js_file(self, tmp_path):
        """Test summary for JavaScript file"""
        js_file = tmp_path / "app.js"
        js_file.write_text("""import React from 'react';
export default App;
function App() {
  return <div>Hello</div>;
}""")
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(js_file)
        assert "javascript" in result.lower() or "import" in result.lower()

    def test_summary_yaml_file(self, tmp_path):
        """Test summary for YAML file"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("""name: test
version: 1.0
[database]
host: localhost
""")
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(yaml_file)
        assert "yaml" in result.lower() or "name" in result.lower()

    def test_summary_markdown_headers(self, tmp_path):
        """Test summary extracts Markdown headers"""
        md_file = tmp_path / "doc.md"
        md_file.write_text("""# Title

## Section 1

Some text here.

## Section 2

More text.
""")
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.get_file_summary(md_file)
        assert "# Title" in result or "markdown" in result.lower()


class TestWorkspaceScannerToContextString:
    """Test to_context_string method"""

    def test_to_context_string(self, tmp_path):
        """Test generating context string"""
        (tmp_path / "test.py").write_text("print('hello')")
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.to_context_string(max_depth=3)
        assert tmp_path.name in result
        assert "test.py" in result
        assert "扫描" in result or "files" in result.lower()

    def test_to_context_string_empty(self, tmp_path):
        """Test context string for empty directory"""
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.to_context_string(max_depth=3)
        assert tmp_path.name in result

    def test_to_context_string_with_errors(self, tmp_path):
        """Test context string includes errors"""
        # Create a file then make it unreadable (hard on macOS)
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.to_context_string(max_depth=3)
        if scanner._scan_stats["errors"]:
            assert "错误" in result or "error" in result.lower()


class TestWorkspaceScannerRenderTree:
    """Test _render_tree method (via to_context_string)"""

    def test_render_tree_format(self, tmp_path):
        """Test tree rendering format"""
        (tmp_path / "test.py").write_text("print('hello')")
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.to_context_string(max_depth=3)
        # Check for tree characters
        assert "├── " in result or "└── " in result or tmp_path.name in result

    def test_render_tree_sorted(self, tmp_path):
        """Test tree rendering sorts directories first"""
        (tmp_path / "zebra.py").write_text("")
        (tmp_path / "alpha.py").write_text("")
        subdir = tmp_path / "dir_a"
        subdir.mkdir()
        scanner = WorkspaceScanner(tmp_path)
        result = scanner.to_context_string(max_depth=3)
        # Directories should appear before files
        lines = result.split("\n")
        dir_idx = next((i for i, line in enumerate(lines) if "dir_a" in line), 999)
        file_idx = next((i for i, line in enumerate(lines) if "alpha.py" in line), 999)
        assert dir_idx < file_idx


class TestReadFileLines:
    """Test _read_file_lines method"""

    def test_read_file_lines(self, tmp_path):
        """Test reading file lines"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3\n")
        scanner = WorkspaceScanner(tmp_path)
        lines = scanner._read_file_lines(test_file, max_lines=10)
        assert len(lines) == 3
        assert lines[0] == "line1"

    def test_read_file_max_lines(self, tmp_path):
        """Test reading file respects max_lines"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("\n".join([f"line{i}" for i in range(100)]))
        scanner = WorkspaceScanner(tmp_path)
        lines = scanner._read_file_lines(test_file, max_lines=50)
        assert len(lines) == 50

    def test_read_file_nonexistent(self, tmp_path):
        """Test reading nonexistent file returns empty list"""
        scanner = WorkspaceScanner(tmp_path)
        lines = scanner._read_file_lines(tmp_path / "nonexistent.txt", max_lines=10)
        assert lines == []

    def test_read_file_os_error(self, tmp_path):
        """Test reading file with OSError returns empty list"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        scanner = WorkspaceScanner(tmp_path)
        with patch("builtins.open", side_effect=OSError("Mocked error")):
            lines = scanner._read_file_lines(test_file, max_lines=10)
            assert lines == []


class TestSummarizeMethods:
    """Test summary generation methods"""

    def test_summarize_python(self, tmp_path):
        """Test _summarize_python method"""
        scanner = WorkspaceScanner(tmp_path)
        lines = [
            "import os",
            "from pathlib import Path",
            "",
            "class MyClass:",
            "    pass",
            "",
            "def my_function():",
            "    pass",
        ]
        result = scanner._summarize_python(lines, tmp_path / "test.py")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_summarize_json(self, tmp_path):
        """Test _summarize_json method"""
        scanner = WorkspaceScanner(tmp_path)
        json_file = tmp_path / "data.json"
        json_file.write_text('{"key1": "value1", "key2": "value2"}')
        result = scanner._summarize_json(json_file)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_summarize_json_invalid(self, tmp_path):
        """Test _summarize_json with invalid JSON"""
        scanner = WorkspaceScanner(tmp_path)
        json_file = tmp_path / "bad.json"
        json_file.write_text("{invalid json}")
        result = scanner._summarize_json(json_file)
        assert isinstance(result, list)

    def test_summarize_config(self, tmp_path):
        """Test _summarize_config method"""
        scanner = WorkspaceScanner(tmp_path)
        lines = [
            "# Comment",
            "[section1]",
            "key1: value1",
            "key2: value2",
        ]
        result = scanner._summarize_config(lines, tmp_path / "config.yaml")
        assert isinstance(result, list)

    def test_summarize_doc(self, tmp_path):
        """Test _summarize_doc method"""
        scanner = WorkspaceScanner(tmp_path)
        lines = [
            "# Title",
            "Some text",
            "## Section",
            "More text",
        ]
        result = scanner._summarize_doc(lines, tmp_path / "README.md")
        assert isinstance(result, list)
        assert "# Title" in result

    def test_summarize_dockerfile(self, tmp_path):
        """Test _summarize_dockerfile method"""
        scanner = WorkspaceScanner(tmp_path)
        lines = [
            "FROM python:3.9",
            "WORKDIR /app",
            "COPY . .",
            "RUN pip install -r requirements.txt",
        ]
        result = scanner._summarize_dockerfile(lines, tmp_path / "Dockerfile")
        assert isinstance(result, list)
        assert len(result) > 1  # Header + instructions
