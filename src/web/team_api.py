"""
团队 API 路由

提供团队创建、加入、任务同步和统计等 API。
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.team import (
    TaskStatus,
    team_auth,
    team_notifier,
    team_statistics,
    task_sync,
)


router = APIRouter(prefix="/api/team", tags=["team"])


# ========================================
# 请求模型
# ========================================


class CreateTeamRequest(BaseModel):
    """创建团队请求"""

    name: str
    owner_id: str
    description: str = ""


class JoinTeamRequest(BaseModel):
    """加入团队请求"""

    invite_code: str
    user_id: str
    display_name: str = ""
    email: str = ""


class CreateTaskRequest(BaseModel):
    """创建任务请求"""

    team_id: str
    creator_id: str
    title: str
    description: str = ""
    workflow: str = "build"
    model: str = "deepseek"


class UpdateTaskRequest(BaseModel):
    """更新任务请求"""

    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0


class RecordUsageRequest(BaseModel):
    """记录使用请求"""

    team_id: str
    user_id: str
    task_id: str
    task_type: str
    model: str
    tokens_used: int
    cost: float
    execution_time: float
    status: str = "success"


class BroadcastRequest(BaseModel):
    """广播消息请求"""

    team_id: str
    title: str
    message: str
    priority: str = "normal"


# ========================================
# 团队管理 API
# ========================================


@router.post("/create")
async def create_team(request: CreateTeamRequest) -> Dict[str, Any]:
    """
    创建团队

    Args:
        request: 创建团队请求

    Returns:
        团队信息
    """
    team = await team_auth.create_team(
        name=request.name,
        owner_id=request.owner_id,
        description=request.description,
    )
    return team.to_dict()


@router.post("/join")
async def join_team(request: JoinTeamRequest) -> Dict[str, Any]:
    """
    加入团队

    Args:
        request: 加入团队请求

    Returns:
        团队信息
    """
    team = await team_auth.join_team(
        invite_code=request.invite_code,
        user_id=request.user_id,
        display_name=request.display_name,
        email=request.email,
    )
    if not team:
        raise HTTPException(status_code=404, detail="无效的邀请码")
    return team.to_dict()


@router.post("/leave")
async def leave_team(user_id: str, team_id: str) -> Dict[str, bool]:
    """
    离开团队

    Args:
        user_id: 用户 ID
        team_id: 团队 ID

    Returns:
        操作结果
    """
    success = await team_auth.leave_team(user_id, team_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法离开团队")
    return {"success": True}


@router.post("/delete")
async def delete_team(team_id: str, requester_id: str) -> Dict[str, bool]:
    """
    删除团队

    Args:
        team_id: 团队 ID
        requester_id: 请求者 ID

    Returns:
        操作结果
    """
    success = await team_auth.delete_team(team_id, requester_id)
    if not success:
        raise HTTPException(status_code=403, detail="无权删除团队")
    return {"success": True}


@router.get("/{team_id}")
async def get_team(team_id: str) -> Dict[str, Any]:
    """
    获取团队信息

    Args:
        team_id: 团队 ID

    Returns:
        团队信息
    """
    team = await team_auth.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    return team.to_dict()


@router.get("/user/{user_id}")
async def get_user_team(user_id: str) -> Dict[str, Any]:
    """
    获取用户所在团队

    Args:
        user_id: 用户 ID

    Returns:
        团队信息
    """
    team = await team_auth.get_user_team(user_id)
    if not team:
        raise HTTPException(status_code=404, detail="用户未加入任何团队")
    return team.to_dict()


@router.post("/{team_id}/regenerate-invite")
async def regenerate_invite(team_id: str, requester_id: str) -> Dict[str, str]:
    """
    重新生成邀请码

    Args:
        team_id: 团队 ID
        requester_id: 请求者 ID

    Returns:
        新邀请码
    """
    code = await team_auth.regenerate_invite_code(team_id, requester_id)
    if not code:
        raise HTTPException(status_code=403, detail="无权生成邀请码")
    return {"invite_code": code}


# ========================================
# 任务同步 API
# ========================================


@router.post("/task/create")
async def create_task(request: CreateTaskRequest) -> Dict[str, Any]:
    """
    创建团队任务

    Args:
        request: 创建任务请求

    Returns:
        任务信息
    """
    import uuid

    task_id = f"task_{uuid.uuid4().hex[:8]}"

    task = await task_sync.create_task(
        task_id=task_id,
        team_id=request.team_id,
        creator_id=request.creator_id,
        title=request.title,
        description=request.description,
        workflow=request.workflow,
        model=request.model,
    )

    # 发送通知
    await team_notifier.notify_task_created(
        task_id=task.task_id,
        team_id=task.team_id,
        creator_id=task.creator_id,
        title=task.title,
    )

    return task.to_dict()


@router.put("/task/{task_id}/status")
async def update_task_status(
    task_id: str, request: UpdateTaskRequest
) -> Dict[str, Any]:
    """
    更新任务状态

    Args:
        task_id: 任务 ID
        request: 更新请求

    Returns:
        更新后的任务信息
    """
    status = TaskStatus(request.status)
    task = await task_sync.update_status(
        task_id=task_id,
        status=status,
        result=request.result,
        error=request.error,
        tokens_used=request.tokens_used,
        cost=request.cost,
    )
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 发送通知
    if status == TaskStatus.COMPLETED:
        await team_notifier.notify_task_completed(
            task_id=task.task_id,
            team_id=task.team_id,
            title=task.title,
            result=request.result or {},
        )
    elif status == TaskStatus.FAILED:
        await team_notifier.notify_task_failed(
            task_id=task.task_id,
            team_id=task.team_id,
            title=task.title,
            error=request.error or "未知错误",
        )

    return task.to_dict()


@router.get("/task/{task_id}")
async def get_task(task_id: str) -> Dict[str, Any]:
    """
    获取任务详情

    Args:
        task_id: 任务 ID

    Returns:
        任务信息
    """
    task = await task_sync.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.to_dict()


@router.get("/{team_id}/tasks")
async def get_team_tasks(team_id: str) -> List[Dict[str, Any]]:
    """
    获取团队任务列表

    Args:
        team_id: 团队 ID

    Returns:
        任务列表
    """
    tasks = await task_sync.get_team_tasks(team_id)
    return [t.to_dict() for t in tasks]


@router.post("/task/{task_id}/subscribe")
async def subscribe_task(task_id: str, user_id: str) -> Dict[str, bool]:
    """
    订阅任务更新

    Args:
        task_id: 任务 ID
        user_id: 用户 ID

    Returns:
        操作结果
    """
    success = await task_sync.subscribe_task(task_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True}


@router.delete("/task/{task_id}")
async def delete_task(task_id: str) -> Dict[str, bool]:
    """
    删除任务

    Args:
        task_id: 任务 ID

    Returns:
        操作结果
    """
    success = await task_sync.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True}


# ========================================
# 统计 API
# ========================================


@router.post("/usage/record")
async def record_usage(request: RecordUsageRequest) -> Dict[str, Any]:
    """
    记录使用数据

    Args:
        request: 记录请求

    Returns:
        记录信息
    """
    import uuid

    record_id = f"usage_{uuid.uuid4().hex[:8]}"

    record = team_statistics.record_usage(
        record_id=record_id,
        team_id=request.team_id,
        user_id=request.user_id,
        task_id=request.task_id,
        task_type=request.task_type,
        model=request.model,
        tokens_used=request.tokens_used,
        cost=request.cost,
        execution_time=request.execution_time,
        status=request.status,
    )

    return record.to_dict()


@router.get("/{team_id}/stats")
async def get_team_stats(
    team_id: str, period: str = Query("week", pattern="^(day|week|month)$")
) -> Dict[str, Any]:
    """
    获取团队统计

    Args:
        team_id: 团队 ID
        period: 统计周期

    Returns:
        统计数据
    """
    stats = team_statistics.get_team_stats(team_id, period)
    return stats.to_dict()


@router.get("/{team_id}/user/{user_id}/stats")
async def get_user_stats(
    team_id: str,
    user_id: str,
    period: str = Query("week", pattern="^(day|week|month)$"),
) -> Dict[str, Any]:
    """
    获取用户统计

    Args:
        team_id: 团队 ID
        user_id: 用户 ID
        period: 统计周期

    Returns:
        统计数据
    """
    stats = team_statistics.get_user_stats(user_id, team_id, period)
    return stats.to_dict()


# ========================================
# 通知 API
# ========================================


@router.post("/broadcast")
async def broadcast_message(request: BroadcastRequest) -> Dict[str, Any]:
    """
    广播消息给团队

    Args:
        request: 广播请求

    Returns:
        通知信息
    """
    from src.team.notification import NotificationPriority

    priority = NotificationPriority(request.priority)

    notification = await team_notifier.broadcast(
        team_id=request.team_id,
        title=request.title,
        message=request.message,
        priority=priority,
    )

    return notification.to_dict()


@router.get("/{team_id}/notifications")
async def get_team_notifications(
    team_id: str, unread_only: bool = False
) -> List[Dict[str, Any]]:
    """
    获取团队通知

    Args:
        team_id: 团队 ID
        unread_only: 是否只返回未读

    Returns:
        通知列表
    """
    notifications = team_notifier.get_team_notifications(team_id, unread_only)
    return [n.to_dict() for n in notifications]


@router.get("/{team_id}/user/{user_id}/notifications")
async def get_user_notifications(
    team_id: str, user_id: str, unread_only: bool = False
) -> List[Dict[str, Any]]:
    """
    获取用户通知

    Args:
        team_id: 团队 ID
        user_id: 用户 ID
        unread_only: 是否只返回未读

    Returns:
        通知列表
    """
    notifications = team_notifier.get_user_notifications(user_id, team_id, unread_only)
    return [n.to_dict() for n in notifications]


@router.post("/notification/{notification_id}/read")
async def mark_notification_read(notification_id: str) -> Dict[str, bool]:
    """
    标记通知为已读

    Args:
        notification_id: 通知 ID

    Returns:
        操作结果
    """
    success = team_notifier.mark_as_read(notification_id)
    return {"success": success}
