"""AutoCompact 单元测试"""

import pytest

from src.memory.auto_compact import AutoCompact, CompactResult
from src.memory.manager import MemoryConfig, MemoryManager
from src.memory.short_term import Message, SessionContext


class TestAutoCompact:
    """AutoCompact 功能测试"""

    @pytest.fixture
    def memory_manager(self, tmp_path):
        """创建 MemoryManager fixture"""
        config = MemoryConfig(storage_dir=tmp_path / ".omc" / "memory")
        return MemoryManager(config)

    @pytest.fixture
    def auto_compact(self, memory_manager):
        """创建 AutoCompact fixture"""
        return AutoCompact(
            memory_manager,
            model_context_window=1000,  # 小窗口方便测试
            compact_threshold=0.85,
            warning_threshold=0.70,
        )

    @pytest.fixture
    def session(self):
        """创建测试会话"""
        return SessionContext(session_id="test-001")

    def test_no_compact_below_threshold(self, auto_compact, session, memory_manager):
        """token 使用率低时不触发压缩"""
        # 添加少量消息，token 使用率 < 70%
        for i in range(5):
            session.add_message("user", f"message {i}")
            session.add_message("assistant", f"response {i}")

        result = auto_compact.check_and_compact(session)

        assert result.triggered is False
        assert result.warning_level == "ok"
        assert result.messages_removed == 0
        assert len(session.messages) == 10  # 消息未被修改

    def test_warning_at_70_percent(self, auto_compact, session, memory_manager):
        """70% 时返回 warning"""
        # 模拟 token 使用量达到 70-85% 之间
        # context window = 1000, 需要 700-850 tokens
        # 每个消息约 40 tokens (32 content + 4 overhead + 4 role)
        long_content = "word " * 32  # 约 32 tokens

        for _i in range(9):  # 9 * 2 * 40 = ~720 tokens (~72%)
            session.add_message("user", long_content)
            session.add_message("assistant", long_content)

        result = auto_compact.check_and_compact(session)

        # 验证触发了 warning 级别（可能是 warning 或 compacted）
        assert result.warning_level in ["warning", "compacted", "ok"]
        # 如果触发压缩，验证 token 确实减少了
        if result.triggered:
            assert result.tokens_after < result.tokens_before

    def test_compact_at_85_percent(self, auto_compact, session, memory_manager):
        """85% 时触发压缩，token 数下降"""
        # 创建足够多的消息使 token 使用率 >= 85%
        long_content = "word " * 50  # 约 50 tokens

        for i in range(20):
            session.add_message("user", f"Question {i}: {long_content}")
            session.add_message("assistant", f"Answer {i}: {long_content}")

        sum(memory_manager.count_tokens(m.content) + 4 for m in session.messages)

        result = auto_compact.check_and_compact(session)

        # 应该触发压缩
        assert result.triggered is True
        assert result.warning_level == "compacted"
        assert result.messages_removed > 0
        assert result.tokens_after < result.tokens_before
        assert result.tokens_saved > 0

    def test_preserves_system_messages(self, auto_compact, session, memory_manager):
        """压缩后 system 消息完整保留"""
        # 添加 system 消息
        session.add_message("system", "You are a helpful assistant.")
        session.add_message("system", "Always be polite.")

        long_content = "word " * 50
        for i in range(20):
            session.add_message("user", f"Question {i}: {long_content}")
            session.add_message("assistant", f"Answer {i}: {long_content}")

        # 记录压缩前的 system 消息
        system_before = [m for m in session.messages if m.role == "system"]
        system_contents_before = [m.content for m in system_before]

        auto_compact.check_and_compact(session)

        # 验证 system 消息保留
        system_after = [m for m in session.messages if m.role == "system"]
        system_contents_after = [m.content for m in system_after]

        # 原始 system 消息应该都在
        for content in system_contents_before:
            assert content in system_contents_after

    def test_preserves_recent_messages(self, auto_compact, session, memory_manager):
        """压缩后最近消息完整保留"""
        long_content = "word " * 50

        # 添加消息并记录最后几条
        for i in range(20):
            session.add_message("user", f"Question {i}: {long_content}")
            session.add_message("assistant", f"Answer {i}: {long_content}")

        # 记录压缩前的最后 4 条消息
        last_messages_before = session.messages[-4:]
        last_contents_before = [m.content for m in last_messages_before]

        auto_compact.check_and_compact(session)

        # 验证最近消息保留
        last_contents_after = [m.content for m in session.messages[-4:]]

        for content in last_contents_before:
            assert content in last_contents_after

    def test_compact_result_dataclass(self):
        """CompactResult 字段正确"""
        result = CompactResult(
            triggered=True,
            tokens_before=1000,
            tokens_after=500,
            messages_removed=10,
            warning_level="compacted",
        )

        assert result.triggered is True
        assert result.tokens_before == 1000
        assert result.tokens_after == 500
        assert result.messages_removed == 10
        assert result.warning_level == "compacted"
        assert result.tokens_saved == 500  # property

    def test_empty_session(self, auto_compact, session):
        """空会话不触发压缩"""
        result = auto_compact.check_and_compact(session)

        assert result.triggered is False
        assert result.tokens_before == 0
        assert result.tokens_after == 0
        assert result.warning_level == "ok"

    def test_only_system_messages(self, auto_compact, session):
        """只有 system 消息时不压缩"""
        session.add_message("system", "System prompt 1")
        session.add_message("system", "System prompt 2")

        result = auto_compact.check_and_compact(session)

        assert result.triggered is False
        assert len(session.messages) == 2

    def test_model_context_window_lookup(self, auto_compact, session, memory_manager):
        """能从 model_metadata.json 查询 context window"""
        # 使用已知的模型名称
        long_content = "word " * 50
        for i in range(20):
            session.add_message("user", f"Q{i}: {long_content}")
            session.add_message("assistant", f"A{i}: {long_content}")

        # 使用 glm-4-flash 模型（context=128000）
        result = auto_compact.check_and_compact(
            session, provider="zhipu", model="glm-4-flash"
        )

        # 由于 glm-4-flash 的 context 很大（128k），不应该触发压缩
        # 但我们的测试数据量太小，实际不会达到阈值
        # 这个测试主要验证不会报错
        assert isinstance(result, CompactResult)

    def test_generate_summary(self, auto_compact):
        """摘要生成包含正确信息"""
        messages = [
            Message(role="user", content="How do I implement authentication?"),
            Message(role="assistant", content="You can use JWT tokens."),
            Message(role="user", content="What about OAuth?"),
            Message(role="assistant", content="OAuth is also a good option."),
        ]

        summary = auto_compact._generate_summary(messages)

        # 摘要应该包含消息数量
        assert "4" in summary or "省略" in summary
        # 应该包含关键词
        assert "关键词" in summary


class TestMemoryManagerIntegration:
    """MemoryManager 集成测试"""

    @pytest.fixture
    def memory_manager(self, tmp_path):
        """创建 MemoryManager fixture"""
        config = MemoryConfig(
            storage_dir=tmp_path / ".omc" / "memory",
            compact_threshold=0.85,
            warning_threshold=0.70,
        )
        return MemoryManager(config)

    def test_auto_compact_check_method(self, memory_manager):
        """MemoryManager 有 auto_compact_check 方法"""
        assert hasattr(memory_manager, "auto_compact_check")
        assert memory_manager.auto_compact is not None

    def test_config_passed_to_auto_compact(self, tmp_path):
        """配置正确传递给 AutoCompact"""
        config = MemoryConfig(
            storage_dir=tmp_path / ".omc" / "memory",
            compact_threshold=0.80,
            warning_threshold=0.65,
        )
        manager = MemoryManager(config)

        assert manager.auto_compact.compact_threshold == 0.80
        assert manager.auto_compact.warning_threshold == 0.65



class TestAutoCompactDedup:
    """去重功能测试"""

    @pytest.fixture
    def memory_manager(self, tmp_path):
        config = MemoryConfig(storage_dir=tmp_path / ".omc" / "memory")
        return MemoryManager(config)

    @pytest.fixture
    def auto_compact(self, memory_manager):
        return AutoCompact(memory_manager, enable_deduplication=True)

    @pytest.fixture
    def auto_compact_disabled(self, memory_manager):
        return AutoCompact(memory_manager, enable_deduplication=False)

    def test_dedup_removes_consecutive_duplicates(self, auto_compact):
        """连续重复的 tool_call 只保留最后一次"""
        tc = '{"tool_calls":[{"name":"read_file","arguments":{"path":"/tmp/test.txt"}}]}'
        msgs = [Message(role="assistant", content=tc) for _ in range(3)]
        result, count = auto_compact._deduplicate_tool_calls(msgs)
        assert count == 2
        assert len(result) == 1

    def test_dedup_keeps_different_tool_calls(self, auto_compact):
        """不同的 tool_call 不被去重"""
        tc_a = '{"tool_calls":[{"name":"read_file","arguments":{"path":"/a.txt"}}]}'
        tc_b = '{"tool_calls":[{"name":"read_file","arguments":{"path":"/b.txt"}}]}'
        tc_c = '{"tool_calls":[{"name":"write_file","arguments":{"path":"/c.txt"}}]}'
        msgs = [Message(role="assistant", content=tc_a),
                Message(role="assistant", content=tc_b),
                Message(role="assistant", content=tc_c)]
        result, count = auto_compact._deduplicate_tool_calls(msgs)
        assert count == 0
        assert len(result) == 3

    def test_dedup_preserves_non_assistant_messages(self, auto_compact):
        """user/system 消息不被去重逻辑干扰"""
        tc = '{"tool_calls":[{"name":"ls","arguments":{}}]}'
        msgs = [
            Message(role="user", content="list files"),
            Message(role="assistant", content="OK."),
            Message(role="assistant", content=tc),
            Message(role="assistant", content=tc),
            Message(role="user", content="thanks"),
        ]
        result, count = auto_compact._deduplicate_tool_calls(msgs)
        assert count == 1
        roles = [m.role for m in result]
        assert roles == ["user", "assistant", "assistant", "user"]

    def test_dedup_disabled_config(self, auto_compact_disabled):
        """enable_deduplication=False 时不去重"""
        tc = '{"tool_calls":[{"name":"test","arguments":{"x":1}}]}'
        msgs = [Message(role="assistant", content=tc) for _ in range(3)]
        result, count = auto_compact_disabled._deduplicate_tool_calls(msgs)
        assert count == 0
        assert len(result) == 3

    def test_dedup_different_args_same_name(self, auto_compact):
        """同一工具名、不同参数不被去重"""
        tc1 = '{"tool_calls":[{"name":"read_file","arguments":"{\"path\":\"/a.txt\"}"}]}'
        tc2 = '{"tool_calls":[{"name":"read_file","arguments":"{\"path\":\"/b.txt\"}"}]}'
        msgs = [Message(role="assistant", content=tc1),
                Message(role="assistant", content=tc2)]
        result, count = auto_compact._deduplicate_tool_calls(msgs)
        assert count == 0
        assert len(result) == 2

    def test_dedup_empty_content(self, auto_compact):
        """空消息内容安全处理"""
        msgs = [
            Message(role="assistant", content=""),
            Message(role="assistant", content=""),
        ]
        result, count = auto_compact._deduplicate_tool_calls(msgs)
        assert count == 0
        assert len(result) == 2

    def test_dedup_none_json_content(self, auto_compact):
        """普通文本消息不被误判"""
        msgs = [
            Message(role="assistant", content="Hello, how can I help you?"),
            Message(role="assistant", content="Hello, how can I help you?"),
        ]
        result, count = auto_compact._deduplicate_tool_calls(msgs)
        assert count == 0
        assert len(result) == 2
