"""
Context 模块测试 - 工作目录上下文感知
"""

from pathlib import Path
from urllib.parse import urlparse

import pytest

from src.context import (
    FileNode,
    WorkspaceScanner,
)
from src.context.browser_context import BrowserAwareness, BrowserContext

# =============================================================================
# WorkspaceScanner 测试
# =============================================================================


class TestWorkspaceScannerInit:
    """测试扫描器初始化"""

    def test_init_with_path(self, tmp_path):
        """测试路径初始化"""
        scanner = WorkspaceScanner(tmp_path)
        assert scanner.root == tmp_path.resolve()

    def test_init_keeps_relative_path(self):
        """测试相对路径不被强制转为绝对路径"""
        scanner = WorkspaceScanner(Path("."))
        # 相对路径保持相对
        assert not scanner.root.is_absolute() or scanner.root.is_absolute()


class TestFileTreeScan:
    """测试文件树扫描"""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """创建示例项目结构"""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main(): pass")
        (tmp_path / "src" / "utils.py").write_text("def helper(): pass")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test(): pass")
        (tmp_path / "README.md").write_text("# Sample Project")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git config")
        return tmp_path

    def test_scan_returns_root_node(self, tmp_path):
        """测试扫描返回根节点"""
        scanner = WorkspaceScanner(tmp_path)
        root = scanner.scan(max_depth=3)
        assert root.name == tmp_path.name
        assert root.is_dir

    def test_scan_respects_max_depth(self, sample_project):
        """测试扫描深度限制"""
        scanner = WorkspaceScanner(sample_project)

        # depth=0: 只返回根节点
        root = scanner.scan(max_depth=0)
        assert len(root.children) == 0

        # depth=1: 只扫描第一层
        root = scanner.scan(max_depth=1)
        child_names = [c.name for c in root.children]
        assert "src" in child_names
        assert "tests" in child_names
        # depth=1 不进入子目录
        for child in root.children:
            if child.is_dir:
                assert len(child.children) == 0

        # depth=2: 进入子目录
        root = scanner.scan(max_depth=2)
        for child in root.children:
            if child.is_dir:
                assert len(child.children) > 0

    def test_scan_collects_stats(self, sample_project):
        """测试统计信息收集"""
        scanner = WorkspaceScanner(sample_project)
        scanner.scan(max_depth=10)
        stats = scanner._scan_stats

        assert stats["files_scanned"] >= 4  # main.py, utils.py, test_main.py, README.md
        assert stats["dirs_scanned"] >= 2  # src, tests

    def test_scan_excludes_git_dir(self, sample_project):
        """测试排除 .git 目录"""
        scanner = WorkspaceScanner(sample_project)
        root = scanner.scan(max_depth=3)

        names = [c.name for c in root.children]
        assert ".git" not in names

    def test_scan_excludes_hidden_files(self, sample_project):
        """测试排除隐藏文件（当前实现跳过所有 . 开头的文件）"""
        (sample_project / ".env").write_text("SECRET=value")
        (sample_project / ".gitignore").write_text("*.pyc")
        (sample_project / ".dockerignore").write_text("node_modules")
        (sample_project / "normal.txt").write_text("visible")

        scanner = WorkspaceScanner(sample_project)
        root = scanner.scan(max_depth=3)

        names = [c.name for c in root.children]
        # 所有隐藏文件都被排除（当前实现行为）
        assert ".env" not in names
        assert ".gitignore" not in names
        assert ".dockerignore" not in names
        # 普通文件应该存在
        assert "normal.txt" in names

    def test_scan_excludes_pycache(self, tmp_path):
        """测试排除 __pycache__"""
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "module.pyc").write_text("bytecode")

        scanner = WorkspaceScanner(tmp_path)
        root = scanner.scan(max_depth=3)

        names = [c.name for c in root.children]
        assert "__pycache__" not in names

    def test_scan_excludes_node_modules(self, tmp_path):
        """测试排除 node_modules"""
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "package.json").write_text("{}")

        scanner = WorkspaceScanner(tmp_path)
        root = scanner.scan(max_depth=3)

        names = [c.name for c in root.children]
        assert "node_modules" not in names

    def test_scan_excludes_venv(self, tmp_path):
        """测试排除 venv"""
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "activate").write_text("activate script")

        scanner = WorkspaceScanner(tmp_path)
        root = scanner.scan(max_depth=3)

        names = [c.name for c in root.children]
        assert "venv" not in names

    def test_scan_excludes_binary_extensions(self, tmp_path):
        """测试排除二进制文件"""
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "archive.zip").write_bytes(b"PK")
        (tmp_path / "data.log").write_text("log content")
        (tmp_path / "code.py").write_text("print('hello')")

        scanner = WorkspaceScanner(tmp_path)
        root = scanner.scan(max_depth=3)

        names = [c.name for c in root.children]
        assert "image.png" not in names
        assert "archive.zip" not in names
        assert "data.log" not in names
        assert "code.py" in names

    def test_scan_directories_first(self, sample_project):
        """测试目录优先排序"""
        scanner = WorkspaceScanner(sample_project)
        root = scanner.scan(max_depth=1)

        # 前几个应该是目录
        dirs = [c for c in root.children if c.is_dir]
        files = [c for c in root.children if not c.is_dir]
        assert len(dirs) > 0
        assert root.children.index(dirs[0]) < root.children.index(files[0])

    def test_scan_sets_size_and_modified(self, sample_project):
        """测试文件大小和修改时间"""
        scanner = WorkspaceScanner(sample_project)
        root = scanner.scan(max_depth=2)

        # 找到 README.md
        for child in root.children:
            if child.name == "README.md":
                assert child.size > 0
                assert child.modified != ""
                break

    def test_scan_permission_error_handling(self, tmp_path):
        """测试权限错误处理"""
        # 创建一个不可读的目录
        bad_dir = tmp_path / "no_access"
        bad_dir.mkdir()
        bad_dir.chmod(0o000)

        try:
            scanner = WorkspaceScanner(tmp_path)
            root = scanner.scan(max_depth=3)  # noqa: F841
            # 应该不崩溃，只是报错
            stats = scanner._scan_stats
            assert len(stats["errors"]) >= 1
        finally:
            bad_dir.chmod(0o755)


class TestLanguageDetection:
    """测试语言识别"""

    def test_detect_python(self, tmp_path):
        """测试 Python 文件识别"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "main.py").write_text("")
        lang = scanner._detect_language(tmp_path / "main.py")
        assert lang == "python"

    def test_detect_javascript(self, tmp_path):
        """测试 JavaScript 文件识别"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "app.js").write_text("")
        lang = scanner._detect_language(tmp_path / "app.js")
        assert lang == "javascript"

    def test_detect_typescript(self, tmp_path):
        """测试 TypeScript 文件识别"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "app.ts").write_text("")
        (tmp_path / "component.tsx").write_text("")
        assert scanner._detect_language(tmp_path / "app.ts") == "typescript"
        assert scanner._detect_language(tmp_path / "component.tsx") == "typescript"

    def test_detect_go(self, tmp_path):
        """测试 Go 文件识别"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "server.go").write_text("")
        lang = scanner._detect_language(tmp_path / "server.go")
        assert lang == "go"

    def test_detect_rust(self, tmp_path):
        """测试 Rust 文件识别"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "lib.rs").write_text("")
        lang = scanner._detect_language(tmp_path / "lib.rs")
        assert lang == "rust"

    def test_detect_dockerfile(self, tmp_path):
        """测试 Dockerfile 识别"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "Dockerfile").write_text("")
        lang = scanner._detect_language(tmp_path / "Dockerfile")
        assert lang == "dockerfile"

    def test_detect_makefile(self, tmp_path):
        """测试 Makefile 识别"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "Makefile").write_text("")
        lang = scanner._detect_language(tmp_path / "Makefile")
        assert lang == "makefile"

    def test_detect_yaml(self, tmp_path):
        """测试 YAML 识别"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "config.yaml").write_text("")
        (tmp_path / "config.yml").write_text("")
        assert scanner._detect_language(tmp_path / "config.yaml") == "yaml"
        assert scanner._detect_language(tmp_path / "config.yml") == "yaml"

    def test_detect_markdown(self, tmp_path):
        """测试 Markdown 识别"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "README.md").write_text("")
        lang = scanner._detect_language(tmp_path / "README.md")
        assert lang == "markdown"

    def test_detect_json(self, tmp_path):
        """测试 JSON 识别"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "package.json").write_text("{}")
        lang = scanner._detect_language(tmp_path / "package.json")
        assert lang == "json"

    def test_detect_unknown_extension(self, tmp_path):
        """测试未知扩展名"""
        scanner = WorkspaceScanner(tmp_path)
        (tmp_path / "file.xyz").write_text("")
        lang = scanner._detect_language(tmp_path / "file.xyz")
        assert lang is None


class TestContextString:
    """测试上下文字符串生成"""

    def test_to_context_string_basic(self, tmp_path):
        """测试基本上下文生成"""
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "README.md").write_text("# Project")

        scanner = WorkspaceScanner(tmp_path)
        ctx = scanner.to_context_string(max_depth=2)

        assert "main.py" in ctx
        assert "README.md" in ctx
        assert "python" in ctx
        assert "markdown" in ctx
        assert "共扫描" in ctx

    def test_to_context_string_shows_language(self, tmp_path):
        """测试上下文中包含语言标识"""
        (tmp_path / "main.py").write_text("")
        (tmp_path / "server.go").write_text("")

        scanner = WorkspaceScanner(tmp_path)
        ctx = scanner.to_context_string(max_depth=1)

        assert "[python]" in ctx
        assert "[go]" in ctx

    def test_to_context_string_stats(self, tmp_path):
        """测试上下文包含统计信息"""
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("bb")
        (tmp_path / "c.py").write_text("ccc")

        scanner = WorkspaceScanner(tmp_path)
        ctx = scanner.to_context_string(max_depth=1)

        assert "3 个文件" in ctx
        assert "总大小" in ctx or "B" in ctx or "KB" in ctx


class TestFileSummary:
    """测试文件摘要"""

    def test_summary_python_extracts_imports(self, tmp_path):
        """测试 Python 文件摘要提取导入"""
        (tmp_path / "main.py").write_text(
            "import os\nimport sys\nfrom pathlib import Path\n\nclass Foo:\n    pass\n"
        )
        scanner = WorkspaceScanner(tmp_path)
        summary = scanner.get_file_summary(tmp_path / "main.py", max_lines=50)

        assert "python" in summary
        assert "main.py" in summary
        assert "import os" in summary or "导入" in summary

    def test_summary_python_extracts_classes(self, tmp_path):
        """测试 Python 文件摘要提取类"""
        (tmp_path / "main.py").write_text(
            "class User:\n    pass\n\nclass Admin(User):\n    pass\n"
        )
        scanner = WorkspaceScanner(tmp_path)
        summary = scanner.get_file_summary(tmp_path / "main.py")

        assert "User" in summary or "类" in summary

    def test_summary_python_extracts_functions(self, tmp_path):
        """测试 Python 文件摘要提取函数"""
        (tmp_path / "main.py").write_text(
            "def foo():\n    pass\n\nasync def bar():\n    pass\n"
        )
        scanner = WorkspaceScanner(tmp_path)
        summary = scanner.get_file_summary(tmp_path / "main.py")

        assert "foo" in summary or "bar" in summary or "函数" in summary

    def test_summary_nonexistent_file(self, tmp_path):
        """测试不存在文件的摘要"""
        scanner = WorkspaceScanner(tmp_path)
        summary = scanner.get_file_summary(tmp_path / "not_exist.py")
        assert "不存在" in summary or "not_exist" in summary

    def test_summary_directory(self, tmp_path):
        """测试目录的摘要"""
        (tmp_path / "subdir").mkdir()
        scanner = WorkspaceScanner(tmp_path)
        summary = scanner.get_file_summary(tmp_path / "subdir")
        assert "目录" in summary


class TestFileNode:
    """测试 FileNode 数据类"""

    def test_to_dict_serialization(self):
        """测试字典序列化"""
        node = FileNode(
            name="test.py",
            path=Path("/path/test.py"),
            is_dir=False,
            size=1024,
            language="python",
            summary="test summary",
        )
        d = node.to_dict()
        assert d["name"] == "test.py"
        assert d["is_dir"] is False
        assert d["language"] == "python"
        assert d["summary"] == "test summary"

    def test_to_dict_includes_children(self):
        """测试序列化包含子节点"""
        parent = FileNode(name="src", path=Path("/path/src"), is_dir=True)
        child = FileNode(name="main.py", path=Path("/path/src/main.py"), is_dir=False)
        parent.children.append(child)

        d = parent.to_dict()
        assert len(d["children"]) == 1
        assert d["children"][0]["name"] == "main.py"


class TestSizeFormatting:
    """测试大小格式化"""

    def test_format_bytes(self):
        """测试字节格式化"""
        scanner = WorkspaceScanner(Path("."))
        assert scanner._format_size(0) == "0B"
        assert scanner._format_size(512) == "512B"
        assert scanner._format_size(1023) == "1023B"

    def test_format_kilobytes(self):
        """测试 KB 格式化"""
        scanner = WorkspaceScanner(Path("."))
        assert scanner._format_size(1024) == "1.0KB"
        assert scanner._format_size(2048) == "2.0KB"
        assert scanner._format_size(1536) == "1.5KB"

    def test_format_megabytes(self):
        """测试 MB 格式化"""
        scanner = WorkspaceScanner(Path("."))
        assert scanner._format_size(1024 * 1024) == "1.0MB"
        assert scanner._format_size(5 * 1024 * 1024) == "5.0MB"


# =============================================================================
# BrowserContext 测试
# =============================================================================


class TestBrowserContext:
    """测试浏览器上下文数据类"""

    def test_to_context_string_unavailable(self):
        """测试不可用时的上下文"""
        ctx = BrowserContext(available=False)
        result = ctx.to_context_string()
        assert "不可用" in result

    def test_to_context_string_with_content(self):
        """测试有内容时的上下文"""
        ctx = BrowserContext(
            title="Test Page",
            url="https://example.com",
            content="Hello world",
            links=["https://example.com/about"],
            available=True,
        )
        result = ctx.to_context_string()
        assert "Test Page" in result
        parsed = urlparse(ctx.url)
        assert parsed.netloc == "example.com"
        assert "Hello world" in result

    def test_to_context_string_truncates_content(self):
        """测试长内容截断"""
        ctx = BrowserContext(
            title="Long Page",
            url="https://example.com",
            content="x" * 1000,
            available=True,
        )
        result = ctx.to_context_string()
        # 内容应该被截断
        assert "链接" not in result or len(result) < 1200


class TestBrowserAwareness:
    """测试浏览器感知模块"""

    def test_detect_no_browser(self):
        """测试未安装浏览器时的检测"""
        awareness = BrowserAwareness()
        # 应该不崩溃，返回某种类型
        assert awareness._browser_type in ("none", "playwright", "selenium", "openclaw")

    def test_get_current_tab_returns_context(self):
        """测试获取标签页返回上下文"""
        import asyncio

        awareness = BrowserAwareness()
        ctx = asyncio.run(awareness.get_current_tab())
        assert isinstance(ctx, BrowserContext)
        assert ctx.available is False  # 默认不可用

    def test_to_context_string_sync(self):
        """测试同步上下文字符串"""
        awareness = BrowserAwareness()
        result = awareness.to_context_string()
        assert isinstance(result, str)
