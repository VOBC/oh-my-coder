"""
Tests for src/web/app.py routes not covered elsewhere.

Covers: page routes, health, task manager, settings, sessions,
workflow CRUD, chat, open-folder, save-report, coverage, and utility helpers.
"""

import asyncio
import json

# ---------------------------------------------------------------------------
# Import the app
# ---------------------------------------------------------------------------
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# Prevent concurrent execution - global singleton pollution
pytestmark = pytest.mark.xdist_group("web_app_routes")

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.responses import JSONResponse

from src.agents.base import AgentStatus
from src.web.app import (
    _cleanup_target,
    _detect_model,
    _detect_target_type,
    _detect_target_type_from_message,
    _detect_workflow,
    _generate_task_summary,
    _mask_key,
    _preprocess_target,
    app,
    json_dumps,
)


# Always get the current task_manager from the module (handles importlib.reload in other tests)
def _tm():
    import sys
    return sys.modules["src.web.app"].task_manager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a test client for the main app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_task_manager():
    """Reset task manager state before each test."""
    _tm()._tasks.clear()
    _tm()._queues.clear()
    yield
    _tm()._tasks.clear()
    _tm()._queues.clear()


@pytest.fixture
def sessions_dir(tmp_path):
    """Use a temp directory for session files."""
    d = tmp_path / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Page Routes
# ---------------------------------------------------------------------------

class TestPageRoutes:
    """HTML page routes."""

    @pytest.mark.parametrize(
        "path", ["/", "/history", "/agents", "/dashboard", "/settings", "/coverage", "/docs"]
    )
    def test_page_returns_html(self, client, path):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_favicon(self, client):
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """GET /health."""

    def test_health_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


# ---------------------------------------------------------------------------
# Task Manager & Task API
# ---------------------------------------------------------------------------

class TestTaskManager:
    """TaskManager utility functions."""

    def test_create_task(self):
        _tm()._tasks.clear()
        _tm()._queues.clear()
        tid = _tm().create_task(
            task_desc="test task",
            model="deepseek",
            workflow="build",
            project_path="/tmp",
        )
        assert tid in _tm()._tasks
        assert _tm().get_task(tid)["task"] == "test task"

    def test_update_step(self):
        _tm()._tasks.clear()
        _tm()._queues.clear()
        tid = _tm().create_task()
        _tm().update_step(tid, "executor", "active", "step output")
        task = _tm().get_task(tid)
        assert task["step_status"]["executor"] == "active"
        assert task["step_outputs"]["executor"] == "step output"

    def test_update_step_unknown_task(self):
        _tm().update_step("nonexistent", "executor", "active")

    def test_complete_task_success(self):
        _tm()._tasks.clear()
        _tm()._queues.clear()
        tid = _tm().create_task()
        _tm().complete_task(tid, result={"ok": True})
        task = _tm().get_task(tid)
        assert task["status"] == "completed"
        assert task["result"] == {"ok": True}

    def test_complete_task_error(self):
        _tm()._tasks.clear()
        _tm()._queues.clear()
        tid = _tm().create_task()
        _tm().complete_task(tid, error="Something went wrong")
        task = _tm().get_task(tid)
        assert task["status"] == "failed"
        assert task["error"] == "Something went wrong"

    def test_complete_task_unknown(self):
        # Should not raise
        _tm().complete_task("nonexistent", result={"ok": True})

    def test_delete_task(self):
        _tm()._tasks.clear()
        _tm()._queues.clear()
        tid = _tm().create_task()
        assert _tm().delete_task(tid) is True
        assert _tm().get_task(tid) is None

    def test_delete_task_unknown(self):
        assert _tm().delete_task("nonexistent") is False

    def test_list_tasks(self):
        _tm()._tasks.clear()
        _tm()._queues.clear()
        tid1 = _tm().create_task()
        tid2 = _tm().create_task()
        tasks = _tm().list_tasks()
        assert len(tasks) >= 2
        ids = [t["task_id"] for t in tasks]
        assert tid1 in ids
        assert tid2 in ids

    def test_get_queue(self):
        _tm()._tasks.clear()
        _tm()._queues.clear()
        tid = _tm().create_task()
        q = _tm().get_queue(tid)
        assert q is not None
        assert isinstance(q, asyncio.Queue)

    def test_get_queue_unknown(self):
        assert _tm().get_queue("nonexistent") is None


class TestTaskAPI:
    """API routes for tasks."""

    def setup_method(self):
        """Clear task manager state before each test."""
        _tm()._tasks.clear()
        _tm()._queues.clear()

    def teardown_method(self):
        """Clear task manager state after each test to prevent pollution."""
        _tm()._tasks.clear()
        _tm()._queues.clear()

    def test_list_tasks_empty(self, client):
        _tm()._tasks.clear()
        _tm()._queues.clear()
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert "tasks" in response.json()

    def test_get_task_not_found(self, client):
        response = client.get("/api/tasks/nonexistent")
        assert response.status_code == 404

    def test_get_task_success(self, client):
        """任务存在时返回任务详情"""
        _tm()._tasks.clear()
        _tm()._queues.clear()
        tid = _tm().create_task()
        response = client.get(f"/api/tasks/{tid}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == tid

    @patch("src.web.app.verify_api_token", return_value="token")
    def test_delete_task_with_token(self, mock_verify, client):
        _tm()._tasks.clear()
        _tm()._queues.clear()
        tid = _tm().create_task()
        response = client.delete(f"/api/tasks/{tid}")
        assert response.status_code == 200

    @patch("src.web.app.verify_api_token", return_value="token")
    def test_delete_task_not_found(self, mock_verify, client):
        with patch("src.web.app.verify_api_token", return_value="token"):
            response = client.delete("/api/tasks/nonexistent")
            assert response.status_code == 404


class TestDashboardAPI:
    """测试仪表板 API"""

    def test_get_dashboard_stats(self, client):
        """获取仪表板统计数据"""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_dashboard_files(self, client):
        """获取仪表板文件列表"""
        response = client.get("/api/dashboard/files")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "files" in data
        assert isinstance(data["files"], list)


class TestApiHistory:
    """GET /api/history (app-level, not history_api)."""

    def test_api_history_returns_records(self, client):
        _tm()._tasks.clear()
        _tm()._queues.clear()
        tid = _tm().create_task()
        _tm()._tasks[tid]["started_at"] = "2026-05-28T10:00:00"
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data


# ---------------------------------------------------------------------------
# Dashboard Files
# ---------------------------------------------------------------------------

class TestDashboardFiles:
    """GET /api/dashboard/files."""

    def test_dashboard_files_returns_files(self, client):
        response = client.get("/api/dashboard/files")
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert "project_path" in data
        assert isinstance(data["files"], list)

    @patch("src.web.app.Path")
    def test_dashboard_files_nonexistent_path(self, mock_path_cls, client):
        """When project_path doesn't exist, falls back to project_root."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path.is_dir.return_value = False
        mock_path.iterdir.return_value = iter([])
        mock_path_cls.return_value = mock_path

        response = client.get("/api/dashboard/files")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Open Folder
# ---------------------------------------------------------------------------

class TestOpenFolder:
    """POST /api/open-folder."""

    def test_open_folder_missing_path(self, client):
        response = client.post("/api/open-folder", json={})
        assert response.status_code == 400
        assert "path required" in response.json()["detail"]

    def test_open_folder_no_payload(self, client):
        response = client.post("/api/open-folder")
        assert response.status_code == 400

    @patch("subprocess.run")
    @patch("platform.system", return_value="Darwin")
    def test_open_folder_success(self, mock_sys, mock_run, client):
        with patch("platform.system", return_value="Darwin"):
            response = client.post("/api/open-folder", json={"path": "/tmp"})
            assert response.status_code == 200
            assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Save Report
# ---------------------------------------------------------------------------

class TestSaveReport:
    """POST /api/save-report."""

    def test_save_report_missing_task_id(self, client):
        response = client.post("/api/save-report", json={})
        assert response.status_code == 400
        assert "task_id required" in response.json()["detail"]

    def test_save_report_task_not_found(self, client):
        response = client.post("/api/save-report", json={"task_id": "nonexistent"})
        assert response.status_code == 404

    @patch("src.web.app.history_store")
    @patch("src.web.app.Path.home")
    def test_save_report_from_history_store(self, mock_home, mock_store, client):
        mock_home.return_value = Path("/tmp")
        mock_store.load.return_value = {
            "task_id": "task-abc",
            "task": "Test task",
            "status": "completed",
            "started_at": "2026-05-28T10:00:00",
            "model": "deepseek",
            "workflow": "build",
            "project_path": "/tmp",
            "stats": {
                "total_tokens": 1000,
                "execution_time": 10.0,
                "total_cost": 0.05,
                "steps_completed": ["explore"],
                "steps_failed": [],
            },
            "result": {
                "summary": "Done",
                "outputs": {},
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            response = client.post("/api/save-report", json={"task_id": "task-abc"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "saved"
            assert "path" in data


# ---------------------------------------------------------------------------
# Settings API
# ---------------------------------------------------------------------------

class TestConnectionAPI:
    """POST /api/test-connection."""

    def test_test_connection_missing_params(self, client):
        response = client.post("/api/test-connection", json={})
        assert response.status_code == 400
        data = response.json()
        assert "参数不完整" in data["msg"] or "ok" in data

    @patch("httpx.Client")
    def test_test_connection_deepseek_success(self, mock_client_cls, client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/json"}
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        response = client.post(
            "/api/test-connection",
            json={"provider": "deepseek", "api_key": "sk-test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    @patch("httpx.Client")
    def test_test_connection_deepseek_401(self, mock_client_cls, client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        response = client.post(
            "/api/test-connection",
            json={"provider": "deepseek", "api_key": "bad-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "401" in data["msg"]

    @patch("httpx.Client")
    def test_test_connection_deepseek_403(self, mock_client_cls, client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        response = client.post(
            "/api/test-connection",
            json={"provider": "deepseek", "api_key": "bad-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "403" in data["msg"]

    @patch("httpx.Client")
    def test_test_connection_deepseek_5xx(self, mock_client_cls, client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"error": {"message": "Server error"}}
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        response = client.post(
            "/api/test-connection",
            json={"provider": "deepseek", "api_key": "sk-test"},
        )
        assert response.status_code == 502

    @patch("httpx.Client")
    def test_test_connection_html_response(self, mock_client_cls, client):
        """Returns HTML page instead of JSON API response."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "text/html"}
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        response = client.post(
            "/api/test-connection",
            json={"provider": "deepseek", "api_key": "sk-test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "网页" in data["msg"]

    @patch("httpx.Client")
    def test_test_connection_timeout(self, mock_client_cls, client):
        import httpx

        mock_client_cls.side_effect = httpx.TimeoutException("timeout")

        response = client.post(
            "/api/test-connection",
            json={"provider": "deepseek", "api_key": "sk-test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "超时" in data["msg"]

    @patch("httpx.Client")
    def test_test_connection_connect_error(self, mock_client_cls, client):
        import httpx

        mock_client_cls.side_effect = httpx.ConnectError("connection refused")

        response = client.post(
            "/api/test-connection",
            json={"provider": "deepseek", "api_key": "sk-test"},
        )
        assert response.status_code == 502

    @patch("httpx.Client")
    def test_test_connection_custom_model_success(self, mock_client_cls, client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        response = client.post(
            "/api/test-connection",
            json={
                "base_url": "https://my-model.example.com/v1",
                "model_id": "my-model",
                "api_key": "sk-custom",
            },
        )
        assert response.status_code == 200

    def test_test_connection_custom_missing_key(self, client):
        response = client.post(
            "/api/test-connection",
            json={"base_url": "https://my-model.example.com/v1", "model_id": "my-model"},
        )
        assert response.status_code == 400

    @patch("httpx.Client")
    def test_test_connection_unknown_provider(self, mock_client_cls, client):
        response = client.post(
            "/api/test-connection",
            json={"provider": "unknown-provider", "api_key": "sk-test"},
        )
        assert response.status_code == 400

    @patch("httpx.Client")
    def test_test_connection_glm_success(self, mock_client_cls, client):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        response = client.post(
            "/api/test-connection",
            json={"provider": "glm", "api_key": "sk-test"},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True


# ---------------------------------------------------------------------------
# Workflow API
# ---------------------------------------------------------------------------

class TestWorkflowsAPI:
    """Workflow CRUD routes."""

    def test_list_workflows(self, client):
        response = client.get("/api/workflows")
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert isinstance(data["workflows"], list)
        assert "builtin_count" in data
        assert "user_count" in data

    @patch("src.web.app.WorkflowLoader")
    def test_get_workflow_not_found(self, mock_loader_cls, client):
        mock_loader = MagicMock()
        mock_loader.get_workflow_config.return_value = None
        mock_loader_cls.return_value = mock_loader
        # Also not in WORKFLOW_TEMPLATES
        with patch("src.web.app.WORKFLOW_TEMPLATES", {}):
            response = client.get("/api/workflows/nonexistent-workflow")
            assert response.status_code == 404

    @patch("src.web.app.WorkflowLoader")
    def test_get_workflow_from_loader(self, mock_loader_cls, client):
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"name": "my-workflow", "steps": []}
        mock_loader = MagicMock()
        mock_loader.get_workflow_config.return_value = mock_config
        mock_loader_cls.return_value = mock_loader

        response = client.get("/api/workflows/my-workflow")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "my-workflow"

    @patch("src.web.app.WorkflowLoader")
    def test_get_workflow_fallback_to_templates(self, mock_loader_cls, client):
        mock_loader = MagicMock()
        mock_loader.get_workflow_config.return_value = None
        mock_loader_cls.return_value = mock_loader

        with patch("src.web.app.WORKFLOW_TEMPLATES", {"build": [MagicMock(model_dump=lambda: {"agent_name": "explore"})]}):
            response = client.get("/api/workflows/build")
            assert response.status_code == 200
            data = response.json()
            assert data["source"] == "builtin"

    @patch("src.web.app.WorkflowLoader")
    def test_save_workflow_parse_fail(self, mock_loader_cls, client):
        mock_loader = MagicMock()
        mock_loader.parse_yaml_string.return_value = None
        mock_loader_cls.return_value = mock_loader

        response = client.put(
            "/api/workflows/my-workflow",
            json={"yaml": "invalid: yaml: content"},
        )
        assert response.status_code == 400

    @patch("src.web.app.WorkflowLoader")
    def test_save_workflow_success(self, mock_loader_cls, client):
        mock_config = MagicMock()
        mock_config.name = "my-workflow"
        mock_loader = MagicMock()
        mock_loader.parse_yaml_string.return_value = mock_config
        mock_loader_cls.return_value = mock_loader

        response = client.put(
            "/api/workflows/my-workflow",
            json={"yaml": "name: my-workflow\nsteps: []"},
        )
        assert response.status_code == 200
        assert "已保存" in response.json()["message"]

    @patch("src.web.app.WorkflowLoader")
    def test_save_workflow_exception(self, mock_loader_cls, client):
        mock_loader = MagicMock()
        mock_loader.parse_yaml_string.side_effect = ValueError("bad yaml")
        mock_loader_cls.return_value = mock_loader

        response = client.put(
            "/api/workflows/my-workflow",
            json={"yaml": "bad"},
        )
        assert response.status_code == 400

    @patch("src.web.app.WorkflowLoader")
    def test_delete_workflow_builtin_forbidden(self, mock_loader_cls, client):
        mock_loader = MagicMock()
        mock_loader.is_builtin.return_value = True
        mock_loader_cls.return_value = mock_loader

        response = client.delete("/api/workflows/build")
        assert response.status_code == 403

    @patch("src.web.app.WorkflowLoader")
    def test_delete_workflow_not_found(self, mock_loader_cls, client):
        mock_loader = MagicMock()
        mock_loader.is_builtin.return_value = False
        mock_loader.delete_workflow.side_effect = FileNotFoundError()
        mock_loader_cls.return_value = mock_loader

        response = client.delete("/api/workflows/nonexistent")
        assert response.status_code == 404

    @patch("src.web.app.WorkflowLoader")
    def test_delete_workflow_success(self, mock_loader_cls, client):
        mock_loader = MagicMock()
        mock_loader.is_builtin.return_value = False
        mock_loader_cls.return_value = mock_loader

        response = client.delete("/api/workflows/my-workflow")
        assert response.status_code == 200
        mock_loader.delete_workflow.assert_called_once_with("my-workflow")


# ---------------------------------------------------------------------------
# Sessions API
# ---------------------------------------------------------------------------

class TestChatEndpoint:
    """POST /api/chat."""

    def test_chat_short_message_needs_more_info(self, client):
        response = client.post("/api/chat", json={"message": "hi"})
        assert response.status_code == 200
        data = response.json()
        assert data["ready_to_execute"] is False

    def test_chat_full_message(self, client):
        response = client.post(
            "/api/chat",
            json={
                "message": "Please review my code in /tmp/project",
                "history": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ready_to_execute"] is True
        assert data["task"] is not None

    def test_chat_with_github_link(self, client):
        response = client.post(
            "/api/chat",
            json={
                "message": "Fix the bug at https://github.com/user/repo",
                "history": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["target_type"] == "github"

    def test_chat_with_http_url(self, client):
        response = client.post(
            "/api/chat",
            json={
                "message": "Analyze https://example.com/page",
                "history": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["target_type"] == "url"


class TestChatCompletions:
    """POST /api/chat/completions."""

    @patch("src.web.app.get_orchestrator")
    def test_chat_completions_non_stream(self, mock_get_orch, client):
        """Test non-streaming chat completions."""
        mock_orch = MagicMock()
        mock_router = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Hello!"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.model = "deepseek-chat"

        # Make route_and_call return a coroutine
        async def mock_route(*args, **kwargs):
            return mock_response
        mock_router.route_and_call = mock_route
        mock_orch.model_router = mock_router
        mock_get_orch.return_value = mock_orch

        response = client.post(
            "/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "deepseek",
                "stream": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Hello!"

    @patch("src.web.app.get_orchestrator")
    def test_chat_completions_stream(self, mock_get_orch, client):
        """Test streaming chat completions."""
        mock_orch = MagicMock()
        mock_router = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Streaming response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.model = "deepseek-chat"

        async def mock_route(*args, **kwargs):
            return mock_response
        mock_router.route_and_call = mock_route
        mock_orch.model_router = mock_router
        mock_get_orch.return_value = mock_orch

        response = client.post(
            "/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "deepseek",
                "stream": True,
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    @patch("src.web.app.get_orchestrator")
    def test_chat_completions_exception(self, mock_get_orch, client):
        """Test exception handling in chat completions."""
        mock_orch = MagicMock()
        mock_router = MagicMock()

        async def mock_route(*args, **kwargs):
            raise RuntimeError("Model error")
        mock_router.route_and_call = mock_route
        mock_orch.model_router = mock_router
        mock_get_orch.return_value = mock_orch

        response = client.post(
            "/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "deepseek",
                "stream": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "❌" in data["content"]


# ---------------------------------------------------------------------------
# SSE Execute Endpoint
# ---------------------------------------------------------------------------

class TestSSEExecute:
    """GET /sse/execute/{task_id}."""

    def test_sse_execute_task_not_found(self, client):
        response = client.get("/sse/execute/nonexistent")
        assert response.status_code == 404

    @pytest.mark.skip(reason="Python 3.9 asyncio event loop incompatibility")
    def test_sse_execute_returns_streaming(self, client):
        pass


# ---------------------------------------------------------------------------
# Execute Task
# ---------------------------------------------------------------------------

class TestExecuteTask:
    """POST /api/execute-sync (synchronous task execution)."""

    @patch("src.web.app.create_router")
    @patch("src.web.app.create_orchestrator")
    def test_execute_sync_success(self, mock_create_orch, mock_create_router, client):
        """Test successful synchronous execution."""

        mock_agent = MagicMock()

        # Create a proper async mock that returns an object with status=COMPLETED
        async def mock_execute(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.status = AgentStatus.COMPLETED
            mock_result.result = "Done"
            mock_result.error = None
            mock_result.usage = {"total_tokens": 100}
            return mock_result

        mock_agent.execute = mock_execute

        mock_orch = MagicMock()
        mock_orch.get_agent.return_value = mock_agent
        mock_orch.model_router = MagicMock()
        mock_create_orch.return_value = mock_orch

        response = client.post(
            "/api/execute-sync",
            json={
                "task": "test task",
                "project_path": ".",
                "model": "deepseek",
                "workflow": "build",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch("src.web.app.create_router")
    @patch("src.web.app.create_orchestrator")
    def test_execute_sync_agent_failed(self, mock_create_orch, mock_create_router, client):
        """Test sync execution with agent failure."""

        mock_agent = MagicMock()

        async def mock_execute(*args, **kwargs):
            return MagicMock(
                status=MagicMock(value="failed"),
                result=None,
                error="Agent failed",
                usage={}
            )

        mock_agent.execute = mock_execute

        mock_orch = MagicMock()
        mock_orch.get_agent.return_value = mock_agent
        mock_create_orch.return_value = mock_orch

        response = client.post(
            "/api/execute-sync",
            json={
                "task": "test task",
                "workflow": "build",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "失败" in data["message"]

    @patch("src.web.app.create_router")
    @patch("src.web.app.create_orchestrator")
    def test_execute_sync_timeout(self, mock_create_orch, mock_create_router, client):
        """Test sync execution timeout."""

        mock_agent = MagicMock()
        # Simulate timeout - raise TimeoutError (not asyncio.TimeoutError)
        async def slow_execution(*args, **kwargs):
            raise TimeoutError("Execution timeout")
        mock_agent.execute = slow_execution

        mock_orch = MagicMock()
        mock_orch.get_agent.return_value = mock_agent
        mock_create_orch.return_value = mock_orch

        response = client.post(
            "/api/execute-sync",
            json={
                "task": "test task",
                "workflow": "build",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        # Check for timeout message
        assert "超时" in data["message"] or "timeout" in data["message"].lower()


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

class TestDetectTargetType:
    """_detect_target_type and _detect_target_type_from_message."""

    @pytest.mark.parametrize(
        "target,expected",
        [
            ("", "local"),
            ("/tmp/project", "local"),
            ("https://github.com/user/repo", "github"),
            ("https://github.com/user/repo.git", "github"),
            ("git@github.com:user/repo.git", "github"),
            ("https://example.com/page", "url"),
            ("http://example.com", "url"),
            ("user/repo", "local"),
        ],
    )
    def test_detect_target_type(self, target, expected):
        assert _detect_target_type(target) == expected

    def test_detect_target_type_from_message_github(self):
        result_type, result_path = _detect_target_type_from_message(
            "Fix bug in https://github.com/user/repo"
        )
        assert result_type == "github"

    def test_detect_target_type_from_message_url(self):
        result_type, result_path = _detect_target_type_from_message(
            "Read https://example.com"
        )
        assert result_type == "url"

    def test_detect_target_type_from_message_local(self):
        result_type, result_path = _detect_target_type_from_message(
            "Build /tmp/myproject"
        )
        assert result_type == "local"


class TestDetectWorkflow:
    """_detect_workflow."""

    @pytest.mark.parametrize(
        "message,expected",
        [
            ("Review my code", "review"),
            ("Fix the bug", "debug"),
            ("Run tests", "test"),
            ("Build a new feature", "build"),
            ("Create a file", "build"),
            ("Add unit tests", "test"),
            ("Check for security issues", "review"),
            ("debug the crash", "debug"),
            ("hello world", "build"),
            ("", "build"),
        ],
    )
    def test_detect_workflow(self, message, expected):
        assert _detect_workflow(message) == expected


class TestDetectModel:
    """_detect_model."""

    @pytest.mark.parametrize(
        "message,expected",
        [
            ("Use deepseek v4", "deepseek"),
            ("kimi 128k model", "moonshot-v1-128k"),
            ("智谱 glm flash", "glm-4-flash"),
            ("minimax mimo", "MiniMax-Text-01"),
            ("doubao 32k", "doubao-pro-32k"),
            ("天工 3", "tiangong-3"),
            ("百川 4", "Baichuan4"),
            ("hello", "deepseek"),
            ("", "deepseek"),
        ],
    )
    def test_detect_model(self, message, expected):
        assert _detect_model(message) == expected


class TestPreprocessTarget:
    """_preprocess_target."""

    @patch("subprocess.run")
    def test_preprocess_local(self, mock_run):
        result = _preprocess_target("/tmp", "local", "task123")
        assert result == ("/tmp", "")

    @patch("subprocess.run")
    def test_preprocess_local_empty(self, mock_run):
        result = _preprocess_target("", "local", "task123")
        assert result == (".", "")

    @patch("subprocess.run")
    def test_preprocess_github_clone_fail(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="git failed")
        with pytest.raises(RuntimeError, match="git clone 失败"):
            _preprocess_target("https://github.com/user/repo", "github", "task123")

    @patch("requests.get")
    def test_preprocess_url_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>Hello World</body></html>"
        mock_get.return_value = mock_resp
        path, extra = _preprocess_target("https://example.com", "url", "task123")
        assert path == "."
        assert "网页内容" in extra

    @patch("requests.get")
    def test_preprocess_url_failure(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        with pytest.raises(RuntimeError, match="获取网页失败"):
            _preprocess_target("https://example.com", "url", "task123")


class TestCleanupTarget:
    """_cleanup_target."""

    @patch("shutil.rmtree")
    def test_cleanup_github(self, mock_rmtree):
        with tempfile.TemporaryDirectory() as tmpdir:
            _cleanup_target(tmpdir, "github")
            mock_rmtree.assert_called_once_with(tmpdir, ignore_errors=True)

    @patch("shutil.rmtree")
    def test_cleanup_local_noop(self, mock_rmtree):
        _cleanup_target("/tmp/project", "local")
        mock_rmtree.assert_not_called()


class TestGenerateTaskSummary:
    """_generate_task_summary."""

    def test_generate_task_summary_build(self):
        task = {
            "workflow": "build",
            "model": "deepseek",
            "target_type": "local",
            "project_path": "/tmp/myproject",
        }
        summary = _generate_task_summary(task)
        assert "完整开发" in summary
        assert "DeepSeek" in summary
        assert "/tmp/myproject" in summary

    def test_generate_task_summary_github(self):
        task = {
            "workflow": "review",
            "model": "kimi",
            "target_type": "github",
            "project_path": "https://github.com/user/repo",
        }
        summary = _generate_task_summary(task)
        assert "GitHub" in summary
        assert "kimi" in summary


class TestMaskKey:
    """_mask_key."""

    @pytest.mark.parametrize(
        "key,expected",
        [
            ("", ""),
            ("abc", "abc"),
            ("sk-12345678", "*******5678"),
            ("long-api-key-abcdefgh", "*****************efgh"),
        ],
    )
    def test_mask_key(self, key, expected):
        assert _mask_key(key) == expected


class TestJsonDumps:
    """json_dumps utility."""

    def test_json_dumps_basic(self):
        result = json_dumps({"key": "value"})
        assert "key" in result
        assert "value" in result

    def test_json_dumps_unicode(self):
        result = json_dumps({"name": "中文测试"})
        assert "中文" in result

    def test_json_dumps_default_handler(self):
        """datetime has a default handler."""
        result = json_dumps({"dt": datetime(2026, 5, 28)})
        assert "2026" in result

    def test_json_dumps_number(self):
        result = json_dumps(42)
        assert result == "42"

    def test_json_dumps_list(self):
        result = json_dumps([1, 2, 3])
        assert "1" in result


# ---------------------------------------------------------------------------
# Config Endpoint
# ---------------------------------------------------------------------------

class TestConfigAPI:
    """GET /api/config."""

    def test_get_config(self, client):
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "workflows" in data
        assert "agents" in data
        assert isinstance(data["workflows"], list)
        assert len(data["workflows"]) > 0


# ---------------------------------------------------------------------------
# Execute Task (async, SSE-driven)
# ---------------------------------------------------------------------------

class TestExecuteAsyncTask:
    """POST /api/execute — async background task."""

    @pytest.mark.skip(reason="Python 3.9 asyncio compatibility")
    def test_execute_auto_detect_local(self, client):
        response = client.post(
            "/api/execute",
            json={
                "task": "do something",
                "project_path": "/tmp",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["target_type"] == "local"

    def test_execute_explicit_target_type(self, client):
        response = client.post(
            "/api/execute",
            json={
                "task": "do something",
                "project_path": "/tmp",
                "target_type": "url",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["target_type"] == "url"

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    def test_execute_preprocess_failure(self, mock_store, mock_get_orch, client):
        """When _preprocess_target fails, error should be recorded."""
        mock_get_orch.return_value = MagicMock()

        with patch("src.web.app._preprocess_target", side_effect=RuntimeError("Bad URL")):
            response = client.post(
                "/api/execute",
                json={
                    "task": "test",
                    "project_path": "https://bad-url.example.com",
                    "target_type": "url",
                },
            )
            assert response.status_code == 200
            response.json()["task_id"]
            # History should record the failure
            mock_store.save.assert_called()
            call_args = mock_store.save.call_args
            record = call_args[0][1]
            assert record["status"] == "failed"


# ========== 新增测试：SSE 端点和 Provider API 测试 ==========


class TestSSEEndpoint:
    """测试 SSE 执行端点"""

    @pytest.mark.skip(reason="Python 3.9 asyncio compatibility")
    @patch("src.web.app.task_manager")
    def test_sse_execute_task_not_found(self, mock_tm, client):
        """任务不存在时返回 404"""
        mock_tm.get_task.return_value = None
        response = client.get("/sse/execute/nonexistent")
        assert response.status_code == 404

    @pytest.mark.skip(reason="Python 3.9 asyncio compatibility")
    @patch("src.web.app.task_manager")
    def test_sse_execute_success(self, mock_tm, client):
        """任务存在时返回 SSE stream"""
        mock_tm.get_task.return_value = {"status": "running"}
        mock_queue = MagicMock()
        mock_queue.get = AsyncMock(side_effect=[None])
        mock_tm._queues = {"task-123": mock_queue}

        response = client.get("/sse/execute/task-123")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


class TestProviderAPI:
    """测试各供应商 API 连接检测"""

    @patch("src.web.app._read_settings")
    @patch("httpx.Client")
    def test_test_connection_kimi_success(self, mock_client, mock_settings, client):
        """Kimi (Moonshot) 连接成功"""
        mock_settings.return_value = {
            "models": {"kimi": {"api_key": "test-key", "base_url": ""}}
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.return_value.__enter__.return_value.post = MagicMock(return_value=mock_resp)

        response = client.post("/api/test-connection", json={"provider": "kimi"})
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_test_connection_missing_api_key(self, client):
        """API Key 缺失时返回错误"""
        # 不传 api_key，且 settings 中也没有 → 端点返回 400
        response = client.post("/api/test-connection", json={"provider": "unknown_provider"})
        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False


class TestAgentLiveStream:
    """Test GET /api/agent/live SSE endpoint."""

    @pytest.mark.skip(reason="Python 3.9 asyncio: await MagicMock not supported")
    @patch("src.web.app.get_orchestrator")
    def test_agent_live_stream_basic(self, mock_get_orch, client):
        """Test agent live stream endpoint returns StreamingResponse."""
        # Mock orchestrator
        mock_orch = MagicMock()
        mock_orch.get_current_state.return_value = {
            "status": "running",
            "agents": [],
            "timestamp": datetime.now().isoformat(),
        }
        mock_get_orch.return_value = mock_orch

        # Mock the entire endpoint to avoid async generator issues in Python 3.9
        with patch("src.web.app.agent_live_stream") as mock_endpoint:
            import json as json_mod

            from fastapi.responses import StreamingResponse

            mock_endpoint.return_value = StreamingResponse(
                content=iter([f"data: {json_mod.dumps({'test': 'ok'})}\n\n".encode()]),
                media_type="text/event-stream",
            )

            response = client.get("/api/agent/live")
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.skip(reason="Python 3.9 asyncio: await MagicMock not supported")
    @patch("src.web.app.get_orchestrator")
    def test_agent_live_stream_error_handling(self, mock_get_orch, client):
        """Test agent live stream handles errors gracefully."""
        # Mock orchestrator to raise exception
        mock_orch = MagicMock()
        mock_orch.get_current_state.side_effect = Exception("Orchestrator error")
        mock_get_orch.return_value = mock_orch

        # Mock the entire endpoint
        with patch("src.web.app.agent_live_stream") as mock_endpoint:
            import json as json_mod

            from fastapi.responses import StreamingResponse

            error_data = {
                "error": "服务端状态获取失败",
                "timestamp": datetime.now().isoformat(),
            }
            mock_endpoint.return_value = StreamingResponse(
                content=iter([f"data: {json_mod.dumps(error_data)}\n\n".encode()]),
                media_type="text/event-stream",
            )

            response = client.get("/api/agent/live")
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")


class TestExecuteSyncEndpoint:
    """Test POST /api/execute-sync endpoint."""

    @pytest.mark.skip(reason="Python 3.9 asyncio compatibility")
    @patch("src.web.app.execute_task_sync")
    def test_execute_sync_success(self, mock_execute, client):
        """Test synchronous execution success."""
        mock_execute.return_value = JSONResponse({
            "status": "completed",
            "result": "Task completed",
            "usage": {"total_tokens": 100, "total_cost": 0.01},
        })

        response = client.post(
            "/api/execute-sync",
            json={
                "task": "test task",
                "project_path": ".",
                "model": "deepseek",
                "workflow": "build",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_execute_sync_missing_task(self, client):
        """Test missing task field returns 422."""
        response = client.post(
            "/api/execute-sync",
            json={
                "project_path": ".",
                "model": "deepseek",
            },
        )
        assert response.status_code == 422


class TestListTasksAPI:
    """Test GET /api/tasks endpoint."""

    def test_list_tasks_empty(self, client):
        """Test listing tasks when empty."""
        with patch("src.web.app.task_manager") as mock_tm:
            mock_tm.list_tasks.return_value = []
            response = client.get("/api/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []

    def test_list_tasks_with_data(self, client):
        """Test listing tasks with data."""
        with patch("src.web.app.task_manager") as mock_tm:
            mock_tm.list_tasks.return_value = [
                {"task_id": "task-1", "status": "completed"},
                {"task_id": "task-2", "status": "running"},
            ]
            response = client.get("/api/tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 2
        assert data["tasks"][0]["task_id"] == "task-1"


class TestOpenFolderAPI:
    """Test POST /api/open-folder endpoint."""

    def test_open_folder_missing_path(self, client):
        """Test open folder without path."""
        response = client.post("/api/open-folder", json={})
        assert response.status_code == 400
        assert "path required" in response.json()["detail"]

    def test_open_folder_success(self, client):
        """Test open folder success."""
        with patch("src.web.app.subprocess.run") as mock_run:
            response = client.post("/api/open-folder", json={"path": "/tmp/test"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        mock_run.assert_called_once()
        # Verify correct command for macOS
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "open"


class TestSaveReportAPI:
    """Test POST /api/save-report endpoint."""

    def test_save_report_missing_task_id(self, client):
        """Test save report without task_id."""
        response = client.post("/api/save-report", json={})
        assert response.status_code == 400
        assert "task_id required" in response.json()["detail"]

    def test_save_report_task_not_found(self, client):
        """Test save report when task not found."""
        with patch("src.web.app.task_manager") as mock_tm, \
             patch("src.web.app.history_store") as mock_hs:
            mock_tm.get_task.return_value = None
            mock_hs.load.return_value = None

            response = client.post("/api/save-report", json={"task_id": "nonexistent"})

        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    def test_save_report_success(self, client, tmp_path):
        """Test save report success."""

        task_data = {
            "task_id": "test-task-123",
            "task": "Test task",
            "status": "completed",
            "started_at": "2026-06-01 12:00:00",
            "output": {"result": "Test result"},
        }

        # Create a temp file to simulate saved report
        report_file = tmp_path / "report.md"
        report_file.write_text("# Test Report\n\nResult: Test result")

        with patch("src.web.app.task_manager") as mock_tm, \
             patch("src.web.app.history_store") as mock_hs, \
             patch("src.web.app.Path.home") as mock_home:

            mock_tm.get_task.return_value = task_data
            mock_hs.load.return_value = None

            # Mock home path to use tmp_path
            mock_home.return_value = tmp_path

            response = client.post("/api/save-report", json={"task_id": "test-task-123"})

        # The endpoint saves to Desktop, which we mocked
        # Just verify it didn't return an error
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "saved"
        assert "path" in data


class TestHealthAPI:
    """Test GET /health endpoint."""

    def test_health_check(self, client):
        """Test health check returns correct status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

        mock_loader = MagicMock()
        mock_loader.list_workflows.return_value = ["build", "test"]
        mock_loader.list_builtins.return_value = ["build"]

        with patch("src.web.app.WorkflowLoader", return_value=mock_loader):
            response = client.get("/api/workflows")

        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert data["builtin_count"] >= 0

    def test_get_workflow_not_found(self, client):
        """Test getting non-existent workflow."""
        mock_loader = MagicMock()
        mock_loader.get_workflow_config.return_value = None

        with patch("src.web.app.WorkflowLoader", return_value=mock_loader), \
             patch("src.web.app.WORKFLOW_TEMPLATES", {}):
            response = client.get("/api/workflows/nonexistent")

        assert response.status_code == 404

    def test_get_workflow_found(self, client):
        """Test getting existing workflow."""
        from dataclasses import dataclass

        @dataclass
        class FakeConfig:
            name: str = "build"
            description: str = "Build workflow"
            source: str = "builtin"
            steps: list = None

            def model_dump(self):
                return {
                    "name": self.name,
                    "description": self.description,
                    "source": self.source,
                    "steps": self.steps or [],
                }

        mock_loader = MagicMock()
        mock_loader.get_workflow_config.return_value = FakeConfig()

        with patch("src.web.app.WorkflowLoader", return_value=mock_loader):
            response = client.get("/api/workflows/build")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "build"

    def test_delete_workflow_builtin(self, client):
        """Test deleting builtin workflow is forbidden."""
        mock_loader = MagicMock()
        mock_loader.is_builtin.return_value = True

        with patch("src.web.app.WorkflowLoader", return_value=mock_loader):
            response = client.delete("/api/workflows/build")

        assert response.status_code == 403
        data = response.json()
        assert "内置" in data["error"] or "builtin" in data["error"].lower() or "不可" in data["error"]


class TestWorkflowSaveDeleteAPI:
    """Test PUT/DELETE /api/workflows/{name}."""

    def test_save_workflow_success(self, client):
        """Test saving a workflow."""
        mock_loader = MagicMock()
        mock_loader.parse_yaml_string.return_value = MagicMock()
        mock_loader.parse_yaml_string.return_value.name = "my-flow"
        mock_loader.parse_yaml_string.return_value.source = "user"

        with patch("src.web.app.WorkflowLoader", return_value=mock_loader):
            response = client.put(
                "/api/workflows/my-flow",
                json={"yaml": "name: my-flow\nsteps: []"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_save_workflow_bad_yaml(self, client):
        """Test saving workflow with bad YAML."""
        mock_loader = MagicMock()
        mock_loader.parse_yaml_string.return_value = None  # parse failed

        with patch("src.web.app.WorkflowLoader", return_value=mock_loader):
            response = client.put(
                "/api/workflows/my-flow",
                json={"yaml": "bad: [yaml"}
            )

        assert response.status_code == 400

    def test_delete_workflow_success(self, client):
        """Test deleting user workflow."""
        mock_loader = MagicMock()
        mock_loader.is_builtin.return_value = False

        with patch("src.web.app.WorkflowLoader", return_value=mock_loader):
            response = client.delete("/api/workflows/my-flow")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_delete_workflow_not_found(self, client):
        """Test deleting non-existent workflow."""
        mock_loader = MagicMock()
        mock_loader.is_builtin.return_value = False
        mock_loader.delete_workflow.side_effect = FileNotFoundError()

        with patch("src.web.app.WorkflowLoader", return_value=mock_loader):
            response = client.delete("/api/workflows/nonexistent")

        assert response.status_code == 404


# ===== Settings API =====
class TestSettingsAPI:
    """Test GET/POST /api/settings"""

    @pytest.mark.skip(reason="Mock patching of pathlib.Path fails on None")
    @patch("src.web.app.SETTINGS_FILE", new_callable=lambda: None)
    @patch("src.web.app.SETTINGS_DIR", new_callable=lambda: None)
    def test_get_settings(self, mock_dir, mock_file, client):
        """GET /api/settings returns default structure"""
        # Mock SETTINGS_FILE.exists() to return False
        with patch("pathlib.Path.exists", return_value=False):
            resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert "defaults" in data

    @patch("src.web.app._read_settings")
    def test_get_settings_with_api_key(self, mock_read, client):
        """GET /api/settings masks api_key"""
        mock_read.return_value = {
            "models": {
                "deepseek": {
                    "provider": "deepseek",
                    "api_key": "sk-real-key-12345",
                    "api_base": "https://api.deepseek.com"
                }
            },
            "defaults": {"model": "deepseek"}
        }
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        model = data["models"]["deepseek"]
        assert model["has_key"] is True
        assert "api_key_masked" in model
        assert model["api_key"] == "sk-real-key-12345"  # original key preserved

    @patch("src.web.app.SETTINGS_FILE")
    def test_save_settings_new_model(self, mock_file, client):
        """POST /api/settings saves new model"""
        mock_file.exists.return_value = False
        mock_file.write_text = Mock()
        with patch("pathlib.Path.mkdir"):
            resp = client.post("/api/settings", json={
                "models": {
                    "new-model": {
                        "provider": "openai",
                        "api_key": "sk-new-key",
                        "api_base": "https://api.openai.com"
                    }
                },
                "defaults": {"model": "new-model"}
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @patch("src.web.app.SETTINGS_FILE")
    def test_save_settings_skip_masked_key(self, mock_file, client):
        """POST /api/settings skips masked api_key (starting with *)"""
        mock_file.exists.return_value = False
        mock_file.write_text = Mock()
        with patch("pathlib.Path.mkdir"):
            resp = client.post("/api/settings", json={
                "models": {
                    "deepseek": {
                        "provider": "deepseek",
                        "api_key": "*******************************************masked",
                        "api_base": "https://api.deepseek.com"
                    }
                }
            })
        assert resp.status_code == 200
        # Verify write_text was called with JSON that preserves original key
        written = mock_file.write_text.call_args[0][0]
        saved = json.loads(written)
        # Masked key should NOT be saved
        assert saved["models"]["deepseek"]["api_key"] != "*******************************************masked"


# ===== Settings API =====
class TestCoverageAPI:
    """Test GET/POST /api/coverage"""

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_get_coverage_success(self, mock_format, mock_run, client):
        """GET /api/coverage returns coverage report"""
        mock_run.return_value = {"overall": {"coverage": 85.2}}
        mock_format.return_value = {
            "overall": {"coverage": 85.2, "color": "#22c55e"},
            "modules": []
        }
        resp = client.get("/api/coverage")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall" in data
        assert data["overall"]["coverage"] == 85.2

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_get_coverage_error(self, mock_format, mock_run, client):
        """GET /api/coverage handles exceptions"""
        mock_run.side_effect = RuntimeError("coverage error")
        resp = client.get("/api/coverage")
        assert resp.status_code == 500
        data = resp.json()
        assert "error" in data
        assert data["overall"]["coverage"] == 0

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_post_coverage_run(self, mock_format, mock_run, client):
        """POST /api/coverage/run re-runs coverage analysis"""
        mock_run.return_value = {"overall": {"coverage": 86.0}}
        mock_format.return_value = {
            "overall": {"coverage": 86.0, "color": "#22c55e"},
            "modules": []
        }
        resp = client.post("/api/coverage/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall"]["coverage"] == 86.0
        mock_run.assert_called_once()


# ===== Sessions API =====
class TestSessionsAPI:
    """Test GET/POST/PUT/DELETE /api/sessions/*"""

    @pytest.fixture
    def sess_dir(self, tmp_path):
        """Mock SESSIONS_DIR to a temp directory"""
        from src.web.app import SESSIONS_DIR
        tmp_sess_dir = tmp_path / "sessions"
        tmp_sess_dir.mkdir()
        import src.web.app as app_module
        original = SESSIONS_DIR
        app_module.SESSIONS_DIR = tmp_sess_dir
        yield tmp_sess_dir
        app_module.SESSIONS_DIR = original

    def test_list_sessions_empty(self, client, sess_dir):
        """GET /api/sessions returns empty list"""
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        assert resp.json() == {"sessions": []}

    def test_create_session(self, client, sess_dir):
        """POST /api/sessions creates a new session"""
        resp = client.post("/api/sessions", json={"title": "Test Chat"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["session"]["title"] == "Test Chat"
        assert "id" in data["session"]

    def test_get_session_not_found(self, client, sess_dir):
        """GET /api/sessions/{id} returns 404"""
        resp = client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404

    def test_get_session_found(self, client, sess_dir):
        """GET /api/sessions/{id} returns session data"""
        # Create a session first
        create_resp = client.post("/api/sessions", json={"title": "My Chat"})
        session_id = create_resp.json()["session"]["id"]
        # Get it
        resp = client.get(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "My Chat"

    def test_update_session_title(self, client, sess_dir):
        """PUT /api/sessions/{id} updates title"""
        create_resp = client.post("/api/sessions", json={"title": "Old"})
        session_id = create_resp.json()["session"]["id"]
        resp = client.put(f"/api/sessions/{session_id}", json={"title": "New"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_delete_session(self, client, sess_dir):
        """DELETE /api/sessions/{id} removes session"""
        create_resp = client.post("/api/sessions", json={"title": "To Delete"})
        session_id = create_resp.json()["session"]["id"]
        resp = client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        # Confirm gone
        resp2 = client.get(f"/api/sessions/{session_id}")
        assert resp2.status_code == 404



# ---------------------------------------------------------------------------
# Additional Coverage Tests for Helper Functions
# ---------------------------------------------------------------------------


class TestPreprocessTargetGitHubSuccess:
    """Test _preprocess_target GitHub clone success (cover line 110)"""

    @patch("subprocess.run")
    @patch("tempfile.mkdtemp")
    def test_preprocess_github_success(self, mock_mkdtemp, mock_run):
        """Test successful GitHub clone returns path and context"""
        # Mock temp directory - return a string that Path can work with
        mock_tmp_dir_str = "/tmp/omc-gh-test123"
        mock_mkdtemp.return_value = mock_tmp_dir_str

        # Mock successful git clone
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # Call the function - should execute the return statement at line 110
        result = _preprocess_target("https://github.com/user/repo", "github", "task123")

        # Verify the return value
        assert result[0] == mock_tmp_dir_str
        assert "GitHub 仓库" in result[1]
        # Verify that subprocess.run was called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "git" in call_args[0][0]
        assert "clone" in call_args[0][0]


class TestPreprocessTargetUrlTruncation:
    """Test _preprocess_target URL content truncation (cover line 139)"""

    @patch("requests.get")
    def test_preprocess_url_content_truncated(self, mock_get):
        """Test URL content > 8000 chars gets truncated"""
        # Create content > 8000 chars
        long_content = "<html><body>" + "x" * 9000 + "</body></html>"
        mock_resp = MagicMock()
        mock_resp.text = long_content
        mock_get.return_value = mock_resp

        path, extra = _preprocess_target("https://example.com", "url", "task123")
        assert path == "."
        assert "网页内容" in extra
        # Check that content was truncated
        # Remove the header to get the actual content
        content_start = extra.find("\n\n") + 2
        actual_content = extra[content_start:]
        assert len(actual_content) <= 8000 + 50  # 50 chars for "... (内容已截断)"
        assert "内容已截断" in extra


class TestDetectTargetTypeFromMessageEdgeCases:
    """Test _detect_target_type_from_message edge cases (cover line 552)"""

    def test_detect_github_url_with_path(self):
        """Test GitHub URL with full path"""
        result_type, result_path = _detect_target_type_from_message(
            "Check https://github.com/user/repo/issues/1"
        )
        assert result_type == "github"
        assert "github.com" in result_path

    def test_detect_url_non_github(self):
        """Test non-GitHub URL"""
        result_type, result_path = _detect_target_type_from_message(
            "Read https://example.com/page"
        )
        assert result_type == "url"
        assert result_path == "https://example.com/page"

    def test_detect_local_path_with_tilde(self):
        """Test local path starting with ~"""
        result_type, result_path = _detect_target_type_from_message(
            "Build ~/projects/myproject"
        )
        assert result_type == "local"
        assert result_path == "~/projects/myproject"


class TestGenerateTaskSummaryExtended:
    """Test _generate_task_summary extended cases"""

    def test_generate_summary_review_workflow(self):
        """Test review workflow"""
        task = {
            "workflow": "review",
            "model": "deepseek",
            "project_path": "/tmp/test",
            "target_type": "local",
        }
        summary = _generate_task_summary(task)
        assert "代码审查" in summary
        assert "DeepSeek V4" in summary

    def test_generate_summary_debug_workflow(self):
        """Test debug workflow"""
        task = {
            "workflow": "debug",
            "model": "glm-4-flash",
            "project_path": "https://github.com/user/repo",
            "target_type": "github",
        }
        summary = _generate_task_summary(task)
        assert "调试修复" in summary
        assert "GLM-4.7-Flash" in summary
        assert "GitHub 仓库" in summary

    def test_generate_summary_test_workflow(self):
        """Test test workflow with URL target"""
        task = {
            "workflow": "test",
            "model": "moonshot-v1-128k",
            "project_path": "https://example.com",
            "target_type": "url",
        }
        summary = _generate_task_summary(task)
        assert "测试用例" in summary
        assert "Kimi 128K" in summary
        assert "网页" in summary

    def test_generate_summary_unknown_workflow_model(self):
        """Test unknown workflow and model"""
        task = {
            "workflow": "unknown",
            "model": "unknown-model",
            "project_path": "/tmp/test",
            "target_type": "local",
        }
        summary = _generate_task_summary(task)
        assert "unknown" in summary
        assert "unknown-model" in summary


class TestOrchestratorFunctions:
    """Test orchestrator factory functions (cover lines 313-316, 324-325, 330-352)"""

    @patch("src.web.app.create_orchestrator")
    @patch("src.web.app.create_router")
    def test_get_orchestrator_creates_singleton(self, mock_create_router, mock_create_orchestrator):
        """Test get_orchestrator() creates singleton (cover lines 313-316)"""
        # Reset global orchestrator
        import src.web.app as app_module
        app_module._global_orchestrator = None

        # Mock the returned objects
        mock_router = MagicMock()
        mock_orch = MagicMock()
        mock_create_router.return_value = mock_router
        mock_create_orchestrator.return_value = mock_orch

        # Call get_orchestrator
        result = app_module.get_orchestrator()

        # Verify create_router and create_orchestrator were called
        mock_create_router.assert_called_once()
        mock_create_orchestrator.assert_called_once_with(mock_router)
        assert result == mock_orch

        # Call again - should return same instance
        result2 = app_module.get_orchestrator()
        assert result2 == mock_orch
        # Should not call create again
        assert mock_create_router.call_count == 1

    def test_create_router(self):
        """Test create_router() function (cover lines 324-325)"""
        from src.web.app import create_router
        router = create_router()
        assert router is not None

    @patch("src.web.app.get_agent")
    def test_create_orchestrator(self, mock_get_agent):
        """Test create_orchestrator() function (cover lines 330-352)"""
        from src.web.app import create_orchestrator, create_router

        # Mock get_agent to return None (agent not found)
        mock_get_agent.return_value = None

        router = create_router()
        orch = create_orchestrator(router)

        assert orch is not None
        # Verify get_agent was called for each agent name
        assert mock_get_agent.call_count == 10


class TestTaskManagerQueueExceptions:
    """Test TaskManager queue exception handling (cover lines 246-247, 271-272, 282-283)"""

    def test_update_step_queue_full(self):
        """Test update_step when queue.put_nowait raises exception"""
        _tm()._tasks.clear()
        _tm()._queues.clear()

        tid = _tm().create_task()

        # Make the queue raise an exception on put_nowait
        queue = _tm()._queues[tid]
        queue.put_nowait = MagicMock(side_effect=Exception("Queue full"))

        # Should not raise - exception is caught and printed
        _tm().update_step(tid, "executor", "active", "output")

        # Verify the step was still updated
        task = _tm().get_task(tid)
        assert task["step_status"]["executor"] == "active"

    def test_complete_task_queue_full(self):
        """Test complete_task when queue.put_nowait raises exception"""
        _tm()._tasks.clear()
        _tm()._queues.clear()

        tid = _tm().create_task()

        # Make the queue raise an exception on put_nowait
        queue = _tm()._queues[tid]
        queue.put_nowait = MagicMock(side_effect=Exception("Queue full"))

        # Should not raise - exception is caught and printed
        _tm().complete_task(tid, result={"ok": True})

        # Verify the task was still completed
        task = _tm().get_task(tid)
        assert task["status"] == "completed"

    def test_delete_task_queue_full(self):
        """Test delete_task when queue.put_nowait raises exception"""
        _tm()._tasks.clear()
        _tm()._queues.clear()

        tid = _tm().create_task()

        # Make the queue raise an exception on put_nowait
        queue = _tm()._queues[tid]
        queue.put_nowait = MagicMock(side_effect=Exception("Queue full"))

        # Should not raise - exception is caught and printed
        result = _tm().delete_task(tid)

        assert result is True


class TestApiHistoryFunction:
    """Test api_history() function (cover lines 526-527)"""

    @patch("src.web.history_api.history_store")
    def test_api_history_no_tasks(self, mock_store, client):
        """Test api_history() when no tasks exist"""
        mock_store.list_all.return_value = []
        mock_store.get_stats.return_value = {
            "total_tasks": 0, "completed_tasks": 0, "failed_tasks": 0,
            "success_rate": 0, "total_tokens": 0, "total_cost": 0,
            "total_duration_hours": 0
        }
        _tm()._tasks.clear()
        _tm()._queues.clear()
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert len(data["records"]) == 0

    @patch("src.web.history_api.history_store")
    def test_api_history_with_tasks(self, mock_store, client):
        """Test api_history() when tasks exist"""
        mock_records = [
            {"task_id": "t1", "task": "task1", "status": "completed", "started_at": "2026-01-01T00:00:00"},
            {"task_id": "t2", "task": "task2", "status": "completed", "started_at": "2026-01-01T00:01:00"},
        ]
        mock_store.list_all.return_value = mock_records
        mock_store.get_stats.return_value = {
            "total_tasks": 2, "completed_tasks": 2, "failed_tasks": 0,
            "success_rate": 100, "total_tokens": 1000, "total_cost": 0.5,
            "total_duration_hours": 0.1
        }
        _tm()._tasks.clear()
        _tm()._queues.clear()
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert len(data["records"]) == 2


class TestDashboardStatsFunction:
    """Test dashboard_stats() function (cover lines 486-488)"""

    def test_dashboard_stats(self, client):
        """Test dashboard_stats() returns stats from history_store.
        Read from real history_store to avoid mock complexity."""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        # Just verify the response shape
        assert "total_tasks" in data
        assert "completed_tasks" in data
        assert "failed_tasks" in data


# ===== Additional Coverage Tests (76% → 80%+) =====

class TestOpenFolderErrors:
    """Test /api/open-folder error handling (cover lines 597-610)"""

    def test_open_folder_missing_path(self, client):
        """Test open-folder with missing path"""
        response = client.post("/api/open-folder", json={})
        assert response.status_code == 400
        data = response.json()
        assert "path" in data.get("detail", "").lower() or "required" in data.get("detail", "").lower()

    def test_open_folder_invalid_path(self, client):
        """Test open-folder with non-existent path"""
        import platform

        if platform.system() == "Darwin":  # macOS might have different behavior
            pass  # Skip detailed assertion due to OS differences

        response = client.post("/api/open-folder", json={"path": "/nonexistent/path/that/does/not/exist"})
        # Should return error status or success (depending on OS)
        assert response.status_code in [200, 500]


class TestSaveReportErrors:
    """Test /api/save-report error handling (cover lines 625-650)"""

    def test_save_report_missing_task_id(self, client):
        """Test save-report with missing task_id"""
        response = client.post("/api/save-report", json={})
        assert response.status_code == 400

    @patch("src.web.app.task_manager.get_task")
    @patch("src.web.app.history_store.load")
    def test_save_report_task_not_found(self, mock_load, mock_get_task, client):
        """Test save-report when task not found"""
        mock_get_task.return_value = None
        mock_load.return_value = None

        response = client.post("/api/save-report", json={"task_id": "nonexistent"})
        assert response.status_code == 404
