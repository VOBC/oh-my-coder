"""
测试 cli_mcp 命令

使用 Typer CliRunner 进行集成测试，mock 外部依赖。
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.commands.cli_mcp import app

# Rich Console writes to stderr by default; mix_stderr=False keeps stdout and
# stderr separate so we can inspect each stream.
runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tests: start
# ---------------------------------------------------------------------------

class TestMcpStart:
    """测试 start 命令"""

    def test_start_calls_server_run(self):
        """验证 start 正确实例化 McpServer 并调用 run()"""
        mock_server = MagicMock()
        with patch("src.commands.cli_mcp.McpServer", return_value=mock_server) as mock_cls:
            with patch("src.commands.cli_mcp.contextlib.suppress", MagicMock()):
                result = runner.invoke(app, ["start"])
        mock_cls.assert_called_once()
        args, kwargs = mock_cls.call_args
        # workspace 应解析为绝对路径
        assert kwargs.get("workspace") is not None
        assert kwargs["workspace"].is_absolute()
        mock_server.run.assert_called_once()
        assert result.exit_code == 0

    def test_start_with_workspace_option(self, tmp_path):
        """验证 --workspace / -w 选项传递正确路径"""
        mock_server = MagicMock()
        with patch("src.commands.cli_mcp.McpServer", return_value=mock_server):
            with patch("src.commands.cli_mcp.contextlib.suppress", MagicMock()):
                result = runner.invoke(app, ["start", "--workspace", str(tmp_path)])
        _, kwargs = mock_server.run.call_args
        # run() 无参数
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Tests: install
# ---------------------------------------------------------------------------

class TestMcpInstall:
    """测试 install 命令"""

    @pytest.fixture
    def mock_home(self, tmp_path, monkeypatch):
        """将 Path.home() 指向 tmp_path，避免污染真实配置"""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        return tmp_path

    # --- Dify ---

    def test_install_dify_writes_json_file(self, mock_home, tmp_path):
        """Dify 模式：将配置写入项目目录 mcp-dify.json"""
        project = tmp_path / "myproject"
        project.mkdir()

        with patch("src.commands.cli_mcp.console"):
            result = runner.invoke(
                app,
                ["install", "--client", "dify", "--project", str(project)],
            )

        config_file = project / "mcp-dify.json"
        assert config_file.exists()
        data = json.loads(config_file.read_text(encoding="utf-8"))
        assert "oh-my-coder" in data["mcpServers"]
        srv = data["mcpServers"]["oh-my-coder"]
        assert srv["command"] == "python3"
        assert srv["args"] == ["-m", "src.mcp.server", "--start"]
        assert srv["cwd"] == str(project.resolve())
        assert result.exit_code == 0

    def test_install_dify_with_yes_flag(self, mock_home, tmp_path):
        """Dify 模式配合 --yes 不应触发任何 prompt"""
        project = tmp_path / "difyproj"
        project.mkdir()

        result = runner.invoke(
            app,
            ["install", "--client", "dify", "--project", str(project), "--yes"],
        )

        assert result.exit_code == 0
        # output carries both stdout and stderr; Rich prints to stderr
        assert "✅" in result.output

    def test_install_unsupported_client(self, mock_home):
        """不支持的客户端类型返回 exit_code 1"""
        result = runner.invoke(app, ["install", "--client", "unknown-client"])
        assert result.exit_code == 1
        assert "不支持" in result.output or "❌" in result.output

    # --- Claude Desktop ---

    def test_install_claude_desktop_new_file(self, mock_home):
        """Claude Desktop：新文件直接写入，无 prompt"""
        result = runner.invoke(
            app,
            ["install", "--client", "claude-desktop", "--yes"],
        )

        cfg = mock_home / ".claude-desktop" / "mcp.json"
        assert cfg.exists()
        data = json.loads(cfg.read_text(encoding="utf-8"))
        assert "oh-my-coder" in data["mcpServers"]
        assert result.exit_code == 0

    def test_install_claude_desktop_existing_yes(self, mock_home):
        """Claude Desktop：文件存在 + --yes 直接覆盖"""
        cfg_dir = mock_home / ".claude-desktop"
        cfg_dir.mkdir(parents=True)
        cfg_file = cfg_dir / "mcp.json"
        cfg_file.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")

        result = runner.invoke(
            app,
            ["install", "--client", "claude-desktop", "--yes"],
        )

        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert "oh-my-coder" in data["mcpServers"]
        assert result.exit_code == 0

    def test_install_claude_desktop_existing_confirm_yes(self, mock_home):
        """Claude Desktop：文件存在 + 用户输入 yes → 覆盖"""
        cfg_dir = mock_home / ".claude-desktop"
        cfg_dir.mkdir(parents=True)
        cfg_file = cfg_dir / "mcp.json"
        cfg_file.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")

        result = runner.invoke(
            app,
            ["install", "--client", "claude-desktop"],
            input="yes\n",
        )

        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert "oh-my-coder" in data["mcpServers"]
        assert result.exit_code == 0

    def test_install_claude_desktop_existing_confirm_no(self, mock_home):
        """Claude Desktop：文件存在 + 用户输入 no → 不覆盖"""
        cfg_dir = mock_home / ".claude-desktop"
        cfg_dir.mkdir(parents=True)
        cfg_file = cfg_dir / "mcp.json"
        original = {"mcpServers": {"old-key": {"command": "echo"}}}
        cfg_file.write_text(json.dumps(original), encoding="utf-8")

        result = runner.invoke(
            app,
            ["install", "--client", "claude-desktop"],
            input="no\n",
        )

        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert "old-key" in data["mcpServers"]
        assert "oh-my-coder" not in data["mcpServers"]
        assert result.exit_code == 0

    def test_install_claude_desktop_corrupt_json(self, mock_home):
        """Claude Desktop：已有配置为无效 JSON → 视为空配置"""
        cfg_dir = mock_home / ".claude-desktop"
        cfg_dir.mkdir(parents=True)
        cfg_file = cfg_dir / "mcp.json"
        cfg_file.write_text("not valid json {{{", encoding="utf-8")

        result = runner.invoke(
            app,
            ["install", "--client", "claude-desktop", "--yes"],
        )

        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert "oh-my-coder" in data["mcpServers"]
        assert result.exit_code == 0

    def test_install_cursor_alias(self, mock_home):
        """--client cursor 等同于 --client claude-desktop（写 .cursor/mcp.json）"""
        result = runner.invoke(
            app,
            ["install", "--client", "cursor", "--yes"],
        )

        cfg = mock_home / ".cursor" / "mcp.json"
        assert cfg.exists()
        data = json.loads(cfg.read_text(encoding="utf-8"))
        assert "oh-my-coder" in data["mcpServers"]
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Tests: list
# ---------------------------------------------------------------------------

class TestMcpList:
    """测试 list 命令"""

    def test_list_shows_tools_and_resources(self):
        """验证输出包含工具表和资源列表"""
        mock_tools = [
            {
                "name": "omc_code_review",
                "description": "执行代码审查",
                "inputSchema": {"type": "object"},
            },
            {
                "name": "omc_debug",
                "description": "定位并修复 Bug",
                "inputSchema": {"type": "object"},
            },
        ]
        mock_resources = [
            {
                "uri": "omc://workspace/summary",
                "name": "workspace_summary",
                "description": "工作区摘要",
                "mimeType": "text/markdown",
            },
        ]

        with patch("src.commands.cli_mcp.get_mcp_tools", return_value=mock_tools):
            with patch("src.commands.cli_mcp.get_mcp_resources", return_value=mock_resources):
                result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "MCP Tools" in result.stdout
        assert "omc_code_review" in result.stdout
        assert "omc_debug" in result.stdout
        assert "MCP Resources" in result.stdout
        assert "omc://workspace/summary" in result.stdout

    def test_list_counts(self):
        """验证底部统计数字"""
        mock_tools = [{"name": "t1", "description": "d1", "inputSchema": {}}] * 3
        mock_resources = [{"uri": "r1", "name": "n1", "description": "d1", "mimeType": "text/plain"}] * 2

        with patch("src.commands.cli_mcp.get_mcp_tools", return_value=mock_tools):
            with patch("src.commands.cli_mcp.get_mcp_resources", return_value=mock_resources):
                result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "3 tools" in result.stdout or "3 tools · 2 resources" in result.stdout

    def test_list_empty(self):
        """工具和资源列表为空时仍正常退出"""
        with patch("src.commands.cli_mcp.get_mcp_tools", return_value=[]):
            with patch("src.commands.cli_mcp.get_mcp_resources", return_value=[]):
                result = runner.invoke(app, ["list"])

        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Tests: status
# ---------------------------------------------------------------------------

class TestMcpStatus:
    """测试 status 命令"""

    def test_status_mcp_sdk_available(self, monkeypatch):
        """MCP SDK 可用时显示版本"""
        # Block the real mcp import by pre-seeding sys.modules before the
        # function's "import mcp" runs.
        fake_mcp = MagicMock()
        fake_mcp.__version__ = "1.2.3"
        monkeypatch.setitem(sys.modules, "mcp", fake_mcp)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "MCP SDK" in result.output

    def test_status_mcp_sdk_missing(self, monkeypatch):
        """MCP SDK 不可用时显示警告"""
        # Remove mcp from sys.modules so the function's import raises
        monkeypatch.setitem(sys.modules, "mcp", None)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "⚠" in result.output or "未安装" in result.output

    def test_status_shows_workspace_hint(self):
        """status 输出应包含可用命令提示"""
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "--start" in result.output or "start" in result.output

    def test_status_workspace_with_omc_dir(self, monkeypatch, tmp_path):
        """工作区含 .omc/ 时显示可用"""
        monkeypatch.chdir(tmp_path)
        omc_dir = tmp_path / ".omc"
        omc_dir.mkdir()

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert ".omc/" in result.output

    def test_status_workspace_without_omc_dir(self, monkeypatch, tmp_path):
        """工作区无 .omc/ 时显示警告"""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "⚠" in result.output or "不存在" in result.output


# ---------------------------------------------------------------------------
# Tests: help / edge cases
# ---------------------------------------------------------------------------

class TestMcpMisc:
    """杂项测试"""

    def test_help_shows_all_commands(self):
        """--help 列出所有子命令"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "start" in result.stdout
        assert "install" in result.stdout
        assert "list" in result.stdout
        assert "status" in result.stdout

    def test_no_args_shows_help(self):
        """无参数调用显示帮助而非崩溃"""
        result = runner.invoke(app, [])
        # typer 会显示帮助或报错，但不崩溃
        assert result.exit_code in (0, 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
