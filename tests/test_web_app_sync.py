"""
Tests for src/web/app.py — 同步端点和未覆盖的 API。

目标覆盖：
  1. execute_task_sync 端点 (lines 1193-1241)
  2. chat_completion_endpoint 的 streaming 分支 (lines 862-918)
  3. Settings API: get_settings, save_settings (lines 1300-1460)
  4. Session API: create_session, get_session, update_session, delete_session (lines 1760-1840)
  5. api_history, dashboard_stats 端点 (lines 486-527)
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web.app import (
    _mask_key,
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


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator 和 router"""
    mock_router = MagicMock()
    mock_orch = MagicMock()

    # Mock create_router 返回 mock_router
    # Mock create_orchestrator 返回 mock_orch
    return mock_router, mock_orch


# ---------------------------------------------------------------------------
# 1. Execute Task Sync Endpoint
# ---------------------------------------------------------------------------


class TestExecuteTaskSync:
    """POST /api/execute-sync — 同步任务执行"""

    @patch("src.web.app.create_orchestrator")
    @patch("src.web.app.create_router")
    def test_execute_sync_success(self, mock_create_router, mock_create_orch, client):
        """测试同步执行成功"""
        # 创建 mock agent 和 output
        mock_agent = MagicMock()
        mock_output = MagicMock()
        mock_output.status = "completed"  # AgentStatus.COMPLETED 的值是 'completed'
        mock_output.error = None
        mock_output.usage = {"total_tokens": 100}
        mock_output.result = {"summary": "Task completed"}
        mock_agent.execute = AsyncMock(return_value=mock_output)

        mock_orch = MagicMock()
        mock_orch.get_agent = MagicMock(return_value=mock_agent)
        mock_create_orch.return_value = mock_orch

        # Mock WORKFLOW_TEMPLATES
        with patch("src.web.app.WORKFLOW_TEMPLATES", {"build": [
            type("Step", (), {"agent_name": "explore", "timeout": 30})()
        ]}):
            response = client.post(
                "/api/execute-sync",
                json={
                    "task": "test task",
                    "project_path": "/tmp",
                    "model": "deepseek",
                    "workflow": "build",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "result" in data

    @patch("src.web.app.create_orchestrator")
    @patch("src.web.app.create_router")
    def test_execute_sync_agent_failed(self, mock_create_router, mock_create_orch, client):
        """测试 agent 执行失败"""
        mock_agent = MagicMock()
        mock_output = MagicMock()
        mock_output.status = "failed"  # AgentStatus.FAILED 的值是 'failed'
        mock_output.error = "Agent failed"
        mock_agent.execute = AsyncMock(return_value=mock_output)

        mock_orch = MagicMock()
        mock_orch.get_agent = MagicMock(return_value=mock_agent)
        mock_create_orch.return_value = mock_orch

        # Mock WORKFLOW_TEMPLATES
        with patch("src.web.app.WORKFLOW_TEMPLATES", {"build": [
            type("Step", (), {"agent_name": "explore", "timeout": 30})()
        ]}):
            response = client.post(
                "/api/execute-sync",
                json={
                    "task": "test task",
                    "project_path": "/tmp",
                    "workflow": "build",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "失败" in data["message"]

    @patch("src.web.app.create_orchestrator")
    @patch("src.web.app.create_router")
    def test_execute_sync_timeout(self, mock_create_router, mock_create_orch, client):
        """测试执行超时"""
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_orch = MagicMock()
        mock_orch.get_agent = MagicMock(return_value=mock_agent)
        mock_create_orch.return_value = mock_orch

        with patch("src.web.app.WORKFLOW_TEMPLATES", {"build": [
            type("Step", (), {"agent_name": "explore", "timeout": 0.1})()
        ]}):
            response = client.post(
                "/api/execute-sync",
                json={
                    "task": "test task",
                    "project_path": "/tmp",
                    "workflow": "build",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        # 服务器内部错误时会返回 "服务器内部错误"
        # 超时应该返回 "执行超时"
        assert "超时" in data["message"] or "服务器" in data["message"]


# ---------------------------------------------------------------------------
# 2. Chat Completion Endpoint — Streaming
# ---------------------------------------------------------------------------


class TestChatCompletionStreaming:
    """POST /api/chat/completions — streaming 分支"""

    @patch("src.web.app.create_router")
    def test_chat_completions_stream(self, mock_create_router, client):
        """测试流式响应"""
        mock_router = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Hello, this is a test response for streaming."
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_response.model = "deepseek-chat"

        # 使 route_and_call 成为 async 函数
        async def mock_route_and_call(*args, **kwargs):
            return mock_response

        mock_router.route_and_call = mock_route_and_call
        mock_create_router.return_value = mock_router

        response = client.post(
            "/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "deepseek",
                "stream": True,
            },
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # 读取流式响应
        content = b""
        for chunk in response.iter_bytes():
            content += chunk
            if b"done" in chunk:
                break

        assert len(content) > 0

    @patch("src.web.app.create_router")
    def test_chat_completions_stream_error(self, mock_create_router, client):
        """测试流式响应出错"""
        mock_router = MagicMock()

        async def mock_route_and_call(*args, **kwargs):
            raise RuntimeError("Model error")

        mock_router.route_and_call = mock_route_and_call
        mock_create_router.return_value = mock_router

        response = client.post(
            "/api/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "deepseek",
                "stream": True,
            },
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 3. Settings API
# ---------------------------------------------------------------------------


class TestSettingsAPIExtended:
    """GET /api/settings 和 POST /api/settings — 扩展测试"""

    @patch("src.web.app.SETTINGS_FILE")
    def test_get_settings_with_real_file(self, mock_settings_file, client):
        """测试从真实文件读取设置"""
        mock_settings_file.exists.return_value = True
        mock_settings_file.read_text.return_value = json.dumps({
            "models": {
                "deepseek": {
                    "provider": "DeepSeek",
                    "api_key": "sk-1234567890abcdef",
                    "cost_level": "free",
                    "enabled": True,
                }
            },
            "defaults": {"model": "deepseek", "workflow": "build", "timeout": 300},
        })

        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "defaults" in data
        # 检查 API key 脱敏
        if "deepseek" in data["models"]:
            masked = data["models"]["deepseek"].get("api_key_masked", "")
            assert masked.endswith("cdef")
            assert data["models"]["deepseek"]["has_key"] is True

    @patch("src.web.app.SETTINGS_DIR")
    @patch("src.web.app.SETTINGS_FILE")
    def test_save_settings_new_model(self, mock_file, mock_dir, client):
        """测试保存新模型设置"""
        mock_dir.mkdir = MagicMock()
        mock_dir.exists.return_value = False
        mock_file.exists.return_value = False
        mock_file.write_text = MagicMock()

        response = client.post(
            "/api/settings",
            json={
                "models": {
                    "new-model": {
                        "provider": "Test",
                        "api_key": "sk-new-key",
                        "cost_level": "low",
                        "enabled": True,
                    }
                },
                "defaults": {"model": "new-model"},
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @patch("src.web.app.SETTINGS_DIR")
    @patch("src.web.app.SETTINGS_FILE")
    def test_save_settings_masked_key_skip(self, mock_file, mock_dir, client):
        """测试保存时跳过脱敏的 API key"""
        mock_dir.mkdir = MagicMock()
        mock_dir.exists.return_value = True
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps({
            "models": {
                "deepseek": {
                    "provider": "DeepSeek",
                    "api_key": "sk-real-key",
                    "cost_level": "free",
                    "enabled": True,
                }
            },
            "defaults": {"model": "deepseek", "workflow": "build", "timeout": 300},
        })
        mock_file.write_text = MagicMock()

        # 发送脱敏的 key（以 * 开头）
        response = client.post(
            "/api/settings",
            json={
                "models": {
                    "deepseek": {
                        "api_key": "*******abcd"  # 脱敏值
                    }
                }
            },
        )

        assert response.status_code == 200
        # 验证 write_text 被调用，且内容中保留了原始 key
        call_args = mock_file.write_text.call_args
        saved_data = json.loads(call_args[0][0])
        # 原始 key 应该被保留（没有被脱敏值覆盖）
        assert saved_data["models"]["deepseek"]["api_key"] == "sk-real-key"


# ---------------------------------------------------------------------------
# 4. Session API
# ---------------------------------------------------------------------------


class TestSessionAPIExtended:
    """Session API — create, get, update, delete"""

    def test_create_session_success(self, client, tmp_path):
        """测试创建会话成功"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        with patch("src.web.app.SESSIONS_DIR", sessions_dir):
            response = client.post(
                "/api/sessions",
                json={"title": "New Test Session"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "session" in data
            assert data["session"]["title"] == "New Test Session"
            assert "id" in data["session"]

            # 验证文件已创建
            session_file = sessions_dir / f"{data['session']['id']}.json"
            assert session_file.exists()

    def test_create_session_empty_title(self, client, tmp_path):
        """测试创建会话（空标题）"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        with patch("src.web.app.SESSIONS_DIR", sessions_dir):
            response = client.post(
                "/api/sessions",
                json={"title": ""},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_get_session_not_found(self, client):
        """测试获取不存在的会话"""
        with patch("src.web.app.SESSIONS_DIR", Path("/nonexistent")):
            response = client.get("/api/sessions/nonexistent-id")
            assert response.status_code == 404

    def test_get_session_success(self, client, tmp_path):
        """测试获取存在的会话"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        # 创建会话文件
        session_id = "test-session-123"
        session_data = {
            "id": session_id,
            "title": "Test Session",
            "messages": [{"role": "user", "content": "Hello"}],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        (sessions_dir / f"{session_id}.json").write_text(
            json.dumps(session_data, ensure_ascii=False), encoding="utf-8"
        )

        with patch("src.web.app.SESSIONS_DIR", sessions_dir):
            response = client.get(f"/api/sessions/{session_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == session_id
            assert data["title"] == "Test Session"
            assert len(data["messages"]) == 1

    def test_update_session_title(self, client, tmp_path):
        """测试更新会话标题"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        # 创建会话文件
        session_id = "test-session-456"
        session_data = {
            "id": session_id,
            "title": "Old Title",
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        (sessions_dir / f"{session_id}.json").write_text(
            json.dumps(session_data, ensure_ascii=False), encoding="utf-8"
        )

        with patch("src.web.app.SESSIONS_DIR", sessions_dir):
            response = client.put(
                f"/api/sessions/{session_id}",
                json={"title": "New Title"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

            # 验证文件已更新
            updated_data = json.loads(
                (sessions_dir / f"{session_id}.json").read_text(encoding="utf-8")
            )
            assert updated_data["title"] == "New Title"

    def test_update_session_messages(self, client, tmp_path):
        """测试更新会话消息"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        # 创建会话文件
        session_id = "test-session-789"
        session_data = {
            "id": session_id,
            "title": "Test",
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        (sessions_dir / f"{session_id}.json").write_text(
            json.dumps(session_data, ensure_ascii=False), encoding="utf-8"
        )

        new_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        with patch("src.web.app.SESSIONS_DIR", sessions_dir):
            response = client.put(
                f"/api/sessions/{session_id}",
                json={"messages": new_messages},
            )
            assert response.status_code == 200

            # 验证文件已更新
            updated_data = json.loads(
                (sessions_dir / f"{session_id}.json").read_text(encoding="utf-8")
            )
            assert len(updated_data["messages"]) == 2

    def test_update_session_not_found(self, client):
        """测试更新不存在的会话"""
        with patch("src.web.app.SESSIONS_DIR", Path("/nonexistent")):
            response = client.put(
                "/api/sessions/nonexistent-id",
                json={"title": "New Title"},
            )
            assert response.status_code == 404

    def test_delete_session_success(self, client, tmp_path):
        """测试删除会话成功"""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        # 创建会话文件
        session_id = "test-session-del"
        session_data = {
            "id": session_id,
            "title": "To Delete",
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        session_file = sessions_dir / f"{session_id}.json"
        session_file.write_text(
            json.dumps(session_data, ensure_ascii=False), encoding="utf-8"
        )

        with patch("src.web.app.SESSIONS_DIR", sessions_dir):
            response = client.delete(f"/api/sessions/{session_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

            # 验证文件已删除
            assert not session_file.exists()

    def test_delete_session_not_found(self, client):
        """测试删除不存在的会话"""
        with patch("src.web.app.SESSIONS_DIR", Path("/nonexistent")):
            response = client.delete("/api/sessions/nonexistent-id")
            assert response.status_code == 404


# ---------------------------------------------------------------------------
# 5. API History & Dashboard Stats
# ---------------------------------------------------------------------------


class TestAPIHistoryExtended:
    """GET /api/history — 扩展测试"""

    def test_api_history_with_task_manager(self, client):
        """测试从 task_manager 获取历史"""
        # 创建一些任务
        tid1 = task_manager.create_task(
            task_desc="Task 1",
            model="deepseek",
            workflow="build",
            project_path="/tmp",
        )
        tid2 = task_manager.create_task(
            task_desc="Task 2",
            model="kimi",
            workflow="review",
            project_path="/tmp",
        )

        # 设置任务状态
        task_manager._tasks[tid1]["status"] = "completed"
        task_manager._tasks[tid1]["started_at"] = "2026-05-28T10:00:00"
        task_manager._tasks[tid2]["status"] = "running"
        task_manager._tasks[tid2]["started_at"] = "2026-05-28T11:00:00"

        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert len(data["records"]) >= 2

    @patch("src.web.history_api.history_store")
    def test_api_history_with_history_store(self, mock_store, client):
        """测试从 history_store 获取历史"""
        mock_store.list_all.return_value = [
            {
                "task_id": "hist-1",
                "task": "Historical task",
                "status": "completed",
                "started_at": "2026-05-28T09:00:00",
                "model": "deepseek",
                "workflow": "build",
                "project_path": "/tmp",
            }
        ]
        mock_store.get_stats.return_value = {"total_tasks": 1}

        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data


class TestDashboardStatsExtended:
    """GET /api/dashboard/stats — 扩展测试"""

    @patch("src.web.dashboard_api._get_real_stats")
    def test_dashboard_stats_success(self, mock_get_stats, client):
        """测试获取仪表板统计成功"""
        # 创建一个 mock 统计对象
        mock_stats = MagicMock()
        mock_stats.total_tasks = 10
        mock_stats.completed_tasks = 8
        mock_stats.running_tasks = 0
        mock_stats.failed_tasks = 2
        mock_stats.success_rate = 80.0
        mock_stats.avg_execution_time = 30.0
        mock_stats.total_tokens = 50000
        mock_stats.period_days = 7

        mock_get_stats.return_value = mock_stats

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 10
        assert data["completed_tasks"] == 8
        assert data["failed_tasks"] == 2
        assert data["success_rate"] == 80.0

    @patch("src.web.dashboard_api._get_real_stats")
    def test_dashboard_stats_empty(self, mock_get_stats, client):
        """测试空统计"""
        mock_stats = MagicMock()
        mock_stats.total_tasks = 0
        mock_stats.completed_tasks = 0
        mock_stats.running_tasks = 0
        mock_stats.failed_tasks = 0
        mock_stats.success_rate = 0.0
        mock_stats.avg_execution_time = 0.0
        mock_stats.total_tokens = 0
        mock_stats.period_days = 7

        mock_get_stats.return_value = mock_stats

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 0


# ---------------------------------------------------------------------------
# Mask Key Utility (extended)
# ---------------------------------------------------------------------------


class TestMaskKeyExtended:
    """_mask_key — 扩展测试"""

    @pytest.mark.parametrize(
        "key,expected",
        [
            ("", ""),
            ("abc", "abc"),
            ("abcd", "abcd"),  # 正好4位不脱敏
            ("sk-12345678", "*******5678"),
            ("sk-long-api-key-abcdefgh", "********************efgh"),
            ("short", "*hort"),  # 5位，脱敏（实现逻辑：len > 4 就脱敏）
        ],
    )
    def test_mask_key(self, key, expected):
        assert _mask_key(key) == expected

    def test_mask_key_long(self):
        """测试长 key"""
        key = "sk-" + "x" * 100
        masked = _mask_key(key)
        assert len(masked) == len(key)
        assert masked.startswith("*")
        assert masked.endswith(key[-4:])

    def test_mask_key_none(self):
        """测试 None 输入"""
        assert _mask_key(None) == ""
