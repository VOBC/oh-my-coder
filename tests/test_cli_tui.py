"""Tests for src/commands/cli_tui.py - simple output functions."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from commands.cli_tui import AGENT_CATEGORIES, MODELS, WORKFLOWS, list_agents, list_models, list_workflows


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
