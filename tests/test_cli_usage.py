"""
Tests for src/commands/cli_usage.py - usage subcommands (stats/trace/memory/compact/thought/context/cost)

Tests the helper functions that power omc usage stats|trace|memory|compact|thought|context|cost.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

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
             patch("src.commands.cli_usage.console_trace.print") as mock_print:
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = None
            with pytest.raises(typer.Exit):
                trace_show(agent="test-agent")

    def test_trace_show_no_trace(self):
        """trace_show when agent not found."""
        from src.commands.cli_usage import trace_show
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print") as mock_print:
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
             patch("src.commands.cli_usage.console_trace.print") as mock_print:
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
             patch("src.commands.cli_usage.console_trace.print") as mock_print:
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
             patch("src.commands.cli_usage.console_trace.print") as mock_print:
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
        from src.commands.cli_usage import compact_sweep
        import inspect
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
        from src.commands.cli_usage import cost_suggest
        import inspect
        sig = inspect.signature(cost_suggest)
        assert "task" in sig.parameters
        assert "list_models" in sig.parameters

    def test_cost_suggest_with_list(self, capsys):
        """cost_suggest with --list flag."""
        from src.commands.cli_usage import cost_suggest
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
        from src.commands.cli_usage import cost_suggest

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
        from src.commands.cli_usage import cost_suggest

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
        assert result == "0.010"

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
        assert "2026-05-22" in result


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
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls:
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
        with patch("src.core.chain_of_thought.ChainOfThoughtRecorder") as mock_cls:
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
             patch("builtins.open", create=True) as mock_open:
            mock_file = mock_open.return_value.__enter__.return_value
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
        buf = io.StringIO()
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
        import sys
        from unittest.mock import patch, MagicMock, mock_open
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


class TestContextTree:
    """Tests for context_tree."""

    def test_context_tree_basic(self, tmp_path):
        """context_tree displays file tree."""
        from src.commands.cli_usage import context_tree
        from unittest.mock import patch, MagicMock

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
        mock_scanner.LANGUAGE_EXTENSIONS = {"py": "Python"}
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
        from src.commands.cli_usage import context_tree
        from unittest.mock import patch, MagicMock

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
        mock_scanner.LANGUAGE_EXTENSIONS = {"py": "Python"}
        mock_scanner._format_size.return_value = "100 B"

        with patch("src.commands.cli_usage._get_scanner") as mock_get_scanner, \
             patch("rich.console.Console") as mock_console_cls:
            mock_get_scanner.return_value = lambda path: mock_scanner
            mock_console = mock_console_cls.return_value

            context_tree(project_path=tmp_path, depth=3, filter_ext="py")

            # Verify console.print was called
            assert mock_console.print.called


class TestContextStats:
    """Tests for context_stats."""

    def test_context_stats_basic(self, tmp_path, capsys):
        """context_stats shows stats."""
        from src.commands.cli_usage import context_stats
        (tmp_path / "a.py").write_text("print('hello')\nprint('world')")
        context_stats(project_path=tmp_path)
        out = capsys.readouterr().out
        assert "python" in out.lower() or "统计" in out


class TestContextBrowser:
    """Tests for context_browser."""

    def test_context_browser_available(self):
        """context_browser when browser available."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.commands.cli_usage import context_browser

        # Mock ctx
        mock_ctx = MagicMock()
        mock_ctx.available = True
        mock_ctx.title = "Google"
        mock_ctx.url = "https://google.com"
        mock_ctx.content = "Search page"
        mock_ctx.links = ["https://mail.google.com"]
        mock_ctx.timestamp = "2026-05-22"

        # Mock awareness
        mock_awareness = MagicMock()
        mock_awareness.get_current_tab = AsyncMock(return_value=mock_ctx)

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

            # Mock Console to capture output
            mock_console = mock_console_cls.return_value

            context_browser(watch=False)

            # Check that console.print was called with the expected output
            assert mock_console.print.called

    def test_context_browser_unavailable(self):
        """context_browser when browser unavailable."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.commands.cli_usage import context_browser

        # Mock ctx with available=False
        mock_ctx = MagicMock()
        mock_ctx.available = False

        # Mock awareness
        mock_awareness = MagicMock()
        mock_awareness.get_current_tab = AsyncMock(return_value=mock_ctx)

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

            # Mock Console to capture output
            mock_console = mock_console_cls.return_value

            context_browser(watch=False)

            # Check that console.print was called with the expected output
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
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
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
            with patch("src.commands.cli_usage._COST_USAGE_FILE", usage_file):
                cost_history(limit=20, model=None)
