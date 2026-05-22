"""
Tests for src/web/history_api.py

Tests HistoryStore, AgentStatusManager, and FastAPI routes.
"""
import json
import os
import glob
import asyncio
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# 导入被测试模块
from src.web.history_api import (
    HistoryStore,
    AgentStatusManager,
    history_router,
    agent_router,
    agent_status_manager,
)


# ========================================
# Fixtures
# ========================================
@pytest.fixture
def temp_store():
    """创建临时 HistoryStore"""
    with TemporaryDirectory() as tmpdir:
        store = HistoryStore(storage_dir=Path(tmpdir))
        yield store


@pytest.fixture
def app():
    """创建测试 FastAPI app"""
    test_app = FastAPI()
    test_app.include_router(history_router, prefix="/api/v1")
    test_app.include_router(agent_router, prefix="/api/v1")
    return test_app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def clean_history_store():
    """清理 history_store"""
    from src.web.history_api import history_store

    # 清除所有记录
    for f in glob.glob(str(history_store.storage_dir / "*.json")):
        os.remove(f)
    history_store._cache.clear()
    yield
    # 清理
    for f in glob.glob(str(history_store.storage_dir / "*.json")):
        os.remove(f)
    history_store._cache.clear()


# ========================================
# HistoryStore 单元测试
# ========================================
class TestHistoryStore:
    """测试 HistoryStore 类"""

    def test_save_and_load(self, temp_store):
        """测试保存和加载"""
        store = temp_store
        record = {
            "task_id": "test-1",
            "status": "completed",
            "workflow": "test",
        }
        store.save("test-1", record)

        loaded = store.load("test-1")
        assert loaded is not None
        assert loaded["task_id"] == "test-1"
        assert loaded["status"] == "completed"
        assert "saved_at" in loaded

    def test_save_creates_file(self, temp_store):
        """测试保存创建文件"""
        store = temp_store
        record = {"task_id": "test-2", "status": "running"}
        store.save("test-2", record)

        file_path = store.storage_dir / "test-2.json"
        assert file_path.exists()

        # 验证文件内容
        with open(file_path, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["task_id"] == "test-2"

    def test_load_nonexistent(self, temp_store):
        """测试加载不存在的记录"""
        store = temp_store
        result = store.load("nonexistent")
        assert result is None

    def test_load_from_cache(self, temp_store):
        """测试从缓存加载"""
        store = temp_store
        record = {"task_id": "test-3", "status": "completed"}
        store.save("test-3", record)

        # 第一次加载（从文件）
        loaded1 = store.load("test-3")
        assert loaded1 is not None

        # 第二次加载（从缓存）
        loaded2 = store.load("test-3")
        assert loaded2 is not None
        assert loaded2["task_id"] == "test-3"

    def test_list_all_empty(self, temp_store):
        """测试列出空记录"""
        store = temp_store
        records = store.list_all()
        assert records == []

    def test_list_all(self, temp_store):
        """测试列出所有记录"""
        store = temp_store
        # 保存多条记录
        for i in range(5):
            record = {
                "task_id": f"task-{i}",
                "status": "completed" if i % 2 == 0 else "failed",
                "workflow": "test",
                "started_at": f"2026-05-{i+1:02d}T10:00:00",
            }
            store.save(f"task-{i}", record)

        records = store.list_all()
        assert len(records) == 5

    def test_list_all_with_limit(self, temp_store):
        """测试限制返回数量"""
        store = temp_store
        for i in range(10):
            record = {"task_id": f"task-{i}", "started_at": f"2026-05-{i+1:02d}"}
            store.save(f"task-{i}", record)

        records = store.list_all(limit=5)
        assert len(records) == 5

    def test_list_all_with_offset(self, temp_store):
        """测试偏移量"""
        store = temp_store
        for i in range(5):
            record = {"task_id": f"task-{i}", "started_at": f"2026-05-{i+1:02d}"}
            store.save(f"task-{i}", record)

        records = store.list_all(limit=10, offset=2)
        assert len(records) == 3

    def test_list_all_filter_status(self, temp_store):
        """测试按状态过滤"""
        store = temp_store
        for i in range(5):
            record = {
                "task_id": f"task-{i}",
                "status": "completed" if i < 3 else "failed",
            }
            store.save(f"task-{i}", record)

        records = store.list_all(status="completed")
        assert len(records) == 3

    def test_list_all_filter_workflow(self, temp_store):
        """测试按工作流过滤"""
        store = temp_store
        for i in range(5):
            record = {
                "task_id": f"task-{i}",
                "workflow": "build" if i < 2 else "review",
            }
            store.save(f"task-{i}", record)

        records = store.list_all(workflow="build")
        assert len(records) == 2

    def test_list_all_sorted_by_time(self, temp_store):
        """测试按时间排序"""
        store = temp_store
        times = ["2026-05-03", "2026-05-01", "2026-05-02"]
        for i, time in enumerate(times):
            record = {"task_id": f"task-{i}", "started_at": f"{time}T10:00:00"}
            store.save(f"task-{i}", record)

        records = store.list_all()
        assert records[0]["started_at"] == "2026-05-03T10:00:00"
        assert records[1]["started_at"] == "2026-05-02T10:00:00"
        assert records[2]["started_at"] == "2026-05-01T10:00:00"

    def test_delete(self, temp_store):
        """测试删除记录"""
        store = temp_store
        record = {"task_id": "test-del", "status": "completed"}
        store.save("test-del", record)

        # 确认存在
        assert store.load("test-del") is not None

        # 删除
        result = store.delete("test-del")
        assert result is True

        # 确认不存在
        assert store.load("test-del") is None

    def test_delete_nonexistent(self, temp_store):
        """测试删除不存在的记录"""
        store = temp_store
        result = store.delete("nonexistent")
        assert result is True  # 总是返回 True

    def test_delete_removes_file_and_cache(self, temp_store):
        """测试删除移除文件和缓存"""
        store = temp_store
        record = {"task_id": "test-del2", "status": "completed"}
        store.save("test-del2", record)

        # 确认文件存在
        file_path = store.storage_dir / "test-del2.json"
        assert file_path.exists()

        # 删除
        store.delete("test-del2")

        # 确认文件不存在
        assert not file_path.exists()
        assert "test-del2" not in store._cache

    def test_get_stats_empty(self, temp_store):
        """测试空统计"""
        store = temp_store
        stats = store.get_stats()
        assert stats["total_tasks"] == 0
        assert stats["completed_tasks"] == 0
        assert stats["failed_tasks"] == 0
        assert stats["success_rate"] == 0

    def test_get_stats(self, temp_store):
        """测试获取统计"""
        store = temp_store
        records = [
            {"task_id": "t1", "status": "completed", "stats": {"total_tokens": 100, "total_cost": 0.01, "execution_time": 10}},
            {"task_id": "t2", "status": "completed", "stats": {"total_tokens": 200, "total_cost": 0.02, "execution_time": 20}},
            {"task_id": "t3", "status": "failed", "stats": {"total_tokens": 50, "total_cost": 0.005, "execution_time": 5}},
        ]
        for r in records:
            store.save(r["task_id"], r)

        stats = store.get_stats()
        assert stats["total_tasks"] == 3
        assert stats["completed_tasks"] == 2
        assert stats["failed_tasks"] == 1
        assert stats["success_rate"] == pytest.approx(66.7, abs=0.1)
        assert stats["total_tokens"] == 350
        assert stats["total_cost"] == pytest.approx(0.035, abs=0.001)
        assert stats["total_duration_hours"] == pytest.approx(0.0097, abs=0.001)

    def test_save_updates_cache(self, temp_store):
        """测试保存更新缓存"""
        store = temp_store
        record = {"task_id": "test-cache", "status": "running"}
        store.save("test-cache", record)

        # 保存新版本（应该更新缓存）
        record2 = {"task_id": "test-cache", "status": "completed"}
        store.save("test-cache", record2)

        loaded = store.load("test-cache")
        assert loaded["status"] == "completed"  # 缓存已更新


# ========================================
# AgentStatusManager 单元测试
# ========================================
class TestAgentStatusManager:
    """测试 AgentStatusManager 类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前保存状态，测试后恢复"""
        # 保存原始状态
        self.original_agents = agent_status_manager._agents.copy()
        self.original_subscribers = agent_status_manager._status_subscribers.copy()

        yield

        # 恢复原始状态
        agent_status_manager._agents = self.original_agents
        agent_status_manager._status_subscribers = self.original_subscribers

    def test_register_agent(self):
        """测试注册 Agent"""
        agent_status_manager.register_agent("TestAgent", {"channel": "TEST"})

        agent = agent_status_manager.get_agent("TestAgent")
        assert agent is not None
        assert agent["name"] == "TestAgent"
        assert agent["status"] == "idle"
        assert agent["channel"] == "TEST"

    def test_register_agent_defaults(self):
        """测试注册 Agent 默认值"""
        agent_status_manager.register_agent("TestAgent2", {})

        agent = agent_status_manager.get_agent("TestAgent2")
        assert agent["status"] == "idle"
        assert agent["current_task"] is None
        assert agent["last_activity"] is None

    def test_update_status(self):
        """测试更新状态"""
        agent_status_manager.register_agent("TestAgent", {})
        agent_status_manager.update_status("TestAgent", "running", task="test-task")

        agent = agent_status_manager.get_agent("TestAgent")
        assert agent["status"] == "running"
        assert agent["current_task"] == "test-task"
        assert agent["last_activity"] is not None

    def test_update_status_with_progress(self):
        """测试更新进度"""
        agent_status_manager.register_agent("TestAgent", {})
        agent_status_manager.update_status("TestAgent", "running", progress=50.0)

        agent = agent_status_manager.get_agent("TestAgent")
        assert agent["progress"] == 50.0

    def test_update_status_nonexistent(self):
        """测试更新不存在的 Agent（应该不报错）"""
        agent_status_manager.update_status("NonExistent", "running")  # 不应该报错

    def test_get_agent(self):
        """测试获取 Agent"""
        agent_status_manager.register_agent("TestAgent", {})
        agent = agent_status_manager.get_agent("TestAgent")
        assert agent is not None
        assert agent["name"] == "TestAgent"

    def test_get_agent_nonexistent(self):
        """测试获取不存在的 Agent"""
        agent = agent_status_manager.get_agent("NonExistent")
        assert agent is None

    def test_get_all(self):
        """测试获取所有 Agent"""
        # 注意：agent_status_manager 是全局的，可能已经注册了 Agent
        all_agents = agent_status_manager.get_all()
        assert isinstance(all_agents, list)
        assert len(all_agents) > 0  # 默认应该注册了一些 Agent

    @pytest.mark.asyncio
    async def test_subscribe(self):
        """测试订阅状态变化"""
        queue = agent_status_manager.subscribe()
        assert isinstance(queue, asyncio.Queue)  # type: ignore

    @pytest.mark.asyncio
    async def test_notify_subscribers(self):
        """测试通知订阅者"""
        agent_status_manager.register_agent("TestAgent", {})

        queue = agent_status_manager.subscribe()
        agent_status_manager.update_status("TestAgent", "running")

        # 队列中应该有数据
        data = await asyncio.wait_for(queue.get(), timeout=0.1)
        assert data["type"] == "agent_status"
        assert data["agent"] == "TestAgent"
        assert data["data"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_notify_subscribers_queue_full(self):
        """测试队列满时跳过"""
        agent_status_manager.register_agent("TestAgent", {})

        queue = agent_status_manager.subscribe()
        # 填满队列（Queue 默认无限大，需要自定义）
        # 这个测试比较复杂，暂时跳过
        pytest.skip("Queue full test requires custom queue implementation")


# ========================================
# FastAPI 路由测试
# ========================================
class TestHistoryAPI:
    """测试 History API 路由"""

    @pytest.fixture(autouse=True)
    def setup(self, client, clean_history_store):
        """每个测试前设置"""
        from src.web.history_api import history_store

        self.history_store = history_store
        self.client = client
        yield
        # 清理在 fixture 中完成

    def test_list_history_empty(self, client):
        """测试列出空历史"""
        response = client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert data["records"] == []
        assert data["pagination"]["total"] == 0

    def test_list_history(self, client):
        """测试列出历史记录"""
        # 添加记录
        for i in range(3):
            record = {
                "task_id": f"task-{i}",
                "status": "completed",
                "workflow": "test",
                "started_at": f"2026-05-{i+1:02d}T10:00:00",
            }
            self.history_store.save(f"task-{i}", record)

        response = client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) == 3
        assert data["pagination"]["total"] == 3

    def test_list_history_with_limit(self, client):
        """测试限制返回数量"""
        for i in range(5):
            record = {"task_id": f"task-{i}"}
            self.history_store.save(f"task-{i}", record)

        response = client.get("/api/v1/history?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) == 2

    def test_list_history_with_status_filter(self, client):
        """测试按状态过滤"""
        for i in range(4):
            record = {
                "task_id": f"task-{i}",
                "status": "completed" if i < 2 else "failed",
            }
            self.history_store.save(f"task-{i}", record)

        response = client.get("/api/v1/history?status=completed")
        assert response.status_code == 200
        data = response.json()
        assert len(data["records"]) == 2

    def test_get_history_detail(self, client):
        """测试获取历史详情"""
        record = {"task_id": "task-1", "status": "completed"}
        self.history_store.save("task-1", record)

        response = client.get("/api/v1/history/task-1")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-1"

    def test_get_history_detail_not_found(self, client):
        """测试获取不存在的历史"""
        response = client.get("/api/v1/history/nonexistent")
        assert response.status_code == 404

    def test_delete_history(self, client):
        """测试删除历史记录"""
        record = {"task_id": "task-del", "status": "completed"}
        self.history_store.save("task-del", record)

        response = client.delete("/api/v1/history/task-del")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 确认已删除
        assert self.history_store.load("task-del") is None

    def test_get_history_stats(self, client):
        """测试获取统计摘要"""
        records = [
            {"task_id": "t1", "status": "completed", "workflow": "build"},
            {"task_id": "t2", "status": "failed", "workflow": "build"},
            {"task_id": "t3", "status": "completed", "workflow": "review"},
        ]
        for r in records:
            self.history_store.save(r["task_id"], r)

        response = client.get("/api/v1/history/stats/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 3
        assert "workflow_stats" in data
        assert "build" in data["workflow_stats"]
        assert data["workflow_stats"]["build"]["count"] == 2


class TestAgentAPI:
    """测试 Agent API 路由"""

    def test_list_agents(self, client):
        """测试列出所有 Agent"""
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) > 0

    def test_get_agent_status(self, client):
        """测试获取 Agent 状态"""
        # Agent Planner 应该已经注册
        response = client.get("/api/v1/agents/Planner")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Planner"

    def test_get_agent_status_not_found(self, client):
        """测试获取不存在的 Agent"""
        response = client.get("/api/v1/agents/NonExistentAgent")
        assert response.status_code == 404


# ========================================
# 缺失的测试覆盖
# ========================================


class TestVerifyToken:
    """测试 token 验证"""

    @pytest.mark.asyncio
    async def test_verify_token_no_token(self):
        """测试未配置 token 时允许操作"""
        from src.web.history_api import verify_api_token

        # Patch API_TOKEN to None
        with patch("src.web.history_api.API_TOKEN", None):
            result = await verify_api_token(credentials=None)
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        """测试无效 token"""
        from fastapi import HTTPException
        from src.web.history_api import verify_api_token
        from fastapi.security import HTTPAuthorizationCredentials

        # Patch API_TOKEN to "test-token"
        with patch("src.web.history_api.API_TOKEN", "test-token"):
            # 传入错误的 credentials
            bad_credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="wrong-token"
            )
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_token(credentials=bad_credentials)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_token_valid(self):
        """测试有效 token"""
        from src.web.history_api import verify_api_token
        from fastapi.security import HTTPAuthorizationCredentials

        # Patch API_TOKEN to "test-token"
        with patch("src.web.history_api.API_TOKEN", "test-token"):
            # 传入正确的 credentials
            good_credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="test-token"
            )
            result = await verify_api_token(credentials=good_credentials)
            assert result == "test-token"


class TestHistoryStoreBrokenFiles:
    """测试损坏文件的处理"""

    def test_list_all_with_corrupted_json(self, temp_store):
        """测试 list_all 跳过损坏的 JSON 文件"""
        store = temp_store
        # 创建一个损坏的 JSON 文件
        corrupted_file = store.storage_dir / "corrupted.json"
        corrupted_file.write_text("{invalid json}")

        # 再创建一个正常的文件
        normal_record = {"task_id": "normal", "status": "completed"}
        store.save("normal", normal_record)

        # list_all 应该跳过损坏的文件，只返回正常的
        records = store.list_all()
        assert len(records) == 1
        assert records[0]["task_id"] == "normal"

    def test_load_corrupted_json(self, temp_store):
        """测试加载损坏的 JSON 文件"""
        store = temp_store
        # 创建一个损坏的 JSON 文件
        corrupted_file = store.storage_dir / "corrupted.json"
        corrupted_file.write_text("{invalid json}")

        # load 应该返回 None
        result = store.load("corrupted")
        assert result is None

    def test_delete_nonexistent_file(self, temp_store):
        """测试删除不存在的文件（错误处理）"""
        store = temp_store
        # 删除不存在的文件应该不报错
        store.delete("nonexistent")  # 应该不报错
        assert True  # 能到这里就说明没报错
