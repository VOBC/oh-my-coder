"""
权限治理模块

功能：
- 基于配置文件规则的权限检查
- 白名单/黑名单正则匹配
- 高风险命令审批拦截
- omc security check <cmd> 预检命令
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


# ─────────────────────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────────────────────


@dataclass
class PermissionRule:
    """权限规则"""

    allowed_patterns: list[str] = field(default_factory=list)
    denied_patterns: list[str] = field(default_factory=list)
    require_approval: list[str] = field(default_factory=list)
    max_command_length: int = 10000

    def compile_patterns(self) -> None:
        """预编译正则（供内部调用）"""
        self._allowed_re = [re.compile(p) for p in self.allowed_patterns]
        self._denied_re = [re.compile(p) for p in self.denied_patterns]
        self._approval_re = [re.compile(p) for p in self.require_approval]

    @classmethod
    def from_dict(cls, data: dict[str, list[str]]) -> PermissionRule:
        """从 dict 创建规则"""
        return cls(
            allowed_patterns=data.get("allowed_patterns", []),
            denied_patterns=data.get("denied_patterns", []),
            require_approval=data.get("require_approval", []),
            max_command_length=data.get("max_command_length", 10000),
        )

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "allowed_patterns": self.allowed_patterns,
            "denied_patterns": self.denied_patterns,
            "require_approval": self.require_approval,
            "max_command_length": self.max_command_length,
        }


@dataclass
class CheckResult:
    """检查结果"""

    allowed: bool
    reason: Optional[str] = None
    matched_pattern: Optional[str] = None
    requires_approval: bool = False

    def to_tuple(self) -> tuple[bool, Optional[str]]:
        """兼容旧接口"""
        return (self.allowed, self.reason)


# ─────────────────────────────────────────────────────────────
# 权限守卫
# ─────────────────────────────────────────────────────────────


class PermissionGuard:
    """权限守卫"""

    # 内置高风险命令模式（即使未配置也拦截）
    BUILTIN_DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/\s*",
        r"rm\s+-rf\s+/[a-zA-Z]+\s*",
        r":\(\)\{.*:\|.*:.*\}",
        r">\s*/dev/sd[a-z]",
        r"dd\s+if=.*of=/dev/",
        r"mkfs\s+",
        r":(){ :|:& };:",
    ]

    def __init__(self, rules: PermissionRule | None = None) -> None:
        self.rules = rules or PermissionRule()
        self._compiled = False
        self._compile()

    def _compile(self) -> None:
        """编译正则表达式（跳过无效正则）"""
        if self._compiled:
            return

        def safe_compile(patterns: list[str]) -> list[re.Pattern[str]]:
            compiled: list[re.Pattern[str]] = []
            for p in patterns:
                try:
                    compiled.append(re.compile(p, re.IGNORECASE))
                except re.error:
                    pass
            return compiled

        self._allowed_re = safe_compile(self.rules.allowed_patterns)
        self._denied_re = safe_compile(self.rules.denied_patterns)
        self._approval_re = safe_compile(self.rules.require_approval)
        self._builtin_re = [
            re.compile(p, re.IGNORECASE) for p in self.BUILTIN_DANGEROUS_PATTERNS
        ]
        self._compiled = True

    def check(self, command: str) -> CheckResult:
        """
        检查命令是否允许执行

        Returns:
            CheckResult(allowed, reason, matched_pattern, requires_approval)
        """
        if not command or not command.strip():
            return CheckResult(allowed=False, reason="命令为空")

        if len(command) > self.rules.max_command_length:
            return CheckResult(
                allowed=False,
                reason=f"命令长度 {len(command)} 超过限制 {self.rules.max_command_length}",
            )

        # 1. 内置黑名单（最高优先级）
        for compiled in self._builtin_re:
            if compiled.search(command):
                return CheckResult(
                    allowed=False,
                    reason="命令匹配内置危险模式",
                    matched_pattern=compiled.pattern,
                )

        # 2. 配置文件黑名单
        for pattern, compiled in zip(self.rules.denied_patterns, self._denied_re):
            if compiled.search(command):
                return CheckResult(
                    allowed=False,
                    reason=f"命令匹配黑名单: {pattern}",
                    matched_pattern=pattern,
                )

        # 3. 白名单模式
        if self._allowed_re:
            for pattern, compiled in zip(self.rules.allowed_patterns, self._allowed_re):
                if compiled.search(command):
                    return CheckResult(allowed=True, reason=f"匹配白名单: {pattern}")
            return CheckResult(
                allowed=False,
                reason="命令不在白名单内",
            )

        return CheckResult(allowed=True, reason=None)

    def needs_approval(self, command: str) -> bool:
        """检查是否需要审批"""
        for compiled in self._approval_re:
            if compiled.search(command):
                return True
        return False

    def validate_rules(self) -> list[str]:
        """验证规则合法性"""
        errors: list[str] = []

        for pattern in self.rules.allowed_patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"allowed_patterns 正则错误 '{pattern}': {e}")

        for pattern in self.rules.denied_patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"denied_patterns 正则错误 '{pattern}': {e}")

        for pattern in self.rules.require_approval:
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"require_approval 正则错误 '{pattern}': {e}")

        return errors

    @classmethod
    def from_agent_config(cls, config: dict[str, Any]) -> PermissionGuard:
        """从 Agent 配置字典创建 PermissionGuard"""
        perm_data = config.get("permissions", {})
        rules = PermissionRule(
            allowed_patterns=perm_data.get("allowed_patterns", []),
            denied_patterns=perm_data.get("denied_patterns", []),
            require_approval=perm_data.get("require_approval", []),
        )
        return cls(rules)


# ─────────────────────────────────────────────────────────────
# 便捷函数
# ─────────────────────────────────────────────────────────────


def check_command(command: str, rules: PermissionRule | None = None) -> CheckResult:
    """检查命令权限（便捷函数）"""
    guard = PermissionGuard(rules)
    return guard.check(command)


def needs_approval(command: str, rules: PermissionRule | None = None) -> bool:
    """检查命令是否需要审批（便捷函数）"""
    guard = PermissionGuard(rules)
    return guard.needs_approval(command)
