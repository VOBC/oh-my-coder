from __future__ import annotations

"""
短期记忆 - 当前会话上下文

存储当前会话的：
- 对话历史（最近 N 条）
- 当前任务状态
- 上下文变量

设计：
- 存于内存 + 临时文件（会话结束写入长期）
- 支持上下文压缩（当对话过长时）
"""

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Message:
    """单条消息"""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionContext:
    """会话上下文"""

    session_id: str
    project_path: Path | None = None
    task: str | None = None
    messages: list[Message] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str, metadata: dict | None = None):
        """添加消息"""
        self.messages.append(
            Message(role=role, content=content, metadata=metadata or {})
        )
        self.last_active = time.time()

    def get_recent_messages(self, limit: int = 20) -> list[Message]:
        """获取最近 N 条消息"""
        return self.messages[-limit:]

    def to_dict(self) -> dict[str, Any]:
        """序列化"""
        return {
            "session_id": self.session_id,
            "project_path": str(self.project_path) if self.project_path else None,
            "task": self.task,
            "messages": [asdict(m) for m in self.messages],
            "variables": self.variables,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionContext":
        """反序列化"""
        messages = [Message(**m) for m in data.get("messages", [])]
        return cls(
            session_id=data["session_id"],
            project_path=(
                Path(data["project_path"]) if data.get("project_path") else None
            ),
            task=data.get("task"),
            messages=messages,
            variables=data.get("variables", {}),
            created_at=data.get("created_at", time.time()),
            last_active=data.get("last_active", time.time()),
        )


class ShortTermMemory:
    """短期记忆管理器"""

    def __init__(self, storage_dir: Path, max_messages: int = 100):
        """
        Args:
            storage_dir: 存储目录
            max_messages: 单个会话最大消息数（超过后压缩）
        """
        self.storage_dir = storage_dir / "short-term"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_messages = max_messages
        self._current_session: SessionContext | None = None

    def create_session(
        self, project_path: Path | None = None, task: str | None = None
    ) -> SessionContext:
        """创建新会话"""
        session = SessionContext(
            session_id=str(uuid.uuid4())[:8],
            project_path=project_path,
            task=task,
        )
        self._current_session = session
        return session

    def get_current_session(self) -> SessionContext | None:
        """获取当前会话"""
        return self._current_session

    def set_current_session(self, session: SessionContext):
        """设置当前会话"""
        self._current_session = session

    def load_session(self, session_id: str) -> SessionContext | None:
        """加载已有会话"""
        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            data = json.loads(session_file.read_text())
            return SessionContext.from_dict(data)
        return None

    def save_session(self, session: SessionContext):
        """保存会话到临时文件"""
        session_file = self.storage_dir / f"{session.session_id}.json"
        session_file.write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2)
        )

    def compress_if_needed(self, session: SessionContext) -> list[Message]:
        """当消息过多时压缩，返回保留的消息

        .. deprecated::
            此方法已被标记为废弃，请使用 `memory.auto_compact.check_and_compact()`
            替代。新实现基于 token 使用率而非消息条数，更加智能。
        """
        if len(session.messages) <= self.max_messages:
            return session.messages

        # 压缩策略：保留系统消息 + 最近的一半 + 摘要
        system_msgs = [m for m in session.messages if m.role == "system"]
        recent = session.messages[len(system_msgs) :]
        keep = recent[-self.max_messages // 2 :]

        # 摘要丢失的消息
        summary = Message(
            role="system",
            content=f"[记忆压缩] 省略了 {len(session.messages) - len(keep)} 条早期消息",
        )

        session.messages = [*system_msgs, summary, *keep]
        return session.messages

    def clear_expired(self, max_age_hours: int = 24):
        """清理过期会话（超过 max_age_hours）"""
        now = time.time()
        max_age = max_age_hours * 3600

        for f in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                last_active = data.get("last_active", 0)
                if now - last_active > max_age:
                    f.unlink()
            except Exception:
                pass
