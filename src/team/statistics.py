"""
团队统计模块

记录和查询团队使用数据。
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class UsageRecord:
    """使用记录"""

    record_id: str
    team_id: str
    user_id: str
    task_id: str
    task_type: str  # build, review, debug, etc.
    model: str
    tokens_used: int
    cost: float
    execution_time: float  # 秒
    status: str  # success, failed
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "team_id": self.team_id,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "execution_time": self.execution_time,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TeamStats:
    """团队统计数据"""

    team_id: str
    period: str  # day, week, month
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_tokens: int
    total_cost: float
    avg_execution_time: float
    top_models: List[Dict[str, Any]]
    top_users: List[Dict[str, Any]]
    daily_breakdown: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "period": self.period,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": (
                self.successful_tasks / self.total_tasks * 100
                if self.total_tasks > 0
                else 0
            ),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_execution_time": self.avg_execution_time,
            "top_models": self.top_models,
            "top_users": self.top_users,
            "daily_breakdown": self.daily_breakdown,
        }


@dataclass
class UserStats:
    """用户统计数据"""

    user_id: str
    team_id: str
    period: str
    total_tasks: int
    successful_tasks: int
    total_tokens: int
    total_cost: float
    avg_execution_time: float
    favorite_model: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "team_id": self.team_id,
            "period": self.period,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "success_rate": (
                self.successful_tasks / self.total_tasks * 100
                if self.total_tasks > 0
                else 0
            ),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_execution_time": self.avg_execution_time,
            "favorite_model": self.favorite_model,
        }


class TeamStatistics:
    """
    团队统计管理器

    使用 SQLite 存储使用记录，支持：
    - 记录使用数据
    - 查询团队/用户统计
    - 数据自动清理（保留30天）
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化

        Args:
            db_path: 数据库文件路径，默认在 .omc 目录下
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path.home() / ".omc" / "team_stats.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 创建使用记录表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_records (
                record_id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens_used INTEGER NOT NULL,
                cost REAL NOT NULL,
                execution_time REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """
        )

        # 创建索引
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_team_created
            ON usage_records(team_id, created_at)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_created
            ON usage_records(user_id, created_at)
        """
        )

        conn.commit()
        conn.close()

    def record_usage(
        self,
        record_id: str,
        team_id: str,
        user_id: str,
        task_id: str,
        task_type: str,
        model: str,
        tokens_used: int,
        cost: float,
        execution_time: float,
        status: str = "success",
    ) -> UsageRecord:
        """
        记录使用数据

        Args:
            record_id: 记录 ID
            team_id: 团队 ID
            user_id: 用户 ID
            task_id: 任务 ID
            task_type: 任务类型
            model: 使用的模型
            tokens_used: 消耗的 Token 数
            cost: 成本
            execution_time: 执行时间（秒）
            status: 状态

        Returns:
            UsageRecord: 创建的记录
        """
        record = UsageRecord(
            record_id=record_id,
            team_id=team_id,
            user_id=user_id,
            task_id=task_id,
            task_type=task_type,
            model=model,
            tokens_used=tokens_used,
            cost=cost,
            execution_time=execution_time,
            status=status,
        )

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO usage_records
            (record_id, team_id, user_id, task_id, task_type, model,
             tokens_used, cost, execution_time, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                record.record_id,
                record.team_id,
                record.user_id,
                record.task_id,
                record.task_type,
                record.model,
                record.tokens_used,
                record.cost,
                record.execution_time,
                record.status,
                record.created_at.isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        return record

    def get_team_stats(self, team_id: str, period: str = "week") -> TeamStats:
        """
        获取团队统计

        Args:
            team_id: 团队 ID
            period: 统计周期（day/week/month）

        Returns:
            TeamStats: 统计数据
        """
        # 计算时间范围
        now = datetime.now()
        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        else:  # month
            start_date = now - timedelta(days=30)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 查询基本统计
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(tokens_used) as total_tokens,
                SUM(cost) as total_cost,
                AVG(execution_time) as avg_time
            FROM usage_records
            WHERE team_id = ? AND created_at >= ?
        """,
            (team_id, start_date.isoformat()),
        )

        row = cursor.fetchone()

        # 查询模型使用排名
        cursor.execute(
            """
            SELECT model, COUNT(*) as count, SUM(tokens_used) as tokens
            FROM usage_records
            WHERE team_id = ? AND created_at >= ?
            GROUP BY model
            ORDER BY count DESC
            LIMIT 5
        """,
            (team_id, start_date.isoformat()),
        )

        top_models = [
            {"model": r[0], "count": r[1], "tokens": r[2]} for r in cursor.fetchall()
        ]

        # 查询用户使用排名
        cursor.execute(
            """
            SELECT user_id, COUNT(*) as count, SUM(cost) as total_cost
            FROM usage_records
            WHERE team_id = ? AND created_at >= ?
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 5
        """,
            (team_id, start_date.isoformat()),
        )

        top_users = [
            {"user_id": r[0], "count": r[1], "cost": r[2]} for r in cursor.fetchall()
        ]

        # 查询每日分布
        cursor.execute(
            """
            SELECT
                DATE(created_at) as date,
                COUNT(*) as count,
                SUM(tokens_used) as tokens,
                SUM(cost) as cost
            FROM usage_records
            WHERE team_id = ? AND created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date
        """,
            (team_id, start_date.isoformat()),
        )

        daily_breakdown = [
            {"date": r[0], "count": r[1], "tokens": r[2], "cost": r[3]}
            for r in cursor.fetchall()
        ]

        conn.close()

        return TeamStats(
            team_id=team_id,
            period=period,
            total_tasks=row[0] or 0,
            successful_tasks=row[1] or 0,
            failed_tasks=row[2] or 0,
            total_tokens=row[3] or 0,
            total_cost=row[4] or 0.0,
            avg_execution_time=row[5] or 0.0,
            top_models=top_models,
            top_users=top_users,
            daily_breakdown=daily_breakdown,
        )

    def get_user_stats(
        self, user_id: str, team_id: str, period: str = "week"
    ) -> UserStats:
        """
        获取用户统计

        Args:
            user_id: 用户 ID
            team_id: 团队 ID
            period: 统计周期

        Returns:
            UserStats: 统计数据
        """
        now = datetime.now()
        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        else:
            start_date = now - timedelta(days=30)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(tokens_used) as total_tokens,
                SUM(cost) as total_cost,
                AVG(execution_time) as avg_time
            FROM usage_records
            WHERE user_id = ? AND team_id = ? AND created_at >= ?
        """,
            (user_id, team_id, start_date.isoformat()),
        )

        row = cursor.fetchone()

        # 查询最常用模型
        cursor.execute(
            """
            SELECT model, COUNT(*) as count
            FROM usage_records
            WHERE user_id = ? AND team_id = ? AND created_at >= ?
            GROUP BY model
            ORDER BY count DESC
            LIMIT 1
        """,
            (user_id, team_id, start_date.isoformat()),
        )

        fav_row = cursor.fetchone()
        favorite_model = fav_row[0] if fav_row else "none"

        conn.close()

        return UserStats(
            user_id=user_id,
            team_id=team_id,
            period=period,
            total_tasks=row[0] or 0,
            successful_tasks=row[1] or 0,
            total_tokens=row[2] or 0,
            total_cost=row[3] or 0.0,
            avg_execution_time=row[4] or 0.0,
            favorite_model=favorite_model,
        )

    def cleanup_old_records(self, days: int = 30) -> int:
        """
        清理旧记录

        Args:
            days: 保留天数

        Returns:
            int: 删除的记录数
        """
        cutoff = datetime.now() - timedelta(days=days)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM usage_records WHERE created_at < ?
        """,
            (cutoff.isoformat(),),
        )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    def get_all_teams(self) -> List[str]:
        """获取所有团队 ID"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT team_id FROM usage_records")
        teams = [row[0] for row in cursor.fetchall()]

        conn.close()
        return teams


# 全局实例
team_statistics = TeamStatistics()
