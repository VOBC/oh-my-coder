"""
团队协作模块

提供多人共享任务状态、团队统计和消息通知功能。
"""

from .auth import Team, TeamAuth, TeamMember, UserSession, team_auth
from .notification import (
    ConnectionManager,
    Notification,
    NotificationPriority,
    NotificationType,
    TeamNotifier,
    team_notifier,
)
from .statistics import (
    TeamStatistics,
    TeamStats,
    UsageRecord,
    UserStats,
    team_statistics,
)
from .task_sync import MemberRole, TaskStatus, TaskSync, TeamTask, task_sync

__all__ = [
    "ConnectionManager",
    "MemberRole",
    "Notification",
    "NotificationPriority",
    "NotificationType",
    "TaskStatus",
    # 任务同步
    "TaskSync",
    "Team",
    # 认证
    "TeamAuth",
    "TeamMember",
    # 通知
    "TeamNotifier",
    # 统计
    "TeamStatistics",
    "TeamStats",
    "TeamTask",
    "UsageRecord",
    "UserSession",
    "UserStats",
    "task_sync",
    "team_auth",
    "team_notifier",
    "team_statistics",
]
