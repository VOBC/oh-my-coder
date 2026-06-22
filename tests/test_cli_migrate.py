"""
Tests for src/commands/cli_migrate.py.
Covers list, claude, gemini commands and _parse_claude_config.
"""
from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from src.commands.cli_migrate import app

runner = CliRunner()


# ── list command ───────────────────────────────────────────────────────


class TestListSources:
    def test_list_renders_table(self):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Claude Code" in result.stdout
        assert "Gemini CLI" in result.stdout
        assert "CLAUDE.md" in result.stdout
        assert ".clinerules" in result.stdout

    def test_list_has_usage_hint(self):
        result = runner.invoke(app, ["list"])
        assert "omc migrate claude" in result.stdout
        assert "omc migrate gemini" in result.stdout


# ── claude command ─────────────────────────────────────────────────────


class TestMigrateClaude:
    def test_missing_claude_md(self, tmp_path):
        result = runner.invoke(app, ["claude", str(tmp_path)])
        assert result.exit_code == 1
        assert "未找到 CLAUDE.md" in result.stdout

    def test_dry_run(self, tmp_path):
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("## Agent: test-bot\n## Commands\n- build\n- test\n")

        result = runner.invoke(app, ["claude", str(tmp_path), "--dry-run"])
        assert result.exit_code == 0
        assert "导入内容预览" in result.stdout
        assert "test-bot" in result.stdout
        assert "build" in result.stdout
        assert "字符" in result.stdout

    def test_dry_run_short_flag(self, tmp_path):
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("hello")

        result = runner.invoke(app, ["claude", str(tmp_path), "-n"])
        assert result.exit_code == 0
        assert "导入内容预览" in result.stdout

    def test_dry_run_truncates_long_content(self, tmp_path):
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("x" * 600)

        result = runner.invoke(app, ["claude", str(tmp_path), "--dry-run"])
        assert result.exit_code == 0
        assert "..." in result.stdout
        assert str(600) in result.stdout

    def test_normal_import(self, tmp_path):
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# My Config\n## Agent: my-agent\n")

        with patch("src.commands.cli_migrate._parse_claude_config") as mock_parse:
            mock_parse.return_value = {"agent": "my-agent"}
            result = runner.invoke(app, ["claude", str(tmp_path)])

        assert result.exit_code == 0
        assert "配置已导入到" in result.stdout
        mock_parse.assert_called_once()

    def test_default_path_is_cwd(self):
        result = runner.invoke(app, ["claude"])
        assert result.exit_code == 1  # No CLAUDE.md in cwd
        assert "未找到 CLAUDE.md" in result.stdout


# ── gemini command ─────────────────────────────────────────────────────


class TestMigrateGemini:
    def test_neither_file_exists(self, tmp_path):
        result = runner.invoke(app, ["gemini", str(tmp_path)])
        assert result.exit_code == 1
        assert "未找到 .clinerules" in result.stdout

    def test_clinerules_exists(self, tmp_path):
        cr = tmp_path / ".clinerules"
        cr.write_text("# rules here\n")

        with patch("src.commands.cli_migrate.Path.mkdir"):
            with patch("src.commands.cli_migrate.Path.write_text"):
                result = runner.invoke(app, ["gemini", str(tmp_path)])

        assert result.exit_code == 0
        assert "配置已导入到" in result.stdout

    def test_clinerules_json_exists(self, tmp_path):
        crj = tmp_path / ".clinerules.json"
        crj.write_text('{"rules": []}\n')

        with patch("src.commands.cli_migrate.Path.mkdir"):
            with patch("src.commands.cli_migrate.Path.write_text"):
                result = runner.invoke(app, ["gemini", str(tmp_path)])

        assert result.exit_code == 0
        assert "配置已导入到" in result.stdout
        assert ".clinerules.json" in result.stdout

    def test_clinerules_priority_over_json(self, tmp_path):
        cr = tmp_path / ".clinerules"
        cr.write_text("# plain rules\n")
        crj = tmp_path / ".clinerules.json"
        crj.write_text('{"rules": []}\n')

        with patch("src.commands.cli_migrate.Path.mkdir"):
            with patch("src.commands.cli_migrate.Path.write_text"):
                result = runner.invoke(app, ["gemini", str(tmp_path)])

        assert result.exit_code == 0
        # .clinerules takes priority
        assert ".clinerules" in result.stdout

    def test_dry_run_clinerules(self, tmp_path):
        cr = tmp_path / ".clinerules"
        cr.write_text("# gemini rules\n" * 10)

        result = runner.invoke(app, ["gemini", str(tmp_path), "--dry-run"])
        assert result.exit_code == 0
        assert "导入内容预览" in result.stdout
        assert "gemini rules" in result.stdout

    def test_dry_run_short_flag(self, tmp_path):
        cr = tmp_path / ".clinerules"
        cr.write_text("hello world")

        result = runner.invoke(app, ["gemini", str(tmp_path), "-n"])
        assert result.exit_code == 0
        assert "导入内容预览" in result.stdout

    def test_dry_run_truncates_long_content(self, tmp_path):
        cr = tmp_path / ".clinerules"
        cr.write_text("y" * 600)

        result = runner.invoke(app, ["gemini", str(tmp_path), "--dry-run"])
        assert result.exit_code == 0
        assert "..." in result.stdout
        assert str(600) in result.stdout

    def test_default_path_no_file(self):
        result = runner.invoke(app, ["gemini"])
        assert result.exit_code == 1
        assert "未找到 .clinerules" in result.stdout


# ── _parse_claude_config ───────────────────────────────────────────────


class TestParseClaudeConfig:
    def test_empty_content(self):
        from src.commands.cli_migrate import _parse_claude_config
        result = _parse_claude_config("")
        assert result["working_directory"] is None
        assert result["agent"] is None
        assert result["commands"] == []

    def test_parse_working_directory(self):
        from src.commands.cli_migrate import _parse_claude_config
        result = _parse_claude_config("## Working Directory: /home/project\n")
        assert result["working_directory"] == "/home/project"

    def test_parse_agent(self):
        from src.commands.cli_migrate import _parse_claude_config
        result = _parse_claude_config("## Agent: code-reviewer\n")
        assert result["agent"] == "code-reviewer"

    def test_parse_commands(self):
        from src.commands.cli_migrate import _parse_claude_config
        content = "## Commands\n- build\n- test\n- deploy\n"
        result = _parse_claude_config(content)
        assert result["commands"] == ["build", "test", "deploy"]

    def test_parse_commands_continues_after_text(self):
        from src.commands.cli_migrate import _parse_claude_config
        content = "## Commands\n- build\nSome text\n- also_matched\n"
        result = _parse_claude_config(content)
        # Once in_commands=True, it matches all list items regardless of non-list lines
        assert result["commands"] == ["build", "also_matched"]

    def test_parse_full_config(self):
        from src.commands.cli_migrate import _parse_claude_config
        content = (
            "## Working Directory: /src\n"
            "## Agent: bot\n"
            "## Commands\n"
            "- lint\n"
            "- format\n"
        )
        result = _parse_claude_config(content)
        assert result["working_directory"] == "/src"
        assert result["agent"] == "bot"
        assert result["commands"] == ["lint", "format"]

    def test_parse_with_extra_content(self):
        from src.commands.cli_migrate import _parse_claude_config
        content = (
            "# My Config\n\n"
            "## Working Directory: /app\n\n"
            "Some description here\n\n"
            "## Commands\n"
            "- build\n"
        )
        result = _parse_claude_config(content)
        assert result["working_directory"] == "/app"
        assert result["commands"] == ["build"]
