"""Tests for src/memory/auto_compact.py"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.memory.auto_compact import AutoCompact, CompactResult
from src.memory.short_term import Message, SessionContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_message(role: str, content: str, **kwargs) -> Message:
    meta = kwargs.pop("metadata", {})
    # Allow kwargs to add/override metadata fields (e.g., is_error=True)
    meta = {**meta, **kwargs}
    return Message(role=role, content=content, metadata=meta)


def make_session(messages: list[Message]) -> SessionContext:
    return SessionContext(session_id="test-session", messages=messages)


def make_memory_manager(count_tokens: int = 100) -> MagicMock:
    mm = MagicMock()
    mm.count_tokens = MagicMock(return_value=count_tokens)
    return mm


# ---------------------------------------------------------------------------
# CompactResult
# ---------------------------------------------------------------------------

class TestCompactResult:
    def test_tokens_saved_positive(self):
        result = CompactResult(
            triggered=True,
            tokens_before=1000,
            tokens_after=400,
            messages_removed=5,
            warning_level="compacted",
        )
        assert result.tokens_saved == 600

    def test_tokens_saved_zero(self):
        result = CompactResult(
            triggered=False,
            tokens_before=200,
            tokens_after=200,
            messages_removed=0,
            warning_level="ok",
        )
        assert result.tokens_saved == 0

    def test_tokens_saved_negative(self):
        result = CompactResult(
            triggered=True,
            tokens_before=100,
            tokens_after=150,
            messages_removed=-2,
            warning_level="compacted",
        )
        assert result.tokens_saved == -50

    def test_deduplicated_count_default(self):
        result = CompactResult(
            triggered=False,
            tokens_before=0,
            tokens_after=0,
            messages_removed=0,
            warning_level="ok",
        )
        assert result.deduplicated_count == 0
        assert result.error_removed_count == 0


# ---------------------------------------------------------------------------
# AutoCompact.__init__
# ---------------------------------------------------------------------------

class TestAutoCompactInit:
    def test_default_values(self):
        mm = make_memory_manager()
        ac = AutoCompact(memory_manager=mm)
        assert ac.memory_manager is mm
        assert ac.model_context_window == 128000
        assert ac.compact_threshold == 0.95
        assert ac.warning_threshold == 0.70
        assert ac.enable_deduplication is True
        assert ac.enable_purge_errors is True

    def test_custom_values(self):
        mm = make_memory_manager()
        ac = AutoCompact(
            memory_manager=mm,
            model_context_window=64000,
            compact_threshold=0.90,
            warning_threshold=0.60,
            enable_deduplication=False,
            enable_purge_errors=False,
        )
        assert ac.model_context_window == 64000
        assert ac.compact_threshold == 0.90
        assert ac.warning_threshold == 0.60
        assert ac.enable_deduplication is False
        assert ac.enable_purge_errors is False


# ---------------------------------------------------------------------------
# AutoCompact._get_model_context_window
# ---------------------------------------------------------------------------

class TestGetModelContextWindow:
    def test_no_model_returns_default(self):
        mm = make_memory_manager()
        ac = AutoCompact(memory_manager=mm, model_context_window=99999)
        result = ac._get_model_context_window(provider="openai", model="")
        assert result == 99999

    def test_no_metadata_file_returns_default(self):
        mm = make_memory_manager()
        ac = AutoCompact(memory_manager=mm, model_context_window=50000)
        with patch.object(Path, "exists", return_value=False):
            result = ac._get_model_context_window(model="gpt-4o")
        assert result == 50000

    def test_model_not_in_metadata_returns_default(self, tmp_path):
        mm = make_memory_manager()
        ac = AutoCompact(memory_manager=mm, model_context_window=64000)
        metadata_file = tmp_path / "model_metadata.json"
        metadata_file.write_text(json.dumps({"gpt-4": {"context": 8192}}))
        with patch.object(
            Path,
            "exists",
            return_value=lambda self: metadata_file.exists(),
        ), patch.object(Path, "read_text", metadata_file.read_text):
            result = ac._get_model_context_window(model="unknown-model")
        assert result == 64000

    def test_metadata_json_error_returns_default(self):
        mm = make_memory_manager()
        ac = AutoCompact(memory_manager=mm, model_context_window=128000)
        with patch.object(Path, "exists", return_value=True), patch.object(
            Path,
            "read_text",
            side_effect=json.JSONDecodeError("err", "", 0),
        ):
            result = ac._get_model_context_window(model="gpt-4o")
        assert result == 128000

    def test_success_returns_context_from_metadata(self):
        mm = make_memory_manager()
        ac = AutoCompact(memory_manager=mm, model_context_window=128000)
        fake_metadata = {"gpt-4o": {"context": 128000, "price": "0.01"}}
        with patch.object(Path, "exists", return_value=True), patch.object(
            Path, "read_text", return_value=json.dumps(fake_metadata)
        ):
            result = ac._get_model_context_window(model="gpt-4o")
        assert result == 128000


# ---------------------------------------------------------------------------
# AutoCompact._count_session_tokens
# ---------------------------------------------------------------------------

class TestCountSessionTokens:
    def test_empty_session(self):
        mm = make_memory_manager()
        ac = AutoCompact(memory_manager=mm)
        session = make_session([])
        assert ac._count_session_tokens(session) == 0

    def test_with_messages(self):
        mm = make_memory_manager(count_tokens=50)
        ac = AutoCompact(memory_manager=mm)
        session = make_session(
            [
                make_message("user", "hello"),
                make_message("assistant", "hi"),
            ]
        )
        # 2 msgs * (50 + 4 overhead) = 108
        assert ac._count_session_tokens(session) == 108


# ---------------------------------------------------------------------------
# AutoCompact.check_and_compact
# ---------------------------------------------------------------------------

class TestCheckAndCompact:
    def _make_ac(self, **kwargs) -> AutoCompact:
        mm = make_memory_manager()
        return AutoCompact(memory_manager=mm, **kwargs)

    def test_below_threshold_not_triggered(self):
        """usage_ratio < compact_threshold -> triggered=False"""
        ac = self._make_ac(compact_threshold=0.95, warning_threshold=0.70)
        session = make_session([make_message("user", "hi")])
        # token ratio ~0.0004 -> below warning
        result = ac.check_and_compact(session, model="gpt-4o")
        assert result.triggered is False
        assert result.warning_level == "ok"

    def test_at_compact_threshold_triggered(self):
        """ratio >= compact_threshold -> triggered (to_compress non-empty needed)"""
        ac = self._make_ac(
            model_context_window=100, compact_threshold=0.95, warning_threshold=0.70
        )
        # Mock _count_session_tokens directly so token count is independent of message count.
        # Need >= 5 messages for to_compress to be non-empty (int(5*0.2)=1 → 4 msgs compressed).
        ac._count_session_tokens = MagicMock(return_value=95)  # 95/100=0.95
        session = make_session([make_message("user", f"msg{i}") for i in range(5)])
        result = ac.check_and_compact(session, model="gpt-4o")
        assert result.triggered is True
        assert result.warning_level == "compacted"
        assert result.tokens_before == 95

    def test_above_threshold_triggered(self):
        """ratio >= compact_threshold -> triggered"""
        ac = self._make_ac(
            model_context_window=100, compact_threshold=0.95, warning_threshold=0.70
        )
        # 100/100=1.0 >= 0.95; >= 5 msgs so to_compress is non-empty
        ac._count_session_tokens = MagicMock(return_value=100)
        session = make_session([make_message("user", f"msg{i}") for i in range(5)])
        result = ac.check_and_compact(session, model="gpt-4o")
        assert result.triggered is True
        assert result.warning_level == "compacted"
        assert result.tokens_before == 100

    def test_force_triggered(self):
        """force=True bypasses threshold"""
        ac = self._make_ac(
            model_context_window=1000, compact_threshold=0.95, warning_threshold=0.70
        )
        # >=5 msgs so to_compress non-empty; force=True bypasses ratio check
        ac._count_session_tokens = MagicMock(return_value=10)
        session = make_session([make_message("user", f"msg{i}") for i in range(5)])
        result = ac.check_and_compact(session, model="gpt-4o", force=True)
        assert result.triggered is True
        assert result.tokens_before == 10

    def test_warning_level(self):
        """70% <= ratio < 95% -> warning"""
        ac = self._make_ac(
            model_context_window=100, compact_threshold=0.95, warning_threshold=0.70
        )
        mm = ac.memory_manager
        mm.count_tokens = MagicMock(return_value=75)  # 75%
        session = make_session([make_message("user", "x")])
        result = ac.check_and_compact(session, model="gpt-4o")
        assert result.triggered is False
        assert result.warning_level == "warning"

    def test_since_last_user_cuts_messages(self):
        """since_last_user=True removes messages before last user"""
        ac = self._make_ac(model_context_window=1000, compact_threshold=0.95)
        mm = ac.memory_manager
        mm.count_tokens = MagicMock(return_value=100)
        session = make_session(
            [
                make_message("user", "first"),
                make_message("assistant", "reply1"),
                make_message("user", "second"),  # last user at index 2
                make_message("assistant", "reply2"),
            ]
        )
        ac.check_and_compact(session, since_last_user=True)
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "second"

    def test_since_last_user_no_user_before(self):
        """last user at index 0 -> no messages removed"""
        ac = self._make_ac(model_context_window=1000, compact_threshold=0.95)
        session = make_session(
            [
                make_message("user", "only"),  # index 0 = last user
                make_message("assistant", "reply"),
            ]
        )
        before = len(session.messages)
        ac.check_and_compact(session, since_last_user=True)
        assert len(session.messages) == before

    def test_since_last_user_no_user_at_all(self):
        """no user messages -> no messages removed"""
        ac = self._make_ac(model_context_window=1000, compact_threshold=0.95)
        session = make_session([make_message("assistant", "no user here")])
        before = len(session.messages)
        ac.check_and_compact(session, since_last_user=True)
        assert len(session.messages) == before


# ---------------------------------------------------------------------------
# AutoCompact._deduplicate_tool_calls
# ---------------------------------------------------------------------------

class TestDeduplicateToolCalls:
    def _make_ac(self, **kwargs) -> AutoCompact:
        mm = make_memory_manager()
        return AutoCompact(memory_manager=mm, **kwargs)

    def test_disabled(self):
        ac = self._make_ac(enable_deduplication=False)
        msgs = [
            make_message(
                "assistant", '{"tool_calls":[{"name":"read","arguments":"{}"}]}'
            ),
            make_message(
                "assistant", '{"tool_calls":[{"name":"read","arguments":"{}"}]}'
            ),
        ]
        result, count = ac._deduplicate_tool_calls(msgs)
        assert result == msgs
        assert count == 0

    def test_no_duplicates(self):
        ac = self._make_ac()
        msgs = [
            make_message(
                "assistant", '{"tool_calls":[{"name":"read","arguments":"{}"}]}'
            ),
            make_message(
                "assistant", '{"tool_calls":[{"name":"edit","arguments":"{}"}]}'
            ),
        ]
        result, count = ac._deduplicate_tool_calls(msgs)
        assert len(result) == 2
        assert count == 0

    def test_single_duplicate(self):
        ac = self._make_ac()
        tc = json.dumps({"tool_calls": [{"name": "bash", "arguments": {"cmd": "ls"}}]})
        msgs = [
            make_message("assistant", tc),
            make_message("assistant", tc),  # duplicate
        ]
        result, count = ac._deduplicate_tool_calls(msgs)
        # Keeps the first one, removes the second
        assert count == 1
        assert len(result) == 1

    def test_multiple_consecutive_duplicates(self):
        ac = self._make_ac()
        tc = json.dumps({"tool_calls": [{"name": "bash", "arguments": {"cmd": "pwd"}}]})
        msgs = [
            make_message("assistant", tc),
            make_message("assistant", tc),
            make_message("assistant", tc),
        ]
        result, count = ac._deduplicate_tool_calls(msgs)
        # Keeps first, removes next 2
        assert count == 2
        assert len(result) == 1

    def test_mixed_duplicates_and_unique(self):
        ac = self._make_ac()
        tc1 = json.dumps(
            {"tool_calls": [{"name": "bash", "arguments": {"cmd": "a"}}]}
        )
        tc2 = json.dumps(
            {"tool_calls": [{"name": "read", "arguments": {"path": "b"}}]}
        )
        msgs = [
            make_message("assistant", tc1),
            make_message("assistant", tc1),  # dup of first
            make_message("assistant", tc2),  # unique
        ]
        result, count = ac._deduplicate_tool_calls(msgs)
        assert count == 1
        assert len(result) == 2

    def test_no_tool_calls_in_content(self):
        ac = self._make_ac()
        msgs = [
            make_message("assistant", "plain text response"),
            make_message("user", "hello"),
        ]
        result, count = ac._deduplicate_tool_calls(msgs)
        assert result == msgs
        assert count == 0

    def test_non_assistant_messages_pass_through(self):
        ac = self._make_ac()
        msgs = [
            make_message("user", "hello"),
            make_message("system", "sys"),
            make_message("tool", "result"),
        ]
        result, count = ac._deduplicate_tool_calls(msgs)
        assert result == msgs
        assert count == 0


# ---------------------------------------------------------------------------
# AutoCompact._extract_tool_calls
# ---------------------------------------------------------------------------

class TestExtractToolCalls:
    def _make_ac(self) -> AutoCompact:
        return AutoCompact(memory_manager=make_memory_manager())

    def test_empty_content(self):
        ac = self._make_ac()
        assert ac._extract_tool_calls("") == []
        assert ac._extract_tool_calls(None) == []

    def test_standard_json_tool_calls(self):
        ac = self._make_ac()
        content = json.dumps(
            {"tool_calls": [{"name": "read", "arguments": '{"path":"a.txt"}'}]}
        )
        result = ac._extract_tool_calls(content)
        assert len(result) == 1
        assert result[0]["name"] == "read"

    def test_function_call_format(self):
        ac = self._make_ac()
        content = json.dumps(
            {"function_call": [{"id": "call_1", "arguments": '{"query":"x"}'}]}
        )
        result = ac._extract_tool_calls(content)
        assert len(result) == 1
        assert result[0]["name"] == "call_1"

    def test_arguments_as_object(self):
        ac = self._make_ac()
        content = json.dumps(
            {
                "tool_calls": [
                    {"name": "edit", "arguments": {"path": "a.txt", "text": "hi"}}
                ]
            }
        )
        result = ac._extract_tool_calls(content)
        assert len(result) == 1
        assert result[0]["name"] == "edit"
        # arguments should be a JSON string
        assert "path" in result[0]["args"]

    def test_json_block_in_markdown(self):
        ac = self._make_ac()
        content = '```json\n{"tool_calls":[{"name":"grep","arguments":"{}"}]}\n```'
        result = ac._extract_tool_calls(content)
        assert len(result) == 1
        assert result[0]["name"] == "grep"

    def test_regex_tool_calls_pattern(self):
        ac = self._make_ac()
        content = '"tool_calls":[{"name":"bash","arguments":"{}"}]'
        result = ac._extract_tool_calls(content)
        assert len(result) == 1
        assert result[0]["name"] == "bash"

    def test_no_matching_pattern(self):
        ac = self._make_ac()
        content = '{"some":"random","content":"without tool_calls"}'
        result = ac._extract_tool_calls(content)
        assert result == []


# ---------------------------------------------------------------------------
# AutoCompact._tool_calls_equal
# ---------------------------------------------------------------------------

class TestToolCallsEqual:
    def _make_ac(self) -> AutoCompact:
        return AutoCompact(memory_manager=make_memory_manager())

    def test_equal(self):
        ac = self._make_ac()
        a = [{"name": "read", "args": '{"path":"a.txt"}'}]
        b = [{"name": "read", "args": '{"path":"a.txt"}'}]
        assert ac._tool_calls_equal(a, b) is True

    def test_different_names(self):
        ac = self._make_ac()
        a = [{"name": "read", "args": '{"path":"a.txt"}'}]
        b = [{"name": "edit", "args": '{"path":"a.txt"}'}]
        assert ac._tool_calls_equal(a, b) is False

    def test_different_args(self):
        ac = self._make_ac()
        a = [{"name": "read", "args": '{"path":"a.txt"}'}]
        b = [{"name": "read", "args": '{"path":"b.txt"}'}]
        assert ac._tool_calls_equal(a, b) is False

    def test_different_length(self):
        ac = self._make_ac()
        a = [{"name": "read", "args": "{}"}]
        b = [{"name": "read", "args": "{}"}, {"name": "edit", "args": "{}"}]
        assert ac._tool_calls_equal(a, b) is False


# ---------------------------------------------------------------------------
# AutoCompact._compact
# ---------------------------------------------------------------------------

class TestCompact:
    def _make_ac(self, **kwargs) -> AutoCompact:
        mm = make_memory_manager()
        return AutoCompact(memory_manager=mm, **kwargs)

    def test_empty_messages(self):
        ac = self._make_ac()
        session = make_session([])
        result = ac._compact(session)
        assert result.triggered is False
        assert result.messages_removed == 0
        assert result.warning_level == "ok"

    def test_only_system_messages(self):
        ac = self._make_ac()
        session = make_session([make_message("system", "sys")])
        result = ac._compact(session)
        assert result.triggered is False
        assert result.messages_removed == 0

    def test_normal_compaction(self):
        ac = self._make_ac()
        msgs = [
            make_message("user", "hello"),
            make_message("assistant", "hi"),
            make_message("user", "q1"),
            make_message("assistant", "a1"),
            make_message("user", "q2"),
            make_message("assistant", "a2"),
            make_message("user", "q3"),
            make_message("assistant", "a3"),
            make_message("user", "q4"),
            make_message("assistant", "a4"),
        ]
        session = make_session(msgs)
        result = ac._compact(session)
        assert result.triggered is True
        assert result.warning_level == "compacted"
        # 10 msgs -> keep 2 (20%) + summary -> 3 total, removed 7
        assert result.messages_removed == 7
        # Verify summary message was inserted
        summaries = [m for m in session.messages if "[上下文压缩]" in m.content]
        assert len(summaries) == 1

    def test_no_messages_to_compress(self):
        """When keep_count * 0.2 >= total non-system, to_compress is empty."""
        ac = self._make_ac()
        # 4 non-system msgs -> keep max(1, int(4*0.2))=1, to_compress=3 -> triggered
        # For to_compress to be empty, we need total <= 5 (keep 1, 0 to compress)
        # But we need system msgs to keep the path where to_compress is empty.
        # Simpler: use system message + 1 non-system = 1 non-system -> keep 1, to_compress empty
        msgs = [
            make_message("system", "sys"),
            make_message("assistant", "hi"),
        ]
        session = make_session(msgs)
        result = ac._compact(session)
        assert result.triggered is False

    def test_compaction_with_dedup_count(self):
        ac = self._make_ac()
        tc = json.dumps(
            {"tool_calls": [{"name": "bash", "arguments": {"cmd": "ls"}}]}
        )
        msgs = [
            make_message("assistant", tc),
            make_message("assistant", tc),
            make_message("assistant", tc),
            make_message("user", "keep"),
            make_message("assistant", "ok"),
        ]
        session = make_session(msgs)
        result = ac._compact(session)
        assert result.triggered is True
        assert result.deduplicated_count >= 1

    def test_compaction_with_error_purge(self):
        ac = self._make_ac(enable_purge_errors=True)
        msgs = [
            make_message("user", "q1"),
            make_message(
                "tool",
                "error result",
                metadata={"role": "tool", "is_error": True},
            ),
            make_message("user", "q2"),
            make_message(
                "tool",
                "error result",
                metadata={"role": "tool", "is_error": True},
            ),
            make_message("user", "q3"),
            make_message(
                "tool",
                "error result",
                metadata={"role": "tool", "is_error": True},
            ),
            make_message("user", "q4"),
            make_message(
                "tool",
                "error result",
                metadata={"role": "tool", "is_error": True},
            ),
            make_message("user", "q5"),
            make_message(
                "tool",
                "error result",
                metadata={"role": "tool", "is_error": True},
            ),
            make_message("user", "q6"),
        ]
        session = make_session(msgs)
        result = ac._compact(session)
        assert result.triggered is True
        # Some old errors should be purged
        assert result.error_removed_count >= 0


# ---------------------------------------------------------------------------
# AutoCompact._generate_summary
# ---------------------------------------------------------------------------

class TestGenerateSummary:
    def _make_ac(self) -> AutoCompact:
        return AutoCompact(memory_manager=make_memory_manager())

    def test_empty_messages(self):
        ac = self._make_ac()
        result = ac._generate_summary([])
        assert "省略了 0 条消息" in result

    def test_file_read_tools(self):
        ac = self._make_ac()
        msgs = [
            make_message("tool", "file content", metadata={"name": "read", "role": "tool"}),
            make_message(
                "tool", "file2 content", metadata={"name": "read_file", "role": "tool"}
            ),
        ]
        result = ac._generate_summary(msgs)
        assert "2 个文件读取" in result

    def test_command_tools(self):
        ac = self._make_ac()
        msgs = [
            make_message("tool", "ls output", metadata={"name": "bash", "role": "tool"}),
            make_message(
                "tool", "pwd output", metadata={"name": "run_command", "role": "tool"}
            ),
        ]
        result = ac._generate_summary(msgs)
        assert "2 个命令" in result

    def test_search_tools(self):
        ac = self._make_ac()
        msgs = [
            make_message(
                "tool", "search result", metadata={"name": "grep", "role": "tool"}
            ),
            make_message(
                "tool", "web result", metadata={"name": "web_search", "role": "tool"}
            ),
        ]
        result = ac._generate_summary(msgs)
        assert "2 次搜索" in result

    def test_write_tools(self):
        ac = self._make_ac()
        msgs = [
            make_message("tool", "ok", metadata={"name": "edit", "role": "tool"}),
            make_message("tool", "ok", metadata={"name": "write_file", "role": "tool"}),
        ]
        result = ac._generate_summary(msgs)
        assert "2 个函数调用" in result

    def test_other_tools(self):
        ac = self._make_ac()
        msgs = [
            make_message(
                "tool", "some result", metadata={"name": "unknown_tool", "role": "tool"}
            ),
        ]
        result = ac._generate_summary(msgs)
        assert "1 个其他工具" in result

    def test_mixed_tools(self):
        ac = self._make_ac()
        msgs = [
            make_message("tool", "file", metadata={"name": "read", "role": "tool"}),
            make_message("tool", "cmd", metadata={"name": "bash", "role": "tool"}),
            make_message(
                "tool",
                "err",
                metadata={"name": "error_handler", "role": "tool", "is_error": True},
            ),
        ]
        result = ac._generate_summary(msgs)
        assert "1 个文件读取" in result
        assert "1 个命令" in result
        assert "1 个错误" in result

    def test_no_tool_messages(self):
        ac = self._make_ac()
        msgs = [
            make_message("user", "hello"),
            make_message("assistant", "hi"),
        ]
        result = ac._generate_summary(msgs)
        assert "无工具调用" in result


# ---------------------------------------------------------------------------
# AutoCompact._purge_old_errors
# ---------------------------------------------------------------------------

class TestPurgeOldErrors:
    def _make_ac(self, **kwargs) -> AutoCompact:
        mm = make_memory_manager()
        return AutoCompact(memory_manager=mm, **kwargs)

    def _err_msg(self, content: str = "error", **kwargs) -> Message:
        return make_message("tool", content, metadata={"role": "tool", **kwargs})

    def _user_msg(self, content: str = "question") -> Message:
        return make_message("user", content)

    def test_empty_messages(self):
        ac = self._make_ac()
        result, count = ac._purge_old_errors([], max_age_rounds=4)
        assert result == []
        assert count == 0

    def test_below_max_age_rounds(self):
        """5 rounds <= 4 max -> nothing purged"""
        ac = self._make_ac()
        msgs = [
            self._user_msg("q1"),
            self._err_msg(),
            self._user_msg("q2"),
            self._err_msg(),
            self._user_msg("q3"),
            self._err_msg(),
            self._user_msg("q4"),
            self._err_msg(),
            self._user_msg("q5"),
            self._err_msg(),
        ]
        result, count = ac._purge_old_errors(msgs, max_age_rounds=4)
        assert count == 0

    def test_old_errors_purged(self):
        """5 rounds > 4 max -> oldest round errors removed"""
        ac = self._make_ac()
        msgs = [
            self._user_msg("q1"),
            self._err_msg("old error 1", is_error=True),
            self._user_msg("q2"),
            self._err_msg("old error 2", is_error=True),
            self._user_msg("q3"),
            self._err_msg("old error 3", is_error=True),
            self._user_msg("q4"),
            self._err_msg("recent error", is_error=True),
            self._user_msg("q5"),
            self._err_msg("recent error 2", is_error=True),
            self._user_msg("q6"),
            self._err_msg("recent error 3", is_error=True),
        ]
        result, count = ac._purge_old_errors(msgs, max_age_rounds=4)
        assert count >= 1
        # Recent errors should still be present
        recent_errs = [m for m in result if m.content == "recent error"]
        assert len(recent_errs) >= 1

    def test_preserves_last_error_in_old_rounds(self):
        """Last error in old rounds is preserved"""
        ac = self._make_ac()
        msgs = [
            self._user_msg("q1"),
            self._err_msg("err1", is_error=True),
            self._err_msg("err2", is_error=True),
            self._user_msg("q2"),
            self._err_msg("recent", is_error=True),
        ]
        # max_age_rounds=1 keeps only the last round; all older errors are removed
        result, count = ac._purge_old_errors(msgs, max_age_rounds=1)
        # Old round (q1+err1+err2) has 2 errors; last 1 is preserved per _purge_old_errors
        assert count == 1
        # err2 (last old error) should be preserved
        old_errs = [m for m in result if m.content == "err2"]
        assert len(old_errs) >= 1

    def test_trailing_messages_merged_to_last_round(self):
        """trailing non-user messages are merged to last round"""
        ac = self._make_ac()
        msgs = [
            self._user_msg("q1"),
            self._err_msg("e1", is_error=True),
            self._user_msg("q2"),
            self._err_msg("trailing error", is_error=True),
        ]
        # max_age_rounds=1: only last round kept; old round has 1 error (e1)
        # preserved_last_error keeps the last error, so removed_count = 0
        result, count = ac._purge_old_errors(msgs, max_age_rounds=1)
        assert count == 0

    def test_no_error_messages(self):
        """non-error tool messages are not removed"""
        ac = self._make_ac()
        msgs = [
            self._user_msg("q1"),
            make_message("tool", "ok result", metadata={"name": "read", "role": "tool"}),
            self._user_msg("q2"),
            make_message(
                "tool", "ok result 2", metadata={"name": "bash", "role": "tool"}
            ),
            self._user_msg("q3"),
        ]
        result, count = ac._purge_old_errors(msgs, max_age_rounds=1)
        assert count == 0
        assert len(result) == len(msgs)


# ---------------------------------------------------------------------------
# AutoCompact._is_error_message
# ---------------------------------------------------------------------------

class TestIsErrorMessage:
    def _make_ac(self) -> AutoCompact:
        return AutoCompact(memory_manager=make_memory_manager())

    def test_non_tool_message(self):
        ac = self._make_ac()
        assert ac._is_error_message(make_message("user", "hello")) is False
        assert ac._is_error_message(make_message("assistant", "hi")) is False
        assert ac._is_error_message(make_message("system", "sys")) is False

    def test_tool_message_no_error(self):
        ac = self._make_ac()
        msg = make_message(
            "tool", "normal result", metadata={"name": "read", "role": "tool"}
        )
        assert ac._is_error_message(msg) is False

    def test_metadata_is_error_flag(self):
        ac = self._make_ac()
        msg = make_message(
            "tool", "some content", metadata={"role": "tool", "is_error": True}
        )
        assert ac._is_error_message(msg) is True

    def test_error_in_name(self):
        ac = self._make_ac()
        for name in ["error_handler", "ExceptionTool", "fail_test", "err_tool"]:
            msg = make_message("tool", "content", metadata={"role": "tool", "name": name})
            assert ac._is_error_message(msg) is True, f"Failed for {name}"

    def test_traceback_in_content(self):
        ac = self._make_ac()
        msg = make_message(
            "tool",
            'File "/a.py", line 1\nTraceback (most recent call last):\n  Error',
            metadata={"role": "tool"},
        )
        assert ac._is_error_message(msg) is True

    def test_error_colon_in_content(self):
        ac = self._make_ac()
        msg = make_message(
            "tool", "Something went wrong\nerror: file not found", metadata={"role": "tool"}
        )
        assert ac._is_error_message(msg) is True

    def test_exception_colon_in_content(self):
        ac = self._make_ac()
        msg = make_message(
            "tool", "Runtime\nexception: null pointer", metadata={"role": "tool"}
        )
        assert ac._is_error_message(msg) is True

    def test_failed_in_content(self):
        ac = self._make_ac()
        msg = make_message(
            "tool", "Command failed: exit 1", metadata={"role": "tool"}
        )
        assert ac._is_error_message(msg) is True

    def test_failure_in_content(self):
        ac = self._make_ac()
        msg = make_message(
            "tool", "Operation failure: timeout", metadata={"role": "tool"}
        )
        assert ac._is_error_message(msg) is True

    def test_critical_in_content(self):
        ac = self._make_ac()
        msg = make_message(
            "tool", "CRITICAL: out of memory", metadata={"role": "tool"}
        )
        assert ac._is_error_message(msg) is True

    def test_fatal_in_content(self):
        ac = self._make_ac()
        msg = make_message(
            "tool", "FATAL: cannot open file", metadata={"role": "tool"}
        )
        assert ac._is_error_message(msg) is True

    def test_metadata_role_overrides_msg_role(self):
        ac = self._make_ac()
        # msg.role is "user" but metadata.role is "tool" -> treated as tool
        msg = make_message(
            "user",
            "error: bad thing",
            metadata={"role": "tool", "is_error": True},
        )
        assert ac._is_error_message(msg) is True
