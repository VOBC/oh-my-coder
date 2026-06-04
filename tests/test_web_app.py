"""Tests for src.web.app - Session API endpoints."""
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.xdist_group("web_app")


@pytest.fixture
def client(tmp_path):
    import src.web.app as app_mod
    old_dir = app_mod.SESSIONS_DIR
    app_mod.SESSIONS_DIR = tmp_path
    app_mod._global_orchestrator = None
    from src.web.app import app
    yield TestClient(app)
    app_mod.SESSIONS_DIR = old_dir


class TestListSessions:
    def test_list_sessions_empty(self, client):
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        assert resp.json()["sessions"] == []

    def test_list_sessions_with_data(self, client, tmp_path):
        """Sessions dir already has JSON files."""
        session_file = tmp_path / "abc123.json"
        session_file.write_text(json.dumps({
            "id": "abc123",
            "title": "Test Session",
            "messages": [{"role": "user", "content": "hi"}],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }), encoding="utf-8")
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        sessions = resp.json()["sessions"]
        assert len(sessions) >= 1

    def test_list_sessions_corrupted_file(self, client, tmp_path):
        """Corrupted JSON is skipped gracefully."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json{{{", encoding="utf-8")
        resp = client.get("/api/sessions")
        assert resp.status_code == 200  # no crash


class TestCreateSession:
    def test_create_session_default_title(self, client):
        resp = client.post("/api/sessions", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["session"]["title"] == "新会话"
        assert "id" in data["session"]

    def test_create_session_custom_title(self, client):
        resp = client.post("/api/sessions", json={"title": "My Chat"})
        assert resp.status_code == 200
        assert resp.json()["session"]["title"] == "My Chat"


class TestGetSession:
    def test_get_session_not_found(self, client):
        resp = client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404

    def test_get_session_success(self, client):
        """Create and retrieve a session."""
        create_resp = client.post("/api/sessions", json={"title": "Get Test"})
        session_id = create_resp.json()["session"]["id"]
        resp = client.get(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Get Test"


class TestUpdateSession:
    def test_update_session_not_found(self, client):
        resp = client.put("/api/sessions/nonexistent", json={"title": "New"})
        assert resp.status_code == 404

    def test_update_session_title(self, client):
        create_resp = client.post("/api/sessions", json={"title": "Old"})
        session_id = create_resp.json()["session"]["id"]
        resp = client.put(f"/api/sessions/{session_id}", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_update_session_messages(self, client):
        create_resp = client.post("/api/sessions", json={"title": "Msg Test"})
        session_id = create_resp.json()["session"]["id"]
        msgs = [{"role": "user", "content": "hello"}]
        resp = client.put(f"/api/sessions/{session_id}", json={"messages": msgs})
        assert resp.status_code == 200


class TestDeleteSession:
    def test_delete_session_not_found(self, client):
        resp = client.delete("/api/sessions/nonexistent")
        assert resp.status_code == 404

    def test_delete_session_success(self, client):
        create_resp = client.post("/api/sessions", json={"title": "Delete Me"})
        session_id = create_resp.json()["session"]["id"]
        resp = client.delete(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        # Confirm gone
        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 404


class TestCoverageEndpoint:
    """Coverage endpoints need mocking (run_coverage_analysis calls pytest recursively)."""

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_get_coverage_success(self, mock_format, mock_run, client):
        mock_run.return_value = {"overall": {"coverage": 85.0}}
        mock_format.return_value = {
            "overall": {"coverage": 85.0, "color": "#22c55e"},
            "modules": []
        }
        resp = client.get("/api/coverage")
        assert resp.status_code == 200
        assert resp.json()["overall"]["coverage"] == 85.0

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_run_coverage_success(self, mock_format, mock_run, client):
        mock_run.return_value = {"overall": {"coverage": 86.0}}
        mock_format.return_value = {
            "overall": {"coverage": 86.0, "color": "#22c55e"},
            "modules": []
        }
        resp = client.post("/api/coverage/run")
        assert resp.status_code == 200

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_get_coverage_error(self, mock_format, mock_run, client):
        mock_run.side_effect = RuntimeError("coverage error")
        mock_format.return_value = {"overall": {"coverage": 0, "color": "#ef4444"}, "modules": []}
        resp = client.get("/api/coverage")
        assert resp.status_code == 500
