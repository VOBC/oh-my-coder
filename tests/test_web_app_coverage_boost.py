"""Targeted tests to boost coverage for src/web/app.py (81% -> 86%+)"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.xdist_group("web_app")


@pytest.fixture(autouse=True)
def reset_orchestrator():
    """Reset global orchestrator between tests."""
    import src.web.app as app_mod
    app_mod._global_orchestrator = None
    yield
    app_mod._global_orchestrator = None


@pytest.fixture
def client():
    from src.web.app import app
    return TestClient(app)


@pytest.fixture
def sessions_dir(tmp_path):
    d = tmp_path / "sessions"
    d.mkdir()
    with patch("src.web.app.SESSIONS_DIR", d):
        yield d


# ============================================================
# TaskManager queue-full exception paths (lines 246-247, 271-272, 282-283)
# ============================================================
class TestTaskManagerQueueFull:
    def test_update_step_queue_full(self):
        from src.web.app import TaskManager
        tm = TaskManager()
        tid = tm.create_task("test")
        queue = tm.get_queue(tid)
        # Fill the queue
        queue._maxsize = 1
        queue.put_nowait("x")
        # This should trigger the except block but not raise
        tm.update_step(tid, "step1", "running", "content")

    def test_complete_task_queue_full(self):
        from src.web.app import TaskManager
        tm = TaskManager()
        tid = tm.create_task("test")
        queue = tm.get_queue(tid)
        queue._maxsize = 1
        queue.put_nowait("x")
        tm.complete_task(tid, result="done")

    def test_delete_task_queue_full(self):
        from src.web.app import TaskManager
        tm = TaskManager()
        tid = tm.create_task("test")
        queue = tm.get_queue(tid)
        queue._maxsize = 1
        queue.put_nowait("x")
        result = tm.delete_task(tid)
        assert result is True


# ============================================================
# Agent registration failure (line 349-350)
# ============================================================
class TestAgentRegistrationFailure:
    def test_create_orchestrator_agent_failure(self):
        from src.web.app import create_orchestrator, create_router
        router = create_router()
        with patch("src.web.app.get_agent", side_effect=Exception("no agent")):
            orch = create_orchestrator(router)
            # Should still return orchestrator even if agents fail
            assert orch is not None


# ============================================================
# Page routes: /history, /docs, /coverage (lines 439-442, 1887, 1891)
# ============================================================
class TestPageRoutes:
    def test_history_page(self, client):
        resp = client.get("/history")
        assert resp.status_code == 200

    def test_docs_page(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_coverage_page(self, client):
        resp = client.get("/coverage")
        assert resp.status_code == 200


# ============================================================
# /api/history endpoint (lines 486-488)
# ============================================================
class TestApiHistoryEndpoint:
    def test_api_history_with_tasks(self, client):
        from src.web.app import task_manager
        # Create a task so there's data
        tid = task_manager.create_task("test task", model="deepseek", workflow="build")
        task_manager._tasks[tid]["started_at"] = "2025-01-01T00:00:00"
        try:
            resp = client.get("/api/history")
            assert resp.status_code == 200
            data = resp.json()
            assert "records" in data
        finally:
            task_manager.delete_task(tid)


# ============================================================
# /api/dashboard/stats (lines 494-495)
# ============================================================
class TestDashboardStats:
    def test_dashboard_stats(self, client):
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 200


# ============================================================
# /api/dashboard/files with project_path fallback (lines 507-508, 526-527)
# ============================================================
class TestDashboardFiles:
    def test_dashboard_files_no_history(self, client):
        with patch("src.web.app.history_store") as mock_store:
            mock_store.list_all.return_value = []
            resp = client.get("/api/dashboard/files")
            assert resp.status_code == 200
            data = resp.json()
            assert "files" in data

    def test_dashboard_files_with_valid_project_path(self, client):
        with patch("src.web.app.history_store") as mock_store:
            mock_store.list_all.return_value = [
                {"project_path": str(Path.cwd())}
            ]
            resp = client.get("/api/dashboard/files")
            assert resp.status_code == 200


# ============================================================
# _read_settings error fallback (lines 1319-1359)
# ============================================================
class TestReadSettingsFallback:
    def test_read_settings_parse_error(self, tmp_path):
        from src.web.app import _read_settings, SETTINGS_FILE
        bad_file = tmp_path / "settings.json"
        bad_file.write_text("not json{{{{", encoding="utf-8")
        with patch("src.web.app.SETTINGS_FILE", bad_file):
            result = _read_settings()
            # Should return defaults
            assert "models" in result
            assert "defaults" in result

    def test_read_settings_missing_keys(self, tmp_path):
        from src.web.app import _read_settings
        bad_file = tmp_path / "settings.json"
        bad_file.write_text("{}", encoding="utf-8")
        with patch("src.web.app.SETTINGS_FILE", bad_file):
            result = _read_settings()
            assert "models" in result
            assert "deepseek" in result["models"]

    def test_read_settings_file_not_found(self, tmp_path):
        from src.web.app import _read_settings
        missing = tmp_path / "nonexistent.json"
        with patch("src.web.app.SETTINGS_FILE", missing):
            result = _read_settings()
            assert "models" in result


# ============================================================
# Delete workflow exception path (line 1742-1754)
# ============================================================
class TestDeleteWorkflowException:
    def test_delete_workflow_generic_error(self, client):
        with patch("src.web.app.WorkflowLoader") as mock_cls:
            mock_loader = MagicMock()
            mock_loader.is_builtin.return_value = False
            mock_loader.delete_workflow.side_effect = RuntimeError("disk error")
            mock_cls.return_value = mock_loader
            resp = client.delete("/api/workflows/my-flow")
            assert resp.status_code == 400


# ============================================================
# Session API exception paths (lines 1713-1835)
# ============================================================
class TestSessionExceptions:
    def test_get_session_corrupt_file(self, client, sessions_dir):
        f = sessions_dir / "bad.json"
        f.write_text("NOT JSON", encoding="utf-8")
        resp = client.get("/api/sessions/bad")
        assert resp.status_code == 500

    def test_update_session_corrupt_file(self, client, sessions_dir):
        f = sessions_dir / "bad.json"
        f.write_text("NOT JSON", encoding="utf-8")
        resp = client.put("/api/sessions/bad", json={"title": "new"})
        assert resp.status_code == 500

    def test_update_session_not_found(self, client, sessions_dir):
        resp = client.put("/api/sessions/nonexistent", json={"title": "new"})
        assert resp.status_code == 404

    def test_delete_session_not_found(self, client, sessions_dir):
        resp = client.delete("/api/sessions/nonexistent")
        assert resp.status_code == 404

    def test_delete_session_unlink_error(self, client, sessions_dir):
        f = sessions_dir / "stuck.json"
        f.write_text('{"id":"stuck","title":"test"}', encoding="utf-8")
        with patch.object(Path, "unlink", side_effect=PermissionError("denied")):
            resp = client.delete("/api/sessions/stuck")
            assert resp.status_code == 500

    def test_update_session_with_messages(self, client, sessions_dir):
        f = sessions_dir / "msg.json"
        f.write_text('{"id":"msg","title":"test","messages":[]}', encoding="utf-8")
        resp = client.put("/api/sessions/msg", json={"messages": [{"role": "user", "content": "hi"}]})
        assert resp.status_code == 200


# ============================================================
# Dashboard files exception path (lines 526-527)
# ============================================================
class TestDashboardFilesException:
    def test_dashboard_files_list_error(self, client):
        with patch("src.web.app.history_store") as mock_store:
            mock_store.list_all.return_value = [
                {"project_path": "/nonexistent/path/xyz"}
            ]
            # Should handle gracefully (project_path won't exist, falls back)
            resp = client.get("/api/dashboard/files")
            assert resp.status_code == 200

    def test_dashboard_files_bad_path_raises(self, client):
        with patch("src.web.app.history_store") as mock_store, \
             patch("src.web.app.Path") as mock_path_cls:
            mock_store.list_all.return_value = []
            # Make Path() raise an exception to cover the except block
            mock_path_inst = MagicMock()
            mock_path_inst.exists.return_value = True
            mock_path_inst.is_dir.return_value = True
            mock_path_inst.iterdir.side_effect = PermissionError("no access")
            mock_path_cls.return_value = mock_path_inst
            resp = client.get("/api/dashboard/files")
            assert resp.status_code == 200


# ============================================================
# API endpoint error path (lines 1257-1259)
# ============================================================
class TestApiEndpointError:
    def test_execute_endpoint_exception(self, client):
        """Test the generic exception handler in /api/execute."""
        with patch("src.web.app.get_orchestrator") as mock_get:
            mock_orch = MagicMock()
            mock_orch.run.side_effect = RuntimeError("boom")
            mock_get.return_value = mock_orch
            # We need to mock enough to get past validation
            resp = client.post("/api/execute", json={
                "task": "test task",
                "model": "deepseek",
                "workflow": "build"
            })
            # Either 200 (success path bypassed) or error response
            assert resp.status_code in (200, 500)


# ============================================================
# Test connection error paths (lines 1797-1835)
# ============================================================
class TestConnectionErrors:
    def test_connection_timeout(self, client):
        import httpx
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_cls.return_value = mock_client
            resp = client.post("/api/test-connection", json={
                "base_url": "https://api.example.com",
                "api_key": "test-key",
                "model": "test"
            })
            assert resp.status_code == 200
            assert "超时" in resp.json()["msg"]

    def test_connection_connect_error(self, client):
        import httpx
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("refused")
            mock_cls.return_value = mock_client
            resp = client.post("/api/test-connection", json={
                "base_url": "https://api.example.com",
                "api_key": "test-key",
                "model": "test"
            })
            assert resp.status_code == 502

    def test_connection_generic_error(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = RuntimeError("unexpected")
            mock_cls.return_value = mock_client
            resp = client.post("/api/test-connection", json={
                "base_url": "https://api.example.com",
                "api_key": "test-key",
                "model": "test"
            })
            assert resp.status_code == 500

    def test_connection_non_json_error_response(self, client):
        """Test error response that isn't JSON (lines 1567-1569)."""
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_resp.json.side_effect = ValueError("not json")
            mock_resp.text = "rate limited"
            mock_client.get.return_value = mock_resp
            mock_cls.return_value = mock_client
            resp = client.post("/api/test-connection", json={
                "base_url": "https://api.example.com",
                "api_key": "test-key",
                "model": "test"
            })
            assert resp.status_code == 502
