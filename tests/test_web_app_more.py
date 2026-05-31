"""
tests/test_web_app_more.py
========================
补充测试，覆盖 app.py 中未覆盖的 API endpoints 和辅助函数。

目标覆盖（来自覆盖率报告的 503 行未覆盖）：
  1. GET  /api/tasks              - 列出任务（包含多个 task）
  2. GET  /api/tasks/{task_id}    - 获取单个任务（存在 + 不存在）
  3. DELETE /api/tasks/{task_id}  - 删除任务（存在 + 不存在）
  4. GET  /api/history            - app 层的 /api/history
  5. GET  /api/dashboard/stats    - 仪表盘统计（mock history_store）
  6. GET  /api/dashboard/files    - 仪表盘文件列表
  7. POST /api/open-folder        - 打开文件夹（多种系统）
  8. POST /api/save-report        - 保存报告（内存 + 历史记录）
  9. GET  /api/config              - 获取配置
 10. GET  /api/coverage           - 获取覆盖率
 11. POST /api/coverage/run        - 运行覆盖率
 12. GET  /health                 - 健康检查
 13. GET  /                        - 首页 HTML
 14. GET  /history                - 历史页面
 15. GET  /settings               - 设置页面
 16. GET  /coverage               - 覆盖率页面
 17. GET  /docs                   - 文档页面
 18. _detect_target_type()        - 完整边界测试
 19. _preprocess_target()          - 完整场景（git clone 成功、URL 截断等）
 20. _cleanup_target()             - 完整场景
"""

# ---------------------------------------------------------------------------
# Import — 必须放在 sys.path.insert 之后（与 app.py 内部逻辑一致）
# ---------------------------------------------------------------------------
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web.app import (
    _cleanup_target,
    _detect_target_type,
    _mask_key,
    _preprocess_target,
    app,
    task_manager,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_task_manager():
    """每个测试前后重置 task_manager，避免状态泄漏"""
    task_manager._tasks.clear()
    task_manager._queues.clear()
    yield
    task_manager._tasks.clear()
    task_manager._queues.clear()


# ---------------------------------------------------------------------------
# Helper Function Tests
# ---------------------------------------------------------------------------

class TestDetectTargetType:
    """_detect_target_type — 完整边界测试"""

    @pytest.mark.parametrize(
        "target, expected",
        [
            # 空字符串 → local
            ("", "local"),
            # 空白 → local
            ("   ", "local"),
            # 本地路径
            ("/tmp/my-project", "local"),
            ("/home/user/repo", "local"),
            ("./relative/path", "local"),
            # GitHub HTTPS
            ("https://github.com/user/repo", "github"),
            ("https://www.github.com/user/repo", "github"),
            ("https://github.com/user/repo.git", "github"),
            ("https://github.com/org/team-repo/", "github"),
            # Git SSH
            ("git@github.com:user/repo.git", "github"),
            ("git@github.com:org/team-repo.git", "github"),
            # 普通 URL（非 GitHub）
            ("https://example.com/path", "url"),
            ("http://example.com", "url"),
            ("https://gitlab.com/user/repo", "url"),
            ("https://internal.company.com/repo", "url"),
            # 用户名/仓库名（不应误判）
            ("user/repo", "local"),
            ("my-awesome-project", "local"),
        ],
    )
    def test_detect_target_type(self, target, expected):
        assert _detect_target_type(target) == expected

    def test_github_url_without_dotgit(self):
        """GitHub HTTPS URL 不带 .git 后缀 → github"""
        assert _detect_target_type("https://github.com/owner/project") == "github"


class TestPreprocessTarget:
    """_preprocess_target — 完整场景覆盖"""

    def test_local_path(self):
        """本地路径：直接返回原路径"""
        result = _preprocess_target("/tmp/myproject", "local", "abcd1234")
        assert result == ("/tmp/myproject", "")

    def test_local_empty_path(self):
        """空路径 → ('.', '')"""
        result = _preprocess_target("", "local", "abcd1234")
        assert result == (".", "")
        result = _preprocess_target("   ", "local", "abcd1234")
        assert result == (".", "")

    @patch("subprocess.run")
    def test_github_clone_success(self, mock_run):
        """GitHub clone 成功：返回临时目录路径"""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tempfile.mkdtemp", return_value=tmpdir):
                path, extra = _preprocess_target(
                    "https://github.com/user/repo", "github", "abcd1234"
                )

        assert path == tmpdir
        assert "GitHub" in extra
        assert "user/repo" in extra
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "clone" in call_args

    @patch("subprocess.run")
    def test_github_clone_failure(self, mock_run):
        """GitHub clone 失败：抛出 RuntimeError"""
        mock_run.return_value = MagicMock(returncode=1, stderr="Authentication failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tempfile.mkdtemp", return_value=tmpdir):
                with pytest.raises(RuntimeError, match="git clone 失败"):
                    _preprocess_target(
                        "https://github.com/user/repo", "github", "abcd1234"
                    )

    @patch("subprocess.run")
    def test_github_clone_url_normalization(self, mock_run):
        """GitHub HTTPS URL 自动补 .git"""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tempfile.mkdtemp", return_value=tmpdir):
                _preprocess_target("https://github.com/user/repo", "github", "abcd1234")

        call_args = mock_run.call_args[0][0]
        # Find the URL argument (starts with http:// or https://)
        clone_url = next(
            a for a in call_args
            if a.startswith(("https://", "http://", "git@"))
        )
        assert clone_url.endswith(".git"), f"Expected URL ending with .git, got: {clone_url}"

    @patch("subprocess.run")
    def test_github_subprocess_exception(self, mock_run):
        """subprocess.run 抛出异常（如 git 命令不存在）"""
        mock_run.side_effect = FileNotFoundError("git not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tempfile.mkdtemp", return_value=tmpdir):
                with pytest.raises(FileNotFoundError):
                    _preprocess_target(
                        "https://github.com/user/repo", "github", "abcd1234"
                    )

    @patch("requests.get")
    def test_url_fetch_success(self, mock_get):
        """URL fetch 成功：去除 HTML 标签"""
        mock_resp = MagicMock()
        mock_resp.text = (
            "<html><head><style>body{}</style></head>"
            "<body><h1>Hello</h1><p>World</p></body></html>"
        )
        mock_get.return_value = mock_resp

        path, extra = _preprocess_target("https://example.com", "url", "abcd1234")

        assert path == "."
        assert "网页内容" in extra
        assert "Hello" in extra
        assert "World" in extra
        # script/style 不应在内容中
        assert "<script" not in extra

    @patch("requests.get")
    def test_url_fetch_content_truncated(self, mock_get):
        """URL fetch 长度超过 8000 字符时截断"""
        long_text = "<html><body>" + "x" * 10000 + "</body></html>"
        mock_resp = MagicMock()
        mock_resp.text = long_text
        mock_get.return_value = mock_resp

        path, extra = _preprocess_target("https://example.com", "url", "abcd1234")

        assert len(extra) < 9000
        assert "截断" in extra or len(extra) < len(long_text) + 200

    @patch("requests.get")
    def test_url_fetch_network_failure(self, mock_get):
        """URL fetch 网络失败"""
        mock_get.side_effect = Exception("Network unreachable")

        with pytest.raises(RuntimeError, match="获取网页失败"):
            _preprocess_target("https://example.com", "url", "abcd1234")


class TestCleanupTarget:
    """_cleanup_target — 完整场景"""

    @patch("shutil.rmtree")
    def test_cleanup_github_temp_dir(self, mock_rmtree):
        """target_type=github 且路径在 tempgettempdir() 下 → 删除"""
        tmpdir = tempfile.gettempdir() + "/omc-gh-abcd-test"
        _cleanup_target(tmpdir, "github")
        mock_rmtree.assert_called_once_with(tmpdir, ignore_errors=True)

    @patch("shutil.rmtree")
    def test_cleanup_non_temp_dir(self, mock_rmtree):
        """不在临时目录不下删除"""
        _cleanup_target("/home/user/project", "github")
        mock_rmtree.assert_not_called()

    @patch("shutil.rmtree")
    def test_cleanup_local_type(self, mock_rmtree):
        """target_type=local 不触发删除"""
        _cleanup_target("/tmp/somepath", "local")
        mock_rmtree.assert_not_called()

    @patch("shutil.rmtree")
    def test_cleanup_url_type(self, mock_rmtree):
        """target_type=url 不触发删除"""
        _cleanup_target("/tmp/somepath", "url")
        mock_rmtree.assert_not_called()


# ---------------------------------------------------------------------------
# Task Manager API
# ---------------------------------------------------------------------------

class TestTasksAPI:
    """GET /api/tasks, GET /api/tasks/{id}, DELETE /api/tasks/{id}"""

    def test_list_tasks_empty(self, client):
        """空任务列表"""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert data["tasks"] == []

    def test_list_tasks_with_tasks(self, client):
        """创建多个任务后列出"""
        tid1 = task_manager.create_task(task_desc="Task 1", model="deepseek")
        tid2 = task_manager.create_task(task_desc="Task 2", model="deepseek")

        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        ids = [t["task_id"] for t in data["tasks"]]
        assert tid1 in ids
        assert tid2 in ids

    def test_get_task_not_found(self, client):
        """获取不存在的任务 → 404"""
        response = client.get("/api/tasks/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_task_found(self, client):
        """获取存在的任务"""
        tid = task_manager.create_task(task_desc="My Task", model="deepseek")
        task_manager._tasks[tid]["status"] = "running"

        response = client.get(f"/api/tasks/{tid}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == tid
        assert data["task"] == "My Task"

    @patch("src.web.app.verify_api_token", return_value="token")
    def test_delete_task_not_found(self, mock_verify, client):
        """删除不存在的任务 → 404"""
        response = client.delete("/api/tasks/nonexistent-id")
        assert response.status_code == 404

    @patch("src.web.app.verify_api_token", return_value="token")
    def test_delete_task_found(self, mock_verify, client):
        """删除存在的任务"""
        tid = task_manager.create_task()

        response = client.delete(f"/api/tasks/{tid}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        # 再次获取应该 404
        assert client.get(f"/api/tasks/{tid}").status_code == 404


# ---------------------------------------------------------------------------
# API History
# ---------------------------------------------------------------------------

class TestAPIHistory:
    """GET /api/history (app 层的端点)"""

    def test_api_history_empty(self, client):
        """无任务时返回空列表"""
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data

    @patch("src.web.history_api.history_store")
    def test_api_history_sorted_by_started_at(self, mock_store, client):
        """记录按 started_at 降序排序（最新的在前）"""
        # 模拟 history_store 返回两条不同 started_at 的记录（降序）
        mock_store.list_all.return_value = [
            {"task_id": "new-tid", "started_at": "2026-01-02T00:00:00"},
            {"task_id": "old-tid", "started_at": "2026-01-01T00:00:00"},
        ]
        mock_store.get_stats.return_value = {"total_tasks": 2}

        response = client.get("/api/history")
        assert response.status_code == 200
        records = response.json()["records"]
        assert isinstance(records, list)
        assert len(records) == 2

        # 验证降序（started_at 最新的在前）
        started_ats = [r["started_at"] for r in records]
        assert started_ats == sorted(started_ats, reverse=True), \
            f"Expected desc order, got: {started_ats}"


# ---------------------------------------------------------------------------
# Dashboard API
# ---------------------------------------------------------------------------

class TestDashboardStats:
    """GET /api/dashboard/stats"""

    @patch("src.web.dashboard_api._get_real_stats")
    def test_dashboard_stats_with_data(self, mock_real_stats, client):
        """mock _get_real_stats 返回数据"""
        from dataclasses import dataclass

        @dataclass
        class FakeStats:
            total_tasks: int = 10
            completed_tasks: int = 8
            running_tasks: int = 0
            failed_tasks: int = 2
            success_rate: float = 80.0
            avg_execution_time: float = 30.0
            total_tokens: int = 50000
            period_days: int = 7

        mock_real_stats.return_value = FakeStats()
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 10
        assert data["completed_tasks"] == 8
        assert data["success_rate"] == 80.0


class TestDashboardFiles:
    """GET /api/dashboard/files"""

    @patch("src.web.app.history_store")
    def test_dashboard_files_with_mock_project(self, mock_store, client):
        """模拟项目目录"""
        mock_store.list_all.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file_a.txt").write_text("content")
            (Path(tmpdir) / "file_b.py").write_text("print('hi')")

            with patch("src.web.app.project_root", Path(tmpdir)):
                response = client.get("/api/dashboard/files")

        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert "project_path" in data
        assert isinstance(data["files"], list)
        assert len(data["files"]) >= 2

    @patch("src.web.app.history_store")
    def test_dashboard_files_filters_hidden(self, mock_store, client):
        """隐藏文件（.开头）不包含在结果中"""
        mock_store.list_all.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "visible.txt").write_text("ok")
            (Path(tmpdir) / ".hidden").write_text("hidden")

            with patch("src.web.app.project_root", Path(tmpdir)):
                response = client.get("/api/dashboard/files")

        names = [f["name"] for f in response.json()["files"]]
        assert ".hidden" not in names


# ---------------------------------------------------------------------------
# Open Folder
# ---------------------------------------------------------------------------

class TestOpenFolder:
    """POST /api/open-folder"""

    def test_open_folder_missing_payload(self, client):
        """无 payload → 422/400"""
        response = client.post("/api/open-folder")
        # TestClient sends {} when no json= provided
        assert response.status_code in (400, 422)

    def test_open_folder_missing_path(self, client):
        """payload 无 path 字段 → 400"""
        response = client.post("/api/open-folder", json={})
        assert response.status_code == 400
        assert "path" in response.json()["detail"].lower()

    @patch("platform.system", return_value="Darwin")
    @patch("subprocess.run")
    def test_open_folder_darwin(self, mock_run, mock_sys, client):
        """macOS 上调用 open 命令"""
        response = client.post("/api/open-folder", json={"path": "/tmp"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        mock_run.assert_called_once()
        assert "open" in mock_run.call_args[0][0]

    @patch("platform.system", return_value="Windows")
    @patch("subprocess.run")
    def test_open_folder_windows(self, mock_run, mock_sys, client):
        """Windows 上调用 explorer 命令"""
        response = client.post("/api/open-folder", json={"path": "C:\\Temp"})
        assert response.status_code == 200
        mock_run.assert_called_once()
        assert "explorer" in mock_run.call_args[0][0]

    @patch("platform.system", return_value="Linux")
    @patch("subprocess.run")
    def test_open_folder_linux(self, mock_run, mock_sys, client):
        """Linux 上调用 xdg-open 命令"""
        response = client.post("/api/open-folder", json={"path": "/home/user"})
        assert response.status_code == 200
        mock_run.assert_called_once()
        assert "xdg-open" in mock_run.call_args[0][0]

    @patch("platform.system", return_value="Darwin")
    @patch("subprocess.run")
    def test_open_folder_subprocess_error(self, mock_run, mock_sys, client):
        """subprocess 报错 → 返回 500"""
        mock_run.side_effect = Exception("Command failed")

        response = client.post("/api/open-folder", json={"path": "/tmp"})
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"


# ---------------------------------------------------------------------------
# Save Report
# ---------------------------------------------------------------------------

class TestSaveReport:
    """POST /api/save-report"""

    def test_save_report_no_payload(self, client):
        """无 payload → 422"""
        response = client.post("/api/save-report")
        assert response.status_code in (400, 422)

    def test_save_report_missing_task_id(self, client):
        """无 task_id → 400"""
        response = client.post("/api/save-report", json={})
        assert response.status_code == 400
        assert "task_id" in response.json()["detail"].lower()

    def test_save_report_task_not_found(self, client):
        """task_id 不存在于内存和历史记录 → 404"""
        response = client.post("/api/save-report", json={"task_id": "no-such-task"})
        assert response.status_code == 404

    def test_save_report_from_memory_task(self, client):
        """从内存 task_manager 读取任务并保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tid = task_manager.create_task(
                task_desc="Build feature X",
                model="deepseek",
                workflow="build",
                project_path="/tmp",
            )
            task_manager._tasks[tid].update({
                "started_at": "2026-05-28T10:00:00",
                "status": "completed",
                "stats": {
                    "total_tokens": 1000,
                    "execution_time": 5.0,
                    "total_cost": 0.02,
                    "steps_completed": ["explore"],
                    "steps_failed": [],
                },
                "result": {
                    "summary": "Done",
                    "outputs": {
                        "explore": {
                            "result": "Explored the codebase"
                        }
                    },
                },
            })

            with patch("src.web.app.Path.home", return_value=Path(tmpdir)):
                response = client.post("/api/save-report", json={"task_id": tid})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "saved"
            assert "path" in data
            # 验证文件确实写入了
            filepath = Path(data["path"])
            assert filepath.exists()
            content = filepath.read_text(encoding="utf-8")
            assert "Build feature X" in content
            assert "completed" in content.lower()

    @patch("src.web.app.history_store")
    def test_save_report_from_history_store(self, mock_store, client):
        """从 history_store 读取任务并保存"""
        mock_store.load.return_value = {
            "task_id": "task-abc",
            "task": "Review code",
            "status": "completed",
            "started_at": "2026-05-28T10:00:00",
            "model": "deepseek",
            "workflow": "review",
            "project_path": "/tmp",
            "stats": {
                "total_tokens": 2000,
                "execution_time": 8.0,
                "total_cost": 0.04,
                "steps_completed": ["analyst"],
                "steps_failed": [],
            },
            "result": {
                "summary": "Review complete",
                "outputs": {},
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.web.app.Path.home", return_value=Path(tmpdir)):
                response = client.post("/api/save-report", json={"task_id": "task-abc"})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "saved"


# ---------------------------------------------------------------------------
# Config API
# ---------------------------------------------------------------------------

class TestConfigAPI:
    """GET /api/config"""

    def test_get_config_models_and_workflows(self, client):
        """配置端点返回 models、workflows、agents"""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "workflows" in data
        assert "agents" in data
        assert isinstance(data["models"], list)
        assert isinstance(data["workflows"], list)
        assert isinstance(data["agents"], list)
        # 常用模型应该存在
        assert "deepseek" in data["models"]
        # 工作流应该包含 build
        assert "build" in data["workflows"]


# ---------------------------------------------------------------------------
# Coverage API
# ---------------------------------------------------------------------------

class TestCoverageAPI:
    """GET /api/coverage 和 POST /api/coverage/run"""

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_get_coverage_success(self, mock_format, mock_run, client):
        """覆盖率获取成功"""
        mock_run.return_value = MagicMock()
        mock_format.return_value = {
            "overall": {"coverage": 75, "color": "#22c55e"}
        }

        response = client.get("/api/coverage")
        assert response.status_code == 200
        data = response.json()
        assert data["overall"]["coverage"] == 75

    @patch("src.web.app.run_coverage_analysis")
    def test_get_coverage_error(self, mock_run, client):
        """覆盖率分析失败 → 500"""
        mock_run.side_effect = RuntimeError("No data")

        response = client.get("/api/coverage")
        assert response.status_code == 500
        assert "error" in response.json()

    @patch("src.web.app.run_coverage_analysis")
    @patch("src.web.app.format_coverage_report")
    def test_run_coverage_success(self, mock_format, mock_run, client):
        """重新运行覆盖率成功"""
        mock_run.return_value = MagicMock()
        mock_format.return_value = {
            "overall": {"coverage": 80, "color": "#22c55e"}
        }

        response = client.post("/api/coverage/run")
        assert response.status_code == 200
        data = response.json()
        assert data["overall"]["coverage"] == 80

    @patch("src.web.app.run_coverage_analysis")
    def test_run_coverage_error(self, mock_run, client):
        """重新运行覆盖率失败 → 500"""
        mock_run.side_effect = Exception("Coverage error")

        response = client.post("/api/coverage/run")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """GET /health"""

    def test_health_check_response(self, client):
        """健康检查返回 healthy 状态"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    def test_health_check_json(self, client):
        """返回 JSON 格式"""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# Page Routes — HTML 响应
# ---------------------------------------------------------------------------

class TestPageRoutes:
    """GET /, /history, /settings, /coverage, /docs"""

    @pytest.mark.parametrize(
        "path",
        [
            "/",
            "/history",
            "/settings",
            "/coverage",
            "/docs",
        ],
    )
    def test_page_returns_html(self, client, path):
        """所有页面路由返回 HTML"""
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_favicon_returns_svg(self, client):
        """GET /favicon.ico 返回 SVG"""
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        # app.py 返回的 content-type 是 image/svg+xml
        assert "svg" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# Mask Key Utility
# ---------------------------------------------------------------------------

class TestMaskKey:
    """_mask_key 脱敏测试"""

    @pytest.mark.parametrize(
        "key, expected",
        [
            ("", ""),
            ("abc", "abc"),           # 太短不脱敏
            ("sk-12345678", "*******5678"),
            ("sk-long-api-key-abcdefgh", "********************efgh"),
            ("abcd", "abcd"),          # 正好4位不脱敏
        ],
    )
    def test_mask_key(self, key, expected):
        assert _mask_key(key) == expected
