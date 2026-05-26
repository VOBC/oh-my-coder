"""Tests for src/commands/cli_quest.py - simple CLI functions."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from commands.cli_quest import _print_fatal


class TestPrintFatal:
    """Test _print_fatal helper."""

    @patch("commands.cli_quest.console")
    def test_print_fatal_output(self, mock_console):
        _print_fatal("something went wrong")
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        assert "something went wrong" in str(call_args[0][0])

    @patch("commands.cli_quest.console")
    def test_print_fatal_format(self, mock_console):
        _print_fatal("测试中文")
        call_args = mock_console.print.call_args
        assert "测试中文" in str(call_args[0][0])
        assert "❌" in str(call_args[0][0])


# ---------------------------------------------------------------------------
# Patch src.quest.QuestManager (where QuestManager is defined, not locally imported)
# ---------------------------------------------------------------------------

class TestQuestList:
    """Test quest_list command."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_list_empty(self, mock_console, mock_qm_class):
        mock_manager = MagicMock()
        mock_manager.list_quests.return_value = []
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_list

        quest_list(project_path=Path("."), status_filter=None, all_quests=False)

        printed_texts = [
            str(call.args[0])
            for call in mock_console.print.call_args_list
            if call.args
        ]
        assert any("暂无" in t for t in printed_texts)

    @patch("src.quest.QuestStatus")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_list_with_quests(self, mock_console, mock_qm_class, mock_qs_class):
        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.title = "Test Quest"
        mock_quest.status = MagicMock()
        mock_quest.status.value = "pending"
        mock_quest.progress.return_value = 0.0
        mock_quest.duration.return_value = None
        mock_quest.created_at.strftime.return_value = "05-26 10:00"

        mock_manager = MagicMock()
        mock_manager.list_quests.return_value = [mock_quest]
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_list

        quest_list(project_path=Path("."), status_filter=None, all_quests=False)

        from rich.table import Table

        has_table = any(
            isinstance(call.args[0], Table)
            for call in mock_console.print.call_args_list
            if call.args
        )
        assert has_table


class TestQuestCancel:
    """Test quest_cancel command."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_cancel_success(self, mock_console, mock_qm_class):
        mock_manager = MagicMock()
        mock_manager.cancel.return_value = True
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_cancel

        quest_cancel(quest_id="abc123", project_path=Path("."))
        mock_manager.cancel.assert_called_once_with("abc123")

        printed = [
            str(call.args[0])
            for call in mock_console.print.call_args_list
            if call.args
        ]
        assert any("已取消" in t for t in printed)

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_cancel_not_found(self, mock_console, mock_qm_class):
        import typer
        mock_manager = MagicMock()
        mock_manager.cancel.return_value = False
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_cancel

        with pytest.raises(typer.Exit):
            quest_cancel(quest_id="notexist", project_path=Path("."))


class TestQuestPause:
    """Test quest_pause command."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_pause_success(self, mock_console, mock_qm_class):
        mock_manager = MagicMock()
        mock_manager.pause.return_value = True
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_pause

        quest_pause(quest_id="abc123", project_path=Path("."))
        mock_manager.pause.assert_called_once_with("abc123")

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_pause_not_found(self, mock_console, mock_qm_class):
        import typer
        mock_manager = MagicMock()
        mock_manager.pause.return_value = False
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_pause

        with pytest.raises(typer.Exit):
            quest_pause(quest_id="notexist", project_path=Path("."))


class TestQuestResume:
    """Test quest_resume command."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_resume_success(self, mock_console, mock_qm_class):
        mock_manager = MagicMock()
        mock_manager.resume.return_value = MagicMock()
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_resume

        quest_resume(quest_id="abc123", project_path=Path("."))
        mock_manager.resume.assert_called_once_with("abc123")

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_resume_not_found(self, mock_console, mock_qm_class):
        import typer
        mock_manager = MagicMock()
        mock_manager.resume.return_value = None
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_resume

        with pytest.raises(typer.Exit):
            quest_resume(quest_id="notexist", project_path=Path("."))


class TestQuestStatus:
    """Test quest_status command."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_status_success(self, mock_console, mock_qm_class):
        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.title = "Test Quest"
        mock_quest.status.value = "completed"
        mock_quest.progress.return_value = 1.0
        mock_quest.duration.return_value = 42.0
        mock_quest.spec_path = None
        mock_quest.error_message = None
        mock_quest.result_summary = "All done"
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_status

        quest_status(quest_id="abc12345", project_path=Path("."))
        # Should print a Panel
        from rich.panel import Panel
        has_panel = any(
            isinstance(call.args[0], Panel)
            for call in mock_console.print.call_args_list
            if call.args
        )
        assert has_panel

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_status_not_found(self, mock_console, mock_qm_class):
        import typer
        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = None
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_status

        with pytest.raises(typer.Exit):
            quest_status(quest_id="notexist", project_path=Path("."))


class TestQuestExec:
    """Test quest_exec command."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_exec_success(self, mock_console, mock_qm_class):
        from src.quest import QuestStatus

        mock_quest = MagicMock()
        mock_quest.status = QuestStatus.SPEC_READY
        mock_quest.id = "abc12345"
        mock_quest.title = "Test Quest"

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_exec

        quest_exec(quest_id="abc12345", project_path=Path("."))
        mock_manager.confirm_and_execute.assert_called_once_with("abc12345")

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_exec_not_found(self, mock_console, mock_qm_class):
        import typer
        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = None
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_exec

        with pytest.raises(typer.Exit):
            quest_exec(quest_id="notexist", project_path=Path("."))

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_exec_wrong_status(self, mock_console, mock_qm_class):
        import typer

        from src.quest import QuestStatus

        mock_quest = MagicMock()
        mock_quest.status = QuestStatus.PENDING  # not SPEC_READY
        mock_quest.id = "abc12345"

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_exec

        with pytest.raises(typer.Exit):
            quest_exec(quest_id="abc12345", project_path=Path("."))


class TestShowAcceptanceReport:
    """Test _show_acceptance_report helper."""

    def _make_quest(self, status_value="completed"):
        mock_quest = MagicMock()
        mock_quest.title = "Test Quest"
        mock_quest.status.value = status_value
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = 42.0
        mock_quest.result_summary = "All done"
        mock_quest.error_message = None
        mock_quest.steps = []
        return mock_quest

    def test_show_completed(self):
        from commands.cli_quest import _show_acceptance_report

        mock_console = MagicMock()
        mock_quest = self._make_quest("completed")

        _show_acceptance_report(mock_quest, mock_console)
        # Should print Panel and text
        from rich.panel import Panel
        has_panel = any(
            isinstance(call.args[0], Panel)
            for call in mock_console.print.call_args_list
            if call.args
        )
        assert has_panel

    def test_show_failed(self):
        from commands.cli_quest import _show_acceptance_report

        mock_console = MagicMock()
        mock_quest = self._make_quest("failed")
        mock_quest.result_summary = None
        mock_quest.error_message = "Something broke"

        _show_acceptance_report(mock_quest, mock_console)
        from rich.panel import Panel
        has_panel = any(
            isinstance(call.args[0], Panel)
            for call in mock_console.print.call_args_list
            if call.args
        )
        assert has_panel
