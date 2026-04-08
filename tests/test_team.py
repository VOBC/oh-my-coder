"""
团队协作模块测试
"""

import pytest
from datetime import datetime, timedelta
import uuid

from src.team import (
    MemberRole,
    TaskStatus,
    team_auth,
    team_notifier,
    team_statistics,
    task_sync,
    NotificationType,
    NotificationPriority,
)


# ========================================
# 团队认证测试
# ========================================


class TestTeamAuth:
    """团队认证测试"""

    @pytest.mark.asyncio
    async def test_create_team(self):
        """测试创建团队"""
        team = await team_auth.create_team(
            name=f"测试团队_{uuid.uuid4().hex[:6]}",
            owner_id=f"user_{uuid.uuid4().hex[:6]}",
            description="这是一个测试团队",
        )

        assert team.name.startswith("测试团队")
        assert len(team.members) == 1
        assert team.members[0].role == MemberRole.OWNER
        assert team.invite_code != ""

    @pytest.mark.asyncio
    async def test_join_team(self):
        """测试加入团队"""
        owner_id = f"owner_{uuid.uuid4().hex[:6]}"
        member_id = f"member_{uuid.uuid4().hex[:6]}"

        # 创建团队
        team = await team_auth.create_team(
            name=f"测试团队2_{uuid.uuid4().hex[:6]}",
            owner_id=owner_id,
        )

        # 加入团队
        joined_team = await team_auth.join_team(
            invite_code=team.invite_code,
            user_id=member_id,
            display_name="测试用户",
        )

        assert joined_team is not None
        assert len(joined_team.members) == 2
        assert any(m.user_id == member_id for m in joined_team.members)

    @pytest.mark.asyncio
    async def test_invalid_invite_code(self):
        """测试无效邀请码"""
        team = await team_auth.join_team(
            invite_code="INVALID_CODE_12345",
            user_id=f"user_{uuid.uuid4().hex[:6]}",
        )
        assert team is None

    @pytest.mark.asyncio
    async def test_leave_team(self):
        """测试离开团队"""
        owner_id = f"owner_{uuid.uuid4().hex[:6]}"
        member_id = f"member_{uuid.uuid4().hex[:6]}"

        team = await team_auth.create_team(
            name=f"测试团队3_{uuid.uuid4().hex[:6]}",
            owner_id=owner_id,
        )
        await team_auth.join_team(
            invite_code=team.invite_code,
            user_id=member_id,
        )

        success = await team_auth.leave_team(member_id, team.team_id)
        assert success is True

        team_after = await team_auth.get_team(team.team_id)
        assert len(team_after.members) == 1

    @pytest.mark.asyncio
    async def test_owner_cannot_leave(self):
        """测试所有者不能离开"""
        owner_id = f"owner_{uuid.uuid4().hex[:6]}"

        team = await team_auth.create_team(
            name=f"测试团队4_{uuid.uuid4().hex[:6]}",
            owner_id=owner_id,
        )

        success = await team_auth.leave_team(owner_id, team.team_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_check_permission(self):
        """测试权限检查"""
        owner_id = f"owner_{uuid.uuid4().hex[:6]}"
        member_id = f"member_{uuid.uuid4().hex[:6]}"

        team = await team_auth.create_team(
            name=f"测试团队5_{uuid.uuid4().hex[:6]}",
            owner_id=owner_id,
        )
        await team_auth.join_team(
            invite_code=team.invite_code,
            user_id=member_id,
        )

        # 所有者有权限
        assert team_auth.check_permission(owner_id, team.team_id, MemberRole.ADMIN) is True

        # 普通成员没有管理员权限
        assert team_auth.check_permission(member_id, team.team_id, MemberRole.ADMIN) is False


# ========================================
# 任务同步测试
# ========================================


class TestTaskSync:
    """任务同步测试"""

    @pytest.mark.asyncio
    async def test_create_task(self):
        """测试创建任务"""
        await task_sync.connect()

        task_id = f"task_{uuid.uuid4().hex[:6]}"
        team_id = f"team_{uuid.uuid4().hex[:6]}"
        user_id = f"user_{uuid.uuid4().hex[:6]}"

        task = await task_sync.create_task(
            task_id=task_id,
            team_id=team_id,
            creator_id=user_id,
            title="实现登录功能",
            description="使用 JWT 实现",
            workflow="build",
            model="deepseek",
        )

        assert task.task_id == task_id
        assert task.status == TaskStatus.PENDING
        assert task.creator_id == user_id

    @pytest.mark.asyncio
    async def test_update_task_status(self):
        """测试更新任务状态"""
        await task_sync.connect()

        task_id = f"task_{uuid.uuid4().hex[:6]}"
        team_id = f"team_{uuid.uuid4().hex[:6]}"
        user_id = f"user_{uuid.uuid4().hex[:6]}"

        await task_sync.create_task(
            task_id=task_id,
            team_id=team_id,
            creator_id=user_id,
            title="测试任务",
        )

        # 更新为运行中
        task = await task_sync.update_status(task_id, TaskStatus.RUNNING)
        assert task is not None
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

        # 完成任务
        task = await task_sync.update_status(
            task_id,
            TaskStatus.COMPLETED,
            result={"files": ["main.py"]},
            tokens_used=1000,
            cost=0.01,
        )
        assert task.status == TaskStatus.COMPLETED
        assert task.tokens_used == 1000

    @pytest.mark.asyncio
    async def test_get_team_tasks(self):
        """测试获取团队任务"""
        await task_sync.connect()

        team_id = f"team_{uuid.uuid4().hex[:6]}"

        # 创建多个任务
        for i in range(3):
            await task_sync.create_task(
                task_id=f"task_{uuid.uuid4().hex[:6]}_{i}",
                team_id=team_id,
                creator_id=f"user_{i}",
                title=f"任务{i}",
            )

        tasks = await task_sync.get_team_tasks(team_id)
        assert len(tasks) >= 3

    @pytest.mark.asyncio
    async def test_subscribe_task(self):
        """测试订阅任务"""
        await task_sync.connect()

        task_id = f"task_{uuid.uuid4().hex[:6]}"
        team_id = f"team_{uuid.uuid4().hex[:6]}"

        await task_sync.create_task(
            task_id=task_id,
            team_id=team_id,
            creator_id="user_001",
            title="订阅测试",
        )

        success = await task_sync.subscribe_task(task_id, "user_003")
        assert success is True

        task = await task_sync.get_task(task_id)
        assert "user_003" in task.subscribers


# ========================================
# 团队统计测试
# ========================================


class TestTeamStatistics:
    """团队统计测试"""

    def test_record_usage(self):
        """测试记录使用数据"""
        record = team_statistics.record_usage(
            record_id=f"usage_{uuid.uuid4().hex[:8]}",
            team_id=f"team_{uuid.uuid4().hex[:6]}",
            user_id=f"user_{uuid.uuid4().hex[:6]}",
            task_id=f"task_{uuid.uuid4().hex[:6]}",
            task_type="build",
            model="deepseek",
            tokens_used=2000,
            cost=0.02,
            execution_time=30.5,
            status="success",
        )

        assert record.tokens_used == 2000

    def test_get_team_stats(self):
        """测试获取团队统计"""
        team_id = f"team_stats_{uuid.uuid4().hex[:6]}"

        # 记录一些数据
        team_statistics.record_usage(
            record_id=f"usage_{uuid.uuid4().hex[:8]}",
            team_id=team_id,
            user_id="user_001",
            task_id="task_001",
            task_type="build",
            model="deepseek",
            tokens_used=1000,
            cost=0.01,
            execution_time=10.0,
            status="success",
        )

        stats = team_statistics.get_team_stats(team_id, "week")

        assert stats.team_id == team_id
        assert stats.period == "week"
        assert stats.total_tasks >= 1

    def test_get_user_stats(self):
        """测试获取用户统计"""
        user_id = f"user_stats_{uuid.uuid4().hex[:6]}"
        team_id = f"team_user_{uuid.uuid4().hex[:6]}"

        team_statistics.record_usage(
            record_id=f"usage_{uuid.uuid4().hex[:8]}",
            team_id=team_id,
            user_id=user_id,
            task_id="task_001",
            task_type="review",
            model="glm",
            tokens_used=500,
            cost=0.005,
            execution_time=5.0,
            status="success",
        )

        stats = team_statistics.get_user_stats(user_id, team_id, "week")

        assert stats.user_id == user_id
        assert stats.period == "week"


# ========================================
# 消息通知测试
# ========================================


class TestTeamNotifier:
    """消息通知测试"""

    @pytest.mark.asyncio
    async def test_notify_task_created(self):
        """测试任务创建通知"""
        notification = await team_notifier.notify_task_created(
            task_id=f"task_{uuid.uuid4().hex[:6]}",
            team_id=f"team_{uuid.uuid4().hex[:6]}",
            creator_id=f"user_{uuid.uuid4().hex[:6]}",
            title="通知测试任务",
        )

        assert notification.type == NotificationType.TASK_CREATED
        assert "通知测试任务" in notification.message

    @pytest.mark.asyncio
    async def test_notify_task_completed(self):
        """测试任务完成通知"""
        notification = await team_notifier.notify_task_completed(
            task_id=f"task_{uuid.uuid4().hex[:6]}",
            team_id=f"team_{uuid.uuid4().hex[:6]}",
            title="完成的任务",
            result={"status": "success"},
        )

        assert notification.type == NotificationType.TASK_COMPLETED
        assert notification.priority == NotificationPriority.NORMAL

    @pytest.mark.asyncio
    async def test_notify_task_failed(self):
        """测试任务失败通知"""
        notification = await team_notifier.notify_task_failed(
            task_id=f"task_{uuid.uuid4().hex[:6]}",
            team_id=f"team_{uuid.uuid4().hex[:6]}",
            title="失败的任务",
            error="网络超时",
        )

        assert notification.type == NotificationType.TASK_FAILED
        assert notification.priority == NotificationPriority.HIGH
        assert "网络超时" in notification.message

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """测试团队广播"""
        notification = await team_notifier.broadcast(
            team_id=f"team_broadcast_{uuid.uuid4().hex[:6]}",
            title="系统公告",
            message="今晚 10 点系统维护",
            priority=NotificationPriority.HIGH,
        )

        assert notification.type == NotificationType.TEAM_BROADCAST
        assert notification.title == "系统公告"

    @pytest.mark.asyncio
    async def test_get_team_notifications(self):
        """测试获取团队通知"""
        team_id = f"team_get_test_{uuid.uuid4().hex[:6]}"

        # 创建一些通知
        await team_notifier.broadcast(
            team_id=team_id,
            title="测试通知1",
            message="消息内容1",
        )
        await team_notifier.broadcast(
            team_id=team_id,
            title="测试通知2",
            message="消息内容2",
        )

        notifications = team_notifier.get_team_notifications(team_id)

        assert len(notifications) >= 2


# ========================================
# 运行测试
# ========================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
