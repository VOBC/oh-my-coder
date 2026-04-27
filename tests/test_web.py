"""
Web 界面测试

测试 FastAPI 界面和 SSE 端点
"""

import asyncio
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.orchestrator import Orchestrator
from src.web.app import app


class TestWebAPI:
    """Web API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_dashboard_stats_endpoint(self, client):
        """测试仪表板统计数据端点"""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_tasks" in data
        assert "completed_tasks" in data
        assert "success_rate" in data

    def test_dashboard_activity_endpoint(self, client):
        """测试活动数据端点"""
        response = client.get("/api/dashboard/activity")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "day" in data[0]
            assert "tasks" in data[0]
            assert "tokens" in data[0]

    def test_dashboard_agents_endpoint(self, client):
        """测试 Agent 状态端点"""
        response = client.get("/api/dashboard/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "name" in data[0]
            assert "status" in data[0]
            assert "total_executions" in data[0]

    def test_dashboard_recent_tasks_endpoint(self, client):
        """测试最近任务端点"""
        response = client.get("/api/dashboard/recent-tasks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "task_id" in data[0]
            assert "task" in data[0]
            assert "workflow" in data[0]
            assert "status" in data[0]

    def test_dashboard_overview_endpoint(self, client):
        """测试仪表板概览端点"""
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "activity" in data
        assert "agents" in data
        assert "recent_tasks" in data
        assert "updated_at" in data

    def test_sse_execute_endpoint_task_not_found(self, client):
        """测试 SSE 端点任务不存在的情况"""
        response = client.get("/sse/execute/nonexistent")
        assert response.status_code == 404

    def test_tasks_list_endpoint(self, client):
        """测试任务列表端点"""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert isinstance(data["tasks"], list)

    def test_task_get_endpoint_not_found(self, client):
        """测试获取不存在的任务"""
        response = client.get("/api/tasks/nonexistent")
        assert response.status_code == 404

    def test_execute_task_missing_payload(self, client):
        """测试执行任务缺少 payload"""
        response = client.post("/api/execute")
        assert response.status_code == 400

    def test_execute_task_missing_task_field(self, client):
        """测试执行任务缺少 task 字段"""
        response = client.post("/api/execute", json={"project_path": "."})
        assert response.status_code == 400

    def test_config_endpoint(self, client):
        """测试配置端点"""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "workflows" in data
        assert "agents" in data
        assert isinstance(data["models"], list)
        assert isinstance(data["workflows"], list)
        assert isinstance(data["agents"], list)

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data

    def test_main_pages(self, client):
        """测试主要页面"""
        for path in ["/", "/history", "/agents", "/dashboard"]:
            response = client.get(path)
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]


class TestAgentLiveStream:
    """Agent 实时流测试"""

    @pytest.fixture
    def mock_orchestrator(self):
        """创建模拟的 orchestrator"""
        mock_orch = MagicMock(spec=Orchestrator)
        mock_orch.get_current_state.return_value = {
            "active_agents": [
                {
                    "name": "test-agent",
                    "status": "working",
                    "task": "测试任务",
                    "started_at": "2026-04-12T08:00:00Z",
                }
            ],
            "completed_agents": [],
            "pending_agents": ["other-agent"],
            "total_progress": "1/2",
            "workflow": "test",
            "timestamp": "2026-04-12T08:00:00Z",
        }
        return mock_orch

    @pytest.mark.asyncio
    async def test_agent_live_stream_returns_streaming_response(self):
        """测试 agent_live_stream 端点返回 StreamingResponse"""
        from fastapi.responses import StreamingResponse

        from src.web.app import agent_live_stream

        response = await agent_live_stream()
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"
        assert response.headers.get("Cache-Control") == "no-cache"

    @pytest.mark.asyncio
    async def test_agent_live_stream_with_data(self):
        """测试 Agent 实时流数据结构"""
        from src.web.app import json_dumps

        mock_orch = MagicMock()
        test_data = {
            "active_agents": [
                {
                    "name": "code-reviewer",
                    "status": "working",
                    "task": "reviewing",
                    "started_at": "2026-04-12T07:50:00Z",
                }
            ],
            "completed_agents": [
                {"name": "planner", "status": "done", "task": "plan", "duration": "12s"}
            ],
            "pending_agents": ["test-engineer", "security-reviewer"],
            "total_progress": "2/6",
            "workflow": "review",
            "timestamp": "2026-04-12T08:00:00Z",
        }
        mock_orch.get_current_state.return_value = test_data

        async def patched_event_generator():
            while True:
                state = mock_orch.get_current_state()
                yield "data: " + json_dumps(state) + "\n\n"
                await asyncio.sleep(2)

        gen = patched_event_generator()
        first_chunk = await gen.__anext__()
        assert "data:" in first_chunk
        json_str = first_chunk.split("data: ", 1)[1].rstrip("\n\n")
        data = json.loads(json_str)
        assert data["active_agents"][0]["name"] == "code-reviewer"
        assert data["completed_agents"][0]["name"] == "planner"
        assert data["total_progress"] == "2/6"
        assert data["workflow"] == "review"

    @pytest.mark.asyncio
    async def test_agent_live_stream_error_handling(self):
        """测试 Agent 实时流错误处理"""
        from src.web.app import json_dumps

        mock_orch = MagicMock()
        mock_orch.get_current_state.side_effect = ValueError("测试错误")

        async def patched_event_generator():
            while True:
                try:
                    state = mock_orch.get_current_state()
                    yield "data: " + json_dumps(state) + "\n\n"
                    await asyncio.sleep(2)
                except ValueError:
                    error_state = {
                        "error": "ValueError",
                        "timestamp": "2026-04-12T08:00:00Z",
                    }
                    yield "data: " + json_dumps(error_state) + "\n\n"

        gen = patched_event_generator()
        first_chunk = await gen.__anext__()
        assert "data:" in first_chunk
        json_str = first_chunk.split("data: ", 1)[1].rstrip("\n\n")
        error_data = json.loads(json_str)
        assert "error" in error_data
        assert error_data["error"] == "ValueError"

    @pytest.mark.asyncio
    async def test_orchestrator_get_current_state(self, mock_orchestrator):
        """测试 orchestrator.get_current_state 方法"""
        orch = mock_orchestrator
        state = orch.get_current_state()
        assert "active_agents" in state
        assert "completed_agents" in state
        assert "pending_agents" in state
        assert "total_progress" in state
        assert "workflow" in state
        assert "timestamp" in state
        assert isinstance(state["active_agents"], list)
        assert isinstance(state["completed_agents"], list)
        assert isinstance(state["pending_agents"], list)
        assert isinstance(state["total_progress"], str)
        assert isinstance(state["workflow"], str)
        assert isinstance(state["timestamp"], str)

    @pytest.mark.asyncio
    async def test_orchestrator_state_with_active_workflow(self):
        """测试有活跃工作流时的状态"""
        orch = MagicMock(spec=Orchestrator)
        orch.get_current_state.return_value = {
            "active_agents": [
                {
                    "name": "code-reviewer",
                    "status": "running",
                    "task": "code review",
                    "started_at": "2026-04-12T08:00:00Z",
                },
                {
                    "name": "planner",
                    "status": "running",
                    "task": "plan tasks",
                    "started_at": "2026-04-12T08:00:00Z",
                },
            ],
            "completed_agents": [],
            "pending_agents": [],
            "total_progress": "2/4",
            "workflow": "test-workflow",
            "timestamp": "2026-04-12T08:00:00Z",
        }
        state = orch.get_current_state()
        assert len(state["active_agents"]) > 0
        assert any(a["name"] == "code-reviewer" for a in state["active_agents"])
        assert any(a["name"] == "planner" for a in state["active_agents"])

    @pytest.mark.asyncio
    async def test_orchestrator_state_with_completed_workflow(self):
        """测试有已完成工作流时的状态"""
        orch = MagicMock(spec=Orchestrator)
        orch.get_current_state.return_value = {
            "active_agents": [],
            "completed_agents": [
                {
                    "name": "planner",
                    "status": "done",
                    "task": "分解任务",
                    "duration": "12s",
                },
                {
                    "name": "architect",
                    "status": "done",
                    "task": "架构设计",
                    "duration": "8s",
                },
            ],
            "pending_agents": [],
            "total_progress": "2/2",
            "workflow": "completed-workflow",
            "timestamp": "2026-04-12T08:00:00Z",
        }
        state = orch.get_current_state()
        assert len(state["completed_agents"]) > 0
        assert any(a["name"] == "planner" for a in state["completed_agents"])
        assert any(a["name"] == "architect" for a in state["completed_agents"])
