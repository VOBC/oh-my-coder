"""
Tests for src/web/app.py synchronous endpoints.

Covers: execute_task_sync, chat_completion, settings,
         session CRUD, api_history, dashboard_stats.

Correct API paths (from reading app.py source):
- POST /api/execute-sync  (not /api/execute)
- POST /api/chat/completions  (not /v1/chat/completions)
- GET/POST /api/settings
- GET/POST /api/sessions  (plural, not /api/session)
- GET/PUT/DELETE /api/sessions/{id}
- GET /api/history  (note: endpoint is /api/history)
- GET /api/dashboard/stats
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web.app import (
    app,
    task_manager,
)

client = TestClient(app)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_state(tmp_path):
    """Use tmp_path for SESSIONS_DIR, reset task_manager."""
    task_manager._tasks.clear()
    task_manager._queues.clear()
    # Patch SESSIONS_DIR to a temp dir
    temp_sessions = tmp_path / "sessions"
    temp_sessions.mkdir(parents=True, exist_ok=True)
    with patch("src.web.app.SESSIONS_DIR", temp_sessions):
        yield temp_sessions
    task_manager._tasks.clear()
    task_manager._queues.clear()


# =============================================================================
# execute_task_sync  (POST /api/execute-sync)
# =============================================================================

class TestExecuteTaskSync:
    @patch("src.web.app.create_router")
    @patch("src.web.app.create_orchestrator")
    def test_execute_success(self, mock_create_orch, mock_create_router, reset_state):
        # Mock orchestrator + router
        orch = AsyncMock()
        mock_create_orch.return_value = orch

        # Mock agent execution result
        from src.agents.base import AgentOutput, AgentStatus

        async def fake_execute(ctx):
            return AgentOutput(
                agent_name="planner",
                status=AgentStatus.COMPLETED,
                result="done",
                usage={},
            )

        orch.get_agent = MagicMock(return_value=MagicMock(execute=fake_execute))

        payload = {"task": "list files", "workflow": "build", "project_path": "/tmp"}
        resp = client.post("/api/execute-sync", json=payload)
        # Returns 200 with status=success
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_execute_missing_task(self, reset_state):
        resp = client.post("/api/execute-sync", json={})
        # FastAPI validation error = 422, or app returns 400
        assert resp.status_code in (400, 422)

    @patch("src.web.app.create_orchestrator")
    def test_execute_orchestrator_error(self, mock_create_orch, reset_state):
        orch = AsyncMock()
        orch.get_agent = MagicMock(side_effect=Exception("boom"))
        mock_create_orch.return_value = orch

        payload = {"task": "fail", "workflow": "build", "project_path": "/tmp"}
        resp = client.post("/api/execute-sync", json=payload)
        # Returns 200 with status=error (app catches exception)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"


# =============================================================================
# chat_completion_endpoint  (POST /api/chat/completions)
# =============================================================================

class TestChatCompletion:
    @patch("src.web.app.create_router")
    def test_non_streaming(self, mock_create_router, reset_state):
        router = MagicMock()
        from src.models.base import ModelResponse

        async def fake_route(*args, **kwargs):
            return ModelResponse(
                content="hello",
                model=kwargs.get("override_model", "test"),
                usage=MagicMock(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

        router.route_and_call = fake_route
        mock_create_router.return_value = router

        resp = client.post(
            "/api/chat/completions",
            json={
                "model": "test",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data

    @patch("src.web.app.create_router")
    def test_streaming(self, mock_create_router, reset_state):
        """Streaming branch returns StreamingResponse (200)."""
        router = MagicMock()

        async def fake_route(*args, **kwargs):
            from src.models.base import ModelResponse

            return ModelResponse(
                content="hello",
                model="test",
                usage=MagicMock(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

        router.route_and_call = fake_route
        mock_create_router.return_value = router

        resp = client.post(
            "/api/chat/completions",
            json={
                "model": "test",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        )
        # StreamingResponse returns 200
        assert resp.status_code == 200


# =============================================================================
# Settings API  (GET/POST /api/settings)
# =============================================================================

class TestSettingsAPI:
    @patch("src.web.app.SETTINGS_FILE")
    @patch("src.web.app._read_settings")
    def test_get_settings(self, mock_read, mock_file, reset_state):
        mock_file.exists.return_value = True
        mock_read.return_value = {"default_model": "qwen", "temperature": 0.7}

        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "default_model" in data

    @patch("src.web.app.SETTINGS_DIR")
    @patch("src.web.app.SETTINGS_FILE")
    @patch("src.web.app._read_settings")
    def test_save_settings(self, mock_read, mock_file, mock_dir, reset_state):
        mock_dir.exists.return_value = True
        mock_dir.mkdir = MagicMock()
        mock_read.return_value = {}
        mock_file.write_text = MagicMock()

        resp = client.post(
            "/api/settings",
            json={"default_model": "deepseek", "temperature": 0.3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# =============================================================================
# Session API  (CRUD at /api/sessions)
# =============================================================================

class TestSessionAPI:
    def test_create_session(self, reset_state):
        temp_sessions = reset_state
        with patch("src.web.app.SESSIONS_DIR", temp_sessions):
            payload = {"title": "New Chat"}
            resp = client.post("/api/sessions", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert "session" in data
            assert "id" in data["session"]

    def test_get_session(self, reset_state):
        temp_sessions = reset_state
        with patch("src.web.app.SESSIONS_DIR", temp_sessions):
            # Create a session file first
            import json

            sid = "test-session-123"
            session_data = {
                "id": sid,
                "title": "Test",
                "messages": [],
                "created_at": "2026-05-30T10:00:00",
                "updated_at": "2026-05-30T10:00:00",
            }
            (temp_sessions / f"{sid}.json").write_text(
                json.dumps(session_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            resp = client.get(f"/api/sessions/{sid}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == sid

    def test_update_session(self, reset_state):
        temp_sessions = reset_state
        with patch("src.web.app.SESSIONS_DIR", temp_sessions):
            import json

            sid = "test-session-456"
            session_data = {
                "id": sid,
                "title": "Old",
                "messages": [],
                "created_at": "2026-05-30T10:00:00",
                "updated_at": "2026-05-30T10:00:00",
            }
            (temp_sessions / f"{sid}.json").write_text(
                json.dumps(session_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            resp = client.put(f"/api/sessions/{sid}", json={"title": "Updated"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"

    def test_delete_session(self, reset_state):
        temp_sessions = reset_state
        with patch("src.web.app.SESSIONS_DIR", temp_sessions):
            import json

            sid = "test-session-789"
            session_data = {
                "id": sid,
                "title": "ToDelete",
                "messages": [],
                "created_at": "2026-05-30T10:00:00",
                "updated_at": "2026-05-30T10:00:00",
            }
            (temp_sessions / f"{sid}.json").write_text(
                json.dumps(session_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            resp = client.delete(f"/api/sessions/{sid}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"


# =============================================================================
# api_history  (GET /api/history)
# dashboard_stats  (GET /api/dashboard/stats)
# =============================================================================

class TestHistoryAndDashboard:
    @patch("src.web.app.history_store")
    def test_api_history(self, mock_store, reset_state):
        mock_store.list_all.return_value = [
            {"task_id": "t1", "task": "do something", "status": "completed"}
        ]
        resp = client.get("/api/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data

    @patch("src.web.app.history_store")
    def test_api_history_with_limit(self, mock_store, reset_state):
        mock_store.list_all.return_value = []
        resp = client.get("/api/history?limit=5")
        assert resp.status_code == 200

    @patch("src.web.app.history_store")
    def test_dashboard_stats(self, mock_store, reset_state):
        mock_store.get_stats.return_value = {
            "total_tasks": 10,
            "completed": 7,
            "running": 1,
            "failed": 2,
        }
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tasks" in data


# =============================================================================
# Health / Ready
# =============================================================================

class TestHealthChecks:
    def test_health_check(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_ready_check(self):
        # /ready endpoint does not exist in app.py (returns 404)
        # This documents the current state - no /ready route is registered
        resp = client.get("/ready")
        assert resp.status_code == 404  # Not implemented (yet)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
