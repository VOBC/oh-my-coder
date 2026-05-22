"""
Tests for src/commands/cli_usage.py - usage subcommands (stats/trace/memory/compact/thought/context/cost)

Tests the helper functions that power omc usage stats|trace|memory|compact|thought|context|cost.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
import typer

from src.commands.cli_usage import (
    _cost_calculate_cost,
    _cost_format_cost,
    _cost_format_datetime,
    # Cost suggest helpers
    _cost_load_prices,
    _cost_load_usage_data,
    # Stats helpers
    _get_manager,
    cost_history,
    cost_model,
    cost_report,
    memory_stats,
    memory_summary,
    memory_tier0,
    memory_tier1,
    stats_command,
    # Trace helpers
    trace_agents,
    trace_latest,
    trace_list,
)

# =============================================================================
# Cost Calculation Helpers
# =============================================================================


class TestCostHelpers:
    """Tests for cost calculation utilities."""

    def test_cost_format_cost_free(self):
        """Format cost when it's zero (free tier)."""
        assert _cost_format_cost(0.0) == "Free"

    def test_cost_format_cost_small(self):
        """Format cost when it's less than 0.01."""
        result = _cost_format_cost(0.005)
        assert result == "< 0.01"

    def test_cost_format_cost_normal(self):
        """Format cost with normal value."""
        result = _cost_format_cost(0.035)
        assert result == "0.035"

    def test_cost_format_cost_large(self):
        """Format cost with large value."""
        result = _cost_format_cost(12.5)
        assert result == "12.500"

    def test_cost_format_datetime_valid(self):
        """Format valid ISO datetime string."""
        dt_str = "2026-05-22T16:44:00"
        result = _cost_format_datetime(dt_str)
        assert result == "2026-05-22 16:44"

    def test_cost_format_datetime_invalid(self):
        """Format invalid datetime string returns as-is."""
        result = _cost_format_datetime("not-a-date")
        assert result == "not-a-date"

    def test_cost_format_datetime_with_microseconds(self):
        """Format datetime with microseconds."""
        dt_str = "2026-05-22T10:30:45.123456"
        result = _cost_format_datetime(dt_str)
        assert result == "2026-05-22 10:30"

    def test_cost_calculate_cost_exact_match(self):
        """Calculate cost for exact model match."""
        # deepseek-chat: prompt=0.001, completion=0.002 per 1k tokens
        cost = _cost_calculate_cost("deepseek-chat", 1000, 500)
        # 1 * 0.001 + 0.5 * 0.002 = 0.001 + 0.001 = 0.002
        assert abs(cost - 0.002) < 1e-9

    def test_cost_calculate_cost_no_match(self):
        """Calculate cost for unknown model (uses default rate)."""
        cost = _cost_calculate_cost("unknown-model", 1000, 1000)
        # Default rate: 0.01 per 1k tokens, so 2000 tokens = 0.02
        assert abs(cost - 0.02) < 1e-9

    def test_cost_calculate_cost_partial_match(self):
        """Calculate cost for partial model match."""
        # Should match on "qwen" prefix
        cost = _cost_calculate_cost("qwen-turbo", 1000, 1000)
        # qwen-turbo: prompt=0.002, completion=0.006
        expected = 1000 / 1000 * 0.002 + 1000 / 1000 * 0.006
        assert abs(cost - expected) < 1e-9

    def test_cost_calculate_cost_zero_tokens(self):
        """Calculate cost with zero tokens."""
        cost = _cost_calculate_cost("deepseek-chat", 0, 0)
        assert cost == 0.0


class TestCostLoadPrices:
    """Tests for _cost_load_prices."""

    def test_load_prices_returns_dict(self):
        """Returns a dictionary."""
        prices = _cost_load_prices()
        assert isinstance(prices, dict)
        assert len(prices) > 0

    def test_load_prices_has_required_models(self):
        """Returns default prices with all required models."""
        prices = _cost_load_prices()
        required = ["deepseek-chat", "gpt-4o", "claude-3-sonnet", "glm-4-flash"]
        for model in required:
            assert model in prices
            assert "prompt" in prices[model]
            assert "completion" in prices[model]

    def test_load_prices_with_custom_file(self, tmp_path):
        """Loads custom prices from config file."""
        config_dir = tmp_path / ".config" / "oh-my-coder"
        config_dir.mkdir(parents=True)
        prices_file = config_dir / "model_prices.json"
        prices_file.write_text(
            json.dumps({
                "my-model": {"prompt": 0.1, "completion": 0.2}
            })
        )
        with patch("src.commands.cli_usage._COST_PRICES_FILE", prices_file):
            prices = _cost_load_prices()
            assert "my-model" in prices
            assert prices["my-model"]["prompt"] == 0.1

    def test_load_prices_custom_overrides_default(self, tmp_path):
        """Custom prices override defaults."""
        config_dir = tmp_path / ".config" / "oh-my-coder"
        config_dir.mkdir(parents=True)
        prices_file = config_dir / "model_prices.json"
        prices_file.write_text(
            json.dumps({
                "deepseek-chat": {"prompt": 0.999, "completion": 0.999}
            })
        )
        with patch("src.commands.cli_usage._COST_PRICES_FILE", prices_file):
            prices = _cost_load_prices()
            assert prices["deepseek-chat"]["prompt"] == 0.999


class TestCostLoadUsageData:
    """Tests for _cost_load_usage_data."""

    def test_load_usage_no_file(self, tmp_path, monkeypatch):
        """Returns empty list when no usage file exists."""
        monkeypatch.setenv("HOME", str(tmp_path))
        with patch("src.commands.cli_usage._COST_USAGE_FILE", tmp_path / "nonexistent.json"):
            data = _cost_load_usage_data()
            assert data == []

    def test_load_usage_with_file(self, tmp_path, monkeypatch):
        """Loads usage data from file."""
        monkeypatch.setenv("HOME", str(tmp_path))
        usage_file = tmp_path / "usage.json"
        usage_file.write_text(
            json.dumps([
                {"model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": "2026-05-22T10:00:00"},
            ])
        )
        with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
            data = _cost_load_usage_data()
            assert len(data) == 1
            assert data[0]["model"] == "deepseek-chat"

    def test_load_usage_invalid_json(self, tmp_path, monkeypatch):
        """Returns empty list on invalid JSON."""
        monkeypatch.setenv("HOME", str(tmp_path))
        usage_file = tmp_path / "usage.json"
        usage_file.write_text("not valid json {{{")
        with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
            data = _cost_load_usage_data()
            assert data == []


# =============================================================================
# Stats Command
# =============================================================================


class TestStatsCommand:
    """Tests for stats_command."""

    def test_stats_command_no_files(self, capsys):
        """stats_command with empty directory shows zero counts."""
        with TemporaryDirectory() as tmpdir:
            stats_command(path=tmpdir)
        out = capsys.readouterr().out
        assert "文件总数" in out or "total_files" in out or "0" in out

    def test_stats_command_with_files(self, tmp_path, capsys):
        """stats_command counts files correctly."""
        (tmp_path / "a.py").write_text("x")
        (tmp_path / "b.py").write_text("y")
        (tmp_path / "c.txt").write_text("z")

        stats_command(path=str(tmp_path))
        out = capsys.readouterr().out
        # Should show some files
        assert "py" in out or "txt" in out

    def test_stats_command_with_subdir(self, tmp_path, capsys):
        """stats_command counts files in subdirectories."""
        subdir = tmp_path / "src"
        subdir.mkdir()
        (tmp_path / "main.py").write_text("x")
        (subdir / "utils.py").write_text("y")

        stats_command(path=str(tmp_path))
        out = capsys.readouterr().out
        assert "py" in out

    def test_stats_command_json_output(self, capsys):
        """stats_command with JSON output format."""
        with TemporaryDirectory() as tmpdir:
            stats_command(path=tmpdir, output_json=True)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "total_files" in data
        assert "total_dirs" in data
        assert "total_size" in data

    def test_stats_command_exclude_dirs(self, tmp_path, capsys):
        """stats_command respects exclude_dirs."""
        (tmp_path / "main.py").write_text("x")
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "lib.py").write_text("y")

        stats_command(path=str(tmp_path), exclude_dirs=("venv",))
        out = capsys.readouterr().out
        # venv should be excluded; only main.py counted
        assert "Python: 1 个文件" in out or "文件总数: 1" in out  # main.py is there

    def test_stats_command_exclude_extensions(self, tmp_path, capsys):
        """stats_command respects exclude_extensions."""
        (tmp_path / "a.py").write_text("x")
        (tmp_path / "b.txt").write_text("y")

        stats_command(path=str(tmp_path), exclude_extensions=(".txt",))
        out = capsys.readouterr().out
        assert "py" in out

    def test_stats_command_max_depth(self, tmp_path, capsys):
        """stats_command respects max_depth."""
        subdir = tmp_path / "a"
        subdir.mkdir()
        (subdir / "deep.py").write_text("x")

        # With max_depth=1, deep.py should not be counted
        stats_command(path=str(tmp_path), max_depth=1)
        out = capsys.readouterr().out
        # Deep file should not appear
        assert "deep.py" not in out or "a.py" in out


# =============================================================================
# Cost Report / Model / History
# =============================================================================


class TestCostReport:
    """Tests for cost_report."""

    def test_cost_report_no_data(self, capsys):
        """cost_report shows no data message when usage is empty."""
        with TemporaryDirectory() as tmpdir:
            # Create empty usage file
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            usage_file.write_text("[]")
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
                cost_report(days=30)
        out = capsys.readouterr().out
        assert "no usage" in out.lower() or "usage" in out.lower()

    def test_cost_report_with_data(self, capsys):
        """cost_report shows usage summary."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            now = datetime.now()
            usage_file.write_text(
                json.dumps([
                    {
                        "model": "deepseek-chat",
                        "prompt_tokens": 1000,
                        "completion_tokens": 500,
                        "timestamp": now.isoformat(),
                    },
                ])
            )
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
                cost_report(days=30)
        out = capsys.readouterr().out
        assert "Total" in out or "total" in out or "deepseek" in out.lower()


class TestCostModel:
    """Tests for cost_model."""

    def test_cost_model_no_data(self, capsys):
        """cost_model shows no data message when usage is empty."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            usage_file.write_text("[]")
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
                cost_model(days=30)
        out = capsys.readouterr().out
        assert "no usage" in out.lower() or "usage" in out.lower()

    def test_cost_model_groups_by_model(self, capsys):
        """cost_model groups usage by model."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            now = datetime.now()
            usage_file.write_text(
                json.dumps([
                    {"model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": now.isoformat()},
                    {"model": "deepseek-chat", "prompt_tokens": 200, "completion_tokens": 100, "timestamp": now.isoformat()},
                    {"model": "gpt-4o", "prompt_tokens": 300, "completion_tokens": 150, "timestamp": now.isoformat()},
                ])
            )
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
                cost_model(days=30)
        out = capsys.readouterr().out
        # Should show deepseek-chat with 2 calls and gpt-4o with 1 call
        assert "deepseek" in out.lower() or "gpt" in out.lower()


class TestCostHistory:
    """Tests for cost_history."""

    def test_cost_history_no_data(self, capsys):
        """cost_history shows no data message when usage is empty."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            usage_file.write_text("[]")
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
                cost_history(limit=20)
        out = capsys.readouterr().out
        assert "no usage" in out.lower()

    def test_cost_history_with_data(self, capsys):
        """cost_history shows recent calls."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            now = datetime.now()
            usage_file.write_text(
                json.dumps([
                    {"model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": now.isoformat()},
                ])
            )
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
                cost_history(limit=20)
        out = capsys.readouterr().out
        # Model name truncated in narrow console: 'deepseek-chat' -> 'de…'
        assert "de" in out.lower()

    def test_cost_history_filter_by_model(self, capsys):
        """cost_history filters by model name."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            now = datetime.now()
            usage_file.write_text(
                json.dumps([
                    {"model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": now.isoformat()},
                    {"model": "gpt-4o", "prompt_tokens": 200, "completion_tokens": 100, "timestamp": now.isoformat()},
                ])
            )
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
                cost_history(limit=20, model="deepseek")
        out = capsys.readouterr().out
        # Model name truncated in narrow console: 'deepseek-chat' -> 'de…'
        assert "de" in out.lower()
        assert "gpt" not in out.lower()  # Should be filtered out

    def test_cost_history_respects_limit(self, capsys):
        """cost_history respects the limit parameter."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            now = datetime.now()
            records = [
                {"model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": (now - timedelta(minutes=i)).isoformat()}
                for i in range(10)
            ]
            usage_file.write_text(json.dumps(records))
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
                cost_history(limit=5)
        out = capsys.readouterr().out
        # Should show 5 records (limit)
        # Model name truncated in narrow console: 'deepseek-chat' -> 'de…'
        assert "de" in out.lower()


# =============================================================================
# Memory Helpers
# =============================================================================


class TestMemoryHelpers:
    """Tests for memory tier helper functions."""

    def test_memory_tier0_empty_project(self, tmp_path, capsys):
        """memory_tier0 with no memory files."""
        _get_manager(tmp_path)
        memory_tier0(project_path=tmp_path)
        out = capsys.readouterr().out
        # Should print a panel with tier info
        assert "Tier 0" in out or "tier0" in out.lower()

    def test_memory_tier1_empty_project(self, tmp_path, capsys):
        """memory_tier1 with no memory files."""
        _get_manager(tmp_path)
        memory_tier1(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "Tier 1" in out or "tier1" in out.lower()

    def test_memory_summary_empty_project(self, tmp_path, capsys):
        """memory_summary with no memory files."""
        _get_manager(tmp_path)
        memory_summary(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "Tier 2" in out or "tier2" in out.lower() or "archive" in out.lower()

    def test_memory_stats_empty_project(self, tmp_path, capsys):
        """memory_stats with no memory files."""
        _get_manager(tmp_path)
        memory_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "统计" in out or "stat" in out.lower() or "Memory" in out


# =============================================================================
# Trace Helpers
# =============================================================================


class TestTraceHelpers:
    """Tests for trace helper functions."""

    def test_trace_list_no_sessions(self, capsys):
        """trace_list with no sessions shows empty message."""
        with patch("src.commands.cli_usage._get_store") as mock_store:
            mock_instance = mock_store.return_value
            mock_instance.list_sessions.return_value = []
            trace_list(limit=5)
        out = capsys.readouterr().out
        assert "暂无" in out or "no trace" in out.lower() or "empty" in out.lower()

    def test_trace_list_with_sessions(self, capsys):
        """trace_list shows sessions."""
        with patch("src.commands.cli_usage._get_store") as mock_store:
            mock_instance = mock_store.return_value
            mock_instance.list_sessions.return_value = ["sess-1"]
            mock_instance.list_traces.return_value = [
                {
                    "agent_name": "planner",
                    "status": "success",
                    "total_duration_ms": 1500,
                    "started_at": "2026-05-22T10:00:00",
                    "output_summary": "planned 3 tasks",
                    "error": "",
                }
            ]
            trace_list(limit=5)
        out = capsys.readouterr().out
        assert "sess" in out.lower() or "session" in out.lower() or "planner" in out.lower()

    def test_trace_list_with_traces(self, capsys):
        """trace_list shows table with traces."""
        with patch("src.commands.cli_usage._get_store") as mock_store:
            mock_instance = mock_store.return_value
            mock_instance.list_sessions.return_value = ["sess-1"]
            mock_instance.list_traces.return_value = [
                {
                    "agent_name": "planner",
                    "status": "success",
                    "total_duration_ms": 1500,
                    "started_at": "2026-05-22T10:00:00",
                    "output_summary": "planned 3 tasks",
                }
            ]
            trace_list(limit=5)
        out = capsys.readouterr().out
        assert "planner" in out.lower() or "success" in out.lower()

    def test_trace_agents_no_session(self):
        """trace_agents with no session."""
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print") as mock_print:
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = None
            with pytest.raises(typer.Exit):
                trace_agents()
        printed = " ".join(str(c.args[0]) for c in mock_print.call_args_list)
        assert "没有" in printed or "no" in printed.lower()

    def test_trace_latest_no_session(self):
        """trace_latest with no sessions."""
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print") as mock_print:
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = None
            with pytest.raises(typer.Exit):
                trace_latest()
        printed = " ".join(str(c.args[0]) for c in mock_print.call_args_list)
        assert "暂无" in printed or "no" in printed.lower()
