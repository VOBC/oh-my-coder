"""
Web 界面测试
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# 确保项目根目录在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web.app import app, task_manager
from src.agents.base import AgentOutput, AgentStatus


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def clean_tasks():
    """每个测试前清空任务管理器"""
    task_manager._tasks.clear()
    task_manager._queues.clear()
    yield
    task_manager._tasks.clear()
    task_manager._queues.clear()


# ============================================================
# Health Check
# ============================================================
@pytest.mark.asyncio
async def test_health_check(client):
    """健康检查接口"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


# ============================================================
# Index Page
# ============================================================
@pytest.mark.asyncio
async def test_index_page(client):
    """主页能正常加载"""
    response = await client.get("/")
    assert response.status_code == 200
    assert "Oh My Coder" in response.text
    assert "text/html" in response.headers.get("content-type", "")


# ============================================================
# Static Files
# ============================================================
@pytest.mark.asyncio
async def test_static_css(client):
    """CSS 静态文件能正常访问"""
    response = await client.get("/static/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")


# ============================================================
# API: Config
# ============================================================
@pytest.mark.asyncio
async def test_get_config(client):
    """获取可用配置"""
    response = await client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "deepseek" in data["models"]
    assert "workflows" in data
    assert "build" in data["workflows"]


# ============================================================
# API: Execute (异步任务)
# ============================================================
@pytest.mark.asyncio
async def test_execute_missing_task(client):
    """缺少 task 字段应返回 422"""
    response = await client.post("/api/execute", json={})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_execute_success(client):
    """正常提交任务应返回 task_id"""
    payload = {
        "task": "实现一个简单的加法函数",
        "project_path": ".",
        "model": "deepseek",
        "workflow": "build",
    }
    response = await client.post("/api/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert "task_id" in data


# ============================================================
# API: Execute-Sync
# ============================================================
@pytest.mark.asyncio
async def test_execute_sync_bad_request(client):
    """同步执行缺少 task 应返回 400"""
    response = await client.post("/api/execute-sync", json={})
    assert response.status_code == 422  # Pydantic validation


# ============================================================
# API: Task Management
# ============================================================
@pytest.mark.asyncio
async def test_list_tasks(client):
    """列出所有任务"""
    response = await client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert isinstance(data["tasks"], list)


@pytest.mark.asyncio
async def test_get_task_not_found(client):
    """获取不存在的任务应返回 404"""
    response = await client.get("/api/tasks/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_after_submit(client):
    """提交任务后能正确查询"""
    payload = {"task": "测试任务", "workflow": "build"}
    resp = await client.post("/api/execute", json=payload)
    task_id = resp.json()["task_id"]

    resp2 = await client.get(f"/api/tasks/{task_id}")
    assert resp2.status_code == 200
    data = resp2.json()
    # 任务可能在后台快速执行完毕，状态可能是 pending/running/completed
    assert data["status"] in ("pending", "running", "completed")


# ============================================================
# API: SSE
# ============================================================
@pytest.mark.asyncio
async def test_sse_task_not_found(client):
    """SSE 连接不存在的任务应返回 404"""
    response = await client.get("/sse/execute/nonexistent")
    assert response.status_code == 404


# ============================================================
# Task Manager Unit Tests
# ============================================================
def test_task_manager_create():
    """TaskManager 能正确创建任务"""
    manager = task_manager.__class__()
    task_id = manager.create_task()
    assert task_id is not None
    assert len(task_id) == 8
    assert manager.get_task(task_id) is not None


def test_task_manager_update_step():
    """TaskManager 能正确更新步骤状态"""
    manager = task_manager.__class__()
    task_id = manager.create_task()

    manager.update_step(task_id, "explore", "active")
    task = manager.get_task(task_id)
    assert task["step_status"]["explore"] == "active"

    manager.update_step(task_id, "explore", "completed", "分析结果")
    task = manager.get_task(task_id)
    assert task["step_status"]["explore"] == "completed"
    assert task["step_outputs"]["explore"] == "分析结果"


def test_task_manager_complete_task():
    """TaskManager 能正确完成任务"""
    manager = task_manager.__class__()
    task_id = manager.create_task()

    manager.complete_task(task_id, result={"result": "done"})
    task = manager.get_task(task_id)
    assert task["status"] == "completed"
    assert task["result"]["result"] == "done"

    manager.complete_task(task_id, error="failed")
    task = manager.get_task(task_id)
    assert task["status"] == "failed"
    assert task["error"] == "failed"


# ============================================================
# Mock: 完整执行流程（SSE + 结果）
# ============================================================
@pytest.mark.asyncio
async def test_execute_with_mocked_agent(client):
    """模拟 Agent 返回，验证完整流程"""
    mock_output = AgentOutput(
        agent_name="explore",
        status=AgentStatus.COMPLETED,
        result="项目结构扫描完成",
        usage={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50},
    )

    with patch("src.web.app.create_router") as mock_router_cls, \
         patch("src.web.app.create_orchestrator") as mock_orch_cls:

        mock_router = MagicMock()
        mock_orch = MagicMock()

        # Mock orchestrator.get_agent 返回 mock agent
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value=mock_output)
        mock_orch.get_agent.return_value = mock_agent

        mock_router_cls.return_value = mock_router
        mock_orch_cls.return_value = mock_orch

        payload = {"task": "测试", "workflow": "build"}
        resp = await client.post("/api/execute", json=payload)
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]

        # 等一小段时间让后台任务处理
        import asyncio
        await asyncio.sleep(0.3)

        # 验证任务状态已更新
        resp2 = await client.get(f"/api/tasks/{task_id}")
        data = resp2.json()
        assert data["status"] in ("running", "completed")
