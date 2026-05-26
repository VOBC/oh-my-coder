
# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"
"""Auto Compact - 上下文自动压缩


当会话 token 接近模型上下文窗口限制时，自动压缩早期消息。
参考 OpenCode 的 95% 阈值策略，但使用 95%。
"""

import json
import re
from dataclasses import dataclass
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
    error_removed_count: int = 0  # 清理的历史 error 消息数

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
        compact_threshold: float = 0.95,
        warning_threshold: float = 0.70,
        enable_deduplication: bool = True,
        enable_purge_errors: bool = True,
    ):
        """
        Args:
            memory_manager: MemoryManager 实例，用于 count_tokens
            model_context_window: 模型上下文窗口大小（默认 128k）
            compact_threshold: 触发压缩的阈值（默认 0.95 = 95%）
            warning_threshold: 发出警告的阈值（默认 0.70 = 70%）
            enable_deduplication: 是否启用工具调用去重（默认 True）
            enable_purge_errors: 是否启用历史错误消息清理（默认 True）
        """
        self.memory_manager = memory_manager
        self.model_context_window = model_context_window
        self.compact_threshold = compact_threshold
        self.warning_threshold = warning_threshold
        self.enable_deduplication = enable_deduplication
        self.enable_purge_errors = enable_purge_errors

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
        force: bool = False,
        since_last_user: bool = False,
    ) -> CompactResult:
        """检查并执行压缩

        Args:
            session: 当前会话上下文
            provider: 模型提供商（用于查 context window）
            model: 模型名称（用于查 context window）
            force: 强制压缩（忽略阈值检查，默认 False）
            since_last_user: 从最后用户消息开始清理（默认 False）

        Returns:
            CompactResult: 压缩结果
        """
        context_window = self._get_model_context_window(provider, model)

        # 如果指定 since_last_user，裁剪消息从最后一条 user 开始
        if since_last_user:
            messages = session.messages
            last_user_idx = None
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].role == "user":
                    last_user_idx = i
                    break
            if last_user_idx is not None and last_user_idx > 0:
                session.messages = messages[last_user_idx:]

        tokens_before = self._count_session_tokens(session)
        usage_ratio = tokens_before / context_window

        # 确定警告级别
        if usage_ratio >= self.compact_threshold:
            warning_level = "critical"
        elif usage_ratio >= self.warning_threshold:
            warning_level = "warning"
        else:
            warning_level = "ok"

        # 如果低于压缩阈值且非强制模式，只返回警告
        if not force and usage_ratio < self.compact_threshold:
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
        for tc_a, tc_b in zip(a, b):  # noqa: B905
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

        # 1. 工具调用去重（先对全量 non_system_msgs 去重，再分片）
        deduped_non_system, dedup_count = self._deduplicate_tool_calls(non_system_msgs)

        # 2. 清理历史 error 消息（清理 4 回合前的 error）
        if self.enable_purge_errors:
            purged_non_system, error_count = self._purge_old_errors(deduped_non_system, max_age_rounds=4)
        else:
            purged_non_system, error_count = deduped_non_system, 0

        # 基于清理后的消息重新分片
        keep_count = max(1, int(len(purged_non_system) * 0.2))
        recent_msgs = purged_non_system[-keep_count:]
        to_compress = purged_non_system[:-keep_count]

        if not to_compress:
            return CompactResult(
                triggered=False,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                messages_removed=0,
                warning_level="ok",
                deduplicated_count=dedup_count,
                error_removed_count=error_count,
            )

        # 3. 生成摘要（简单实现：提取关键词和统计信息）
        summary_parts = []
        if dedup_count > 0:
            summary_parts.append(f"[去重: {dedup_count} 次重复 tool_call]")
        if error_count > 0:
            summary_parts.append(f"[已清理 {error_count} 个历史错误]")
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
            error_removed_count=error_count,
        )

    def _generate_summary(self, messages: list[Message]) -> str:
        """生成消息摘要

        按消息类型分类统计，输出格式：
        省略了 X 条消息（Y 个文件读取, Z 个命令, W 个错误, ...）

        Args:
            messages: 需要摘要的消息列表

        Returns:
            str: 摘要文本
        """
        file_reads = 0
        commands = 0
        errors = 0
        function_calls = 0
        searches = 0
        other_tool = 0

        for msg in messages:
            if msg.role == "tool":
                name = (msg.metadata.get("name") or "").lower()
                content_lower = msg.content.lower()
                is_err = (
                    msg.metadata.get("is_error") is True
                    or "error" in name
                    or "exception" in name
                    or any(k in content_lower for k in ["error:", "traceback", "exception:", "failed:"])
                )
                if is_err:
                    errors += 1
                elif name in ("read", "read_file", "read_file_list"):
                    file_reads += 1
                elif name in ("bash", "execute", "command", "run_command"):
                    commands += 1
                elif name in ("grep", "search", "web_search", "find"):
                    searches += 1
                elif name in ("edit", "write", "write_file", "create_file"):
                    function_calls += 1
                else:
                    other_tool += 1

        parts = []
        if file_reads > 0:
            parts.append(f"{file_reads} 个文件读取")
        if commands > 0:
            parts.append(f"{commands} 个命令")
        if errors > 0:
            parts.append(f"{errors} 个错误")
        if searches > 0:
            parts.append(f"{searches} 次搜索")
        if function_calls > 0:
            parts.append(f"{function_calls} 个函数调用")
        if other_tool > 0:
            parts.append(f"{other_tool} 个其他工具")

        detail = ", ".join(parts) if parts else "无工具调用"
        return f"省略了 {len(messages)} 条消息（{detail}）"


    # ------------------------------------------------------------------ P1-2: Error Purge ---------------------------------------------------------

    def _purge_old_errors(
        self, messages: list[Message], max_age_rounds: int = 4
    ) -> tuple[list[Message], int]:
        """清理历史 error 消息

        删除超过 max_age_rounds 回合的历史 error 消息。
        需保留的回合内的 error 消息不受影响。
        超出阈值的旧回合：清除所有 error，但保留最后 1 条 error。

        回合定义：两 user 消息之间的所有消息（含开头的 user）。
        最后一段 trailing 内容（不包含 user 的消息）合并到最后一回合。

        Args:
            messages: 消息列表（按时间顺序）
            max_age_rounds: 最大保留的回合数（默认 4）

        Returns:
            (清理后的消息列表, 被清理的 error 消息数)
        """
        if not messages:
            return messages, 0

        # 将消息按回合分组
        # 回合 = 从上一个 user 到下一个 user 之前（含开头 user，不含下一个 user）
        # 最后一个 user 之后的内容（trailing）→ 单独作为最后一个 round
        rounds: list[list[Message]] = []
        current_round: list[Message] = []

        for msg in messages:
            if msg.role == "user" and current_round:
                rounds.append(current_round)
                current_round = []
            current_round.append(msg)

        # trailing 内容作为最后一个 round 追加
        if current_round:
            rounds.append(current_round)

        total_rounds = len(rounds)
        if total_rounds <= max_age_rounds:
            return messages, 0

        # 旧回合：超过 max_age_rounds 的部分（会被压缩的中间段）
        old_round_count = total_rounds - max_age_rounds
        old_rounds = rounds[:old_round_count]
        keep_rounds = rounds[old_round_count:]

        # 旧回合中所有 error 消息
        old_error_msgs = [
            m for round_msgs in old_rounds for m in round_msgs
            if self._is_error_message(m)
        ]

        # 保留旧回合中最后 1 条 error
        preserved_last_error: list[Message] = [old_error_msgs[-1]] if old_error_msgs else []

        # 旧回合：删除所有 error 消息
        old_kept: list[Message] = [
            m for round_msgs in old_rounds for m in round_msgs
            if not self._is_error_message(m)
        ]
        removed_count = len(old_error_msgs) - len(preserved_last_error)

        # 重建：旧回合保留非 error + 最后 1 条 error + 近 max_age_rounds 回合（全部保留）
        purged = old_kept + preserved_last_error + [
            m for round_msgs in keep_rounds for m in round_msgs
        ]

        # 按原始顺序排序
        msg_id_to_index = {id(m): i for i, m in enumerate(messages)}
        purged.sort(key=lambda m: msg_id_to_index.get(id(m), 0))

        return purged, removed_count

    def _is_error_message(self, msg: Message) -> bool:
        """判断消息是否为 error 类型

        检测依据：
        1. metadata.role == "tool" 且 name 包含 error/exception/fail/err
        2. metadata.is_error == True
        3. tool role 的 content 包含 traceback/error:/exception: 等关键词
        """
        meta = msg.metadata or {}

        # 兼容：role 可能在 Message.role 或 metadata.role 中
        is_tool_msg = msg.role == "tool" or meta.get("role") == "tool"
        if not is_tool_msg:
            return False

        # metadata 明确标注
        if meta.get("is_error"):
            return True
        name = (meta.get("name") or "").lower()
        if any(k in name for k in ("error", "exception", "fail", "err")):
            return True
        # tool 结果内容含 traceback / error:
        content_lower = (msg.content or "").lower()
        error_keywords = (
            "traceback",
            "error:",
            "exception:",
            "failed:",
            "failure:",
            "critical:",
            "fatal:",
        )
        if any(kw in content_lower for kw in error_keywords):
            return True

        return False
