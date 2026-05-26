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
