"""
Agent 执行透明性 - 完整执行过程记录

核心功能：
1. AgentTrace 类：记录每个 Agent 的完整执行过程
2. 记录内容：开始时间、每步操作（读/写文件、调API）、耗时、输出摘要、结束时间
3. 存储到 .omc/traces/{session_id}/{agent_name}.jsonl
4. CLI: omc trace list / omc trace show <agent>
"""

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class TraceEventType(str, Enum):
    """Trace 事件类型"""

    START = "start"
    END = "end"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    CALL_API = "call_api"
    RUN_COMMAND = "run_command"
    THINKING = "thinking"
    ERROR = "error"
    METADATA = "metadata"


@dataclass
class TraceEvent:
    """Trace 单条事件"""

    timestamp: str
    type: str
    step: int
    duration_ms: float = 0.0
    description: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    output_preview: str = ""  # 输出摘要（前 200 字符）

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentTrace:
    """单个 Agent 的完整执行轨迹"""

    trace_id: str
    agent_name: str
    session_id: str
    workflow_id: str = ""
    started_at: str = ""
    ended_at: str = ""
    status: str = "running"  # running | completed | failed
    events: list[TraceEvent] = field(default_factory=list)
    total_duration_ms: float = 0.0
    error: str | None = None
    output_summary: str = ""  # 最终输出摘要
    metadata: dict[str, Any] = field(default_factory=dict)

    def _now(self) -> str:
        return datetime.now().isoformat()

    def start(self) -> None:
        """开始追踪"""
        self.started_at = self._now()
        self.events.append(
            TraceEvent(
                timestamp=self.started_at,
                type=TraceEventType.START.value,
                step=len(self.events),
                description=f"Agent '{self.agent_name}' 开始执行",
            )
        )

    def end(
        self,
        status: str = "completed",
        output_summary: str = "",
        error: str | None = None,
    ) -> None:
        """结束追踪"""
        self.ended_at = self._now()
        self.status = status
        self.output_summary = output_summary
        self.error = error
        if self.started_at and self.ended_at:
            start_dt = datetime.fromisoformat(self.started_at)
            end_dt = datetime.fromisoformat(self.ended_at)
            self.total_duration_ms = (end_dt - start_dt).total_seconds() * 1000
        self.events.append(
            TraceEvent(
                timestamp=self.ended_at,
                type=TraceEventType.END.value,
                step=len(self.events),
                duration_ms=self.total_duration_ms,
                description=f"Agent '{self.agent_name}' 结束 ({status})",
                output_preview=output_summary[:200] if output_summary else "",
            )
        )

    def log(
        self,
        event_type: TraceEventType,
        description: str,
        details: dict[str, Any] | None = None,
        output_preview: str = "",
    ) -> None:
        """记录任意事件"""
        now = self._now()
        # 计算距开始的时间
        duration_ms = 0.0
        if self.started_at:
            try:
                start_dt = datetime.fromisoformat(self.started_at)
                end_dt = datetime.fromisoformat(now)
                duration_ms = (end_dt - start_dt).total_seconds() * 1000
            except ValueError:
                pass

        self.events.append(
            TraceEvent(
                timestamp=now,
                type=event_type.value,
                step=len(self.events),
                duration_ms=duration_ms,
                description=description,
                details=details or {},
                output_preview=output_preview[:200] if output_preview else "",
            )
        )

    def log_read(self, file_path: str, lines: int = 0) -> None:
        """记录读取文件"""
        self.log(
            TraceEventType.READ_FILE,
            f"读取文件: {file_path}",
            details={"path": file_path, "lines": lines},
        )

    def log_write(self, file_path: str, lines: int = 0) -> None:
        """记录写入文件"""
        self.log(
            TraceEventType.WRITE_FILE,
            f"写入文件: {file_path}",
            details={"path": file_path, "lines": lines},
        )

    def log_api(self, model: str, tokens: int = 0, duration_ms: float = 0.0) -> None:
        """记录 API 调用"""
        self.log(
            TraceEventType.CALL_API,
            f"调用 API: {model}",
            details={"model": model, "tokens": tokens, "duration_ms": duration_ms},
        )

    def log_command(self, command: str, exit_code: int = 0) -> None:
        """记录命令执行"""
        self.log(
            TraceEventType.RUN_COMMAND,
            f"执行命令: {command[:80]}{'...' if len(command) > 80 else ''}",
            details={"command": command, "exit_code": exit_code},
        )

    def log_error(self, error_msg: str) -> None:
        """记录错误"""
        self.log(
            TraceEventType.ERROR,
            f"发生错误: {error_msg}",
            details={"error": error_msg},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "workflow_id": self.workflow_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error,
            "output_summary": self.output_summary,
            "metadata": self.metadata,
            "events": [e.to_dict() for e in self.events],
        }

    def to_jsonl_line(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Trace Store
# ---------------------------------------------------------------------------


class TraceStore:
    """
    Trace 存储管理器
    存储路径: .omc/traces/{session_id}/{agent_name}_{timestamp}.jsonl
    """

    _instance: Optional["TraceStore"] = None
    _lock = threading.Lock()

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path.home() / ".omc" / "traces"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> "TraceStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _session_dir(self, session_id: str) -> Path:
        return self.base_dir / session_id

    def save(self, trace: AgentTrace) -> Path:
        """保存 trace 到文件"""
        session_dir = self._session_dir(trace.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        # 文件名: agent_name.jsonl
        safe_name = trace.agent_name.replace("/", "_").replace("\\", "_")
        file_path = session_dir / f"{safe_name}.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(trace.to_jsonl_line() + "\n")
        return file_path

    def list_sessions(self) -> list[str]:
        """列出所有 session"""
        if not self.base_dir.exists():
            return []
        return sorted(
            [d.name for d in self.base_dir.iterdir() if d.is_dir()], reverse=True
        )

    def list_traces(self, session_id: str) -> list[dict[str, Any]]:
        """列出某个 session 下的所有 trace"""
        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            return []
        traces = []
        for f in sorted(
            session_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            if f.suffix == ".jsonl":
                try:
                    with open(f, encoding="utf-8") as fh:
                        for line in fh:
                            line = line.strip()
                            if line:
                                traces.append(json.loads(line))
                except (json.JSONDecodeError, OSError):
                    pass
        return traces

    def get_trace(self, session_id: str, agent_name: str) -> dict[str, Any] | None:
        """获取指定 agent 的最新 trace"""
        session_dir = self._session_dir(session_id)
        safe_name = agent_name.replace("/", "_").replace("\\", "_")
        file_path = session_dir / f"{safe_name}.jsonl"
        if not file_path.exists():
            return None
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
                if lines:
                    return json.loads(lines[-1])
        except (json.JSONDecodeError, OSError):
            pass
        return None

    def get_latest_session(self) -> str | None:
        """获取最新 session ID"""
        sessions = self.list_sessions()
        return sessions[0] if sessions else None

    def get_all_agents_in_session(self, session_id: str) -> list[str]:
        """获取某个 session 下所有 agent 名"""
        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            return []
        agents = []
        for f in session_dir.iterdir():
            if f.suffix == ".jsonl":
                agents.append(f.stem)
        return sorted(agents)


# ---------------------------------------------------------------------------
# Trace Context Manager
# ---------------------------------------------------------------------------


class TraceContext:
    """与某个 Agent 执行绑定的 trace 上下文"""

    def __init__(
        self,
        agent_name: str,
        session_id: str | None = None,
        workflow_id: str = "",
    ) -> None:
        self.agent_name = agent_name
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.workflow_id = workflow_id
        self._trace: AgentTrace | None = None
        self._store = TraceStore.get_instance()

    def start(self) -> AgentTrace:
        trace = AgentTrace(
            trace_id=str(uuid.uuid4()),
            agent_name=self.agent_name,
            session_id=self.session_id,
            workflow_id=self.workflow_id,
        )
        trace.start()
        self._trace = trace
        return trace

    def stop(
        self,
        status: str = "completed",
        output_summary: str = "",
        error: str | None = None,
    ) -> None:
        if self._trace is not None:
            self._trace.end(status=status, output_summary=output_summary, error=error)
            self._store.save(self._trace)

    def log(
        self,
        event_type: TraceEventType,
        description: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        if self._trace is not None:
            self._trace.log(event_type, description, details)

    def log_read(self, path: str, lines: int = 0) -> None:
        if self._trace is not None:
            self._trace.log_read(path, lines)

    def log_write(self, path: str, lines: int = 0) -> None:
        if self._trace is not None:
            self._trace.log_write(path, lines)

    def log_api(self, model: str, tokens: int = 0, duration_ms: float = 0.0) -> None:
        if self._trace is not None:
            self._trace.log_api(model, tokens, duration_ms)

    def log_command(self, command: str, exit_code: int = 0) -> None:
        if self._trace is not None:
            self._trace.log_command(command, exit_code)

    def log_error(self, msg: str) -> None:
        if self._trace is not None:
            self._trace.log_error(msg)


# Global trace context for current agent execution
_current_trace: dict[str, TraceContext] = {}


def get_trace_context(agent_name: str) -> TraceContext | None:
    return _current_trace.get(agent_name)


def set_trace_context(agent_name: str, ctx: TraceContext) -> None:
    _current_trace[agent_name] = ctx


def remove_trace_context(agent_name: str) -> None:
    _current_trace.pop(agent_name, None)
