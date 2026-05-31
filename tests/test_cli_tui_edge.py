"""
Edge case tests for cli_tui.py to improve coverage from 80% to 95%+

Targets missing lines: 301, 306-357, 361-371, 375, 457, 479-524
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.commands.cli_tui import (
    TUISession, State, Keys, WORKFLOWS, MODELS, AGENT_CATEGORIES
)


class TestSlashCommandHandling:
    """Test _handle_slash_command method (lines 301, 306-357)"""

    @patch("src.commands.cli_tui.subprocess.run")
    @patch("src.commands.cli_tui.Path")
    @patch.object(TUISession, "_wait_key")
    def test_slash_command_success(self, mock_wait, mock_path, mock_run):
        """Test successful slash command execution"""
        session = TUISession()
        mock_run.return_value = Mock(
            stdout="Skill executed successfully",
            stderr=""
        )

        # Mock file exists
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.read_text.return_value = "print('hello')"
        mock_path.return_value = mock_file

        result = session._handle_slash_command("/test-skill /path/to/file.py")

        assert result is True
        mock_run.assert_called_once()

    @patch("src.commands.cli_tui.subprocess.run")
    @patch.object(TUISession, "_wait_key")
    def test_slash_command_no_file(self, mock_wait, mock_run):
        """Test slash command without file path (uses workspace code)"""
        session = TUISession()
        mock_run.return_value = Mock(stdout="OK", stderr="")

        with patch.object(session, "_collect_workspace_code", return_value="code here"):
            result = session._handle_slash_command("/test-skill")

        assert result is True
        mock_run.assert_called_once()

    @patch.object(TUISession, "_wait_key")
    def test_slash_command_file_not_found(self, mock_wait):
        """Test slash command with non-existent file"""
        session = TUISession()

        result = session._handle_slash_command("/test-skill /nonexistent/file.py")

        assert result is True

    @patch("src.commands.cli_tui.subprocess.run")
    @patch.object(TUISession, "_wait_key")
    def test_slash_command_timeout(self, mock_wait, mock_run):
        """Test slash command that times out"""
        session = TUISession()
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="omc", timeout=30)

        result = session._handle_slash_command("/test-skill")

        assert result is True

    @patch("src.commands.cli_tui.subprocess.run")
    @patch.object(TUISession, "_wait_key")
    def test_slash_command_exception(self, mock_wait, mock_run):
        """Test slash command that raises exception"""
        session = TUISession()
        mock_run.side_effect = Exception("Skill failed")

        result = session._handle_slash_command("/test-skill")

        assert result is True

    @patch("src.commands.cli_tui.subprocess.run")
    @patch.object(TUISession, "_wait_key")
    def test_slash_command_with_stderr(self, mock_wait, mock_run):
        """Test slash command that produces stderr output"""
        session = TUISession()
        mock_run.return_value = Mock(
            stdout="",
            stderr="Some error occurred"
        )

        result = session._handle_slash_command("/test-skill")

        assert result is True
        mock_run.assert_called_once()

    def test_slash_command_not_a_command(self):
        """Test input that doesn't start with /"""
        session = TUISession()

        result = session._handle_slash_command("not-a-command")

        assert result is False

    @patch("src.commands.cli_tui.subprocess.run")
    @patch.object(TUISession, "_wait_key")
    def test_slash_command_empty_input(self, mock_wait, mock_run):
        """Test empty slash command"""
        session = TUISession()
        mock_run.return_value = Mock(stdout="", stderr="")

        result = session._handle_slash_command("/")

        assert result is True
        # Should try to run skill with empty name


class TestCollectWorkspaceCode:
    """Test _collect_workspace_code method"""

    @patch("src.commands.cli_tui.Path")
    def test_collect_workspace_code_success(self, mock_path):
        """Test successful workspace code collection"""
        session = TUISession()

        # Mock Path.cwd() and rglob
        mock_cwd = Mock()
        mock_file1 = Mock()
        mock_file1.relative_to.return_value = Path("test1.py")
        mock_file1.read_text.return_value = "\n".join([f"line{i}" for i in range(100)])

        mock_file2 = Mock()
        mock_file2.relative_to.return_value = Path("test2.py")
        mock_file2.read_text.return_value = "\n".join([f"code{i}" for i in range(100)])

        mock_cwd.rglob.return_value = [mock_file1, mock_file2]
        mock_path.cwd.return_value = mock_cwd

        result = session._collect_workspace_code()

        assert "test1.py" in result
        assert "test2.py" in result

    @patch("src.commands.cli_tui.Path")
    def test_collect_workspace_code_exception(self, mock_path):
        """Test workspace code collection with file read exception"""
        session = TUISession()

        mock_cwd = Mock()
        mock_file = Mock()
        mock_file.relative_to.return_value = Path("test.py")
        mock_file.read_text.side_effect = Exception("Cannot read file")

        mock_cwd.rglob.return_value = [mock_file]
        mock_path.cwd.return_value = mock_cwd

        result = session._collect_workspace_code()

        assert result == ""  # Should return empty string on exception


class TestWaitKey:
    """Test _wait_key method (line 361)"""

    @patch("src.commands.cli_tui.console")
    def test_wait_key(self, mock_console):
        """Test _wait_key method"""
        session = TUISession()
        mock_console.input.return_value = "x"

        session._wait_key()

        mock_console.input.assert_called_once()


class TestHandleMain:
    """Test _handle_main method (lines 363-375)"""

    def test_handle_main_up_key(self):
        """Test Up key in main menu"""
        session = TUISession()
        session.cursor = 2

        result = session._handle_main(Keys.Up)

        assert result is True
        assert session.cursor == 1

    def test_handle_main_down_key(self):
        """Test Down key in main menu"""
        session = TUISession()
        session.cursor = 0

        result = session._handle_main(Keys.Down)

        assert result is True
        assert session.cursor == 1

    def test_handle_main_numeric_key(self):
        """Test numeric key selection in main menu"""
        session = TUISession()

        result = session._handle_main("1")

        assert result is True
        assert session.cursor == 0
        assert session.selected_workflow == WORKFLOWS[0][0]
        assert session.state == State.TASK

    def test_handle_main_numeric_key_out_of_range(self):
        """Test numeric key that's out of range"""
        session = TUISession()

        result = session._handle_main("9")  # Only 7 workflows

        assert result is True
        # Cursor should not change if out of range (no check in code?)

    def test_handle_main_enter_key(self):
        """Test Enter key in main menu"""
        session = TUISession()
        session.cursor = 2

        result = session._handle_main("\n")

        assert result is True
        assert session.selected_workflow == WORKFLOWS[2][0]
        assert session.state == State.TASK

    def test_handle_main_m_key(self):
        """Test 'm' key to switch to model selection"""
        session = TUISession()

        result = session._handle_main("m")

        assert result is True
        assert session.state == State.MODEL
        assert session.cursor == 0

    def test_handle_main_a_key(self):
        """Test 'a' key to switch to agents view"""
        session = TUISession()

        result = session._handle_main("a")

        assert result is True
        assert session.state == State.AGENTS


class TestExecuteTask:
    """Test _execute_task method (line 457)"""

    @patch("src.commands.cli_tui.console")
    def test_execute_task(self, mock_console):
        """Test task execution"""
        session = TUISession()
        session.task_input = "test task"
        session.selected_workflow = "chat"
        session.selected_model = "gpt-4"

        session._execute_task()

        # Should print task info
        assert mock_console.print.called


class TestCLICmds:
    """Test CLI commands (lines 479-524): list_agents, list_workflows, list_models"""

    @patch("src.commands.cli_tui.console")
    def test_list_agents(self, mock_console):
        """Test list_agents command"""
        from src.commands.cli_tui import list_agents

        list_agents()

        # Should print table with agents
        assert mock_console.print.called

    @patch("src.commands.cli_tui.console")
    def test_list_workflows(self, mock_console):
        """Test list_workflows command"""
        from src.commands.cli_tui import list_workflows

        list_workflows()

        # Should print table with workflows
        assert mock_console.print.called

    @patch("src.commands.cli_tui.console")
    def test_list_models(self, mock_console):
        """Test list_models command"""
        from src.commands.cli_tui import list_models

        list_models()

        # Should print table with models
        assert mock_console.print.called


class TestStartFunction:
    """Test start function with various arguments"""

    @patch("src.commands.cli_tui.TUISession")
    @patch("src.commands.cli_tui.Live")
    @patch("src.commands.cli_tui.console")
    def test_start_with_task(self, mock_console, mock_live, mock_session):
        """Test start function with task argument"""
        from src.commands.cli_tui import start

        mock_session_instance = Mock()
        mock_session_instance.render.return_value = "rendered"
        mock_session.return_value = mock_session_instance

        start(task="test task", workflow=None, model=None)

        assert mock_session_instance.task_input == "test task"
        assert mock_session_instance.state == State.CONFIRM

    @patch("src.commands.cli_tui.TUISession")
    @patch("src.commands.cli_tui.Live")
    @patch("src.commands.cli_tui.console")
    def test_start_with_workflow(self, mock_console, mock_live, mock_session):
        """Test start function with workflow argument"""
        from src.commands.cli_tui import start

        mock_session_instance = Mock()
        mock_session_instance.render.return_value = "rendered"
        mock_session.return_value = mock_session_instance

        start(task=None, workflow="code-review", model=None)

        assert mock_session_instance.selected_workflow == "code-review"
        assert mock_session_instance.state == State.TASK

    @patch("src.commands.cli_tui.TUISession")
    @patch("src.commands.cli_tui.Live")
    @patch("src.commands.cli_tui.console")
    def test_start_with_model(self, mock_console, mock_live, mock_session):
        """Test start function with model argument"""
        from src.commands.cli_tui import start

        mock_session_instance = Mock()
        mock_session_instance.render.return_value = "rendered"
        mock_session.return_value = mock_session_instance

        start(task=None, workflow=None, model="gpt-4")

        assert mock_session_instance.selected_model == "gpt-4"

    @patch("src.commands.cli_tui.console")
    @patch("src.commands.cli_tui.Live")
    @patch("src.commands.cli_tui.TUISession")
    def test_start_interactive(self, mock_session, mock_live, mock_console):
        """Test start function in interactive mode"""
        from src.commands.cli_tui import start

        mock_session_instance = Mock()
        mock_session_instance.handle_key.return_value = False  # Exit immediately
        mock_session.return_value = mock_session_instance
        mock_console.input.return_value = "q"

        # Should not raise
        start(task=None, workflow=None, model=None)


class TestHandleWorkflow:
    """Test _handle_workflow method"""

    def test_handle_workflow_up(self):
        """Test Up key in workflow selection"""
        session = TUISession()
        session.cursor = 1
        session.state = State.WORKFLOW

        result = session._handle_workflow(Keys.Up)

        assert result is True
        assert session.cursor == 0

    def test_handle_workflow_down(self):
        """Test Down key in workflow selection"""
        session = TUISession()
        session.cursor = 0
        session.state = State.WORKFLOW

        result = session._handle_workflow(Keys.Down)

        assert result is True
        assert session.cursor == 1

    def test_handle_workflow_enter(self):
        """Test Enter key in workflow selection"""
        session = TUISession()
        session.cursor = 1
        session.state = State.WORKFLOW

        result = session._handle_workflow("\n")

        assert result is True
        assert session.selected_workflow == WORKFLOWS[1][0]
        assert session.state == State.TASK

    def test_handle_workflow_escape(self):
        """Test Escape key in workflow selection"""
        session = TUISession()
        session.state = State.WORKFLOW

        result = session._handle_workflow("escape")

        assert result is True
        assert session.state == State.MAIN
        assert session.cursor == 0


class TestHandleModel:
    """Test _handle_model method"""

    def test_handle_model_up(self):
        """Test Up key in model selection"""
        session = TUISession()
        session.cursor = 1
        session.state = State.MODEL

        result = session._handle_model(Keys.Up)

        assert result is True
        assert session.cursor == 0

    def test_handle_model_down(self):
        """Test Down key in model selection"""
        session = TUISession()
        session.cursor = 0
        session.state = State.MODEL

        result = session._handle_model(Keys.Down)

        assert result is True
        assert session.cursor == 1

    def test_handle_model_enter(self):
        """Test Enter key in model selection"""
        session = TUISession()
        session.cursor = 1
        session.state = State.MODEL

        result = session._handle_model("\n")

        assert result is True
        assert session.selected_model == MODELS[1][0]
        assert session.state == State.MAIN

    def test_handle_model_escape(self):
        """Test Escape key in model selection"""
        session = TUISession()
        session.state = State.MODEL

        result = session._handle_model("escape")

        assert result is True
        assert session.state == State.MAIN


class TestHandleAgents:
    """Test _handle_agents method"""

    def test_handle_agents_escape(self):
        """Test Escape key in agents view"""
        session = TUISession()
        session.state = State.AGENTS

        result = session._handle_agents("escape")

        assert result is True
        assert session.state == State.MAIN

    def test_handle_agents_ctrl_c(self):
        """Test Ctrl+C in agents view"""
        session = TUISession()
        session.state = State.AGENTS

        result = session._handle_agents("ctrl+c")

        assert result is True
        assert session.state == State.MAIN

    def test_handle_agents_q(self):
        """Test 'q' key in agents view"""
        session = TUISession()
        session.state = State.AGENTS

        result = session._handle_agents("q")

        assert result is True
        assert session.state == State.MAIN


class TestHandleTask:
    """Test _handle_task method"""

    def test_handle_task_escape(self):
        """Test Escape key in task input"""
        session = TUISession()
        session.state = State.TASK

        result = session._handle_task("escape")

        assert result is True
        assert session.state == State.MAIN

    def test_handle_task_ctrl_c(self):
        """Test Ctrl+C in task input"""
        session = TUISession()
        session.state = State.TASK

        result = session._handle_task("ctrl+c")

        assert result is True
        assert session.state == State.MAIN

    def test_handle_task_enter_with_input(self):
        """Test Enter key with task input"""
        session = TUISession()
        session.state = State.TASK
        session.task_input = "test task"

        result = session._handle_task("\n")

        assert result is True
        assert session.state == State.CONFIRM

    def test_handle_task_enter_with_slash_command(self):
        """Test Enter key with slash command"""
        session = TUISession()
        session.state = State.TASK
        session.task_input = "/test-skill"

        with patch.object(session, "_handle_slash_command", return_value=True):
            result = session._handle_task("\n")

        assert result is True
        assert session.task_input == ""
        assert session.state == State.MAIN

    def test_handle_task_backspace(self):
        """Test Backspace in task input"""
        session = TUISession()
        session.state = State.TASK
        session.task_input = "test"

        result = session._handle_task("backspace")

        assert result is True
        assert session.task_input == "tes"

    def test_handle_task_character_input(self):
        """Test character input in task input"""
        session = TUISession()
        session.state = State.TASK
        session.task_input = "tes"

        result = session._handle_task("t")

        assert result is True
        assert session.task_input == "test"


class TestHandleConfirm:
    """Test _handle_confirm method"""

    def test_handle_confirm_yes(self):
        """Test 'y' key in confirm"""
        session = TUISession()
        session.state = State.CONFIRM

        with patch.object(session, "_execute_task"):
            result = session._handle_confirm("y")

        assert result is False  # Exit TUI

    def test_handle_confirm_no(self):
        """Test 'n' key in confirm"""
        session = TUISession()
        session.state = State.CONFIRM

        result = session._handle_confirm("n")

        assert result is True
        assert session.state == State.TASK

    def test_handle_confirm_escape(self):
        """Test Escape key in confirm"""
        session = TUISession()
        session.state = State.CONFIRM
        session.task_input = "test"

        result = session._handle_confirm("escape")

        assert result is True
        assert session.state == State.MAIN
        assert session.task_input == ""


class TestRender:
    """Test render method for various states"""

    def test_render_main_state(self):
        """Test rendering main state"""
        session = TUISession()
        session.state = State.MAIN

        result = session.render()

        assert result is not None

    def test_render_task_state(self):
        """Test rendering task state"""
        session = TUISession()
        session.state = State.TASK

        result = session.render()

        assert result is not None

    def test_render_confirm_state(self):
        """Test rendering confirm state"""
        session = TUISession()
        session.state = State.CONFIRM

        result = session.render()

        assert result is not None

    def test_render_model_state(self):
        """Test rendering model state"""
        session = TUISession()
        session.state = State.MODEL

        result = session.render()

        assert result is not None

    def test_render_agents_state(self):
        """Test rendering agents state"""
        session = TUISession()
        session.state = State.AGENTS

        result = session.render()

        assert result is not None

    def test_render_workflow_state(self):
        """Test rendering workflow state"""
        session = TUISession()
        session.state = State.WORKFLOW

        result = session.render()

        assert result is not None
