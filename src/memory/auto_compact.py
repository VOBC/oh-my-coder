"""Auto Compact - 上下文自动压缩

当会话 token 接近模型上下文窗口限制时，自动压缩早期消息。
参考 OpenCode 的 95% 阈值策略，但使用更保守的 85%。
"""

import json
from dataclasses import dataclass
from pathlib import Path

from .short_term import Message, SessionContext


@dataclass
class CompactResult:
    """压缩结果"""

    triggered: bool  # 是否触发了压缩
    tokens_before: int
    tokens_after: int
    messages_removed: int
    warning_level: str  # "ok" / "warning" / "critical" / "compacted"

    @property
    def tokens_saved(self) -> int:
        return self.tokens_before - self.tokens_after


class AutoCompact:
    """自动上下文压缩器

    监控会话 token 使用量，在接近模型上下文窗口限制时自动压缩。
    """

    DEFAULT_CONTEXT_WINDOW = 128000

    def __init__(
        self,
        memory_manager,
        model_context_window: int = DEFAULT_CONTEXT_WINDOW,
        compact_threshold: float = 0.85,
        warning_threshold: float = 0.70,
    ):
        """
        Args:
            memory_manager: MemoryManager 实例，用于 count_tokens
            model_context_window: 模型上下文窗口大小（默认 128k）
            compact_threshold: 触发压缩的阈值（默认 0.85 = 85%）
            warning_threshold: 发出警告的阈值（默认 0.70 = 70%）
        """
        self.memory_manager = memory_manager
        self.model_context_window = model_context_window
        self.compact_threshold = compact_threshold
        self.warning_threshold = warning_threshold

    def _get_model_context_window(self, provider: str = "", model: str = "") -> int:
        """从 model_metadata.json 获取模型的 context window"""
        if not model:
            return self.model_context_window

        try:
            metadata_path = (
                Path(__file__).parent.parent / "models" / "model_metadata.json"
            )
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text())
                model_key = model.lower()
                if model_key in metadata and "context" in metadata[model_key]:
                    return metadata[model_key]["context"]
        except Exception:
            pass

        return self.model_context_window

    def _count_session_tokens(self, session: SessionContext) -> int:
        """计算会话总 token 数"""
        total = 0
        for msg in session.messages:
            # 每条消息加上角色标记的 token 开销
            total += self.memory_manager.count_tokens(msg.content)
            total += 4  # 角色标记和格式开销估算
        return total

    def check_and_compact(
        self,
        session: SessionContext,
        provider: str = "",
        model: str = "",
    ) -> CompactResult:
        """检查并执行压缩

        Args:
            session: 当前会话上下文
            provider: 模型提供商（用于查 context window）
            model: 模型名称（用于查 context window）

        Returns:
            CompactResult: 压缩结果
        """
        context_window = self._get_model_context_window(provider, model)
        tokens_before = self._count_session_tokens(session)
        usage_ratio = tokens_before / context_window

        # 确定警告级别
        if usage_ratio >= self.compact_threshold:
            warning_level = "critical"
        elif usage_ratio >= self.warning_threshold:
            warning_level = "warning"
        else:
            warning_level = "ok"

        # 如果低于压缩阈值，只返回警告
        if usage_ratio < self.compact_threshold:
            return CompactResult(
                triggered=False,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_removed=0,
                warning_level=warning_level,
            )

        # 执行压缩
        return self._compact(session, target_ratio=0.5)

    def _compact(
        self, session: SessionContext, target_ratio: float = 0.5
    ) -> CompactResult:
        """执行压缩

        策略：
        1. 保留所有 system 消息
        2. 保留最近 20% 的消息
        3. 对中间消息生成摘要（简单实现：提取关键词）
        4. 替换 session.messages

        Args:
            session: 当前会话
            target_ratio: 目标压缩比例（保留多少比例的消息）

        Returns:
            CompactResult: 压缩结果
        """
        if not session.messages:
            return CompactResult(
                triggered=False,
                tokens_before=0,
                tokens_after=0,
                messages_removed=0,
                warning_level="ok",
            )

        tokens_before = self._count_session_tokens(session)
        original_count = len(session.messages)

        # 分离 system 消息和非 system 消息
        system_msgs: list[Message] = [m for m in session.messages if m.role == "system"]
        non_system_msgs: list[Message] = [
            m for m in session.messages if m.role != "system"
        ]

        if not non_system_msgs:
            # 只有 system 消息，不压缩
            return CompactResult(
                triggered=False,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_removed=0,
                warning_level="ok",
            )

        # 保留最近 20% 的消息
        keep_count = max(1, int(len(non_system_msgs) * 0.2))
        recent_msgs = non_system_msgs[-keep_count:]

        # 中间部分需要压缩的消息
        to_compress = non_system_msgs[:-keep_count]

        if not to_compress:
            # 消息太少，不压缩
            return CompactResult(
                triggered=False,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_removed=0,
                warning_level="ok",
            )

        # 生成摘要（简单实现：提取关键词和统计信息）
        summary_content = self._generate_summary(to_compress)
        summary_msg = Message(
            role="system",
            content=f"[上下文压缩] {summary_content}",
        )

        # 重建消息列表
        session.messages = [*system_msgs, summary_msg, *recent_msgs]

        tokens_after = self._count_session_tokens(session)
        messages_removed = original_count - len(session.messages)

        return CompactResult(
            triggered=True,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            messages_removed=messages_removed,
            warning_level="compacted",
        )

    def _generate_summary(self, messages: list[Message]) -> str:
        """生成消息摘要（简单实现）

        实际生产环境可以调用 LLM 生成更智能的摘要。
        这里使用简单的关键词提取和统计。

        Args:
            messages: 需要摘要的消息列表

        Returns:
            str: 摘要文本
        """
        user_count = sum(1 for m in messages if m.role == "user")
        assistant_count = sum(1 for m in messages if m.role == "assistant")

        # 提取关键词（简单实现：找出现频率较高的词）
        all_text = " ".join(m.content for m in messages)
        words = [w.lower() for w in all_text.split() if len(w) > 3 and w.isalpha()]

        # 统计词频
        word_freq = {}
        for w in words:
            word_freq[w] = word_freq.get(w, 0) + 1

        # 取 top 5 关键词
        top_keywords = sorted(word_freq.items(), key=lambda x: -x[1])[:5]
        keywords_str = ", ".join(w for w, _ in top_keywords) if top_keywords else "无"

        return (
            f"省略了 {len(messages)} 条消息 "
            f"({user_count} user, {assistant_count} assistant)。"
            f"关键词: {keywords_str}"
        )
