"""Auto Compact - 上下文自动压缩

当会话 token 接近模型上下文窗口限制时，自动压缩早期消息。
参考 OpenCode 的 95% 阈值策略，但使用更保守的 85%。
"""

import json
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .short_term import Message, SessionContext


@dataclass
class CompactResult:
    """压缩结果"""

    triggered: bool  # 是否触发了压缩
    tokens_before: int
    tokens_after: int
    messages_removed: int
    warning_level: str  # "ok" / "warning" / "critical" / "compacted"
    deduplicated_count: int = 0  # 去重次数（连续重复的 tool_call 结果数）

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
        enable_deduplication: bool = True,
    ):
        """
        Args:
            memory_manager: MemoryManager 实例，用于 count_tokens
            model_context_window: 模型上下文窗口大小（默认 128k）
            compact_threshold: 触发压缩的阈值（默认 0.85 = 85%）
            warning_threshold: 发出警告的阈值（默认 0.70 = 70%）
            enable_deduplication: 是否启用工具调用去重（默认 True）
        """
        self.memory_manager = memory_manager
        self.model_context_window = model_context_window
        self.compact_threshold = compact_threshold
        self.warning_threshold = warning_threshold
        self.enable_deduplication = enable_deduplication

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
                deduplicated_count=0,
            )

        # 执行压缩
        return self._compact(session, target_ratio=0.5)

    def _deduplicate_tool_calls(
        self, messages: list[Message]
    ) -> tuple[list[Message], int]:
        """检测并去除连续重复的 tool_call 结果

        遍历 assistant 消息，找出连续重复的 tool_call 结果
        （相同工具名称 + 相同参数），只保留最后一次。

        Args:
            messages: 消息列表（按时间顺序）

        Returns:
            (去重后的消息列表, 被去重的次数)
        """
        if not self.enable_deduplication:
            return messages, 0

        result: list[Message] = []
        dedup_count = 0
        i = 0

        while i < len(messages):
            msg = messages[i]

            # 只处理 assistant 消息，尝试解析 tool_call
            if msg.role != "assistant":
                result.append(msg)
                i += 1
                continue

            # 提取 tool_call 信息
            current_calls = self._extract_tool_calls(msg.content)
            if not current_calls:
                result.append(msg)
                i += 1
                continue

            # 收集连续重复的 tool_call 结果
            # current_calls 是本条消息里的所有 tool_call
            # 检查下一条消息是否也是 assistant，且 tool_call 相同
            consecutive_dups: list[tuple[Message, int]] = []  # (消息, 被去重的tool_call数)
            j = i + 1

            while j < len(messages):
                next_msg = messages[j]
                if next_msg.role != "assistant":
                    break
                next_calls = self._extract_tool_calls(next_msg.content)
                if not next_calls:
                    break
                # 判断是否完全相同（工具名 + 参数都一样）
                if self._tool_calls_equal(current_calls, next_calls):
                    consecutive_dups.append((next_msg, len(next_calls)))
                    j += 1
                else:
                    break

            if consecutive_dups:
                # 保留当前消息（最后一次），删除之前的重复
                dedup_count += sum(n for _, n in consecutive_dups)
                result.append(msg)
                i = j
            else:
                result.append(msg)
                i += 1

        return result, dedup_count

    def _extract_tool_calls(self, content: str) -> list[dict[str, Any]]:
        """从 assistant 消息内容中提取 tool_call 列表

        支持多种格式：
        - {"tool_calls": [...]} (标准 JSON)
        - function_call 格式
        - 嵌套在 JSON 块中

        Returns:
            tool_call 列表，每个 dict 包含 name/id 和 arguments
        """
        if not content:
            return []

        # 尝试 JSON 解析（处理 tool_calls 字段）
        try:
            # 先尝试直接解析整个 content
            data = json.loads(content)
            tool_calls = data.get("tool_calls") or data.get("function_call") or []
            if isinstance(tool_calls, list):
                normalized = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        name = tc.get("name") or tc.get("id") or ""
                        args = tc.get("arguments") or ""
                        if isinstance(args, str):
                            args_str = args
                        else:
                            args_str = json.dumps(args, sort_keys=True)
                        normalized.append({"name": name, "args": args_str})
                return normalized
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试从文本中提取 tool_calls JSON 块
        patterns = [
            r'"tool_calls"\s*:\s*(\[.*?\])',
            r'"function_call"\s*:\s*(\[.*?\])',
            r'```json\s*(.*?)\s*```',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    tc_list = json.loads(match.group(1))
                    if isinstance(tc_list, list):
                        normalized = []
                        for tc in tc_list:
                            if isinstance(tc, dict):
                                name = tc.get("name") or tc.get("id") or ""
                                args = tc.get("arguments") or ""
                                if isinstance(args, str):
                                    args_str = args
                                else:
                                    args_str = json.dumps(args, sort_keys=True)
                                normalized.append({"name": name, "args": args_str})
                        if normalized:
                            return normalized
                except (json.JSONDecodeError, TypeError):
                    continue

        return []

    def _tool_calls_equal(
        self, a: list[dict[str, Any]], b: list[dict[str, Any]]
    ) -> bool:
        """判断两组 tool_call 是否完全相同（用于去重检测）"""
        if len(a) != len(b):
            return False
        for tc_a, tc_b in zip(a, b):
            if tc_a["name"] != tc_b["name"]:
                return False
            if tc_a["args"] != tc_b["args"]:
                return False
        return True

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
                deduplicated_count=0,
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
                deduplicated_count=0,
            )

        # 1. 工具调用去重（先对全量 non_system_msgs 去重，再分片）
        deduped_non_system, dedup_count = self._deduplicate_tool_calls(non_system_msgs)

        # 重新计算 keep_count 和分片（基于去重后的消息数）
        keep_count = max(1, int(len(deduped_non_system) * 0.2))
        recent_msgs = deduped_non_system[-keep_count:]
        to_compress = deduped_non_system[:-keep_count]

        if not to_compress:
            return CompactResult(
                triggered=False,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_removed=0,
                warning_level="ok",
                deduplicated_count=dedup_count,
            )

        # 2. 生成摘要（简单实现：提取关键词和统计信息）
        summary_parts = []
        if dedup_count > 0:
            summary_parts.append(f"[去重: {dedup_count} 次重复 tool_call]")
        summary_parts.append(self._generate_summary(to_compress))
        summary_content = " ".join(summary_parts)
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
            deduplicated_count=dedup_count,
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
