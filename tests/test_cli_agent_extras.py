"""
Edge-case tests for cli_agent.py — covering remaining uncovered paths.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

import pytest
from typer.testing import CliRunner

from src.commands.cli_agent import app


@pytest.fixture
def runner():
    """Create Typer CliRunner."""
    return CliRunner()


@pytest.fixture
def mock_console():
    """Mock cli_agent console."""
    with patch("src.commands.cli_agent.console") as m:
        yield m


class TestMonorepoNoSubprojects:
    """Cover lines 74-75: monorepo with no subprojects."""

    @patch("src.agents.base.list_all_agents")
    @patch("src.core.monorepo.detect_monorepo")
    @patch("src.core.monorepo.list_subprojects")
    def test_list_monorepo_no_subprojects(
        self, mock_list_sub, mock_detect, mock_list_all, runner, mock_console
    ):
        """monorepo detected but no subprojects found."""
        mock_list_all.return_value = []
        mock_info = Mock()
        mock_info.root = Path("/test")
        mock_info.type = "pnpm"
        mock_detect.return_value = mock_info
        mock_list_sub.return_value = []

        result = runner.invoke(app, ["list", "--monorepo"])

        assert result.exit_code == 0
        mock_console.print.assert_any_call("[dim]未检测到子项目[/dim]")


class TestExportWithPatterns:
    """Cover lines 218-228, 250: export with include_patterns."""

    @patch("src.commands.cli_agent.Path.home")
    @patch("src.agents.evolution.EvolutionStore")
    @patch("src.agents.base.get_agent")
    def test_export_with_patterns(
        self, mock_get_agent, mock_evo_store_cls, mock_home, runner, mock_console, tmp_path
    ):
        """Export agent with --patterns flag."""
        # Setup agent
        mock_agent = Mock()
        mock_agent.name = "test-agent"
        mock_agent.description = "test"
        mock_agent.model = "deepseek"
        mock_agent.temperature = 0.7
        mock_agent.max_tokens = 8000
        mock_agent.timeout = 60
        type(mock_agent).lane = Mock(value="code")
        mock_agent.default_tier = "smart"
        mock_agent.icon = "🤖"
        mock_agent.tools = ["tool1"]
        mock_agent.system_prompt = "You are helpful."
        mock_agent.format_name_for_export.return_value = "test-agent"
        mock_get_agent.return_value = mock_agent

        # Mock evolution store
        mock_store = Mock()
        mock_store.load_success_patterns.return_value = []
        mock_evo_store_cls.return_value = mock_store

        # Setup home dir with state
        mock_home.return_value = Path("/mock/home")

        output_file = tmp_path / "export.json"

        result = runner.invoke(app, ["export", "test-agent", "-o", str(output_file), "--patterns"])

        assert result.exit_code == 0

    @patch("src.commands.cli_agent.Path.home")
    @patch("src.agents.evolution.EvolutionStore")
    @patch("src.agents.base.get_agent")
    def test_export_with_patterns_and_evolution(
        self, mock_get_agent, mock_evo_store_cls, mock_home, runner, mock_console, tmp_path
    ):
        """Export agent with both --patterns and --evolution flags."""
        mock_agent = Mock()
        mock_agent.name = "test-agent"
        mock_agent.description = "test"
        mock_agent.model = "deepseek"
        mock_agent.temperature = 0.7
        mock_agent.max_tokens = 8000
        mock_agent.timeout = 60
        type(mock_agent).lane = Mock(value="code")
        mock_agent.default_tier = "smart"
        mock_agent.icon = "🤖"
        mock_agent.tools = ["tool1"]
        mock_agent.system_prompt = "You are helpful."
        mock_agent.format_name_for_export.return_value = "test-agent"
        mock_get_agent.return_value = mock_agent

        mock_store = Mock()
        mock_store.load_evolution_history.return_value = []
        mock_store.load_success_patterns.return_value = []
        mock_evo_store_cls.return_value = mock_store
        mock_home.return_value = Path("/mock/home")

        output_file = tmp_path / "export.json"

        result = runner.invoke(app, ["export", "test-agent", "-o", str(output_file), "--evolution", "--patterns"])

        assert result.exit_code == 0


class TestImportWithEvolutionAndPatterns:
    """Cover lines 322-355: import with evolution_history and success_patterns."""

    @patch("src.commands.cli_agent.Path.home")
    @patch("src.agents.evolution.EvolutionStore")
    @patch("src.agents.evolution.EvolutionRecord")
    @patch("src.agents.base.register_agent")
    def test_import_with_evolution_history(
        self, mock_register, mock_evo_record_cls, mock_evo_store_cls, mock_home,
        runner, mock_console, tmp_path
    ):
        """Import agent config with evolution_history."""
        mock_register.return_value = Mock()
        mock_store = Mock()
        mock_store.save_evolution_record.return_value = None
        mock_evo_store_cls.return_value = mock_store
        mock_evo_record_cls.return_value = Mock()
        mock_home.return_value = Path("/mock/home")

        config = {
            "name": "test-agent",
            "description": "test",
            "model": "deepseek",
            "temperature": 0.7,
            "max_tokens": 8000,
            "timeout": 60,
            "lane": "code",
            "default_tier": "smart",
            "icon": "🤖",
            "tools": ["tool1"],
            "system_prompt": "You are helpful.",
            "evolution_history": [
                {"id": "ev-1", "timestamp": "2024-01-01", "generation": 1, "changes": []}
            ],
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config), encoding="utf-8")

        result = runner.invoke(app, ["import", str(config_file)])

        assert result.exit_code == 0

    @patch("src.commands.cli_agent.Path.home")
    @patch("src.agents.evolution.EvolutionStore")
    @patch("src.agents.base.register_agent")
    def test_import_with_success_patterns(
        self, mock_register, mock_evo_store_cls, mock_home, runner, mock_console, tmp_path
    ):
        """Import agent config with success_patterns."""
        mock_register.return_value = Mock()
        mock_store = Mock()
        mock_store.add_success_pattern.return_value = None
        mock_evo_store_cls.return_value = mock_store
        mock_home.return_value = Path("/mock/home")

        config = {
            "name": "test-agent",
            "description": "test",
            "model": "deepseek",
            "temperature": 0.7,
            "max_tokens": 8000,
            "timeout": 60,
            "lane": "code",
            "default_tier": "smart",
            "icon": "🤖",
            "tools": ["tool1"],
            "system_prompt": "You are helpful.",
            "success_patterns": [
                {"pattern_type": "bug_fix", "description": "Fix timeout"}
            ],
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config), encoding="utf-8")

        result = runner.invoke(app, ["import", str(config_file)])

        assert result.exit_code == 0


class TestHealthNoActive:
    """Cover lines 566-569, 601, 605-617: health edge paths."""

    def test_health_with_corrupt_file_skipped(self, runner, mock_console, tmp_path, monkeypatch):
        """Cover lines 568-569: corrupt health file is skipped."""
        state_dir = tmp_path / "health"
        state_dir.mkdir(parents=True)
        (state_dir / "health_test.json").write_text("not json {{{", encoding="utf-8")
        monkeypatch.setattr("src.commands.cli_agent.Path.home", lambda: Path("/nonexistent"))

        # Patch the health state dir
        with patch("src.commands.cli_agent.state_dir", state_dir):
            result = runner.invoke(app, ["health"])

        assert result.exit_code == 0
        mock_console.print.assert_any_call("[yellow]暂无活跃 Agent 健康记录[/yellow]")

    def test_health_with_reassignment_logs(self, runner, mock_console, tmp_path, monkeypatch):
        """Cover lines 605-617: show reassignment logs."""
        import time
        state_dir = tmp_path / "health"
        state_dir.mkdir(parents=True)

        # Create health records so health_map is not empty
        (state_dir / "health_test.json").write_text(
            json.dumps({"agent_name": "test", "status": "healthy"}),
            encoding="utf-8",
        )

        # Create status file
        (state_dir / "status.json").write_text(
            json.dumps({"total_registered": 1, "healthy": 1, "stale": 0,
                        "failed": 0, "total_reassignments": 2, "running": 1,
                        "check_interval": 60, "stale_threshold": 300, "max_retries": 3}),
            encoding="utf-8",
        )

        # Create reassignment log
        reassign = {
            "timestamp": "2024-01-01T00:00:00",
            "from_agent": "agent-a",
            "to_agent": "agent-b",
            "step": "3/5",
            "reason": "timeout",
        }
        (state_dir / "reassignment_001.json").write_text(json.dumps(reassign), encoding="utf-8")

        monkeypatch.setattr("src.commands.cli_agent.Path.home", lambda: Path("/nonexistent"))

        with patch("src.commands.cli_agent.state_dir", state_dir), \
             patch("src.commands.cli_agent.format_health_display", return_value="[mock display]"):
            result = runner.invoke(app, ["health", "--logs"])

        assert result.exit_code == 0


class TestExportAgentStateWithHistory:
    """Cover line 751: export with include_history."""

    @patch("src.agents.store.AgentStore")
    def test_export_state_with_history(
        self, mock_store_cls, runner, mock_console, tmp_path
    ):
        """Export agent state with --include-history flag."""
        mock_store = Mock()
        mock_store.export_agent_state.return_value = {"name": "test-agent", "history": []}
        mock_store_cls.return_value = mock_store

        output_file = tmp_path / "state.json"

        result = runner.invoke(app, ["save", "export", "test-agent", "-o", str(output_file), "--include-history"])

        assert result.exit_code == 0
        mock_store.export_agent_state.assert_called_once()


class TestImportAgentStateException:
    """Cover lines 784-786: import exception handler."""

    @patch("src.agents.store.AgentStore")
    def test_import_state_exception(
        self, mock_store_cls, runner, mock_console, tmp_path
    ):
        """Import agent state fails with exception."""
        mock_store = Mock()
        mock_store.import_agent_state.side_effect = ValueError("import failed")
        mock_store_cls.return_value = mock_store

        config_file = tmp_path / "state.json"
        config_file.write_text('{"name": "test-agent"}', encoding="utf-8")

        result = runner.invoke(app, ["save", "import", str(config_file)])

        assert result.exit_code == 1
        mock_console.print.assert_any_call("[red]导入失败: import failed[/red]")


class TestDeleteAgentFailure:
    """Cover lines 844-845: delete failure."""

    @patch("src.agents.store.AgentStore")
    def test_delete_agent_fails(
        self, mock_store_cls, runner, mock_console
    ):
        """Delete returns False -> error message + exit 1."""
        mock_store = Mock()
        mock_store.delete.return_value = False
        mock_store_cls.return_value = mock_store

        result = runner.invoke(app, ["save", "delete", "nonexistent", "--yes"])

        assert result.exit_code == 1
        mock_console.print.assert_any_call("[red]删除失败[/red]")
