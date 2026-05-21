"""Tests for health_check.py"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.health_check import (
    AgentHealth,
    AgentStatus,
    HealthCheckResult,
    HealthChecker,
    format_health_display,
)


# ── AgentStatus ──────────────────────────────────────────────────

class TestAgentStatus:
    def test_values(self):
        assert AgentStatus.HEALTHY.value == "healthy"
        assert AgentStatus.STALE.value == "stale"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.REASSIGNED.value == "reassigned"


# ── AgentHealth ──────────────────────────────────────────────────

class TestAgentHealth:
    def test_defaults(self):
        h = AgentHealth(agent_name="a1")
        assert h.status == AgentStatus.HEALTHY
        assert h.task_id is None
        assert h.retry_count == 0
        assert h.last_error is None
        assert h.workflow_id is None
        assert h.step_index == -1
        assert h.MAX_RETRIES == 3

    def test_touch(self):
        h = AgentHealth(agent_name="a1")
        h.status = AgentStatus.STALE
        old = h.last_heartbeat
        time.sleep(0.01)
        h.touch()
        assert h.last_heartbeat > old
        assert h.status == AgentStatus.HEALTHY

    def test_touch_no_stale_reset(self):
        h = AgentHealth(agent_name="a1")
        h.status = AgentStatus.FAILED
        h.touch()
        # touch only resets STALE -> HEALTHY
        assert h.status == AgentStatus.FAILED

    def test_is_stale(self):
        h = AgentHealth(agent_name="a1")
        h.last_heartbeat = time.time() - 600
        assert h.is_stale(threshold=300) is True
        assert h.is_stale(threshold=700) is False

    def test_is_stale_not_stale(self):
        h = AgentHealth(agent_name="a1")
        assert h.is_stale() is False

    def test_record_failure_below_limit(self):
        h = AgentHealth(agent_name="a1")
        exceeded = h.record_failure("err1")
        assert exceeded is False
        assert h.retry_count == 1
        assert h.status == AgentStatus.STALE
        assert h.last_error == "err1"

    def test_record_failure_at_limit(self):
        h = AgentHealth(agent_name="a1", retry_count=2)
        exceeded = h.record_failure("err_final")
        assert exceeded is True
        assert h.retry_count == 3
        assert h.status == AgentStatus.FAILED

    def test_record_failure_resets_heartbeat(self):
        h = AgentHealth(agent_name="a1")
        h.last_heartbeat = 0
        h.record_failure("err")
        assert h.last_heartbeat > 0

    def test_can_retry(self):
        h = AgentHealth(agent_name="a1")
        assert h.can_retry() is True
        h.retry_count = 3
        assert h.can_retry() is False

    def test_to_dict(self):
        h = AgentHealth(agent_name="a1", task_id="t1", workflow_id="w1", step_index=2)
        d = h.to_dict()
        assert d["agent_name"] == "a1"
        assert d["status"] == "healthy"
        assert d["task_id"] == "t1"
        assert d["workflow_id"] == "w1"
        assert d["step_index"] == 2
        assert "MAX_RETRIES" not in d
        assert isinstance(d["last_heartbeat"], str)


# ── HealthCheckResult ────────────────────────────────────────────

class TestHealthCheckResult:
    def test_defaults(self):
        r = HealthCheckResult(check_id="abc", checked_agents=0, healthy_count=0,
                               stale_count=0, failed_count=0, reassigned_count=0)
        assert r.check_id == "abc"
        assert r.reassignments == []
        assert r.timestamp != ""

    def test_to_dict(self):
        r = HealthCheckResult(check_id="x1", checked_agents=2, healthy_count=1,
                               stale_count=1, failed_count=0, reassigned_count=0)
        d = r.to_dict()
        assert "check_id" not in d
        assert d["checked_agents"] == 2
        assert d["healthy_count"] == 1


# ── HealthChecker ────────────────────────────────────────────────

@pytest.fixture
def checker(tmp_path):
    return HealthChecker(state_dir=tmp_path / "health", max_retries=3)


class TestHealthCheckerInit:
    def test_creates_state_dir(self, tmp_path):
        d = tmp_path / "nested" / "health"
        hc = HealthChecker(state_dir=d)
        assert d.exists()

    def test_default_params(self, tmp_path):
        hc = HealthChecker(state_dir=tmp_path / "h")
        assert hc.check_interval == 60.0
        assert hc.stale_threshold == 300.0
        assert hc.max_retries == 3

    def test_custom_params(self, tmp_path):
        hc = HealthChecker(state_dir=tmp_path / "h", check_interval=10,
                           stale_threshold=60, max_retries=5)
        assert hc.check_interval == 10
        assert hc.stale_threshold == 60
        assert hc.max_retries == 5


class TestRegisterAgent:
    def test_register(self, checker):
        h = checker.register_agent("a1", task_id="t1", workflow_id="w1", step_index=0)
        assert h.agent_name == "a1"
        assert h.task_id == "t1"
        assert h.status == AgentStatus.HEALTHY
        assert h.MAX_RETRIES == checker.max_retries
        assert "a1" in checker._agent_health

    def test_register_overwrite(self, checker):
        checker.register_agent("a1", task_id="old")
        checker.register_agent("a1", task_id="new")
        assert checker._agent_health["a1"].task_id == "new"


class TestUnregisterAgent:
    def test_unregister(self, checker):
        checker.register_agent("a1")
        assert checker.unregister_agent("a1") is True
        assert "a1" not in checker._agent_health

    def test_unregister_not_registered(self, checker):
        assert checker.unregister_agent("ghost") is True

    def test_unregister_removes_active_task(self, checker):
        checker.register_agent("a1")
        checker._active_tasks["a1"] = MagicMock()
        checker.unregister_agent("a1")
        assert "a1" not in checker._active_tasks


class TestHeartbeat:
    def test_heartbeat_registered(self, checker):
        checker.register_agent("a1")
        assert checker.heartbeat("a1") is True

    def test_heartbeat_unregistered(self, checker):
        assert checker.heartbeat("ghost") is False

    def test_heartbeat_touches(self, checker):
        h = checker.register_agent("a1")
        h.last_heartbeat = 0
        checker.heartbeat("a1")
        assert checker._agent_health["a1"].last_heartbeat > 0


class TestRecordFailure:
    def test_record_failure_below_limit(self, checker):
        exceeded = checker.record_failure("a1", "error1")
        assert exceeded is False
        assert checker._agent_health["a1"].retry_count == 1

    def test_record_failure_exceeds_limit(self, checker):
        checker.register_agent("a1")
        for i in range(2):
            checker._agent_health["a1"].record_failure(f"err{i}")
        exceeded = checker.record_failure("a1", "final_err")
        assert exceeded is True

    def test_record_failure_unregistered_agent(self, checker):
        # Should auto-register
        exceeded = checker.record_failure("new_agent", "err", workflow_id="w1")
        assert "new_agent" in checker._agent_health
        assert exceeded is False

    def test_record_failure_notification(self, checker):
        notifications = []
        checker.on_notification = lambda t, b: notifications.append((t, b))
        checker.record_failure("a1", "err")
        assert len(notifications) == 1
        assert "重试" in notifications[0][0]

    def test_record_failure_exceeded_notification(self, checker):
        notifications = []
        checker.on_notification = lambda t, b: notifications.append((t, b))
        h = checker.register_agent("a1")
        h.retry_count = 2  # one more will exceed
        checker.record_failure("a1", "err")
        assert len(notifications) == 1
        assert "失败" in notifications[0][0]


class TestReassignTask:
    def test_reassign_to_idle_agent(self, checker):
        checker.register_agent("a1")
        checker.register_agent("a2")
        checker._active_tasks["a1"] = MagicMock()  # a1 is busy
        step = MagicMock(agent_name="step1")
        result = checker.reassign_task("a1", "w1", step)
        assert result == "a2"

    def test_reassign_no_idle(self, checker):
        checker.register_agent("a1")
        checker._active_tasks["a1"] = MagicMock()
        step = MagicMock(agent_name="step1")
        result = checker.reassign_task("a1", "w1", step)
        assert result is None

    def test_reassign_no_other_agents(self, checker):
        step = MagicMock(agent_name="step1")
        result = checker.reassign_task("a1", "w1", step)
        assert result is None


class TestCheckAll:
    @pytest.mark.asyncio
    async def test_check_all_empty(self, checker):
        result = await checker._check_all()
        assert result is None

    @pytest.mark.asyncio
    async def test_check_all_healthy(self, checker):
        checker.register_agent("a1")
        result = await checker._check_all()
        assert result.healthy_count == 1
        assert result.stale_count == 0

    @pytest.mark.asyncio
    async def test_check_all_stale_retries(self, checker):
        checker.stale_threshold = 0.01
        h = checker.register_agent("a1")
        time.sleep(0.02)
        result = await checker._check_all()
        assert result.stale_count == 1
        assert result.reassigned_count == 1

    @pytest.mark.asyncio
    async def test_check_all_stale_exceeds_retries(self, checker):
        checker.stale_threshold = 0.01
        h = checker.register_agent("a1")
        h.retry_count = 3  # already at max
        time.sleep(0.02)
        result = await checker._check_all()
        assert result.failed_count == 1

    @pytest.mark.asyncio
    async def test_check_all_skips_failed(self, checker):
        h = checker.register_agent("a1")
        h.status = AgentStatus.FAILED
        result = await checker._check_all()
        assert result.checked_agents == 0

    @pytest.mark.asyncio
    async def test_check_all_skips_reassigned(self, checker):
        h = checker.register_agent("a1")
        h.status = AgentStatus.REASSIGNED
        result = await checker._check_all()
        assert result.checked_agents == 0


class TestStartStop:
    def test_start_stop(self, checker):
        checker.check_interval = 600
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(checker.start())
            assert checker._check_task is not None
            # cancel the check loop directly
            checker._stop_event.set()
            checker._check_task.cancel()
            try:
                loop.run_until_complete(checker._check_task)
            except asyncio.CancelledError:
                pass
            checker._check_task = None
            checker._stop_event = None
        finally:
            loop.close()

    def test_start_idempotent(self, checker):
        checker.check_interval = 600
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(checker.start())
            task = checker._check_task
            loop.run_until_complete(checker.start())
            assert checker._check_task is task
            # cleanup
            checker._stop_event.set()
            checker._check_task.cancel()
            try:
                loop.run_until_complete(checker._check_task)
            except asyncio.CancelledError:
                pass
            checker._check_task = None
            checker._stop_event = None
        finally:
            loop.close()

    def test_stop_when_not_started(self, checker):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(checker.stop())
        finally:
            loop.close()


class TestGetAllHealth:
    def test_empty(self, checker):
        assert checker.get_all_health() == {}

    def test_with_agents(self, checker):
        checker.register_agent("a1")
        result = checker.get_all_health()
        assert "a1" in result
        assert result["a1"]["status"] == "healthy"


class TestGetSummary:
    def test_empty(self, checker):
        s = checker.get_summary()
        assert s["total_registered"] == 0
        assert s["is_running"] is False

    def test_with_agents(self, checker):
        checker.register_agent("a1")
        h2 = checker.register_agent("a2")
        h2.status = AgentStatus.STALE
        s = checker.get_summary()
        assert s["total_registered"] == 2
        assert s["healthy"] == 1
        assert s["stale"] == 1


class TestPersistence:
    def test_save_health_log(self, checker):
        h = checker.register_agent("a1")
        checker._save_health_log(h)
        log_file = checker.state_dir / "health_a1.json"
        assert log_file.exists()
        data = json.loads(log_file.read_text())
        assert data["agent_name"] == "a1"

    def test_save_check_result(self, checker):
        r = HealthCheckResult(check_id="c1", checked_agents=1, healthy_count=1,
                               stale_count=0, failed_count=0, reassigned_count=0)
        checker._save_check_result(r)
        f = checker.state_dir / "check_c1.json"
        assert f.exists()

    def test_save_status(self, checker):
        checker._save_status()
        f = checker.state_dir / "status.json"
        assert f.exists()
        data = json.loads(f.read_text())
        assert "total_registered" in data


class TestNotify:
    def test_notify_with_callback(self, checker):
        calls = []
        checker.on_notification = lambda t, b: calls.append((t, b))
        checker._notify("title", "body")
        assert len(calls) == 1

    def test_notify_without_callback(self, checker):
        checker._notify("title", "body")  # no error

    def test_notify_callback_exception_suppressed(self, checker):
        checker.on_notification = MagicMock(side_effect=RuntimeError("boom"))
        checker._notify("title", "body")  # suppressed

    def test_notify_writes_log(self, checker):
        checker._notify("title", "body")
        log_file = checker.state_dir / "notifications.jsonl"
        assert log_file.exists()


class TestRegisterTask:
    def test_register_task(self, checker):
        task = MagicMock(spec=asyncio.Task)
        checker.register_task("a1", task)
        assert checker._active_tasks["a1"] is task


# ── format_health_display ────────────────────────────────────────

class TestFormatHealthDisplay:
    def test_empty(self):
        assert format_health_display({}) == "  (no agents registered)"

    def test_healthy_agent(self):
        result = format_health_display({
            "a1": {"status": "healthy", "retry_count": 0,
                    "last_heartbeat": "2026-01-01T00:00:00", "workflow_id": "w1"}
        })
        assert "✅ a1" in result

    def test_stale_agent(self):
        result = format_health_display({
            "a1": {"status": "stale", "retry_count": 1, "workflow_id": None,
                    "last_heartbeat": "", "last_error": "timeout"}
        })
        assert "⚠️ a1" in result
        assert "timeout" in result

    def test_failed_agent(self):
        result = format_health_display({
            "a1": {"status": "failed", "retry_count": 3, "workflow_id": None,
                    "last_heartbeat": "", "last_error": ""}
        })
        assert "❌ a1" in result

    def test_reassigned_agent(self):
        result = format_health_display({
            "a1": {"status": "reassigned", "retry_count": 0, "workflow_id": None,
                    "last_heartbeat": ""}
        })
        assert "🔄 a1" in result

    def test_no_workflow_shows_dash(self):
        result = format_health_display({
            "a1": {"status": "healthy", "retry_count": 0,
                    "last_heartbeat": "", "workflow_id": None}
        })
        assert "—" in result
