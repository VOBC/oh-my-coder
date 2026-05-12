"""
上下文压缩优化 — 智能压缩静态知识，保留动态推理

核心策略：
1. 识别静态知识（文件内容、文档、配置）→ 压缩为摘要
2. 保留动态推理（思维链、决策过程、错误修复）→ 完整保留
3. 分级压缩：根据消息类型和重要性应用不同压缩策略
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MessageType(Enum):
    """消息类型分类"""
    STATIC_KNOWLEDGE = "static"      # 静态知识：文件内容、文档、配置
    DYNAMIC_REASONING = "dynamic"    # 动态推理：思维链、分析过程
    TOOL_EXECUTION = "tool"          # 工具执行：命令输出、搜索结果
    ERROR = "error"                  # 错误信息
    SYSTEM = "system"                # 系统消息
    USER = "user"                    # 用户输入
    ASSISTANT = "assistant"          # 助手回复


class CompressionLevel(Enum):
    """压缩级别"""
    NONE = 0         # 不压缩（保留完整）
    LIGHT = 1        # 轻度压缩（保留关键信息）
    MEDIUM = 2       # 中度压缩（生成摘要）
    HEAVY = 3        # 重度压缩（仅保留元数据）


@dataclass
class CompressionRule:
    """压缩规则"""
    message_type: MessageType
    level: CompressionLevel
    priority: int  # 优先级，数字越小越重要
    description: str


# 默认压缩规则：动态推理 > 用户输入 > 系统消息 > 工具执行 > 静态知识 > 错误
DEFAULT_RULES = [
    CompressionRule(MessageType.DYNAMIC_REASONING, CompressionLevel.NONE, 1, "保留完整推理过程"),
    CompressionRule(MessageType.USER, CompressionLevel.NONE, 2, "保留用户输入"),
    CompressionRule(MessageType.SYSTEM, CompressionLevel.LIGHT, 3, "轻度压缩系统消息"),
    CompressionRule(MessageType.ASSISTANT, CompressionLevel.LIGHT, 4, "轻度压缩助手回复"),
    CompressionRule(MessageType.TOOL_EXECUTION, CompressionLevel.MEDIUM, 5, "中度压缩工具输出"),
    CompressionRule(MessageType.STATIC_KNOWLEDGE, CompressionLevel.HEAVY, 6, "重度压缩静态知识"),
    CompressionRule(MessageType.ERROR, CompressionLevel.MEDIUM, 7, "中度压缩历史错误"),
]


@dataclass
class CompressedMessage:
    """压缩后的消息"""
    original_role: str
    original_content: str
    compressed_content: str
    message_type: MessageType
    compression_level: CompressionLevel
    tokens_saved: int
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextCompressor:
    """上下文压缩器

    智能识别消息类型，应用差异化压缩策略：
    - 静态知识（文件内容、文档）→ 提取关键信息，删除冗余
    - 动态推理（思维链、分析）→ 完整保留
    - 工具执行（命令输出）→ 保留结果，省略过程
    """

    def __init__(self, rules: Optional[list[CompressionRule]] = None):
        self.rules = rules or DEFAULT_RULES
        self.rules_map = {r.message_type: r for r in self.rules}

    def classify_message(self, role: str, content: str) -> MessageType:
        """分类消息类型"""
        # 系统消息
        if role == "system":
            return MessageType.SYSTEM

        # 用户消息
        if role == "user":
            return MessageType.USER

        # 错误消息
        if self._is_error(content):
            return MessageType.ERROR

        # 动态推理（思维链、分析过程）
        if self._is_reasoning(content):
            return MessageType.DYNAMIC_REASONING

        # 静态知识（文件内容、文档、配置）
        if self._is_static_knowledge(content):
            return MessageType.STATIC_KNOWLEDGE

        # 工具执行
        if role == "tool" or self._is_tool_execution(content):
            return MessageType.TOOL_EXECUTION

        # 默认
        return MessageType.ASSISTANT

    def compress(self, role: str, content: str, tokens_before: int) -> CompressedMessage:
        """压缩单条消息"""
        msg_type = self.classify_message(role, content)
        rule = self.rules_map.get(msg_type, DEFAULT_RULES[-1])

        if rule.level == CompressionLevel.NONE:
            return CompressedMessage(
                original_role=role,
                original_content=content,
                compressed_content=content,
                message_type=msg_type,
                compression_level=rule.level,
                tokens_saved=0,
            )

        compressed, saved = self._apply_compression(content, rule.level, tokens_before)

        return CompressedMessage(
            original_role=role,
            original_content=content,
            compressed_content=compressed,
            message_type=msg_type,
            compression_level=rule.level,
            tokens_saved=saved,
        )

    def compress_session(
        self,
        messages: list[dict[str, Any]],
        token_counter: Optional[Any] = None,
    ) -> tuple[list[dict[str, Any]], CompressionSummary]:
        """压缩整个会话

        Args:
            messages: 消息列表，每条是 {"role": str, "content": str}
            token_counter: token 计数器函数

        Returns:
            (压缩后的消息列表, 压缩摘要)
        """
        compressed_messages = []
        total_saved = 0
        type_stats = {t: 0 for t in MessageType}

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            # 估算 token 数
            tokens_before = len(content) // 4 if token_counter is None else token_counter(content)

            result = self.compress(role, content, tokens_before)

            compressed_messages.append({
                "role": role,
                "content": result.compressed_content,
                "_compressed": result.compression_level != CompressionLevel.NONE,
                "_original_type": result.message_type.value,
            })

            total_saved += result.tokens_saved
            type_stats[result.message_type] += 1

        summary = CompressionSummary(
            total_messages=len(messages),
            total_tokens_saved=total_saved,
            type_distribution=type_stats,
        )

        return compressed_messages, summary

    # ===== 内部方法 =====

    def _is_error(self, content: str) -> bool:
        """判断是否为错误消息"""
        error_patterns = [
            r"error:", r"exception:", r"traceback", r"failed:",
            r"^\s*error\s", r"^\s*exception\s",
        ]
        content_lower = content.lower()
        return any(re.search(p, content_lower) for p in error_patterns)

    def _is_reasoning(self, content: str) -> bool:
        """判断是否为动态推理（思维链）"""
        reasoning_patterns = [
            r"让我思考一下",
            r"分析.*原因",
            r"推理.*过程",
            r"决策.*依据",
            r"选择.*因为",
            r"比较.*优劣",
            r"评估.*方案",
            r"思考.*步骤",
            r"^\d+\.\s+(首先|然后|接下来|最后)",
            r"(planning|reasoning|thinking|analysis)",
        ]
        return any(re.search(p, content, re.IGNORECASE) for p in reasoning_patterns)

    def _is_static_knowledge(self, content: str) -> bool:
        """判断是否为静态知识"""
        static_patterns = [
            r"^\s*```\w+",  # 代码块
            r"^\s*#+\s+",   # Markdown 标题
            r"^\s*[-*]\s+", # 列表
            r"文件内容",
            r"文档说明",
            r"配置参数",
            r"^\s*\{",       # JSON
            r"^\s*<",        # XML/HTML
        ]
        return any(re.search(p, content) for p in static_patterns)

    def _is_tool_execution(self, content: str) -> bool:
        """判断是否为工具执行结果"""
        tool_patterns = [
            r"^\s*\$\s+",    # 命令行
            r"^\s*>",        # 命令输出
            r"执行结果",
            r"输出内容",
            r"^\s*\[\d{4}-\d{2}-\d{2}",  # 时间戳日志
        ]
        return any(re.search(p, content) for p in tool_patterns)

    def _apply_compression(
        self,
        content: str,
        level: CompressionLevel,
        tokens_before: int,
    ) -> tuple[str, int]:
        """应用压缩策略"""
        if level == CompressionLevel.LIGHT:
            # 轻度：删除多余空行，合并连续空格
            compressed = re.sub(r"\n{3,}", "\n\n", content)
            compressed = re.sub(r" {2,}", " ", compressed)
            saved = tokens_before - len(compressed) // 4
            return compressed, max(0, saved)

        elif level == CompressionLevel.MEDIUM:
            # 中度：提取关键信息，生成摘要
            compressed = self._extract_key_info(content)
            saved = tokens_before - len(compressed) // 4
            return compressed, max(0, saved)

        elif level == CompressionLevel.HEAVY:
            # 重度：仅保留元数据和关键结果
            compressed = self._extract_metadata(content)
            saved = tokens_before - len(compressed) // 4
            return compressed, max(0, saved)

        return content, 0

    def _extract_key_info(self, content: str) -> str:
        """提取关键信息（中度压缩）"""
        lines = content.split("\n")
        key_lines = []

        for line in lines:
            # 保留包含关键信息的行
            if any(kw in line.lower() for kw in [
                "结果", "成功", "失败", "错误", "警告",
                "result", "success", "fail", "error", "warning",
                "总结", "结论", "summary", "conclusion",
            ]):
                key_lines.append(line)

        if key_lines:
            return "[摘要] " + " | ".join(key_lines[:5])
        return content[:200] + "..." if len(content) > 200 else content

    def _extract_metadata(self, content: str) -> str:
        """提取元数据（重度压缩）"""
        # 统计信息
        lines = content.split("\n")
        code_blocks = len(re.findall(r"```", content)) // 2
        urls = len(re.findall(r"https?://\S+", content))

        meta = f"[压缩内容: {len(lines)}行"
        if code_blocks > 0:
            meta += f", {code_blocks}个代码块"
        if urls > 0:
            meta += f", {urls}个链接"
        meta += "]"

        # 保留第一行（通常是标题/摘要）
        first_line = lines[0][:100] if lines else ""
        return f"{meta}\n{first_line}..."


@dataclass
class CompressionSummary:
    """压缩摘要"""
    total_messages: int
    total_tokens_saved: int
    type_distribution: dict[MessageType, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_messages": self.total_messages,
            "total_tokens_saved": self.total_tokens_saved,
            "type_distribution": {
                k.value: v for k, v in self.type_distribution.items()
            },
        }
