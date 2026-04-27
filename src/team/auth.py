from __future__ import annotations
"""
团队认证模块

管理团队创建、成员管理和权限控制。
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .task_sync import MemberRole


@dataclass
class TeamMember:
    """团队成员"""

    user_id: str
    team_id: str
    role: MemberRole = MemberRole.MEMBER
    display_name: str = ""
    email: str = ""
    avatar_url: str | None = None
    joined_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "team_id": self.team_id,
            "role": self.role.value,
            "display_name": self.display_name,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "joined_at": self.joined_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "settings": self.settings,
        }


@dataclass
class Team:
    """团队"""

    team_id: str
    name: str
    owner_id: str
    description: str = ""
    invite_code: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    members: list[TeamMember] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "description": self.description,
            "invite_code": self.invite_code,
            "settings": self.settings,
            "created_at": self.created_at.isoformat(),
            "member_count": len(self.members),
            "members": [m.to_dict() for m in self.members],
        }


@dataclass
class UserSession:
    """用户会话"""

    session_id: str
    user_id: str
    team_id: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

    def is_valid(self) -> bool:
        return self.is_active and datetime.now() < self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_active": self.is_active,
        }


class TeamAuth:
    """
    团队认证管理器

    功能：
    - 创建/删除团队
    - 加入/退出团队
    - 成员管理
    - 权限验证
    """

    def __init__(self):
        self._teams: dict[str, Team] = {}
        self._user_teams: dict[str, str] = {}  # user_id -> team_id
        self._sessions: dict[str, UserSession] = {}
        self._invite_codes: dict[str, str] = {}  # invite_code -> team_id

    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return secrets.token_hex(8)

    def _generate_invite_code(self) -> str:
        """生成邀请码"""
        return secrets.token_urlsafe(6).upper()

    def _hash_password(self, password: str, salt: str) -> str:
        """哈希密码（PBKDF2-SHA256，100k 迭代）"""
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100_000,
        ).hex()

    async def create_team(
        self,
        name: str,
        owner_id: str,
        description: str = "",
    ) -> Team:
        """
        创建团队

        Args:
            name: 团队名称
            owner_id: 所有者 ID
            description: 团队描述

        Returns:
            Team: 创建的团队
        """
        team_id = f"team_{self._generate_id()}"
        invite_code = self._generate_invite_code()

        owner_member = TeamMember(
            user_id=owner_id,
            team_id=team_id,
            role=MemberRole.OWNER,
            joined_at=datetime.now(),
        )

        team = Team(
            team_id=team_id,
            name=name,
            owner_id=owner_id,
            description=description,
            invite_code=invite_code,
            members=[owner_member],
        )

        self._teams[team_id] = team
        self._user_teams[owner_id] = team_id
        self._invite_codes[invite_code] = team_id

        return team

    async def join_team(
        self,
        invite_code: str,
        user_id: str,
        display_name: str = "",
        email: str = "",
    ) -> Team | None:
        """
        加入团队

        Args:
            invite_code: 邀请码
            user_id: 用户 ID
            display_name: 显示名称
            email: 邮箱

        Returns:
            Team: 加入的团队
        """
        team_id = self._invite_codes.get(invite_code)
        if not team_id:
            return None

        team = self._teams.get(team_id)
        if not team:
            return None

        # 检查是否已加入
        if any(m.user_id == user_id for m in team.members):
            return team

        member = TeamMember(
            user_id=user_id,
            team_id=team_id,
            role=MemberRole.MEMBER,
            display_name=display_name,
            email=email,
            joined_at=datetime.now(),
        )

        team.members.append(member)
        self._user_teams[user_id] = team_id

        return team

    async def leave_team(self, user_id: str, team_id: str) -> bool:
        """
        离开团队

        Args:
            user_id: 用户 ID
            team_id: 团队 ID

        Returns:
            bool: 是否成功
        """
        team = self._teams.get(team_id)
        if not team:
            return False

        # 所有者不能离开
        if team.owner_id == user_id:
            return False

        team.members = [m for m in team.members if m.user_id != user_id]
        self._user_teams.pop(user_id, None)

        return True

    async def delete_team(self, team_id: str, requester_id: str) -> bool:
        """
        删除团队

        Args:
            team_id: 团队 ID
            requester_id: 请求者 ID

        Returns:
            bool: 是否成功
        """
        team = self._teams.get(team_id)
        if not team:
            return False

        # 只有所有者可以删除
        if team.owner_id != requester_id:
            return False

        # 清理用户关联
        for member in team.members:
            self._user_teams.pop(member.user_id, None)

        # 清理邀请码
        self._invite_codes.pop(team.invite_code, None)

        del self._teams[team_id]

        return True

    async def get_team(self, team_id: str) -> Team | None:
        """获取团队"""
        return self._teams.get(team_id)

    async def get_user_team(self, user_id: str) -> Team | None:
        """获取用户所在团队"""
        team_id = self._user_teams.get(user_id)
        if team_id:
            return self._teams.get(team_id)
        return None

    async def update_member_role(
        self,
        team_id: str,
        user_id: str,
        new_role: MemberRole,
        requester_id: str,
    ) -> bool:
        """
        更新成员角色

        Args:
            team_id: 团队 ID
            user_id: 目标用户 ID
            new_role: 新角色
            requester_id: 请求者 ID

        Returns:
            bool: 是否成功
        """
        team = self._teams.get(team_id)
        if not team:
            return False

        # 只有所有者可以更改角色
        if team.owner_id != requester_id:
            return False

        for member in team.members:
            if member.user_id == user_id:
                member.role = new_role
                return True

        return False

    def check_permission(
        self,
        user_id: str,
        team_id: str,
        required_role: MemberRole,
    ) -> bool:
        """
        检查权限

        Args:
            user_id: 用户 ID
            team_id: 团队 ID
            required_role: 需要的角色

        Returns:
            bool: 是否有权限
        """
        team = self._teams.get(team_id)
        if not team:
            return False

        for member in team.members:
            if member.user_id == user_id:
                role_order = {
                    MemberRole.OWNER: 3,
                    MemberRole.ADMIN: 2,
                    MemberRole.MEMBER: 1,
                }
                return role_order.get(member.role, 0) >= role_order.get(
                    required_role, 0
                )

        return False

    async def create_session(
        self,
        user_id: str,
        team_id: str,
        expires_in_hours: int = 24,
    ) -> UserSession:
        """
        创建会话

        Args:
            user_id: 用户 ID
            team_id: 团队 ID
            expires_in_hours: 过期时间（小时）

        Returns:
            UserSession: 创建的会话
        """
        session_id = f"session_{self._generate_id()}"

        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            team_id=team_id,
            expires_at=datetime.now().timestamp() + expires_in_hours * 3600,
        )

        self._sessions[session_id] = session
        return session

    async def validate_session(self, session_id: str) -> UserSession | None:
        """验证会话"""
        session = self._sessions.get(session_id)
        if session and session.is_valid():
            return session
        return None

    async def invalidate_session(self, session_id: str) -> bool:
        """使会话失效"""
        if session_id in self._sessions:
            self._sessions[session_id].is_active = False
            return True
        return False

    async def regenerate_invite_code(
        self, team_id: str, requester_id: str
    ) -> str | None:
        """
        重新生成邀请码

        Args:
            team_id: 团队 ID
            requester_id: 请求者 ID

        Returns:
            str: 新邀请码
        """
        team = self._teams.get(team_id)
        if not team or team.owner_id != requester_id:
            return None

        # 删除旧邀请码
        self._invite_codes.pop(team.invite_code, None)

        # 生成新邀请码
        team.invite_code = self._generate_invite_code()
        self._invite_codes[team.invite_code] = team_id

        return team.invite_code


# 全局实例
team_auth = TeamAuth()
