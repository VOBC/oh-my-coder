"""
Extra tests for src/commands/cli_usage.py — covering previously uncovered lines.

Focuses on pure-function paths that don't require Typer CLI app import.
"""
from __future__ import annotations

from unittest.mock import patch

from src.commands.cli_usage import (
    _get_store,
    compact_sweep,
    stats_command,
    trace_latest,
    trace_show,
)
from src.stats.models import StatsResult

# =============================================================================
# stats_command error handling (lines 110-112)
# =============================================================================


class TestStatsCommandErrors:
    """Cover stats_command paths (non-err)."""

    def test_stats_command_errors_json_output(self, capsys):
        """stats_command JSON output includes errors."""
        result = StatsResult(
            total_files=1,
            total_dirs=0,
            total_size=100,
            errors=["Some error"],
        )

        with patch(
            "src.commands.cli_usage._get_count_files",
            return_value=lambda **kwargs: result,
        ):
            stats_command(path="/fake/path", output_json=True)

        out = capsys.readouterr().out
        assert '"errors"' in out
        assert "Some error" in out


# =============================================================================
# _get_store (lines 124-126)
# =============================================================================


class TestGetStore:
    """Cover lines 124-126: _get_store body (docstring + import + return)."""

    def test_get_store_returns_trace_store(self):
        """_get_store returns a TraceStore instance."""
        store = _get_store()
        # Should return a TraceStore instance
        from src.agents.transparency import TraceStore
        assert isinstance(store, TraceStore)


# =============================================================================
# trace_show exact-match path (line 184)
# =============================================================================


class TestTraceShowExactMatch:
    """Cover line 184: exact agent name match in trace_show."""

    def test_trace_show_exact_match_in_all_agents(self):
        """trace_show when agent name is found in all_agents after initial miss."""
        trace_data = {
            "agent_name": "planner",
            "session_id": "sess-1",
            "status": "success",
            "total_duration_ms": 2000,
            "started_at": "2026-05-22T10:00:00",
            "ended_at": "2026-05-22T10:00:02",
            "events": [],
        }
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print"):
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = "sess-1"
            # First get_trace returns None (not in trace store)
            # Second get_trace succeeds (after finding agent in all_agents)
            mock_instance.get_trace.side_effect = [None, trace_data]
            # all_agents contains the exact agent name
            mock_instance.get_all_agents_in_session.return_value = ["planner"]
            # Should not raise — this hits line 184 (exact match retry)
            trace_show(agent="planner")

    def test_trace_show_exact_match_case_sensitive(self):
        """trace_show exact match is case-sensitive; falls to fuzzy."""
        trace_data = {
            "agent_name": "Planner",
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
            # First get_trace returns None
            # Exact match: "planner" not in ["Planner"] (case-sensitive)
            # Falls to fuzzy: "planner" in "Planner".lower() → matches
            mock_instance.get_trace.side_effect = [None, trace_data]
            mock_instance.get_all_agents_in_session.return_value = ["Planner"]
            trace_show(agent="planner")
        printed = " ".join(
            str(c.args[0]) if c.args else "" for c in mock_print.call_args_list
        )
        assert "模糊匹配" in printed


# =============================================================================
# trace_latest success path (lines 286-287)
# =============================================================================


class TestTraceLatestSuccess:
    """Cover lines 286-287: trace_latest when session exists."""

    def test_trace_latest_with_session(self):
        """trace_latest prints session ID and calls trace_list."""
        with patch("src.commands.cli_usage._get_store") as mock_store, \
             patch("src.commands.cli_usage.console_trace.print") as mock_print, \
             patch("src.commands.cli_usage.trace_list") as mock_trace_list:
            mock_instance = mock_store.return_value
            mock_instance.get_latest_session.return_value = "sess-abc-123"
            trace_latest()
        # Verify console_trace.print was called with the session message
        printed = " ".join(
            str(c.args[0]) if c.args else "" for c in mock_print.call_args_list
        )
        assert "sess-abc-123" in printed
        # Verify trace_list was called with the session
        mock_trace_list.assert_called_once_with(session="sess-abc-123", limit=10)


# =============================================================================
# compact_sweep since_last_user success (lines 641-642)
# =============================================================================


class TestCompactSweepSinceLastUser:
    """Cover lines 641-642: compact_sweep since_last_user when user msg found."""

    def test_since_last_user_success_cuts_messages(self, tmp_path):
        """since_last_user=True with user message not at position 0."""
        # Create mock messages: system, user, assistant, user
        msg_system = type("M", (), {"role": "system"})()
        msg_user1 = type("M", (), {"role": "user"})()
        msg_asst = type("M", (), {"role": "assistant"})()
        msg_user2 = type("M", (), {"role": "user"})()
        messages = [msg_system, msg_user1, msg_asst, msg_user2]

        mock_session = type("S", (), {"messages": messages})()
        mock_result = type("R", (), {"compacted": True, "messages_removed": 2, "tokens_saved": 1000})()

        with patch("src.memory.manager.MemoryManager") as mock_mgr_cls, \
             patch("src.commands.cli_usage.console_compact.print"):
            mock_mgr = mock_mgr_cls.from_project.return_value
            mock_mgr.get_latest_session.return_value = mock_session
            mock_mgr.auto_compact_check.return_value = mock_result

            compact_sweep(project_path=tmp_path, since_last_user=True, dry_run=False)

        # Verify messages were cut: last_user_idx = 3, messages[3:] = [msg_user2]
        assert mock_session.messages == [msg_user2]

    def test_since_last_user_success_prints_info(self, tmp_path):
        """since_last_user prints the success message."""
        msg_system = type("M", (), {"role": "system"})()
        msg_user = type("M", (), {"role": "user"})()
        messages = [msg_system, msg_user]

        mock_session = type("S", (), {"messages": messages})()
        mock_result = type("R", (), {"compacted": True, "messages_removed": 1, "tokens_saved": 500})()

        with patch("src.memory.manager.MemoryManager") as mock_mgr_cls, \
             patch("src.commands.cli_usage.console_compact.print") as mock_print:
            mock_mgr = mock_mgr_cls.from_project.return_value
            mock_mgr.get_latest_session.return_value = mock_session
            mock_mgr.auto_compact_check.return_value = mock_result

            compact_sweep(project_path=tmp_path, since_last_user=True, dry_run=False)

        printed = " ".join(
            str(c.args[0]) if c.args else "" for c in mock_print.call_args_list
        )
        assert "已裁剪到第" in printed

    def test_since_last_user_then_compact(self, tmp_path):
        """since_last_user=True then proceeds to actual compact (not dry_run)."""
        msg_system = type("M", (), {"role": "system"})()
        msg_user = type("M", (), {"role": "user"})()
        messages = [msg_system, msg_user]

        mock_session = type("S", (), {"messages": messages})()
        mock_result = type("R", (), {"compacted": True, "messages_removed": 1, "tokens_saved": 500})()

        with patch("src.memory.manager.MemoryManager") as mock_mgr_cls, \
             patch("src.commands.cli_usage.console_compact.print"):
            mock_mgr = mock_mgr_cls.from_project.return_value
            mock_mgr.get_latest_session.return_value = mock_session
            mock_mgr.auto_compact_check.return_value = mock_result

            compact_sweep(project_path=tmp_path, since_last_user=True, dry_run=False)

        # auto_compact_check called with force=True (actual compact, not dry-run)
        mock_mgr.auto_compact_check.assert_called_once_with(mock_session, force=True)
        # save_session called
        mock_mgr.save_session.assert_called_once_with(mock_session)
