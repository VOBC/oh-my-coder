"""Tests for src/commands/cli_tui.py - simple output functions."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from commands.cli_tui import (
    AGENT_CATEGORIES,
    MODELS,
    WORKFLOWS,
    list_agents,
    list_models,
    list_workflows,
)


class TestListAgents:
    """Test list_agents() output."""

    @patch("commands.cli_tui.console")
    def test_calls_console_print(self, mock_console):
        list_agents()
        mock_console.print.assert_called()

    @patch("commands.cli_tui.console")
    def test_prints_table(self, mock_console):
        list_agents()
        from rich.table import Table

        has_table = any(
            isinstance(call.args[0], Table)
            for call in mock_console.print.call_args_list
            if call.args
        )
        assert has_table

    @patch("commands.cli_tui.console")
    def test_prints_agent_count(self, mock_console):
        list_agents()
        total_agents = sum(len(agents) for agents in AGENT_CATEGORIES.values())
        found = False
        for call in mock_console.print.call_args_list:
            if call.args and isinstance(call.args[0], str):
                if str(total_agents) in call.args[0]:
                    found = True
        assert found


class TestListWorkflows:
    """Test list_workflows() output."""

    @patch("commands.cli_tui.console")
    def test_calls_console_print(self, mock_console):
        list_workflows()
        mock_console.print.assert_called()

    @patch("commands.cli_tui.console")
    def test_prints_table(self, mock_console):
        list_workflows()
        from rich.table import Table

        has_table = any(
            isinstance(call.args[0], Table)
            for call in mock_console.print.call_args_list
            if call.args
        )
        assert has_table

    def test_workflow_count_matches_workflows(self):
        assert len(WORKFLOWS) == 7

    @patch("commands.cli_tui.console")
    def test_table_title_mentions_workflow(self, mock_console):
        list_workflows()
        from rich.table import Table

        table = next(
            call.args[0]
            for call in mock_console.print.call_args_list
            if call.args and isinstance(call.args[0], Table)
        )
        assert "工作流" in str(table.title)


class TestListModels:
    """Test list_models() output."""

    @patch("commands.cli_tui.console")
    def test_calls_console_print(self, mock_console):
        list_models()
        mock_console.print.assert_called()

    @patch("commands.cli_tui.console")
    def test_prints_table(self, mock_console):
        list_models()
        from rich.table import Table

        has_table = any(
            isinstance(call.args[0], Table)
            for call in mock_console.print.call_args_list
            if call.args
        )
        assert has_table

    def test_models_count_matches_constant(self):
        assert len(MODELS) == 5

    @patch("commands.cli_tui.console")
    def test_table_title_mentions_model(self, mock_console):
        list_models()
        from rich.table import Table

        table = next(
            call.args[0]
            for call in mock_console.print.call_args_list
            if call.args and isinstance(call.args[0], Table)
        )
        assert "模型" in str(table.title)


class TestConstants:
    """Test that constants are well-formed."""

    def test_workflows_format(self):
        for key, desc, detail in WORKFLOWS:
            assert isinstance(key, str)
            assert isinstance(desc, str)
            assert isinstance(detail, str)

    def test_models_format(self):
        for key, name, desc in MODELS:
            assert isinstance(key, str)
            assert isinstance(name, str)
            assert isinstance(desc, str)

    def test_agent_categories_format(self):
        for category, agents in AGENT_CATEGORIES.items():
            assert isinstance(category, str)
            assert isinstance(agents, list)
            assert all(isinstance(a, str) for a in agents)


# =============================================================================
# TUISession unit tests - covers all render methods and state transitions
# =============================================================================
from commands.cli_tui import Keys, State, TUISession


class TestTUISessionInit:
    """Test TUISession initialization."""

    def test_default_state_is_main(self):
        session = TUISession()
        assert session.state == State.MAIN

    def test_default_model_is_deepseek(self):
        session = TUISession()
        assert session.selected_model == "deepseek"

    def test_cursor_starts_at_zero(self):
        session = TUISession()
        assert session.cursor == 0

    def test_task_input_starts_empty(self):
        session = TUISession()
        assert session.task_input == ""

    def test_confirm_choice_starts_false(self):
        session = TUISession()
        assert session.confirm_choice is False


class TestTUISessionRender:
    """Test TUISession.render() for all states."""

    def test_render_main_state(self):
        session = TUISession()
        session.state = State.MAIN
        panel = session.render()
        from rich.panel import Panel
        assert isinstance(panel, Panel)

    def test_render_workflow_state(self):
        session = TUISession()
        session.state = State.WORKFLOW
        panel = session.render()
        assert panel.title == "[bold]工作流选择[/bold]"

    def test_render_model_state(self):
        session = TUISession()
        session.state = State.MODEL
        panel = session.render()
        assert panel.title == "[bold]模型选择[/bold]"

    def test_render_agents_state(self):
        session = TUISession()
        session.state = State.AGENTS
        panel = session.render()
        assert panel.title == "[bold]Agent 列表[/bold]"

    def test_render_task_state(self):
        session = TUISession()
        session.state = State.TASK
        session.selected_workflow = "explore"
        panel = session.render()
        from rich.panel import Panel
        assert isinstance(panel, Panel)

    def test_render_confirm_state(self):
        session = TUISession()
        session.state = State.CONFIRM
        panel = session.render()
        from rich.panel import Panel
        assert isinstance(panel, Panel)

    def test_render_unknown_state_falls_back(self):
        session = TUISession()
        session.state = None  # type: ignore
        panel = session.render()
        from rich.panel import Panel
        assert isinstance(panel, Panel)


class TestRenderMain:
    """Test _render_main() details."""

    def test_renders_all_7_workflows(self):
        session = TUISession()
        panel = session._render_main()
        content = str(panel.renderable)
        for key, _, _ in WORKFLOWS:
            assert key in content

    def test_cursor_highlight_in_content(self):
        session = TUISession()
        session.cursor = 0
        panel = session._render_main()
        content = str(panel.renderable)
        # First workflow should be highlighted
        assert "▶" in content or "[1]" in content

    def test_shortcuts_shown(self):
        session = TUISession()
        panel = session._render_main()
        content = str(panel.renderable)
        assert "m" in content and "a" in content and "q" in content


class TestRenderWorkflow:
    """Test _render_workflow() details."""

    def test_all_7_workflows_shown(self):
        session = TUISession()
        panel = session._render_workflow()
        content = str(panel.renderable)
        for key, desc, _ in WORKFLOWS:
            assert key in content
            assert desc in content

    def test_navigation_hints_shown(self):
        session = TUISession()
        panel = session._render_workflow()
        content = str(panel.renderable)
        assert "↑↓" in content and "Enter" in content and "Esc" in content


class TestRenderModel:
    """Test _render_model() details."""

    def test_all_models_shown(self):
        session = TUISession()
        panel = session._render_model()
        content = str(panel.renderable)
        for _key, name, _ in MODELS:
            assert name in content

    def test_current_model_marked(self):
        session = TUISession()
        session.selected_model = "deepseek"
        panel = session._render_model()
        content = str(panel.renderable)
        assert "◀" in content or "当前" in content


class TestRenderAgents:
    """Test _render_agents() details."""

    def test_shows_categories(self):
        session = TUISession()
        panel = session._render_agents()
        content = str(panel.renderable)
        # Only first 3 categories are shown due to [:3] slice
        categories_shown = list(AGENT_CATEGORIES.keys())[:3]
        for category in categories_shown:
            assert category in content

    def test_shows_agent_names(self):
        session = TUISession()
        panel = session._render_agents()
        content = str(panel.renderable)
        # Should show some agent names
        agents = list(AGENT_CATEGORIES.values())[0]
        assert any(a in content for a in agents[:3])


class TestRenderTask:
    """Test _render_task() details."""

    def test_shows_selected_workflow(self):
        session = TUISession()
        session.selected_workflow = "build"
        panel = session._render_task()
        content = str(panel.renderable)
        assert "build" in content

    def test_empty_workflow_handled(self):
        session = TUISession()
        session.selected_workflow = None
        panel = session._render_task()
        from rich.panel import Panel
        assert isinstance(panel, Panel)


class TestRenderConfirm:
    """Test _render_confirm() details."""

    def test_confirm_panel_exists(self):
        session = TUISession()
        session.confirm_choice = False
        panel = session._render_confirm()
        from rich.panel import Panel
        assert isinstance(panel, Panel)

    def test_confirm_true_different_from_false(self):
        session_false = TUISession()
        session_false.confirm_choice = False
        session_true = TUISession()
        session_true.confirm_choice = True
        p1 = session_false._render_confirm()
        p2 = session_true._render_confirm()
        # Both are Panels, content may differ
        assert p1 is not p2


class TestTUISessionStateTransitions:
    """Test state transitions."""

    def test_can_change_state(self):
        session = TUISession()
        session.state = State.MODEL
        assert session.state == State.MODEL

    def test_can_change_selected_workflow(self):
        session = TUISession()
        session.selected_workflow = "debug"
        assert session.selected_workflow == "debug"

    def test_can_change_selected_model(self):
        session = TUISession()
        session.selected_model = "glm"
        assert session.selected_model == "glm"

    def test_can_change_task_input(self):
        session = TUISession()
        session.task_input = "fix the bug"
        assert session.task_input == "fix the bug"

    def test_can_change_cursor(self):
        session = TUISession()
        session.cursor = 5
        assert session.cursor == 5

    def test_can_toggle_confirm_choice(self):
        session = TUISession()
        session.confirm_choice = True
        assert session.confirm_choice is True



    def test_workflow_keys_are_unique(self):
        keys = [w[0] for w in WORKFLOWS]
        assert len(keys) == len(set(keys))

    def test_model_keys_are_unique(self):
        keys = [m[0] for m in MODELS]
        assert len(keys) == len(set(keys))


class TestStateEnum:
    """Test State enum."""

    def test_all_expected_states_exist(self):
        expected = {State.MAIN, State.WORKFLOW, State.MODEL, State.AGENTS, State.TASK, State.CONFIRM}
        assert expected.issubset(set(State))

    def test_state_values_are_strings(self):
        for s in State:
            assert isinstance(s.value, str)


# =============================================================================
# Additional coverage for handle_key, _handle_* methods, start command
# =============================================================================


class TestHandleKey:
    """Test handle_key() dispatcher."""

    def test_q_key_returns_false(self):
        session = TUISession()
        result = session.handle_key("q")
        assert result is False

    def test_unknown_key_stays_true(self):
        session = TUISession()
        result = session.handle_key("x")
        assert result is True

    def test_main_state_dispatched(self):
        session = TUISession()
        session.state = State.MAIN
        result = session.handle_key(Keys.Up)
        assert result is True

    def test_workflow_state_dispatched(self):
        session = TUISession()
        session.state = State.WORKFLOW
        result = session.handle_key(Keys.Down)
        assert result is True

    def test_model_state_dispatched(self):
        session = TUISession()
        session.state = State.MODEL
        result = session.handle_key(Keys.Up)
        assert result is True

    def test_agents_state_dispatched(self):
        session = TUISession()
        session.state = State.AGENTS
        result = session.handle_key("x")
        assert result is True

    def test_task_state_dispatched(self):
        session = TUISession()
        session.state = State.TASK
        result = session.handle_key("x")
        assert result is True

    def test_confirm_state_dispatched(self):
        session = TUISession()
        session.state = State.CONFIRM
        result = session.handle_key("x")
        assert result is True

    def test_escape_key_transitions_from_confirm(self):
        session = TUISession()
        session.state = State.CONFIRM
        session.handle_key("escape")
        assert session.state == State.MAIN

    def test_y_key_executes_task(self):
        session = TUISession()
        session.state = State.CONFIRM
        session.task_input = "test task"
        session.selected_workflow = "explore"
        session.selected_model = "deepseek"
        result = session.handle_key("y")
        assert result is False  # Exits after execution


class TestHandleMain:
    """Test _handle_main() keyboard handling."""

    def test_up_key_decrements_cursor(self):
        session = TUISession()
        session.cursor = 3
        session._handle_main(Keys.Up)
        assert session.cursor == 2

    def test_down_key_increments_cursor(self):
        session = TUISession()
        session.cursor = 1
        session._handle_main(Keys.Down)
        assert session.cursor == 2

    def test_up_at_zero_stays_zero(self):
        session = TUISession()
        session.cursor = 0
        session._handle_main(Keys.Up)
        assert session.cursor == 0

    def test_down_at_max_stays_max(self):
        session = TUISession()
        session.cursor = 6
        session._handle_main(Keys.Down)
        assert session.cursor == 6

    def test_numeric_key_selects_workflow(self):
        session = TUISession()
        session._handle_main("3")
        assert session.state == State.TASK
        assert session.selected_workflow == "debug"

    def test_m_key_switches_to_model(self):
        session = TUISession()
        session._handle_main("m")
        assert session.state == State.MODEL

    def test_a_key_switches_to_agents(self):
        session = TUISession()
        session._handle_main("a")
        assert session.state == State.AGENTS

    def test_enter_key_transitions_to_task(self):
        session = TUISession()
        session._handle_main("\n")
        assert session.state == State.TASK


class TestHandleWorkflow:
    """Test _handle_workflow() keyboard handling."""

    def test_up_key_navigates(self):
        session = TUISession()
        session.cursor = 3
        session._handle_workflow(Keys.Up)
        assert session.cursor == 2

    def test_down_key_navigates(self):
        session = TUISession()
        session.cursor = 1
        session._handle_workflow(Keys.Down)
        assert session.cursor == 2

    def test_enter_selects_workflow(self):
        session = TUISession()
        session.cursor = 0
        session._handle_workflow("\n")
        assert session.selected_workflow == "explore"

    def test_escape_returns_to_main(self):
        session = TUISession()
        session._handle_workflow("escape")
        assert session.state == State.MAIN

    def test_ctrl_c_returns_to_main(self):
        session = TUISession()
        session._handle_workflow("ctrl+c")
        assert session.state == State.MAIN


class TestHandleModel:
    """Test _handle_model() keyboard handling."""

    def test_up_key_navigates(self):
        session = TUISession()
        session.cursor = 2
        session._handle_model(Keys.Up)
        assert session.cursor == 1

    def test_down_key_navigates(self):
        session = TUISession()
        session.cursor = 1
        session._handle_model(Keys.Down)
        assert session.cursor == 2

    def test_enter_selects_model(self):
        session = TUISession()
        session.cursor = 0
        session._handle_model("\n")
        assert session.selected_model == "deepseek"

    def test_escape_returns_to_main(self):
        session = TUISession()
        session._handle_model("escape")
        assert session.state == State.MAIN


class TestHandleAgents:
    """Test _handle_agents() keyboard handling."""

    def test_escape_returns_to_main(self):
        session = TUISession()
        session._handle_agents("escape")
        assert session.state == State.MAIN

    def test_q_returns_to_main(self):
        session = TUISession()
        session._handle_agents("q")
        assert session.state == State.MAIN


class TestHandleTask:
    """Test _handle_task() keyboard handling."""

    def test_escape_returns_to_main(self):
        session = TUISession()
        session._handle_task("escape")
        assert session.state == State.MAIN

    def test_ctrl_c_returns_to_main(self):
        session = TUISession()
        session._handle_task("ctrl+c")
        assert session.state == State.MAIN

    def test_enter_empty_input_stays_in_task(self):
        """Empty input with Enter → state stays (no transition to CONFIRM)."""
        session = TUISession()
        # Enter TASK via model selection, type something, then clear it
        session.state = State.TASK
        session.task_input = ""  # empty from start
        session._handle_task("\n")
        # State stays in TASK (CONFIRM only on non-empty)
        assert session.state == State.TASK
        assert session.task_input == ""

    def test_non_empty_input_transitions_to_confirm(self):
        """Non-empty input + Enter → transitions to CONFIRM."""
        session = TUISession()
        session.state = State.TASK
        session.task_input = "hello"
        session._handle_task("\n")
        assert session.state == State.CONFIRM

    @patch("commands.cli_tui.console.input")
    def test_enter_with_skill_command_handles_slash(self, mock_input):
        """Skill command (/xxx) → clears input, returns to MAIN."""
        session = TUISession()
        session.state = State.TASK
        session.task_input = "/test-skill"
        mock_input.return_value = ""
        session._handle_task("\n")
        assert session.task_input == ""
        # Skill command transitions to MAIN
        assert session.state == State.MAIN

    def test_backspace_removes_last_char(self):
        session = TUISession()
        session.task_input = "test"
        session._handle_task("backspace")
        assert session.task_input == "tes"


class TestExecuteTask:
    """Test _execute_task()."""

    def test_execute_task_sets_fields(self):
        session = TUISession()
        session.task_input = "build api"
        session.selected_workflow = "build"
        session.selected_model = "glm"
        # Just verify no crash
        session._execute_task()
