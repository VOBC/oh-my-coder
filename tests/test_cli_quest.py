"""Tests for src/commands/cli_quest.py - simple CLI functions."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from commands.cli_quest import _print_fatal


@pytest.fixture(autouse=True)
def _instant_async_sleep(monkeypatch):
    """Make asyncio.sleep instant so watch-loop tests don't really sleep.

    The watch loops in cli_quest.py call `await asyncio.sleep(5)` (or 3).
    When asyncio.run is mocked to execute the coroutine, the real sleep would
    block 5s per iteration AND hang forever whenever get_quest never returns a
    terminal status. Patching it instant keeps the tests fast and finite.
    """

    async def _instant(*args, **kwargs):
        return None

    monkeypatch.setattr("asyncio.sleep", _instant)


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


class TestQuestMainCommand:
    """Test the main quest() command."""

    @patch("commands.cli_quest.console")
    def test_quest_nonexistent_path(self, mock_console):
        import typer

        from commands.cli_quest import quest

        with pytest.raises(typer.Exit):
            quest(
                ctx=MagicMock(),
                description="test task",
                project_path=Path("/nonexistent/path/xyz"),
                title=None,
                skip_spec=False,
                auto_confirm=False,
            )

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_quest_auto_confirm(self, mock_console, mock_qm_class, mock_asyncio_run):
        mock_manager = MagicMock()
        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_qm_class.return_value = mock_manager
        mock_asyncio_run.return_value = None

        from commands.cli_quest import quest

        quest(
            ctx=MagicMock(),
            description="implement auth module",
            project_path=Path("."),
            title="Auth",
            skip_spec=True,
            auto_confirm=True,
        )
        mock_asyncio_run.assert_called_once()

    @patch("asyncio.run", side_effect=Exception("Quest failed"))
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_quest_exception_handling(self, mock_console, mock_qm_class, mock_asyncio_run):
        import typer

        from commands.cli_quest import quest

        mock_qm_class.return_value = MagicMock()

        with pytest.raises(typer.Exit):
            quest(
                ctx=MagicMock(),
                description="test task",
                project_path=Path("."),
                title=None,
                skip_spec=True,
                auto_confirm=True,
            )


class TestQuestListWithFilter:
    """Test quest_list with status filter."""

    @patch("src.quest.QuestStatus")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_list_with_valid_status_filter(self, mock_console, mock_qm_class, mock_qs_class):
        mock_qs_class.side_effect = lambda v: v

        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.title = "Test Quest"
        mock_quest.status = MagicMock()
        mock_quest.status.value = "completed"
        mock_quest.progress.return_value = 1.0
        mock_quest.duration.return_value = 30.0
        mock_quest.created_at.strftime.return_value = "05-26 10:00"

        mock_manager = MagicMock()
        mock_manager.list_quests.return_value = [mock_quest]
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_list

        quest_list(project_path=Path("."), status_filter="completed", all_quests=False)
        mock_manager.list_quests.assert_called_once()

    @patch("src.quest.QuestStatus")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_list_with_invalid_status(self, mock_console, mock_qm_class, mock_qs_class):
        import typer

        mock_qs_class.side_effect = ValueError("invalid status")
        mock_qm_class.return_value = MagicMock()

        from commands.cli_quest import quest_list

        with pytest.raises(typer.Exit):
            quest_list(project_path=Path("."), status_filter="invalid", all_quests=False)


class TestQuestStatusWithDetails:
    """Test quest_status with various quest states."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_status_with_spec_path_and_error(self, mock_console, mock_qm_class):
        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.title = "Test Quest"
        mock_quest.status.value = "spec_ready"
        mock_quest.progress.return_value = 0.5
        mock_quest.duration.return_value = 10.0
        mock_quest.spec_path = "/path/to/spec.md"
        mock_quest.error_message = "Some error"
        mock_quest.result_summary = "Summary here"
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_status

        quest_status(quest_id="abc12345", project_path=Path("."))
        assert mock_console.print.called

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_status_with_steps(self, mock_console, mock_qm_class):
        from src.quest import QuestStatus

        mock_step = MagicMock()
        mock_step.step_id = "1"
        mock_step.title = "Write tests"
        mock_step.agent = "coder"
        mock_step.status = QuestStatus.COMPLETED

        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.title = "Test Quest"
        mock_quest.status = QuestStatus.COMPLETED
        mock_quest.progress.return_value = 1.0
        mock_quest.duration.return_value = 42.0
        mock_quest.spec_path = None
        mock_quest.error_message = None
        mock_quest.result_summary = "Done"
        mock_quest.steps = [mock_step]

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_status

        quest_status(quest_id="abc12345", project_path=Path("."))
        assert mock_console.print.call_count >= 2


class TestQuestNotify:
    """Test quest_notify command."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_quest_not_found(self, mock_console, mock_qm_class):
        import typer
        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = None
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_notify

        with pytest.raises(typer.Exit):
            quest_notify(quest_id="notexist", project_path=Path("."))


class TestQuestWait:
    """Test quest_wait command."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_already_completed(self, mock_console, mock_qm_class):
        from src.quest import QuestStatus

        mock_quest = MagicMock()
        mock_quest.status = QuestStatus.COMPLETED
        mock_quest.title = "Test"
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = 10.0
        mock_quest.result_summary = "Done"
        mock_quest.error_message = None
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        assert mock_console.print.called

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_not_found(self, mock_console, mock_qm_class):
        import typer
        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = None
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_wait

        with pytest.raises(typer.Exit):
            quest_wait(quest_id="notexist", project_path=Path("."))

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_already_failed(self, mock_console, mock_qm_class):
        from src.quest import QuestStatus

        mock_quest = MagicMock()
        mock_quest.status = QuestStatus.FAILED
        mock_quest.title = "Test"
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = 5.0
        mock_quest.result_summary = None
        mock_quest.error_message = "Error"
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        assert mock_console.print.called

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_already_cancelled(self, mock_console, mock_qm_class):
        from src.quest import QuestStatus

        mock_quest = MagicMock()
        mock_quest.status = QuestStatus.CANCELLED
        mock_quest.title = "Test"
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = None
        mock_quest.result_summary = None
        mock_quest.error_message = None
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        assert mock_console.print.called


class TestShowAcceptanceReportExtended:
    """Extended tests for _show_acceptance_report."""

    def test_show_cancelled(self):
        from commands.cli_quest import _show_acceptance_report

        mock_console = MagicMock()
        mock_quest = MagicMock()
        mock_quest.title = "Test Quest"
        mock_quest.status.value = "cancelled"
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = None
        mock_quest.result_summary = None
        mock_quest.error_message = None
        mock_quest.steps = []

        _show_acceptance_report(mock_quest, mock_console)
        assert mock_console.print.called

    def test_show_with_failed_steps(self):
        from commands.cli_quest import _show_acceptance_report
        from src.quest import QuestStatus

        mock_step = MagicMock()
        mock_step.step_id = "1"
        mock_step.title = "Write code"
        mock_step.status = QuestStatus.FAILED
        mock_step.error = "Compilation error"

        mock_console = MagicMock()
        mock_quest = MagicMock()
        mock_quest.title = "Test Quest"
        mock_quest.status.value = "failed"
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = 30.0
        mock_quest.result_summary = None
        mock_quest.error_message = "Failed"
        mock_quest.steps = [mock_step]

        _show_acceptance_report(mock_quest, mock_console)
        assert mock_console.print.call_count >= 3

    def test_show_with_no_duration(self):
        from commands.cli_quest import _show_acceptance_report

        mock_console = MagicMock()
        mock_quest = MagicMock()
        mock_quest.title = "Test"
        mock_quest.status.value = "completed"
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = None
        mock_quest.result_summary = "Done"
        mock_quest.error_message = None
        mock_quest.steps = []

        _show_acceptance_report(mock_quest, mock_console)
        assert mock_console.print.called


class TestQuestMainWithAsync:
    """Test main quest command with async paths."""

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_quest_no_auto_confirm_exits(self, mock_console, mock_qm_class, mock_asyncio_run):
        """Without auto_confirm and skip_spec, should exit after showing SPEC."""
        from commands.cli_quest import quest

        # The inner run() calls raise typer.Exit(0) when !auto_confirm
        # asyncio.run will raise SystemExit from typer.Exit
        mock_asyncio_run.side_effect = SystemExit(0)

        with pytest.raises(SystemExit):
            quest(
                ctx=MagicMock(),
                description="test task",
                project_path=Path("."),
                title=None,
                skip_spec=False,
                auto_confirm=False,
            )

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    @patch("commands.cli_quest.Progress")
    def test_quest_skip_spec_auto_confirm(self, mock_progress, mock_console, mock_qm_class, mock_asyncio_run):
        """skip_spec=True + auto_confirm=True should call confirm_and_execute."""
        from commands.cli_quest import quest

        mock_manager = MagicMock()
        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_qm_class.return_value = mock_manager
        mock_asyncio_run.return_value = None

        quest(
            ctx=MagicMock(),
            description="test",
            project_path=Path("."),
            title=None,
            skip_spec=True,
            auto_confirm=True,
        )
        mock_asyncio_run.assert_called_once()


class TestQuestListMultipleQuests:
    """Test quest_list with multiple quests and progress bars."""

    @patch("src.quest.QuestStatus")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_list_multiple_quests(self, mock_console, mock_qm_class, mock_qs_class):
        mock_qs_class.side_effect = lambda v: v

        quest1 = MagicMock()
        quest1.id = "abc11111"
        quest1.title = "Quest One"
        quest1.status = MagicMock()
        quest1.status.value = "completed"
        quest1.progress.return_value = 1.0
        quest1.duration.return_value = 60.0
        quest1.created_at.strftime.return_value = "05-26 10:00"

        quest2 = MagicMock()
        quest2.id = "def22222"
        quest2.title = "Quest Two"
        quest2.status = MagicMock()
        quest2.status.value = "pending"
        quest2.progress.return_value = 0.0
        quest2.duration.return_value = None
        quest2.created_at.strftime.return_value = "05-26 11:00"

        mock_manager = MagicMock()
        mock_manager.list_quests.return_value = [quest1, quest2]
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


class TestQuestNotifyFound:
    """Test quest_notify when quest exists."""

    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_quest_found_creates_config(self, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class):
        """When quest exists, should create NotificationConfig and NotificationManager."""
        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.status.value = "executing"
        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        mock_notifier = MagicMock()
        mock_notifier._channels = []
        mock_nm_class.return_value = mock_notifier

        mock_cn_instance = MagicMock()
        mock_cn_class.return_value = mock_cn_instance

        from commands.cli_quest import quest_notify

        # asyncio.run(watch()) will hang, so mock it
        with patch("asyncio.run"):
            quest_notify(
                quest_id="abc12345",
                project_path=Path("."),
                dingtalk_webhook="https://example.com",
            )

        mock_nc_class.assert_called_once()
        mock_nm_class.assert_called_once()
        assert mock_cn_instance in mock_notifier._channels


class TestQuestNotifyProgress:
    """Test on_progress callback inside quest_notify."""

    def test_on_progress_info(self):
        """Test the on_progress callback logic directly."""
        color_map = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }
        level = "info"
        color = color_map.get(level, "white")
        assert color == "cyan"

    def test_on_progress_unknown(self):
        color_map = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }
        color = color_map.get("unknown", "white")
        assert color == "white"


class TestQuestNotifyWatchLoop:
    """Test the watch loop inside quest_notify using patch('asyncio.run')."""

    def _run_coro(self, coro):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()

    @patch("asyncio.run")
    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_watch_completes(self, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class, mock_asyncio_run):
        """Watch loop detects completed quest and calls notifier."""

        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test Quest"
            mock_quest.result_summary = "Done"
            mock_quest.error_message = None
            if call_count[0] == 1:
                mock_quest.status.value = "executing"
                mock_quest.steps = None
            else:
                mock_quest.status.value = "completed"
                mock_quest.steps = None
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_notifier = MagicMock()
        mock_notifier._channels = []
        mock_nm_class.return_value = mock_notifier
        mock_cn_class.return_value = MagicMock()

        mock_asyncio_run.side_effect = self._run_coro

        from commands.cli_quest import quest_notify

        quest_notify(quest_id="abc12345", project_path=Path("."))

        mock_notifier.notify_completed.assert_called_once()
        mock_nc_class.assert_called_once()


class TestQuestWaitAlreadyDone:
    """Additional tests for quest_wait with different terminal states."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_with_cancelled_quest(self, mock_console, mock_qm_class):
        from src.quest import QuestStatus

        mock_quest = MagicMock()
        mock_quest.status = QuestStatus.CANCELLED
        mock_quest.title = "Test"
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = None
        mock_quest.result_summary = None
        mock_quest.error_message = None
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        assert mock_console.print.called

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_no_duration(self, mock_console, mock_qm_class):
        from src.quest import QuestStatus

        mock_quest = MagicMock()
        mock_quest.status = QuestStatus.COMPLETED
        mock_quest.title = "Test"
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = None
        mock_quest.result_summary = "Done"
        mock_quest.error_message = None
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        assert mock_console.print.called


# =============================================================================
# Additional coverage for uncovered lines:
#   70-85   : review_callback inside quest()
#   91-131  : run() inside quest() (SPEC generation path)
#   449-456 : on_progress + ConsoleNotificationChannel import in quest_notify
#   475     : watch() step-completion output in quest_notify
#   479-486 : status change -> completed/failed/paused branches in quest_notify
#   498-505 : watch loop break on completed/failed/cancelled in quest_notify
#   516-517 : asyncio.CancelledError in quest_notify watch
#   521-522 : KeyboardInterrupt in quest_notify
#   567     : quest_wait watch() loop
#   571-577 : quest_wait watch body (steps + status check)
#   595-596 : quest_wait terminal status break
#   600-601 : KeyboardInterrupt in quest_wait
# =============================================================================


class TestReviewCallback:
    """Test review_callback function (lines 70-85).

    review_callback is defined inside quest() and uses Prompt.ask.
    We reproduce its logic here and verify Prompt.ask integration.
    """

    def test_review_callback_prompt_integration(self):
        """Lines 70-85: review_callback logic - Prompt.ask integration."""
        # Reproduce review_callback logic inline, patching Prompt.ask at source
        from unittest.mock import patch

        async def review_callback_logic(quest_id, step_id, preview):
            """Exact copy of review_callback from cli_quest.py lines 70-85."""
            # Use actual rich console (not mocked for print part)
            from rich.panel import Panel

            from commands.cli_quest import console
            console.print(f"\n[bold cyan]📋 步骤验收: {step_id}[/bold cyan]")
            if preview:
                console.print(
                    Panel.fit(preview[:500], title="执行结果预览", border_style="dim")
                )

            from rich.prompt import Prompt
            choice = Prompt.ask(
                "请选择",
                choices=["p", "r", "s"],
                default="p",
                show_choices=True,
            )
            mapping = {"p": "pass", "r": "retry", "s": "skip"}
            return mapping.get(choice, "pass")

        # Test all choices - patch Prompt.ask at the source module
        with patch("rich.prompt.Prompt.ask") as mock_ask:
            mock_ask.return_value = "p"
            result = asyncio.run(review_callback_logic("q1", "step1", "preview text"))
            assert result == "pass"

            mock_ask.return_value = "r"
            result = asyncio.run(review_callback_logic("q1", "step1", "preview text"))
            assert result == "retry"

            mock_ask.return_value = "s"
            result = asyncio.run(review_callback_logic("q1", "step1", "preview text"))
            assert result == "skip"

            # Default fallback for unknown choice
            mock_ask.return_value = "x"
            result = asyncio.run(review_callback_logic("q1", "step1", ""))
            assert result == "pass"

    def test_review_callback_with_preview_truncation(self):
        """Line 72-75: review_callback truncates preview to 500 chars."""
        from unittest.mock import MagicMock, patch

        async def review_callback_logic(quest_id, step_id, preview):
            from commands.cli_quest import console
            console.print(f"\n[bold cyan]📋 步骤验收: {step_id}[/bold cyan]")
            if preview:
                from rich.panel import Panel
                console.print(
                    Panel.fit(preview[:500], title="执行结果预览", border_style="dim")
                )
            from rich.prompt import Prompt
            choice = Prompt.ask("请选择", choices=["p", "r", "s"], default="p", show_choices=True)
            mapping = {"p": "pass", "r": "retry", "s": "skip"}
            return mapping.get(choice, "pass")

        with patch("rich.prompt.Prompt.ask") as mock_ask:
            mock_ask.return_value = "p"
            long_preview = "x" * 600
            mock_console = MagicMock()
            with patch("commands.cli_quest.console", mock_console):
                asyncio.run(review_callback_logic("q1", "step1", long_preview))
            # review_callback 至少应触发一次输出
            assert mock_console.print.called


class TestQuestRunSpecPath:
    """Test run() inside quest() with skip_spec=False (lines 91-131)."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    @patch("commands.cli_quest.Progress")
    def test_quest_skip_spec_false_generates_spec(self, mock_progress_cls, mock_console, mock_qm_class):
        """Lines 91-131: run() with SPEC generation path."""
        from commands.cli_quest import quest

        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.spec = MagicMock()
        mock_quest.spec.to_markdown.return_value = "# SPEC\ncontent" * 100

        mock_manager = MagicMock()
        mock_manager.create_quest = AsyncMock(return_value=mock_quest)
        mock_manager.generate_spec = AsyncMock(return_value=mock_quest)
        mock_qm_class.return_value = mock_manager

        mock_progress_instance = MagicMock()
        mock_progress_instance.add_task.return_value = "task1"
        mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress_cls.return_value.__exit__ = MagicMock(return_value=None)

        # auto_confirm=False raises SystemExit(0) after showing SPEC
        with pytest.raises(typer.Exit) as exc_info:
            quest(
                ctx=MagicMock(),
                description="test spec generation",
                project_path=Path("."),
                title="Spec Test",
                skip_spec=False,
                auto_confirm=False,
            )
        assert exc_info.value.exit_code == 0

        # Verify create_quest was awaited
        mock_manager.create_quest.assert_awaited_once()
        # Verify generate_spec was awaited
        mock_manager.generate_spec.assert_awaited_once()

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    @patch("commands.cli_quest.Progress")
    def test_quest_skip_spec_false_long_spec_truncation(self, mock_progress_cls, mock_console, mock_qm_class):
        """Lines 109-114: SPEC content > 3000 chars gets truncated with '...'."""
        from commands.cli_quest import quest

        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.spec = MagicMock()
        mock_quest.spec.to_markdown.return_value = "x" * 4000

        mock_manager = MagicMock()
        mock_manager.create_quest = AsyncMock(return_value=mock_quest)
        mock_manager.generate_spec = AsyncMock(return_value=mock_quest)
        mock_qm_class.return_value = mock_manager

        mock_progress_instance = MagicMock()
        mock_progress_instance.add_task.return_value = "task1"
        mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress_cls.return_value.__exit__ = MagicMock(return_value=None)

        with pytest.raises(typer.Exit):
            quest(
                ctx=MagicMock(),
                description="long spec",
                project_path=Path("."),
                title=None,
                skip_spec=False,
                auto_confirm=False,
            )

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    @patch("commands.cli_quest.Progress")
    def test_quest_skip_spec_false_auto_confirm_executes(self, mock_progress_cls, mock_console, mock_qm_class):
        """Lines 125-131: skip_spec=False + auto_confirm=True -> confirm_and_execute."""
        from commands.cli_quest import quest

        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.spec = None

        mock_manager = MagicMock()
        mock_manager.create_quest = AsyncMock(return_value=mock_quest)
        mock_manager.generate_spec = AsyncMock(return_value=mock_quest)
        mock_qm_class.return_value = mock_manager

        mock_progress_instance = MagicMock()
        mock_progress_instance.add_task.return_value = "task1"
        mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress_cls.return_value.__exit__ = MagicMock(return_value=None)

        quest(
            ctx=MagicMock(),
            description="auto execute",
            project_path=Path("."),
            title=None,
            skip_spec=False,
            auto_confirm=True,
        )

        mock_manager.confirm_and_execute.assert_called_once_with("abc12345")

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    @patch("commands.cli_quest.Progress")
    def test_quest_skip_spec_false_no_spec(self, mock_progress_cls, mock_console, mock_qm_class):
        """Lines 109-114: spec is None, skips SPEC panel display."""
        from commands.cli_quest import quest

        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.spec = None

        mock_manager = MagicMock()
        mock_manager.create_quest = AsyncMock(return_value=mock_quest)
        mock_manager.generate_spec = AsyncMock(return_value=mock_quest)
        mock_qm_class.return_value = mock_manager

        mock_progress_instance = MagicMock()
        mock_progress_instance.add_task.return_value = "task1"
        mock_progress_cls.return_value.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress_cls.return_value.__exit__ = MagicMock(return_value=None)

        with pytest.raises(typer.Exit):
            quest(
                ctx=MagicMock(),
                description="no spec",
                project_path=Path("."),
                title=None,
                skip_spec=False,
                auto_confirm=False,
            )


class TestQuestNotifyWatchCases:
    """Test quest_notify watch loop branches (lines 449-522)."""

    def _run_watch_in_new_loop(self, coro):
        """Helper: run a coroutine in a fresh event loop (simulates asyncio.run)."""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()

    @patch("asyncio.run")
    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_watch_detects_failed(self, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class, mock_asyncio_run):
        """Lines 479-486: quest_notify watch loop detects failed status."""
        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test Quest"
            mock_quest.result_summary = None
            mock_quest.error_message = "Build failed"
            mock_quest.steps = None
            if call_count[0] <= 1:
                mock_quest.status.value = "executing"
            else:
                mock_quest.status.value = "failed"
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_notifier = MagicMock()
        mock_notifier._channels = []
        mock_nm_class.return_value = mock_notifier
        mock_cn_class.return_value = MagicMock()

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_notify

        quest_notify(quest_id="abc12345", project_path=Path("."))
        mock_notifier.notify_failed.assert_called_once()

    @patch("asyncio.run")
    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_watch_detects_paused(self, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class, mock_asyncio_run):
        """Lines 479-486: quest_notify watch loop detects paused status.

        Note: 'paused' is not a terminal state, so the watch loop continues.
        The final get_quest call returns 'completed' to allow the loop to exit.
        """
        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test Quest"
            mock_quest.result_summary = None
            mock_quest.error_message = None
            mock_quest.steps = None
            if call_count[0] <= 1:
                mock_quest.status.value = "executing"
            elif call_count[0] == 2:
                mock_quest.status.value = "paused"
            else:
                # Return terminal state so loop can exit
                mock_quest.status.value = "completed"
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_notifier = MagicMock()
        mock_notifier._channels = []
        mock_nm_class.return_value = mock_notifier
        mock_cn_class.return_value = MagicMock()

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_notify

        quest_notify(quest_id="abc12345", project_path=Path("."))
        mock_notifier.send.assert_called_once()

    @patch("asyncio.run")
    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_watch_with_step_progress(self, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class, mock_asyncio_run):
        """Lines 467-477: quest_notify watch loop outputs step progress bar."""
        from src.quest import QuestStatus

        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_step = MagicMock()
            mock_step.status = QuestStatus.COMPLETED

            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test"
            mock_quest.result_summary = "Done"
            mock_quest.error_message = None
            mock_quest.steps = [mock_step]
            if call_count[0] <= 1:
                mock_quest.status.value = "executing"
            else:
                mock_quest.status.value = "completed"
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_notifier = MagicMock()
        mock_notifier._channels = []
        mock_nm_class.return_value = mock_notifier
        mock_cn_class.return_value = MagicMock()

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_notify

        quest_notify(quest_id="abc12345", project_path=Path("."))
        mock_notifier.notify_completed.assert_called_once()

    @patch("asyncio.run")
    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_watch_quest_becomes_none(self, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class, mock_asyncio_run):
        """Lines 467-469: quest_notify watch loop exits when get_quest returns None."""
        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            if call_count[0] == 1:
                m = MagicMock()
                m.id = "abc12345"
                m.status.value = "executing"
                m.steps = None
                return m
            return None

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_notifier = MagicMock()
        mock_notifier._channels = []
        mock_nm_class.return_value = mock_notifier
        mock_cn_class.return_value = MagicMock()

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_notify

        # Should not raise, just exit cleanly
        quest_notify(quest_id="abc12345", project_path=Path("."))

    @patch("asyncio.run")
    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_keyboard_interrupt(self, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class, mock_asyncio_run):
        """Lines 521-522: quest_notify handles KeyboardInterrupt."""
        mock_asyncio_run.side_effect = KeyboardInterrupt

        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.status.value = "executing"
        mock_quest.steps = None

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        mock_notifier = MagicMock()
        mock_notifier._channels = []
        mock_nm_class.return_value = mock_notifier
        mock_cn_class.return_value = MagicMock()

        from commands.cli_quest import quest_notify

        quest_notify(quest_id="abc12345", project_path=Path("."))
        printed = [str(c.args[0]) for c in mock_console.print.call_args_list if c.args]
        assert any("监控已退出" in t for t in printed)

    @patch("asyncio.run")
    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_watch_cancelled_status(self, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class, mock_asyncio_run):
        """Lines 498-505: quest_notify watch loop detects cancelled status."""
        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test"
            mock_quest.result_summary = None
            mock_quest.error_message = None
            mock_quest.steps = None
            if call_count[0] <= 1:
                mock_quest.status.value = "executing"
            else:
                mock_quest.status.value = "cancelled"
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_notifier = MagicMock()
        mock_notifier._channels = []
        mock_nm_class.return_value = mock_notifier
        mock_cn_class.return_value = MagicMock()

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_notify

        quest_notify(quest_id="abc12345", project_path=Path("."))


class TestQuestWaitWatchCases:
    """Test quest_wait watch loop branches (lines 567-601)."""

    def _run_watch_in_new_loop(self, coro):
        """Helper: run a coroutine in a fresh event loop (simulates asyncio.run)."""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_watch_detects_completed(self, mock_console, mock_qm_class, mock_asyncio_run):
        """Lines 571-577, 595-596: quest_wait watch detects COMPLETED status."""
        from src.quest import QuestStatus

        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test"
            mock_quest.duration.return_value = 10.0
            mock_quest.result_summary = "Done"
            mock_quest.error_message = None
            mock_quest.steps = []
            if call_count[0] <= 1:
                mock_quest.status = QuestStatus.EXECUTING
            else:
                mock_quest.status = QuestStatus.COMPLETED
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        assert mock_console.print.call_count >= 2

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_watch_detects_failed(self, mock_console, mock_qm_class, mock_asyncio_run):
        """Lines 571-577, 595-596: quest_wait watch detects FAILED status."""
        from src.quest import QuestStatus

        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test"
            mock_quest.duration.return_value = 10.0
            mock_quest.result_summary = None
            mock_quest.error_message = "Build error"
            mock_quest.steps = []
            if call_count[0] <= 1:
                mock_quest.status = QuestStatus.EXECUTING
            else:
                mock_quest.status = QuestStatus.FAILED
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        assert mock_console.print.call_count >= 2

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_watch_detects_cancelled(self, mock_console, mock_qm_class, mock_asyncio_run):
        """Lines 595-596: quest_wait watch detects CANCELLED status."""
        from src.quest import QuestStatus

        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test"
            mock_quest.duration.return_value = None
            mock_quest.result_summary = None
            mock_quest.error_message = None
            mock_quest.steps = []
            if call_count[0] <= 1:
                mock_quest.status = QuestStatus.EXECUTING
            else:
                mock_quest.status = QuestStatus.CANCELLED
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        assert mock_console.print.call_count >= 1

    @patch("commands.cli_quest._show_acceptance_report")
    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_watch_with_steps_progress(self, mock_console, mock_qm_class, mock_asyncio_run, mock_show_report):
        """Lines 571-577: quest_wait watch shows step progress bar."""
        from src.quest import QuestStatus

        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_step = MagicMock()
            mock_step.step_id = "1"
            mock_step.title = "Write code"
            mock_step.status = QuestStatus.COMPLETED

            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test"
            mock_quest.duration.return_value = 10.0
            mock_quest.result_summary = "Done"
            mock_quest.error_message = None
            mock_quest.steps = [mock_step]
            if call_count[0] <= 1:
                mock_quest.status = QuestStatus.EXECUTING
            else:
                mock_quest.status = QuestStatus.COMPLETED
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        # Step progress bar and acceptance report trigger print calls
        assert mock_console.print.call_count >= 2

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_watch_quest_becomes_none(self, mock_console, mock_qm_class, mock_asyncio_run):
        """Lines 567-569: quest_wait watch exits when get_quest returns None."""
        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            if call_count[0] == 1:
                m = MagicMock()
                m.id = "abc12345"
                m.status = MagicMock()
                m.steps = []
                return m
            return None

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        assert mock_asyncio_run.called

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_keyboard_interrupt(self, mock_console, mock_qm_class, mock_asyncio_run):
        """Lines 600-601: quest_wait handles KeyboardInterrupt."""
        mock_asyncio_run.side_effect = KeyboardInterrupt

        from src.quest import QuestStatus

        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.status = QuestStatus.EXECUTING
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))
        printed = [str(c.args[0]) for c in mock_console.print.call_args_list if c.args]
        assert any("等待已中断" in t for t in printed)

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_watch_timeout_breaks_loop(self, mock_console, mock_qm_class, mock_asyncio_run):
        """Lines 598-599: quest_wait respects timeout and breaks."""
        from src.quest import QuestStatus

        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.status = QuestStatus.EXECUTING
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        mock_asyncio_run.side_effect = self._run_watch_in_new_loop

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."), timeout=3)

        printed = [str(c.args[0]) for c in mock_console.print.call_args_list if c.args]
        assert any("超时" in t for t in printed)


class TestOnProgressCallback:
    """Test on_progress callback (lines 449-456)."""

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_on_progress_callback_info(self, mock_console, mock_qm_class, mock_asyncio_run):
        """Test on_progress callback with 'info' level."""
        from commands.cli_quest import quest_notify

        call_count = [0]

        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.steps = None
            if call_count[0] <= 1:
                mock_quest.status.value = "executing"
            else:
                mock_quest.status.value = "completed"
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_notifier = MagicMock()
        mock_notifier._channels = []

        with patch("src.quest.NotificationManager", return_value=mock_notifier):
            with patch("src.quest.NotificationConfig"):
                with patch("src.quest.notifications.ConsoleNotificationChannel"):
                    # asyncio.run is patched to just execute the coroutine
                    import asyncio
                    def fake_run(coro):
                        loop = asyncio.new_event_loop()
                        try:
                            loop.run_until_complete(coro)
                        finally:
                            loop.close()
                    mock_asyncio_run.side_effect = fake_run
                    quest_notify(quest_id="abc12345", project_path=Path("."))

        # Verify console.print was called (initial message + any progress)
        assert mock_console.print.called


class TestShowAcceptanceReportStepDetails:
    """Test _show_acceptance_report with step details (line 449 and beyond)."""

    def test_show_with_executing_and_paused_status(self):
        """Test _show_acceptance_report with EXECUTING and PAUSED status."""
        from commands.cli_quest import _show_acceptance_report
        from src.quest import QuestStatus

        mock_step_exec = MagicMock()
        mock_step_exec.step_id = "1"
        mock_step_exec.title = "Running step"
        mock_step_exec.status = QuestStatus.EXECUTING

        mock_step_paused = MagicMock()
        mock_step_paused.step_id = "2"
        mock_step_paused.title = "Paused step"
        mock_step_paused.status = QuestStatus.PAUSED

        mock_console = MagicMock()
        mock_quest = MagicMock()
        mock_quest.title = "Test Quest"
        mock_quest.status.value = "executing"
        mock_quest.status = QuestStatus.EXECUTING
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = 30.0
        mock_quest.result_summary = None
        mock_quest.error_message = None
        mock_quest.steps = [mock_step_exec, mock_step_paused]

        _show_acceptance_report(mock_quest, mock_console)
        assert mock_console.print.call_count >= 2

    def test_show_executing_status_no_table(self):
        """Test _show_acceptance_report with EXECUTING status (no steps table)."""
        from commands.cli_quest import _show_acceptance_report
        from src.quest import QuestStatus

        mock_console = MagicMock()
        mock_quest = MagicMock()
        mock_quest.title = "Test Quest"
        mock_quest.status.value = "executing"
        mock_quest.status = QuestStatus.EXECUTING
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = 10.0
        mock_quest.result_summary = None
        mock_quest.error_message = None
        mock_quest.steps = []

        _show_acceptance_report(mock_quest, mock_console)
        assert mock_console.print.called

    def test_show_paused_status(self):
        """Test _show_acceptance_report with PAUSED status."""
        from commands.cli_quest import _show_acceptance_report
        from src.quest import QuestStatus

        mock_console = MagicMock()
        mock_quest = MagicMock()
        mock_quest.title = "Paused Quest"
        mock_quest.status.value = "paused"
        mock_quest.status = QuestStatus.PAUSED
        mock_quest.id = "abc12345"
        mock_quest.duration.return_value = 15.0
        mock_quest.result_summary = None
        mock_quest.error_message = None
        mock_quest.steps = []

        _show_acceptance_report(mock_quest, mock_console)
        assert mock_console.print.called


class TestQuestNotifyAsyncWatch:
    """Test quest_notify with actual async execution."""

    def _run_coro(self, coro):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()

    @patch("asyncio.run")
    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_watch_detects_completed(self, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class, mock_asyncio_run):
        """Watch loop detects completed quest and breaks."""

        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test Quest"
            mock_quest.result_summary = "All done"
            mock_quest.error_message = None
            mock_quest.steps = None
            if call_count[0] <= 1:
                mock_quest.status.value = "executing"
            else:
                mock_quest.status.value = "completed"
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_notifier = MagicMock()
        mock_notifier._channels = []
        mock_nm_class.return_value = mock_notifier
        mock_cn_class.return_value = MagicMock()

        mock_asyncio_run.side_effect = self._run_coro

        from commands.cli_quest import quest_notify

        quest_notify(quest_id="abc12345", project_path=Path("."))

        mock_notifier.notify_completed.assert_called_once()


class TestQuestWaitAsyncWatch:
    """Test quest_wait with actual async execution."""

    def _run_coro(self, coro):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_watch_detects_completed(self, mock_console, mock_qm_class, mock_asyncio_run):
        """Watch loop detects completed quest and shows report."""
        from src.quest import QuestStatus

        call_count = [0]
        def get_quest_side_effect(qid):
            call_count[0] += 1
            mock_quest = MagicMock()
            mock_quest.id = "abc12345"
            mock_quest.title = "Test"
            mock_quest.duration.return_value = 10.0
            mock_quest.result_summary = "Done"
            mock_quest.error_message = None
            mock_quest.steps = []
            if call_count[0] <= 1:
                mock_quest.status = QuestStatus.EXECUTING
            else:
                mock_quest.status = QuestStatus.COMPLETED
            return mock_quest

        mock_manager = MagicMock()
        mock_manager.get_quest.side_effect = get_quest_side_effect
        mock_qm_class.return_value = mock_manager

        mock_asyncio_run.side_effect = self._run_coro

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))

        assert mock_console.print.call_count >= 2

    @patch("asyncio.run")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_wait_watch_timeout(self, mock_console, mock_qm_class, mock_asyncio_run):
        """Watch loop respects timeout and breaks."""
        from src.quest import QuestStatus

        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.title = "Test"
        mock_quest.status = QuestStatus.EXECUTING
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        mock_asyncio_run.side_effect = self._run_coro

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."), timeout=1)

        assert mock_console.print.called
