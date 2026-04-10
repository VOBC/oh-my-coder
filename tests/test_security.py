"""
测试权限治理模块
"""


from src.security.permissions import (
    PermissionRule,
    PermissionGuard,
    check_command,
    needs_approval,
)


class TestPermissionRule:
    """PermissionRule 测试"""

    def test_from_dict(self) -> None:
        data = {
            "allowed_patterns": ["git", "grep"],
            "denied_patterns": ["rm -rf", "dd if="],
            "require_approval": ["shell>dd", "shell>mkfs"],
        }
        rule = PermissionRule.from_dict(data)

        assert rule.allowed_patterns == ["git", "grep"]
        assert rule.denied_patterns == ["rm -rf", "dd if="]
        assert rule.require_approval == ["shell>dd", "shell>mkfs"]

    def test_to_dict(self) -> None:
        rule = PermissionRule(
            allowed_patterns=["ls"],
            denied_patterns=["rm"],
        )
        data = rule.to_dict()
        assert data["allowed_patterns"] == ["ls"]
        assert data["denied_patterns"] == ["rm"]


class TestPermissionGuard:
    """PermissionGuard 测试"""

    def test_builtin_dangerous_rm_rf(self) -> None:
        guard = PermissionGuard()
        result = guard.check("rm -rf /tmp/test")
        assert result.allowed is False
        assert "危险" in result.reason or "内置" in result.reason

    def test_builtin_dangerous_fork_bomb(self) -> None:
        guard = PermissionGuard()
        result = guard.check(":(){ :|:& };:")
        assert result.allowed is False

    def test_builtin_dangerous_dd(self) -> None:
        guard = PermissionGuard()
        result = guard.check("dd if=/dev/zero of=/dev/sda bs=1M count=1")
        assert result.allowed is False

    def test_allowed_command(self) -> None:
        guard = PermissionGuard()
        result = guard.check("git status")
        assert result.allowed is True

    def test_empty_command(self) -> None:
        guard = PermissionGuard()
        result = guard.check("")
        assert result.allowed is False
        assert "空" in result.reason

    def test_whitelist_mode(self) -> None:
        rule = PermissionRule(
            allowed_patterns=["^git status$", "^ls"],
            denied_patterns=[],
        )
        guard = PermissionGuard(rule)

        # 白名单内
        assert guard.check("git status").allowed is True
        # 白名单外
        assert guard.check("git commit").allowed is False

    def test_blacklist_overrides(self) -> None:
        rule = PermissionRule(
            allowed_patterns=[".*"],  # 全部允许
            denied_patterns=["rm -rf"],
        )
        guard = PermissionGuard(rule)

        assert guard.check("git commit").allowed is True

    def test_max_command_length(self) -> None:
        rule = PermissionRule(max_command_length=10)
        guard = PermissionGuard(rule)

        result = guard.check("a" * 20)
        assert result.allowed is False
        assert "长度" in result.reason

    def test_needs_approval(self) -> None:
        rule = PermissionRule(
            require_approval=["dd", "mkfs", "shell>sudo"],
        )
        guard = PermissionGuard(rule)

        assert guard.needs_approval("dd if=/dev/zero of=/tmp/test") is True
        assert guard.needs_approval("mkfs.ext4 /dev/sda1") is True
        assert guard.needs_approval("git status") is False

    def test_from_agent_config(self) -> None:
        config = {
            "permissions": {
                "allowed_patterns": ["git", "ls"],
                "denied_patterns": ["rm -rf /"],
                "require_approval": ["sudo"],
            }
        }
        guard = PermissionGuard.from_agent_config(config)
        assert guard.check("git status").allowed is True
        assert guard.check("rm -rf /").allowed is False

    def test_validate_rules_invalid_regex(self) -> None:
        rule = PermissionRule(
            denied_patterns=["[invalid("],
        )
        guard = PermissionGuard(rule)
        errors = guard.validate_rules()
        assert len(errors) > 0
        assert "denied_patterns" in errors[0]

    def test_case_insensitive(self) -> None:
        guard = PermissionGuard()
        # 内置危险模式大小写不敏感
        result = guard.check("RM -RF /TMP")
        assert result.allowed is False


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_check_command_default(self) -> None:
        result = check_command("git status")
        assert result.allowed is True

    def test_check_command_dangerous(self) -> None:
        result = check_command("rm -rf /")
        assert result.allowed is False

    def test_needs_approval_default(self) -> None:
        assert needs_approval("git status") is False
        # 内置不拦截普通命令
