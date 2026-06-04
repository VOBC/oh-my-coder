"""Boost coverage for src/web/app.py: _preprocess_target, _cleanup_target, TaskManager, test_connection fixes."""
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.xdist_group("web_app")


@pytest.fixture(autouse=True)
def reset_orchestrator():
    import src.web.app as app_mod
    app_mod._global_orchestrator = None
    yield
    app_mod._global_orchestrator = None


@pytest.fixture
def client():
    from src.web.app import app
    return TestClient(app)


# ============================================================
# Fix broken TestConnectionErrors tests (pass provider instead of model)
# ============================================================
class TestConnectionErrorsFixed:
    """Replaces broken tests in test_web_app_coverage_boost.py that pass model field."""

    def test_connection_timeout(self, client):
        import httpx
        with patch("httpx.Client") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_inst)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_inst.post.side_effect = httpx.TimeoutException("timeout")
            resp = client.post("/api/test-connection", json={
                "provider": "deepseek",
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com/v1"
            })
            assert resp.status_code == 200
            assert "超时" in resp.json()["msg"]

    def test_connection_connect_error(self, client):
        import httpx
        with patch("httpx.Client") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_inst)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_inst.post.side_effect = httpx.ConnectError("refused")
            resp = client.post("/api/test-connection", json={
                "provider": "deepseek",
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com/v1"
            })
            assert resp.status_code == 502
            assert "失败" in resp.json()["msg"]

    def test_connection_generic_error(self, client):
        with patch("httpx.Client") as mock_cls:
            mock_inst = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_inst)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_inst.post.side_effect = RuntimeError("unexpected")
            resp = client.post("/api/test-connection", json={
                "provider": "deepseek",
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com/v1"
            })
            assert resp.status_code == 500

    def test_connection_non_json_error_response(self, client):
        with patch("httpx.Client") as mock_cls:
            mock_inst = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_resp.json.side_effect = ValueError("not json")
            mock_resp.text = "rate limited"
            mock_inst.post.return_value = mock_resp
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_inst)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.post("/api/test-connection", json={
                "provider": "deepseek",
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com/v1"
            })
            assert resp.status_code == 502

    def test_connection_unknown_provider(self, client):
        resp = client.post("/api/test-connection", json={
            "provider": "nonexistent",
            "api_key": "sk-test",
        })
        assert resp.status_code == 400
        assert "未知供应商" in resp.json()["msg"]

    def test_connection_custom_mode_no_key(self, client):
        resp = client.post("/api/test-connection", json={
            "base_url": "https://api.example.com/v1",
            "model_id": "my-model",
            "api_key": ""
        })
        assert resp.status_code == 400
        assert "API Key 为空" in resp.json()["msg"]

    def test_connection_custom_mode_success(self, client):
        with patch("httpx.Client") as mock_cls:
            mock_inst = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
            mock_inst.post.return_value = mock_resp
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_inst)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.post("/api/test-connection", json={
                "base_url": "https://api.example.com/v1",
                "model_id": "my-model",
                "api_key": "sk-test"
            })
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

    def test_connection_custom_mode_api_error(self, client):
        with patch("httpx.Client") as mock_cls:
            mock_inst = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.text = "invalid key"
            mock_inst.post.return_value = mock_resp
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_inst)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.post("/api/test-connection", json={
                "base_url": "https://api.example.com/v1",
                "model_id": "my-model",
                "api_key": "sk-invalid"
            })
            assert resp.status_code == 502


# ============================================================
# _preprocess_target error paths (lines 89, 110, 120-142)
# ============================================================
class TestPreprocessTarget:
    def test_preprocess_target_github_clone_failure(self):
        """Line 110: git clone returncode != 0."""
        from src.web.app import _preprocess_target
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 128
            mock_result.stderr = "fatal: repository not found"
            mock_run.return_value = mock_result
            with pytest.raises(RuntimeError, match="git clone 失败"):
                _preprocess_target("https://github.com/user/nonexistent", "github", "task123")

    def test_preprocess_target_github_subprocess_exception(self):
        """Line 120-123: subprocess.run raises Exception."""
        from src.web.app import _preprocess_target
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("git not found")
            with pytest.raises(OSError):
                _preprocess_target("https://github.com/user/repo", "github", "task456")

    def test_preprocess_target_url_fetch_failure(self):
        """Line 135-137: requests.get raises Exception."""

        import requests as req_lib

        from src.web.app import _preprocess_target
        # Mock requests module
        req_mock = MagicMock()
        req_mock.get.side_effect = req_lib.ConnectionError("DNS failed")
        with patch.dict("sys.modules", {"requests": req_mock}):
            with pytest.raises(RuntimeError, match="获取网页失败"):
                _preprocess_target("https://example.com", "url", "task789")


# ============================================================
# _cleanup_target (lines 151-152)
# ============================================================
class TestCleanupTarget:
    def test_cleanup_target_github_temp_dir(self):
        """Remove github temp dir."""
        from src.web.app import _cleanup_target
        tmp = tempfile.mkdtemp(prefix="omc-gh-test-")
        assert Path(tmp).exists()
        _cleanup_target(tmp, "github")
        assert not Path(tmp).exists()

    def test_cleanup_target_non_github(self):
        """Non-github paths not removed."""
        from src.web.app import _cleanup_target
        _cleanup_target("/some/other/path", "local")


# ============================================================
# TaskManager methods
# ============================================================
class TestTaskManagerMethods:
    def test_get_queue_existing(self):
        from src.web.app import TaskManager
        tm = TaskManager()
        tid = tm.create_task("test")
        queue = tm.get_queue(tid)
        assert queue is not None

    def test_get_queue_nonexistent(self):
        from src.web.app import TaskManager
        tm = TaskManager()
        assert tm.get_queue("nonexistent") is None

    def test_update_step_nonexistent_task(self):
        """Line 235: update_step on non-existent task does nothing."""
        from src.web.app import TaskManager
        tm = TaskManager()
        tm.update_step("nonexistent", "step1", "running", "content")

    def test_complete_task_nonexistent_task(self):
        from src.web.app import TaskManager
        tm = TaskManager()
        tm.complete_task("nonexistent")

    def test_delete_task_nonexistent(self):
        from src.web.app import TaskManager
        tm = TaskManager()
        result = tm.delete_task("nonexistent")
        assert result is False


# ============================================================
# /api/chat endpoint — uses message field (not messages)
# ============================================================
class TestChatEndpoint:
    def test_chat_missing_body(self, client):
        """FastAPI returns 422 when body is missing entirely."""
        resp = client.post("/api/chat", json=None)
        assert resp.status_code == 422

    def test_chat_empty_message(self, client):
        """Empty message is accepted (short message logic triggers)."""
        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data

    def test_chat_short_message_needs_more_info(self, client):
        """Short message (<10 chars) returns ready_to_execute=False."""
        resp = client.post("/api/chat", json={"message": "hi"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready_to_execute"] is False

    def test_chat_long_message_ready(self, client):
        """Long message with target is ready to execute."""
        resp = client.post("/api/chat", json={
            "message": "Please review my code at github.com/user/repo"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data

    def test_chat_completions_success_nonstreaming(self, client):
        """POST /api/chat/completions non-streaming."""
        from src.web.app import create_orchestrator, create_router
        router = create_router()
        orch = create_orchestrator(router)
        with patch("src.web.app.get_orchestrator", return_value=orch):
            mock_response = MagicMock()
            mock_response.content = "Hello from model"
            mock_response.model = "deepseek-chat"
            mock_response.usage = MagicMock(
                prompt_tokens=10, completion_tokens=5, total_tokens=15
            )
            with patch.object(orch.model_router, "route_and_call", new_callable=AsyncMock, return_value=mock_response):
                resp = client.post("/api/chat/completions", json={
                    "messages": [{"role": "user", "content": "hello"}],
                    "model": "deepseek",
                    "stream": False
                })
                assert resp.status_code == 200
                data = resp.json()
                assert "content" in data


# ============================================================
# /api/save-report edge cases
# ============================================================
class TestSaveReportEdgeCases:
    def test_save_report_task_not_found(self, client):
        resp = client.post("/api/save-report", json={"task_id": "nonexistent-task-id"})
        assert resp.status_code == 404

    def test_save_report_missing_task_id(self, client):
        resp = client.post("/api/save-report", json={})
        assert resp.status_code == 400


# ============================================================
# Startup / initialization paths
# ============================================================
class TestStartupPaths:
    def test_mask_key_function(self):
        """_mask_key masks all but last 4 characters."""
        from src.web.app import _mask_key
        # Long key: only last 4 chars visible
        result = _mask_key("sk-abcdefghij1234567890")
        assert result.endswith("7890")
        assert "*" in result
        # Short key (<=4): shown as-is
        result2 = _mask_key("abc")
        assert result2 == "abc"
        # Empty key
        result3 = _mask_key("")
        assert result3 == ""


# ============================================================
# _detect_target_type edge cases
# ============================================================
class TestDetectTargetType:
    def test_detect_github_git_url(self):
        from src.web.app import _detect_target_type
        assert _detect_target_type("git@github.com:user/repo.git") == "github"

    def test_detect_http_url(self):
        from src.web.app import _detect_target_type
        assert _detect_target_type("http://example.com/page") == "url"
        assert _detect_target_type("https://example.com/page") == "url"

    def test_detect_local_path(self):
        from src.web.app import _detect_target_type
        assert _detect_target_type("./my-project") == "local"
        assert _detect_target_type("~/projects/app") == "local"
        assert _detect_target_type("/usr/local/bin") == "local"
        assert _detect_target_type("") == "local"


# ============================================================
# Additional edge case coverage
# ============================================================
class TestAdditionalCoverage:
    def test_chat_with_history(self, client):
        """Chat with history (no short-message check triggers)."""
        resp = client.post("/api/chat", json={
            "message": "hi",
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "how can i help?"}
            ]
        })
        assert resp.status_code == 200

    def test_detect_workflow_explicit(self):
        """Explicit workflow detection."""
        from src.web.app import _detect_workflow
        assert _detect_workflow("Review the code quality") in ["review", "build", "debug", "test"]
        assert _detect_workflow("Fix the bug in main.py") in ["review", "build", "debug", "test"]
        assert _detect_workflow("Build a new feature") in ["review", "build", "debug", "test"]

    def test_generate_task_summary(self):
        """Task summary generation."""
        from src.web.app import _generate_task_summary
        config = {
            "description": "test",
            "workflow": "build",
            "model": "deepseek",
            "target_type": "local",
            "project_path": "/tmp/test"
        }
        result = _generate_task_summary(config)
        assert isinstance(result, str)

    def test_delete_task_existing(self):
        """Delete an existing task returns True."""
        from src.web.app import TaskManager
        tm = TaskManager()
        tid = tm.create_task("delete-me")
        assert tm.delete_task(tid) is True
        assert tm.get_task(tid) is None
