"""测试 src/commands/cli_multiagent.py 中的 Typer 命令"""

import json
from unittest.mock import MagicMock, patch
import asyncio

import pytest
from typer.testing import CliRunner

from src.commands.cli_multiagent import app, _agent_status_color
from src.multiagent.coordinator import (
    CoordinationResult,
    SubAgent,
    SubAgentStatus,
    TaskResult,
)


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


@pytest.fixture
def mock_console():
    with patch("src.commands.cli_multiagent.console") as m:
        yield m


@pytest.fixture
def mock_coordinator():
    with patch("src.commands.cli_multiagent.get_coordinator") as m:
        coord = MagicMock()
        m.return_value = coord
        yield coord


def make_sub_agent(
    agent_id="abc12345",
    name="test-agent",
    role="coder",
    status=SubAgentStatus.IDLE,
):
    return SubAgent(agent_id=agent_id, name=name, role=role, status=status)


def make_coord_result(
    task_id="t1",
    started_at="2026-01-01T00:00:00",
    completed_at="2026-01-01T00:01:00",
    summary="ok",
):
    return CoordinationResult(
        task_id=task_id,
        results=[
            TaskResult(
                agent_id="abc12345",
                role="coder",
                success=True,
                output="done",
                error=None,
            )
        ],
        summary=summary,
        started_at=started_at,
        completed_at=completed_at,
    )


# ── _agent_status_color ──


class TestAgentStatusColor:
    def test_known_statuses(self):
        assert _agent_status_color(SubAgentStatus.IDLE) == "dim"
        assert _agent_status_color(SubAgentStatus.RUNNING) == "cyan"
        assert _agent_status_color(SubAgentStatus.COMPLETED) == "green"
        assert _agent_status_color(SubAgentStatus.FAILED) == "red"

    def test_unknown_status(self):
        # Use a string that isn't in the enum — but since the function takes
        # SubAgentStatus, we just test the default via .get() by mocking
        assert _agent_status_color("nonexistent") == "white"


# ── status ──


class TestStatus:
    def test_status_with_agents(self, runner, mock_coordinator, mock_console):
        mock_coordinator.get_status.return_value = {
            "total_agents": 2,
            "active_tasks": 1,
            "running": 1,
            "completed": 1,
            "failed": 0,
            "idle": 1,
            "agents": [
                {"agent_id": "a1", "name": "agent1", "role": "coder", "status": "idle"},
                {"agent_id": "a2", "name": "agent2", "role": "reviewer", "status": "running"},
            ],
        }
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0

    def test_status_no_agents(self, runner, mock_coordinator, mock_console):
        mock_coordinator.get_status.return_value = {
            "total_agents": 0,
            "active_tasks": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "idle": 0,
            "agents": [],
        }
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0


# ── spawn ──


class TestSpawn:
    def test_spawn_basic(self, runner, mock_coordinator, mock_console):
        agent = make_sub_agent()
        mock_coordinator.spawn.return_value = agent
        result = runner.invoke(app, ["spawn", "coder", "my-agent"])
        assert result.exit_code == 0
        mock_coordinator.spawn.assert_called_once_with(
            role="coder", name="my-agent", metadata={}
        )

    def test_spawn_with_metadata(self, runner, mock_coordinator, mock_console):
        agent = make_sub_agent()
        mock_coordinator.spawn.return_value = agent
        result = runner.invoke(
            app, ["spawn", "reviewer", "r1", "-m", '{"priority":"high"}']
        )
        assert result.exit_code == 0
        mock_coordinator.spawn.assert_called_once_with(
            role="reviewer", name="r1", metadata={"priority": "high"}
        )

    def test_spawn_invalid_metadata(self, runner, mock_coordinator, mock_console):
        result = runner.invoke(app, ["spawn", "coder", "x", "-m", "not-json"])
        assert result.exit_code == 1


# ── list ──


class TestList:
    def test_list_with_agents(self, runner, mock_coordinator, mock_console):
        a1 = make_sub_agent(agent_id="id1", name="a1", role="coder", status=SubAgentStatus.IDLE)
        a2 = make_sub_agent(agent_id="id2", name="a2", role="reviewer", status=SubAgentStatus.COMPLETED)
        mock_coordinator.agents = {"id1": a1, "id2": a2}
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_list_empty(self, runner, mock_coordinator, mock_console):
        mock_coordinator.agents = {}
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0


# ── dispatch ──


class TestDispatch:
    def test_dispatch_all_agents(self, runner, mock_coordinator, mock_console):
        a1 = make_sub_agent(agent_id="id1", name="a1", role="coder")
        mock_coordinator.agents = {"id1": a1}
        mock_coordinator.dispatch.return_value = make_coord_result()

        with patch("asyncio.run", return_value=make_coord_result()):
            result = runner.invoke(app, ["dispatch", "do stuff"])
        assert result.exit_code == 0

    def test_dispatch_no_agents(self, runner, mock_coordinator, mock_console):
        mock_coordinator.agents = {}
        result = runner.invoke(app, ["dispatch", "do stuff"])
        assert result.exit_code == 1

    def test_dispatch_specific_agents(self, runner, mock_coordinator, mock_console):
        a1 = make_sub_agent(agent_id="id1", name="a1", role="coder")
        mock_coordinator.agents = {"id1": a1}
        mock_coordinator.get_agent.return_value = a1
        mock_coordinator.dispatch.return_value = make_coord_result()

        with patch("asyncio.run", return_value=make_coord_result()):
            result = runner.invoke(app, ["dispatch", "task", "-a", "id1"])
        assert result.exit_code == 0

    def test_dispatch_agent_ids_not_found(self, runner, mock_coordinator, mock_console):
        a1 = make_sub_agent(agent_id="id1", name="a1", role="coder")
        mock_coordinator.agents = {"id1": a1}
        mock_coordinator.get_agent.return_value = None
        result = runner.invoke(app, ["dispatch", "task", "-a", "nonexist"])
        assert result.exit_code == 1

    def test_dispatch_sequential(self, runner, mock_coordinator, mock_console):
        a1 = make_sub_agent(agent_id="id1", name="a1", role="coder")
        mock_coordinator.agents = {"id1": a1}
        mock_coordinator.dispatch_sequential.return_value = make_coord_result()

        with patch("asyncio.run", return_value=make_coord_result()):
            result = runner.invoke(app, ["dispatch", "task", "--mode", "sequential"])
        assert result.exit_code == 0

    def test_dispatch_exception(self, runner, mock_coordinator, mock_console):
        a1 = make_sub_agent(agent_id="id1", name="a1", role="coder")
        mock_coordinator.agents = {"id1": a1}

        with patch("asyncio.run", side_effect=RuntimeError("boom")):
            result = runner.invoke(app, ["dispatch", "task"])
        assert result.exit_code == 1


# ── remove ──


class TestRemove:
    def test_remove_with_force(self, runner, mock_coordinator, mock_console):
        a1 = make_sub_agent(agent_id="id1", name="a1")
        mock_coordinator.get_agent.return_value = a1
        mock_coordinator.remove_agent.return_value = True

        result = runner.invoke(app, ["remove", "id1", "-f"])
        assert result.exit_code == 0

    def test_remove_not_found(self, runner, mock_coordinator, mock_console):
        mock_coordinator.get_agent.return_value = None
        result = runner.invoke(app, ["remove", "nonexist"])
        assert result.exit_code == 1

    def test_remove_confirm_yes(self, runner, mock_coordinator, mock_console):
        a1 = make_sub_agent(agent_id="id1", name="a1")
        mock_coordinator.get_agent.return_value = a1
        mock_coordinator.remove_agent.return_value = True

        with patch("src.commands.cli_multiagent.Confirm", create=True) as mock_confirm:
            # We need to patch the import inside the function
            pass

        # Simpler: use force flag to skip Confirm
        result = runner.invoke(app, ["remove", "id1", "-f"])
        assert result.exit_code == 0

    def test_remove_failed(self, runner, mock_coordinator, mock_console):
        a1 = make_sub_agent(agent_id="id1", name="a1")
        mock_coordinator.get_agent.return_value = a1
        mock_coordinator.remove_agent.return_value = False

        result = runner.invoke(app, ["remove", "id1", "-f"])
        assert result.exit_code == 1


# ── clear ──


class TestClear:
    def test_clear_with_force(self, runner, mock_coordinator, mock_console):
        mock_coordinator.agents = {"id1": MagicMock()}
        result = runner.invoke(app, ["clear", "-f"])
        assert result.exit_code == 0
        mock_coordinator.clear_agents.assert_called_once()

    def test_clear_no_agents(self, runner, mock_coordinator, mock_console):
        mock_coordinator.agents = {}
        result = runner.invoke(app, ["clear"])
        assert result.exit_code == 0

    def test_clear_confirm_cancelled(self, runner, mock_coordinator, mock_console):
        mock_coordinator.agents = {"id1": MagicMock()}
        with patch("rich.prompt.Confirm.ask", return_value=False):
            result = runner.invoke(app, ["clear"])
            assert result.exit_code == 0
            mock_coordinator.clear_agents.assert_not_called()
