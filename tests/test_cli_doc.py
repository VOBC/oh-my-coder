"""测试 cli_doc.py — 文档生成与管理命令"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.commands.cli_doc import (
    _collect_cli_commands,
    _collect_web_api,
    _write_json_docs,
    _write_markdown_docs,
    app,
)

runner = CliRunner()


# ===== generate 命令 =====


class TestGenerateDocs:
    def test_generate_markdown_default(self, tmp_path):
        """默认参数生成 markdown 文档"""
        with patch("src.commands.cli_doc._collect_cli_commands", return_value=[
            {"name": "init", "file": "cli_init.py", "help": "初始化项目"}
        ]), \
        patch("src.commands.cli_doc._collect_web_api", return_value=[
            {"method": "GET", "path": "/api/status"}
        ]), \
        patch("src.commands.cli_doc.DOCS_DIR", tmp_path / "docs"):
            result = runner.invoke(app, ["generate"])
        assert result.exit_code == 0
        assert "✅" in result.output

    def test_generate_json_format(self, tmp_path):
        """json 格式生成文档"""
        with patch("src.commands.cli_doc._collect_cli_commands", return_value=[]), \
        patch("src.commands.cli_doc._collect_web_api", return_value=[]), \
        patch("src.commands.cli_doc.DOCS_DIR", tmp_path / "docs"):
            result = runner.invoke(app, ["generate", "-f", "json"])
        assert result.exit_code == 0

    def test_generate_custom_output(self, tmp_path):
        """自定义输出目录"""
        output = tmp_path / "custom_out"
        with patch("src.commands.cli_doc._collect_cli_commands", return_value=[]), \
        patch("src.commands.cli_doc._collect_web_api", return_value=[]):
            result = runner.invoke(app, ["generate", "-o", str(output)])
        assert result.exit_code == 0
        assert output.exists()


# ===== check 命令 =====


class TestCheckDocs:
    def test_check_with_missing_readme(self, tmp_path):
        """README 不存在时报错"""
        with patch("src.commands.cli_doc.README_PATH", tmp_path / "missing.md"), \
        patch("src.commands.cli_doc.DOCS_DIR", tmp_path / "docs"), \
        patch("src.commands.cli_doc._collect_cli_commands", return_value=[]):
            result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "README" in result.output

    def test_check_missing_dirs(self, tmp_path):
        """docs 子目录缺失时报告"""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        with patch("src.commands.cli_doc.README_PATH", tmp_path / "README.md"), \
        patch("src.commands.cli_doc.DOCS_DIR", docs_dir), \
        patch("src.commands.cli_doc._collect_cli_commands", return_value=[
            {"name": "build", "file": "cli_build.py", "help": "构建"}
        ]):
            result = runner.invoke(app, ["check"])
        assert "缺失" in result.output or "缺少" in result.output

    def test_check_all_good(self, tmp_path):
        """所有文档齐全时通过"""
        docs_dir = tmp_path / "docs"
        for d in ["guide", "api", "features", "agents"]:
            (docs_dir / d).mkdir(parents=True)
        (docs_dir / "api" / "build.md").write_text("ok")
        (tmp_path / "README.md").write_text("ok")

        with patch("src.commands.cli_doc.README_PATH", tmp_path / "README.md"), \
        patch("src.commands.cli_doc.DOCS_DIR", docs_dir), \
        patch("src.commands.cli_doc._collect_cli_commands", return_value=[
            {"name": "build", "file": "cli_build.py", "help": "构建"}
        ]):
            result = runner.invoke(app, ["check"])
        assert "良好" in result.output

    def test_check_truncates_long_issues(self, tmp_path):
        """超过 10 个问题时有截断提示"""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # 生成 11+ 个缺失命令
        cmds = [{"name": f"cmd{i}", "file": f"cli_cmd{i}.py", "help": f"命令{i}"} for i in range(11)]

        with patch("src.commands.cli_doc.README_PATH", tmp_path / "README.md"), \
        patch("src.commands.cli_doc.DOCS_DIR", docs_dir), \
        patch("src.commands.cli_doc._collect_cli_commands", return_value=cmds):
            result = runner.invoke(app, ["check"])
        assert "还有" in result.output


# ===== serve 命令 =====


class TestServeDocs:
    def test_serve_nonexistent_dir(self, tmp_path):
        """docs 目录不存在时报错退出"""
        with patch("src.commands.cli_doc.DOCS_DIR", tmp_path / "no_docs"):
            result = runner.invoke(app, ["serve"])
        assert result.exit_code == 1
        assert "不存在" in result.output

    def test_serve_keyboard_interrupt(self, tmp_path):
        """KeyboardInterrupt 优雅退出"""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        mock_httpd = MagicMock()
        mock_httpd.__enter__ = MagicMock(return_value=mock_httpd)
        mock_httpd.__exit__ = MagicMock(return_value=False)
        mock_httpd.serve_forever = MagicMock(side_effect=KeyboardInterrupt)

        with patch("src.commands.cli_doc.DOCS_DIR", docs_dir), \
        patch("socketserver.TCPServer", return_value=mock_httpd):
            result = runner.invoke(app, ["serve"])
        assert "停止" in result.output


# ===== index 命令 =====


class TestGenerateIndex:
    def test_index_empty_dir(self, tmp_path):
        """空 docs 目录"""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        with patch("src.commands.cli_doc.DOCS_DIR", docs_dir):
            result = runner.invoke(app, ["index"])
        assert result.exit_code == 0
        assert "文档结构" in result.output

    def test_index_with_files(self, tmp_path):
        """有文件和子目录"""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "intro.md").write_text("# Intro")
        sub = docs_dir / "guide"
        sub.mkdir()
        (sub / "start.md").write_text("# Start")
        # 隐藏文件应被跳过
        (docs_dir / ".hidden.md").write_text("hidden")

        with patch("src.commands.cli_doc.DOCS_DIR", docs_dir):
            result = runner.invoke(app, ["index"])
        assert "intro.md" in result.output
        assert "start.md" in result.output
        assert ".hidden" not in result.output


# ===== 内部函数 =====


class TestCollectCliCommands:
    def test_collect_from_directory(self, tmp_path):
        """从 cli_*.py 文件收集命令"""
        # 创建模拟 cli 文件
        (tmp_path / "cli_init.py").write_text('"""初始化项目"""\n')
        (tmp_path / "cli_build.py").write_text('"""构建项目"""\n')
        (tmp_path / "cli_doc.py").write_text('"""文档命令"""\n')  # 应被跳过

        with patch.object(Path, "glob") as mock_glob:
            mock_glob.return_value = [
                tmp_path / "cli_init.py",
                tmp_path / "cli_build.py",
                tmp_path / "cli_doc.py",
            ]
            result = _collect_cli_commands()
            names = [c["name"] for c in result]
            assert "doc" not in names
            assert "init" in names
            assert "build" in names

    def test_collect_empty(self):
        """无 cli 文件时返回空列表"""
        with patch.object(Path, "glob", return_value=[]):
            assert _collect_cli_commands() == []

    def test_collect_no_docstring(self, tmp_path):
        """无 docstring 时使用默认 help"""
        (tmp_path / "cli_test.py").write_text("pass\n")
        with patch.object(Path, "glob", return_value=[tmp_path / "cli_test.py"]):
            result = _collect_cli_commands()
            assert result[0]["help"] == "test 命令"


class TestCollectWebApi:
    def test_collect_from_app(self, tmp_path):
        """从 web/app.py 收集 API 端点"""
        app_file = tmp_path / "app.py"
        app_file.write_text('''
@app.get("/api/status")
@app.post("/api/run")
@app.put("/api/config")
@app.delete("/api/task")
''')

        with patch("src.commands.cli_doc.Path") as MockPath:
            mock_p = MockPath.return_value
            mock_p.exists.return_value = True
            mock_p.read_text.return_value = app_file.read_text()
            result = _collect_web_api()
            assert len(result) == 4
            assert result[0]["method"] == "GET"
            assert result[0]["path"] == "/api/status"

    def test_collect_no_app_file(self):
        """web/app.py 不存在时返回空列表"""
        with patch("src.commands.cli_doc.Path") as MockPath:
            MockPath.return_value.exists.return_value = False
            assert _collect_web_api() == []


class TestWriteMarkdownDocs:
    def test_write_markdown(self, tmp_path):
        """写入 markdown 文件"""
        cli_info = [{"name": "init", "file": "cli_init.py", "help": "初始化"}]
        api_info = [{"method": "GET", "path": "/api/status"}]

        _write_markdown_docs(tmp_path, cli_info, api_info)
        cli_md = tmp_path / "cli-commands.md"
        api_md = tmp_path / "web-api.md"
        assert cli_md.exists()
        assert api_md.exists()
        assert "init" in cli_md.read_text()
        assert "GET" in api_md.read_text()


class TestWriteJsonDocs:
    def test_write_json(self, tmp_path):
        """写入 json 文件"""
        cli_info = [{"name": "init", "file": "cli_init.py", "help": "初始化"}]
        api_info = [{"method": "GET", "path": "/api/status"}]

        _write_json_docs(tmp_path, cli_info, api_info)
        json_path = tmp_path / "api-reference.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert "cli_commands" in data
        assert "web_api" in data
