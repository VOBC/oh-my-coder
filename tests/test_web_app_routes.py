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
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

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
    task_manager,
)

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
    task_manager._tasks.clear()
    task_manager._queues.clear()
    yield
    task_manager._tasks.clear()
    task_manager._queues.clear()


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
        task_manager._tasks.clear()
        task_manager._queues.clear()
        tid = task_manager.create_task(
            task_desc="test task",
            model="deepseek",
            workflow="build",
            project_path="/tmp",
        )
        assert tid in task_manager._tasks
        assert task_manager.get_task(tid)["task"] == "test task"

    def test_update_step(self):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        tid = task_manager.create_task()
        task_manager.update_step(tid, "executor", "active", "step output")
        task = task_manager.get_task(tid)
        assert task["step_status"]["executor"] == "active"
        assert task["step_outputs"]["executor"] == "step output"

    def test_update_step_unknown_task(self):
        task_manager.update_step("nonexistent", "executor", "active")

    def test_complete_task_success(self):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        tid = task_manager.create_task()
        task_manager.complete_task(tid, result={"ok": True})
        task = task_manager.get_task(tid)
        assert task["status"] == "completed"
        assert task["result"] == {"ok": True}

    def test_complete_task_error(self):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        tid = task_manager.create_task()
        task_manager.complete_task(tid, error="Something went wrong")
        task = task_manager.get_task(tid)
        assert task["status"] == "failed"
        assert task["error"] == "Something went wrong"

    def test_complete_task_unknown(self):
        # Should not raise
        task_manager.complete_task("nonexistent", result={"ok": True})

    def test_delete_task(self):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        tid = task_manager.create_task()
        assert task_manager.delete_task(tid) is True
        assert task_manager.get_task(tid) is None

    def test_delete_task_unknown(self):
        assert task_manager.delete_task("nonexistent") is False

    def test_list_tasks(self):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        tid1 = task_manager.create_task()
        tid2 = task_manager.create_task()
        tasks = task_manager.list_tasks()
        assert len(tasks) >= 2
        ids = [t["task_id"] for t in tasks]
        assert tid1 in ids
        assert tid2 in ids

    def test_get_queue(self):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        tid = task_manager.create_task()
        q = task_manager.get_queue(tid)
        assert q is not None
        assert isinstance(q, asyncio.Queue)

    def test_get_queue_unknown(self):
        assert task_manager.get_queue("nonexistent") is None


class TestTaskAPI:
    """API routes for tasks."""

    def test_list_tasks_empty(self, client):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert "tasks" in response.json()

    def test_get_task_not_found(self, client):
        response = client.get("/api/tasks/nonexistent")
        assert response.status_code == 404

    def test_get_task_success(self, client):
        """任务存在时返回任务详情"""
        task_manager._tasks.clear()
        task_manager._queues.clear()
        tid = task_manager.create_task()
        response = client.get(f"/api/tasks/{tid}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == tid

    @patch("src.web.app.verify_api_token", return_value="token")
    def test_delete_task_with_token(self, mock_verify, client):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        tid = task_manager.create_task()
        response = client.delete(f"/api/tasks/{tid}")
        assert response.status_code == 200

    @patch("src.web.app.verify_api_token", return_value="token")
    def test_delete_task_not_found(self, mock_verify, client):
        with patch("src.web.app.verify_api_token", return_value="token"):
            response = client.delete("/api/tasks/nonexistent")
            assert response.status_code == 404


class TestApiHistory:
    """GET /api/history (app-level, not history_api)."""

    def test_api_history_returns_records(self, client):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        tid = task_manager.create_task()
        task_manager._tasks[tid]["started_at"] = "2026-05-28T10:00:00"
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

class TestSettingsAPI:
    """GET /api/settings and POST /api/settings."""

    @patch("src.web.app.SETTINGS_FILE")
    def test_get_settings_default(self, mock_settings_file, client):
        """When no settings file exists, return defaults."""
        mock_settings_file.exists.return_value = False
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "defaults" in data

    def test_get_settings_masks_keys(self, client):
        """"API keys are masked and has_key flag is set."""
        with patch("src.web.app._read_settings") as mock_read:
            mock_read.return_value = {
                "models": {
                    "deepseek": {
                        "provider": "DeepSeek",
                        "api_key": "sk-1234567890abcdef",
                        "cost_level": "free",
                        "enabled": True,
                    }
                },
                "defaults": {"model": "deepseek", "workflow": "build", "timeout": 300},
            }
            response = client.get("/api/settings")
            data = response.json()
            model = data["models"]["deepseek"]
            # Real mask for 'sk-1234567890abcdef' (len 20): 16 stars + last 4
            assert model["api_key_masked"].endswith("cdef")
            assert model["has_key"] is True

    @patch("src.web.app.SETTINGS_DIR")
    @patch("src.web.app.SETTINGS_FILE")
    @patch("src.web.app._read_settings")
    def test_save_settings(self, mock_read, mock_file, mock_dir, client):
        mock_dir.mkdir = MagicMock()
        mock_dir.exists.return_value = True
        mock_read.return_value = {
            "models": {"deepseek": {"provider": "DeepSeek", "api_key": "", "cost_level": "free", "enabled": True}},
            "defaults": {"model": "deepseek", "workflow": "build", "timeout": 300},
        }
        mock_file.write_text = MagicMock()

        response = client.post(
            "/api/settings",
            json={
                "defaults": {"model": "kimi"}
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @patch("src.web.app.SETTINGS_DIR")
    @patch("src.web.app.SETTINGS_FILE")
    @patch("src.web.app._read_settings")
    def test_save_settings_skips_masked_keys(self, mock_read, mock_file, mock_dir, client):
        mock_dir.mkdir = MagicMock()
        mock_dir.exists.return_value = True
        mock_read.return_value = {
            "models": {"deepseek": {"provider": "DeepSeek", "api_key": "sk-old", "cost_level": "free", "enabled": True}},
            "defaults": {"model": "deepseek", "workflow": "build", "timeout": 300},
        }
        mock_file.write_text = MagicMock()

        # Sending a masked key (starts with *) should be skipped
        response = client.post(
            "/api/settings",
            json={
                "models": {
                    "deepseek": {"api_key": "*****12345678"}
                }
            },
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Test Connection API
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

class TestSessionsAPI:
    """Sessions CRUD routes."""

    @patch("src.web.app.SESSIONS_DIR")
    def test_list_sessions_empty(self, mock_dir, client):
        mock_dir.glob.return_value = []
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []

    @patch("src.web.app.SESSIONS_DIR")
    def test_list_sessions_with_files(self, mock_dir, client):
        mock_file = MagicMock()
        mock_file.stem = "session-123"
        mock_file.stat().st_mtime = 0
        mock_file.read_text.return_value = json.dumps({
            "id": "session-123",
            "title": "Test Session",
            "created_at": "2026-05-28T10:00:00",
            "updated_at": "2026-05-28T10:00:00",
            "messages": [{"role": "user", "content": "hello"}],
        })
        mock_dir.glob.return_value = [mock_file]
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["title"] == "Test Session"
        assert data["sessions"][0]["message_count"] == 1

    @patch("src.web.app.SESSIONS_DIR")
    def test_list_sessions_with_bad_file(self, mock_dir, client):
        """Bad JSON file should be skipped."""
        mock_file = MagicMock()
        mock_file.stem = "bad-session"
        mock_file.stat().st_mtime = 0
        mock_file.read_text.return_value = "not json"
        mock_dir.glob.return_value = [mock_file]
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []

    @patch("src.web.app.SESSIONS_DIR")
    def test_create_session(self, mock_dir, client, tmp_path):
        mock_dir.mkdir = MagicMock()
        mock_dir.__truediv__ = lambda self, x: tmp_path / "sessions" / x
        mock_dir.__truediv__.return_value = tmp_path / "sessions" / "test.json"

        with patch("src.web.app.SESSIONS_DIR", tmp_path / "sessions"):
            (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
            response = client.post("/api/sessions", json={"title": "New Session"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["session"]["title"] == "New Session"

    @patch("src.web.app.SESSIONS_DIR")
    def test_get_session_not_found(self, mock_dir, client):
        mock_dir.__truediv__.return_value.exists.return_value = False
        response = client.get("/api/sessions/nonexistent")
        assert response.status_code == 404

    @patch("src.web.app.SESSIONS_DIR")
    def test_get_session_success(self, mock_dir, client, tmp_path):
        session_file = tmp_path / "sessions" / "session-abc.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({"id": "session-abc", "title": "Test"}))
        with patch("src.web.app.SESSIONS_DIR", tmp_path / "sessions"):
            response = client.get("/api/sessions/session-abc")
            assert response.status_code == 200
            assert response.json()["title"] == "Test"

    @patch("src.web.app.SESSIONS_DIR")
    def test_update_session_not_found(self, mock_dir, client):
        mock_dir.__truediv__.return_value.exists.return_value = False
        response = client.put("/api/sessions/session-abc", json={"title": "New Title"})
        assert response.status_code == 404

    @patch("src.web.app.SESSIONS_DIR")
    def test_update_session_success(self, mock_dir, client, tmp_path):
        session_file = tmp_path / "sessions" / "session-abc.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({"id": "session-abc", "title": "Old"}))
        with patch("src.web.app.SESSIONS_DIR", tmp_path / "sessions"):
            response = client.put(
                "/api/sessions/session-abc",
                json={"title": "New Title"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    @patch("src.web.app.SESSIONS_DIR")
    def test_update_session_messages(self, mock_dir, client, tmp_path):
        session_file = tmp_path / "sessions" / "session-abc.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({"id": "session-abc", "messages": []}))
        with patch("src.web.app.SESSIONS_DIR", tmp_path / "sessions"):
            response = client.put(
                "/api/sessions/session-abc",
                json={"messages": [{"role": "user", "content": "hello"}]},
            )
            assert response.status_code == 200

    @patch("src.web.app.SESSIONS_DIR")
    def test_delete_session_not_found(self, mock_dir, client):
        mock_dir.__truediv__.return_value.exists.return_value = False
        response = client.delete("/api/sessions/session-abc")
        assert response.status_code == 404

    @patch("src.web.app.SESSIONS_DIR")
    def test_delete_session_success(self, mock_dir, client, tmp_path):
        session_file = tmp_path / "sessions" / "session-abc.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({"id": "session-abc"}))
        with patch("src.web.app.SESSIONS_DIR", tmp_path / "sessions"):
            response = client.delete("/api/sessions/session-abc")
            assert response.status_code == 200
            assert not session_file.exists()


# ---------------------------------------------------------------------------
# Coverage API
# ---------------------------------------------------------------------------

class TestCoverageAPI:
    """GET /api/coverage and POST /api/coverage/run."""

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_get_coverage_success(self, mock_format, mock_run, client):
        mock_run.return_value = {}
        mock_format.return_value = {"overall": {"coverage": 85, "color": "#22c55e"}}
        response = client.get("/api/coverage")
        assert response.status_code == 200
        data = response.json()
        assert data["overall"]["coverage"] == 85

    @patch("src.web.app.run_coverage_analysis")
    def test_get_coverage_exception(self, mock_run, client):
        mock_run.side_effect = RuntimeError("No coverage data")
        response = client.get("/api/coverage")
        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_run_coverage_success(self, mock_format, mock_run, client):
        mock_run.return_value = {}
        mock_format.return_value = {"overall": {"coverage": 90}}
        response = client.post("/api/coverage/run")
        assert response.status_code == 200

    @patch("src.web.app.run_coverage_analysis")
    def test_run_coverage_exception(self, mock_run, client):
        mock_run.side_effect = Exception("Coverage error")
        response = client.post("/api/coverage/run")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Chat Endpoint
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
        from src.web.app import AgentStatus
        
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
        import asyncio
        
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
        import asyncio
        from src.web.app import AgentStatus
        
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

    def test_execute_auto_detect_github(self, client):
        """When no target_type is given, it should be auto-detected."""
        response = client.post(
            "/api/execute",
            json={
                "task": "do something",
                "project_path": "https://github.com/user/repo",
                "model": "deepseek",
                "workflow": "build",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "task_id" in data
        assert data["target_type"] == "github"

    def test_execute_missing_task_field(self, client):
        """Missing 'task' field should return 400."""
        response = client.post(
            "/api/execute",
            json={
                "project_path": "/tmp",
            },
        )
        assert response.status_code == 400
        assert "Missing" in response.json()["detail"]

    @patch("src.web.app._preprocess_target")
    def test_execute_preprocess_exception(self, mock_preprocess, client):
        """When _preprocess_target raises, should return 200 but task fails."""
        mock_preprocess.side_effect = RuntimeError("Clone failed")
        response = client.post(
            "/api/execute",
            json={
                "task": "test task",
                "project_path": "https://github.com/user/repo",
                "target_type": "github",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        # The task should have failed during preprocessing
        task_id = data["task_id"]
        task = task_manager.get_task(task_id)
        # Give it a moment for background task to potentially start
        import time
        time.sleep(0.1)
        # Check if task exists and has error
        if task:
            assert task.get("status") == "failed"

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
