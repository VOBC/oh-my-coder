"""Tests for team/auth.py."""

from datetime import datetime, timedelta

import pytest

from src.team.auth import (
    Team,
    TeamAuth,
    TeamMember,
    UserSession,
    team_auth,
)
from src.team.task_sync import MemberRole

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth() -> TeamAuth:
    """Create a fresh TeamAuth instance."""
    return TeamAuth()


@pytest.fixture
def sample_team(auth: TeamAuth) -> Team:
    """Create a sample team with owner."""
    team = Team(
        team_id="team_test123",
        name="Test Team",
        owner_id="owner1",
        description="A test team",
        invite_code="ABC123",
    )
    team.members.append(
        TeamMember(
            user_id="owner1",
            team_id="team_test123",
            role=MemberRole.OWNER,
        )
    )
    auth._teams["team_test123"] = team
    auth._user_teams["owner1"] = "team_test123"
    auth._invite_codes["ABC123"] = "team_test123"
    return team


@pytest.fixture
def sample_member() -> TeamMember:
    """Create a sample team member."""
    return TeamMember(
        user_id="user1",
        team_id="team_test123",
        role=MemberRole.MEMBER,
        display_name="Test User",
        email="user@example.com",
    )


@pytest.fixture
def sample_session() -> UserSession:
    """Create a sample user session."""
    return UserSession(
        session_id="session_abc123",
        user_id="user1",
        team_id="team_test123",
        expires_at=datetime.now() + timedelta(hours=24),
    )


# ---------------------------------------------------------------------------
# TeamMember Dataclass
# ---------------------------------------------------------------------------

class TestTeamMember:
    def test_team_member_creation_defaults(self) -> None:
        member = TeamMember(user_id="user1", team_id="team1")
        assert member.user_id == "user1"
        assert member.team_id == "team1"
        assert member.role == MemberRole.MEMBER
        assert member.display_name == ""
        assert member.email == ""
        assert member.avatar_url is None
        assert isinstance(member.joined_at, datetime)
        assert isinstance(member.last_active, datetime)
        assert member.settings == {}

    def test_team_member_creation_custom(self) -> None:
        joined = datetime(2024, 1, 1, 12, 0, 0)
        last_active = datetime(2024, 1, 15, 10, 0, 0)
        member = TeamMember(
            user_id="user1",
            team_id="team1",
            role=MemberRole.ADMIN,
            display_name="Admin User",
            email="admin@example.com",
            avatar_url="https://example.com/avatar.png",
            joined_at=joined,
            last_active=last_active,
            settings={"theme": "dark"},
        )
        assert member.role == MemberRole.ADMIN
        assert member.display_name == "Admin User"
        assert member.email == "admin@example.com"
        assert member.avatar_url == "https://example.com/avatar.png"
        assert member.joined_at == joined
        assert member.last_active == last_active
        assert member.settings == {"theme": "dark"}

    def test_team_member_to_dict(self, sample_member: TeamMember) -> None:
        result = sample_member.to_dict()
        assert result["user_id"] == "user1"
        assert result["team_id"] == "team_test123"
        assert result["role"] == MemberRole.MEMBER.value
        assert result["display_name"] == "Test User"
        assert result["email"] == "user@example.com"
        assert result["avatar_url"] is None
        assert "joined_at" in result
        assert "last_active" in result
        assert result["settings"] == {}

    def test_team_member_to_dict_with_avatar(self) -> None:
        member = TeamMember(
            user_id="user1",
            team_id="team1",
            avatar_url="https://example.com/avatar.jpg",
        )
        result = member.to_dict()
        assert result["avatar_url"] == "https://example.com/avatar.jpg"

    def test_team_member_to_dict_isoformat_dates(self) -> None:
        joined = datetime(2024, 1, 1, 12, 0, 0)
        last_active = datetime(2024, 1, 15, 10, 0, 0)
        member = TeamMember(
            user_id="user1",
            team_id="team1",
            joined_at=joined,
            last_active=last_active,
        )
        result = member.to_dict()
        assert result["joined_at"] == "2024-01-01T12:00:00"
        assert result["last_active"] == "2024-01-15T10:00:00"


# ---------------------------------------------------------------------------
# Team Dataclass
# ---------------------------------------------------------------------------

class TestTeam:
    def test_team_creation_defaults(self) -> None:
        team = Team(team_id="team1", name="Team 1", owner_id="owner1")
        assert team.team_id == "team1"
        assert team.name == "Team 1"
        assert team.owner_id == "owner1"
        assert team.description == ""
        assert team.invite_code == ""
        assert team.settings == {}
        assert isinstance(team.created_at, datetime)
        assert team.members == []

    def test_team_creation_custom(self) -> None:
        created = datetime(2024, 1, 1, 12, 0, 0)
        team = Team(
            team_id="team1",
            name="Custom Team",
            owner_id="owner1",
            description="A custom team",
            invite_code="XYZ789",
            settings={"public": True},
            created_at=created,
        )
        assert team.description == "A custom team"
        assert team.invite_code == "XYZ789"
        assert team.settings == {"public": True}
        assert team.created_at == created

    def test_team_to_dict_no_members(self) -> None:
        team = Team(team_id="team1", name="Team 1", owner_id="owner1")
        result = team.to_dict()
        assert result["team_id"] == "team1"
        assert result["name"] == "Team 1"
        assert result["owner_id"] == "owner1"
        assert result["description"] == ""
        assert result["invite_code"] == ""
        assert result["settings"] == {}
        assert "created_at" in result
        assert result["member_count"] == 0
        assert result["members"] == []

    def test_team_to_dict_with_members(self, sample_member: TeamMember) -> None:
        team = Team(
            team_id="team1",
            name="Team 1",
            owner_id="owner1",
            members=[sample_member],
        )
        result = team.to_dict()
        assert result["member_count"] == 1
        assert len(result["members"]) == 1
        assert result["members"][0]["user_id"] == "user1"

    def test_team_to_dict_multiple_members(self) -> None:
        members = [
            TeamMember(user_id=f"user{i}", team_id="team1")
            for i in range(5)
        ]
        team = Team(team_id="team1", name="Team", owner_id="owner1", members=members)
        result = team.to_dict()
        assert result["member_count"] == 5
        assert len(result["members"]) == 5


# ---------------------------------------------------------------------------
# UserSession Dataclass
# ---------------------------------------------------------------------------

class TestUserSession:
    def test_user_session_creation_defaults(self) -> None:
        session = UserSession(session_id="sess1", user_id="user1", team_id="team1")
        assert session.session_id == "sess1"
        assert session.user_id == "user1"
        assert session.team_id == "team1"
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.expires_at, datetime)
        assert session.is_active is True
        # expires_at should be close to created_at (default timedelta is 0)
        assert abs((session.expires_at - session.created_at).total_seconds()) < 1

    def test_user_session_creation_custom(self) -> None:
        created = datetime(2024, 1, 1, 12, 0, 0)
        expires = datetime(2024, 1, 2, 12, 0, 0)
        session = UserSession(
            session_id="sess1",
            user_id="user1",
            team_id="team1",
            created_at=created,
            expires_at=expires,
            is_active=False,
        )
        assert session.created_at == created
        assert session.expires_at == expires
        assert session.is_active is False

    def test_user_session_is_valid_active_not_expired(self) -> None:
        session = UserSession(
            session_id="sess1",
            user_id="user1",
            team_id="team1",
            expires_at=datetime.now() + timedelta(hours=1),
            is_active=True,
        )
        assert session.is_valid() is True

    def test_user_session_is_valid_inactive(self) -> None:
        session = UserSession(
            session_id="sess1",
            user_id="user1",
            team_id="team1",
            expires_at=datetime.now() + timedelta(hours=1),
            is_active=False,
        )
        assert session.is_valid() is False

    def test_user_session_is_valid_expired(self) -> None:
        session = UserSession(
            session_id="sess1",
            user_id="user1",
            team_id="team1",
            expires_at=datetime.now() - timedelta(hours=1),
            is_active=True,
        )
        assert session.is_valid() is False

    def test_user_session_is_valid_expired_and_inactive(self) -> None:
        session = UserSession(
            session_id="sess1",
            user_id="user1",
            team_id="team1",
            expires_at=datetime.now() - timedelta(hours=1),
            is_active=False,
        )
        assert session.is_valid() is False

    def test_user_session_to_dict(self) -> None:
        created = datetime(2024, 1, 1, 12, 0, 0)
        expires = datetime(2024, 1, 2, 12, 0, 0)
        session = UserSession(
            session_id="sess1",
            user_id="user1",
            team_id="team1",
            created_at=created,
            expires_at=expires,
            is_active=True,
        )
        result = session.to_dict()
        assert result["session_id"] == "sess1"
        assert result["user_id"] == "user1"
        assert result["team_id"] == "team1"
        assert result["created_at"] == "2024-01-01T12:00:00"
        assert result["expires_at"] == "2024-01-02T12:00:00"
        assert result["is_active"] is True


# ---------------------------------------------------------------------------
# TeamAuth - Initialization
# ---------------------------------------------------------------------------

class TestTeamAuthInit:
    def test_init_creates_empty_structures(self) -> None:
        auth = TeamAuth()
        assert auth._teams == {}
        assert auth._user_teams == {}
        assert auth._sessions == {}
        assert auth._invite_codes == {}


# ---------------------------------------------------------------------------
# TeamAuth - _generate_id
# ---------------------------------------------------------------------------

class TestGenerateId:
    def test_generate_id_returns_string(self) -> None:
        auth = TeamAuth()
        result = auth._generate_id()
        assert isinstance(result, str)

    def test_generate_id_length(self) -> None:
        auth = TeamAuth()
        result = auth._generate_id()
        # secrets.token_hex(8) returns 16 hex characters
        assert len(result) == 16

    def test_generate_id_unique(self) -> None:
        auth = TeamAuth()
        ids = {auth._generate_id() for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# TeamAuth - _generate_invite_code
# ---------------------------------------------------------------------------

class TestGenerateInviteCode:
    def test_generate_invite_code_returns_string(self) -> None:
        auth = TeamAuth()
        result = auth._generate_invite_code()
        assert isinstance(result, str)

    def test_generate_invite_code_uppercase(self) -> None:
        auth = TeamAuth()
        result = auth._generate_invite_code()
        assert result == result.upper()

    def test_generate_invite_code_length(self) -> None:
        auth = TeamAuth()
        result = auth._generate_invite_code()
        # token_urlsafe(6) is ~8 characters, then upper()
        assert len(result) >= 6

    def test_generate_invite_code_unique(self) -> None:
        auth = TeamAuth()
        codes = {auth._generate_invite_code() for _ in range(100)}
        assert len(codes) == 100


# ---------------------------------------------------------------------------
# TeamAuth - _hash_password
# ---------------------------------------------------------------------------

class TestHashPassword:
    def test_hash_password_returns_hex_string(self) -> None:
        auth = TeamAuth()
        result = auth._hash_password("password123", "somesalt")
        assert isinstance(result, str)
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_password_consistent(self) -> None:
        auth = TeamAuth()
        result1 = auth._hash_password("password123", "somesalt")
        result2 = auth._hash_password("password123", "somesalt")
        assert result1 == result2

    def test_hash_password_different_salt(self) -> None:
        auth = TeamAuth()
        result1 = auth._hash_password("password123", "somesalt")
        result2 = auth._hash_password("password123", "different")
        assert result1 != result2

    def test_hash_password_different_password(self) -> None:
        auth = TeamAuth()
        result1 = auth._hash_password("password123", "somesalt")
        result2 = auth._hash_password("different", "somesalt")
        assert result1 != result2


# ---------------------------------------------------------------------------
# TeamAuth - create_team
# ---------------------------------------------------------------------------

class TestCreateTeam:
    @pytest.mark.asyncio
    async def test_create_team_success(self, auth: TeamAuth) -> None:
        team = await auth.create_team("New Team", "owner1", "A new team")

        assert isinstance(team, Team)
        assert team.name == "New Team"
        assert team.owner_id == "owner1"
        assert team.description == "A new team"
        assert team.team_id.startswith("team_")
        assert team.invite_code != ""
        assert len(team.members) == 1
        assert team.members[0].user_id == "owner1"
        assert team.members[0].role == MemberRole.OWNER

    @pytest.mark.asyncio
    async def test_create_team_stored_in_auth(self, auth: TeamAuth) -> None:
        team = await auth.create_team("Team", "owner1")

        assert team.team_id in auth._teams
        assert auth._teams[team.team_id] is team
        assert "owner1" in auth._user_teams
        assert auth._user_teams["owner1"] == team.team_id
        assert team.invite_code in auth._invite_codes
        assert auth._invite_codes[team.invite_code] == team.team_id

    @pytest.mark.asyncio
    async def test_create_team_default_description(self, auth: TeamAuth) -> None:
        team = await auth.create_team("Team", "owner1")

        assert team.description == ""

    @pytest.mark.asyncio
    async def test_create_team_generates_unique_ids(self, auth: TeamAuth) -> None:
        team1 = await auth.create_team("Team 1", "owner1")
        team2 = await auth.create_team("Team 2", "owner2")

        assert team1.team_id != team2.team_id
        assert team1.invite_code != team2.invite_code

    @pytest.mark.asyncio
    async def test_create_team_owner_joined_at(self, auth: TeamAuth) -> None:
        team = await auth.create_team("Team", "owner1")

        owner = team.members[0]
        assert isinstance(owner.joined_at, datetime)
        # Should be very recent
        assert (datetime.now() - owner.joined_at).total_seconds() < 5


# ---------------------------------------------------------------------------
# TeamAuth - join_team
# ---------------------------------------------------------------------------

class TestJoinTeam:
    @pytest.mark.asyncio
    async def test_join_team_success(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = await auth.join_team("ABC123", "user1", "Test User", "user@test.com")

        assert result is not None
        assert result.team_id == "team_test123"
        assert len(result.members) == 2
        assert any(m.user_id == "user1" for m in result.members)

        new_member = next(m for m in result.members if m.user_id == "user1")
        assert new_member.role == MemberRole.MEMBER
        assert new_member.display_name == "Test User"
        assert new_member.email == "user@test.com"

    @pytest.mark.asyncio
    async def test_join_team_user_added_to_user_teams(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        await auth.join_team("ABC123", "user1")
        assert "user1" in auth._user_teams
        assert auth._user_teams["user1"] == "team_test123"

    @pytest.mark.asyncio
    async def test_join_team_invalid_invite_code(self, auth: TeamAuth) -> None:
        result = await auth.join_team("INVALID", "user1")
        assert result is None

    @pytest.mark.asyncio
    async def test_join_team_team_not_found(
        self, auth: TeamAuth
    ) -> None:
        # Add invite code but not the team
        auth._invite_codes["XYZ789"] = "nonexistent"
        result = await auth.join_team("XYZ789", "user1")
        assert result is None

    @pytest.mark.asyncio
    async def test_join_team_already_member(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        # Add owner as already joined
        result = await auth.join_team("ABC123", "owner1")
        assert result is not None
        assert len(result.members) == 1  # No duplicate

    @pytest.mark.asyncio
    async def test_join_team_default_display_name_and_email(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = await auth.join_team("ABC123", "user1")

        new_member = next(m for m in result.members if m.user_id == "user1")
        assert new_member.display_name == ""
        assert new_member.email == ""


# ---------------------------------------------------------------------------
# TeamAuth - leave_team
# ---------------------------------------------------------------------------

class TestLeaveTeam:
    @pytest.mark.asyncio
    async def test_leave_team_success(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        # Add a member first
        sample_team.members.append(
            TeamMember(user_id="user1", team_id="team_test123")
        )
        auth._user_teams["user1"] = "team_test123"

        result = await auth.leave_team("user1", "team_test123")

        assert result is True
        assert len(sample_team.members) == 1
        assert all(m.user_id != "user1" for m in sample_team.members)
        assert "user1" not in auth._user_teams

    @pytest.mark.asyncio
    async def test_leave_team_owner_cannot_leave(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = await auth.leave_team("owner1", "team_test123")
        assert result is False
        # Owner should still be in team
        assert any(m.user_id == "owner1" for m in sample_team.members)

    @pytest.mark.asyncio
    async def test_leave_team_invalid_team(self, auth: TeamAuth) -> None:
        result = await auth.leave_team("user1", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_leave_team_user_not_member(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        """Test that leave_team returns False when user is not a member"""
        # user1 is not in sample_team's members
        result = await auth.leave_team("user1", "team_test123")
        assert result is False
        # Team should remain unchanged
        assert len(sample_team.members) == 1  # only owner
        assert sample_team.members[0].user_id == "owner1"

    @pytest.mark.asyncio
    async def test_leave_team_removes_from_user_teams(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        sample_team.members.append(
            TeamMember(user_id="user1", team_id="team_test123")
        )
        auth._user_teams["user1"] = "team_test123"

        await auth.leave_team("user1", "team_test123")

        assert "user1" not in auth._user_teams


# ---------------------------------------------------------------------------
# TeamAuth - delete_team
# ---------------------------------------------------------------------------

class TestDeleteTeam:
    @pytest.mark.asyncio
    async def test_delete_team_success(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        # Add some members
        sample_team.members.append(
            TeamMember(user_id="user1", team_id="team_test123")
        )
        sample_team.members.append(
            TeamMember(user_id="user2", team_id="team_test123")
        )
        auth._user_teams["user1"] = "team_test123"
        auth._user_teams["user2"] = "team_test123"

        result = await auth.delete_team("team_test123", "owner1")

        assert result is True
        assert "team_test123" not in auth._teams
        assert "user1" not in auth._user_teams
        assert "user2" not in auth._user_teams
        assert "owner1" not in auth._user_teams
        assert "ABC123" not in auth._invite_codes

    @pytest.mark.asyncio
    async def test_delete_team_not_owner(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = await auth.delete_team("team_test123", "user1")
        assert result is False
        assert "team_test123" in auth._teams

    @pytest.mark.asyncio
    async def test_delete_team_invalid_team(self, auth: TeamAuth) -> None:
        result = await auth.delete_team("nonexistent", "owner1")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_team_cleans_invite_code(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        await auth.delete_team("team_test123", "owner1")
        assert sample_team.invite_code not in auth._invite_codes


# ---------------------------------------------------------------------------
# TeamAuth - get_team
# ---------------------------------------------------------------------------

class TestGetTeam:
    @pytest.mark.asyncio
    async def test_get_team_exists(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = await auth.get_team("team_test123")
        assert result is not None
        assert result.team_id == "team_test123"
        assert result.name == "Test Team"

    @pytest.mark.asyncio
    async def test_get_team_not_exists(self, auth: TeamAuth) -> None:
        result = await auth.get_team("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# TeamAuth - get_user_team
# ---------------------------------------------------------------------------

class TestGetUserTeam:
    @pytest.mark.asyncio
    async def test_get_user_team_exists(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = await auth.get_user_team("owner1")
        assert result is not None
        assert result.team_id == "team_test123"

    @pytest.mark.asyncio
    async def test_get_user_team_not_in_team(self, auth: TeamAuth) -> None:
        result = await auth.get_user_team("user1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_team_invalid_user(self, auth: TeamAuth) -> None:
        result = await auth.get_user_team("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# TeamAuth - update_member_role
# ---------------------------------------------------------------------------

class TestUpdateMemberRole:
    @pytest.mark.asyncio
    async def test_update_member_role_success(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        # Add a member
        sample_team.members.append(
            TeamMember(user_id="user1", team_id="team_test123", role=MemberRole.MEMBER)
        )

        result = await auth.update_member_role(
            "team_test123", "user1", MemberRole.ADMIN, "owner1"
        )

        assert result is True
        user1 = next(m for m in sample_team.members if m.user_id == "user1")
        assert user1.role == MemberRole.ADMIN

    @pytest.mark.asyncio
    async def test_update_member_role_not_owner(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        sample_team.members.append(
            TeamMember(user_id="user1", team_id="team_test123")
        )

        result = await auth.update_member_role(
            "team_test123", "user1", MemberRole.ADMIN, "user1"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_member_role_invalid_team(self, auth: TeamAuth) -> None:
        result = await auth.update_member_role(
            "nonexistent", "user1", MemberRole.ADMIN, "owner1"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_update_member_role_user_not_in_team(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = await auth.update_member_role(
            "team_test123", "user1", MemberRole.ADMIN, "owner1"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_update_member_role_to_owner(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        sample_team.members.append(
            TeamMember(user_id="user1", team_id="team_test123", role=MemberRole.MEMBER)
        )

        result = await auth.update_member_role(
            "team_test123", "user1", MemberRole.OWNER, "owner1"
        )

        assert result is True
        user1 = next(m for m in sample_team.members if m.user_id == "user1")
        assert user1.role == MemberRole.OWNER


# ---------------------------------------------------------------------------
# TeamAuth - check_permission
# ---------------------------------------------------------------------------

class TestCheckPermission:
    def test_check_permission_owner_access(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = auth.check_permission("owner1", "team_test123", MemberRole.OWNER)
        assert result is True

    def test_check_permission_owner_admin(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = auth.check_permission("owner1", "team_test123", MemberRole.ADMIN)
        assert result is True

    def test_check_permission_owner_member(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = auth.check_permission("owner1", "team_test123", MemberRole.MEMBER)
        assert result is True

    def test_check_permission_admin_admin(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        sample_team.members.append(
            TeamMember(user_id="admin1", team_id="team_test123", role=MemberRole.ADMIN)
        )

        result = auth.check_permission("admin1", "team_test123", MemberRole.ADMIN)
        assert result is True

    def test_check_permission_admin_member(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        sample_team.members.append(
            TeamMember(user_id="admin1", team_id="team_test123", role=MemberRole.ADMIN)
        )

        result = auth.check_permission("admin1", "team_test123", MemberRole.MEMBER)
        assert result is True

    def test_check_permission_admin_owner(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        sample_team.members.append(
            TeamMember(user_id="admin1", team_id="team_test123", role=MemberRole.ADMIN)
        )

        result = auth.check_permission("admin1", "team_test123", MemberRole.OWNER)
        assert result is False

    def test_check_permission_member_member(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        sample_team.members.append(
            TeamMember(user_id="user1", team_id="team_test123", role=MemberRole.MEMBER)
        )

        result = auth.check_permission("user1", "team_test123", MemberRole.MEMBER)
        assert result is True

    def test_check_permission_member_admin(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        sample_team.members.append(
            TeamMember(user_id="user1", team_id="team_test123", role=MemberRole.MEMBER)
        )

        result = auth.check_permission("user1", "team_test123", MemberRole.ADMIN)
        assert result is False

    def test_check_permission_not_in_team(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        result = auth.check_permission("user1", "team_test123", MemberRole.MEMBER)
        assert result is False

    def test_check_permission_invalid_team(self, auth: TeamAuth) -> None:
        result = auth.check_permission("user1", "nonexistent", MemberRole.MEMBER)
        assert result is False

    def test_check_permission_role_order(self, auth: TeamAuth) -> None:
        """Test that role hierarchy is correct."""
        role_order = {
            MemberRole.OWNER: 3,
            MemberRole.ADMIN: 2,
            MemberRole.MEMBER: 1,
        }
        assert role_order[MemberRole.OWNER] > role_order[MemberRole.ADMIN]
        assert role_order[MemberRole.ADMIN] > role_order[MemberRole.MEMBER]


# ---------------------------------------------------------------------------
# TeamAuth - create_session
# ---------------------------------------------------------------------------

class TestCreateSession:
    @pytest.mark.asyncio
    async def test_create_session_success(self, auth: TeamAuth) -> None:
        session = await auth.create_session("user1", "team1")

        assert isinstance(session, UserSession)
        assert session.user_id == "user1"
        assert session.team_id == "team1"
        assert session.session_id.startswith("session_")
        assert session.is_active is True
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.expires_at, datetime)

    @pytest.mark.asyncio
    async def test_create_session_default_expiry(self, auth: TeamAuth) -> None:
        session = await auth.create_session("user1", "team1")

        # Default is 24 hours
        delta = session.expires_at - session.created_at
        assert delta.total_seconds() == pytest.approx(24 * 3600, rel=1)

    @pytest.mark.asyncio
    async def test_create_session_custom_expiry(self, auth: TeamAuth) -> None:
        session = await auth.create_session("user1", "team1", expires_in_hours=48)

        delta = session.expires_at - session.created_at
        assert delta.total_seconds() == pytest.approx(48 * 3600, rel=1)

    @pytest.mark.asyncio
    async def test_create_session_stored_in_auth(self, auth: TeamAuth) -> None:
        session = await auth.create_session("user1", "team1")

        assert session.session_id in auth._sessions
        assert auth._sessions[session.session_id] is session

    @pytest.mark.asyncio
    async def test_create_session_unique_ids(self, auth: TeamAuth) -> None:
        session1 = await auth.create_session("user1", "team1")
        session2 = await auth.create_session("user2", "team1")

        assert session1.session_id != session2.session_id


# ---------------------------------------------------------------------------
# TeamAuth - validate_session
# ---------------------------------------------------------------------------

class TestValidateSession:
    @pytest.mark.asyncio
    async def test_validate_session_valid(
        self, auth: TeamAuth, sample_session: UserSession
    ) -> None:
        auth._sessions["session_abc123"] = sample_session

        result = await auth.validate_session("session_abc123")
        assert result is not None
        assert result.session_id == "session_abc123"

    @pytest.mark.asyncio
    async def test_validate_session_not_found(self, auth: TeamAuth) -> None:
        result = await auth.validate_session("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_session_inactive(
        self, auth: TeamAuth, sample_session: UserSession
    ) -> None:
        sample_session.is_active = False
        auth._sessions["session_abc123"] = sample_session

        result = await auth.validate_session("session_abc123")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_session_expired(
        self, auth: TeamAuth
    ) -> None:
        expired_session = UserSession(
            session_id="expired",
            user_id="user1",
            team_id="team1",
            expires_at=datetime.now() - timedelta(hours=1),
            is_active=True,
        )
        auth._sessions["expired"] = expired_session

        result = await auth.validate_session("expired")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_session_both_invalid(
        self, auth: TeamAuth
    ) -> None:
        expired_inactive = UserSession(
            session_id="both_invalid",
            user_id="user1",
            team_id="team1",
            expires_at=datetime.now() - timedelta(hours=1),
            is_active=False,
        )
        auth._sessions["both_invalid"] = expired_inactive

        result = await auth.validate_session("both_invalid")
        assert result is None


# ---------------------------------------------------------------------------
# TeamAuth - invalidate_session
# ---------------------------------------------------------------------------

class TestInvalidateSession:
    @pytest.mark.asyncio
    async def test_invalidate_session_success(
        self, auth: TeamAuth, sample_session: UserSession
    ) -> None:
        auth._sessions["session_abc123"] = sample_session

        result = await auth.invalidate_session("session_abc123")

        assert result is True
        assert sample_session.is_active is False

    @pytest.mark.asyncio
    async def test_invalidate_session_not_found(self, auth: TeamAuth) -> None:
        result = await auth.invalidate_session("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_session_marks_inactive(
        self, auth: TeamAuth, sample_session: UserSession
    ) -> None:
        auth._sessions["session_abc123"] = sample_session
        await auth.invalidate_session("session_abc123")

        # Session should still be in _sessions but marked inactive
        assert "session_abc123" in auth._sessions
        assert auth._sessions["session_abc123"].is_active is False


# ---------------------------------------------------------------------------
# TeamAuth - regenerate_invite_code
# ---------------------------------------------------------------------------

class TestRegenerateInviteCode:
    @pytest.mark.asyncio
    async def test_regenerate_invite_code_success(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        old_code = sample_team.invite_code

        new_code = await auth.regenerate_invite_code("team_test123", "owner1")

        assert new_code is not None
        assert new_code != old_code
        assert sample_team.invite_code == new_code
        assert old_code not in auth._invite_codes
        assert new_code in auth._invite_codes
        assert auth._invite_codes[new_code] == "team_test123"

    @pytest.mark.asyncio
    async def test_regenerate_invite_code_not_owner(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        old_code = sample_team.invite_code

        result = await auth.regenerate_invite_code("team_test123", "user1")

        assert result is None
        assert sample_team.invite_code == old_code

    @pytest.mark.asyncio
    async def test_regenerate_invite_code_invalid_team(self, auth: TeamAuth) -> None:
        result = await auth.regenerate_invite_code("nonexistent", "owner1")
        assert result is None

    @pytest.mark.asyncio
    async def test_regenerate_invite_code_unique(
        self, auth: TeamAuth, sample_team: Team
    ) -> None:
        # Generate multiple codes to ensure uniqueness
        codes = set()
        for _ in range(10):
            code = await auth.regenerate_invite_code("team_test123", "owner1")
            codes.add(code)

        # Might be flaky due to randomness, but very unlikely to collide
        assert len(codes) == 10


# ---------------------------------------------------------------------------
# Global Instance
# ---------------------------------------------------------------------------

class TestGlobalInstance:
    def test_team_auth_global_instance(self) -> None:
        assert isinstance(team_auth, TeamAuth)
