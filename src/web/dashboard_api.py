"""
仪表板 API

提供项目统计和概览数据。
"""

from datetime import datetime
from pathlib import Path
from typing import Any

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
    current_task: str | None = None
    total_executions: int


class RecentTask(BaseModel):
    """最近任务"""

    task_id: str
    task: str
    workflow: str
    model: str
    status: str
    started_at: str
    completed_at: str | None = None
    execution_time: float | None = None


# 模拟数据存储
_stats_cache: dict[str, Any] = {}
_activity_cache: list[ActivityData] = []
_stats_cache_time: float = 0.0


def _get_real_stats(days: int = 7) -> DashboardStats:
    """从 .omc/state/ 目录读取真实工作流数据统计

    优先使用缓存（5 分钟有效），减少磁盘 IO。
    """
    global _stats_cache, _stats_cache_time
    import json
    import time

    now = time.time()
    cache_key = f"stats_{days}"
    if cache_key in _stats_cache and now - _stats_cache_time < 300:
        return _stats_cache[cache_key]

    state_dir = Path(".omc/state")
    if not state_dir.exists():
        return DashboardStats(
            total_tasks=0,
            completed_tasks=0,
            running_tasks=0,
            failed_tasks=0,
            success_rate=0.0,
            avg_execution_time=0.0,
            total_tokens=0,
            period_days=days,
        )

    cutoff = datetime.now().timestamp() - days * 86400
    workflows = []
    for wf_file in state_dir.glob("workflow_*.json"):
        try:
            wf = json.loads(wf_file.read_text())
            wf_time = datetime.fromisoformat(
                wf.get("timestamp", "2000-01-01")
            ).timestamp()
            if wf_time >= cutoff:
                workflows.append(wf)
        except Exception:
            pass

    total = len(workflows)
    completed = sum(1 for w in workflows if w.get("status") == "completed")
    running = sum(1 for w in workflows if w.get("status") == "running")
    failed = sum(1 for w in workflows if w.get("status") == "failed")
    tokens = sum(w.get("total_tokens", 0) for w in workflows)
    exec_times = [
        w.get("execution_time", 0) for w in workflows if w.get("execution_time")
    ]
    avg_time = sum(exec_times) / len(exec_times) if exec_times else 0.0
    rate = completed / total * 100 if total > 0 else 0.0

    stats = DashboardStats(
        total_tasks=total,
        completed_tasks=completed,
        running_tasks=running,
        failed_tasks=failed,
        success_rate=round(rate, 1),
        avg_execution_time=round(avg_time, 1),
        total_tokens=tokens,
        period_days=days,
    )
    _stats_cache[cache_key] = stats
    _stats_cache_time = now
    return stats


def _get_real_activity(days: int = 7) -> list[ActivityData]:
    """从 .omc/state/ 读取最近 days 天的每日工作流活动数据"""
    global _activity_cache, _stats_cache, _stats_cache_time
    import json
    import time
    from collections import defaultdict

    now = time.time()
    cache_key = f"activity_{days}"
    if cache_key in _stats_cache and now - _stats_cache_time < 300:
        return _activity_cache or _build_mock_activity(days)

    state_dir = Path(".omc/state")
    daily: dict[str, dict[str, int]] = defaultdict(lambda: {"tasks": 0, "tokens": 0})

    if state_dir.exists():
        cutoff = datetime.now().timestamp() - days * 86400
        for wf_file in state_dir.glob("workflow_*.json"):
            try:
                wf = json.loads(wf_file.read_text())
                wf_time = datetime.fromisoformat(
                    wf.get("timestamp", "2000-01-01")
                ).timestamp()
                if wf_time >= cutoff:
                    day = wf.get("timestamp", "")[:10]
                    if day:
                        daily[day]["tasks"] += 1
                        daily[day]["tokens"] += wf.get("total_tokens", 0)
            except Exception:
                pass

    # 填充最近 days 天
    result = []
    for i in range(days, 0, -1):
        day_str = (
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            - __import__("datetime").timedelta(days=i - 1)
        ).strftime("%Y-%m-%d")
        entry = daily.get(day_str, {"tasks": 0, "tokens": 0})
        result.append(
            ActivityData(
                day=day_str,
                tasks=entry["tasks"],
                tokens=entry["tokens"],
            )
        )

    _stats_cache[cache_key] = True
    _activity_cache = result
    return result


def _build_mock_activity(days: int) -> list[ActivityData]:
    """兜底：返回空活动数据"""
    return [
        ActivityData(
            day=(
                datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                - __import__("datetime").timedelta(days=i)
            ).strftime("%Y-%m-%d"),
            tasks=0,
            tokens=0,
        )
        for i in range(days, 0, -1)
    ]


# 保留旧函数名用于兼容，直接替换为真实实现
def _get_mock_stats() -> DashboardStats:
    """获取统计数据（现已从真实文件读取，7 天窗口）"""
    return _get_real_stats(7)


def _get_mock_activity() -> list[ActivityData]:
    """获取活动数据（现已从真实文件读取，7 天窗口）"""
    return _get_real_activity(7)


def _get_mock_agents() -> list[AgentStatus]:
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


def _get_mock_recent_tasks() -> list[RecentTask]:
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
    days: int = Query(7, ge=1, le=30, description="统计周期（天）"),
) -> DashboardStats:
    """
    获取仪表板统计数据

    Args:
        days: 统计周期，默认 7 天

    Returns:
        统计数据
    """
    # TODO: 从数据库获取真实数据
    return _get_real_stats(days)


@router.get("/activity", response_model=list[ActivityData])
async def get_activity_data(days: int = Query(7, ge=1, le=30)) -> list[ActivityData]:
    """
    获取活动数据

    Args:
        days: 统计周期

    Returns:
        每日活动数据
    """
    # TODO: 从数据库获取真实数据
    return _get_real_activity(days)


@router.get("/agents", response_model=list[AgentStatus])
async def get_agent_status() -> list[AgentStatus]:
    """
    获取所有 Agent 状态

    Returns:
        Agent 状态列表
    """
    return _get_mock_agents()


@router.get("/recent-tasks", response_model=list[RecentTask])
async def get_recent_tasks(limit: int = Query(10, ge=1, le=50)) -> list[RecentTask]:
    """
    获取最近任务

    Args:
        limit: 返回数量

    Returns:
        最近任务列表
    """
    return _get_mock_recent_tasks()[:limit]


@router.get("/overview")
async def get_overview() -> dict[str, Any]:
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
