"""
测试沙箱安全模块
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from src.sandbox.sandbox import (
    Sandbox,
    SandboxConfig,
    create_sandbox,
    run_sandboxed,
)


class TestSandbox:
    """Sandbox 测试"""

    def test_init_default(self) -> None:
        sandbox = Sandbox()
        assert sandbox.config.timeout == 60
        assert len(sandbox.get_allowed_dirs()) > 0

    def test_init_custom_config(self) -> None:
        config = SandboxConfig(
            allowed_dirs=["/tmp"],
            timeout=30,
        )
        sandbox = Sandbox(config)
        assert sandbox.config.timeout == 30

    def test_validate_path_allowed(self) -> None:
        sandbox = Sandbox()
        # /tmp 总是允许
        assert sandbox.validate_path("/tmp/test.txt") is True
        assert sandbox.validate_path("/tmp") is True

    def test_validate_path_home(self) -> None:
        sandbox = Sandbox()
        home = str(Path.home())
        assert sandbox.validate_path(home) is True

    def test_validate_path_forbidden(self) -> None:
        sandbox = Sandbox()
        # /etc/passwd 不在允许目录
        assert sandbox.validate_path("/etc/passwd") is False

    def test_validate_paths_batch(self) -> None:
        sandbox = Sandbox()
        ok, invalid = sandbox.validate_paths(["/tmp/a", "/etc/shadow"])
        assert ok is False
        assert "/etc/shadow" in invalid

        ok2, invalid2 = sandbox.validate_paths(["/tmp/b", "/tmp/c"])
        assert ok2 is True
        assert invalid2 == []

    def test_add_allowed_dir(self) -> None:
        sandbox = Sandbox()
        initial = len(sandbox.get_allowed_dirs())
        sandbox.add_allowed_dir("/usr/local/bin")
        assert len(sandbox.get_allowed_dirs()) == initial + 1

    def test_run_command_echo(self) -> None:
        sandbox = Sandbox()
        result = sandbox.run_command("echo 'hello sandbox'", timeout=5)
        assert result.returncode == 0
        assert "hello sandbox" in result.stdout

    def test_run_command_forbidden_path(self) -> None:
        sandbox = Sandbox()
        with pytest.raises(PermissionError, match="沙箱拒绝"):
            sandbox.run_command("cat /etc/shadow")

    def test_run_command_timeout(self) -> None:
        sandbox = Sandbox(config=SandboxConfig(timeout=1))
        # TimeoutError should be raised when command times out
        import pytest

        with pytest.raises(TimeoutError, match="超时"):
            sandbox.run_command("sleep 10", timeout=1)

    def test_run_command_with_output_limit(self) -> None:
        sandbox = Sandbox()
        result = sandbox.run_command_with_output_limit(
            "python3 -c 'print(\"x\" * 100)'", timeout=5
        )
        assert result["success"] is True
        assert "x" * 100 in result["output"]

    def test_run_command_cwd(self) -> None:
        sandbox = Sandbox(config=SandboxConfig(working_dir="/tmp"))
        result = sandbox.run_command("pwd", timeout=5)
        # cwd 应该在 working_dir 范围内
        assert result.returncode == 0

    def test_get_allowed_dirs(self) -> None:
        sandbox = Sandbox()
        dirs = sandbox.get_allowed_dirs()
        assert len(dirs) > 0
        assert any("/tmp" in d for d in dirs)


class TestSandboxConfig:
    """SandboxConfig 测试"""

    def test_default_values(self) -> None:
        config = SandboxConfig()
        assert config.timeout == 60
        assert config.max_output_size == 10 * 1024 * 1024
        assert config.allow_network is True
        assert config.allow_subprocess is True

    def test_default_dirs_include_home(self) -> None:
        config = SandboxConfig()
        home_str = str(Path.home())
        assert any(home_str in d for d in config.allowed_dirs)


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_sandbox(self) -> None:
        sandbox = create_sandbox(allowed_dirs=["/tmp"], timeout=10)
        assert sandbox.config.timeout == 10
        assert sandbox.validate_path("/tmp") is True

    def test_run_sandboxed_echo(self) -> None:
        result = run_sandboxed("echo 'test'", timeout=5)
        assert result["success"] is True
        assert "test" in result["output"]

    def test_run_sandboxed_forbidden(self) -> None:
        result = run_sandboxed("cat /etc/passwd", timeout=5)
        assert result["success"] is False
        assert "returncode" in result
