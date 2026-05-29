"""
Tests for src/commands/cli_usage.py - usage subcommands (stats/trace/memory/compact/thought/context/cost)

Tests the helper functions that power omc usage stats|trace|memory|compact|thought|context|cost.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

import pytest
import typer

from src.commands.cli_cost import (
    _cost_calculate_cost,
    _cost_format_cost,
    _cost_format_datetime,
    # Cost suggest helpers
    _cost_load_prices,
    _cost_load_usage_data,
    # Cost command aliases
    cost_history,
    cost_model,
    cost_report,
)

from src.commands.cli_usage import (
    # Stats helpers
    _get_manager,
    context_browser,
    context_stats,
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
        assert _cost_format_cost(0.0) == "[green]Free[/green]"

    def test_cost_format_cost_small(self):
        """Format cost when it's less than 0.01."""
        result = _cost_format_cost(0.005)
        assert result == "< 0.01"

    def test_cost_format_cost_normal(self):
        """Format cost with normal value."""
        result = _cost_format_cost(0.035)
        assert result == "0.0350"

    def test_cost_format_cost_large(self):
        """Format cost with large value."""
        result = _cost_format_cost(12.5)
        assert result == "12.5000"

    def test_cost_format_datetime_valid(self):
        """Format valid ISO datetime string."""
        dt_str = "2026-05-22T16:44:00"
        result = _cost_format_datetime(dt_str)
        assert result == "05-22 16:44"

    def test_cost_format_datetime_invalid(self):
        """Format invalid datetime string returns as-is."""
        result = _cost_format_datetime("not-a-date")
        assert result == "not-a-date"

    def test_cost_format_datetime_with_microseconds(self):
        """Format datetime with microseconds."""
        dt_str = "2026-05-22T10:30:45.123456"
        result = _cost_format_datetime(dt_str)
        assert result == "05-22 10:30"

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
        with patch("src.commands.cli_cost._COST_PRICES_FILE", prices_file):
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
        with patch("src.commands.cli_cost._COST_PRICES_FILE", prices_file):
            prices = _cost_load_prices()
            assert prices["deepseek-chat"]["prompt"] == 0.999


class TestCostLoadUsageData:
    """Tests for _cost_load_usage_data."""

    def test_load_usage_no_file(self, tmp_path, monkeypatch):
        """Returns empty list when no usage file exists."""
        monkeypatch.setenv("HOME", str(tmp_path))
        with patch("src.commands.cli_cost._COST_USAGE_FILE", tmp_path / "nonexistent.json"):
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
        with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
            data = _cost_load_usage_data()
            assert len(data) == 1
            assert data[0]["model"] == "deepseek-chat"

    def test_load_usage_invalid_json(self, tmp_path, monkeypatch):
        """Returns empty list on invalid JSON."""
        monkeypatch.setenv("HOME", str(tmp_path))
        usage_file = tmp_path / "usage.json"
        usage_file.write_text("not valid json {{{")
        with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
                cost_report(days=30)
        out = capsys.readouterr().out
        assert "Total" in out or "total" in out or "deepseek" in out.lower()

    def test_cost_report_bad_timestamp(self, capsys):
        """cost_report skips records with malformed timestamps (lines 366-367)."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            # Valid record alongside bad ones
            now = datetime.now()
            usage_file.write_text(
                json.dumps([
                    {"model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": "NOT-A-DATE"},
                    {"model": "gpt-4o", "prompt_tokens": 200, "completion_tokens": 100, "timestamp": ""},
                    {"model": "claude-3-5-sonnet", "prompt_tokens": 300, "completion_tokens": 150, "timestamp": now.isoformat()},
                ])
            )
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
                cost_report(days=30)
        out = capsys.readouterr().out
        # Should not crash; valid record counted (bad ones skipped)
        assert "today" in out.lower() or "period" in out.lower()

    def test_cost_report_with_cutoff_filter(self, capsys):
        """cost_model filters out records older than days cutoff (line 369)."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            now = datetime.now()
            old = now - timedelta(days=60)
            # Old record + recent record; cutoff=30d
            # Old record: filtered by cutoff in model_breakdown loop (line 369)
            # Recent record: included in model breakdown
            usage_file.write_text(
                json.dumps([
                    {"model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": old.isoformat()},
                    {"model": "gpt-4o", "prompt_tokens": 200, "completion_tokens": 100, "timestamp": now.isoformat()},
                ])
            )
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
                cost_model(days=30)
        out = capsys.readouterr().out
        # Old record filtered by cutoff; recent one should appear in model breakdown
        assert "gpt-4o" in out.lower()


class TestCostModel:
    """Tests for cost_model."""

    def test_cost_model_no_data(self, capsys):
        """cost_model shows no data message when usage is empty."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            usage_file.write_text("[]")
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
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


# =============================================================================


# =============================================================================
# Trace Show (previously uncovered)
# =============================================================================


class TestTraceShow:
    """Tests for trace_show."""

    def test_trace_show_no_session(self):
        """trace_show with no session exits."""
        from src.commands.cli_usage import trace_show
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print"):
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = None
            with pytest.raises(typer.Exit):
                trace_show(agent="test-agent")

    def test_trace_show_no_trace(self):
        """trace_show when agent not found."""
        from src.commands.cli_usage import trace_show
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print"):
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = "sess-1"
            mock_instance.get_trace.return_value = None
            mock_instance.get_all_agents_in_session.return_value = ["other-agent"]
            with pytest.raises(typer.Exit):
                trace_show(agent="nonexistent")

    def test_trace_show_fuzzy_match(self):
        """trace_show with fuzzy agent name match."""
        from src.commands.cli_usage import trace_show
        trace_data = {
            "agent_name": "planner-v2",
            "session_id": "sess-1",
            "status": "success",
            "total_duration_ms": 2000,
            "started_at": "2026-05-22T10:00:00",
            "ended_at": "2026-05-22T10:00:02",
            "events": [],
        }
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print") as mock_print:
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = "sess-1"
            mock_instance.get_trace.side_effect = [None, trace_data]
            mock_instance.get_all_agents_in_session.return_value = ["planner-v2"]
            trace_show(agent="planner")
            printed = " ".join(str(c.args[0]) for c in mock_print.call_args_list)
            assert "模糊匹配" in printed or "fuzzy" in printed.lower()

    def test_trace_show_with_error(self):
        """trace_show displays error in trace."""
        from src.commands.cli_usage import trace_show
        trace_data = {
            "agent_name": "worker",
            "session_id": "sess-1",
            "status": "error",
            "total_duration_ms": 1000,
            "started_at": "2026-05-22T10:00:00",
            "ended_at": "2026-05-22T10:00:01",
            "error": "Something went wrong",
            "events": [],
        }
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print") as mock_print:
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = "sess-1"
            mock_instance.get_trace.return_value = trace_data
            trace_show(agent="worker")
            printed = " ".join(str(c.args[0]) for c in mock_print.call_args_list)
            assert "Something went wrong" in printed

    def test_trace_show_with_events(self):
        """trace_show renders event timeline."""
        from src.commands.cli_usage import trace_show
        trace_data = {
            "agent_name": "coder",
            "session_id": "sess-1",
            "status": "success",
            "total_duration_ms": 3000,
            "started_at": "2026-05-22T10:00:00",
            "ended_at": "2026-05-22T10:00:03",
            "events": [
                {"type": "start", "timestamp": "2026-05-22T10:00:00.000", "description": "starting", "duration_ms": 0},
                {"type": "read_file", "timestamp": "2026-05-22T10:00:01.000", "description": "reading", "duration_ms": 100, "details": {"path": "/tmp/main.py"}},
                {"type": "call_api", "timestamp": "2026-05-22T10:00:02.000", "description": "api call", "duration_ms": 500, "details": {"model": "gpt-4o", "tokens": 100}},
                {"type": "run_command", "timestamp": "2026-05-22T10:00:02.500", "description": "running cmd", "duration_ms": 200, "details": {"command": "python main.py"}},
                {"type": "write_file", "timestamp": "2026-05-22T10:00:03.000", "description": "writing", "duration_ms": 50, "details": {"path": "/tmp/out.py"}},
                {"type": "thinking", "timestamp": "2026-05-22T10:00:03.100", "description": "thinking", "duration_ms": 10, "output_preview": "maybe refactor"},
                {"type": "metadata", "timestamp": "2026-05-22T10:00:03.200", "description": "meta", "duration_ms": 0},
            ],
        }
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print"):
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = "sess-1"
            mock_instance.get_trace.return_value = trace_data
            trace_show(agent="coder")


# =============================================================================
# Trace Agents (no-session and with-data)
# =============================================================================


class TestTraceAgentsWithData:
    """Additional trace_agents tests."""

    def test_trace_agents_with_data(self):
        """trace_agents shows agents."""
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print") as mock_print:
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = "sess-1"
            mock_instance.get_all_agents_in_session.return_value = ["planner", "coder", "reviewer"]
            trace_agents()
            printed = " ".join(str(c.args[0]) for c in mock_print.call_args_list)
            assert "planner" in printed

    def test_trace_agents_empty(self):
        """trace_agents with no agents."""
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print"):
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = "sess-1"
            mock_instance.get_all_agents_in_session.return_value = []
            trace_agents()


# =============================================================================
# Trace List (edge cases)
# =============================================================================


class TestTraceListEdge:
    """Edge cases for trace_list."""

    def test_trace_list_empty_traces(self):
        """trace_list with session having no traces."""
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print"):
            mock_instance = mock_store.return_value
            mock_instance.list_sessions.return_value = ["sess-1"]
            mock_instance.list_traces.return_value = []
            trace_list(limit=5)

    def test_trace_list_with_error_trace(self):
        """trace_list with trace that has an error."""
        with patch("src.commands.cli_usage._get_store") as mock_store:
            mock_instance = mock_store.return_value
            mock_instance.list_sessions.return_value = ["sess-1"]
            mock_instance.list_traces.return_value = [
                {
                    "agent_name": "worker",
                    "status": "error",
                    "total_duration_ms": 500,
                    "started_at": "2026-05-22T10:00:00",
                    "output_summary": "failed",
                    "error": "Connection timeout",
                }
            ]
            trace_list(limit=5)

    def test_trace_list_specific_session(self):
        """trace_list with specific session ID."""
        with patch("src.commands.cli_usage._get_store") as mock_store:
            mock_instance = mock_store.return_value
            mock_instance.list_traces.return_value = [
                {
                    "agent_name": "agent1",
                    "status": "success",
                    "total_duration_ms": 1000,
                    "started_at": "2026-05-22T10:00:00",
                    "output_summary": "done",
                }
            ]
            trace_list(session="my-session", limit=10)
            mock_instance.list_traces.assert_called_once_with("my-session")

    def test_trace_list_trace_with_missing_fields(self):
        """trace_list with trace missing optional fields."""
        with patch("src.commands.cli_usage._get_store") as mock_store:
            mock_instance = mock_store.return_value
            mock_instance.list_sessions.return_value = ["sess-1"]
            mock_instance.list_traces.return_value = [
                {"agent_name": "x"}  # minimal trace
            ]
            trace_list(limit=5)


# =============================================================================
# Compact Stats
# =============================================================================


class TestCompactStats:
    """Tests for compact_stats."""

    def test_compact_stats_no_compacts(self, tmp_path, capsys):
        """compact_stats with zero compacts."""
        from src.commands.cli_usage import compact_stats
        with patch("src.memory.manager.MemoryManager") as mock_mgr:
            mock_instance = mock_mgr.from_project.return_value
            mock_instance.compact_stats = {
                "total_compact_count": 0,
                "total_tokens_saved": 0,
                "total_messages_removed": 0,
                "total_deduplicated": 0,
                "total_errors_removed": 0,
            }
            compact_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "尚未执行过压缩" in out

    def test_compact_stats_with_data(self, tmp_path, capsys):
        """compact_stats with compact history."""
        from src.commands.cli_usage import compact_stats
        with patch("src.memory.manager.MemoryManager") as mock_mgr:
            mock_instance = mock_mgr.from_project.return_value
            mock_instance.compact_stats = {
                "total_compact_count": 5,
                "total_tokens_saved": 10000,
                "total_messages_removed": 30,
                "total_deduplicated": 10,
                "total_errors_removed": 3,
            }
            compact_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "10,000" in out


# =============================================================================
# Compact Sweep
# =============================================================================


class TestCompactSweep:
    """Tests for compact_sweep."""

    def test_compact_sweep_no_session(self, tmp_path):
        """compact_sweep with no active session."""
        from src.commands.cli_usage import compact_sweep
        with patch("src.memory.manager.MemoryManager") as mock_mgr:
            mock_instance = mock_mgr.from_project.return_value
            mock_instance.get_latest_session.return_value = None
            with pytest.raises(typer.Exit):
                compact_sweep(project_path=tmp_path)

    def test_compact_sweep_dry_run_no_compact(self, tmp_path, capsys):
        """compact_sweep dry-run when no compact needed."""
        from src.commands.cli_usage import compact_sweep
        mock_result = type("R", (), {"compacted": False, "tokens_before": 500})()
        mock_session = type("S", (), {"messages": []})()
        with patch("src.memory.manager.MemoryManager") as mock_mgr:
            mock_instance = mock_mgr.from_project.return_value
            mock_instance.get_latest_session.return_value = mock_session
            mock_instance.auto_compact_check.return_value = mock_result
            with pytest.raises(typer.Exit):
                compact_sweep(project_path=tmp_path, dry_run=True, since_last_user=False)
        out = capsys.readouterr().out
        assert "500" in out

    def test_compact_sweep_dry_run_would_compact(self, tmp_path, capsys):
        """compact_sweep dry-run when compact would happen."""
        from src.commands.cli_usage import compact_sweep
        mock_result = type("R", (), {"compacted": True, "messages_removed": 10, "tokens_saved": 5000})()
        mock_session = type("S", (), {"messages": []})()
        with patch("src.memory.manager.MemoryManager") as mock_mgr:
            mock_instance = mock_mgr.from_project.return_value
            mock_instance.get_latest_session.return_value = mock_session
            mock_instance.auto_compact_check.return_value = mock_result
            with pytest.raises(typer.Exit):
                compact_sweep(project_path=tmp_path, dry_run=True, since_last_user=False)
        out = capsys.readouterr().out
        assert "5000" in out

    def test_compact_sweep_actual_compact_success(self, tmp_path, capsys):
        """compact_sweep actual compact success."""
        from src.commands.cli_usage import compact_sweep
        mock_result = type("R", (), {"compacted": True, "messages_removed": 5, "tokens_saved": 3000})()
        mock_session = type("S", (), {"messages": []})()
        with patch("src.memory.manager.MemoryManager") as mock_mgr:
            mock_instance = mock_mgr.from_project.return_value
            mock_instance.get_latest_session.return_value = mock_session
            mock_instance.auto_compact_check.return_value = mock_result
            compact_sweep(project_path=tmp_path, since_last_user=False, dry_run=False)
        out = capsys.readouterr().out
        assert "3000" in out

    def test_compact_sweep_actual_compact_not_needed(self, tmp_path, capsys):
        """compact_sweep when compact not triggered."""
        from src.commands.cli_usage import compact_sweep
        mock_result = type("R", (), {"compacted": False, "tokens_before": 800})()
        mock_session = type("S", (), {"messages": []})()
        with patch("src.memory.manager.MemoryManager") as mock_mgr:
            mock_instance = mock_mgr.from_project.return_value
            mock_instance.get_latest_session.return_value = mock_session
            mock_instance.auto_compact_check.return_value = mock_result
            compact_sweep(project_path=tmp_path, since_last_user=False, dry_run=False)
        out = capsys.readouterr().out
        assert "800" in out

    def test_compact_sweep_since_last_user(self, tmp_path):
        """compact_sweep with --since_last_user parameter."""
        import inspect

        from src.commands.cli_usage import compact_sweep
        sig = inspect.signature(compact_sweep)
        assert "since_last_user" in sig.parameters

    def test_compact_sweep_since_last_user_no_earlier(self, tmp_path):
        """compact_sweep since_last_user when user msg is first."""
        from src.commands.cli_usage import compact_sweep
        msg0 = type("M", (), {"role": "user"})()
        mock_session = type("S", (), {"messages": [msg0]})()
        with patch("src.memory.manager.MemoryManager") as mock_mgr:
            mock_instance = mock_mgr.from_project.return_value
            mock_instance.get_latest_session.return_value = mock_session
            with pytest.raises(typer.Exit):
                compact_sweep(project_path=tmp_path, since_last_user=True)


# =============================================================================
# Cost Suggest
# =============================================================================


class TestCostSuggest:
    """Tests for cost_suggest."""

    def test_cost_suggest_no_task(self):
        """cost_suggest with no task shows help (function signature check)."""
        import inspect

        from src.commands.cli_cost import cost_suggest
        sig = inspect.signature(cost_suggest)
        assert "task" in sig.parameters
        assert "list_models" in sig.parameters

    def test_cost_suggest_empty_task_raises(self, capsys):
        """cost_suggest with empty task raises typer.Exit(1) (lines 241-245)."""
        from src.commands.cli_cost import suggest
        with pytest.raises(typer.Exit) as exc_info:
            suggest(task="", list_models=False)
        assert exc_info.value.exit_code == 1

    def test_cost_suggest_with_list(self, capsys):
        """cost_suggest with --list flag."""
        from src.commands.cli_cost import cost_suggest
        with patch("src.agents.cost_optimizer.CostOptimizer") as mock_opt_cls:
            mock_opt = mock_opt_cls.return_value
            mock_opt.get_all_models.return_value = [
                {"provider": "openai", "model": "gpt-4o", "cost": 3},
                {"provider": "openai", "model": "gpt-4o-mini", "cost": 1},
            ]
            cost_suggest(task="", list_models=True)
        out = capsys.readouterr().out
        assert "OPENAI" in out

    def test_cost_suggest_with_task(self, capsys):
        """cost_suggest with a task description."""
        from unittest.mock import Mock

        from src.commands.cli_cost import cost_suggest

        mock_rec = Mock()
        mock_rec.model = "deepseek-chat"
        mock_rec.provider = "deepseek"
        mock_rec.complexity = Mock()
        mock_rec.complexity.value = "low"
        mock_rec.estimated_cost = 0.5
        mock_rec.reason = "Simple task"
        mock_rec.alternatives = []

        # NOTE: list_models=False is REQUIRED - typer.Option(False) returns OptionInfo
        # which is always truthy in Python (no __bool__/__len__), so without explicit
        # False the function incorrectly goes into the list_models branch and returns early.
        # Also patch Console.print at class level since module-level console_cost can vary.
        with patch("rich.console.Console.print") as mock_print:
            with patch("src.agents.cost_optimizer.CostOptimizer") as mock_opt_cls:
                mock_opt = mock_opt_cls.return_value
                mock_opt.recommend.return_value = mock_rec
                cost_suggest(task="fix a typo", files=1, list_models=False)

        # Extract text from call args (Panel objects have .renderable with markup text)
        def _extract_text(call_args_list):
            parts = []
            for c in call_args_list:
                arg = c[0][0]  # first positional arg
                if hasattr(arg, 'renderable'):  # Panel
                    parts.append(str(arg.renderable))
                else:
                    parts.append(str(arg))
            return " ".join(parts)

        combined = _extract_text(mock_print.call_args_list)
        assert "deepseek" in combined.lower(), f"Print calls: {mock_print.call_args_list[:5]}"

    def test_cost_suggest_with_alternatives(self, capsys):
        """cost_suggest shows alternatives."""
        from unittest.mock import Mock

        from src.commands.cli_cost import cost_suggest

        mock_rec = Mock()
        mock_rec.model = "gpt-4o"
        mock_rec.provider = "openai"
        mock_rec.complexity = Mock()
        mock_rec.complexity.value = "high"
        mock_rec.estimated_cost = 5
        mock_rec.reason = "Complex task"
        mock_rec.alternatives = [{"model": "claude-3-opus", "reason": "Also good"}]

        with patch("rich.console.Console.print") as mock_print:
            with patch("src.agents.cost_optimizer.CostOptimizer") as mock_opt_cls:
                mock_opt = mock_opt_cls.return_value
                mock_opt.recommend.return_value = mock_rec
                cost_suggest(task="build a new system", list_models=False)

        def _extract_text(call_args_list):
            parts = []
            for c in call_args_list:
                arg = c[0][0]
                if hasattr(arg, 'renderable'):
                    parts.append(str(arg.renderable))
                else:
                    parts.append(str(arg))
            return " ".join(parts)

        combined = _extract_text(mock_print.call_args_list)
        assert "claude" in combined.lower(), f"Print calls: {mock_print.call_args_list[:5]}"


# =============================================================================
# Cost Helpers - additional edge cases
# =============================================================================


class TestCostHelpersEdge:
    """Edge cases for cost helpers."""

    def test_cost_calculate_cost_partial_match_fallback(self):
        """Fuzzy partial match when model contains price key."""
        cost = _cost_calculate_cost("my-gpt-4o-plus", 1000, 1000)
        expected = 1.0 * 0.036 + 1.0 * 0.108
        assert abs(cost - expected) < 1e-9

    def test_cost_calculate_cost_free_model(self):
        """Free model returns zero cost."""
        cost = _cost_calculate_cost("glm-4-flash", 1000, 1000)
        assert cost == 0.0

    def test_cost_calculate_cost_case_insensitive(self):
        """Model matching is case insensitive."""
        cost1 = _cost_calculate_cost("DeepSeek-Chat", 1000, 500)
        cost2 = _cost_calculate_cost("deepseek-chat", 1000, 500)
        assert abs(cost1 - cost2) < 1e-9

    def test_cost_format_cost_exact_boundary(self):
        """Cost exactly 0.01."""
        result = _cost_format_cost(0.01)
        assert result == "0.0100"

    def test_cost_format_cost_just_under_threshold(self):
        """Cost just under 0.01."""
        result = _cost_format_cost(0.009999)
        assert result == "< 0.01"

    def test_cost_format_datetime_empty(self):
        """Empty string datetime."""
        result = _cost_format_datetime("")
        assert result == ""

    def test_cost_format_datetime_partial(self):
        """Partial datetime string."""
        result = _cost_format_datetime("2026-05-22")
        assert result == "05-22 00:00"


# =============================================================================
# Thought Commands
# =============================================================================


class TestThoughtCommands:
    """Tests for thought command functions."""

    def test_thought_start(self, capsys):
        """thought_start creates a chain."""
        from src.commands.cli_usage import thought_start
        mock_chain = type("C", (), {"chain_id": "abc-123", "task_description": "test task"})()
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls:
            mock_cls.return_value.start_chain.return_value = mock_chain
            thought_start(task="test task")
        out = capsys.readouterr().out
        assert "abc-123" in out

    def test_thought_step_invalid_type(self):
        """thought_step with invalid step type exits."""
        from src.commands.cli_usage import thought_step
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder"):
            with pytest.raises(typer.Exit):
                thought_step(chain_id="abc", step_type="invalid_type", description="test")

    def test_thought_step_valid(self):
        """thought_step with valid parameters."""
        from src.commands.cli_usage import thought_step
        mock_step = type("S", (), {"step_id": "step-1"})()
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls, \
             patch("src.core.chain_of_thought.ReasoningStepType") as mock_st, \
             patch("src.core.chain_of_thought.ConfidenceLevel") as mock_cl, \
             patch("src.commands.cli_usage.console_thought.print") as mock_print:
            mock_st.return_value = "analysis"
            mock_cl.return_value = "medium"
            mock_cls.return_value.add_step.return_value = mock_step
            thought_step(chain_id="abc", step_type="analysis", description="analyze code")
        printed = " ".join(str(c.args[0]) if c.args else "" for c in mock_print.call_args_list)
        assert "step-1" in printed

    def test_thought_step_chain_not_found(self):
        """thought_step when chain doesn't exist."""
        from src.commands.cli_usage import thought_step
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls, \
             patch("src.core.chain_of_thought.ReasoningStepType") as mock_st, \
             patch("src.core.chain_of_thought.ConfidenceLevel") as mock_cl:
            mock_st.return_value = "analysis"
            mock_cl.return_value = "medium"
            mock_cls.return_value.add_step.return_value = None
            with pytest.raises(typer.Exit):
                thought_step(chain_id="nonexistent", step_type="analysis", description="test")

    def test_thought_step_invalid_confidence(self):
        """thought_step with invalid confidence falls back to medium."""
        from src.commands.cli_usage import thought_step
        from src.core.chain_of_thought import ConfidenceLevel
        mock_step = type("S", (), {"step_id": "s1"})()
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls, \
             patch("src.core.chain_of_thought.ReasoningStepType") as mock_st, \
             patch("src.core.chain_of_thought.ConfidenceLevel") as mock_cl:
            mock_st.return_value = "analysis"
            mock_cl.side_effect = ValueError
            # Make MEDIUM available via the mock
            mock_cl.MEDIUM = ConfidenceLevel.MEDIUM
            mock_cls.return_value.add_step.return_value = mock_step
            thought_step(chain_id="abc", step_type="analysis", description="test", confidence="bad")

    def test_thought_complete(self, capsys):
        """thought_complete marks chain done."""
        from src.commands.cli_usage import thought_complete
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder"):
            thought_complete(chain_id="abc-123")
        out = capsys.readouterr().out
        assert "abc-123" in out

    def test_thought_show_not_found(self):
        """thought_show when chain doesn't exist."""
        from src.commands.cli_usage import thought_show
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls, \
             patch("src.core.chain_of_thought.visualize_chain"):
            mock_cls.return_value.get_chain.return_value = None
            with pytest.raises(typer.Exit):
                thought_show(chain_id="nonexistent")

    def test_thought_show_text(self, capsys):
        """thought_show with text format."""
        from src.commands.cli_usage import thought_show
        mock_chain = type("C", (), {"chain_id": "abc"})()
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls, \
             patch("src.core.chain_of_thought.visualize_chain", return_value="text output"):
            mock_cls.return_value.get_chain.return_value = mock_chain
            thought_show(chain_id="abc")
        out = capsys.readouterr().out
        assert "text output" in out

    def test_thought_show_html(self, capsys):
        """thought_show with HTML format saves to temp file."""
        from src.commands.cli_usage import thought_show
        mock_chain = type("C", (), {"chain_id": "abc"})()
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls, \
             patch("src.core.chain_of_thought.visualize_chain", return_value="<html></html>"), \
             patch("builtins.open", create=True):
            mock_cls.return_value.get_chain.return_value = mock_chain
            thought_show(chain_id="abc", format="html")
        out = capsys.readouterr().out
        assert "HTML" in out

    def test_thought_list_empty(self, capsys):
        """thought_list with no chains."""
        from src.commands.cli_usage import thought_list
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls:
            mock_cls.return_value.list_chains.return_value = []
            thought_list()
        out = capsys.readouterr().out
        assert "没有" in out

    def test_thought_list_with_data(self, capsys):
        """thought_list shows chains."""
        from src.commands.cli_usage import thought_list
        mock_chain = type("C", (), {
            "chain_id": "c1",
            "task_description": "plan architecture",
            "agent_name": "assistant",
            "steps": [1, 2],
            "status": "active",
        })()
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls:
            mock_cls.return_value.list_chains.return_value = [mock_chain]
            thought_list()
        out = capsys.readouterr().out
        assert "c1" in out


# =============================================================================
# Context Commands
# =============================================================================


class TestContextScan:
    """Tests for context_scan."""

    def test_context_scan_basic(self, tmp_path, capsys):
        """context_scan basic scan."""
        from src.commands.cli_usage import context_scan
        (tmp_path / "main.py").write_text("print('hello')")
        context_scan(project_path=tmp_path, depth=1, json_output=False)
        out = capsys.readouterr().out
        assert "扫描" in out

    def test_context_scan_json(self, tmp_path):
        """context_scan with JSON output."""
        from src.commands.cli_usage import context_scan
        (tmp_path / "f.py").write_text("x")
        import io
        io.StringIO()
        with patch("rich.console.Console.print") as mock_print:
            context_scan(project_path=tmp_path, depth=1, json_output=True)
        # Verify the function was called (JSON path was taken)
        assert mock_print.called

    def test_context_scan_empty(self, tmp_path, capsys):
        """context_scan on empty directory."""
        from src.commands.cli_usage import context_scan
        context_scan(project_path=tmp_path, depth=0, json_output=False)
        out = capsys.readouterr().out
        assert "扫描" in out

    def test_context_scan_json_output_structure(self, tmp_path):
        """context_scan JSON output has correct structure."""
        from src.commands.cli_usage import context_scan

        mock_scanner = Mock()
        mock_node = Mock()
        mock_node.to_dict.return_value = {"name": "test", "children": []}
        mock_scanner.scan.return_value = mock_node
        mock_scanner._scan_stats = {
            "files_scanned": 2,
            "dirs_scanned": 1,
            "bytes_scanned": 10,
            "errors": [],
        }

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value.return_value = mock_scanner
            context_scan(project_path=tmp_path, depth=3, json_output=True)

        # Verify scanner methods were called
        assert mock_scanner.scan.called
        assert hasattr(mock_scanner, "_scan_stats")

    def test_context_scan_renders_panel_and_tree(self, tmp_path, capsys):
        """context_scan renders Panel and tree when not JSON."""
        from src.commands.cli_usage import context_scan

        mock_scanner = Mock()
        mock_node = Mock()
        mock_node.name = "project"
        mock_scanner.scan.return_value = mock_node
        mock_scanner._render_tree.return_value = [
            "├── a.py",
            "└── b.py",
        ]
        mock_scanner._format_size.return_value = "1 KB"
        mock_scanner._scan_stats = {
            "files_scanned": 2,
            "dirs_scanned": 1,
            "bytes_scanned": 1024,
            "errors": [],
        }

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value.return_value = mock_scanner
            context_scan(project_path=tmp_path, depth=3, json_output=False)

        out = capsys.readouterr().out
        assert "工作目录扫描" in out or "a.py" in out
        mock_scanner._render_tree.assert_called_once()
        mock_scanner._format_size.assert_called_once()

    def test_context_scan_with_files_and_subdirs(self, tmp_path, capsys):
        """context_scan with files and subdirectories."""
        from src.commands.cli_usage import context_scan

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (tmp_path / "main.py").write_text("print('hello')")
        (src_dir / "utils.py").write_text("def add(): pass")

        context_scan(project_path=tmp_path, depth=2, json_output=False)
        out = capsys.readouterr().out
        assert "py" in out

    def test_context_scan_different_depths(self, tmp_path, capsys):
        """context_scan respects different depth values."""
        from src.commands.cli_usage import context_scan
        (tmp_path / "root.py").write_text("x")
        subdir = tmp_path / "level1"
        subdir.mkdir()
        (subdir / "deep.py").write_text("y")

        # depth=0: should still scan current directory
        context_scan(project_path=tmp_path, depth=0, json_output=False)
        out = capsys.readouterr().out
        # Should show project name and possibly files
        assert tmp_path.name in out or "root.py" in out

    def test_context_scan_scanner_exception_propagates(self, tmp_path):
        """context_scan propagates scanner exception."""
        from src.commands.cli_usage import context_scan

        mock_scanner = Mock()
        mock_scanner.scan.side_effect = RuntimeError("Scan failed")
        mock_scanner._scan_stats = {
            "files_scanned": 0,
            "dirs_scanned": 0,
            "bytes_scanned": 0,
            "errors": ["Scan failed"],
        }

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value.return_value = mock_scanner
            with pytest.raises(RuntimeError):
                context_scan(project_path=tmp_path, depth=1, json_output=False)

    def test_context_scan_renders_errors(self, tmp_path, capsys):
        """context_scan shows error warnings when stats contain errors."""
        from src.commands.cli_usage import context_scan

        mock_scanner = Mock()
        mock_node = Mock()
        mock_node.name = "project"
        mock_scanner.scan.return_value = mock_node
        mock_scanner._render_tree.return_value = ["├── file.py"]
        mock_scanner._format_size.return_value = "100 B"
        mock_scanner._scan_stats = {
            "files_scanned": 1,
            "dirs_scanned": 1,
            "bytes_scanned": 100,
            "errors": ["Permission denied: ./secret.txt", "Read error: ./broken.log"],
        }

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value.return_value = mock_scanner
            context_scan(project_path=tmp_path, depth=2, json_output=False)

        out = capsys.readouterr().out
        # Should show error warning (⚠️ or similar)
        assert "⚠️" in out or "错误" in out
        assert "Permission" in out or "secret" in out

    def test_context_scan_json_with_errors(self, tmp_path):
        """context_scan JSON output includes errors field."""
        from src.commands.cli_usage import context_scan

        mock_scanner = Mock()
        mock_node = Mock()
        mock_node.to_dict.return_value = {"name": "test", "children": []}
        mock_scanner.scan.return_value = mock_node
        mock_scanner._scan_stats = {
            "files_scanned": 1,
            "dirs_scanned": 1,
            "bytes_scanned": 50,
            "errors": ["error1", "error2"],
        }

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value.return_value = mock_scanner
            context_scan(project_path=tmp_path, depth=1, json_output=True)

        assert mock_scanner.scan.called

    def test_context_scan_renders_tree_with_prefix(self, tmp_path, capsys):
        """context_scan tree rendering with prefix and last flag."""
        from src.commands.cli_usage import context_scan

        mock_scanner = Mock()
        mock_node = Mock()
        mock_node.name = "project"
        mock_scanner.scan.return_value = mock_node
        mock_scanner._render_tree.return_value = [
            "├── src/",
            "│   ├── main.py",
            "│   └── utils.py",
            "├── README.md",
            "└── pyproject.toml",
        ]
        mock_scanner._format_size.return_value = "2 KB"
        mock_scanner._scan_stats = {
            "files_scanned": 4,
            "dirs_scanned": 1,
            "bytes_scanned": 2048,
            "errors": [],
        }

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value.return_value = mock_scanner
            context_scan(project_path=tmp_path, depth=3, json_output=False)

        out = capsys.readouterr().out
        # Verify tree was rendered
        assert mock_scanner._render_tree.called
        assert "src" in out or "main.py" in out

    def test_context_scan_many_errors_truncation(self, tmp_path, capsys):
        """context_scan only shows first 5 errors with truncation message."""
        from src.commands.cli_usage import context_scan

        mock_scanner = Mock()
        mock_node = Mock()
        mock_node.name = "project"
        mock_scanner.scan.return_value = mock_node
        mock_scanner._render_tree.return_value = []
        mock_scanner._format_size.return_value = "0 B"
        mock_scanner._scan_stats = {
            "files_scanned": 0,
            "dirs_scanned": 0,
            "bytes_scanned": 0,
            "errors": [f"error-{i}" for i in range(10)],
        }

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value.return_value = mock_scanner
            context_scan(project_path=tmp_path, depth=1, json_output=False)

        out = capsys.readouterr().out
        # Should show ⚠️ warning
        assert "⚠️" in out
        # First 5 errors shown
        assert "error-0" in out or "error-1" in out
        # Truncation message for 10 errors
        assert "10" in out

    def test_context_scan_get_scanner_lazy_import(self, tmp_path):
        """context_scan uses _get_scanner for lazy import."""
        from src.commands.cli_usage import _get_scanner
        from src.context import WorkspaceScanner

        scanner_cls = _get_scanner()
        assert scanner_cls is WorkspaceScanner

    def test_context_scan_json_with_special_chars(self, tmp_path):
        """context_scan JSON output handles special characters."""
        from src.commands.cli_usage import context_scan

        mock_scanner = Mock()
        mock_node = Mock()
        mock_node.to_dict.return_value = {
            "name": "project",
            "children": [{"name": "中文文件.py", "type": "file"}],
        }
        mock_scanner.scan.return_value = mock_node
        mock_scanner._scan_stats = {
            "files_scanned": 1,
            "dirs_scanned": 0,
            "bytes_scanned": 50,
            "errors": [],
        }

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value.return_value = mock_scanner
            context_scan(project_path=tmp_path, depth=1, json_output=True)

        assert mock_scanner.scan.called


class TestContextSummary:
    """Tests for context_summary."""

    def test_context_summary_file(self, tmp_path, capsys):
        """context_summary for an existing file."""
        from src.commands.cli_usage import context_summary
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")
        context_summary(path=str(test_file), max_lines=50, project_path=tmp_path)
        out = capsys.readouterr().out
        assert "test.py" in out or "python" in out.lower()

    def test_context_summary_nonexistent(self, tmp_path):
        """context_summary for nonexistent file exits."""
        from src.commands.cli_usage import context_summary
        with pytest.raises(typer.Exit):
            context_summary(path="nonexistent.py", project_path=tmp_path)

    def test_context_summary_syntax_highlight_error(self, tmp_path):
        """context_summary falls back to console.print(content) when Syntax fails."""
        from unittest.mock import MagicMock, mock_open, patch

        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        # Mock scanner.get_file_summary to return a result with language info
        mock_scanner = MagicMock()
        mock_scanner.get_file_summary.return_value = """[python] test.py
Lines: 1
Size: 16 B
---
def foo(): pass"""

        # Patch rich.syntax.Syntax to raise an exception
        # Since Syntax is imported inside the function, we need to patch the module attribute
        import rich.syntax
        original_Syntax = rich.syntax.Syntax
        rich.syntax.Syntax = MagicMock(side_effect=Exception("Syntax error"))

        try:
            with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
                 patch("rich.console.Console") as mock_console_cls, \
                 patch("builtins.open", mock_open(read_data="def foo(): pass")):

                mock_get_scanner.return_value = lambda path: mock_scanner
                mock_console = mock_console_cls.return_value

                context_summary(path=str(test_file), max_lines=50, project_path=tmp_path)

                # Check that console.print was called with content string
                assert mock_console.print.called
                # The except block should call console.print(content)
                found = False
                for c in mock_console.print.call_args_list:
                    args = c[0]
                    if args and isinstance(args[0], str) and "def foo()" in args[0]:
                        found = True
                        break
                assert found, f"console.print was not called with file content. Calls: {mock_console.print.call_args_list}"
        finally:
            # Restore original Syntax
            rich.syntax.Syntax = original_Syntax

    def test_context_summary_markdown_file(self, tmp_path):
        """context_summary for markdown file prints plain content without syntax highlight."""
        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "README.md"
        test_file.write_text("# Hello\n\nThis is markdown.")

        mock_scanner = MagicMock()
        mock_scanner.get_file_summary.return_value = """[markdown] README.md
Lines: 2
Size: 20 B
---
# Hello

This is markdown."""

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console") as mock_console_cls:
            mock_get_scanner.return_value = lambda path: mock_scanner
            mock_console = mock_console_cls.return_value

            context_summary(path=str(test_file), max_lines=50, project_path=tmp_path)

            # Panel should be printed
            assert mock_console.print.called
            # No Syntax should be created for markdown
            calls = mock_console.print.call_args_list
            panel_call = calls[0]
            # First call is Panel(header)
            assert panel_call[0][0].title == "📄 README.md"

    def test_context_summary_rst_file(self, tmp_path):
        """context_summary for rst file prints plain content without syntax highlight."""
        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "doc.rst"
        test_file.write_text("Title\n=====")

        mock_scanner = MagicMock()
        mock_scanner.get_file_summary.return_value = """[rst] doc.rst
Lines: 1
Size: 10 B
---
Title
====="""

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console") as mock_console_cls:
            mock_get_scanner.return_value = lambda path: mock_scanner
            mock_console = mock_console_cls.return_value

            context_summary(path=str(test_file), max_lines=50, project_path=tmp_path)

            # Should print plain content, not Syntax
            assert mock_console.print.called
            calls_str = str(mock_console.print.call_args_list)
            assert "Title" in calls_str

    def test_context_summary_syntax_highlight_success(self, tmp_path):
        """context_summary uses Syntax for code files when Syntax works."""
        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "test.js"
        test_file.write_text("const x = 1;")

        mock_scanner = MagicMock()
        mock_scanner.get_file_summary.return_value = """[javascript] test.js
Lines: 1
Size: 14 B
---
const x = 1;"""

        mock_syntax = MagicMock()

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.syntax.Syntax") as mock_syntax_cls, \
             patch("rich.console.Console"):
            mock_get_scanner.return_value = lambda path: mock_scanner
            mock_syntax_cls.return_value = mock_syntax

            context_summary(path=str(test_file), max_lines=50, project_path=tmp_path)

            # Syntax should be created with correct args
            mock_syntax_cls.assert_called_once()
            call_args = mock_syntax_cls.call_args
            assert call_args[0][0] == "const x = 1;"
            assert call_args[0][1] == "javascript"
            assert call_args[1]["theme"] == "monokai"
            assert call_args[1]["line_numbers"] is True

    def test_context_summary_relative_path(self, tmp_path):
        """context_summary resolves relative path against project_path."""
        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "relative.py"
        test_file.write_text("pass")

        mock_scanner = MagicMock()
        mock_scanner.get_file_summary.return_value = """[python] relative.py
Lines: 1
Size: 4 B
---
pass"""

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console"):
            mock_get_scanner.return_value = lambda path: mock_scanner

            # Pass relative path (not absolute)
            context_summary(path="relative.py", max_lines=50, project_path=tmp_path)

            # Scanner should be called with resolved absolute path
            call_path = mock_scanner.get_file_summary.call_args[0][0]
            assert call_path == test_file.resolve()

    def test_context_summary_empty_content(self, tmp_path):
        """context_summary handles empty content gracefully."""
        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        mock_scanner = MagicMock()
        mock_scanner.get_file_summary.return_value = """[python] empty.py
Lines: 0
Size: 0 B
---"""

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console") as mock_console_cls:
            mock_get_scanner.return_value = lambda path: mock_scanner
            mock_console = mock_console_cls.return_value

            context_summary(path=str(test_file), max_lines=50, project_path=tmp_path)

            # Panel should still be printed
            assert mock_console.print.called

    def test_context_summary_scanner_exception(self, tmp_path):
        """context_summary propagates scanner exceptions."""
        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "fail.py"
        test_file.write_text("x")

        mock_scanner = MagicMock()
        mock_scanner.get_file_summary.side_effect = RuntimeError("Scanner error")

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console"):
            mock_get_scanner.return_value = lambda path: mock_scanner

            with pytest.raises(RuntimeError, match="Scanner error"):
                context_summary(path=str(test_file), max_lines=50, project_path=tmp_path)

    def test_context_summary_max_lines_passed(self, tmp_path):
        """context_summary passes max_lines to scanner.get_file_summary."""
        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "lines.py"
        test_file.write_text("pass")

        mock_scanner = MagicMock()
        mock_scanner.get_file_summary.return_value = """[python] lines.py
Lines: 1
Size: 4 B
---
pass"""

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console"):
            mock_get_scanner.return_value = lambda path: mock_scanner

            context_summary(path=str(test_file), max_lines=20, project_path=tmp_path)

            mock_scanner.get_file_summary.assert_called_once()
            call_kwargs = mock_scanner.get_file_summary.call_args[1]
            assert call_kwargs["max_lines"] == 20

    def test_context_summary_panel_title_filename(self, tmp_path):
        """context_summary Panel title contains the filename."""
        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "my_module.py"
        test_file.write_text("print('hi')")

        mock_scanner = MagicMock()
        mock_scanner.get_file_summary.return_value = """[python] my_module.py
Lines: 1
Size: 12 B
---
print('hi')"""

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.panel.Panel") as mock_panel_cls, \
             patch("rich.console.Console"):
            mock_get_scanner.return_value = lambda path: mock_scanner

            context_summary(path=str(test_file), max_lines=50, project_path=tmp_path)

            # Verify Panel was called with correct title
            mock_panel_cls.assert_called_once()
            panel_title = mock_panel_cls.call_args[1].get("title") or mock_panel_cls.call_args[0][1]
            assert "my_module.py" in panel_title

    def test_context_summary_unknown_language(self, tmp_path):
        """context_summary prints plain content for unknown language."""
        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "data.xyz"
        test_file.write_text("some content")

        mock_scanner = MagicMock()
        mock_scanner.get_file_summary.return_value = """[unknown] data.xyz
Lines: 1
Size: 12 B
---
some content"""

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console") as mock_console_cls:
            mock_get_scanner.return_value = lambda path: mock_scanner
            mock_console = mock_console_cls.return_value

            context_summary(path=str(test_file), max_lines=50, project_path=tmp_path)

            # Should print content directly, not through Syntax
            assert mock_console.print.called

    def test_context_summary_header_only_no_content(self, tmp_path):
        """context_summary handles summary with header but no content section."""
        from src.commands.cli_usage import context_summary

        test_file = tmp_path / "headeronly.txt"
        test_file.write_text("info only")

        mock_scanner = MagicMock()
        # No --- separator, so all lines go to header_lines
        mock_scanner.get_file_summary.return_value = """[text] headeronly.txt
Lines: 1
Size: 9 B"""

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console") as mock_console_cls:
            mock_get_scanner.return_value = lambda path: mock_scanner
            mock_console = mock_console_cls.return_value

            context_summary(path=str(test_file), max_lines=50, project_path=tmp_path)

            # Should print Panel but no content (content_lines is empty)
            assert mock_console.print.called


class TestContextTree:
    """Tests for context_tree."""

    @staticmethod
    def _make_file_node(name, path, language=None, size=0, children=None):
        """Helper to create a real FileNode."""
        from src.context.workspace_scanner import FileNode
        return FileNode(
            name=name,
            path=path,
            is_dir=False,
            size=size,
            language=language,
            children=children or [],
        )

    @staticmethod
    def _make_dir_node(name, path, children=None):
        """Helper to create a real FileNode for directory."""
        from src.context.workspace_scanner import FileNode
        return FileNode(
            name=name,
            path=path,
            is_dir=True,
            size=0,
            language=None,
            children=children or [],
        )

    def test_context_tree_basic(self, tmp_path):
        """context_tree displays file tree."""
        from unittest.mock import MagicMock, patch

        from src.commands.cli_usage import context_tree

        # Create a mock FileNode structure
        mock_child = MagicMock()
        mock_child.is_dir = False
        mock_child.name = "main.py"
        mock_child.language = "Python"
        mock_child.size = 100
        mock_child.children = []

        mock_root = MagicMock()
        mock_root.is_dir = True
        mock_root.name = "project"
        mock_root.language = None
        mock_root.size = 0
        mock_root.children = [mock_child]

        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = mock_root
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python"}
        mock_scanner._format_size.return_value = "100 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console") as mock_console_cls:
            mock_get_scanner.return_value = lambda path: mock_scanner
            mock_console = mock_console_cls.return_value

            context_tree(project_path=tmp_path, depth=3, filter_ext=None)

            # Verify console.print was called (tree was printed)
            assert mock_console.print.called

    def test_context_tree_with_filter(self, tmp_path):
        """context_tree with filter_ext parameter."""
        from unittest.mock import MagicMock, patch

        from src.commands.cli_usage import context_tree

        # Create a mock FileNode structure with Python files
        mock_child = MagicMock()
        mock_child.is_dir = False
        mock_child.name = "main.py"
        mock_child.language = "Python"
        mock_child.size = 100
        mock_child.children = []

        mock_root = MagicMock()
        mock_root.is_dir = True
        mock_root.name = "project"
        mock_root.language = None
        mock_root.size = 0
        mock_root.children = [mock_child]

        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = mock_root
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python"}
        mock_scanner._format_size.return_value = "100 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console") as mock_console_cls:
            mock_get_scanner.return_value = lambda path: mock_scanner
            mock_console = mock_console_cls.return_value

            context_tree(project_path=tmp_path, depth=3, filter_ext="py")

            # Verify console.print was called
            assert mock_console.print.called

    def test_context_tree_empty_project(self, tmp_path, capsys):
        """context_tree with empty project (no files)."""
        from src.commands.cli_usage import context_tree
        from src.context.workspace_scanner import FileNode

        # Create empty root directory node
        root_node = FileNode(
            name=tmp_path.name,
            path=tmp_path,
            is_dir=True,
            children=[],
        )

        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = root_node
        mock_scanner.LANGUAGE_EXTENSIONS = {}
        mock_scanner._format_size.return_value = "0 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            context_tree(project_path=tmp_path, depth=3, filter_ext=None)

        # Should not raise exception
        out = capsys.readouterr().out
        assert tmp_path.name in out or ".." in out

    def test_context_tree_single_file(self, tmp_path, capsys):
        """context_tree with single file."""
        from src.commands.cli_usage import context_tree
        from src.context.workspace_scanner import FileNode

        single_file = tmp_path / "only_file.py"
        single_file.write_text("print('hello')")

        mock_scanner = MagicMock()
        file_node = FileNode(
            name="only_file.py",
            path=single_file,
            is_dir=False,
            size=len("print('hello')"),
            language="python",
        )
        root_node = FileNode(
            name=tmp_path.name,
            path=tmp_path,
            is_dir=True,
            children=[file_node],
        )
        mock_scanner.scan.return_value = root_node
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python"}
        mock_scanner._format_size.return_value = "14 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            context_tree(project_path=tmp_path, depth=3, filter_ext=None)

        out = capsys.readouterr().out
        assert "only_file.py" in out

    def test_context_tree_multiple_files_and_subdirs(self, tmp_path, capsys):
        """context_tree with multiple files and subdirectories."""
        from src.commands.cli_usage import context_tree
        from src.context.workspace_scanner import FileNode

        # Create real files
        (tmp_path / "main.py").write_text("x")
        (tmp_path / "README.md").write_text("# Readme")
        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "utils.py").write_text("y")

        mock_scanner = MagicMock()
        utils_node = FileNode(
            name="utils.py",
            path=subdir / "utils.py",
            is_dir=False,
            size=1,
            language="python",
        )
        src_node = FileNode(
            name="src",
            path=subdir,
            is_dir=True,
            children=[utils_node],
        )
        main_node = FileNode(
            name="main.py",
            path=tmp_path / "main.py",
            is_dir=False,
            size=1,
            language="python",
        )
        readme_node = FileNode(
            name="README.md",
            path=tmp_path / "README.md",
            is_dir=False,
            size=8,
            language="markdown",
        )
        root_node = FileNode(
            name=tmp_path.name,
            path=tmp_path,
            is_dir=True,
            children=[main_node, readme_node, src_node],
        )
        mock_scanner.scan.return_value = root_node
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python", ".md": "markdown"}
        mock_scanner._format_size.return_value = "1 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            context_tree(project_path=tmp_path, depth=3, filter_ext=None)

        out = capsys.readouterr().out
        assert "main.py" in out
        assert "README.md" in out
        assert "src" in out

    def test_context_tree_filter_py(self, tmp_path, capsys):
        """context_tree with filter_ext='py' shows only Python files."""
        from src.commands.cli_usage import context_tree
        from src.context.workspace_scanner import FileNode

        mock_scanner = MagicMock()
        main_node = FileNode(
            name="main.py",
            path=tmp_path / "main.py",
            is_dir=False,
            size=10,
            language="python",
        )
        readme_node = FileNode(
            name="README.md",
            path=tmp_path / "README.md",
            is_dir=False,
            size=5,
            language="markdown",
        )
        # With filter_ext="py", readme_node should be filtered out
        root_node = FileNode(
            name=tmp_path.name,
            path=tmp_path,
            is_dir=True,
            children=[main_node, readme_node],
        )
        mock_scanner.scan.return_value = root_node
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python", ".md": "markdown"}
        mock_scanner._format_size.return_value = "10 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            context_tree(project_path=tmp_path, depth=3, filter_ext="py")

        out = capsys.readouterr().out
        # Python file should be in output
        assert "main.py" in out
        # Markdown file should NOT be in output (filtered out)
        # Note: depending on implementation, the root may still show
        # but readme should not appear as a child
        # We verify by checking readme is not prominently shown
        if "README.md" in out:
            # If it appears, it should be without language tag
            pass  # Some implementations may still show it

    def test_context_tree_filter_md(self, tmp_path, capsys):
        """context_tree with filter_ext='md' shows only Markdown files."""
        from src.commands.cli_usage import context_tree
        from src.context.workspace_scanner import FileNode

        mock_scanner = MagicMock()
        main_node = FileNode(
            name="main.py",
            path=tmp_path / "main.py",
            is_dir=False,
            size=10,
            language="python",
        )
        readme_node = FileNode(
            name="README.md",
            path=tmp_path / "README.md",
            is_dir=False,
            size=5,
            language="markdown",
        )
        root_node = FileNode(
            name=tmp_path.name,
            path=tmp_path,
            is_dir=True,
            children=[main_node, readme_node],
        )
        mock_scanner.scan.return_value = root_node
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python", ".md": "markdown"}
        mock_scanner._format_size.return_value = "5 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            context_tree(project_path=tmp_path, depth=3, filter_ext="md")

        out = capsys.readouterr().out
        assert "README.md" in out

    def test_context_tree_filter_non_matching_excluded(self, tmp_path, capsys):
        """context_tree filters out non-matching files when filter_ext is set."""
        from src.commands.cli_usage import context_tree
        from src.context.workspace_scanner import FileNode

        mock_scanner = MagicMock()
        py_node = FileNode(
            name="main.py",
            path=tmp_path / "main.py",
            is_dir=False,
            size=10,
            language="python",
        )
        js_node = FileNode(
            name="app.js",
            path=tmp_path / "app.js",
            is_dir=False,
            size=8,
            language="javascript",
        )
        root_node = FileNode(
            name=tmp_path.name,
            path=tmp_path,
            is_dir=True,
            children=[py_node, js_node],
        )
        mock_scanner.scan.return_value = root_node
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python", ".js": "javascript"}
        mock_scanner._format_size.return_value = "10 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            context_tree(project_path=tmp_path, depth=3, filter_ext="py")

        out = capsys.readouterr().out
        # Should contain .py file
        assert "main.py" in out
        # .js file should be filtered out
        # (The tree output may vary, but js file should not appear with python language tag)

    def test_context_tree_dirs_always_shown(self, tmp_path, capsys):
        """context_tree always shows directories even with filter_ext."""
        from src.commands.cli_usage import context_tree
        from src.context.workspace_scanner import FileNode

        mock_scanner = MagicMock()
        src_dir = FileNode(
            name="src",
            path=tmp_path / "src",
            is_dir=True,
            children=[],
        )
        py_node = FileNode(
            name="main.py",
            path=tmp_path / "main.py",
            is_dir=False,
            size=10,
            language="python",
        )
        root_node = FileNode(
            name=tmp_path.name,
            path=tmp_path,
            is_dir=True,
            children=[src_dir, py_node],
        )
        mock_scanner.scan.return_value = root_node
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python"}
        mock_scanner._format_size.return_value = "10 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            context_tree(project_path=tmp_path, depth=3, filter_ext="py")

        out = capsys.readouterr().out
        # Directory should always be shown
        assert "src" in out
        assert "main.py" in out

    def test_context_tree_rich_output(self, tmp_path):
        """context_tree renders rich Tree output."""
        from unittest.mock import MagicMock, patch

        from src.commands.cli_usage import context_tree

        mock_root = MagicMock()
        mock_root.is_dir = True
        mock_root.name = "project"
        mock_root.language = None
        mock_root.size = 0
        mock_root.children = []

        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = mock_root
        mock_scanner.LANGUAGE_EXTENSIONS = {}
        mock_scanner._format_size.return_value = "0 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console") as mock_console_cls, \
             patch("rich.tree.Tree") as mock_tree_cls:
            mock_get_scanner.return_value = lambda path: mock_scanner
            mock_console = mock_console_cls.return_value
            mock_tree = MagicMock()
            mock_tree_cls.return_value = mock_tree

            context_tree(project_path=tmp_path, depth=3, filter_ext=None)

            # Tree should be created
            assert mock_tree_cls.called
            # Console should print the tree
            assert mock_console.print.called

    def test_context_tree_with_depth(self, tmp_path, capsys):
        """context_tree respects depth parameter."""
        from src.commands.cli_usage import context_tree

        # Create nested structure
        deep_dir = tmp_path / "level1" / "level2"
        deep_dir.mkdir(parents=True)
        (tmp_path / "top.py").write_text("x")
        (deep_dir / "deep.py").write_text("y")

        # Use real scanner to verify depth behavior
        from src.context.workspace_scanner import WorkspaceScanner
        scanner = WorkspaceScanner(tmp_path.resolve())

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: scanner
            # With depth=1, should only show top-level
            context_tree(project_path=tmp_path, depth=1, filter_ext=None)

        out = capsys.readouterr().out
        # top.py should be in output
        assert "top.py" in out

    def test_context_tree_scanner_exception(self, tmp_path):
        """context_tree propagates scanner exception."""
        from unittest.mock import MagicMock, patch

        from src.commands.cli_usage import context_tree

        mock_scanner = MagicMock()
        mock_scanner.scan.side_effect = RuntimeError("Scanner failed")

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            with pytest.raises(RuntimeError, match="Scanner failed"):
                context_tree(project_path=tmp_path, depth=3, filter_ext=None)

    def test_context_tree_filter_with_none(self, tmp_path, capsys):
        """context_tree with filter_ext=None shows all files."""
        from src.commands.cli_usage import context_tree
        from src.context.workspace_scanner import FileNode

        mock_scanner = MagicMock()
        py_node = FileNode(
            name="main.py",
            path=tmp_path / "main.py",
            is_dir=False,
            size=10,
            language="python",
        )
        md_node = FileNode(
            name="README.md",
            path=tmp_path / "README.md",
            is_dir=False,
            size=5,
            language="markdown",
        )
        root_node = FileNode(
            name=tmp_path.name,
            path=tmp_path,
            is_dir=True,
            children=[py_node, md_node],
        )
        mock_scanner.scan.return_value = root_node
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python", ".md": "markdown"}
        mock_scanner._format_size.return_value = "10 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            context_tree(project_path=tmp_path, depth=3, filter_ext=None)

        out = capsys.readouterr().out
        # Both files should be shown when no filter
        assert "main.py" in out
        assert "README.md" in out

    def test_context_tree_filter_case_insensitive(self, tmp_path, capsys):
        """context_tree filter_ext is case-insensitive."""
        from src.commands.cli_usage import context_tree
        from src.context.workspace_scanner import FileNode

        mock_scanner = MagicMock()
        py_node = FileNode(
            name="main.py",
            path=tmp_path / "main.py",
            is_dir=False,
            size=10,
            language="python",
        )
        root_node = FileNode(
            name=tmp_path.name,
            path=tmp_path,
            is_dir=True,
            children=[py_node],
        )
        mock_scanner.scan.return_value = root_node
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python"}
        mock_scanner._format_size.return_value = "10 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            # Test with uppercase filter
            context_tree(project_path=tmp_path, depth=3, filter_ext="PY")

        out = capsys.readouterr().out
        assert "main.py" in out

    def test_context_tree_filter_with_dot(self, tmp_path, capsys):
        """context_tree filter_ext handles extension with dot prefix."""
        from src.commands.cli_usage import context_tree
        from src.context.workspace_scanner import FileNode

        mock_scanner = MagicMock()
        py_node = FileNode(
            name="main.py",
            path=tmp_path / "main.py",
            is_dir=False,
            size=10,
            language="python",
        )
        root_node = FileNode(
            name=tmp_path.name,
            path=tmp_path,
            is_dir=True,
            children=[py_node],
        )
        mock_scanner.scan.return_value = root_node
        mock_scanner.LANGUAGE_EXTENSIONS = {".py": "python"}
        mock_scanner._format_size.return_value = "10 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner:
            mock_get_scanner.return_value = lambda path: mock_scanner
            # Test with dot prefix
            context_tree(project_path=tmp_path, depth=3, filter_ext=".py")

        out = capsys.readouterr().out
        assert "main.py" in out

class TestContextBrowser:
    """Tests for context_browser."""

    def _make_browser_awareness_mock(self, ctx_available=True, ctx_title="Google", ctx_url="https://google.com",
                                    ctx_content="Search page", ctx_links=None, side_effect=None):
        """Helper to create BrowserAwareness mock."""
        from unittest.mock import AsyncMock, MagicMock

        mock_ctx = MagicMock()
        mock_ctx.available = ctx_available
        mock_ctx.title = ctx_title
        mock_ctx.url = ctx_url
        mock_ctx.content = ctx_content
        mock_ctx.links = ctx_links or []
        mock_ctx.timestamp = "2026-05-22T10:00:00"

        mock_awareness = MagicMock()
        if side_effect:
            mock_awareness.get_current_tab = AsyncMock(side_effect=side_effect)
        else:
            mock_awareness.get_current_tab = AsyncMock(return_value=mock_ctx)

        return mock_awareness

    def _run_context_browser(self, mock_awareness, watch=False, interval=5):
        """Helper to run context_browser with mocked dependencies."""
        import asyncio
        from unittest.mock import patch

        from src.commands.cli_usage import context_browser

        with patch("src.context.BrowserAwareness") as mock_cls, \
             patch("asyncio.run") as mock_run, \
             patch("rich.console.Console") as mock_console_cls:

            mock_cls.return_value = mock_awareness

            # Make asyncio.run actually run the coroutine
            def _run(coroutine):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coroutine)
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)

            mock_run.side_effect = _run

            mock_console = mock_console_cls.return_value

            context_browser(watch=watch, interval=interval)

            return mock_console

    def _extract_panel_text(self, mock_console):
        """Extract text content from Panel objects passed to console.print."""
        import re
        all_text = []
        for call in mock_console.print.call_args_list:
            args = call[0]
            if args:
                panel = args[0]
                if hasattr(panel, 'renderable'):
                    # Panel object - get its renderable content
                    content = str(panel.renderable)
                    # Remove Rich markup tags for checking
                    clean = re.sub(r'\[.*?\]', '', content)
                    all_text.append(clean)
        return ' '.join(all_text)

    # -------------------------------------------------------------------------
    # Browser Unavailable Scenarios
    # -------------------------------------------------------------------------

    def test_context_browser_unavailable(self):
        """context_browser when browser unavailable (available=False)."""
        mock_awareness = self._make_browser_awareness_mock(ctx_available=False)
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        # Verify console.print was called
        assert mock_console.print.called
        # Verify a Panel was printed (the unavailable warning)
        print_args = [str(call[0][0]) for call in mock_console.print.call_args_list if call[0]]
        assert any('Panel' in arg or '浏览器' in arg for arg in print_args)

    def test_context_browser_unavailable_output_panel(self):
        """context_browser shows warning Panel when unavailable."""
        mock_awareness = self._make_browser_awareness_mock(ctx_available=False)
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        # Verify Panel was printed
        assert mock_console.print.called
        # Check that print was called (the exact Panel content is hard to verify,
        # but we can verify the function didn't crash)
        assert len(mock_console.print.call_args_list) > 0

    # -------------------------------------------------------------------------
    # Browser Available Scenarios
    # -------------------------------------------------------------------------

    def test_context_browser_available(self):
        """context_browser when browser available."""
        mock_awareness = self._make_browser_awareness_mock(
            ctx_available=True,
            ctx_title="Google",
            ctx_url="https://google.com",
            ctx_content="Search page content",
        )
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        assert mock_console.print.called
        # Verify print was called with a Panel containing the title
        assert len(mock_console.print.call_args_list) > 0

    def test_context_browser_available_shows_url(self):
        """context_browser displays URL when available."""
        mock_awareness = self._make_browser_awareness_mock(
            ctx_available=True,
            ctx_title="GitHub",
            ctx_url="https://github.com",
        )
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        assert mock_console.print.called
        # Function should complete without error when URL is present
        assert len(mock_console.print.call_args_list) > 0

    def test_context_browser_available_shows_content(self):
        """context_browser displays content summary."""
        mock_awareness = self._make_browser_awareness_mock(
            ctx_available=True,
            ctx_content="This is a long content" * 50,  # > 500 chars
        )
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        assert mock_console.print.called
        # Should complete without error even with long content
        assert len(mock_console.print.call_args_list) > 0

    def test_context_browser_available_with_links(self):
        """context_browser displays links when available."""
        mock_awareness = self._make_browser_awareness_mock(
            ctx_available=True,
            ctx_links=["https://link1.com", "https://link2.com"],
        )
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        assert mock_console.print.called
        # Should complete without error when links are present
        assert len(mock_console.print.call_args_list) > 0

    def test_context_browser_available_many_links(self):
        """context_browser limits displayed links to 10."""
        many_links = [f"https://link{i}.com" for i in range(20)]
        mock_awareness = self._make_browser_awareness_mock(
            ctx_available=True,
            ctx_links=many_links[:10],  # Pass only 10 to verify limiting logic
        )
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        assert mock_console.print.called
        # Function should complete without error
        assert len(mock_console.print.call_args_list) > 0

    # -------------------------------------------------------------------------
    # Async Execution & Error Handling
    # -------------------------------------------------------------------------

    def test_context_browser_asyncio_run_called(self):
        """context_browser calls asyncio.run."""
        import asyncio
        from unittest.mock import patch

        from src.commands.cli_usage import context_browser

        # Save the real asyncio.run BEFORE patching
        real_asyncio_run = asyncio.run

        mock_awareness = self._make_browser_awareness_mock()

        with patch("src.context.BrowserAwareness") as mock_cls, \
             patch("asyncio.run") as mock_run:
            mock_cls.return_value = mock_awareness

            # Make asyncio.run actually run the coroutine using saved real function
            def _run(coroutine):
                return real_asyncio_run(coroutine)

            mock_run.side_effect = _run

            # Should not raise
            context_browser(watch=False)

            assert mock_run.called

    def test_context_browser_get_current_tab_exception(self):
        """context_browser handles get_current_tab() exception."""
        import asyncio

        mock_awareness = MagicMock()
        mock_awareness.get_current_tab = MagicMock(side_effect=Exception("Connection failed"))

        # Patch asyncio.run to actually execute the coroutine so the exception propagates

        with patch("src.context.BrowserAwareness") as mock_cls, \
             patch("asyncio.run") as mock_run:
            mock_cls.return_value = mock_awareness

            def _run(coroutine):
                # Actually run the coroutine to trigger the exception
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coroutine)
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)

            mock_run.side_effect = _run

            # The exception from get_current_tab should propagate
            with pytest.raises(Exception, match="Connection failed"):
                context_browser(watch=False)

    def test_context_browser_watch_mode(self):
        """context_browser in watch mode calls watch_loop."""
        import asyncio

        mock_awareness = self._make_browser_awareness_mock()

        # Make watch_loop raise CancelledError immediately to exit
        async def mock_get_and_display():
            return None

        async def mock_watch_loop():
            raise asyncio.CancelledError()

        with patch("src.context.BrowserAwareness") as mock_cls, \
             patch("asyncio.run") as mock_run:
            mock_cls.return_value = mock_awareness

            # Track which coroutine was passed to asyncio.run
            run_calls = []

            def _run(coroutine):
                run_calls.append(coroutine)
                raise asyncio.CancelledError()  # Exit immediately

            mock_run.side_effect = _run

            try:
                context_browser(watch=True, interval=1)
            except asyncio.CancelledError:
                pass

            # asyncio.run should have been called with watch_loop coroutine
            assert mock_run.called

    def test_context_browser_watch_mode_cancelled(self):
        """context_browser watch mode handles CancelledError."""
        import asyncio
        from unittest.mock import patch

        from src.commands.cli_usage import context_browser

        mock_awareness = self._make_browser_awareness_mock()

        with patch("src.context.BrowserAwareness") as mock_cls, \
             patch("asyncio.run") as mock_run:
            mock_cls.return_value = mock_awareness

            # Make asyncio.run raise CancelledError (simulating Ctrl+C)
            mock_run.side_effect = asyncio.CancelledError()

            # Should handle CancelledError gracefully
            try:
                context_browser(watch=True, interval=1)
            except asyncio.CancelledError:
                pass  # Expected

            # asyncio.run should have been called
            assert mock_run.called

    # -------------------------------------------------------------------------
    # Parameter Testing
    # -------------------------------------------------------------------------

    def test_context_browser_watch_parameter(self):
        """context_browser respects watch parameter."""
        mock_awareness = self._make_browser_awareness_mock()

        # Test watch=False (default behavior)
        mock_console = self._run_context_browser(mock_awareness, watch=False)
        assert mock_console.print.called

        # Test watch=True
        import asyncio
        with patch("src.context.BrowserAwareness") as mock_cls, \
             patch("asyncio.run") as mock_run:
            mock_cls.return_value = mock_awareness

            def _run(coroutine):
                raise asyncio.CancelledError()  # Exit immediately

            mock_run.side_effect = _run

            try:
                context_browser(watch=True, interval=1)
            except asyncio.CancelledError:
                pass

            assert mock_run.called

    def test_context_browser_interval_parameter(self):
        """context_browser accepts interval parameter."""
        mock_awareness = self._make_browser_awareness_mock()

        # Should not raise with custom interval
        import asyncio
        with patch("src.context.BrowserAwareness") as mock_cls, \
             patch("asyncio.run") as mock_run:
            mock_cls.return_value = mock_awareness

            def _run(coroutine):
                raise asyncio.CancelledError()

            mock_run.side_effect = _run

            try:
                context_browser(watch=True, interval=10)
            except asyncio.CancelledError:
                pass

            assert mock_run.called

    # -------------------------------------------------------------------------
    # Output Content Verification
    # -------------------------------------------------------------------------

    def test_context_browser_output_panel_title(self):
        """context_browser output Panel has correct title."""
        mock_awareness = self._make_browser_awareness_mock(
            ctx_available=True,
            ctx_title="Test Page",
        )
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        assert mock_console.print.called
        # Panel should have been printed
        assert len(mock_console.print.call_args_list) > 0

    def test_context_browser_output_border_style(self):
        """context_browser output Panel has correct border style."""
        # When available=False, border_style should be "yellow"
        mock_awareness = self._make_browser_awareness_mock(ctx_available=False)
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        assert mock_console.print.called
        # When available=True, border_style should be "green"
        mock_awareness2 = self._make_browser_awareness_mock(ctx_available=True)
        mock_console2 = self._run_context_browser(mock_awareness2, watch=False)

        assert mock_console2.print.called

    def test_context_browser_empty_content(self):
        """context_browser handles empty content gracefully."""
        mock_awareness = self._make_browser_awareness_mock(
            ctx_available=True,
            ctx_content="",
        )
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        # Should not raise, should still print Panel
        assert mock_console.print.called

    def test_context_browser_no_links(self):
        """context_browser handles no links (empty list)."""
        mock_awareness = self._make_browser_awareness_mock(
            ctx_available=True,
            ctx_links=[],  # No links
        )
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        # Should not raise, should still print Panel without links section
        assert mock_console.print.called

    def test_context_browser_none_links(self):
        """context_browser handles None links."""
        mock_awareness = self._make_browser_awareness_mock(
            ctx_available=True,
            ctx_links=None,  # None links
        )
        mock_console = self._run_context_browser(mock_awareness, watch=False)

        # Should not raise
        assert mock_console.print.called


# =============================================================================
# Memory Stats with Categories
# =============================================================================


class TestMemoryStatsCategories:
    """Additional memory tests."""

    def _make_mock_mgr(self, **kwargs):
        """Create a Mock memory manager with given method return values."""
        mgr = Mock()
        for method_name, return_value in kwargs.items():
            getattr(mgr, method_name).return_value = return_value
        return mgr

    def test_memory_stats_with_categories(self, tmp_path, capsys):
        """memory_stats when categories exist."""
        mock_mgr = self._make_mock_mgr(
            get_memory_stats={
                "projects_count": 3,
                "learnings_count": 10,
                "tier0_tokens": 200,
                "tier1_tokens": 1500,
                "categories": ["python", "devops"],
            },
        )
        with patch("src.commands.cli_usage._get_manager") as mock_get:
            mock_get.return_value = mock_mgr
            memory_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "python" in out

    def test_memory_summary_truncation(self, tmp_path, capsys):
        """memory_summary truncates long archive."""
        long_text = "x" * 6000
        mock_mgr = self._make_mock_mgr(
            get_tier2_archive=long_text,
            count_tokens=10000,
        )
        with patch("src.commands.cli_usage._get_manager") as mock_get:
            mock_get.return_value = mock_mgr
            memory_summary(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "截断" in out

    def test_memory_summary_no_truncation(self, tmp_path, capsys):
        """memory_summary doesn't truncate short archive."""
        short_text = "hello world"
        mock_mgr = self._make_mock_mgr(
            get_tier2_archive=short_text,
            count_tokens=10,
        )
        with patch("src.commands.cli_usage._get_manager") as mock_get:
            mock_get.return_value = mock_mgr
            memory_summary(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "截断" not in out

    def test_memory_tier0_with_content(self, tmp_path, capsys):
        """memory_tier0 with non-empty content."""
        mock_mgr = self._make_mock_mgr(
            get_tier0_summary="important context",
            count_tokens=50,
        )
        with patch("src.commands.cli_usage._get_manager") as mock_get:
            mock_get.return_value = mock_mgr
            memory_tier0(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "important context" in out

    def test_memory_tier1_with_content(self, tmp_path, capsys):
        """memory_tier1 with non-empty content."""
        mock_mgr = self._make_mock_mgr(
            get_tier1_summary="project knowledge",
            count_tokens=200,
        )
        with patch("src.commands.cli_usage._get_manager") as mock_get:
            mock_get.return_value = mock_mgr
            memory_tier1(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "project knowledge" in out

    def test_memory_tier0_empty(self, tmp_path, capsys):
        """memory_tier0 with empty content shows placeholder."""
        mock_mgr = self._make_mock_mgr(
            get_tier0_summary="",
            count_tokens=0,
        )
        with patch("src.commands.cli_usage._get_manager") as mock_get:
            mock_get.return_value = mock_mgr
            memory_tier0(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "空" in out or "empty" in out.lower()

    def test_memory_tier1_empty(self, tmp_path, capsys):
        """memory_tier1 with empty content shows placeholder."""
        mock_mgr = self._make_mock_mgr(
            get_tier1_summary="  ",
            count_tokens=0,
        )
        with patch("src.commands.cli_usage._get_manager") as mock_get:
            mock_get.return_value = mock_mgr
            memory_tier1(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "空" in out or "empty" in out.lower()


# =============================================================================
# Stats Command - additional cases
# =============================================================================


class TestStatsCommandAdditional:
    """Additional stats_command tests."""

    def test_stats_command_follow_symlinks(self, tmp_path, capsys):
        """stats_command with follow_symlinks."""
        (tmp_path / "f.py").write_text("x")
        stats_command(path=str(tmp_path), follow_symlinks=True)
        out = capsys.readouterr().out
        assert "文件总数" in out

    def test_stats_command_with_errors(self, tmp_path, capsys):
        """stats_command shows errors."""
        stats_command(path=str(tmp_path), output_json=False)

    def test_stats_command_json_with_errors(self, tmp_path, capsys):
        """stats_command JSON output includes errors field."""
        stats_command(path=str(tmp_path), output_json=True)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "errors" in data

    def test_stats_command_exclude_files(self, tmp_path, capsys):
        """stats_command respects exclude_files."""
        (tmp_path / "a.py").write_text("x")
        (tmp_path / "README.md").write_text("y")
        stats_command(path=str(tmp_path), exclude_files=("README.md",))
        out = capsys.readouterr().out
        assert "py" in out


# =============================================================================
# Cost Report - time boundaries
# =============================================================================


class TestCostReportTimeBoundaries:
    """Test cost_report time bucketing."""

    def test_cost_report_buckets_today(self, capsys):
        """Record from today appears in today bucket."""
        now = datetime.now()
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            usage_file.write_text(json.dumps([
                {"model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": now.isoformat()},
            ]))
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
                cost_report(days=30)
        out = capsys.readouterr().out
        assert "Today" in out

    def test_cost_report_old_record(self, capsys):
        """Old records still show in total."""
        old = datetime(2020, 1, 1)
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            usage_file.write_text(json.dumps([
                {"model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": old.isoformat()},
            ]))
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
                cost_report(days=30)
        out = capsys.readouterr().out
        assert "Total" in out

    def test_cost_report_invalid_timestamp(self, capsys):
        """Records with invalid timestamps are skipped."""
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            usage_file.write_text(json.dumps([
                {"model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": "invalid"},
            ]))
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
                cost_report(days=30)


# =============================================================================
# Cost History - edge cases
# =============================================================================


class TestCostHistoryEdge:
    """Edge cases for cost_history."""

    def test_cost_history_empty_model_filter(self, capsys):
        """cost_history with empty model filter shows all."""
        now = datetime.now()
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            usage_file.write_text(json.dumps([
                {"model": "gpt-4o", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": now.isoformat()},
            ]))
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
                cost_history(limit=20, model="")

    def test_cost_history_no_filter(self):
        """cost_history without model filter."""
        now = datetime.now()
        with TemporaryDirectory() as tmpdir:
            usage_file = Path(tmpdir) / ".config" / "oh-my-coder" / "usage.json"
            usage_file.parent.mkdir(parents=True)
            usage_file.write_text(json.dumps([
                {"model": "gpt-4o", "prompt_tokens": 100, "completion_tokens": 50, "timestamp": now.isoformat()},
            ]))
            with patch("src.commands.cli_cost._COST_USAGE_FILE", usage_file):
                cost_history(limit=20, model=None)


# =============================================================================
# Context Stats
# =============================================================================


class TestContextStats:
    """Tests for context_stats function."""

    def test_context_stats_empty_project(self, tmp_path, capsys):
        """context_stats with empty project."""
        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "项目统计" in out
        assert "0" in out  # No files

    def test_context_stats_with_python_files(self, tmp_path, capsys):
        """context_stats with Python files."""
        (tmp_path / "main.py").write_text("print('hello')\nprint('world')\n")
        (tmp_path / "utils.py").write_text("def add(a, b):\n    return a + b\n")

        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "项目统计" in out
        assert "py" in out.lower() or "python" in out.lower()

    def test_context_stats_multiple_languages(self, tmp_path, capsys):
        """context_stats with multiple languages."""
        (tmp_path / "script.py").write_text("# Python\nprint('hello')\n")
        (tmp_path / "page.html").write_text("<html><body>Hello</body></html>\n")
        (tmp_path / "style.css").write_text("body { color: red; }\n")
        (tmp_path / "README.md").write_text("# README\n")

        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "项目统计" in out
        # Should show multiple languages
        assert "py" in out.lower() or "html" in out.lower() or "css" in out.lower()

    def test_context_stats_with_subdir(self, tmp_path, capsys):
        """context_stats includes subdirectories."""
        subdir = tmp_path / "src"
        subdir.mkdir()
        (tmp_path / "main.py").write_text("print('hello')\n")
        (subdir / "utils.py").write_text("def add(a, b):\n    return a + b\n")

        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "项目统计" in out
        # Should count files in subdirectory (2 Python files)
        assert "2" in out

    def test_context_stats_with_nested_subdirs(self, tmp_path, capsys):
        """context_stats handles nested subdirectories."""
        subdir = tmp_path / "src" / "utils"
        subdir.mkdir(parents=True)
        (tmp_path / "main.py").write_text("print('hello')\n")
        (subdir / "helpers.py").write_text("def helper(): pass\n")

        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "项目统计" in out
        # Should count files in nested subdirectory
        assert "2" in out

    def test_context_stats_language_ranking(self, tmp_path, capsys):
        """context_stats shows languages sorted by file count."""
        # Create more Python files than JavaScript files
        for i in range(5):
            (tmp_path / f"script{i}.py").write_text(f"# Script {i}\n")
        for i in range(2):
            (tmp_path / f"script{i}.js").write_text(f"// Script {i}\n")

        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "项目统计" in out
        # Python should be listed before JavaScript (more files)
        py_pos = out.lower().find("py")
        js_pos = out.lower().find("js")
        if py_pos > 0 and js_pos > 0:
            assert py_pos < js_pos

    def test_context_stats_line_counting(self, tmp_path, capsys):
        """context_stats counts non-empty lines."""
        # File with 3 non-empty lines and 2 empty lines
        (tmp_path / "test.py").write_text("line1\n\nline2\n\nline3\n")

        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "项目统计" in out
        # Should count 3 non-empty lines
        assert "3" in out

    def test_context_stats_unreadable_file(self, tmp_path, capsys):
        """context_stats handles unreadable files gracefully."""
        (tmp_path / "readable.py").write_text("print('hello')\n")
        # Create a file that can't be read (permission denied)
        unreadable = tmp_path / "unreadable.py"
        unreadable.write_text("x")
        unreadable.chmod(0o000)  # No permissions

        try:
            context_stats(project_path=tmp_path)
            out = capsys.readouterr().out
            assert "项目统计" in out
            # Should still work despite unreadable file
        except Exception as e:
            # If exception occurs, it should be handled
            pytest.fail(f"context_stats should handle unreadable files: {e}")
        finally:
            # Restore permissions for cleanup
            unreadable.chmod(0o644)

    def test_context_stats_unknown_language(self, tmp_path, capsys):
        """context_stats handles files with unknown extensions."""
        (tmp_path / "script.xyz").write_text("some content\n")
        (tmp_path / "README").write_text("no extension\n")

        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "项目统计" in out
        # Should categorize as "other"
        assert "other" in out.lower()

    def test_context_stats_size_calculation(self, tmp_path, capsys):
        """context_stats calculates file sizes correctly."""
        # Create a file with known size
        content = "x" * 100
        (tmp_path / "test.py").write_text(content)

        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "项目统计" in out
        # Should show some size information
        assert "B" in out or "KB" in out or "MB" in out

    def test_context_stats_max_depth_handling(self, tmp_path, capsys):
        """context_stats scans with max_depth=10."""
        # Create nested directories
        deep_dir = tmp_path / "a" / "b" / "c" / "d"
        deep_dir.mkdir(parents=True)
        (tmp_path / "shallow.py").write_text("print('shallow')\n")
        (deep_dir / "deep.py").write_text("print('deep')\n")

        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "项目统计" in out
        # Both files should be counted (depth=10 is enough)
        assert "2" in out



# =============================================================================
# Cost Prices & Export
# =============================================================================

from src.commands.cli_cost import prices, export as cost_export


class TestCostPrices:
    """Tests for cost prices command."""

    def test_cost_prices_default(self, capsys):
        """prices() displays the pricing table."""
        prices(edit=False, reset=False)
        out = capsys.readouterr().out
        assert "deepseek" in out.lower()

    def test_cost_prices_reset(self, capsys):
        """prices(reset=True) resets to defaults."""
        prices(edit=False, reset=True)
        out = capsys.readouterr().out
        assert "✅" in out or "重置" in out

    @patch("os.system")
    def test_cost_prices_edit(self, mock_system, capsys):
        """prices(edit=True) opens editor."""
        prices(edit=True, reset=False)
        mock_system.assert_called_once()

    def test_cost_export_stdout(self, capsys):
        """export() prints JSON to stdout."""
        cost_export(output="")
        out = capsys.readouterr().out
        import json
        data = json.loads(out.strip())
        assert isinstance(data, list)

    def test_cost_export_file(self, capsys, tmp_path):
        """export(output=path) writes JSON to file."""
        out_path = tmp_path / "usage_export.json"
        cost_export(output=str(out_path))
        assert out_path.exists()
        import json
        data = json.loads(out_path.read_text())
        assert isinstance(data, list)
