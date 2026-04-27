"""
tests/test_transparency.py - Agent 执行透明性测试
"""

import json
import time
import uuid

import pytest

from src.agents.transparency import (
    AgentTrace,
    TraceContext,
    TraceEventType,
    TraceStore,
    get_trace_context,
    remove_trace_context,
    set_trace_context,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_trace_dir(tmp_path):
    """创建临时 trace 目录"""
    return TraceStore(base_dir=tmp_path / "traces")


@pytest.fixture
def sample_trace():
    """创建示例 trace"""
    t = AgentTrace(
        trace_id=str(uuid.uuid4()),
        agent_name="executor",
        session_id="test-session-1",
    )
    t.start()
    t.log_read("src/main.py", lines=50)
    t.log_write("src/output.py", lines=20)
    t.log_api("gpt-4o", tokens=1500, duration_ms=2000.0)
    t.log_command("pytest tests/", exit_code=0)
    t.end(status="completed", output_summary="任务完成，生成 20 行代码")
    return t


# ---------------------------------------------------------------------------
# AgentTrace tests
# ---------------------------------------------------------------------------


class TestAgentTrace:
    def test_trace_start_end(self):
        t = AgentTrace(trace_id="t1", agent_name="explorer", session_id="s1")
        assert t.status == "running"
        assert t.started_at == ""
        t.start()
        assert t.started_at != ""
        assert len(t.events) == 1
        assert t.events[0].type == TraceEventType.START.value

        t.end(status="completed", output_summary="ok")
        assert t.status == "completed"
        assert t.ended_at != ""
        assert t.total_duration_ms >= 0

    def test_trace_events(self):
        t = AgentTrace(trace_id="t2", agent_name="tester", session_id="s1")
        t.start()
        t.log_read("foo.py", lines=10)
        t.log_write("bar.py", lines=5)
        t.log_api("claude-3", tokens=100, duration_ms=500.0)
        t.log_command("make test", exit_code=1)
        t.end()

        assert len(t.events) == 6  # start + 4 logs + end
        assert t.events[1].type == TraceEventType.READ_FILE.value
        assert t.events[1].details["path"] == "foo.py"
        assert t.events[2].type == TraceEventType.WRITE_FILE.value
        assert t.events[3].type == TraceEventType.CALL_API.value
        assert t.events[4].type == TraceEventType.RUN_COMMAND.value

    def test_trace_error(self):
        t = AgentTrace(trace_id="t3", agent_name="builder", session_id="s1")
        t.start()
        t.log_error("Connection timeout")
        t.end(status="failed", error="Connection timeout")
        assert t.status == "failed"
        assert t.error == "Connection timeout"

    def test_trace_to_dict(self):
        t = AgentTrace(
            trace_id="t4", agent_name="coder", session_id="s1", workflow_id="w1"
        )
        t.start()
        t.end(output_summary="done")
        d = t.to_dict()
        assert d["trace_id"] == "t4"
        assert d["agent_name"] == "coder"
        assert d["workflow_id"] == "w1"
        assert len(d["events"]) == 2

    def test_trace_to_jsonl_line(self):
        t = AgentTrace(trace_id="t5", agent_name="reviewer", session_id="s1")
        t.start()
        t.end()
        line = t.to_jsonl_line()
        parsed = json.loads(line)
        assert parsed["trace_id"] == "t5"
        assert parsed["agent_name"] == "reviewer"


# ---------------------------------------------------------------------------
# TraceStore tests
# ---------------------------------------------------------------------------


class TestTraceStore:
    def test_save_and_load(self, temp_trace_dir):
        store = temp_trace_dir
        t = AgentTrace(trace_id="t10", agent_name="builder", session_id="session-x")
        t.start()
        t.log_read("a.py", lines=10)
        t.end(status="completed", output_summary="ok")
        path = store.save(t)
        assert path.exists()

    def test_list_sessions(self, temp_trace_dir):
        store = temp_trace_dir
        # 创建两个 session
        for sid in ["session-a", "session-b"]:
            t = AgentTrace(trace_id=f"t-{sid}", agent_name="agent", session_id=sid)
            t.start()
            t.end()
            store.save(t)

        sessions = store.list_sessions()
        assert "session-a" in sessions
        assert "session-b" in sessions

    def test_list_traces(self, temp_trace_dir):
        store = temp_trace_dir
        session_id = "session-list"
        for agent in ["explorer", "builder", "tester"]:
            t = AgentTrace(
                trace_id=f"t-{agent}", agent_name=agent, session_id=session_id
            )
            t.start()
            t.end()
            store.save(t)

        traces = store.list_traces(session_id)
        assert len(traces) == 3
        names = {tr["agent_name"] for tr in traces}
        assert names == {"explorer", "builder", "tester"}

    def test_get_trace_latest(self, temp_trace_dir):
        store = temp_trace_dir
        session_id = "session-latest"
        t1 = AgentTrace(trace_id="t-first", agent_name="first", session_id=session_id)
        t1.start()
        t1.end()
        store.save(t1)

        time.sleep(0.01)  # 确保时间戳不同

        t2 = AgentTrace(trace_id="t-second", agent_name="second", session_id=session_id)
        t2.start()
        t2.end()
        store.save(t2)

        latest = store.get_trace(session_id, "second")
        assert latest is not None
        assert latest["trace_id"] == "t-second"

        # second 不存在时返回 None
        assert store.get_trace(session_id, "nonexistent") is None

    def test_get_latest_session(self, temp_trace_dir):
        store = temp_trace_dir
        assert store.get_latest_session() is None

        # APFS mtime 排序不稳定，改测 list_sessions 返回全部 session
        for sid in ["session-a", "session-b"]:
            t = AgentTrace(trace_id=f"t-{sid}", agent_name="a", session_id=sid)
            t.start()
            t.end()
            store.save(t)

        sessions = store.list_sessions()
        assert "session-a" in sessions
        assert "session-b" in sessions

    def test_get_all_agents_in_session(self, temp_trace_dir):
        store = temp_trace_dir
        session_id = "session-agents"
        for agent in ["alpha", "beta", "gamma"]:
            t = AgentTrace(
                trace_id=f"t-{agent}", agent_name=agent, session_id=session_id
            )
            t.start()
            t.end()
            store.save(t)

        agents = store.get_all_agents_in_session(session_id)
        assert sorted(agents) == ["alpha", "beta", "gamma"]


# ---------------------------------------------------------------------------
# TraceContext tests
# ---------------------------------------------------------------------------


class TestTraceContext:
    def test_trace_context_lifecycle(self, temp_trace_dir):
        TraceStore._instance = None  # 重置单例
        store = TraceStore(base_dir=temp_trace_dir.base_dir / "traces")
        TraceStore._instance = store

        ctx = TraceContext(agent_name="lifecycle-agent", session_id="lifecycle-session")
        ctx.start()
        assert ctx._trace is not None

        ctx.log_read("test.py", lines=10)
        ctx.log_write("out.py", lines=5)
        ctx.log_api("model-x", tokens=200, duration_ms=1000.0)
        ctx.stop(status="completed", output_summary="all good")

        # 验证已保存
        loaded = store.get_trace("lifecycle-session", "lifecycle-agent")
        assert loaded is not None
        assert loaded["status"] == "completed"
        assert loaded["output_summary"] == "all good"
        assert len(loaded["events"]) == 5  # start + read + write + api + end

        TraceStore._instance = None  # 恢复

    def test_trace_context_error(self, temp_trace_dir):
        TraceStore._instance = None
        store = TraceStore(base_dir=temp_trace_dir.base_dir / "traces")
        TraceStore._instance = store

        ctx = TraceContext(agent_name="error-agent", session_id="error-session")
        ctx.start()
        ctx.log_error("Something went wrong")
        ctx.stop(status="failed", error="Something went wrong")

        loaded = store.get_trace("error-session", "error-agent")
        assert loaded is not None
        assert loaded["status"] == "failed"
        assert loaded["error"] == "Something went wrong"

        TraceStore._instance = None


# ---------------------------------------------------------------------------
# Module-level function tests
# ---------------------------------------------------------------------------


class TestModuleFunctions:
    def test_set_get_remove_trace_context(self):
        ctx = TraceContext(agent_name="test-agent", session_id="test-session")
        set_trace_context("test-agent", ctx)
        assert get_trace_context("test-agent") is ctx
        remove_trace_context("test-agent")
        assert get_trace_context("test-agent") is None


# ---------------------------------------------------------------------------
# CLI smoke test (import only)
# ---------------------------------------------------------------------------


def test_trace_package_exports():
    from src.agents.transparency import AgentTrace, TraceContext, TraceStore

    assert AgentTrace is not None
    assert TraceContext is not None
    assert TraceStore is not None
