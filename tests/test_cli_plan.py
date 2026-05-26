"""Tests for src/commands/cli_plan.py — Plan Mode commands."""

from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

# Must use 'from src.commands' so the module loads as part of the src package;
# otherwise cli_plan.py's relative imports (..agents.planner) fail.
from src.commands.cli_plan import (
    _check_env,
    _display_plan,
    _save_plan,
    app,
)

# ─────────────────────────────────────────────
# _check_env
# ─────────────────────────────────────────────

class TestCheckEnv:
    @patch("os.getenv", side_effect=lambda k: "sk-test" if k == "DEEPSEEK_API_KEY" else None)
    def test_has_deepseek_key(self, mock_env):
        assert _check_env() is True

    @patch("os.getenv", side_effect=lambda k: "sk-test" if k == "OPENAI_API_KEY" else None)
    def test_has_openai_key(self, mock_env):
        assert _check_env() is True

    @patch("os.getenv", side_effect=lambda k: "http://localhost:11434" if k == "OLLAMA_BASE_URL" else None)
    def test_has_ollama_url(self, mock_env):
        assert _check_env() is True

    @patch("os.getenv", return_value=None)
    def test_no_keys(self, mock_env, capsys):
        result = _check_env()
        assert result is False
        out = capsys.readouterr().out
        assert "API Key" in out or "❌" in out


# ─────────────────────────────────────────────
# _display_plan
# ─────────────────────────────────────────────

class TestDisplayPlan:
    @pytest.fixture
    def console(self):
        return Console(file=StringIO(), force_terminal=True)

    def test_empty_plan(self, console):
        """Empty plan dict — should print warning, not crash."""
        _display_plan({}, [], console)
        out = console.file.getvalue()
        assert "未生成有效计划" in out

    def test_plan_no_phases(self, console):
        """Plan with title/summary but no phases."""
        _display_plan({"title": "Empty", "summary": "Nothing"}, [], console)
        out = console.file.getvalue()
        assert "Empty" in out

    def test_with_phases(self, console):
        """Normal plan with one phase and one task."""
        plan_data = {
            "title": "Build Auth",
            "summary": "Add auth system",
            "phases": [
                {
                    "name": "Phase1",
                    "tasks": [
                        {
                            "id": "t1",
                            "title": "Add login API",
                            "files_to_modify": ["auth.py"],
                            "agent": "coder",
                        }
                    ],
                }
            ],
        }
        _display_plan(plan_data, ["t1"], console)
        out = console.file.getvalue()
        assert "Build Auth" in out
        assert "Add login API" in out

    def test_multiple_phases_and_tasks(self, console):
        """Plan with multiple phases and tasks."""
        plan_data = {
            "title": "Multi",
            "phases": [
                {
                    "name": "Phase1",
                    "tasks": [
                        {
                            "id": "t1",
                            "title": "Step one",
                            "files_to_modify": ["a.py", "b.py"],
                            "agent": "explorer",
                        },
                        {
                            "id": "t2",
                            "title": "Step two",
                            "files_to_modify": [],
                            "agent": "coder",
                        },
                    ],
                },
                {
                    "name": "Phase2",
                    "tasks": [
                        {
                            "id": "t3",
                            "title": "Step three",
                            "files_to_modify": ["c.py"],
                            "agent": "reviewer",
                        },
                    ],
                },
            ],
        }
        _display_plan(plan_data, ["t1", "t2", "t3"], console)
        out = console.file.getvalue()
        assert "Phase1" in out
        assert "Phase2" in out
        assert "a.py, b.py" in out

    def test_execution_order_short(self, console):
        """Short execution order — no ellipsis."""
        _display_plan({"title": "Short"}, ["t1", "t2"], console)
        out = console.file.getvalue()
        assert "t1" in out
        assert "t2" in out
        assert "..." not in out

    def test_execution_order_long(self, console):
        """Long execution order — should truncate with ellipsis."""
        order = [f"t{i}" for i in range(10)]
        _display_plan({"title": "Long"}, order, console)
        out = console.file.getvalue()
        assert "..." in out

    def test_empty_phase_tasks(self, console):
        """Phase with empty tasks list — should still print the phase."""
        plan_data = {
            "title": "Empty phase",
            "phases": [{"name": "Empty", "tasks": []}],
        }
        _display_plan(plan_data, [], console)
        out = console.file.getvalue()
        assert "Empty phase" in out


# ─────────────────────────────────────────────
# _save_plan
# ─────────────────────────────────────────────

class TestSavePlan:
    @pytest.fixture
    def console(self):
        return Console(file=StringIO(), force_terminal=True)

    def test_save_basic(self, tmp_path, console):
        """Basic save with summary and execution order."""
        output = tmp_path / "plan.md"
        plan_data = {"summary": "test summary", "phases": []}
        _save_plan(plan_data, ["a", "b"], output, console)
        content = output.read_text()
        assert "test summary" in content
        assert "a → b" in content

    def test_save_with_title(self, tmp_path, console):
        """Save includes JSON block with plan data."""
        output = tmp_path / "plan.md"
        plan_data = {
            "title": "Test Plan",
            "phases": [{"name": "P1", "tasks": []}],
        }
        _save_plan(plan_data, ["t1"], output, console)
        content = output.read_text()
        assert "# 执行计划" in content
        assert "Test Plan" in content

    def test_save_utf8_encoding(self, tmp_path, console):
        """Saved file contains UTF-8 content (Chinese)."""
        output = tmp_path / "plan.md"
        plan_data = {"summary": "中文测试", "phases": []}
        _save_plan(plan_data, [], output, console)
        content = output.read_text(encoding="utf-8")
        assert "中文测试" in content

    def test_save_empty_execution_order(self, tmp_path, console):
        """Save with no execution order."""
        output = tmp_path / "plan.md"
        plan_data = {"summary": "no order"}
        _save_plan(plan_data, [], output, console)
        content = output.read_text()
        assert "no order" in content


# ─────────────────────────────────────────────
# plan command — CliRunner integration
#
# The plan() function imports asyncio locally inside itself, so we can't
# patch 'asyncio' on the module.  Instead we mock PlannerAgent._run directly
# (asyncio.run calls it synchronously in our tests).
# ─────────────────────────────────────────────

def _mock_planner_agent():
    """Fully-configured mock PlannerAgent for CLI tests.

    _run is async, so we must use AsyncMock so asyncio.run() accepts it.
    """
    mock_agent = MagicMock()
    mock_output = MagicMock()
    mock_output.artifacts = {"plan": {}, "execution_order": []}
    mock_agent._run = AsyncMock(return_value="result")
    mock_agent._post_process.return_value = mock_output
    return mock_agent


class TestPlanCommand:
    @patch("src.commands.cli_plan._check_env", return_value=False)
    def test_env_check_fails(self, mock_check):
        """If _check_env returns False, command exits with code 1."""
        result = CliRunner().invoke(app, ["test task"])
        assert result.exit_code == 1

    @patch("src.commands.cli_plan._check_env", return_value=True)
    @patch("src.commands.cli_plan._init_router")
    def test_init_router_fails(self, mock_init, mock_check):
        """If _init_router raises SystemExit, command exits with code 1."""
        mock_init.side_effect = SystemExit(1)
        result = CliRunner().invoke(app, ["test task"])
        assert result.exit_code == 1

    @patch("src.commands.cli_plan._check_env", return_value=True)
    @patch("src.commands.cli_plan._init_router")
    @patch("src.commands.cli_plan.PlannerAgent")
    def test_planner_raises_exception(
        self, mock_agent_cls, mock_init, mock_check
    ):
        """If planner._run raises, command prints error and exits with code 1."""
        mock_agent = MagicMock()
        mock_agent._run.side_effect = ValueError("boom")
        # asyncio.run is imported locally inside plan(); patch it at the stdlib.
        mock_agent_cls.return_value = mock_agent

        result = CliRunner().invoke(app, ["test task"])
        assert result.exit_code == 1

    @patch("src.commands.cli_plan._check_env", return_value=True)
    @patch("src.commands.cli_plan._init_router")
    @patch("src.commands.cli_plan.PlannerAgent")
    def test_user_cancels(self, mock_agent_cls, mock_init, mock_check):
        """When user enters N, command exits 0 and prints cancel message."""
        mock_agent_cls.return_value = _mock_planner_agent()

        result = CliRunner().invoke(app, ["test task"], input="N\n")
        assert result.exit_code == 0
        assert "已取消" in result.output

    @patch("src.commands.cli_plan._check_env", return_value=True)
    @patch("src.commands.cli_plan._init_router")
    @patch("src.commands.cli_plan.PlannerAgent")
    def test_user_answers_yes(self, mock_agent_cls, mock_init, mock_check):
        """When user enters Y, command proceeds to execute phase."""
        mock_agent_cls.return_value = _mock_planner_agent()

        result = CliRunner().invoke(app, ["test task"], input="Y\n")
        assert result.exit_code == 0
        assert "执行" in result.output or "Plan Mode" in result.output

    @patch("src.commands.cli_plan._check_env", return_value=True)
    @patch("src.commands.cli_plan._init_router")
    @patch("src.commands.cli_plan.PlannerAgent")
    def test_yes_flag_skips_prompt(self, mock_agent_cls, mock_init, mock_check):
        """With --yes flag, skips confirmation and goes straight to execute."""
        mock_agent_cls.return_value = _mock_planner_agent()

        result = CliRunner().invoke(app, ["test task", "--yes"])
        assert result.exit_code == 0

    @patch("src.commands.cli_plan._check_env", return_value=True)
    @patch("src.commands.cli_plan._init_router")
    @patch("src.commands.cli_plan.PlannerAgent")
    @patch("src.commands.cli_plan._save_plan")
    def test_output_option(
        self, mock_save, mock_agent_cls, mock_init, mock_check, tmp_path
    ):
        """With --output / -o flag, _save_plan is called."""
        mock_agent_cls.return_value = _mock_planner_agent()

        out_file = tmp_path / "plan.md"
        result = CliRunner().invoke(app, ["test task", "-y", "-o", str(out_file)])
        assert result.exit_code == 0
        mock_save.assert_called_once()

    @patch("src.commands.cli_plan._check_env", return_value=True)
    @patch("src.commands.cli_plan._init_router")
    @patch("src.commands.cli_plan.PlannerAgent")
    def test_model_option(self, mock_agent_cls, mock_init, mock_check):
        """--model / -m flag is accepted; planner gets model_router kwarg."""
        mock_agent_cls.return_value = _mock_planner_agent()

        result = CliRunner().invoke(app, ["test task", "-y", "--model", "gpt-4"])
        assert result.exit_code == 0
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        assert "model_router" in call_kwargs

    @patch("src.commands.cli_plan._check_env", return_value=True)
    @patch("src.commands.cli_plan._init_router")
    @patch("src.commands.cli_plan.PlannerAgent")
    def test_project_path_option(
        self, mock_agent_cls, mock_init, mock_check, tmp_path
    ):
        """--project / -p option is accepted without error."""
        mock_agent_cls.return_value = _mock_planner_agent()

        project = tmp_path / "myproject"
        project.mkdir()
        result = CliRunner().invoke(
            app, ["test task", "-y", "--project", str(project)]
        )
        assert result.exit_code == 0
