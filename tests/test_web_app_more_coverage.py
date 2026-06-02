"""Additional simple tests for src.web.app.py - targeting specific missing lines."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Prevent concurrent execution - global singleton pollution
pytestmark = pytest.mark.xdist_group("web_app")


class TestExecuteEndpointBranches:
    """Tests for execute endpoint branches."""

    @patch("src.web.app.task_manager")
    def test_execute_with_auto_target_type(self, mock_task_manager):
        """Test execute with target_type='auto' triggers detection."""
        from src.web.app import app
        client = TestClient(app)

        # Mock task_manager
        mock_task_manager.create_task.return_value = "test-id-123"
        mock_task_manager._tasks = {"test-id-123": {"started_at": None, "status": "pending"}}

        response = client.post("/api/execute", json={
            "task": "test task",
            "project_path": "https://github.com/user/repo",
            "model": "deepseek",
            "workflow": "build",
            "target_type": "auto"
        })
        # Should work and detect target type
        assert response.status_code == 200
        assert response.json()["target_type"] == "github"

    @patch("src.web.app.task_manager")
    def test_execute_with_empty_target_type(self, mock_task_manager):
        """Test execute with empty target_type triggers detection."""
        from src.web.app import app
        client = TestClient(app)

        # Mock task_manager
        mock_task_manager.create_task.return_value = "test-id-123"
        mock_task_manager._tasks = {"test-id-123": {"started_at": None, "status": "pending"}}

        response = client.post("/api/execute", json={
            "task": "test task",
            "project_path": "./local-path",
            "model": "deepseek",
            "workflow": "build",
            "target_type": ""
        })
        # Should work and detect target type
        assert response.status_code == 200
        assert response.json()["target_type"] == "local"

    @patch("src.web.app.task_manager")
    def test_execute_with_explicit_target_type(self, mock_task_manager):
        """Test execute with explicit target_type skips detection."""
        from src.web.app import app
        client = TestClient(app)

        # Mock task_manager
        mock_task_manager.create_task.return_value = "test-id-123"
        mock_task_manager._tasks = {"test-id-123": {"started_at": None, "status": "pending"}}

        response = client.post("/api/execute", json={
            "task": "test task",
            "project_path": "whatever",
            "model": "deepseek",
            "workflow": "build",
            "target_type": "github"
        })
        assert response.status_code == 200
        assert response.json()["target_type"] == "github"


class TestSaveReportEdgeCases:
    """Tests for save_report edge cases."""

    @patch("src.web.app.history_store")
    def test_save_report_with_empty_result_outputs(self, mock_history_store):
        """Test save_report when result.outputs is empty."""
        from src.web.app import task_manager, app
        client = TestClient(app)

        task_id = task_manager.create_task("test", "deepseek", "build", ".")
        task = task_manager.get_task(task_id)
        task["status"] = "completed"
        task["started_at"] = "2024-01-01 12:00:00"
        task["result"] = {"summary": "test", "execution_time": 1.5, "total_tokens": 100, "outputs": {}}

        mock_history_store.load.return_value = None

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200

        task_manager.delete_task(task_id)

    @patch("src.web.app.history_store")
    def test_save_report_with_step_outputs_and_result_outputs(self, mock_history_store):
        """Test save_report with both step_outputs and result.outputs."""
        from src.web.app import task_manager, app
        client = TestClient(app)

        task_id = task_manager.create_task("test", "deepseek", "build", ".")
        task = task_manager.get_task(task_id)
        task["status"] = "completed"
        task["started_at"] = "2024-01-01 12:00:00"
        task["step_outputs"] = {"step1": "step output"}
        task["result"] = {"summary": "test", "execution_time": 1.5, "total_tokens": 100, "outputs": {"step2": "result output"}}

        mock_history_store.load.return_value = None

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200

        task_manager.delete_task(task_id)


class TestJsonDumpsFunction:
    """Tests for json_dumps function."""

    def test_json_dumps_with_datetime(self):
        """Test json_dumps handles datetime objects."""
        from src.web.app import json_dumps
        from datetime import datetime
        data = {"time": datetime(2024, 1, 1, 12, 0, 0)}
        result = json_dumps(data)
        assert "2024" in result

    def test_json_dumps_with_none(self):
        """Test json_dumps handles None values."""
        from src.web.app import json_dumps
        data = {"value": None}
        result = json_dumps(data)
        assert "null" in result or "None" in result

    def test_json_dumps_with_special_chars(self):
        """Test json_dumps handles special characters."""
        from src.web.app import json_dumps
        data = {"text": "中文测试\n换行\t制表"}
        result = json_dumps(data)
        assert "中文" in result
