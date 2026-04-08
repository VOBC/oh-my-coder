"""
仪表板 API

提供项目统计和概览数据。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DashboardStats(BaseModel):
    """仪表板统计数据"""

    total_tasks: int
    completed_tasks: int
    running_tasks: int
    failed_tasks: int
    success_rate: float
    avg_execution_time: float
    total_tokens: int
    period_days: int


class ActivityData(BaseModel):
    """活动数据"""

    day: str
    tasks: int
    tokens: int


class AgentStatus(BaseModel):
    """Agent 状态"""

    name: str
    status: str  # idle, running, error
    current_task: Optional[str] = None
    total_executions: int


class RecentTask(BaseModel):
    """最近任务"""

    task_id: str
    task: str
    workflow: str
    model: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    execution_time: Optional[float] = None


# 模拟数据存储
_stats_cache: Dict[str, Any] = {}
_activity_cache: List[ActivityData] = []


def _get_mock_stats() -> DashboardStats:
    """获取模拟统计数据"""
    return DashboardStats(
        total_tasks=156,
        completed_tasks=142,
        running_tasks=3,
        failed_tasks=11,
        success_rate=91.0,
        avg_execution_time=45.2,
        total_tokens=2300000,
        period_days=7,
    )


def _get_mock_activity() -> List[ActivityData]:
    """获取模拟活动数据"""
    days = ["一", "二", "三", "四", "五", "六", "日"]
    return [
        ActivityData(day=d, tasks=t, tokens=t * 15000)
        for d, t in zip(days, [12, 19, 8, 15, 22, 18, 14])
    ]


def _get_mock_agents() -> List[AgentStatus]:
    """获取模拟 Agent 状态"""
    return [
        AgentStatus(name="Planner", status="idle", total_executions=45),
        AgentStatus(name="Architect", status="idle", total_executions=32),
        AgentStatus(
            name="Executor",
            status="running",
            current_task="生成代码",
            total_executions=89,
        ),
        AgentStatus(name="Verifier", status="idle", total_executions=67),
        AgentStatus(name="Reviewer", status="idle", total_executions=28),
        AgentStatus(name="Debugger", status="idle", total_executions=15),
        AgentStatus(
            name="Writer",
            status="running",
            current_task="生成文档",
            total_executions=23,
        ),
    ]


def _get_mock_recent_tasks() -> List[RecentTask]:
    """获取模拟最近任务"""
    return [
        RecentTask(
            task_id="task-001",
            task="实现用户登录功能",
            workflow="build",
            model="deepseek",
            status="completed",
            started_at="2024-01-15T10:30:00",
            completed_at="2024-01-15T10:35:00",
            execution_time=300,
        ),
        RecentTask(
            task_id="task-002",
            task="生成 API 文档",
            workflow="document",
            model="tongyi",
            status="running",
            started_at="2024-01-15T10:40:00",
        ),
        RecentTask(
            task_id="task-003",
            task="代码审查 PR #42",
            workflow="review",
            model="wenxin",
            status="completed",
            started_at="2024-01-15T09:00:00",
            completed_at="2024-01-15T09:15:00",
            execution_time=900,
        ),
        RecentTask(
            task_id="task-004",
            task="修复数据库连接问题",
            workflow="debug",
            model="kimi",
            status="failed",
            started_at="2024-01-15T08:00:00",
            completed_at="2024-01-15T08:10:00",
            execution_time=600,
        ),
    ]


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    days: int = Query(7, ge=1, le=30, description="统计周期（天）")
) -> DashboardStats:
    """
    获取仪表板统计数据

    Args:
        days: 统计周期，默认 7 天

    Returns:
        统计数据
    """
    # TODO: 从数据库获取真实数据
    return _get_mock_stats()


@router.get("/activity", response_model=List[ActivityData])
async def get_activity_data(days: int = Query(7, ge=1, le=30)) -> List[ActivityData]:
    """
    获取活动数据

    Args:
        days: 统计周期

    Returns:
        每日活动数据
    """
    # TODO: 从数据库获取真实数据
    return _get_mock_activity()


@router.get("/agents", response_model=List[AgentStatus])
async def get_agent_status() -> List[AgentStatus]:
    """
    获取所有 Agent 状态

    Returns:
        Agent 状态列表
    """
    return _get_mock_agents()


@router.get("/recent-tasks", response_model=List[RecentTask])
async def get_recent_tasks(limit: int = Query(10, ge=1, le=50)) -> List[RecentTask]:
    """
    获取最近任务

    Args:
        limit: 返回数量

    Returns:
        最近任务列表
    """
    return _get_mock_recent_tasks()[:limit]


@router.get("/overview")
async def get_overview() -> Dict[str, Any]:
    """
    获取完整仪表板概览

    Returns:
        所有仪表板数据
    """
    return {
        "stats": _get_mock_stats().model_dump(),
        "activity": [a.model_dump() for a in _get_mock_activity()],
        "agents": [a.model_dump() for a in _get_mock_agents()],
        "recent_tasks": [t.model_dump() for t in _get_mock_recent_tasks()[:5]],
        "updated_at": datetime.now().isoformat(),
    }
