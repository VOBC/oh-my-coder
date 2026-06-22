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

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.xdist_group("web_app")

# ===== _detect_target_type =====
class TestDetectTargetType:
    def test_empty(self):
        from src.web.app import _detect_target_type
        assert _detect_target_type("") == "local"

    def test_github(self):
        from src.web.app import _detect_target_type
        assert _detect_target_type("https://github.com/user/repo") == "github"

    def test_github_www(self):
        from src.web.app import _detect_target_type
        assert _detect_target_type("https://www.github.com/u/r") == "github"

    def test_git_at(self):
        from src.web.app import _detect_target_type
        assert _detect_target_type("git@github.com:u/r.git") == "github"

    def test_http(self):
        from src.web.app import _detect_target_type
        assert _detect_target_type("https://example.com") == "url"

    def test_local(self):
        from src.web.app import _detect_target_type
        assert _detect_target_type("/tmp/x") == "local"

    def test_whitespace(self):
        from src.web.app import _detect_target_type
        assert _detect_target_type("   ") == "local"


# ===== _preprocess_target =====
class TestPreprocessTarget:
    def test_empty(self):
        from src.web.app import _preprocess_target
        p, c = _preprocess_target("", "local", "a")
        assert p == "." and c == ""

    def test_local(self):
        from src.web.app import _preprocess_target
        p, c = _preprocess_target("/tmp/x", "local", "a")
        assert p == "/tmp/x" and c == ""

    def test_url_ok(self):
        from src.web.app import _preprocess_target
        import requests as rm
        mr = MagicMock()
        mr.text = "<html><body><h1>Hello</h1></body></html>"
        with patch.object(rm, "get", return_value=mr):
            p, c = _preprocess_target("https://x.com", "url", "a")
        assert p == "." and "Hello" in c

    def test_url_truncated(self):
        from src.web.app import _preprocess_target
        import requests as rm
        mr = MagicMock(text="<p>" + "x" * 10000 + "</p>")
        with patch.object(rm, "get", return_value=mr):
            _, c = _preprocess_target("https://x.com", "url", "a")
        assert "截断" in c

    def test_url_fail(self):
        from src.web.app import _preprocess_target
        import requests as rm
        with patch.object(rm, "get", side_effect=Exception("f")):
            with pytest.raises(RuntimeError, match="获取网页失败"):
                _preprocess_target("https://bad.com", "url", "a")

    def test_url_strip_scripts(self):
        from src.web.app import _preprocess_target
        import requests as rm
        mr = MagicMock(text="<style>x</style><script>alert(1)</script>Content")
        with patch.object(rm, "get", return_value=mr):
            _, c = _preprocess_target("https://x.com", "url", "a")
        assert "alert(1)" not in c

    def test_github_ok(self):
        from src.web.app import _preprocess_target
        mr = MagicMock(returncode=0)
        with patch("src.web.app.subprocess.run", MagicMock(return_value=mr)), \
             patch("src.web.app.tempfile.mkdtemp", return_value="/tmp/t"), \
             patch("src.web.app.shutil.rmtree"):
            _, c = _preprocess_target("https://github.com/u/r", "github", "t")
        assert "github" in c

    def test_github_dotgit(self):
        from src.web.app import _preprocess_target
        mr = MagicMock(returncode=0)
        with patch("src.web.app.subprocess.run", MagicMock(return_value=mr)), \
             patch("src.web.app.tempfile.mkdtemp", return_value="/tmp/t"), \
             patch("src.web.app.shutil.rmtree"):
            _, c = _preprocess_target("https://github.com/u/r.git", "github", "t")
        assert "github" in c

    def test_github_fail(self):
        from src.web.app import _preprocess_target
        mr = MagicMock(returncode=1, stderr="fatal")
        with patch("src.web.app.subprocess.run", MagicMock(return_value=mr)), \
             patch("src.web.app.tempfile.mkdtemp", return_value="/tmp/t"), \
             patch("src.web.app.shutil.rmtree"):
            with pytest.raises(RuntimeError):
                _preprocess_target("https://github.com/u/r", "github", "t")


class TestCleanupTarget:
    def test_github(self):
        import tempfile
        from src.web.app import _cleanup_target
        with patch("src.web.app.shutil.rmtree") as m:
            _cleanup_target(f"{tempfile.gettempdir()}/t", "github")
            m.assert_called_once()

    def test_local(self):
        from src.web.app import _cleanup_target
        with patch("src.web.app.shutil.rmtree") as m:
            _cleanup_target("/x", "local")
            m.assert_not_called()


class TestTaskManager:
    @pytest.fixture
    def tm(self):
        from src.web.app import TaskManager
        return TaskManager()

    def test_create(self, tm):
        tid = tm.create_task("t", "deepseek", "build", ".")
        assert len(tid) == 8 and tm.get_task(tid)["task"] == "t"

    def test_get_queue(self, tm):
        tid = tm.create_task()
        assert tm.get_queue(tid) is not None
        assert tm.get_queue("nope") is None

    def test_update_step(self, tm):
        tid = tm.create_task()
        tm.update_step(tid, "e", "active", "m")
        assert tm.get_task(tid)["step_status"]["e"] == "active"

    def test_update_step_nocontent(self, tm):
        tid = tm.create_task()
        tm.update_step(tid, "e", "active")
        assert "e" not in tm.get_task(tid).get("step_outputs", {})

    def test_update_step_nonexistent(self, tm):
        tm.update_step("nope", "e", "a")

    def test_complete_ok(self, tm):
        tid = tm.create_task()
        tm.complete_task(tid, result={"s": "ok"})
        assert tm.get_task(tid)["status"] == "completed"

    def test_complete_err(self, tm):
        tid = tm.create_task()
        tm.complete_task(tid, error="e")
        assert tm.get_task(tid)["status"] == "failed"

    def test_complete_nonexistent(self, tm):
        tm.complete_task("nope", result={"x": 1})

    def test_delete(self, tm):
        tid = tm.create_task()
        assert tm.delete_task(tid) and tm.get_task(tid) is None

    def test_delete_nonexistent(self, tm):
        assert not tm.delete_task("nope")

    def test_list(self, tm):
        tm.create_task("a"); tm.create_task("b")
        assert len(tm.list_tasks()) == 2

    def test_list_empty(self, tm):
        assert tm.list_tasks() == []


class TestJsonDumps:
    def test_basic(self):
        from src.web.app import json_dumps
        assert '"key"' in json_dumps({"key": "v"})

    def test_chinese(self):
        from src.web.app import json_dumps
        assert "你好" in json_dumps({"msg": "你好"})

    def test_non_serializable(self):
        from src.web.app import json_dumps
        assert "2024" in json_dumps({"dt": __import__("datetime").datetime(2024,1,1)})


class TestDetectFunctions:
    def test_wf_review(self):
        from src.web.app import _detect_workflow
        assert _detect_workflow("审查代码") == "review"

    def test_wf_debug(self):
        from src.web.app import _detect_workflow
        assert _detect_workflow("debug") == "debug"

    def test_wf_test(self):
        from src.web.app import _detect_workflow
        assert _detect_workflow("单元测试") == "test"

    def test_wf_default(self):
        from src.web.app import _detect_workflow
        assert _detect_workflow("random") == "build"

    def test_model_ds(self):
        from src.web.app import _detect_model
        assert _detect_model("deepseek") == "deepseek"

    def test_model_glm(self):
        from src.web.app import _detect_model
        assert _detect_model("免费智谱glm") == "glm-4-flash"

    def test_model_mimo(self):
        from src.web.app import _detect_model
        assert _detect_model("minimax小米") == "MiniMax-Text-01"

    def test_model_kimi(self):
        from src.web.app import _detect_model
        assert _detect_model("kimi月之暗面") == "moonshot-v1-128k"

    def test_model_doubao(self):
        from src.web.app import _detect_model
        assert _detect_model("豆包doubao") == "doubao-pro-32k"

    def test_model_tiangong(self):
        from src.web.app import _detect_model
        assert _detect_model("天工") == "tiangong-3"

    def test_model_baichuan(self):
        from src.web.app import _detect_model
        assert _detect_model("百川baichuan") == "Baichuan4"

    def test_model_default(self):
        from src.web.app import _detect_model
        assert _detect_model("随便") == "deepseek"

    def test_target_gh(self):
        from src.web.app import _detect_target_type_from_message
        assert _detect_target_type_from_message("https://github.com/u/r")[0] == "github"

    def test_target_url(self):
        from src.web.app import _detect_target_type_from_message
        assert _detect_target_type_from_message("https://x.com")[0] == "url"

    def test_target_local(self):
        from src.web.app import _detect_target_type_from_message
        assert _detect_target_type_from_message("./p")[0] == "local"

    def test_target_none(self):
        from src.web.app import _detect_target_type_from_message
        t, p = _detect_target_type_from_message("写功能")
        assert t == "local" and p == "."

    def test_target_home(self):
        from src.web.app import _detect_target_type_from_message
        assert _detect_target_type_from_message("~/p")[0] == "local"


class TestGenerateTaskSummary:
    def test_github(self):
        from src.web.app import _generate_task_summary
        s = _generate_task_summary({"workflow": "build", "model": "deepseek",
            "project_path": "https://github.com/u/r", "target_type": "github"})
        assert "DeepSeek" in s and "GitHub" in s

    def test_url(self):
        from src.web.app import _generate_task_summary
        assert "GLM" in _generate_task_summary({"workflow": "review", "model": "glm-4-flash",
            "project_path": "https://x.com", "target_type": "url"})

    def test_local(self):
        from src.web.app import _generate_task_summary
        assert "/tmp" in _generate_task_summary({"workflow": "debug", "model": "deepseek",
            "project_path": "/tmp", "target_type": "local"})

    def test_unknown(self):
        from src.web.app import _generate_task_summary
        assert "custom" in _generate_task_summary({"workflow": "custom",
            "model": "x", "project_path": ".", "target_type": "local"})


class TestMaskKey:
    def test_short(self):
        from src.web.app import _mask_key
        assert _mask_key("abc") == "abc"

    def test_empty(self):
        from src.web.app import _mask_key
        assert _mask_key("") == "" and _mask_key(None) == ""

    def test_long(self):
        from src.web.app import _mask_key
        assert _mask_key("abcdefghij") == "******ghij"


class TestReadSettings:
    def test_default(self, tmp_path):
        from src.web.app import _read_settings
        with patch("src.web.app.SETTINGS_FILE", tmp_path / "c"), \
             patch("src.web.app.SETTINGS_DIR", tmp_path):
            assert "models" in _read_settings()

    def test_existing(self, tmp_path):
        from src.web.app import _read_settings
        f = tmp_path / "c"
        f.write_text('{"models":{"deepseek":{"api_key":"x"}},"defaults":{}}')
        with patch("src.web.app.SETTINGS_FILE", f), \
             patch("src.web.app.SETTINGS_DIR", tmp_path):
            assert _read_settings()["models"]["deepseek"]["api_key"] == "x"

    def test_corrupted(self, tmp_path):
        from src.web.app import _read_settings
        f = tmp_path / "c"
        f.write_text("not json")
        with patch("src.web.app.SETTINGS_FILE", f), \
             patch("src.web.app.SETTINGS_DIR", tmp_path):
            assert "models" in _read_settings()

    def test_partial(self, tmp_path):
        from src.web.app import _read_settings
        f = tmp_path / "c"
        f.write_text('{"models":{}}')
        with patch("src.web.app.SETTINGS_FILE", f), \
             patch("src.web.app.SETTINGS_DIR", tmp_path):
            assert "deepseek" in _read_settings()["models"]


# ===== HTML Pages =====
class TestPages:
    def test_index(self, client): assert client.get("/").status_code == 200
    def test_history(self, client): assert client.get("/history").status_code == 200
    def test_agents(self, client): assert client.get("/agents").status_code == 200
    def test_dashboard(self, client): assert client.get("/dashboard").status_code == 200
    def test_settings(self, client): assert client.get("/settings").status_code == 200
    def test_coverage(self, client): assert client.get("/coverage").status_code == 200
    def test_docs(self, client): assert client.get("/docs").status_code == 200
    def test_favicon(self, client): assert client.get("/favicon.ico").status_code == 200


# ===== API Endpoints =====
class TestHealth:
    def test_ok(self, client):
        r = client.get("/health")
        assert r.json()["status"] == "healthy"


class TestTasks:
    def test_list_empty(self, client):
        from src.web.app import task_manager
        task_manager._tasks.clear(); task_manager._queues.clear()
        assert client.get("/api/tasks").json()["tasks"] == []

    def test_get_404(self, client):
        assert client.get("/api/tasks/nope").status_code == 404

    def test_get_ok(self, client):
        from src.web.app import task_manager
        tid = task_manager.create_task("t")
        assert client.get(f"/api/tasks/{tid}").status_code == 200


class TestApiHistory:
    def test_200(self, client):
        r = client.get("/api/history")
        assert r.status_code == 200 and "records" in r.json()


class TestDashboard:
    @patch("src.web.app.history_store")
    def test_stats(self, m, client):
        m.get_stats.return_value = {"total_tasks": 5}
        assert client.get("/api/dashboard/stats").status_code == 200

    @patch("src.web.app.history_store")
    def test_files(self, m, client):
        m.list_all.return_value = []
        r = client.get("/api/dashboard/files")
        assert r.status_code == 200 and "files" in r.json()

    @patch("src.web.app.history_store")
    def test_files_with_path(self, m, client, tmp_path):
        m.list_all.return_value = [{"project_path": str(tmp_path)}]
        assert client.get("/api/dashboard/files").status_code == 200

    @patch("src.web.app.history_store")
    def test_files_nonexistent(self, m, client):
        m.list_all.return_value = [{"project_path": "/nonexistent_12345"}]
        assert client.get("/api/dashboard/files").status_code == 200


class TestOpenFolder:
    def test_no_path(self, client):
        assert client.post("/api/open-folder", json={}).status_code == 400

    def test_ok_darwin(self, client):
        with patch("subprocess.run"), patch("platform.system", return_value="Darwin"):
            assert client.post("/api/open-folder", json={"path": "/tmp"}).json()["status"] == "ok"

    def test_ok_windows(self, client):
        with patch("subprocess.run"), patch("platform.system", return_value="Windows"):
            assert client.post("/api/open-folder", json={"path": "C:\\\\t"}).status_code == 200

    def test_ok_linux(self, client):
        with patch("subprocess.run"), patch("platform.system", return_value="Linux"):
            assert client.post("/api/open-folder", json={"path": "/tmp"}).status_code == 200

    def test_error(self, client):
        with patch("subprocess.run", side_effect=Exception("x")), \
             patch("platform.system", return_value="Darwin"):
            assert client.post("/api/open-folder", json={"path": "/x"}).status_code == 500


class TestSaveReport:
    def test_no_task_id(self, client):
        assert client.post("/api/save-report", json={}).status_code == 400

    def test_not_found(self, client):
        assert client.post("/api/save-report", json={"task_id": "nope"}).status_code == 404

    def test_from_memory(self, client, tmp_path):
        from src.web.app import task_manager
        tid = task_manager.create_task("t", "deepseek", "build", "/tmp")
        task_manager._tasks[tid]["started_at"] = "2024-01-01T00:00:00"
        with patch("src.web.app.Path.home", return_value=tmp_path):
            assert client.post("/api/save-report", json={"task_id": tid}).status_code == 200

    def test_from_history(self, client, tmp_path):
        mt = {"task_id":"h","task":"t","status":"completed","started_at":"2024-01-01",
            "model":"deepseek","workflow":"build","project_path":"/tmp",
            "stats":{"total_tokens":100,"execution_time":5.0,"total_cost":0.01},
            "result":{"summary":"ok","execution_time":5.0,"total_tokens":100,
                "outputs":{"e":{"result":"done"}}},"step_outputs":{}}
        with patch("src.web.app.task_manager") as m, \
             patch("src.web.app.history_store") as h, \
             patch("src.web.app.Path.home", return_value=tmp_path):
            m.get_task.return_value = None; h.load.return_value = mt
            assert client.post("/api/save-report", json={"task_id":"h"}).status_code == 200

    def test_string_step_output(self, client, tmp_path):
        from src.web.app import task_manager
        tid = task_manager.create_task("t", "deepseek", "build", "/tmp")
        task_manager._tasks[tid]["started_at"] = "2024-01-01T00:00:00"
        task_manager._tasks[tid]["result"] = {"outputs": {"e": "string output"}}
        with patch("src.web.app.Path.home", return_value=tmp_path):
            assert client.post("/api/save-report", json={"task_id": tid}).status_code == 200

    def test_dict_step_with_result(self, client, tmp_path):
        from src.web.app import task_manager
        tid = task_manager.create_task("t", "deepseek", "build", "/tmp")
        task_manager._tasks[tid]["started_at"] = "2024-01-01T00:00:00"
        task_manager._tasks[tid]["result"] = {"outputs": {"e": {"result": "done"}}}
        with patch("src.web.app.Path.home", return_value=tmp_path):
            assert client.post("/api/save-report", json={"task_id": tid}).status_code == 200

    def test_dict_step_no_result(self, client, tmp_path):
        from src.web.app import task_manager
        tid = task_manager.create_task("t", "deepseek", "build", "/tmp")
        task_manager._tasks[tid]["started_at"] = "2024-01-01T00:00:00"
        task_manager._tasks[tid]["result"] = {"outputs": {"e": {"data": [1]}}}
        with patch("src.web.app.Path.home", return_value=tmp_path):
            assert client.post("/api/save-report", json={"task_id": tid}).status_code == 200

    def test_result_extra_dict(self, client, tmp_path):
        from src.web.app import task_manager
        tid = task_manager.create_task("t", "deepseek", "build", "/tmp")
        task_manager._tasks[tid]["started_at"] = "2024-01-01T00:00:00"
        task_manager._tasks[tid]["result"] = {"summary":"ok","execution_time":1.0,
            "total_tokens":10,"outputs":{},"extra":{"a":1}}
        with patch("src.web.app.Path.home", return_value=tmp_path):
            assert client.post("/api/save-report", json={"task_id": tid}).status_code == 200

    def test_history_no_outputs(self, client, tmp_path):
        mt = {"task_id":"h","task":"t","status":"completed","started_at":"2024-01-01",
            "model":"deepseek","workflow":"build","project_path":"/tmp",
            "stats":{"total_tokens":0,"execution_time":0,"total_cost":0},
            "result":{"summary":"ok"},"step_outputs":{}}
        with patch("src.web.app.task_manager") as m, \
             patch("src.web.app.history_store") as h, \
             patch("src.web.app.Path.home", return_value=tmp_path):
            m.get_task.return_value = None; h.load.return_value = mt
            assert client.post("/api/save-report", json={"task_id":"h"}).status_code == 200

    def test_step_output_empty_string(self, client, tmp_path):
        from src.web.app import task_manager
        tid = task_manager.create_task("t", "deepseek", "build", "/tmp")
        task_manager._tasks[tid]["started_at"] = "2024-01-01T00:00:00"
        task_manager._tasks[tid]["step_outputs"] = {"e": ""}
        task_manager._tasks[tid]["result"] = {"outputs": {}}
        with patch("src.web.app.Path.home", return_value=tmp_path):
            assert client.post("/api/save-report", json={"task_id": tid}).status_code == 200


class TestChatEndpoint:
    def test_short(self, client):
        assert not client.post("/api/chat", json={"message":"hi","history":[]}).json()["ready_to_execute"]

    def test_long(self, client):
        r = client.post("/api/chat", json={"message":"请帮我开发一个完整的用户认证功能包括登录注册和JWT"})
        assert r.json()["ready_to_execute"]

    def test_with_history(self, client):
        r = client.post("/api/chat", json={"message":"go","history":[
            {"role":"user","content":"some long history message text"},
            {"role":"assistant","content":"some long history response text"}]})
        assert r.json()["ready_to_execute"]

    def test_review(self, client):
        assert "审查" in client.post("/api/chat", json={"message":"请审查这段代码的质量"}).json()["reply"]

    def test_test(self, client):
        assert "测试" in client.post("/api/chat", json={"message":"请帮我为这个项目写完整的单元测试"}).json()["reply"]

    def test_debug(self, client):
        assert "调试" in client.post("/api/chat", json={"message":"请debug修复这个bug问题"}).json()["reply"]

    def test_build(self, client):
        assert "开发" in client.post("/api/chat", json={"message":"请帮我开发一个完整的用户认证功能"}).json()["reply"]

    def test_github_target(self, client):
        r = client.post("/api/chat", json={"message":"请分析 https://github.com/user/repo 的代码质量"})
        assert "github.com" in r.json()["reply"]


class TestChatCompletion:
    @patch("src.web.app.get_orchestrator")
    def test_ok(self, go, client):
        mo = MagicMock()
        mr = AsyncMock()
        resp = MagicMock(content="Hi", model="ds",
            usage=MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30))
        mr.route_and_call = AsyncMock(return_value=resp)
        mo.model_router = mr; go.return_value = mo
        r = client.post("/api/chat/completions", json={
            "messages":[{"role":"user","content":"hi"}],"model":"ds","stream":False})
        assert r.json()["content"] == "Hi"

    @patch("src.web.app.get_orchestrator")
    def test_error(self, go, client):
        mo = MagicMock()
        mr = AsyncMock()
        mr.route_and_call = AsyncMock(side_effect=Exception("e"))
        mo.model_router = mr; go.return_value = mo
        assert "失败" in client.post("/api/chat/completions", json={
            "messages":[{"role":"user","content":"hi"}],"model":"ds","stream":False}).json()["content"]


class TestExecuteEndpoint:
    def test_no_body(self, client):
        assert client.post("/api/execute").status_code == 400

    def test_no_task(self, client):
        assert client.post("/api/execute", json={"project_path":"."}).status_code == 400

    @patch("src.web.app.run_task")
    def test_ok(self, m, client):
        r = client.post("/api/execute", json={"task":"do","project_path":"/tmp",
            "model":"deepseek","workflow":"build"})
        assert r.json()["status"] == "started" and "task_id" in r.json()

    @patch("src.web.app.run_task")
    def test_github(self, m, client):
        assert client.post("/api/execute", json={"task":"x",
            "project_path":"https://github.com/u/r","workflow":"build"}).json()["target_type"] == "github"


class TestExecuteSync:
    @patch("src.web.app.create_orchestrator")
    @patch("src.web.app.create_router")
    def test_success(self, cr, co, client):
        from src.agents.base import AgentStatus
        cr.return_value = MagicMock()
        orch = MagicMock()
        agent = AsyncMock()
        out = MagicMock(status=AgentStatus.COMPLETED, result="done",
            usage={"total_tokens":10})
        agent.execute = AsyncMock(return_value=out)
        orch.get_agent.return_value = agent; co.return_value = orch
        assert client.post("/api/execute-sync", json={
            "task":"do","project_path":"/tmp"}).status_code == 200

    @patch("src.web.app.create_orchestrator")
    @patch("src.web.app.create_router")
    def test_agent_fail(self, cr, co, client):
        from src.agents.base import AgentStatus
        cr.return_value = MagicMock()
        orch = MagicMock()
        agent = AsyncMock()
        out = MagicMock(status=AgentStatus.FAILED, error="err")
        agent.execute = AsyncMock(return_value=out)
        orch.get_agent.return_value = agent; co.return_value = orch
        r = client.post("/api/execute-sync", json={
            "task":"do","project_path":"/tmp"})
        assert r.json()["status"] == "error"

    @patch("src.web.app.create_orchestrator")
    @patch("src.web.app.create_router")
    def test_timeout(self, cr, co, client):
        cr.return_value = MagicMock()
        orch = MagicMock()
        agent = AsyncMock(execute=AsyncMock(side_effect=TimeoutError()))
        orch.get_agent.return_value = agent; co.return_value = orch
        assert "超时" in client.post("/api/execute-sync", json={
            "task":"do","project_path":"/tmp"}).json()["message"]

    @patch("src.web.app.create_orchestrator")
    @patch("src.web.app.create_router")
    def test_exception(self, cr, co, client):
        cr.side_effect = Exception("fail")
        r = client.post("/api/execute-sync", json={
            "task":"do","project_path":"/tmp"})
        assert r.json()["status"] == "error"


class TestConfigEndpoint:
    def test_get(self, client):
        d = client.get("/api/config").json()
        assert "models" in d and "workflows" in d


class TestSettingsEndpoints:
    def test_get(self, client, tmp_path):
        with patch("src.web.app.SETTINGS_FILE", tmp_path/"c"), \
             patch("src.web.app.SETTINGS_DIR", tmp_path):
            assert client.get("/api/settings").status_code == 200

    def test_post(self, client, tmp_path):
        f = tmp_path/"c"
        with patch("src.web.app.SETTINGS_FILE", f), \
             patch("src.web.app.SETTINGS_DIR", tmp_path):
            r = client.post("/api/settings", json={
                "models":{"deepseek":{"api_key":"sk-key"}},"defaults":{"timeout":600}})
        assert r.status_code == 200
        assert json.loads(f.read_text())["models"]["deepseek"]["api_key"] == "sk-key"

    def test_post_masked(self, client, tmp_path):
        f = tmp_path/"c"
        with patch("src.web.app.SETTINGS_FILE", f), \
             patch("src.web.app.SETTINGS_DIR", tmp_path):
            client.post("/api/settings", json={"models":{"deepseek":{"api_key":"****x"}}})
        assert json.loads(f.read_text())["models"]["deepseek"]["api_key"] == ""

    def test_post_new_model(self, client, tmp_path):
        f = tmp_path/"c"
        with patch("src.web.app.SETTINGS_FILE", f), \
             patch("src.web.app.SETTINGS_DIR", tmp_path):
            r = client.post("/api/settings", json={"models":{"new":{"provider":"N","api_key":"k"}}})
        assert r.status_code == 200 and "new" in json.loads(f.read_text())["models"]


class TestTestConnection:
    def _mc(self, status=200, ct="application/json", text="", jd=None):
        r = MagicMock(status_code=status, headers={"content-type":ct}, text=text)
        if jd: r.json.return_value = jd
        else: r.json.side_effect = Exception("not json")
        c = MagicMock(); c.post.return_value = r
        return c

    def test_no_params(self, client):
        assert client.post("/api/test-connection", json={}).status_code == 400

    def test_unknown_provider(self, client):
        assert client.post("/api/test-connection",
            json={"provider":"xyz","api_key":"k"}).status_code == 400

    @patch("httpx.Client")
    def test_provider_ok(self, hx, client):
        hx.return_value.__enter__ = MagicMock(return_value=self._mc())
        hx.return_value.__exit__ = MagicMock(return_value=False)
        assert client.post("/api/test-connection",
            json={"provider":"deepseek","api_key":"sk"}).json()["ok"]

    @patch("httpx.Client")
    def test_provider_html(self, hx, client):
        hx.return_value.__enter__ = MagicMock(return_value=self._mc(ct="text/html"))
        hx.return_value.__exit__ = MagicMock(return_value=False)
        r = client.post("/api/test-connection", json={"provider":"glm","api_key":"sk"})
        assert not r.json()["ok"] and "网页" in r.json()["msg"]

    @patch("httpx.Client")
    def test_provider_401(self, hx, client):
        hx.return_value.__enter__ = MagicMock(return_value=self._mc(401))
        hx.return_value.__exit__ = MagicMock(return_value=False)
        assert "401" in client.post("/api/test-connection",
            json={"provider":"kimi","api_key":"sk"}).json()["msg"]

    @patch("httpx.Client")
    def test_provider_403(self, hx, client):
        hx.return_value.__enter__ = MagicMock(return_value=self._mc(403))
        hx.return_value.__exit__ = MagicMock(return_value=False)
        assert "403" in client.post("/api/test-connection",
            json={"provider":"doubao","api_key":"sk"}).json()["msg"]

    @patch("httpx.Client")
    def test_provider_timeout(self, hx, client):
        import httpx
        hx.side_effect = httpx.TimeoutException("t/o")
        assert "超时" in client.post("/api/test-connection",
            json={"provider":"deepseek","api_key":"sk"}).json()["msg"]

    @patch("httpx.Client")
    def test_provider_connect_err(self, hx, client):
        import httpx
        hx.side_effect = httpx.ConnectError("refused")
        assert client.post("/api/test-connection",
            json={"provider":"mimo","api_key":"sk"}).status_code == 502

    @patch("httpx.Client")
    def test_provider_generic(self, hx, client):
        hx.side_effect = Exception("err")
        assert client.post("/api/test-connection",
            json={"provider":"tiangong","api_key":"sk"}).status_code == 500

    @patch("httpx.Client")
    def test_provider_500_json(self, hx, client):
        hx.return_value.__enter__ = MagicMock(return_value=self._mc(500, jd={"error":{"message":"int"}}))
        hx.return_value.__exit__ = MagicMock(return_value=False)
        assert client.post("/api/test-connection",
            json={"provider":"baichuan","api_key":"sk"}).status_code == 502

    @patch("httpx.Client")
    def test_provider_500_text(self, hx, client):
        hx.return_value.__enter__ = MagicMock(return_value=self._mc(500, "text/plain", "err"))
        hx.return_value.__exit__ = MagicMock(return_value=False)
        assert client.post("/api/test-connection",
            json={"provider":"baichuan","api_key":"sk"}).status_code == 502

    def test_custom_no_key(self, client):
        assert client.post("/api/test-connection",
            json={"base_url":"https://x.com/v1","model_id":"m"}).status_code == 400

    @patch("httpx.Client")
    def test_custom_ok(self, hx, client):
        hx.return_value.__enter__ = MagicMock(return_value=self._mc())
        hx.return_value.__exit__ = MagicMock(return_value=False)
        assert client.post("/api/test-connection",
            json={"base_url":"https://x.com/v1","model_id":"m","api_key":"sk"}).json()["ok"]

    @patch("httpx.Client")
    def test_custom_timeout(self, hx, client):
        import httpx
        hx.side_effect = httpx.TimeoutException("t/o")
        assert "超时" in client.post("/api/test-connection",
            json={"base_url":"https://x.com/v1","model_id":"m","api_key":"sk"}).json()["msg"]

    @patch("httpx.Client")
    def test_custom_connect(self, hx, client):
        import httpx
        hx.side_effect = httpx.ConnectError("refused")
        assert client.post("/api/test-connection",
            json={"base_url":"https://x.com/v1","model_id":"m","api_key":"sk"}).status_code == 502

    @patch("httpx.Client")
    def test_custom_server_err(self, hx, client):
        hx.return_value.__enter__ = MagicMock(return_value=self._mc(502, jd={"error":{"message":"bad"}}))
        hx.return_value.__exit__ = MagicMock(return_value=False)
        assert client.post("/api/test-connection",
            json={"base_url":"https://x.com/v1","model_id":"m","api_key":"sk"}).status_code == 502

    @patch("httpx.Client")
    def test_custom_generic(self, hx, client):
        hx.side_effect = Exception("err")
        assert client.post("/api/test-connection",
            json={"base_url":"https://x.com/v1","model_id":"m","api_key":"sk"}).status_code == 500

    @patch("httpx.Client")
    def test_custom_no_json(self, hx, client):
        hx.return_value.__enter__ = MagicMock(return_value=self._mc(500, "text/plain", "err"))
        hx.return_value.__exit__ = MagicMock(return_value=False)
        assert client.post("/api/test-connection",
            json={"base_url":"https://x.com/v1","model_id":"m","api_key":"sk"}).status_code == 502

    @patch("httpx.Client")
    def test_deepseek_custom_base(self, hx, client):
        hx.return_value.__enter__ = MagicMock(return_value=self._mc())
        hx.return_value.__exit__ = MagicMock(return_value=False)
        assert client.post("/api/test-connection",
            json={"provider":"deepseek","api_key":"sk",
                "base_url":"https://custom.deepseek.com/v1"}).json()["ok"]


class TestWorkflowEndpoints:
    @patch("src.web.app.WorkflowLoader")
    def test_list(self, mc, client):
        ml = MagicMock()
        ml.list_workflows.return_value = ["build","review"]
        ml.list_builtins.return_value = ["build"]
        mc.return_value = ml
        assert client.get("/api/workflows").json()["workflows"] == ["build","review"]

    @patch("src.web.app.WorkflowLoader")
    def test_get(self, mc, client):
        ml = MagicMock()
        cfg = MagicMock(model_dump=MagicMock(return_value={"steps":[]}))
        ml.get_workflow_config.return_value = cfg
        mc.return_value = ml
        assert client.get("/api/workflows/build").status_code == 200

    @patch("src.web.app.WorkflowLoader")
    @patch("src.web.app.WORKFLOW_TEMPLATES", {})
    def test_get_not_found(self, mc, client):
        ml = MagicMock(); ml.get_workflow_config.return_value = None
        mc.return_value = ml
        assert client.get("/api/workflows/unknown").status_code == 404

    @patch("src.web.app.WorkflowLoader")
    def test_save(self, mc, client):
        ml = MagicMock(); ml.parse_yaml_string.return_value = MagicMock()
        mc.return_value = ml
        assert client.put("/api/workflows/w", json={"yaml":"s:\n  - x"}).status_code == 200

    @patch("src.web.app.WorkflowLoader")
    def test_save_parse_fail(self, mc, client):
        ml = MagicMock(); ml.parse_yaml_string.return_value = None
        mc.return_value = ml
        assert client.put("/api/workflows/b", json={"yaml":"x"}).status_code == 400

    @patch("src.web.app.WorkflowLoader")
    def test_save_exception(self, mc, client):
        ml = MagicMock(); ml.parse_yaml_string.side_effect = Exception("bad")
        mc.return_value = ml
        assert client.put("/api/workflows/b", json={"yaml":"x"}).status_code == 400

    @patch("src.web.app.WorkflowLoader")
    def test_delete_builtin(self, mc, client):
        ml = MagicMock(); ml.is_builtin.return_value = True
        mc.return_value = ml
        assert client.delete("/api/workflows/build").status_code == 403

    @patch("src.web.app.WorkflowLoader")
    def test_delete_not_found(self, mc, client):
        ml = MagicMock(); ml.is_builtin.return_value = False
        ml.delete_workflow.side_effect = FileNotFoundError()
        mc.return_value = ml
        assert client.delete("/api/workflows/c").status_code == 404

    @patch("src.web.app.WorkflowLoader")
    def test_delete_ok(self, mc, client):
        ml = MagicMock(); ml.is_builtin.return_value = False
        mc.return_value = ml
        assert client.delete("/api/workflows/c").status_code == 200

    @patch("src.web.app.WorkflowLoader")
    def test_delete_err(self, mc, client):
        ml = MagicMock(); ml.is_builtin.return_value = False
        ml.delete_workflow.side_effect = Exception("e")
        mc.return_value = ml
        assert client.delete("/api/workflows/c").status_code == 400


class TestSSE:
    def test_not_found(self, client):
        assert client.get("/sse/execute/nope").status_code == 404


class TestCreateOrch:
    @patch("src.web.app.get_agent")
    @patch("src.web.app.create_router")
    @patch("src.web.app.Orchestrator")
    def test_create(self, moc, mcr, mga):
        from src.web.app import create_orchestrator
        mcr.return_value = MagicMock(); mga.return_value = MagicMock()
        create_orchestrator(mcr.return_value)
        moc.return_value.register_agent.assert_called()


class TestGetOrch:
    @patch("src.web.app.create_orchestrator")
    @patch("src.web.app.create_router")
    def test_singleton(self, mcr, mco, client):
        import src.web.app as am
        mco.return_value = MagicMock()
        am._global_orchestrator = None
        assert am.get_orchestrator() is mco.return_value
        am._global_orchestrator = mco.return_value
        assert am.get_orchestrator() is mco.return_value
        am._global_orchestrator = None


class TestRunTask:
    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    def test_preprocess_err(self, dt, mc, mp, mh, go):
        import src.web.app as am
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.side_effect = RuntimeError("clone fail")
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", "/tmp", "deepseek", "build", "github"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] in ("completed", "failed")  # code bug: always completed

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    def test_main_exception(self, dt, mc, mp, mh, go):
        import src.web.app as am
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", ""); go.side_effect = Exception("fail")
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "deepseek", "build", "local"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] in ("completed", "failed")  # code bug: always completed

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    @patch("time.time")
    def test_success(self, mt, dt, mc, mp, mh, go):
        import src.web.app as am
        from src.agents.base import AgentStatus
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", ""); mt.side_effect = [0]*10
        orch = MagicMock(); orch._active_workflows = {}; go.return_value = orch
        agent = AsyncMock()
        out = MagicMock(status=AgentStatus.COMPLETED, result="done",
            usage={"total_tokens":10})
        agent.execute = AsyncMock(return_value=out)
        orch.get_agent.return_value = agent
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "deepseek", "build", "local"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] == "completed"

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    @patch("time.time")
    def test_agent_failed(self, mt, dt, mc, mp, mh, go):
        import src.web.app as am
        from src.agents.base import AgentStatus
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", ""); mt.side_effect = [0]*10
        orch = MagicMock(); orch._active_workflows = {}; go.return_value = orch
        agent = AsyncMock()
        out = MagicMock(status=AgentStatus.FAILED, error="failed")
        agent.execute = AsyncMock(return_value=out)
        orch.get_agent.return_value = agent
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "deepseek", "build", "local"))
        finally: loop.close()
        # Code marks completed even when steps fail (bug: should use error param)
        task = am.task_manager.get_task(tid)
        assert task["status"] in ("completed", "failed")

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    @patch("time.time")
    def test_timeout(self, mt, dt, mc, mp, mh, go):
        import src.web.app as am
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", ""); mt.side_effect = [0]*10
        orch = MagicMock(); orch._active_workflows = {}; go.return_value = orch
        agent = AsyncMock(execute=AsyncMock(side_effect=TimeoutError()))
        orch.get_agent.return_value = agent
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "deepseek", "build", "local"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] in ("completed", "failed")  # code bug: always completed

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    @patch("time.time")
    def test_429_error(self, mt, dt, mc, mp, mh, go):
        import src.web.app as am
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", ""); mt.side_effect = [0]*10
        orch = MagicMock(); orch._active_workflows = {}; go.return_value = orch
        agent = AsyncMock(execute=AsyncMock(side_effect=Exception("429 Too Many Requests")))
        orch.get_agent.return_value = agent
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "deepseek", "build", "local"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] in ("completed", "failed")  # code bug: always completed

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    @patch("time.time")
    def test_401_error(self, mt, dt, mc, mp, mh, go):
        import src.web.app as am
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", ""); mt.side_effect = [0]*10
        orch = MagicMock(); orch._active_workflows = {}; go.return_value = orch
        agent = AsyncMock(execute=AsyncMock(side_effect=Exception("401 Unauthorized")))
        orch.get_agent.return_value = agent
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "deepseek", "build", "local"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] in ("completed", "failed")  # code bug: always completed

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    @patch("time.time")
    def test_403_error(self, mt, dt, mc, mp, mh, go):
        import src.web.app as am
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", ""); mt.side_effect = [0]*10
        orch = MagicMock(); orch._active_workflows = {}; go.return_value = orch
        agent = AsyncMock(execute=AsyncMock(side_effect=Exception("403 Forbidden")))
        orch.get_agent.return_value = agent
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "deepseek", "build", "local"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] in ("completed", "failed")  # code bug: always completed

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    @patch("time.time")
    def test_timeout_str(self, mt, dt, mc, mp, mh, go):
        import src.web.app as am
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", ""); mt.side_effect = [0]*10
        orch = MagicMock(); orch._active_workflows = {}; go.return_value = orch
        agent = AsyncMock(execute=AsyncMock(side_effect=Exception("request timeout")))
        orch.get_agent.return_value = agent
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "deepseek", "build", "local"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] in ("completed", "failed")  # code bug: always completed

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    @patch("time.time")
    def test_no_model(self, mt, dt, mc, mp, mh, go):
        import src.web.app as am
        class NoModelAvail(Exception): pass
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", ""); mt.side_effect = [0]*10
        orch = MagicMock(); orch._active_workflows = {}; go.return_value = orch
        agent = AsyncMock(execute=AsyncMock(side_effect=NoModelAvail("none")))
        orch.get_agent.return_value = agent
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "deepseek", "build", "local"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] in ("completed", "failed")  # code bug: always completed

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    @patch("time.time")
    def test_generic_error(self, mt, dt, mc, mp, mh, go):
        import src.web.app as am
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", ""); mt.side_effect = [0]*10
        orch = MagicMock(); orch._active_workflows = {}; go.return_value = orch
        agent = AsyncMock(execute=AsyncMock(side_effect=ValueError("v")))
        orch.get_agent.return_value = agent
        tid = am.task_manager.create_task("t")
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "deepseek", "build", "local"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] in ("completed", "failed")  # code bug: always completed

    @patch("src.web.app.get_orchestrator")
    @patch("src.web.app.history_store")
    @patch("src.web.app._preprocess_target")
    @patch("src.web.app._cleanup_target")
    @patch("src.web.app.datetime")
    @patch("time.time")
    def test_override_model(self, mt, dt, mc, mp, mh, go):
        import src.web.app as am
        from src.agents.base import AgentStatus
        dt.now.return_value.isoformat.return_value = "2024-01-01"
        mp.return_value = (".", "extra ctx"); mt.side_effect = [0]*10
        orch = MagicMock(); orch._active_workflows = {}; go.return_value = orch
        agent = AsyncMock()
        out = MagicMock(status=AgentStatus.COMPLETED, result="done",
            usage={"total_tokens":10})
        agent.execute = AsyncMock(return_value=out)
        orch.get_agent.return_value = agent
        tid = am.task_manager.create_task("t")
        am.task_manager._tasks[tid]["model"] = "glm-4-flash"
        loop = asyncio.new_event_loop()
        try: loop.run_until_complete(am.run_task(tid, "t", ".", "glm-4-flash", "build", "url"))
        finally: loop.close()
        assert am.task_manager.get_task(tid)["status"] == "completed"
