"""测试 context_compressor.py — 上下文压缩"""


from src.core.context_compressor import (
    DEFAULT_RULES,
    CompressedMessage,
    CompressionLevel,
    CompressionRule,
    CompressionSummary,
    ContextCompressor,
    MessageType,
)

# ===== MessageType =====


class TestMessageType:
    def test_values(self):
        assert MessageType.STATIC_KNOWLEDGE.value == "static"
        assert MessageType.DYNAMIC_REASONING.value == "dynamic"


# ===== CompressionLevel =====


class TestCompressionLevel:
    def test_ordering(self):
        assert CompressionLevel.NONE.value < CompressionLevel.LIGHT.value


# ===== CompressionRule =====


class TestCompressionRule:
    def test_create(self):
        r = CompressionRule(MessageType.USER, CompressionLevel.NONE, 2, "保留用户输入")
        assert r.priority == 2


# ===== DEFAULT_RULES =====


class TestDefaultRules:
    def test_count(self):
        assert len(DEFAULT_RULES) == 7

    def test_reasoning_is_none(self):
        r = [r for r in DEFAULT_RULES if r.message_type == MessageType.DYNAMIC_REASONING][0]
        assert r.level == CompressionLevel.NONE


# ===== ContextCompressor =====


class TestClassifyMessage:
    def test_system(self):
        c = ContextCompressor()
        assert c.classify_message("system", "any") == MessageType.SYSTEM

    def test_user(self):
        c = ContextCompressor()
        assert c.classify_message("user", "any") == MessageType.USER

    def test_error(self):
        c = ContextCompressor()
        assert c.classify_message("assistant", "Error: something failed") == MessageType.ERROR

    def test_error_traceback(self):
        c = ContextCompressor()
        assert c.classify_message("assistant", "Traceback (most recent call)") == MessageType.ERROR

    def test_reasoning_chinese(self):
        c = ContextCompressor()
        assert c.classify_message("assistant", "让我思考一下这个问题") == MessageType.DYNAMIC_REASONING

    def test_reasoning_english(self):
        c = ContextCompressor()
        assert c.classify_message("assistant", "My reasoning process shows") == MessageType.DYNAMIC_REASONING

    def test_static_code_block(self):
        c = ContextCompressor()
        assert c.classify_message("assistant", "```python\nprint('hi')\n```") == MessageType.STATIC_KNOWLEDGE

    def test_static_markdown_heading(self):
        c = ContextCompressor()
        assert c.classify_message("assistant", "# 标题\n内容") == MessageType.STATIC_KNOWLEDGE

    def test_static_json(self):
        c = ContextCompressor()
        assert c.classify_message("assistant", "{\n  \"key\": \"value\"\n}") == MessageType.STATIC_KNOWLEDGE

    def test_tool_role(self):
        c = ContextCompressor()
        assert c.classify_message("tool", "output") == MessageType.TOOL_EXECUTION

    def test_tool_execution(self):
        c = ContextCompressor()
        assert c.classify_message("assistant", "执行结果：成功") == MessageType.TOOL_EXECUTION

    def test_default_assistant(self):
        c = ContextCompressor()
        assert c.classify_message("assistant", "简单的回复") == MessageType.ASSISTANT

    def test_custom_rules(self):
        rule = CompressionRule(MessageType.USER, CompressionLevel.MEDIUM, 1, "压缩用户")
        c = ContextCompressor(rules=[rule])
        assert c.classify_message("user", "hello") == MessageType.USER


class TestCompress:
    def test_none_level(self):
        c = ContextCompressor()
        result = c.compress("user", "hello world", 10)
        assert result.compression_level == CompressionLevel.NONE
        assert result.compressed_content == "hello world"
        assert result.tokens_saved == 0

    def test_light_compression(self):
        c = ContextCompressor()
        content = "line1\n\n\n\nline2\n\n\n\nline3"
        result = c.compress("system", content, 50)
        assert result.compression_level == CompressionLevel.LIGHT
        assert result.tokens_saved > 0
        assert "\n\n\n" not in result.compressed_content

    def test_heavy_compression(self):
        c = ContextCompressor()
        content = "# Title\nline1\nline2\nline3\nline4\nline5\n```python\ncode\n```"
        result = c.compress("assistant", content, 100)
        assert result.compression_level == CompressionLevel.HEAVY
        assert "压缩内容" in result.compressed_content

    def test_medium_compression_with_keywords(self):
        c = ContextCompressor()
        content = "some text\n结果：成功完成\n更多文本\n错误：nothing\n最终总结"
        result = c.compress("tool", content, 80)
        assert result.compression_level == CompressionLevel.MEDIUM
        assert "摘要" in result.compressed_content or len(result.compressed_content) < len(content)


class TestCompressSession:
    def test_basic(self):
        c = ContextCompressor()
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "让我思考一下"},
        ]
        compressed, summary = c.compress_session(messages)
        assert len(compressed) == 3
        assert summary.total_messages == 3

    def test_with_token_counter(self):
        c = ContextCompressor()
        messages = [{"role": "user", "content": "test"}]
        compressed, summary = c.compress_session(messages, token_counter=lambda x: len(x))
        assert summary.total_messages == 1

    def test_type_distribution(self):
        c = ContextCompressor()
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Error: bug"},
        ]
        _, summary = c.compress_session(messages)
        assert summary.type_distribution[MessageType.USER] == 1
        assert summary.type_distribution[MessageType.ERROR] == 1


# ===== CompressedMessage =====


class TestCompressedMessage:
    def test_create(self):
        m = CompressedMessage(
            original_role="user",
            original_content="hello",
            compressed_content="hello",
            message_type=MessageType.USER,
            compression_level=CompressionLevel.NONE,
            tokens_saved=0,
        )
        assert m.original_role == "user"


# ===== CompressionSummary =====


class TestCompressionSummary:
    def test_to_dict(self):
        s = CompressionSummary(
            total_messages=10,
            total_tokens_saved=500,
            type_distribution={MessageType.USER: 5, MessageType.ASSISTANT: 5},
        )
        d = s.to_dict()
        assert d["total_messages"] == 10
        assert d["total_tokens_saved"] == 500
        assert "user" in d["type_distribution"]
