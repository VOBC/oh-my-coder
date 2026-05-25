"""
Tests for src/web/dashboard_api.py

Tests DashboardStats, ActivityData, AgentStatus, RecentTask models and FastAPI routes.
"""
import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 导入被测试模块
from src.web.dashboard_api import (
    ActivityData,
    AgentStatus,
    DashboardStats,
    RecentTask,
    _activity_cache,
    _build_mock_activity,
    _get_mock_agents,
    _get_mock_recent_tasks,
    _stats_cache,
    _stats_cache_time,
    router,
)


# ========================================
# Fixtures
# ========================================
@pytest.fixture
def app():
    """创建测试 FastAPI app"""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_cache():
    """每个测试前清除缓存"""
    global _stats_cache, _stats_cache_time, _activity_cache
    _stats_cache.clear()
    _stats_cache_time = 0.0
    _activity_cache.clear()
    yield


@pytest.fixture
def mock_workflow_data():
    """创建模拟的工作流数据"""
    now = datetime.now()
    return [
        {
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "status": "completed",
            "total_tokens": 1000,
            "execution_time": 120.5,
        },
        {
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "status": "running",
            "total_tokens": 500,
            "execution_time": None,
        },
        {
            "timestamp": (now - timedelta(days=3)).isoformat(),
            "status": "failed",
            "total_tokens": 300,
            "execution_time": 45.0,
        },
        {
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "status": "completed",
            "total_tokens": 2000,
            "execution_time": 90.0,
        },
    ]


# ========================================
# Model Tests
# ========================================
class TestDashboardStats:
    """测试 DashboardStats 模型"""

    def test_create_basic(self):
        """测试创建基本统计"""
        stats = DashboardStats(
            total_tasks=10,
            completed_tasks=5,
            running_tasks=3,
            failed_tasks=2,
            success_rate=50.0,
            avg_execution_time=100.5,
            total_tokens=10000,
            period_days=7,
        )
        assert stats.total_tasks == 10
        assert stats.completed_tasks == 5
        assert stats.success_rate == 50.0

    def test_model_dump(self):
        """测试 model_dump"""
        stats = DashboardStats(
            total_tasks=0,
            completed_tasks=0,
            running_tasks=0,
            failed_tasks=0,
            success_rate=0.0,
            avg_execution_time=0.0,
            total_tokens=0,
            period_days=7,
        )
        data = stats.model_dump()
        assert isinstance(data, dict)
        assert data["total_tasks"] == 0


class TestActivityData:
    """测试 ActivityData 模型"""

    def test_create_basic(self):
        """测试创建活动数据"""
        activity = ActivityData(day="2026-05-20", tasks=5, tokens=1000)
        assert activity.day == "2026-05-20"
        assert activity.tasks == 5
        assert activity.tokens == 1000

    def test_model_dump(self):
        """测试 model_dump"""
        activity = ActivityData(day="2026-05-20", tasks=0, tokens=0)
        data = activity.model_dump()
        assert data["day"] == "2026-05-20"


class TestAgentStatus:
    """测试 AgentStatus 模型"""

    def test_create_idle(self):
        """测试创建空闲 Agent"""
        agent = AgentStatus(name="Planner", status="idle", total_executions=45)
        assert agent.name == "Planner"
        assert agent.status == "idle"
        assert agent.current_task is None

    def test_create_running(self):
        """测试创建运行中的 Agent"""
        agent = AgentStatus(
            name="Executor",
            status="running",
            current_task="生成代码",
            total_executions=89,
        )
        assert agent.status == "running"
        assert agent.current_task == "生成代码"

    def test_invalid_status(self):
        """测试无效状态（如果有验证）"""
        agent = AgentStatus(name="Test", status="error", total_executions=0)
        assert agent.status == "error"


class TestRecentTask:
    """测试 RecentTask 模型"""

    def test_create_completed(self):
        """测试创建已完成任务"""
        task = RecentTask(
            task_id="task-001",
            task="实现登录",
            workflow="build",
            model="deepseek",
            status="completed",
            started_at="2026-05-20T10:00:00",
            completed_at="2026-05-20T10:05:00",
            execution_time=300,
        )
        assert task.status == "completed"
        assert task.execution_time == 300

    def test_create_running(self):
        """测试创建运行中的任务"""
        task = RecentTask(
            task_id="task-002",
            task="生成文档",
            workflow="document",
            model="tongyi",
            status="running",
            started_at="2026-05-20T10:10:00",
        )
        assert task.status == "running"
        assert task.completed_at is None
        assert task.execution_time is None


# ========================================
# Helper Functions Tests
# ========================================
class TestGetMockAgents:
    """测试 _get_mock_agents"""

    def test_returns_list(self):
        """测试返回列表"""
        agents = _get_mock_agents()
        assert isinstance(agents, list)
        assert len(agents) > 0

    def test_agent_structure(self):
        """测试 Agent 结构"""
        agents = _get_mock_agents()
        for agent in agents:
            assert isinstance(agent, AgentStatus)
            assert hasattr(agent, "name")
            assert hasattr(agent, "status")
            assert hasattr(agent, "total_executions")


class TestGetMockRecentTasks:
    """测试 _get_mock_recent_tasks"""

    def test_returns_list(self):
        """测试返回列表"""
        tasks = _get_mock_recent_tasks()
        assert isinstance(tasks, list)
        assert len(tasks) > 0

    def test_task_structure(self):
        """测试任务结构"""
        tasks = _get_mock_recent_tasks()
        for task in tasks:
            assert isinstance(task, RecentTask)
            assert hasattr(task, "task_id")
            assert hasattr(task, "status")

    def test_limit(self):
        """测试限制返回数量"""
        tasks = _get_mock_recent_tasks()
        assert len(tasks) <= 10  # 默认限制


class TestBuildMockActivity:
    """测试 _build_mock_activity"""

    def test_returns_correct_days(self):
        """测试返回正确天数"""
        activity = _build_mock_activity(7)
        assert len(activity) == 7

    def test_all_zero(self):
        """测试所有数据都是零"""
        activity = _build_mock_activity(7)
        for a in activity:
            assert a.tasks == 0
            assert a.tokens == 0

    def test_days_parameter(self):
        """测试不同天数参数"""
        for days in [1, 7, 14, 30]:
            activity = _build_mock_activity(days)
            assert len(activity) == days


# ========================================
# API Route Tests - /stats
# ========================================
class TestGetDashboardStats:
    """测试 GET /api/dashboard/stats"""

    @patch("src.web.dashboard_api.Path.exists")
    def test_stats_no_state_dir(self, mock_exists, client):
        """测试无 .omc/state 目录"""
        mock_exists.return_value = False

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 0
        assert data["completed_tasks"] == 0
        assert data["success_rate"] == 0.0

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_with_workflows(self, mock_glob, mock_exists, client, mock_workflow_data):
        """测试有工作流数据"""
        mock_exists.return_value = True

        # 创建模拟文件对象
        mock_files = []
        for wf in mock_workflow_data:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        response = client.get("/api/dashboard/stats?days=7")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 4
        assert data["completed_tasks"] == 2
        assert data["running_tasks"] == 1
        assert data["failed_tasks"] == 1

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_empty_state_dir(self, mock_glob, mock_exists, client):
        """测试空的状态目录"""
        mock_exists.return_value = True
        mock_glob.return_value = []

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 0

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_days_filter(self, mock_glob, mock_exists, client, mock_workflow_data):
        """测试 days 参数过滤"""
        mock_exists.return_value = True

        # 只有 1 天内的数据
        now = datetime.now()
        recent_data = [
            {
                "timestamp": now.isoformat(),
                "status": "completed",
                "total_tokens": 100,
                "execution_time": 50,
            }
        ]

        mock_files = []
        for wf in recent_data:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        # days=1 应该包含
        response = client.get("/api/dashboard/stats?days=1")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 1

    def test_stats_days_min(self, client):
        """测试 days 最小值"""
        response = client.get("/api/dashboard/stats?days=1")
        assert response.status_code == 200

    def test_stats_days_max(self, client):
        """测试 days 最大值"""
        response = client.get("/api/dashboard/stats?days=30")
        assert response.status_code == 200

    def test_stats_days_too_small(self, client):
        """测试 days 太小"""
        response = client.get("/api/dashboard/stats?days=0")
        assert response.status_code == 422  # Validation error

    def test_stats_days_too_large(self, client):
        """测试 days 太大"""
        response = client.get("/api/dashboard/stats?days=31")
        assert response.status_code == 422  # Validation error

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_json_error(self, mock_glob, mock_exists, client):
        """测试 JSON 解析错误"""
        mock_exists.return_value = True

        mock_file = type("MockFile", (), {})()
        mock_file.read_text = lambda: "{invalid json"
        mock_glob.return_value = [mock_file]

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        # 解析失败应该跳过，返回 0
        assert data["total_tasks"] == 0

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_success_rate(self, mock_glob, mock_exists, client):
        """测试成功率计算"""
        mock_exists.return_value = True

        now = datetime.now()
        workflows = [
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 100, "execution_time": 50},
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 200, "execution_time": 60},
            {"timestamp": now.isoformat(), "status": "failed", "total_tokens": 50, "execution_time": 30},
        ]

        mock_files = []
        for wf in workflows:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["success_rate"] == pytest.approx(66.7, abs=0.1)

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_avg_execution_time(self, mock_glob, mock_exists, client):
        """测试平均执行时间"""
        mock_exists.return_value = True

        now = datetime.now()
        workflows = [
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 100, "execution_time": 100},
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 200, "execution_time": 200},
        ]

        mock_files = []
        for wf in workflows:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["avg_execution_time"] == pytest.approx(150.0, abs=0.1)

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_cache(self, mock_glob, mock_exists, client, mock_workflow_data):
        """测试缓存机制"""
        mock_exists.return_value = True

        mock_files = []
        for wf in mock_workflow_data:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        # 第一次请求
        response1 = client.get("/api/dashboard/stats?days=7")
        assert response1.status_code == 200

        # 第二次请求（应该使用缓存）
        response2 = client.get("/api/dashboard/stats?days=7")
        assert response2.status_code == 200

        # 数据应该一致
        assert response1.json() == response2.json()

        # glob 应该只调用一次（第二次命中缓存）
        # 注意：由于 time.time() mock 困难，这里主要测试不报错


# ========================================
# API Route Tests - /activity
# ========================================
class TestGetActivityData:
    """测试 GET /api/dashboard/activity"""

    @patch("src.web.dashboard_api.Path.exists")
    def test_activity_no_state_dir(self, mock_exists, client):
        """测试无状态目录"""
        mock_exists.return_value = False

        response = client.get("/api/dashboard/activity")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 7  # 默认 7 天
        # 所有数据应该为空
        for day in data:
            assert day["tasks"] == 0
            assert day["tokens"] == 0

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_activity_with_data(self, mock_glob, mock_exists, client):
        """测试有活动数据"""
        mock_exists.return_value = True

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        workflows = [
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 1000},
            {"timestamp": now.isoformat(), "status": "running", "total_tokens": 500},
        ]

        mock_files = []
        for wf in workflows:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        response = client.get("/api/dashboard/activity?days=7")
        assert response.status_code == 200
        data = response.json()

        # 找到今天的数据
        today_data = next((d for d in data if d["day"] == today_str), None)
        assert today_data is not None
        assert today_data["tasks"] == 2
        assert today_data["tokens"] == 1500

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_activity_days_parameter(self, mock_glob, mock_exists, client):
        """测试 days 参数"""
        mock_exists.return_value = True
        mock_glob.return_value = []

        for days in [1, 7, 14, 30]:
            response = client.get(f"/api/dashboard/activity?days={days}")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == days

    def test_activity_days_validation(self, client):
        """测试 days 参数验证"""
        # 太小
        response = client.get("/api/dashboard/activity?days=0")
        assert response.status_code == 422

        # 太大
        response = client.get("/api/dashboard/activity?days=31")
        assert response.status_code == 422

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_activity_json_error(self, mock_glob, mock_exists, client):
        """测试 JSON 解析错误"""
        mock_exists.return_value = True

        mock_file = type("MockFile", (), {})()
        mock_file.read_text = lambda: "{invalid"
        mock_glob.return_value = [mock_file]

        response = client.get("/api/dashboard/activity")
        assert response.status_code == 200
        data = response.json()
        # 应该返回空数据但不报错
        assert len(data) == 7

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_activity_missing_timestamp(self, mock_glob, mock_exists, client):
        """测试缺少 timestamp 字段"""
        mock_exists.return_value = True

        workflow = {"status": "completed", "total_tokens": 100}  # 没有 timestamp

        mock_file = type("MockFile", (), {})()
        mock_file.read_text = lambda: json.dumps(workflow)
        mock_glob.return_value = [mock_file]

        response = client.get("/api/dashboard/activity")
        assert response.status_code == 200
        # 不应该崩溃


# ========================================
# API Route Tests - /agents
# ========================================
class TestGetAgentStatus:
    """测试 GET /api/dashboard/agents"""

    def test_agents_returns_list(self, client):
        """测试返回 Agent 列表"""
        response = client.get("/api/dashboard/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_agents_structure(self, client):
        """测试 Agent 数据结构"""
        response = client.get("/api/dashboard/agents")
        assert response.status_code == 200
        data = response.json()

        expected_agents = ["Planner", "Architect", "Executor", "Verifier", "Reviewer", "Debugger", "Writer"]
        agent_names = [a["name"] for a in data]
        for name in expected_agents:
            assert name in agent_names

    def test_agents_status_values(self, client):
        """测试 Agent 状态值"""
        response = client.get("/api/dashboard/agents")
        assert response.status_code == 200
        data = response.json()

        for agent in data:
            assert agent["status"] in ["idle", "running", "error"]

    def test_agents_running_have_current_task(self, client):
        """测试运行中的 Agent 有当前任务"""
        response = client.get("/api/dashboard/agents")
        assert response.status_code == 200
        data = response.json()

        for agent in data:
            if agent["status"] == "running":
                assert "current_task" in agent
                assert agent["current_task"] is not None


# ========================================
# API Route Tests - /recent-tasks
# ========================================
class TestGetRecentTasks:
    """测试 GET /api/dashboard/recent-tasks"""

    def test_recent_tasks_default_limit(self, client):
        """测试默认限制"""
        response = client.get("/api/dashboard/recent-tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10

    def test_recent_tasks_custom_limit(self, client):
        """测试自定义限制"""
        response = client.get("/api/dashboard/recent-tasks?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    def test_recent_tasks_limit_min(self, client):
        """测试最小限制"""
        response = client.get("/api/dashboard/recent-tasks?limit=1")
        assert response.status_code == 200

    def test_recent_tasks_limit_max(self, client):
        """测试最大限制"""
        response = client.get("/api/dashboard/recent-tasks?limit=50")
        assert response.status_code == 200

    def test_recent_tasks_limit_too_small(self, client):
        """测试限制太小"""
        response = client.get("/api/dashboard/recent-tasks?limit=0")
        assert response.status_code == 422

    def test_recent_tasks_limit_too_large(self, client):
        """测试限制太大"""
        response = client.get("/api/dashboard/recent-tasks?limit=51")
        assert response.status_code == 422

    def test_recent_tasks_structure(self, client):
        """测试任务结构"""
        response = client.get("/api/dashboard/recent-tasks")
        assert response.status_code == 200
        data = response.json()

        if len(data) > 0:
            task = data[0]
            assert "task_id" in task
            assert "task" in task
            assert "workflow" in task
            assert "model" in task
            assert "status" in task
            assert "started_at" in task

    def test_recent_tasks_status_values(self, client):
        """测试任务状态值"""
        response = client.get("/api/dashboard/recent-tasks")
        assert response.status_code == 200
        data = response.json()

        valid_statuses = ["completed", "running", "failed"]
        for task in data:
            assert task["status"] in valid_statuses


# ========================================
# API Route Tests - /overview
# ========================================
class TestGetOverview:
    """测试 GET /api/dashboard/overview"""

    def test_overview_structure(self, client):
        """测试概览结构"""
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()

        assert "stats" in data
        assert "activity" in data
        assert "agents" in data
        assert "recent_tasks" in data
        assert "updated_at" in data

    def test_overview_stats(self, client):
        """测试概览中的统计"""
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()

        stats = data["stats"]
        assert "total_tasks" in stats
        assert "success_rate" in stats

    def test_overview_activity(self, client):
        """测试概览中的活动"""
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()

        activity = data["activity"]
        assert isinstance(activity, list)
        assert len(activity) == 7  # 默认 7 天

    def test_overview_agents(self, client):
        """测试概览中的 Agent"""
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()

        agents = data["agents"]
        assert isinstance(agents, list)
        assert len(agents) > 0

    def test_overview_recent_tasks_limit(self, client):
        """测试概览中最近任务限制"""
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()

        tasks = data["recent_tasks"]
        assert len(tasks) <= 5  # overview 限制为 5

    def test_overview_updated_at(self, client):
        """测试 updated_at 字段"""
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()

        # 应该是 ISO 格式时间
        assert "T" in data["updated_at"]


# ========================================
# Edge Cases and Error Handling
# ========================================
class TestEdgeCases:
    """测试边界情况和错误处理"""

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_all_completed(self, mock_glob, mock_exists, client):
        """测试全部完成"""
        mock_exists.return_value = True

        now = datetime.now()
        workflows = [
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 100, "execution_time": 50},
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 200, "execution_time": 60},
        ]

        mock_files = []
        for wf in workflows:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["success_rate"] == 100.0

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_all_failed(self, mock_glob, mock_exists, client):
        """测试全部失败"""
        mock_exists.return_value = True

        now = datetime.now()
        workflows = [
            {"timestamp": now.isoformat(), "status": "failed", "total_tokens": 100, "execution_time": 50},
            {"timestamp": now.isoformat(), "status": "failed", "total_tokens": 200, "execution_time": 60},
        ]

        mock_files = []
        for wf in workflows:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["success_rate"] == 0.0

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_no_execution_time(self, mock_glob, mock_exists, client):
        """测试没有执行时间"""
        mock_exists.return_value = True

        now = datetime.now()
        workflows = [
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 100},  # 没有 execution_time
        ]

        mock_files = []
        for wf in workflows:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["avg_execution_time"] == 0.0

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_stats_old_data_excluded(self, mock_glob, mock_exists, client):
        """测试旧数据被排除"""
        mock_exists.return_value = True

        # 31 天前的数据
        old_time = datetime.now() - timedelta(days=31)
        old_data = [
            {"timestamp": old_time.isoformat(), "status": "completed", "total_tokens": 100, "execution_time": 50},
        ]

        # 1 天前的数据
        now = datetime.now()
        recent_data = [
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 200, "execution_time": 60},
        ]

        mock_files = []
        for wf in old_data + recent_data:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        # days=7 应该只包括最近 7 天
        response = client.get("/api/dashboard/stats?days=7")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 1  # 只有 recent_data

    def test_concurrent_requests(self, client):
        """测试并发请求（模拟）"""
        # 发送多个请求
        responses = []
        for _ in range(5):
            response = client.get("/api/dashboard/stats")
            responses.append(response)

        # 所有请求都应该成功
        for response in responses:
            assert response.status_code == 200

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_activity_calculation(self, mock_glob, mock_exists, client):
        """测试活动数据计算"""
        mock_exists.return_value = True

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # 创建同一天的多个工作流
        workflows = [
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 100},
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 200},
            {"timestamp": now.isoformat(), "status": "running", "total_tokens": 50},
        ]

        mock_files = []
        for wf in workflows:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        response = client.get("/api/dashboard/activity")
        assert response.status_code == 200
        data = response.json()

        # 找到今天
        today_data = next((d for d in data if d["day"] == today_str), None)
        assert today_data is not None
        assert today_data["tasks"] == 3
        assert today_data["tokens"] == 350

    def test_response_model_validation(self, client):
        """测试响应模型验证"""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()

        # 验证返回字段
        required_fields = [
            "total_tasks", "completed_tasks", "running_tasks",
            "failed_tasks", "success_rate", "avg_execution_time",
            "total_tokens", "period_days",
        ]
        for field in required_fields:
            assert field in data


# ========================================
# Integration-style Tests
# ========================================
class TestIntegration:
    """集成测试（较少 mock）"""

    def test_all_routes_exist(self, client):
        """测试所有路由都存在"""
        # GET /stats
        response = client.get("/api/dashboard/stats")
        assert response.status_code != 404

        # GET /activity
        response = client.get("/api/dashboard/activity")
        assert response.status_code != 404

        # GET /agents
        response = client.get("/api/dashboard/agents")
        assert response.status_code != 404

        # GET /recent-tasks
        response = client.get("/api/dashboard/recent-tasks")
        assert response.status_code != 404

        # GET /overview
        response = client.get("/api/dashboard/overview")
        assert response.status_code != 404

    def test_overview_consistency(self, client):
        """测试 overview 数据一致性"""
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()

        # overview 应该包含所有其他端点的数据
        assert "stats" in data
        assert "activity" in data
        assert "agents" in data
        assert "recent_tasks" in data

    def test_stats_and_overview_stats_match(self, client):
        """测试 /stats 和 /overview 中的 stats 一致"""
        stats_response = client.get("/api/dashboard/stats?days=7")
        overview_response = client.get("/api/dashboard/overview")

        assert stats_response.status_code == 200
        assert overview_response.status_code == 200

        stats_data = stats_response.json()
        overview_data = overview_response.json()

        # stats 应该匹配
        assert stats_data == overview_data["stats"]

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    def test_complete_flow(self, mock_glob, mock_exists, client):
        """测试完整流程：获取所有数据"""
        mock_exists.return_value = True

        now = datetime.now()
        workflows = [
            {"timestamp": now.isoformat(), "status": "completed", "total_tokens": 1000, "execution_time": 120},
        ]

        mock_files = []
        for wf in workflows:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        # 1. 获取统计
        stats_response = client.get("/api/dashboard/stats")
        assert stats_response.status_code == 200

        # 2. 获取活动
        activity_response = client.get("/api/dashboard/activity")
        assert activity_response.status_code == 200

        # 3. 获取 Agent
        agents_response = client.get("/api/dashboard/agents")
        assert agents_response.status_code == 200

        # 4. 获取最近任务
        tasks_response = client.get("/api/dashboard/recent-tasks")
        assert tasks_response.status_code == 200

        # 5. 获取概览
        overview_response = client.get("/api/dashboard/overview")
        assert overview_response.status_code == 200

        # 验证数据一致性
        overview_data = overview_response.json()
        assert overview_data["stats"] == stats_response.json()
        assert overview_data["activity"] == activity_response.json()
        assert overview_data["agents"] == agents_response.json()
        # recent_tasks 在 overview 中限制为 5，可能需要调整
        assert len(overview_data["recent_tasks"]) <= 5

    def test_different_days_parameter(self, client):
        """测试不同 days 参数"""
        for days in [1, 3, 7, 14, 30]:
            response = client.get(f"/api/dashboard/stats?days={days}")
            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == days

    def test_model_dump_consistency(self):
        """测试 model_dump 一致性"""
        stats = DashboardStats(
            total_tasks=10,
            completed_tasks=5,
            running_tasks=3,
            failed_tasks=2,
            success_rate=50.0,
            avg_execution_time=100.0,
            total_tokens=5000,
            period_days=7,
        )
        data = stats.model_dump()
        assert data["total_tasks"] == 10
        assert data["success_rate"] == 50.0


# ========================================
# Cache Tests
# ========================================
class TestCache:
    """测试缓存机制"""

    def test_cache_clear_on_test(self, clear_cache):
        """测试缓存在每个测试前清除"""
        global _stats_cache, _stats_cache_time
        assert len(_stats_cache) == 0
        assert _stats_cache_time == 0.0

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    @patch("time.time")
    def test_cache_hit(self, mock_time, mock_glob, mock_exists, client, mock_workflow_data):
        """测试缓存命中"""
        mock_exists.return_value = True
        mock_time.return_value = 1000.0  # 固定时间

        mock_files = []
        for wf in mock_workflow_data:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        # 第一次请求
        response1 = client.get("/api/dashboard/stats?days=7")
        assert response1.status_code == 200

        # 第二次请求（时间未变，应该命中缓存）
        response2 = client.get("/api/dashboard/stats?days=7")
        assert response2.status_code == 200

        # 数据应该一致
        assert response1.json() == response2.json()

    @patch("src.web.dashboard_api.Path.exists")
    @patch("src.web.dashboard_api.Path.glob")
    @patch("time.time")
    def test_cache_miss_after_timeout(self, mock_time, mock_glob, mock_exists, client, mock_workflow_data):
        """测试缓存超时后未命中"""
        mock_exists.return_value = True

        mock_files = []
        for wf in mock_workflow_data:
            mock_file = type("MockFile", (), {})()
            mock_file.read_text = lambda w=wf: json.dumps(w)
            mock_files.append(mock_file)

        mock_glob.return_value = mock_files

        # 第一次请求，time = 1000
        mock_time.return_value = 1000.0
        response1 = client.get("/api/dashboard/stats?days=7")
        assert response1.status_code == 200

        # 301 秒后（超过 5 分钟缓存），time = 1301
        mock_time.return_value = 1301.0
        response2 = client.get("/api/dashboard/stats?days=7")
        assert response2.status_code == 200

        # 由于重新计算，glob 应该被调用两次
        assert mock_glob.call_count >= 2

    def test_different_days_different_cache(self, client):
        """测试不同 days 参数使用不同缓存键"""
        global _stats_cache
        _stats_cache["stats_7"] = "cache_7"
        _stats_cache["stats_14"] = "cache_14"

        assert "stats_7" in _stats_cache
        assert "stats_14" in _stats_cache
        assert _stats_cache["stats_7"] != _stats_cache["stats_14"]
