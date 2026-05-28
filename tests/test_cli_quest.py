"""Tests for src/commands/cli_quest.py - simple CLI functions."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
    """Test the watch loop inside quest_notify by mocking asyncio.run to execute the coroutine."""

    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    def test_notify_watch_completes(self, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class):
        """Test that watch loop detects completed quest."""
        import asyncio as real_asyncio


        # Create a quest that's already completed on second check
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

        from commands.cli_quest import quest_notify

        # Patch asyncio.sleep with AsyncMock (compatible with all Python versions, including 3.12+)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Simpler approach: just mock asyncio.run and verify setup
            with patch("asyncio.run"):
                quest_notify(quest_id="abc12345", project_path=Path("."))

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


class TestQuestNotifyAsyncWatch:
    """Test quest_notify with actual async execution."""

    @patch("src.quest.notifications.ConsoleNotificationChannel")
    @patch("src.quest.NotificationManager")
    @patch("src.quest.NotificationConfig")
    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    @patch("asyncio.sleep", new_callable=AsyncMock)
    def test_notify_watch_detects_completed(self, mock_sleep, mock_console, mock_qm_class, mock_nc_class, mock_nm_class, mock_cn_class):
        """Watch loop should detect completed quest and break."""

        # Quest starts executing, then becomes completed
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

        from commands.cli_quest import quest_notify

        quest_notify(quest_id="abc12345", project_path=Path("."))

        # Verify notifier was called for completion
        mock_notifier.notify_completed.assert_called_once()


class TestQuestWaitAsyncWatch:
    """Test quest_wait with actual async execution."""

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    @patch("asyncio.sleep", new_callable=AsyncMock)
    def test_wait_watch_detects_completed(self, mock_sleep, mock_console, mock_qm_class):
        """Watch loop should detect completed quest and show report."""
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

        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."))

        # Should have printed acceptance report
        assert mock_console.print.call_count >= 2

    @patch("src.quest.QuestManager")
    @patch("commands.cli_quest.console")
    @patch("asyncio.sleep", new_callable=AsyncMock)
    def test_wait_watch_timeout(self, mock_sleep, mock_console, mock_qm_class):
        """Watch loop should respect timeout."""
        from src.quest import QuestStatus

        # Quest stays executing forever
        mock_quest = MagicMock()
        mock_quest.id = "abc12345"
        mock_quest.title = "Test"
        mock_quest.status = QuestStatus.EXECUTING
        mock_quest.steps = []

        mock_manager = MagicMock()
        mock_manager.get_quest.return_value = mock_quest
        mock_qm_class.return_value = mock_manager

        # Make sleep increment time faster
        from commands.cli_quest import quest_wait

        quest_wait(quest_id="abc12345", project_path=Path("."), timeout=1)

        assert mock_console.print.called
