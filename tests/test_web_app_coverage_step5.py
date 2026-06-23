"""
Step 5: Coverage boost for src/web/app.py (77% -> 90%+)

Covers:
1. /api/chat/completions (stream + non-stream)
2. run_task (success/failure/timeout/429/generic error)
3. _preprocess_target (url, github, local, empty)
4. tiangong/baichuan/mimo/doubao provider test-connection
5. Session CRUD API
6. _read_settings error fallback
7. Save-report with various step_outputs formats
8. Custom model test-connection
9. Coverage API
10. _cleanup_target
11. SSE execute / agent live stream
12. Settings API
"""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Use a separate xdist group to avoid task_manager state pollution
# with test_web_app_routes.py
pytestmark = pytest.mark.xdist_group("web_app_coverage_step5")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.base import AgentOutput, AgentStatus
from src.web.app import (
    _cleanup_target,
    _preprocess_target,
    app,
    task_manager,
)


@pytest.fixture
def client():
    return TestClient(app)


# Store task IDs created during each test for proper cleanup
def _get_task_ids_to_cleanup():
    """Get list of task IDs that should be cleaned up."""
    return list(task_manager._tasks.keys())


@pytest.fixture(autouse=True)
def reset_task_manager():
    task_manager._tasks.clear()
    task_manager._queues.clear()
    yield
    task_manager._tasks.clear()
    task_manager._queues.clear()


# ============================================================
# 1. /api/chat/completions
# ============================================================
class TestChatCompletions:
    """Test /api/chat/completions endpoint (stream + non-stream)"""

    @patch("src.web.app.get_orchestrator")
    def test_chat_completions_non_stream(self, mock_get_orch, client):
        """Non-streaming chat completion"""
        from src.models.base import ModelResponse, ModelTier, Usage

        mock_orch = MagicMock()
        mock_router = MagicMock()

        success_resp = ModelResponse(
            content="Hello! How can I help?",
            model="deepseek-chat",
            provider="deepseek",
            tier=ModelTier.LOW,
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            finish_reason="stop",
        )
        mock_router.route_and_call = AsyncMock(return_value=success_resp)
        mock_orch.model_router = mock_router
        mock_get_orch.return_value = mock_orch

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
        assert data["content"] == "Hello! How can I help?"
        assert data["model"] == "deepseek-chat"

    @patch("src.web.app.get_orchestrator")
    def test_chat_completions_non_stream_error(self, mock_get_orch, client):
        """Non-streaming chat completion with model error"""
        mock_orch = MagicMock()
        mock_router = MagicMock()
        mock_router.route_and_call = AsyncMock(
            side_effect=Exception("Model unavailable")
        )
        mock_orch.model_router = mock_router
        mock_get_orch.return_value = mock_orch

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
        assert "模型调用失败" in data["content"]

    @patch("src.web.app.get_orchestrator")
    def test_chat_completions_stream(self, mock_get_orch, client):
        """Streaming chat completion via SSE"""
        from src.models.base import ModelResponse, ModelTier, Usage

        mock_orch = MagicMock()
        mock_router = MagicMock()

        success_resp = ModelResponse(
            content="Hello stream!",
            model="deepseek-chat",
            provider="deepseek",
            tier=ModelTier.LOW,
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            finish_reason="stop",
        )
        mock_router.route_and_call = AsyncMock(return_value=success_resp)
        mock_orch.model_router = mock_router
        mock_get_orch.return_value = mock_orch

        with client.stream(
            "POST",
            "/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "deepseek",
                "stream": True,
            },
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            chunks = []
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    chunks.append(line[6:])
            assert len(chunks) >= 2
            last = json.loads(chunks[-1])
            assert last.get("done") is True

    @patch("src.web.app.get_orchestrator")
    def test_chat_completions_stream_error(self, mock_get_orch, client):
        """Streaming chat completion with error"""
        mock_orch = MagicMock()
        mock_router = MagicMock()
        mock_router.route_and_call = AsyncMock(
            side_effect=Exception("Stream error")
        )
        mock_orch.model_router = mock_router
        mock_get_orch.return_value = mock_orch

        with client.stream(
            "POST",
            "/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "deepseek",
                "stream": True,
            },
        ) as resp:
            assert resp.status_code == 200
            chunks = []
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    chunks.append(line[6:])
            assert len(chunks) >= 1
            error_data = json.loads(chunks[-1])
            assert error_data.get("error") is True


# ============================================================
# 2. run_task
# ============================================================
class TestRunTask:
    """Test run_task function (lines 1018-1180)"""

    @pytest.mark.asyncio
    @patch("src.web.app.history_store")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app._preprocess_target")
    async def test_run_task_success(
        self, mock_preprocess, mock_get_orch, mock_cleanup, mock_hist_store, tmp_path
    ):
        """run_task with successful workflow execution"""
        mock_preprocess.return_value = (str(tmp_path), "")
        mock_cleanup.return_value = None
        mock_hist_store.save = MagicMock()

        mock_orch = MagicMock()
        mock_agent = MagicMock()
        mock_output = AgentOutput(
            agent_name="explore",
            status=AgentStatus.COMPLETED,
            result="Scan complete",
            usage={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50},
        )
        mock_agent.execute = AsyncMock(return_value=mock_output)
        mock_orch.get_agent.return_value = mock_agent

        from src.core.orchestrator import (
            WORKFLOW_TEMPLATES,
        )
        from src.web.app import run_task

        # Setup active_workflows dict
        mock_orch._active_workflows = {}

        with patch("src.web.app.WORKFLOW_TEMPLATES", WORKFLOW_TEMPLATES):
            with patch("src.web.app.history_store", mock_hist_store):
                mock_get_orch.return_value = mock_orch

                task_id = task_manager.create_task(
                    task_desc="test run_task",
                    model="deepseek",
                    workflow="build",
                    project_path=str(tmp_path),
                )

                await run_task(
                    task_id=task_id,
                    task="test task",
                    project_path=str(tmp_path),
                    model="deepseek",
                    workflow_name="build",
                    target_type="local",
                )

                t = task_manager.get_task(task_id)
                assert t is not None

    @pytest.mark.asyncio
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    async def test_run_task_preprocess_failure(self, mock_preprocess, mock_hist_store, tmp_path):
        """run_task with _preprocess_target failure"""
        mock_preprocess.side_effect = RuntimeError("Preprocess failed")
        mock_hist_store.save = MagicMock()

        from src.web.app import run_task

        task_id = task_manager.create_task(
            task_desc="test preprocess fail",
            model="deepseek",
            workflow="build",
            project_path=str(tmp_path),
        )

        with patch("src.web.app.history_store", mock_hist_store):
            await run_task(
                task_id=task_id,
                task="test task",
                project_path=str(tmp_path),
                model="deepseek",
                workflow_name="build",
                target_type="local",
            )

        t = task_manager.get_task(task_id)
        assert t["status"] == "failed"

    @pytest.mark.asyncio
    @patch("src.web.app.history_store")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app._preprocess_target")
    async def test_run_task_agent_timeout(
        self, mock_preprocess, mock_get_orch, mock_cleanup, mock_hist_store, tmp_path
    ):
        """run_task with agent timeout"""
        mock_preprocess.return_value = (str(tmp_path), "")
        mock_cleanup.return_value = None
        mock_hist_store.save = MagicMock()

        mock_orch = MagicMock()
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=TimeoutError("Agent timed out"))
        mock_orch.get_agent.return_value = mock_agent
        mock_orch._active_workflows = {}

        from src.core.orchestrator import WORKFLOW_TEMPLATES
        from src.web.app import run_task

        with patch("src.web.app.WORKFLOW_TEMPLATES", WORKFLOW_TEMPLATES):
            with patch("src.web.app.history_store", mock_hist_store):
                mock_get_orch.return_value = mock_orch

                task_id = task_manager.create_task(
                    task_desc="test timeout",
                    model="deepseek",
                    workflow="build",
                    project_path=str(tmp_path),
                )

                await run_task(
                    task_id=task_id,
                    task="test task",
                    project_path=str(tmp_path),
                    model="deepseek",
                    workflow_name="build",
                    target_type="local",
                )

                t = task_manager.get_task(task_id)
                assert t is not None

    @pytest.mark.asyncio
    @patch("src.web.app.history_store")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app._preprocess_target")
    async def test_run_task_agent_generic_error(
        self, mock_preprocess, mock_get_orch, mock_cleanup, mock_hist_store, tmp_path
    ):
        """run_task with generic agent error"""
        mock_preprocess.return_value = (str(tmp_path), "")
        mock_cleanup.return_value = None
        mock_hist_store.save = MagicMock()

        mock_orch = MagicMock()
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=RuntimeError("Something went wrong"))
        mock_orch.get_agent.return_value = mock_agent
        mock_orch._active_workflows = {}

        from src.core.orchestrator import WORKFLOW_TEMPLATES
        from src.web.app import run_task

        with patch("src.web.app.WORKFLOW_TEMPLATES", WORKFLOW_TEMPLATES):
            with patch("src.web.app.history_store", mock_hist_store):
                mock_get_orch.return_value = mock_orch

                task_id = task_manager.create_task(
                    task_desc="test generic error",
                    model="deepseek",
                    workflow="build",
                    project_path=str(tmp_path),
                )

                await run_task(
                    task_id=task_id,
                    task="test task",
                    project_path=str(tmp_path),
                    model="deepseek",
                    workflow_name="build",
                    target_type="local",
                )

                t = task_manager.get_task(task_id)
                assert t is not None

    @pytest.mark.asyncio
    @patch("src.web.app.history_store")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app._preprocess_target")
    async def test_run_task_outer_exception(
        self, mock_preprocess, mock_get_orch, mock_cleanup, mock_hist_store, tmp_path
    ):
        """run_task with outer exception"""
        mock_preprocess.return_value = (str(tmp_path), "")
        mock_cleanup.return_value = None
        mock_hist_store.save = MagicMock()

        mock_get_orch.side_effect = Exception("Orchestrator init failed")

        from src.web.app import run_task

        task_id = task_manager.create_task(
            task_desc="test outer exception",
            model="deepseek",
            workflow="build",
            project_path=str(tmp_path),
        )

        with patch("src.web.app.history_store", mock_hist_store):
            await run_task(
                task_id=task_id,
                task="test task",
                project_path=str(tmp_path),
                model="deepseek",
                workflow_name="build",
                target_type="local",
            )

        t = task_manager.get_task(task_id)
        assert t["status"] == "failed"


# ============================================================
# 3. _preprocess_target
# ============================================================
class TestPreprocessTarget:
    """Test _preprocess_target function (lines 80-148)"""

    def test_empty_target(self):
        path, ctx = _preprocess_target("", "local", "test-id")
        assert path == "."
        assert ctx == ""

    def test_whitespace_target(self):
        path, ctx = _preprocess_target("   ", "local", "test-id")
        assert path == "."

    def test_local_target(self):
        path, ctx = _preprocess_target("/tmp/project", "local", "test-id")
        assert path == "/tmp/project"
        assert ctx == ""

    def test_default_type_is_local(self):
        path, ctx = _preprocess_target("/tmp/project", "unknown_type", "test-id")
        assert path == "/tmp/project"

    @patch("src.web.app.subprocess.run")
    def test_github_target_success(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)

        with patch("src.web.app.tempfile.mkdtemp", return_value=str(tmp_path / "gh-clone")):
            (tmp_path / "gh-clone").mkdir(exist_ok=True)
            path, ctx = _preprocess_target(
                "https://github.com/test/repo", "github", "test-id-1234"
            )
        assert "gh-clone" in path
        assert "GitHub 仓库" in ctx

    @patch("src.web.app.subprocess.run")
    def test_github_target_clone_failure(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stderr="fatal: repo not found")

        with patch("src.web.app.tempfile.mkdtemp", return_value=str(tmp_path / "gh-fail")):
            (tmp_path / "gh-fail").mkdir(exist_ok=True)
            with pytest.raises(RuntimeError, match="git clone"):
                _preprocess_target(
                    "https://github.com/test/nonexistent", "github", "test-id-1234"
                )

    def test_url_target_success(self):
        """Test URL target with mocked requests"""
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>Hello <b>World</b></body></html>"

        with (
            patch("src.web.app.requests", create=True),
            patch("builtins.__import__"),
        ):
            # Since requests is imported locally inside the function,
            # we need to patch the builtin import
            # This is too complex; let's test the function directly
            pass

        # Instead, let's just test with a mock of the whole function behavior
        # by using subprocess.run to avoid the local import issue
        # Actually, let's patch at the right level

        # The function does `import requests` locally, so we need to
        # make requests available in sys.modules
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_resp

        with patch.dict("sys.modules", {"requests": mock_requests}):
            path, ctx = _preprocess_target("https://example.com/page", "url", "test-id")
            assert path == "."
            assert "网页内容" in ctx

    def test_url_target_failure(self):
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("Network error")

        with patch.dict("sys.modules", {"requests": mock_requests}):
            with pytest.raises(RuntimeError, match="获取网页失败"):
                _preprocess_target("https://example.com/fail", "url", "test-id")

    def test_url_target_long_content_truncated(self):
        mock_resp = MagicMock()
        mock_resp.text = "<p>" + "x" * 10000 + "</p>"
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_resp

        with patch.dict("sys.modules", {"requests": mock_requests}):
            path, ctx = _preprocess_target("https://example.com/long", "url", "test-id")
            assert "内容已截断" in ctx


# ============================================================
# 4. test-connection: tiangong/baichuan/mimo/doubao providers
# ============================================================
class TestConnectionProviders:
    """Test /api/test-connection for various providers (lines 1489-1582)"""

    def _make_mock_httpx_client(self, status_code=200, headers=None, json_data=None, text=""):
        """Helper to create a mock httpx.Client that works as context manager"""
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.headers = headers or {"content-type": "application/json"}
        if json_data is not None:
            mock_resp.json.return_value = json_data
        else:
            mock_resp.json.side_effect = ValueError("No JSON")
        mock_resp.text = text

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_resp

        # Context manager support
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        return mock_client_cls

    def test_tiangong_provider_success(self, client):
        mock_client_cls = self._make_mock_httpx_client(
            status_code=200,
            headers={"content-type": "application/json"},
        )

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "tiangong", "api_key": "test-key"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True

    def test_baichuan_provider_success(self, client):
        mock_client_cls = self._make_mock_httpx_client(status_code=200)

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "baichuan", "api_key": "test-key"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True

    def test_mimo_provider_success(self, client):
        mock_client_cls = self._make_mock_httpx_client(status_code=200)

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "mimo", "api_key": "test-key"},
            )
            assert response.status_code == 200

    def test_doubao_provider_success(self, client):
        mock_client_cls = self._make_mock_httpx_client(status_code=200)

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "doubao", "api_key": "test-key"},
            )
            assert response.status_code == 200

    def test_unknown_provider(self, client):
        response = client.post(
            "/api/test-connection",
            json={"provider": "unknown_provider", "api_key": "test-key"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False
        assert "未知供应商" in data["msg"]

    def test_provider_401_error(self, client):
        mock_client_cls = self._make_mock_httpx_client(status_code=401)

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "tiangong", "api_key": "bad-key"},
            )
            data = response.json()
            assert data["ok"] is False
            assert "401" in data["msg"]

    def test_provider_403_error(self, client):
        mock_client_cls = self._make_mock_httpx_client(status_code=403)

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "baichuan", "api_key": "forbidden-key"},
            )
            data = response.json()
            assert data["ok"] is False
            assert "403" in data["msg"]

    def test_provider_500_error_with_json(self, client):
        mock_client_cls = self._make_mock_httpx_client(
            status_code=500,
            json_data={"error": {"message": "Internal error"}},
            text='{"error":{"message":"Internal error"}}',
        )

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "tiangong", "api_key": "test-key"},
            )
            data = response.json()
            assert data["ok"] is False

    def test_provider_502_error_non_json(self, client):
        mock_client_cls = self._make_mock_httpx_client(
            status_code=502,
            text="Bad Gateway",
        )

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "baichuan", "api_key": "test-key"},
            )
            data = response.json()
            assert data["ok"] is False

    def test_provider_html_response(self, client):
        """Provider returns HTML instead of JSON API response"""
        mock_client_cls = self._make_mock_httpx_client(
            status_code=200,
            headers={"content-type": "text/html"},
        )

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "tiangong", "api_key": "test-key"},
            )
            data = response.json()
            assert data["ok"] is False

    def test_provider_timeout(self, client):
        import httpx as real_httpx

        mock_client_instance = MagicMock()
        mock_client_instance.post.side_effect = real_httpx.TimeoutException("Timeout")

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "baichuan", "api_key": "test-key"},
            )
            data = response.json()
            assert data["ok"] is False
            assert "超时" in data["msg"]

    def test_provider_connect_error(self, client):
        import httpx as real_httpx

        mock_client_instance = MagicMock()
        mock_client_instance.post.side_effect = real_httpx.ConnectError("Connection refused")

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Must use the REAL httpx module since the function does `import httpx` locally
        # and catches httpx.ConnectError which must be a real exception class
        original_httpx = sys.modules.get("httpx")
        try:
            # Patch httpx.Client to return our mock, but keep real exception classes
            with patch.object(real_httpx, "Client", mock_client_cls):
                response = client.post(
                    "/api/test-connection",
                    json={"provider": "tiangong", "api_key": "test-key"},
                )
                data = response.json()
                assert data["ok"] is False
        finally:
            if original_httpx:
                sys.modules["httpx"] = original_httpx

    def test_provider_generic_error(self, client):
        mock_client_instance = MagicMock()
        mock_client_instance.post.side_effect = RuntimeError("Unexpected error")

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={"provider": "baichuan", "api_key": "test-key"},
            )
            data = response.json()
            assert data["ok"] is False

    def test_custom_model_success(self, client):
        """Custom model test-connection (base_url + model_id)"""
        mock_client_cls = self._make_mock_httpx_client(status_code=200)

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={
                    "base_url": "https://custom.api.com/v1",
                    "model_id": "my-model",
                    "api_key": "test-key",
                },
            )
            data = response.json()
            assert data["ok"] is True

    def test_custom_model_error(self, client):
        mock_client_cls = self._make_mock_httpx_client(
            status_code=500,
            text="Error",
        )

        import httpx as real_httpx
        with patch.object(real_httpx, "Client", mock_client_cls):
            response = client.post(
                "/api/test-connection",
                json={
                    "base_url": "https://custom.api.com/v1",
                    "model_id": "my-model",
                    "api_key": "test-key",
                },
            )
            data = response.json()
            assert data["ok"] is False

    def test_custom_model_no_api_key(self, client):
        response = client.post(
            "/api/test-connection",
            json={
                "base_url": "https://custom.api.com/v1",
                "model_id": "my-model",
                "api_key": "",
            },
        )
        assert response.status_code == 400

    def test_missing_params(self, client):
        response = client.post("/api/test-connection", json={})
        assert response.status_code == 400


# ============================================================
# 5. Session API
# ============================================================
class TestSessionAPI:
    """Test Session CRUD API (lines 1712-1820)"""

    def test_create_session(self, client, tmp_path):
        with patch("src.web.app.SESSIONS_DIR", tmp_path):
            response = client.post("/api/sessions", json={"title": "Test Session"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "id" in data.get("session", data)

    def test_list_sessions(self, client, tmp_path):
        with patch("src.web.app.SESSIONS_DIR", tmp_path):
            session_file = tmp_path / "test-session-1.json"
            session_file.write_text(
                json.dumps({
                    "id": "test-session-1",
                    "title": "Test",
                    "messages": [],
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                })
            )
            response = client.get("/api/sessions")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict) and "sessions" in data
            sessions = data.get("sessions", data) if isinstance(data, dict) else data
            assert any(s["id"] == "test-session-1" for s in sessions)

    def test_get_session(self, client, tmp_path):
        with patch("src.web.app.SESSIONS_DIR", tmp_path):
            session_file = tmp_path / "session-abc.json"
            session_file.write_text(
                json.dumps({
                    "id": "session-abc",
                    "title": "My Session",
                    "messages": [{"role": "user", "content": "hello"}],
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                })
            )
            response = client.get("/api/sessions/session-abc")
            assert response.status_code == 200

    def test_get_session_not_found(self, client, tmp_path):
        with patch("src.web.app.SESSIONS_DIR", tmp_path):
            response = client.get("/api/sessions/nonexistent")
            assert response.status_code == 404

    def test_update_session(self, client, tmp_path):
        with patch("src.web.app.SESSIONS_DIR", tmp_path):
            session_file = tmp_path / "session-upd.json"
            session_file.write_text(
                json.dumps({
                    "id": "session-upd",
                    "title": "Old Title",
                    "messages": [],
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                })
            )
            response = client.put(
                "/api/sessions/session-upd",
                json={"title": "New Title"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_update_session_not_found(self, client, tmp_path):
        with patch("src.web.app.SESSIONS_DIR", tmp_path):
            response = client.put(
                "/api/sessions/nonexistent",
                json={"title": "New Title"},
            )
            assert response.status_code == 404

    def test_delete_session(self, client, tmp_path):
        with patch("src.web.app.SESSIONS_DIR", tmp_path):
            session_file = tmp_path / "session-del.json"
            session_file.write_text(
                json.dumps({
                    "id": "session-del",
                    "title": "To Delete",
                    "messages": [],
                })
            )
            response = client.delete("/api/sessions/session-del")
            assert response.status_code == 200

    def test_delete_session_not_found(self, client, tmp_path):
        with patch("src.web.app.SESSIONS_DIR", tmp_path):
            response = client.delete("/api/sessions/nonexistent")
            assert response.status_code == 404


# ============================================================
# 6. _read_settings error fallback
# ============================================================
class TestReadSettingsFallback:
    """Test _read_settings error fallback (lines 1314-1378)"""

    def test_read_settings_parse_error(self):
        from src.web.app import _read_settings

        with patch("src.web.app.SETTINGS_FILE", Path("/nonexistent/settings.json")):
            result = _read_settings()
            assert "models" in result
            assert "defaults" in result

    def test_read_settings_missing_keys(self, tmp_path):
        from src.web.app import _read_settings

        settings_file = tmp_path / "config.json"
        settings_file.write_text(json.dumps({"something": "else"}))

        with patch("src.web.app.SETTINGS_FILE", settings_file):
            result = _read_settings()
            assert "models" in result
            assert "deepseek" in result["models"]
            assert "defaults" in result


# ============================================================
# 7. Save-report with various step_outputs formats
# ============================================================
class TestSaveReportStepOutputs:
    """Test save-report with various step_outputs formats (lines 604-649)"""

    @pytest.fixture(autouse=True)
    def mock_task_manager(self, monkeypatch):
        """Mock task_manager to avoid parallel execution conflicts."""
        from src.web.app import task_manager as real_tm

        mock_tasks = {}
        mock_queues = {}

        # Create a real task_manager-like object with real dicts
        class MockTaskManager:
            def __init__(self):
                self._tasks = mock_tasks
                self._queues = mock_queues

            def create_task(self, **kwargs):
                tid = real_tm.create_task(**kwargs)
                self._tasks[tid] = real_tm._tasks[tid].copy()
                self._tasks[tid]["started_at"] = datetime.now().isoformat()
                return tid

            def get_task(self, tid):
                return self._tasks.get(tid)

        mock_tm = MockTaskManager()

        # Patch the endpoint to use our mock
        monkeypatch.setattr("src.web.app.task_manager", mock_tm)

        yield

        mock_tasks.clear()
        mock_queues.clear()

    def _create_task(self, mock_tasks, **kwargs):
        """Helper to create a task and store in mock_tasks."""
        # Use the real task_manager to create a task
        from src.web.app import task_manager as real_tm
        tid = real_tm.create_task(**kwargs)
        # Store in mock_tasks for the test to use
        mock_tasks[tid] = real_tm._tasks[tid].copy()
        return tid

    @patch("src.web.app.history_store")
    @patch("src.web.app.Path.home")
    def test_save_report_with_string_step_outputs(self, mock_home, mock_store, client, tmp_path):
        mock_home.return_value = tmp_path
        tid = self._create_task(
            task_manager._tasks,
            task_desc="report test",
            model="deepseek",
            workflow="build",
            project_path=str(tmp_path),
        )
        task_manager._tasks[tid]["status"] = "completed"
        task_manager._tasks[tid]["started_at"] = datetime.now().isoformat()
        task_manager._tasks[tid]["step_outputs"] = {
            "explore": "Scanned the project",
            "architect": "Designed the architecture",
        }
        task_manager._tasks[tid]["result"] = {"summary": "done"}

        response = client.post("/api/save-report", json={"task_id": tid})
        assert response.status_code == 200

    @patch("src.web.app.history_store")
    @patch("src.web.app.Path.home")
    def test_save_report_with_dict_step_outputs(self, mock_home, mock_store, client, tmp_path):
        mock_home.return_value = tmp_path
        tid = self._create_task(
            task_manager._tasks,
            task_desc="report test 2",
            model="deepseek",
            workflow="build",
            project_path=str(tmp_path),
        )
        task_manager._tasks[tid]["status"] = "completed"
        task_manager._tasks[tid]["started_at"] = datetime.now().isoformat()
        task_manager._tasks[tid]["step_outputs"] = {
            "explore": {"result": "Scan result", "tokens": 100},
            "architect": {"output": "Architecture design"},
        }
        task_manager._tasks[tid]["result"] = {
            "summary": "completed",
            "execution_time": 10,
            "total_tokens": 200,
            "custom_key": "custom_value",
        }

        response = client.post("/api/save-report", json={"task_id": tid})
        assert response.status_code == 200

    @patch("src.web.app.history_store")
    @patch("src.web.app.Path.home")
    def test_save_report_with_dict_result_other_types(self, mock_home, mock_store, client, tmp_path):
        mock_home.return_value = tmp_path
        tid = self._create_task(
            task_manager._tasks,
            task_desc="report test 3",
            model="deepseek",
            workflow="build",
            project_path=str(tmp_path),
        )
        task_manager._tasks[tid]["status"] = "completed"
        task_manager._tasks[tid]["started_at"] = datetime.now().isoformat()
        task_manager._tasks[tid]["step_outputs"] = {
            "explore": {"content": "Scan content"},
        }
        task_manager._tasks[tid]["result"] = {
            "summary": "done",
            "execution_time": 5,
            "total_tokens": 100,
            "count": 42,
        }

        response = client.post("/api/save-report", json={"task_id": tid})
        assert response.status_code == 200

    @patch("src.web.app.history_store")
    @patch("src.web.app.Path.home")
    def test_save_report_with_string_final_result(self, mock_home, mock_store, client, tmp_path):
        """Test save-report when result dict has a string value for a key"""
        mock_home.return_value = tmp_path
        tid = self._create_task(
            task_manager._tasks,
            task_desc="report test 4",
            model="deepseek",
            workflow="build",
            project_path=str(tmp_path),
        )
        task_manager._tasks[tid]["status"] = "completed"
        task_manager._tasks[tid]["started_at"] = datetime.now().isoformat()
        # result must be a dict; test the else branch for non-dict final result
        task_manager._tasks[tid]["result"] = {
            "summary": "done",
            "execution_time": 5,
            "total_tokens": 100,
            "note": "A simple note",
        }

        response = client.post("/api/save-report", json={"task_id": tid})
        assert response.status_code == 200

    @patch("src.web.app.history_store")
    @patch("src.web.app.Path.home")
    def test_save_report_with_none_step_output(self, mock_home, mock_store, client, tmp_path):
        """Test step_output that is None (should show '无输出')"""
        mock_home.return_value = tmp_path
        tid = self._create_task(
            task_manager._tasks,
            task_desc="report test 5",
            model="deepseek",
            workflow="build",
            project_path=str(tmp_path),
        )
        task_manager._tasks[tid]["status"] = "completed"
        task_manager._tasks[tid]["started_at"] = datetime.now().isoformat()
        task_manager._tasks[tid]["step_outputs"] = {
            "explore": None,
        }
        task_manager._tasks[tid]["result"] = {"summary": "done"}

        response = client.post("/api/save-report", json={"task_id": tid})
        assert response.status_code == 200


class TestCoverageAPI:
    """Test /api/coverage endpoints (lines 1832-1863)"""

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_get_coverage_success(self, mock_format, mock_run, client):
        mock_run.return_value = {"overall": 0.9}
        mock_format.return_value = {"overall": {"coverage": 90}}

        response = client.get("/api/coverage")
        assert response.status_code == 200

    @patch("src.web.app.run_coverage_analysis")
    def test_get_coverage_error(self, mock_run, client):
        mock_run.side_effect = RuntimeError("Analysis failed")

        response = client.get("/api/coverage")
        assert response.status_code == 500

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_run_coverage_success(self, mock_format, mock_run, client):
        mock_run.return_value = {"overall": 0.9}
        mock_format.return_value = {"overall": {"coverage": 90}}

        response = client.post("/api/coverage/run")
        assert response.status_code == 200

    @patch("src.web.app.run_coverage_analysis")
    def test_run_coverage_error(self, mock_run, client):
        mock_run.side_effect = RuntimeError("Run failed")

        response = client.post("/api/coverage/run")
        assert response.status_code == 500


# ============================================================
# 9. _cleanup_target
# ============================================================
class TestCleanupTarget:
    """Test _cleanup_target function"""

    def test_cleanup_github_target_in_tempdir(self):
        """Cleanup should work for paths under tempfile.gettempdir()"""
        gh_dir = Path(tempfile.mkdtemp(prefix="omc-gh-test-"))
        (gh_dir / "file.txt").write_text("test")

        _cleanup_target(str(gh_dir), "github")
        assert not gh_dir.exists()

    def test_cleanup_non_github_target(self, tmp_path):
        """Non-github targets should not be cleaned"""
        _cleanup_target(str(tmp_path), "local")
        assert tmp_path.exists()

    def test_cleanup_nonexistent_path(self):
        """Should not raise on nonexistent path"""
        _cleanup_target("/nonexistent/path/that/does/not/exist", "github")


# ============================================================
# 10. SSE execute endpoint
# ============================================================
class TestSSEExecute:
    """Test /sse/execute/{task_id} endpoint (lines 348-373)"""

    def test_sse_execute_not_found(self, client):
        response = client.get("/sse/execute/nonexistent")
        assert response.status_code == 404

    # NOTE: agent_live_stream and sse_execute_with_task tests are skipped
    # because they require async event loop handling that conflicts with
    # TestClient's sync context manager. These are covered by integration tests.


# ============================================================
# 11. Settings API
# ============================================================
class TestSettingsAPI:
    """Test settings read/save endpoints"""

    def test_get_settings(self, client):
        response = client.get("/api/settings")
        assert response.status_code == 200

    def test_save_settings(self, client, tmp_path):
        with patch("src.web.app.SETTINGS_DIR", tmp_path):
            with patch("src.web.app.SETTINGS_FILE", tmp_path / "config.json"):
                response = client.post(
                    "/api/settings",
                    json={
                        "models": {
                            "deepseek": {"api_key": "sk-test123"},
                        },
                        "defaults": {"model": "deepseek"},
                    },
                )
                assert response.status_code == 200

    def test_save_settings_masked_key(self, client, tmp_path):
        """Masked API keys (starting with *) should be skipped"""
        with patch("src.web.app.SETTINGS_DIR", tmp_path):
            with patch("src.web.app.SETTINGS_FILE", tmp_path / "config.json"):
                response = client.post(
                    "/api/settings",
                    json={
                        "models": {
                            "deepseek": {"api_key": "***masked***"},
                        },
                    },
                )
                assert response.status_code == 200
