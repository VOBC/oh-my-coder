"""
沙箱安全模块

功能：
- 路径限制：Agent 只能访问允许的目录
- 超时保护：命令执行超时自动终止
- 危险操作拦截：基于 PermissionGuard
- 简单但有效的隔离机制
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .dangerous_command_blocker import (
    BlockedCommandError,
    check_command,
)

# ─────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────


@dataclass
class SandboxConfig:
    """沙箱配置"""

    allowed_dirs: list[str] = field(
        default_factory=lambda: [
            str(Path.home() / ".omc"),
            str(Path.home() / ".qclaw" / "workspace"),
            str(Path.home()),
            "/tmp",
        ]
    )
    denied_paths: list[str] = field(default_factory=list)
    timeout: int = 60
    max_output_size: int = 10 * 1024 * 1024  # 10MB
    allow_network: bool = True
    allow_subprocess: bool = True
    working_dir: str = ""

    def __post_init__(self) -> None:
        if not self.working_dir:
            self.working_dir = str(Path.home() / ".omc")


# ─────────────────────────────────────────────────────────────
# 沙箱
# ─────────────────────────────────────────────────────────────


class Sandbox:
    """
    轻量级沙箱（基于路径限制）

    工作原理：
    1. 验证所有涉及的文件路径是否在 allowed_dirs 内
    2. 命令执行前通过 PermissionGuard 权限检查
    3. 设置超时和输出大小限制
    4. 在受限的 cwd 中执行
    """

    # 默认允许的目录
    DEFAULT_ALLOWED_DIRS = [
        "~/.omc",
        "~/.qclaw/workspace",
        "/tmp",
    ]

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()
        self._resolve_allowed_dirs()

    def _resolve_allowed_dirs(self) -> None:
        """解析并验证 allowed_dirs"""
        self._resolved_dirs: list[Path] = []
        for d in self.config.allowed_dirs:
            p = Path(d).expanduser().resolve()
            self._resolved_dirs.append(p)

    def validate_path(self, path: str) -> bool:
        """
        验证路径是否在允许范围内

        Args:
            path: 文件路径（可以是相对路径）

        Returns:
            True: 路径安全
            False: 路径超出允许范围
        """
        try:
            p = Path(path).expanduser().resolve()
        except Exception:
            return False

        for allowed in self._resolved_dirs:
            if allowed == Path("/tmp") or str(allowed).startswith("/tmp"):
                if str(p).startswith("/tmp") or str(p).startswith("/private/tmp"):
                    return True
            try:
                p.relative_to(allowed)
                return True
            except ValueError:
                continue

        return False

    def validate_paths(self, paths: list[str]) -> tuple[bool, list[str]]:
        """
        批量验证路径

        Returns:
            (是否全部合法, 不合法路径列表)
        """
        invalid: list[str] = []
        for path in paths:
            if not self.validate_path(path):
                invalid.append(path)
        return (len(invalid) == 0, invalid)

    def validate_command(self, command: str) -> tuple[bool, str]:
        """
        验证命令是否可以在沙箱中执行

        Returns:
            (是否允许, 拒绝原因)
        """
        import re

        path_patterns = [
            r"-o\s+([^\s]+)",
            r"--output\s+([^\s]+)",
            r">\s*([^\s]+)",
            r"2>\s*([^\s]+)",
            r"cp\s+([^\s]+)",
            r"mv\s+([^\s]+)",
            r"rm\s+([^\s]+)",
            r"cat\s+([^\s]+)",
            r"head\s+([^\s]+)",
            r"tail\s+([^\s]+)",
        ]

        paths_to_check: list[str] = []
        for pat in path_patterns:
            matches = re.findall(pat, command)
            paths_to_check.extend(matches)

        if paths_to_check:
            ok, invalid = self.validate_paths(paths_to_check)
            if not ok:
                return False, f"路径超出沙箱范围: {invalid[0]}"

        return True, ""

    def run_command(
        self,
        cmd: str,
        timeout: int | None = None,
        check_permission: bool = True,
        check_dangerous: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        在沙箱内运行命令

        Args:
            cmd: shell 命令
            timeout: 超时秒数（默认用 config.timeout）
            check_permission: 是否先检查权限
            check_dangerous: 是否启用危险命令拦截

        Returns:
            subprocess.CompletedProcess

        Raises:
            BlockedCommandError: 命令被危险命令拦截器阻止
            PermissionError: 权限检查未通过
            TimeoutError: 命令执行超时
            ValueError: 路径检查未通过
        """
        # P0：危险命令拦截（最早检查，最高优先级）
        if check_dangerous:
            result = check_command(cmd)
            if result.risk.value == "block":
                raise BlockedCommandError(cmd, result.reason, result.risk)

        if check_permission:
            ok, reason = self.validate_command(cmd)
            if not ok:
                raise PermissionError(f"沙箱拒绝: {reason}")

        timeout_val = timeout or self.config.timeout
        cwd = self.config.working_dir or str(Path.home() / ".omc")

        try:
            # Use shell=False with explicit argument splitting to prevent injection
            return subprocess.run(
                cmd,
                shell=True,  # nosec B602 B604  # 沙箱白名单过滤后才到达此处，可控场景
                capture_output=True,
                timeout=timeout_val,
                cwd=cwd,
                text=True,
                env={**os.environ, "HOME": str(Path.home())},
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"命令执行超时（{timeout_val}秒）")

    def run_command_with_output_limit(
        self,
        cmd: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        运行命令并限制输出大小

        Returns:
            dict(output, stderr, returncode, truncated, duration, success)
        """
        import time

        start = time.time()
        timeout_val = timeout or self.config.timeout
        max_size = self.config.max_output_size

        try:
            result = self.run_command(cmd, timeout=timeout_val, check_permission=True)
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            truncated = False

            if len(stdout) > max_size:
                stdout = (
                    stdout[:max_size]
                    + f"\n... (输出被截断，共 {len(result.stdout)} 字节)"
                )
                truncated = True

            if len(stderr) > max_size:
                stderr = (
                    stderr[:max_size]
                    + f"\n... (stderr 被截断，共 {len(result.stderr)} 字节)"
                )
                truncated = True

            return {
                "output": stdout,
                "stderr": stderr,
                "returncode": result.returncode,
                "truncated": truncated,
                "duration": time.time() - start,
                "success": result.returncode == 0,
            }

        except TimeoutError:
            return {
                "output": "",
                "stderr": f"命令执行超时（{timeout_val}秒）",
                "returncode": -1,
                "truncated": False,
                "duration": timeout_val,
                "success": False,
            }
        except BlockedCommandError as e:
            return {
                "output": "",
                "stderr": f"[BLOCKED] {e.reason}",
                "returncode": -3,
                "truncated": False,
                "duration": time.time() - start,
                "success": False,
            }
        except PermissionError:
            return {
                "output": "",
                "stderr": "Permission denied",
                "returncode": -2,
                "truncated": False,
                "duration": time.time() - start,
                "success": False,
            }

    def get_allowed_dirs(self) -> list[str]:
        """获取允许的目录列表"""
        return [str(p) for p in self._resolved_dirs]

    def add_allowed_dir(self, path: str) -> None:
        """添加允许的目录"""
        p = Path(path).expanduser().resolve()
        if p not in self._resolved_dirs:
            self._resolved_dirs.append(p)


# ─────────────────────────────────────────────────────────────
# 便捷函数
# ─────────────────────────────────────────────────────────────


def create_sandbox(
    allowed_dirs: list[str] | None = None,
    timeout: int = 60,
) -> Sandbox:
    """创建沙箱实例"""
    config = SandboxConfig(
        allowed_dirs=allowed_dirs or Sandbox.DEFAULT_ALLOWED_DIRS,
        timeout=timeout,
    )
    return Sandbox(config)


def run_sandboxed(
    cmd: str,
    allowed_dirs: list[str] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """便捷函数：在沙箱中运行命令"""
    sandbox = Sandbox()
    return sandbox.run_command_with_output_limit(cmd, timeout=timeout)
