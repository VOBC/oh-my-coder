"""Targeted coverage tests for src.web.app.py - Batch 2."""

from unittest.mock import patch

import pytest

# Prevent concurrent execution - global singleton pollution
pytestmark = pytest.mark.xdist_group("web_app")


class TestSaveReportBranches:
    """Tests to cover missing branches in save_report function."""

    @patch("src.web.app.history_store")
    def test_save_report_with_step_outputs_string(self, mock_history_store):
        """Test save_report with step outputs as string."""
        from fastapi.testclient import TestClient

        from src.web.app import app, task_manager

        client = TestClient(app)

        # Create a task with string step output
        task_id = task_manager.create_task("test task", "deepseek", "build", ".")
        task = task_manager.get_task(task_id)
        task["status"] = "completed"
        task["started_at"] = "2024-01-01 12:00:00"
        task["step_outputs"] = {"step1": "output string"}
        task["result"] = {"summary": "test", "execution_time": 1.5, "total_tokens": 100}

        # Mock history_store.load to return None (task only in memory)
        mock_history_store.load.return_value = None

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200
        assert response.json()["status"] == "saved"

        # Cleanup
        task_manager.delete_task(task_id)

    @patch("src.web.app.history_store")
    def test_save_report_with_step_outputs_dict_with_result(self, mock_history_store):
        """Test save_report with step outputs dict containing result field."""
        from fastapi.testclient import TestClient

        from src.web.app import app, task_manager

        client = TestClient(app)

        # Create a task with dict step output that has result field
        task_id = task_manager.create_task("test task", "deepseek", "build", ".")
        task = task_manager.get_task(task_id)
        task["status"] = "completed"
        task["started_at"] = "2024-01-01 12:00:00"
        task["step_outputs"] = {"step1": {"result": "processed output"}}
        task["result"] = {"summary": "test", "execution_time": 1.5, "total_tokens": 100}

        mock_history_store.load.return_value = None

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200

        task_manager.delete_task(task_id)

    @patch("src.web.app.history_store")
    def test_save_report_with_step_outputs_dict_without_result(self, mock_history_store):
        """Test save_report with step outputs dict without result field."""
        from fastapi.testclient import TestClient

        from src.web.app import app, task_manager

        client = TestClient(app)

        # Create a task with dict step output without result field
        task_id = task_manager.create_task("test task", "deepseek", "build", ".")
        task = task_manager.get_task(task_id)
        task["status"] = "completed"
        task["started_at"] = "2024-01-01 12:00:00"
        task["step_outputs"] = {"step1": {"output": "some output", "data": 123}}
        task["result"] = {"summary": "test", "execution_time": 1.5, "total_tokens": 100}

        mock_history_store.load.return_value = None

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200

        task_manager.delete_task(task_id)

    @patch("src.web.app.history_store")
    def test_save_report_with_step_outputs_other_type(self, mock_history_store):
        """Test save_report with step outputs of other type (list)."""
        from fastapi.testclient import TestClient

        from src.web.app import app, task_manager

        client = TestClient(app)

        # Create a task with list step output
        task_id = task_manager.create_task("test task", "deepseek", "build", ".")
        task = task_manager.get_task(task_id)
        task["status"] = "completed"
        task["started_at"] = "2024-01-01 12:00:00"
        task["step_outputs"] = {"step1": ["item1", "item2"]}
        task["result"] = {"summary": "test", "execution_time": 1.5, "total_tokens": 100}

        mock_history_store.load.return_value = None

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200

        task_manager.delete_task(task_id)

    @patch("src.web.app.history_store")
    def test_save_report_with_empty_step_outputs(self, mock_history_store):
        """Test save_report with empty step outputs."""
        from fastapi.testclient import TestClient

        from src.web.app import app, task_manager

        client = TestClient(app)

        # Create a task with empty step outputs
        task_id = task_manager.create_task("test task", "deepseek", "build", ".")
        task = task_manager.get_task(task_id)
        task["status"] = "completed"
        task["started_at"] = "2024-01-01 12:00:00"
        task["step_outputs"] = {}
        task["result"] = {"summary": "test", "execution_time": 1.5, "total_tokens": 100}

        mock_history_store.load.return_value = None

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200

        task_manager.delete_task(task_id)

    @patch("src.web.app.history_store")
    def test_save_report_with_result_outputs(self, mock_history_store):
        """Test save_report with result.outputs (persisted task)."""
        from fastapi.testclient import TestClient

        from src.web.app import app, task_manager

        client = TestClient(app)

        # Create a task with result.outputs
        task_id = task_manager.create_task("test task", "deepseek", "build", ".")
        task = task_manager.get_task(task_id)
        task["status"] = "completed"
        task["started_at"] = "2024-01-01 12:00:00"
        task["result"] = {
            "summary": "test",
            "execution_time": 1.5,
            "total_tokens": 100,
            "outputs": {"step1": "output from result"}
        }

        mock_history_store.load.return_value = None

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200

        task_manager.delete_task(task_id)

    @patch("src.web.app.history_store")
    def test_save_report_with_final_result_dict_extra_keys(self, mock_history_store):
        """Test save_report with final result dict with extra keys."""
        from fastapi.testclient import TestClient

        from src.web.app import app, task_manager

        client = TestClient(app)

        # Create a task with extra keys in result
        task_id = task_manager.create_task("test task", "deepseek", "build", ".")
        task = task_manager.get_task(task_id)
        task["status"] = "completed"
        task["started_at"] = "2024-01-01 12:00:00"
        task["result"] = {
            "summary": "test",
            "execution_time": 1.5,
            "total_tokens": 100,
            "extra_key": "extra_value",
            "another_key": {"nested": "data"}
        }

        mock_history_store.load.return_value = None

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200

        task_manager.delete_task(task_id)

    @patch("src.web.app.history_store")
    def test_save_report_with_no_result(self, mock_history_store):
        """Test save_report with no result."""
        from fastapi.testclient import TestClient

        from src.web.app import app, task_manager

        client = TestClient(app)

        # Create a task with no result
        task_id = task_manager.create_task("test task", "deepseek", "build", ".")
        task = task_manager.get_task(task_id)
        task["status"] = "completed"
        task["started_at"] = "2024-01-01 12:00:00"
        task["result"] = None

        mock_history_store.load.return_value = None

        response = client.post("/api/save-report", json={"task_id": task_id})
        assert response.status_code == 200

        task_manager.delete_task(task_id)


class TestGenerateTaskSummaryCoverage:
    """Tests to cover _generate_task_summary function."""

    def test_with_all_workflow_types(self):
        """Test _generate_task_summary with all workflow types."""
        from src.web.app import _generate_task_summary

        for workflow in ["build", "review", "debug", "test"]:
            task = {
                "workflow": workflow,
                "model": "deepseek",
                "project_path": "./test",
                "target_type": "local"
            }
            result = _generate_task_summary(task)
            assert len(result) > 0

    def test_with_all_model_types(self):
        """Test _generate_task_summary with all model types."""
        from src.web.app import _generate_task_summary

        models = ["deepseek", "glm-4-flash", "MiniMax-Text-01", "moonshot-v1-128k",
                   "doubao-pro-32k", "tiangong-3", "Baichuan4", "unknown"]

        for model in models:
            task = {
                "workflow": "build",
                "model": model,
                "project_path": "./test",
                "target_type": "local"
            }
            result = _generate_task_summary(task)
            assert len(result) > 0

    def test_with_github_target(self):
        """Test _generate_task_summary with github target."""
        from src.web.app import _generate_task_summary

        task = {
            "workflow": "build",
            "model": "deepseek",
            "project_path": "https://github.com/user/repo",
            "target_type": "github"
        }
        result = _generate_task_summary(task)
        assert "GitHub 仓库" in result

    def test_with_url_target(self):
        """Test _generate_task_summary with url target."""
        from src.web.app import _generate_task_summary

        task = {
            "workflow": "build",
            "model": "deepseek",
            "project_path": "https://example.com",
            "target_type": "url"
        }
        result = _generate_task_summary(task)
        assert "网页" in result

    def test_with_local_target(self):
        """Test _generate_task_summary with local target."""
        from src.web.app import _generate_task_summary

        task = {
            "workflow": "build",
            "model": "deepseek",
            "project_path": "./local-path",
            "target_type": "local"
        }
        result = _generate_task_summary(task)
        assert "./local-path" in result
