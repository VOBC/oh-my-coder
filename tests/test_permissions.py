"""Tests for security/permissions.py."""
import re

from src.security.permissions import (
    CheckResult,
    PermissionGuard,
    PermissionRule,
    check_command,
    needs_approval,
)

BUILTIN_DANGEROUS_PATTERNS = PermissionGuard.BUILTIN_DANGEROUS_PATTERNS


# ─────────────────────────────────────────────────────────────
# PermissionRule
# ─────────────────────────────────────────────────────────────


class TestPermissionRule:
    def test_defaults(self):
        rule = PermissionRule()
        assert rule.allowed_patterns == []
        assert rule.denied_patterns == []
        assert rule.require_approval == []
        assert rule.max_command_length == 10000

    def test_from_dict(self):
        data = {
            "allowed_patterns": ["ls.*"],
            "denied_patterns": ["rm.*"],
            "require_approval": ["git push.*"],
            "max_command_length": 5000,
        }
        rule = PermissionRule.from_dict(data)
        assert rule.allowed_patterns == ["ls.*"]
        assert rule.denied_patterns == ["rm.*"]
        assert rule.require_approval == ["git push.*"]
        assert rule.max_command_length == 5000

    def test_from_dict_partial(self):
        data = {"allowed_patterns": ["ls"]}
        rule = PermissionRule.from_dict(data)
        assert rule.allowed_patterns == ["ls"]
        assert rule.denied_patterns == []
        assert rule.max_command_length == 10000

    def test_to_dict(self):
        rule = PermissionRule(
            allowed_patterns=["ls"],
            denied_patterns=["rm"],
            require_approval=["git push"],
            max_command_length=5000,
        )
        d = rule.to_dict()
        assert d["allowed_patterns"] == ["ls"]
        assert d["denied_patterns"] == ["rm"]
        assert d["require_approval"] == ["git push"]
        assert d["max_command_length"] == 5000

    def test_compile_patterns(self):
        rule = PermissionRule(
            allowed_patterns=["ls.*"],
            denied_patterns=["rm.*"],
            require_approval=["git push.*"],
        )
        rule.compile_patterns()
        assert len(rule._allowed_re) == 1
        assert isinstance(rule._allowed_re[0], re.Pattern)
        assert len(rule._denied_re) == 1
        assert len(rule._approval_re) == 1


# ─────────────────────────────────────────────────────────────
# CheckResult
# ─────────────────────────────────────────────────────────────


class TestCheckResult:
    def test_allowed_true(self):
        r = CheckResult(allowed=True, reason="OK")
        assert r.allowed is True
        assert r.reason == "OK"

    def test_allowed_false(self):
        r = CheckResult(allowed=False, reason="Blocked")
        assert r.allowed is False

    def test_to_tuple(self):
        r = CheckResult(allowed=True, reason="whitelist")
        assert r.to_tuple() == (True, "whitelist")

    def test_to_tuple_false(self):
        r = CheckResult(allowed=False, reason="denied")
        assert r.to_tuple() == (False, "denied")


# ─────────────────────────────────────────────────────────────
# PermissionGuard - init & compile
# ─────────────────────────────────────────────────────────────


class TestPermissionGuardInit:
    def test_init_default(self):
        guard = PermissionGuard()
        assert guard.rules is not None  # default PermissionRule
        assert guard._compiled is True  # _compile is called in __init__

    def test_init_with_rules(self):
        rule = PermissionRule(allowed_patterns=["ls.*"])
        guard = PermissionGuard(rule)
        assert guard.rules is rule

    def test_compile_idempotent(self):
        rule = PermissionRule(allowed_patterns=["ls.*"])
        guard = PermissionGuard(rule)
        assert guard._compiled is True
        guard._compile()  # should be no-op
        assert guard._compiled is True

    def test_safe_compile_skips_invalid(self):
        """Invalid regex patterns should be skipped, not crash."""
        rule = PermissionRule(allowed_patterns=["[invalid", "ls.*"])
        guard = PermissionGuard(rule)
        # Only the valid pattern should be compiled
        assert len(guard._allowed_re) == 1


# ─────────────────────────────────────────────────────────────
# PermissionGuard - check: empty / too long
# ─────────────────────────────────────────────────────────────


class TestPermissionGuardCheckEmpty:
    def test_empty_string(self):
        guard = PermissionGuard()
        result = guard.check("")
        assert result.allowed is False
        assert "为空" in result.reason

    def test_whitespace_only(self):
        guard = PermissionGuard()
        result = guard.check("   ")
        assert result.allowed is False
        assert "为空" in result.reason

    def test_none_not_possible(self):
        """check() takes a string, passing None returns allowed=False."""
        guard = PermissionGuard()
        result = guard.check("")  # empty string, not None
        assert result.allowed is False

    def test_too_long(self):
        rule = PermissionRule(max_command_length=5)
        guard = PermissionGuard(rule)
        result = guard.check("echo hello")
        assert result.allowed is False
        assert "超过限制" in result.reason


# ─────────────────────────────────────────────────────────────
# PermissionGuard - check: built-in dangerous patterns
# ─────────────────────────────────────────────────────────────


class TestPermissionGuardCheckBuiltin:
    def test_rm_rf_root(self):
        guard = PermissionGuard()
        result = guard.check("rm -rf /")
        assert result.allowed is False
        assert "危险" in result.reason

    def test_rm_rf_var(self):
        guard = PermissionGuard()
        result = guard.check("rm -rf /var")
        assert result.allowed is False

    def test_fork_bomb(self):
        guard = PermissionGuard()
        result = guard.check(":(){ :|:& };:")
        assert result.allowed is False

    def test_dd_command(self):
        guard = PermissionGuard()
        result = guard.check("dd if=/dev/zero of=/dev/sda")
        assert result.allowed is False

    def test_builtin_patterns_compiled(self):
        guard = PermissionGuard()
        assert len(guard._builtin_re) == len(guard.BUILTIN_DANGEROUS_PATTERNS)


# ─────────────────────────────────────────────────────────────
# PermissionGuard - check: denied patterns
# ─────────────────────────────────────────────────────────────


class TestPermissionGuardCheckDenied:
    def test_denied_pattern_match(self):
        rule = PermissionRule(denied_patterns=[r"git\s+push\s+--force"])
        guard = PermissionGuard(rule)
        result = guard.check("git push --force origin main")
        assert result.allowed is False
        assert "黑名单" in result.reason

    def test_denied_pattern_no_match(self):
        rule = PermissionRule(denied_patterns=[r"git\s+push\s+--force"])
        guard = PermissionGuard(rule)
        result = guard.check("ls -la")
        assert result.allowed is True  # no whitelist = allow all

    def test_denied_pattern_ignore_case(self):
        rule = PermissionRule(denied_patterns=[r"RM\s+-RF"])
        guard = PermissionGuard(rule)
        result = guard.check("rm -rf /")
        # BUILTIN pattern matches first
        assert result.allowed is False


# ─────────────────────────────────────────────────────────────
# PermissionGuard - check: allowed patterns (whitelist)
# ─────────────────────────────────────────────────────────────


class TestPermissionGuardCheckAllowed:
    def test_whitelist_allows(self):
        rule = PermissionRule(allowed_patterns=[r"ls.*", r"echo.*"])
        guard = PermissionGuard(rule)
        result = guard.check("ls -la")
        assert result.allowed is True
        assert "白名单" in result.reason

    def test_whitelist_denies(self):
        rule = PermissionRule(allowed_patterns=[r"ls.*"])
        guard = PermissionGuard(rule)
        # git status 不匹配内置危险模式，也不在白名单
        result = guard.check("git status")
        assert result.allowed is False
        assert "不在白名单" in result.reason

    def test_whitelist_empty_allows_all(self):
        rule = PermissionRule(allowed_patterns=[])
        guard = PermissionGuard(rule)
        result = guard.check("ls -la")
        assert result.allowed is True  # no whitelist = allow

    def test_whitelist_with_denied(self):
        rule = PermissionRule(
            allowed_patterns=[r"git.*"],
            denied_patterns=[r"git\s+push\s+--force"],
        )
        guard = PermissionGuard(rule)
        # denied checked first
        result = guard.check("git push --force origin main")
        assert result.allowed is False


# ─────────────────────────────────────────────────────────────
# PermissionGuard - needs_approval
# ─────────────────────────────────────────────────────────────


class TestPermissionGuardNeedsApproval:
    def test_needs_approval_true(self):
        rule = PermissionRule(require_approval=[r"git push.*"])
        guard = PermissionGuard(rule)
        assert guard.needs_approval("git push origin main") is True

    def test_needs_approval_false(self):
        rule = PermissionRule(require_approval=[r"git push.*"])
        guard = PermissionGuard(rule)
        assert guard.needs_approval("git status") is False

    def test_needs_approval_empty(self):
        guard = PermissionGuard(PermissionRule())
        assert guard.needs_approval("any command") is False


# ─────────────────────────────────────────────────────────────
# PermissionGuard - validate_rules
# ─────────────────────────────────────────────────────────────


class TestPermissionGuardValidateRules:
    def test_valid_rules(self):
        rule = PermissionRule(
            allowed_patterns=[r"ls.*"],
            denied_patterns=[r"rm.*"],
            require_approval=[r"git push.*"],
        )
        guard = PermissionGuard(rule)
        errors = guard.validate_rules()
        assert errors == []

    def test_invalid_allowed_pattern(self):
        rule = PermissionRule(allowed_patterns=["[invalid"])
        guard = PermissionGuard(rule)
        errors = guard.validate_rules()
        assert len(errors) > 0
        assert "allowed_patterns" in errors[0]

    def test_invalid_denied_pattern(self):
        rule = PermissionRule(denied_patterns=["[invalid"])
        guard = PermissionGuard(rule)
        errors = guard.validate_rules()
        assert len(errors) > 0
        assert "denied_patterns" in errors[0]

    def test_invalid_approval_pattern(self):
        rule = PermissionRule(require_approval=["[invalid"])
        guard = PermissionGuard(rule)
        errors = guard.validate_rules()
        assert len(errors) > 0
        assert "require_approval" in errors[0]


# ─────────────────────────────────────────────────────────────
# PermissionGuard - from_agent_config
# ─────────────────────────────────────────────────────────────


class TestPermissionGuardFromAgentConfig:
    def test_from_dict(self):
        config = {
            "permissions": {
                "allowed_patterns": ["ls.*"],
                "denied_patterns": ["rm.*"],
                "require_approval": ["git push.*"],
            }
        }
        guard = PermissionGuard.from_agent_config(config)
        assert isinstance(guard, PermissionGuard)
        assert guard.rules.allowed_patterns == ["ls.*"]

    def test_from_dict_no_permissions(self):
        config = {}
        guard = PermissionGuard.from_agent_config(config)
        assert isinstance(guard, PermissionGuard)
        assert guard.rules.allowed_patterns == []

    def test_from_dict_partial(self):
        config = {"permissions": {"allowed_patterns": ["ls"]}}
        guard = PermissionGuard.from_agent_config(config)
        assert guard.rules.allowed_patterns == ["ls"]
        assert guard.rules.denied_patterns == []


# ─────────────────────────────────────────────────────────────
# Convenience functions
# ─────────────────────────────────────────────────────────────


class TestCheckCommand:
    def test_check_command_allowed(self):
        result = check_command("ls -la")
        assert isinstance(result, CheckResult)
        assert result.allowed is True

    def test_check_command_denied(self):
        result = check_command("rm -rf /")
        assert result.allowed is False

    def test_check_command_with_rules(self):
        rule = PermissionRule(allowed_patterns=[r"ls.*"])
        result = check_command("ls -la", rule)
        assert result.allowed is True


class TestNeedsApproval:
    def test_needs_approval_true(self):
        rule = PermissionRule(require_approval=[r"git push.*"])
        assert needs_approval("git push origin", rule) is True

    def test_needs_approval_false(self):
        rule = PermissionRule(require_approval=[r"git push.*"])
        assert needs_approval("git status", rule) is False


# ─────────────────────────────────────────────────────────────
# BUILTIN_DANGEROUS_PATTERNS
# ─────────────────────────────────────────────────────────────


class TestBuiltinPatterns:
    def test_all_compile(self):
        """All built-in patterns should be valid regex."""
        for p in BUILTIN_DANGEROUS_PATTERNS:
            compiled = re.compile(p, re.IGNORECASE)
            assert isinstance(compiled, re.Pattern)

    def test_pattern_rm_rf_root(self):
        compiled = re.compile(BUILTIN_DANGEROUS_PATTERNS[0], re.IGNORECASE)
        assert compiled.search("rm -rf /") is not None

    def test_pattern_fork_bomb(self):
        compiled = re.compile(BUILTIN_DANGEROUS_PATTERNS[2], re.IGNORECASE)
        assert compiled.search(":(){ :|:& };:") is not None
