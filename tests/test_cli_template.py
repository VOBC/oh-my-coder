"""
Tests for src/commands/cli_template.py.
Covers list, show, use, create commands.
"""
from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from src.commands.cli_template import app

runner = CliRunner()


# ── list command ───────────────────────────────────────────────────────


class TestListTemplates:
    def test_list_all(self):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "flask-api" in result.stdout
        assert "code-review" in result.stdout
        assert "bug-fix" in result.stdout
        assert "enterprise" in result.stdout
        assert "multimodal" in result.stdout
        assert "omc template show" in result.stdout

    def test_list_filter_by_category(self):
        result = runner.invoke(app, ["list", "--category", "quality"])
        assert result.exit_code == 0
        assert "code-review" in result.stdout
        assert "flask-api" not in result.stdout

    def test_list_filter_no_match(self):
        result = runner.invoke(app, ["list", "--category", "nonexistent"])
        assert result.exit_code == 0
        # Table rendered but no rows
        assert result.stdout.strip() != ""


# ── show command ───────────────────────────────────────────────────────


class TestShowTemplate:
    def test_show_existing(self):
        """Show template when doc file doesn't exist — shows info panel."""
        with patch("src.commands.cli_template.Path.exists", return_value=False):
            result = runner.invoke(app, ["show", "code-review"])
        assert result.exit_code == 0
        assert "code-review" in result.stdout
        assert "代码审查" in result.stdout
        assert "quality" in result.stdout

    def test_show_not_found(self):
        result = runner.invoke(app, ["show", "nonexistent"])
        assert result.exit_code == 1
        assert "未找到模板" in result.stdout

    def test_show_with_doc_file(self):
        """When doc file exists, render it as Markdown."""
        with patch("src.commands.cli_template.Path.exists", return_value=True):
            with patch("src.commands.cli_template.Path.read_text",
                       return_value="# Code Review\nDetailed docs"):
                result = runner.invoke(app, ["show", "code-review"])
        assert result.exit_code == 0
        assert "Code Review" in result.stdout

    def test_show_raw_flag(self):
        """--raw flag skips doc file, shows basic info."""
        with patch("src.commands.cli_template.Path.exists", return_value=False):
            result = runner.invoke(app, ["show", "bug-fix", "--raw"])
        assert result.exit_code == 0
        assert "bug-fix" in result.stdout
        assert "Bug 修复" in result.stdout

    def test_show_enterprise_template(self):
        with patch("src.commands.cli_template.Path.exists", return_value=False):
            result = runner.invoke(app, ["show", "enterprise"])
        assert result.exit_code == 0
        assert "enterprise" in result.stdout


# ── use command ────────────────────────────────────────────────────────


class TestUseTemplate:
    def test_use_not_found(self):
        result = runner.invoke(app, ["use", "nonexistent"])
        assert result.exit_code == 1
        assert "未找到模板" in result.stdout

    def test_use_without_task(self):
        result = runner.invoke(app, ["use", "code-review"])
        assert result.exit_code == 0
        assert "启动工作流" in result.stdout
        assert "工作流已启动" in result.stdout

    def test_use_with_task(self):
        result = runner.invoke(app, ["use", "code-review", "--task", "review auth.py"])
        assert result.exit_code == 0
        assert "review auth.py" in result.stdout

    def test_use_dry_run(self):
        result = runner.invoke(app, ["use", "flask-api", "--dry-run"])
        assert result.exit_code == 0
        assert "将执行的命令" in result.stdout
        assert "omc run build" in result.stdout

    def test_use_dry_run_with_task(self):
        result = runner.invoke(
            app, ["use", "bug-fix", "--task", "null pointer", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "omc run debug" in result.stdout
        assert "null pointer" in result.stdout

    def test_use_with_project(self):
        result = runner.invoke(
            app, ["use", "code-review", "--project", "/tmp/myproject"]
        )
        assert result.exit_code == 0
        assert "工作流已启动" in result.stdout


# ── create command ─────────────────────────────────────────────────────


class TestCreateTemplate:
    def test_create_without_base(self):
        """Interactive creation (simulated input)."""
        input_str = "My Template\ncustom\ntest desc\nbuild\nexecutor,verifier\n"
        with patch("src.commands.cli_template.Path.mkdir"):
            with patch("src.commands.cli_template.Path.write_text"):
                result = runner.invoke(app, ["create", "my-tpl"], input=input_str)
        assert result.exit_code == 0
        assert "模板 'my-tpl' 已创建" in result.stdout

    def test_create_with_valid_base(self):
        input_str = "Based Template\ncustom\nbased desc\nreview\na,b\n"
        with patch("src.commands.cli_template.Path.mkdir"):
            with patch("src.commands.cli_template.Path.write_text"):
                result = runner.invoke(
                    app, ["create", "derived", "--base", "code-review"], input=input_str
                )
        assert result.exit_code == 0
        assert "模板 'derived' 已创建" in result.stdout

    def test_create_with_invalid_base(self):
        result = runner.invoke(app, ["create", "bad", "--base", "no-exist"])
        assert result.exit_code == 1
        assert "基础模板" in result.stdout
        assert "不存在" in result.stdout

    def test_create_enterprise_template(self):
        input_str = "Ent\nenterprise\nent desc\nbuild\na,b,c,d\n"
        with patch("src.commands.cli_template.Path.mkdir"):
            with patch("src.commands.cli_template.Path.write_text"):
                result = runner.invoke(
                    app, ["create", "ent-tpl", "--base", "enterprise"], input=input_str
                )
        assert result.exit_code == 0
        assert "模板 'ent-tpl' 已创建" in result.stdout
