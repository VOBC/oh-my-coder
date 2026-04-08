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
from .task_sync import MemberRole, TaskStatus, TeamTask, TaskSync, task_sync

__all__ = [
    # 认证
    "TeamAuth",
    "Team",
    "TeamMember",
    "UserSession",
    "team_auth",
    # 任务同步
    "TaskSync",
    "TeamTask",
    "TaskStatus",
    "MemberRole",
    "task_sync",
    # 统计
    "TeamStatistics",
    "UsageRecord",
    "TeamStats",
    "UserStats",
    "team_statistics",
    # 通知
    "TeamNotifier",
    "Notification",
    "NotificationType",
    "NotificationPriority",
    "ConnectionManager",
    "team_notifier",
]
