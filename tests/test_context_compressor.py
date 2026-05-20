"""测试 context_compressor.py — 上下文压缩模块"""

import pytest

from src.core.context_compressor import (
    DEFAULT_RULES,
    CompressedMessage,
    CompressionLevel,
    CompressionRule,
    CompressionSummary,
    ContextCompressor,
    MessageType,
)

# ===== Enums =====


class TestMessageType:
    def test_values(self):
        assert MessageType.STATIC_KNOWLEDGE.value == "static"
        assert MessageType.DYNAMIC_REASONING.value == "dynamic"
        assert MessageType.TOOL_EXECUTION.value == "tool"
        assert MessageType.ERROR.value == "error"
        assert MessageType.SYSTEM.value == "system"
        assert MessageType.USER.value == "user"
        assert MessageType.ASSISTANT.value == "assistant"

    def test_count(self):
        assert len(MessageType) == 7


class TestCompressionLevel:
    def test_values(self):
        assert CompressionLevel.NONE.value == 0
        assert CompressionLevel.LIGHT.value == 1
        assert CompressionLevel.MEDIUM.value == 2
        assert CompressionLevel.HEAVY.value == 3


class TestCompressionRule:
    def test_create(self):
        rule = CompressionRule(MessageType.USER, CompressionLevel.NONE, 2, "desc")
        assert rule.message_type == MessageType.USER
        assert rule.level == CompressionLevel.NONE


class TestDefaultRules:
    def test_count(self):
        assert len(DEFAULT_RULES) == 7

    def test_reasoning_has_none_level(self):
        r = [r for r in DEFAULT_RULES if r.message_type == MessageType.DYNAMIC_REASONING][0]
        assert r.level == CompressionLevel.NONE

    def test_static_has_heavy_level(self):
        r = [r for r in DEFAULT_RULES if r.message_type == MessageType.STATIC_KNOWLEDGE][0]
        assert r.level == CompressionLevel.HEAVY


# ===== CompressedMessage =====


class TestCompressedMessage:
    def test_create(self):
        msg = CompressedMessage(
            original_role="user",
            original_content="hello",
            compressed_content="hello",
            message_type=MessageType.USER,
            compression_level=CompressionLevel.NONE,
            tokens_saved=0,
        )
        assert msg.original_role == "user"
        assert msg.tokens_saved == 0
        assert msg.metadata == {}


# ===== ContextCompressor =====


class TestContextCompressor:
    @pytest.fixture()
    def compressor(self):
        return ContextCompressor()

    # classify_message
    def test_classify_system(self, compressor):
        assert compressor.classify_message("system", "config") == MessageType.SYSTEM

    def test_classify_user(self, compressor):
        assert compressor.classify_message("user", "hello") == MessageType.USER

    def test_classify_error(self, compressor):
        assert compressor.classify_message("assistant", "Error: something failed") == MessageType.ERROR

    def test_classify_exception(self, compressor):
        assert compressor.classify_message("assistant", "Exception: bad") == MessageType.ERROR

    def test_classify_traceback(self, compressor):
        assert compressor.classify_message("assistant", "Traceback at line 5") == MessageType.ERROR

    def test_classify_reasoning(self, compressor):
        assert compressor.classify_message("assistant", "让我思考一下这个问题") == MessageType.DYNAMIC_REASONING

    def test_classify_reasoning_planning(self, compressor):
        assert compressor.classify_message("assistant", "Planning steps for the project") == MessageType.DYNAMIC_REASONING

    def test_classify_static_code(self, compressor):
        assert compressor.classify_message("assistant", "```python\nprint('hi')\n```") == MessageType.STATIC_KNOWLEDGE

    def test_classify_static_markdown(self, compressor):
        assert compressor.classify_message("assistant", "# Heading\nContent") == MessageType.STATIC_KNOWLEDGE

    def test_classify_static_list(self, compressor):
        assert compressor.classify_message("assistant", "- Item 1\n- Item 2") == MessageType.STATIC_KNOWLEDGE

    def test_classify_static_json(self, compressor):
        assert compressor.classify_message("assistant", '{"key": "value"}') == MessageType.STATIC_KNOWLEDGE

    def test_classify_tool_role(self, compressor):
        assert compressor.classify_message("tool", "output") == MessageType.TOOL_EXECUTION

    def test_classify_tool_execution(self, compressor):
        assert compressor.classify_message("assistant", "执行结果: success") == MessageType.TOOL_EXECUTION

    def test_classify_assistant_default(self, compressor):
        assert compressor.classify_message("assistant", "Here's the answer") == MessageType.ASSISTANT

    # compress
    def test_compress_none_level(self, compressor):
        result = compressor.compress("user", "hello world", 10)
        assert result.compressed_content == "hello world"
        assert result.tokens_saved == 0
        assert result.compression_level == CompressionLevel.NONE

    def test_compress_light(self, compressor):
        # System messages get LIGHT compression
        content = "system   config\n\n\n\nmore"
        result = compressor.compress("system", content, 20)
        assert result.compression_level == CompressionLevel.LIGHT
        assert "system config" in result.compressed_content  # spaces merged
        assert result.tokens_saved >= 0

    def test_compress_medium(self, compressor):
        # Tool execution gets MEDIUM compression
        content = "line1\n成功执行\nline3\n错误信息\n结果: done"
        result = compressor.compress("tool", content, 50)
        assert result.compression_level == CompressionLevel.MEDIUM
        assert result.tokens_saved >= 0

    def test_compress_heavy(self, compressor):
        # Static knowledge gets HEAVY compression
        content = "```python\nprint('hello')\n```\nMore content here\nLine 3"
        result = compressor.compress("assistant", content, 30)
        assert result.compression_level == CompressionLevel.HEAVY
        assert "压缩内容" in result.compressed_content

    def test_compress_heavy_with_urls(self, compressor):
        content = "# Doc\nhttps://example.com\nhttps://test.com\nMore lines"
        result = compressor.compress("assistant", content, 30)
        assert "链接" in result.compressed_content

    # compress_session
    def test_compress_session(self, compressor):
        messages = [
            {"role": "system", "content": "You are an assistant"},
            {"role": "user", "content": "Help me"},
            {"role": "assistant", "content": "Error: failed"},
        ]
        compressed, summary = compressor.compress_session(messages)
        assert len(compressed) == 3
        assert summary.total_messages == 3
        assert summary.total_tokens_saved >= 0

    def test_compress_session_with_token_counter(self, compressor):
        messages = [{"role": "user", "content": "test"}]
        counter = lambda c: 5  # noqa: E731
        compressed, summary = compressor.compress_session(messages, token_counter=counter)
        assert summary.total_messages == 1

    def test_compress_session_empty(self, compressor):
        compressed, summary = compressor.compress_session([])
        assert compressed == []
        assert summary.total_messages == 0

    def test_compress_session_type_distribution(self, compressor):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ]
        compressed, summary = compressor.compress_session(messages)
        assert summary.type_distribution[MessageType.SYSTEM] == 1
        assert summary.type_distribution[MessageType.USER] == 1

    # custom rules
    def test_custom_rules(self):
        rules = [CompressionRule(MessageType.USER, CompressionLevel.HEAVY, 1, "Custom")]
        comp = ContextCompressor(rules=rules)
        result = comp.compress("user", "Hello world content here", 20)
        assert result.compression_level == CompressionLevel.HEAVY

    # _is_error internal
    def test_is_error_failed(self, compressor):
        assert compressor._is_error("Failed: timeout")

    def test_is_error_no_match(self, compressor):
        assert not compressor._is_error("Normal content")

    # _is_reasoning
    def test_is_reasoning_analysis(self, compressor):
        assert compressor._is_reasoning("分析问题的原因")

    def test_is_reasoning_no_match(self, compressor):
        assert not compressor._is_reasoning("Simple response")

    # _is_static_knowledge
    def test_is_static_file(self, compressor):
        assert compressor._is_static_knowledge("文件内容如下")

    def test_is_static_xml(self, compressor):
        assert compressor._is_static_knowledge("<tag>value</tag>")

    def test_is_static_no_match(self, compressor):
        assert not compressor._is_static_knowledge("Plain text here")

    # _is_tool_execution
    def test_is_tool_command(self, compressor):
        assert compressor._is_tool_execution("$ ls -la")

    def test_is_tool_timestamp(self, compressor):
        assert compressor._is_tool_execution("[2026-01-01 10:00] Log entry")

    # _apply_compression
    def test_light_compress_whitespace(self, compressor):
        content = "a\n\n\n\nb   c"
        result, saved = compressor._apply_compression(content, CompressionLevel.LIGHT, 20)
        assert "a\n\nb c" in result

    def test_medium_compress_with_keywords(self, compressor):
        content = "Line1\n成功完成\nLine3\n结果: good"
        result, saved = compressor._apply_compression(content, CompressionLevel.MEDIUM, 30)
        assert "摘要" in result

    def test_medium_compress_no_keywords(self, compressor):
        content = "Plain text without keywords"
        result, saved = compressor._apply_compression(content, CompressionLevel.MEDIUM, 30)
        # Should truncate if > 200 chars, or return original if short
        assert len(result) <= 203  # 200 + "..."

    def test_heavy_compress(self, compressor):
        content = "Title\nLine1\nLine2\nLine3\n```code```"
        result, saved = compressor._apply_compression(content, CompressionLevel.HEAVY, 30)
        assert "压缩内容" in result
        assert "代码块" in result

    def test_heavy_compress_no_codeblocks(self, compressor):
        content = "Just\nplain\nlines"
        result, saved = compressor._apply_compression(content, CompressionLevel.HEAVY, 15)
        assert "压缩内容" in result
        assert "代码块" not in result


# ===== CompressionSummary =====


class TestCompressionSummary:
    def test_to_dict(self):
        dist = {MessageType.USER: 2, MessageType.SYSTEM: 1}
        s = CompressionSummary(total_messages=3, total_tokens_saved=10, type_distribution=dist)
        d = s.to_dict()
        assert d["total_messages"] == 3
        assert d["total_tokens_saved"] == 10
        assert d["type_distribution"]["user"] == 2
