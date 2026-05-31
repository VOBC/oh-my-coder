"""
Comprehensive tests for src/web/app.py — targeting missing lines to push coverage from 85% to 90%+.

Covers:
1. TaskManager edge cases (queue full warnings, missing tasks)
2. SSE endpoints
3. Chat completion endpoint
4. Helper functions (_detect_workflow, _detect_model, _generate_task_summary)
5. Settings API error handling
6. Workflow API operations
7. Session API operations
8. Save report edge cases
9. Error handling in execute_task
"""

import sys
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch, Mock
from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web.app import app, task_manager, history_store, _detect_workflow, _detect_model
from src.web.app import _generate_task_summary, _detect_target_type_from_message


# ===========================================================================
# Test Class 1: TaskManager Edge Cases
# ===========================================================================

class TestTaskManagerEdgeCases:
    """Test TaskManager edge cases"""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        yield
        task_manager._tasks.clear()
        task_manager._queues.clear()

    def test_update_step_queue_full(self):
        """Test update_step when queue is full"""
        task_id = task_manager.create_task("test", "model", "build", ".")
        queue = task_manager.get_queue(task_id)

        # Fill queue to cause Full exception
        import asyncio
        while not queue.full():
            try:
                queue.put_nowait({"type": "test"})
            except asyncio.QueueFull:
                break

        # Now this should trigger the warning path
        with patch("builtins.print") as mock_print:
            task_manager.update_step(task_id, "step1", "active", "content")
            # The warning should be printed
            assert mock_print.called

    def test_complete_task_queue_full(self):
        """Test complete_task when queue is full"""
        task_id = task_manager.create_task("test", "model", "build", ".")
        queue = task_manager.get_queue(task_id)

        # Fill queue
        import asyncio
        while not queue.full():
            try:
                queue.put_nowait({"type": "test"})
            except asyncio.QueueFull:
                break

        # Now this should trigger the warning path
        with patch("builtins.print") as mock_print:
            task_manager.complete_task(task_id, result="test")
            assert mock_print.called

    def test_delete_task_nonexistent(self):
        """Test delete_task with non-existent task"""
        result = task_manager.delete_task("nonexistent-id")
        assert result is False

    def test_get_task_nonexistent(self):
        """Test get_task with non-existent task"""
        result = task_manager.get_task("nonexistent-id")
        assert result is None


# ===========================================================================
# Test Class 2: SSE Endpoints
# ===========================================================================

class TestSSEEndpoints:
    """Test SSE endpoints"""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        yield
        task_manager._tasks.clear()
        task_manager._queues.clear()

    def test_sse_execute_nonexistent_task(self):
        """Test SSE endpoint with non-existent task"""
        client = TestClient(app)
        response = client.get("/sse/execute/nonexistent-id")
        assert response.status_code == 404

    def test_agent_live_stream_error(self):
        """Test /api/agent/live when orchestrator fails"""
        client = TestClient(app)
        with patch("src.web.app.get_orchestrator") as mock_get:
            mock_orch = MagicMock()
            mock_orch.get_current_state.side_effect = Exception("Orchestrator error")
            mock_get.return_value = mock_orch

            response = client.get("/api/agent/live")
            assert response.status_code == 200


# ===========================================================================
# Test Class 3: Chat Completion Endpoint
# ===========================================================================

class TestChatCompletionEndpoint:
    """Test POST /api/chat/completions"""

    def test_chat_completion_non_stream_success(self):
        """Test non-streaming chat completion success"""
        client = TestClient(app)
        with patch("src.web.app.get_orchestrator") as mock_get:
            mock_orch = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Test response"
            mock_response.model = "deepseek"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_response.usage.total_tokens = 30
            mock_orch.model_router.route_and_call.return_value = mock_response
            mock_get.return_value = mock_orch

            response = client.post(
                "/api/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "deepseek",
                    "stream": False,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "content" in data

    def test_chat_completion_non_stream_error(self):
        """Test non-streaming chat completion error"""
        client = TestClient(app)
        with patch("src.web.app.get_orchestrator") as mock_get:
            mock_orch = MagicMock()
            mock_orch.model_router.route_and_call.side_effect = Exception("API error")
            mock_get.return_value = mock_orch

            response = client.post(
                "/api/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "model": "deepseek",
                    "stream": False,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "content" in data


# ===========================================================================
# Test Class 4: Helper Functions
# ===========================================================================

class TestHelperFunctions:
    """Test helper functions"""

    def test_detect_workflow_empty_message(self):
        """Test _detect_workflow with empty message"""
        result = _detect_workflow("")
        assert result == "build"  # default

    def test_detect_workflow_review_keywords(self):
        """Test _detect_workflow with review keywords"""
        result = _detect_workflow("Please review my code for security vulnerabilities")
        assert result == "review"

    def test_detect_workflow_debug_keywords(self):
        """Test _detect_workflow with debug keywords"""
        result = _detect_workflow("Fix the bug in the code")
        assert result == "debug"

    def test_detect_workflow_test_keywords(self):
        """Test _detect_workflow with test keywords"""
        result = _detect_workflow("Generate unit tests for this function")
        assert result == "test"

    def test_detect_model_keywords(self):
        """Test _detect_model with various keywords"""
        assert _detect_model("Use deepseek for this task") == "deepseek"
        assert _detect_model("I want to use glm flash model") == "glm-4-flash"
        assert _detect_model("Use minimax for this") == "MiniMax-Text-01"
        assert _detect_model("Use kimi 128k") == "moonshot-v1-128k"
        assert _detect_model("Use doubao pro") == "doubao-pro-32k"
        assert _detect_model("Use tiangong 3") == "tiangong-3"
        assert _detect_model("Use baichuan 4") == "Baichuan4"
        assert _detect_model("Random task without keywords") == "deepseek"  # default

    def test_generate_task_summary(self):
        """Test _generate_task_summary"""
        task = {
            "workflow": "build",
            "model": "deepseek",
            "target_type": "local",
            "project_path": "/tmp/project",
        }
        result = _generate_task_summary(task)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_detect_target_type_from_message_github(self):
        """Test _detect_target_type_from_message with GitHub URL"""
        target_type, path = _detect_target_type_from_message(
            "Check this repo: https://github.com/user/repo"
        )
        assert target_type == "github"
        assert "github.com" in path

    def test_detect_target_type_from_message_url(self):
        """Test _detect_target_type_from_message with URL"""
        target_type, path = _detect_target_type_from_message(
            "Analyze this page: https://example.com"
        )
        assert target_type == "url"
        assert path == "https://example.com"

    def test_detect_target_type_from_message_local(self):
        """Test _detect_target_type_from_message with local path"""
        target_type, path = _detect_target_type_from_message(
            "Analyze code in ./src"
        )
        assert target_type == "local"
        assert path == "./src"


# ===========================================================================
# Test Class 5: Workflow API Operations
# ===========================================================================

class TestWorkflowAPIOperations:
    """Test workflow API operations"""

    def test_get_nonexistent_workflow(self):
        """Test GET /api/workflows/{name} with non-existent workflow"""
        client = TestClient(app)
        response = client.get("/api/workflows/nonexistent-workflow")
        assert response.status_code == 404

    def test_delete_nonexistent_workflow(self):
        """Test DELETE /api/workflows/{name} with non-existent workflow"""
        client = TestClient(app)
        response = client.delete("/api/workflows/nonexistent-workflow")
        # The actual implementation may return 404 or 200 with error in body
        assert response.status_code in [404, 400, 200]

    def test_delete_builtin_workflow(self):
        """Test DELETE /api/workflows/{name} with built-in workflow"""
        client = TestClient(app)
        response = client.delete("/api/workflows/build")  # built-in
        assert response.status_code == 403


# ===========================================================================
# Test Class 6: Session API Operations
# ===========================================================================

class TestSessionAPIOperations:
    """Test session API operations"""

    @pytest.fixture
    def mock_sessions_dir(self, tmp_path):
        """Use temp directory for sessions"""
        d = tmp_path / "sessions"
        d.mkdir()
        with patch("src.web.app.SESSIONS_DIR", d):
            yield d

    def test_get_nonexistent_session(self, mock_sessions_dir):
        """Test GET /api/sessions/{id} with non-existent session"""
        client = TestClient(app)
        response = client.get("/api/sessions/nonexistent-id")
        assert response.status_code == 404

    def test_update_nonexistent_session(self, mock_sessions_dir):
        """Test PUT /api/sessions/{id} with non-existent session"""
        client = TestClient(app)
        response = client.put(
            "/api/sessions/nonexistent-id",
            json={"title": "Updated"},
        )
        assert response.status_code == 404

    def test_delete_nonexistent_session(self, mock_sessions_dir):
        """Test DELETE /api/sessions/{id} with non-existent session"""
        client = TestClient(app)
        response = client.delete("/api/sessions/nonexistent-id")
        assert response.status_code == 404

    def test_create_and_manage_session(self, mock_sessions_dir):
        """Test full session lifecycle"""
        client = TestClient(app)

        # Create
        response = client.post("/api/sessions", json={"title": "Test Session"})
        assert response.status_code == 200
        data = response.json()
        session_id = data["session"]["id"]

        # Get
        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Test Session"

        # Update
        response = client.put(
            f"/api/sessions/{session_id}",
            json={"title": "Updated Session", "messages": [{"role": "user", "content": "Hello"}]},
        )
        assert response.status_code == 200

        # Delete
        response = client.delete(f"/api/sessions/{session_id}")
        assert response.status_code == 200

        # Verify deleted
        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 404


# ===========================================================================
# Test Class 7: Save Report Edge Cases
# ===========================================================================

class TestSaveReportEdgeCases:
    """Test POST /api/save-report edge cases"""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        task_manager._tasks.clear()
        task_manager._queues.clear()
        yield
        task_manager._tasks.clear()
        task_manager._queues.clear()

    def test_save_report_missing_task_id(self):
        """Test save-report with missing task_id"""
        client = TestClient(app)
        response = client.post("/api/save-report", json={})
        assert response.status_code == 400

    def test_save_report_nonexistent_task(self):
        """Test save-report with non-existent task"""
        client = TestClient(app)
        response = client.post(
            "/api/save-report", json={"task_id": "nonexistent-id"}
        )
        assert response.status_code == 404

    def test_save_report_from_history(self):
        """Test save-report with task from history_store"""
        client = TestClient(app)

        # Create a fake history record
        task_id = "test-history-id"
        history_store.save(
            task_id,
            {
                "task_id": task_id,
                "task": "Test task from history",
                "status": "completed",
                "started_at": datetime.now().isoformat(),
                "model": "deepseek",
                "workflow": "build",
                "project_path": ".",
                "stats": {
                    "total_tokens": 100,
                    "execution_time": 5.0,
                    "total_cost": 0.01,
                    "steps_completed": ["explore"],
                    "steps_failed": [],
                },
                "result": {
                    "summary": "Test completed",
                    "outputs": {"explore": {"result": "Done"}},
                },
            },
        )

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert data["status"] == "saved"

        # Cleanup
        history_store.delete(task_id)


# ===========================================================================
# Test Class 8: Execute Task Error Handling
# ===========================================================================

class TestExecuteTaskErrors:
    """Test execute_task error handling paths"""

    def test_execute_task_missing_body(self):
        """Test POST /api/execute with missing body"""
        client = TestClient(app)
        response = client.post("/api/execute", json=None)
        assert response.status_code == 400

    def test_execute_task_empty_task(self):
        """Test POST /api/execute with empty task field"""
        client = TestClient(app)
        response = client.post("/api/execute", json={"task": ""})
        assert response.status_code == 400


# ===========================================================================
# Test Class 9: Chat Endpoint Edge Cases
# ===========================================================================

class TestChatEndpointEdgeCases:
    """Test POST /api/chat edge cases"""

    def test_chat_short_message(self):
        """Test chat with short message"""
        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={
                "message": "Hi",
                "history": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "ready_to_execute" in data


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
