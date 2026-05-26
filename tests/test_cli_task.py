"""Tests for src/commands/cli_task.py"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.commands.cli_task import (
    _status_color,
    _status_emoji,
    app,
)
from src.state.task_state import StepRecord, TaskState, TaskStatus

runner = CliRunner()


def _make_task(
    task_id: str = "abc123",
    status: TaskStatus = TaskStatus.RUNNING,
    progress: float = 0.5,
    current_step: str = "doing stuff",
    steps: list[StepRecord] | None = None,
    error: str | None = None,
    artifacts: dict[str, Any] | None = None,
) -> TaskState:
    now = datetime.now().isoformat()
    return TaskState(
        task_id=task_id,
        status=status,
        created_at=now,
        updated_at=now,
        progress=progress,
        current_step=current_step,
        steps=steps or [],
        error=error,
        artifacts=artifacts or {},
    )


# ── helpers ──────────────────────────────────────────────────


class TestStatusHelpers:
    def test_status_color_all(self) -> None:
        colors = {_status_color(s) for s in TaskStatus}
        assert colors == {"dim", "cyan", "yellow", "green", "red"}

    def test_status_color_unknown(self) -> None:
        mock = MagicMock()
        mock.value = "unknown"
        assert _status_color(mock) == "white"

    def test_status_emoji_all(self) -> None:
        emojis = {_status_emoji(s) for s in TaskStatus}
        assert emojis == {"⏳", "🔄", "⏸️", "✅", "❌"}

    def test_status_emoji_unknown(self) -> None:
        mock = MagicMock()
        mock.value = "unknown"
        assert _status_emoji(mock) == "❓"


# ── task list ────────────────────────────────────────────────


@patch("src.commands.cli_task.list_tasks")
def test_task_list_empty(mock_list: MagicMock) -> None:
    mock_list.return_value = []
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "暂无任务" in result.output


@patch("src.commands.cli_task.list_tasks")
def test_task_list_with_tasks(mock_list: MagicMock) -> None:
    mock_list.return_value = [
        _make_task(task_id="t1", status=TaskStatus.RUNNING),
        _make_task(task_id="t2", status=TaskStatus.COMPLETED),
    ]
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "t1" in result.output
    assert "t2" in result.output
    assert "50%" in result.output


@patch("src.commands.cli_task.list_tasks")
def test_task_list_long_step_truncated(mock_list: MagicMock) -> None:
    mock_list.return_value = [
        _make_task(current_step="x" * 60),
    ]
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "\u2026" in result.output


@patch("src.commands.cli_task.list_tasks")
def test_task_list_limit(mock_list: MagicMock) -> None:
    mock_list.return_value = [_make_task(task_id=f"t{i}") for i in range(5)]
    result = runner.invoke(app, ["list", "-n", "2"])
    assert result.exit_code == 0
    assert "任务列表 (2)" in result.output


@patch("src.commands.cli_task.list_tasks")
def test_task_list_invalid_status(mock_list: MagicMock) -> None:
    result = runner.invoke(app, ["list", "--status", "oops"])
    assert result.exit_code == 1
    assert "无效状态" in result.output


@patch("src.commands.cli_task.list_tasks")
def test_task_list_status_filter(mock_list: MagicMock) -> None:
    mock_list.return_value = [_make_task(status=TaskStatus.FAILED)]
    result = runner.invoke(app, ["list", "--status", "failed"])
    assert result.exit_code == 0
    assert "t1" not in result.output  # uses abc123 default
    mock_list.assert_called_once_with(TaskStatus.FAILED)


# ── task status ──────────────────────────────────────────────


@patch("src.commands.cli_task.get_task")
def test_task_status_not_found(mock_get: MagicMock) -> None:
    mock_get.return_value = None
    result = runner.invoke(app, ["status", "nope"])
    assert result.exit_code == 1
    assert "任务不存在" in result.output


@patch("src.commands.cli_task.get_task")
def test_task_status_found(mock_get: MagicMock) -> None:
    mock_get.return_value = _make_task(progress=0.75)
    result = runner.invoke(app, ["status", "abc123"])
    assert result.exit_code == 0
    assert "75.0%" in result.output
    assert "doing stuff" in result.output


@patch("src.commands.cli_task.get_task")
def test_task_status_with_error(mock_get: MagicMock) -> None:
    mock_get.return_value = _make_task(error="boom", status=TaskStatus.FAILED)
    result = runner.invoke(app, ["status", "abc123"])
    assert result.exit_code == 0
    assert "boom" in result.output


@patch("src.commands.cli_task.get_task")
def test_task_status_with_artifacts(mock_get: MagicMock) -> None:
    mock_get.return_value = _make_task(artifacts={"a": 1})
    result = runner.invoke(app, ["status", "abc123"])
    assert result.exit_code == 0
    assert "产物数" in result.output


@patch("src.commands.cli_task.get_task")
def test_task_status_verbose(mock_get: MagicMock) -> None:
    ts = "2026-01-01T12:30:00"
    mock_get.return_value = TaskState(
        task_id="abc123",
        status=TaskStatus.COMPLETED,
        created_at=ts,
        updated_at=ts,
        steps=[
            StepRecord(step="step1", result="ok", timestamp=ts),
            StepRecord(step="step2", result="x" * 120, timestamp=ts),
        ],
    )
    result = runner.invoke(app, ["status", "abc123", "-v"])
    assert result.exit_code == 0
    assert "执行步骤" in result.output
    assert "..." in result.output  # long result truncated


@patch("src.commands.cli_task.get_task")
def test_task_status_no_current_step(mock_get: MagicMock) -> None:
    mock_get.return_value = _make_task(current_step="")
    result = runner.invoke(app, ["status", "abc123"])
    assert result.exit_code == 0
    assert "无" in result.output


# ── task pause ───────────────────────────────────────────────


@patch("src.commands.cli_task.pause_task")
@patch("src.commands.cli_task.get_task")
def test_task_pause_not_found(mock_get: MagicMock, mock_pause: MagicMock) -> None:
    mock_get.return_value = None
    result = runner.invoke(app, ["pause", "nope"])
    assert result.exit_code == 1


@patch("src.commands.cli_task.pause_task")
@patch("src.commands.cli_task.get_task")
def test_task_pause_already_paused(mock_get: MagicMock, mock_pause: MagicMock) -> None:
    mock_get.return_value = _make_task(status=TaskStatus.PAUSED)
    result = runner.invoke(app, ["pause", "abc123"])
    assert result.exit_code == 0
    assert "已经是暂停状态" in result.output
    mock_pause.assert_not_called()


@patch("src.commands.cli_task.pause_task")
@patch("src.commands.cli_task.get_task")
def test_task_pause_wrong_status(mock_get: MagicMock, mock_pause: MagicMock) -> None:
    mock_get.return_value = _make_task(status=TaskStatus.COMPLETED)
    result = runner.invoke(app, ["pause", "abc123"])
    assert result.exit_code == 1
    assert "无法暂停" in result.output
    mock_pause.assert_not_called()


@patch("src.commands.cli_task.pause_task")
@patch("src.commands.cli_task.get_task")
def test_task_pause_success(mock_get: MagicMock, mock_pause: MagicMock) -> None:
    mock_get.return_value = _make_task(status=TaskStatus.RUNNING)
    mock_pause.return_value = True
    result = runner.invoke(app, ["pause", "abc123"])
    assert result.exit_code == 0
    assert "已暂停" in result.output


@patch("src.commands.cli_task.pause_task")
@patch("src.commands.cli_task.get_task")
def test_task_pause_fail(mock_get: MagicMock, mock_pause: MagicMock) -> None:
    mock_get.return_value = _make_task(status=TaskStatus.RUNNING)
    mock_pause.return_value = False
    result = runner.invoke(app, ["pause", "abc123"])
    assert result.exit_code == 1
    assert "暂停失败" in result.output


@patch("src.commands.cli_task.pause_task")
@patch("src.commands.cli_task.get_task")
def test_task_pause_pending_ok(mock_get: MagicMock, mock_pause: MagicMock) -> None:
    mock_get.return_value = _make_task(status=TaskStatus.PENDING)
    mock_pause.return_value = True
    result = runner.invoke(app, ["pause", "abc123"])
    assert result.exit_code == 0
    assert "已暂停" in result.output


# ── task resume ──────────────────────────────────────────────


@patch("src.commands.cli_task.resume_task")
@patch("src.commands.cli_task.get_task")
def test_task_resume_not_found(mock_get: MagicMock, mock_resume: MagicMock) -> None:
    mock_get.return_value = None
    result = runner.invoke(app, ["resume", "nope"])
    assert result.exit_code == 1


@patch("src.commands.cli_task.resume_task")
@patch("src.commands.cli_task.get_task")
def test_task_resume_not_paused(mock_get: MagicMock, mock_resume: MagicMock) -> None:
    mock_get.return_value = _make_task(status=TaskStatus.RUNNING)
    result = runner.invoke(app, ["resume", "abc123"])
    assert result.exit_code == 0
    assert "不是暂停状态" in result.output
    mock_resume.assert_not_called()


@patch("src.commands.cli_task.resume_task")
@patch("src.commands.cli_task.get_task")
def test_task_resume_success(mock_get: MagicMock, mock_resume: MagicMock) -> None:
    mock_get.return_value = _make_task(status=TaskStatus.PAUSED, current_step="step3")
    mock_resume.return_value = True
    result = runner.invoke(app, ["resume", "abc123"])
    assert result.exit_code == 0
    assert "已恢复" in result.output
    assert "step3" in result.output


@patch("src.commands.cli_task.resume_task")
@patch("src.commands.cli_task.get_task")
def test_task_resume_fail(mock_get: MagicMock, mock_resume: MagicMock) -> None:
    mock_get.return_value = _make_task(status=TaskStatus.PAUSED)
    mock_resume.return_value = False
    result = runner.invoke(app, ["resume", "abc123"])
    assert result.exit_code == 1
    assert "恢复失败" in result.output


@patch("src.commands.cli_task.resume_task")
@patch("src.commands.cli_task.get_task")
def test_task_resume_no_current_step(mock_get: MagicMock, mock_resume: MagicMock) -> None:
    mock_get.return_value = _make_task(status=TaskStatus.PAUSED, current_step="")
    mock_resume.return_value = True
    result = runner.invoke(app, ["resume", "abc123"])
    assert result.exit_code == 0
    assert "任务开始" in result.output


# ── task delete ──────────────────────────────────────────────


@patch("src.commands.cli_task.delete_task")
@patch("src.commands.cli_task.get_task")
def test_task_delete_not_found(mock_get: MagicMock, mock_delete: MagicMock) -> None:
    mock_get.return_value = None
    result = runner.invoke(app, ["delete", "nope"])
    assert result.exit_code == 1


@patch("src.commands.cli_task.delete_task")
@patch("src.commands.cli_task.get_task")
def test_task_delete_force(mock_get: MagicMock, mock_delete: MagicMock) -> None:
    mock_get.return_value = _make_task()
    mock_delete.return_value = True
    result = runner.invoke(app, ["delete", "abc123", "--force"])
    assert result.exit_code == 0
    assert "已删除" in result.output
    mock_delete.assert_called_once_with("abc123")


@patch("src.commands.cli_task.delete_task")
@patch("src.commands.cli_task.get_task")
def test_task_delete_force_fail(mock_get: MagicMock, mock_delete: MagicMock) -> None:
    mock_get.return_value = _make_task()
    mock_delete.return_value = False
    result = runner.invoke(app, ["delete", "abc123", "-f"])
    assert result.exit_code == 1
    assert "删除失败" in result.output


@patch("src.commands.cli_task.delete_task")
@patch("src.commands.cli_task.get_task")
def test_task_delete_cancelled(mock_get: MagicMock, mock_delete: MagicMock) -> None:
    mock_get.return_value = _make_task()
    # CliRunner doesn't support interactive prompts well; simulate with input "n"
    result = runner.invoke(app, ["delete", "abc123"], input="n\n")
    assert result.exit_code == 0
    assert "已取消" in result.output or "取消" in result.output
    mock_delete.assert_not_called()
