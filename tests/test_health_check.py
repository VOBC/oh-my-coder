"""
测试 Agent 健康检查与故障自动重分配

运行: pytest tests/test_health_check.py -v
"""

import json
import sys
import time
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, "/Users/vobc/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder")

from src.agents.health_check import (
    AgentHealth,
    AgentStatus,
    HealthChecker,
    format_health_display,
)

# ------------------------------------------------------------------
# AgentHealth 测试
# ------------------------------------------------------------------


class TestAgentHealth:
    """AgentHealth 数据结构测试"""

    def test_default_healthy(self):
        h = AgentHealth(agent_name="executor")
        assert h.status == AgentStatus.HEALTHY
        assert h.retry_count == 0
        assert h.last_error is None
        assert h.can_retry()

    def test_touch_updates_heartbeat(self):
        h = AgentHealth(agent_name="executor")
        before = h.last_heartbeat
        time.sleep(0.01)
        h.touch()
        assert h.last_heartbeat > before
        assert h.status == AgentStatus.HEALTHY

    def test_is_stale_false_when_fresh(self):
        h = AgentHealth(agent_name="executor")
        assert h.is_stale(threshold=300.0) is False

    def test_is_stale_true_after_threshold(self):
        h = AgentHealth(agent_name="executor")
        h.last_heartbeat = time.time() - 400  # 400秒前
        assert h.is_stale(threshold=300.0) is True

    def test_record_failure_increments_retry(self):
        h = AgentHealth(agent_name="executor")
        exceeded = h.record_failure("timeout")
        assert not exceeded
        assert h.retry_count == 1
        assert h.status == AgentStatus.STALE
        assert h.last_error == "timeout"

    def test_record_failure_max_retries(self):
        h = AgentHealth(agent_name="executor", retry_count=2)
        h.MAX_RETRIES = 3
        # 第3次失败
        exceeded = h.record_failure("timeout")
        assert exceeded  # 达到上限
        assert h.status == AgentStatus.FAILED
        assert h.retry_count == 3

    def test_can_retry_false_at_limit(self):
        h = AgentHealth(agent_name="executor", retry_count=3)
        h.MAX_RETRIES = 3
        assert h.can_retry() is False

    def test_can_retry_true_below_limit(self):
        h = AgentHealth(agent_name="executor", retry_count=2)
        h.MAX_RETRIES = 3
        assert h.can_retry() is True

    def test_to_dict_serialization(self):
        h = AgentHealth(agent_name="analyst", task_id="task-1", retry_count=1)
        d = h.to_dict()
        assert d["agent_name"] == "analyst"
        assert d["status"] == "healthy"
        assert d["retry_count"] == 1
        assert "last_heartbeat" in d
        assert "MAX_RETRIES" not in d  # 常量不应序列化


class TestAgentStatus:
    """AgentStatus 枚举测试"""

    def test_all_statuses_exist(self):
        assert AgentStatus.HEALTHY.value == "healthy"
        assert AgentStatus.STALE.value == "stale"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.REASSIGNED.value == "reassigned"


# ------------------------------------------------------------------
# HealthChecker 测试
# ------------------------------------------------------------------


class TestHealthCheckerInit:
    """HealthChecker 初始化测试"""

    def test_default_values(self):
        hc = HealthChecker()
        assert hc.check_interval == 60.0
        assert hc.stale_threshold == 300.0
        assert hc.max_retries == 3
        assert hc._agent_health == {}
        assert hc._active_tasks == {}

    def test_custom_values(self):
        hc = HealthChecker(check_interval=30.0, stale_threshold=120.0, max_retries=5)
        assert hc.check_interval == 30.0
        assert hc.stale_threshold == 120.0
        assert hc.max_retries == 5


class TestAgentRegistration:
    """Agent 注册与心跳测试"""

    def setup_method(self):
        self.hc = HealthChecker()

    def test_register_agent(self):
        h = self.hc.register_agent("executor", task_id="task-1")
        assert h.agent_name == "executor"
        assert h.task_id == "task-1"
        assert h.status == AgentStatus.HEALTHY
        assert "executor" in self.hc._agent_health

    def test_register_multiple_agents(self):
        self.hc.register_agent("analyst")
        self.hc.register_agent("executor")
        assert len(self.hc._agent_health) == 2

    def test_heartbeat_updates_existing(self):
        self.hc.register_agent("executor")
        before = self.hc._agent_health["executor"].last_heartbeat
        time.sleep(0.01)
        self.hc.heartbeat("executor")
        assert self.hc._agent_health["executor"].last_heartbeat > before

    def test_heartbeat_unknown_agent_returns_false(self):
        result = self.hc.heartbeat("unknown")
        assert result is False

    def test_unregister_agent(self):
        self.hc.register_agent("executor")
        self.hc.unregister_agent("executor")
        assert "executor" not in self.hc._agent_health


class TestRecordFailure:
    """故障记录与重试测试"""

    def setup_method(self):
        self.hc = HealthChecker(max_retries=3)

    def test_record_failure_not_exceeded(self):
        self.hc.register_agent("executor")
        exceeded = self.hc.record_failure("executor", "timeout error")
        assert not exceeded
        assert self.hc._agent_health["executor"].retry_count == 1
        assert self.hc._agent_health["executor"].status == AgentStatus.STALE

    def test_record_failure_unregistered_agent(self):
        # 自动注册未注册的 agent
        exceeded = self.hc.record_failure("unknown", "error")
        assert not exceeded
        assert "unknown" in self.hc._agent_health
        assert self.hc._agent_health["unknown"].retry_count == 1

    def test_record_failure_max_exceeded(self):
        self.hc.register_agent("executor")
        # 连续失败3次
        for _ in range(3):
            self.hc.record_failure("executor", "timeout")
        # 第3次返回 True（已达上限）
        exceeded = self.hc.record_failure("executor", "timeout")
        assert exceeded
        assert self.hc._agent_health["executor"].status == AgentStatus.FAILED


class TestReassignment:
    """任务重分配测试"""

    def setup_method(self):
        self.hc = HealthChecker()

    def test_reassign_to_idle_agent(self):
        """有空闲健康 Agent 时，任务重分配到该 Agent"""
        self.hc.register_agent("executor-1", workflow_id="wf-1")
        self.hc.register_agent("analyst", workflow_id="wf-1")
        # analyst 空闲（无 active task）

        mock_step = MagicMock()
        mock_step.agent_name = "executor-1"

        new_agent = self.hc.reassign_task(
            agent_name="executor-1",
            workflow_id="wf-1",
            step=mock_step,
        )
        # 应该分配给 analyst（唯一的空闲健康 Agent）
        assert new_agent == "analyst"

    def test_reassign_no_idle_agent(self):
        """没有空闲 Agent 时返回 None"""
        self.hc.register_agent("executor-1", workflow_id="wf-1")
        # executor-1 是唯一的 Agent，无法重分配给自己
        mock_step = MagicMock()
        mock_step.agent_name = "executor-1"

        new_agent = self.hc.reassign_task(
            agent_name="executor-1",
            workflow_id="wf-1",
            step=mock_step,
        )
        assert new_agent is None

    def test_reassign_skips_failed_agent(self):
        """跳过已标记为 FAILED 的 Agent"""
        self.hc.register_agent("executor-1")
        self.hc.register_agent("analyst")
        self.hc._agent_health["analyst"].status = AgentStatus.FAILED

        mock_step = MagicMock()
        mock_step.agent_name = "executor-1"

        new_agent = self.hc.reassign_task(
            agent_name="executor-1",
            workflow_id="wf-1",
            step=mock_step,
        )
        # analyst 是 FAILED，无法分配
        assert new_agent is None


class TestPeriodicCheck:
    """定期检查测试"""

    def setup_method(self):
        self.hc = HealthChecker(stale_threshold=1.0, max_retries=3)  # 1秒超时

    @pytest.mark.asyncio
    async def test_check_detects_stale_agent(self):
        """检测到超时的 Agent 并标记为 STALE"""
        h = self.hc.register_agent("executor", workflow_id="wf-1")
        h.last_heartbeat = time.time() - 10  # 10秒前（> 1秒阈值）

        result = await self.hc._check_all()

        assert result is not None
        assert result.stale_count >= 1
        assert result.checked_agents >= 1
        assert self.hc._agent_health["executor"].status == AgentStatus.STALE

    @pytest.mark.asyncio
    async def test_check_empty_returns_none(self):
        """无 Agent 时检查返回 None"""
        result = await self.hc._check_all()
        assert result is None

    @pytest.mark.asyncio
    async def test_check_auto_retry_on_stale(self):
        """STALE Agent 自动重试并触发重分配"""
        h = self.hc.register_agent("executor", workflow_id="wf-1")
        h.last_heartbeat = time.time() - 10

        # 同时注册一个空闲的备份 Agent
        self.hc.register_agent("executor-backup", workflow_id="wf-1")

        result = await self.hc._check_all()

        assert result is not None
        assert result.stale_count >= 1
        assert result.reassigned_count >= 1

    @pytest.mark.asyncio
    async def test_check_healthy_agent_untouched(self):
        """健康 Agent 不受影响"""
        self.hc.register_agent("executor")
        result = await self.hc._check_all()
        assert result.healthy_count >= 1
        assert self.hc._agent_health["executor"].status == AgentStatus.HEALTHY


class TestHealthCheckerSummary:
    """状态摘要测试"""

    def test_get_summary_empty(self):
        hc = HealthChecker()
        summary = hc.get_summary()
        assert summary["total_registered"] == 0
        assert summary["healthy"] == 0
        assert summary["is_running"] is False

    def test_get_summary_mixed_status(self):
        hc = HealthChecker()
        hc.register_agent("executor-1")
        h2 = hc.register_agent("executor-2")
        h2.status = AgentStatus.FAILED
        h3 = hc.register_agent("analyst")
        h3.status = AgentStatus.STALE

        summary = hc.get_summary()
        assert summary["total_registered"] == 3
        assert summary["healthy"] == 1
        assert summary["failed"] == 1
        assert summary["stale"] == 1

    def test_get_all_health(self):
        hc = HealthChecker()
        hc.register_agent("executor", task_id="task-1")
        health_map = hc.get_all_health()
        assert "executor" in health_map
        assert health_map["executor"]["task_id"] == "task-1"


class TestFormatDisplay:
    """CLI 格式化输出测试"""

    def test_format_empty(self):
        display = format_health_display({})
        assert "no agents" in display

    def test_format_healthy(self):
        health_map = {
            "executor": {
                "status": "healthy",
                "retry_count": 0,
                "last_heartbeat": "2026-04-23T12:00:00",
                "workflow_id": "wf-abc",
                "last_error": "",
            }
        }
        display = format_health_display(health_map)
        assert "✅" in display
        assert "executor" in display
        assert "healthy" in display

    def test_format_failed(self):
        health_map = {
            "analyst": {
                "status": "failed",
                "retry_count": 3,
                "last_heartbeat": "2026-04-23T12:00:00",
                "workflow_id": "wf-xyz",
                "last_error": "connection timeout",
            }
        }
        display = format_health_display(health_map)
        assert "❌" in display
        assert "failed" in display
        assert "3" in display


class TestNotification:
    """通知测试"""

    def test_notify_callback(self):
        notifications = []

        def on_notify(title: str, body: str):
            notifications.append((title, body))

        hc = HealthChecker(on_notification=on_notify)
        hc._notify("test title", "test body")

        assert len(notifications) == 1
        assert notifications[0] == ("test title", "test body")

    def test_notify_without_callback(self):
        """无回调时不抛异常"""
        hc = HealthChecker(on_notification=None)
        hc._notify("test", "body")  # 不应抛异常


# ------------------------------------------------------------------
# 集成场景：模拟 Agent 超时，观察自动重分配
# ------------------------------------------------------------------


class TestIntegrationTimeoutReassignment:
    """验收测试：模拟 Agent 超时，观察任务是否自动重分配"""

    def setup_method(self):
        self.hc = HealthChecker(check_interval=60.0, stale_threshold=1.0, max_retries=3)

    @pytest.mark.asyncio
    async def test_timeout_triggers_reassignment(self):
        """
        场景：
        1. executor-1 注册并开始执行
        2. executor-1 心跳超时（>1s 无响应）
        3. 系统自动重分配给 executor-backup

        预期：executor-1 被标记为 STALE，重分配事件被记录
        """
        # Step 1: 注册两个 Agent
        h1 = self.hc.register_agent("executor-1", workflow_id="wf-1")
        self.hc.register_agent("executor-backup", workflow_id="wf-1")

        # Step 2: 模拟 executor-1 很久没有心跳
        h1.last_heartbeat = time.time() - 10

        # Step 3: 触发检查
        result = await self.hc._check_all()

        # 验证
        assert result is not None
        assert result.stale_count >= 1
        assert result.reassigned_count >= 1
        assert h1.status in (AgentStatus.STALE, AgentStatus.FAILED)
        assert h1.retry_count >= 1

    def test_max_retries_then_failed(self):
        """
        场景：连续 3 次失败后，Agent 被标记为 FAILED，通知用户
        """
        h = self.hc.register_agent("buggy-agent", workflow_id="wf-1")

        # 模拟3次失败
        for _ in range(3):
            exceeded = self.hc.record_failure("buggy-agent", "always fails")
            if exceeded:
                break

        assert h.status == AgentStatus.FAILED
        assert h.retry_count == 3
        assert h.can_retry() is False

    def test_reassignment_logs_to_file(self, tmp_path):
        """
        验收：重分配事件被记录到文件
        """
        hc = HealthChecker(
            state_dir=tmp_path,
            max_retries=3,
        )
        hc.register_agent("agent-1", workflow_id="wf-test")
        hc.register_agent("agent-2", workflow_id="wf-test")

        mock_step = MagicMock()
        mock_step.agent_name = "agent-1"

        hc.reassign_task("agent-1", "wf-test", mock_step)

        log_files = list(tmp_path.glob("reassignment_*.json"))
        assert len(log_files) >= 1
        content = json.loads(log_files[0].read_text(encoding="utf-8"))
        assert content["from_agent"] == "agent-1"
        assert content["workflow_id"] == "wf-test"
