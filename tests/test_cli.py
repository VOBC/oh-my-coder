"""
测试 CLI 命令

使用 Typer 的 CliRunner 进行集成测试。
"""

import os
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from src.cli import app, __version__

runner = CliRunner()


class TestMainCallback:
    """测试主回调函数"""

    def test_version_flag(self):
        """测试 --version 选项"""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_help_flag(self):
        """测试 --help 选项"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Oh My Coder" in result.stdout

    def test_no_args_shows_info(self):
        """测试无参数时的行为（输出包含 Oh My Coder）"""
        result = runner.invoke(app, [])
        # Typer no_args_is_help=True 时应该显示帮助信息
        # exit_code 可能在 0（新版）或 2（旧版）之间不一致
        assert "Oh My Coder" in result.stdout or "omc" in result.stdout


class TestAgentsCommand:
    """测试 agents 命令"""

    def test_agents_list(self):
        """测试列出所有 Agent"""
        result = runner.invoke(app, ["agents"])
        assert result.exit_code == 0
        assert "explore" in result.stdout
        assert "analyst" in result.stdout
        assert "planner" in result.stdout

    def test_agents_count(self):
        """测试 Agent 数量显示"""
        result = runner.invoke(app, ["agents"])
        assert result.exit_code == 0
        assert "18" in result.stdout or "智能体" in result.stdout


class TestStatusCommand:
    """测试 status 命令"""

    def test_status_without_api_key(self):
        """测试无 API Key 时的状态"""
        # 临时清空环境变量
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "未配置" in result.stdout or "路由器" in result.stdout

    def test_status_with_api_key(self):
        """测试有 API Key 时的状态"""
        with patch.dict(
            os.environ, {"DEEPSEEK_API_KEY": "test_key_for_cli"}, clear=False
        ):
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            # 应该显示已配置或路由器状态
            assert "已配置" in result.stdout or "路由器" in result.stdout


class TestExploreCommand:
    """测试 explore 命令"""

    def test_explore_without_api_key(self):
        """测试无 API Key 时探索"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
            result = runner.invoke(app, ["explore", "."])
            # 应该失败或显示错误提示
            assert result.exit_code != 0 or "API Key" in result.stdout


class TestRunCommand:
    """测试 run 命令"""

    def test_run_without_api_key(self):
        """测试无 API Key 时运行任务"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
            result = runner.invoke(app, ["run", "test task"])
            # 应该失败或显示错误提示
            assert result.exit_code != 0 or "API Key" in result.stdout

    def test_run_missing_task(self):
        """测试缺少任务参数"""
        result = runner.invoke(app, ["run"])
        # 应该显示错误或帮助
        assert result.exit_code != 0


class TestHelperFunctions:
    """测试辅助函数"""

    def test_print_version(self):
        """测试版本打印"""
        # 捕获输出
        result = runner.invoke(app, ["--version"])
        assert __version__ in result.stdout

    def test_status_color(self):
        """测试状态颜色映射"""
        from src.cli import _status_color

        assert "已完成" in _status_color("completed")
        assert "失败" in _status_color("failed")
        assert "运行中" in _status_color("running")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
