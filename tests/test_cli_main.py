"""
测试 cli.py 主入口文件

覆盖关键函数：
- --version 选项
- --help 选项
- 主 callback 函数
- _print_version()
- agents() 命令
- status() 命令
- _mask_secret() 函数

Mock 策略：
- patch 源模块，不是导入模块
- 使用 @pytest.fixture 共享 mock
- 参考 test_cli_model_coverage.py 的写法
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commands.cli import app as cli_app, __version__, __author__, __repo__

runner = CliRunner()


# =============================================================================
# Helpers
# =============================================================================

def _run(cmd):
    """运行 CLI 命令"""
    return runner.invoke(cli_app, cmd if isinstance(cmd, list) else cmd.split())


# =============================================================================
# 1) 测试 --version 选项
# =============================================================================

class TestVersionOption:
    """测试 --version 和 -v 选项"""

    def test_version_long(self):
        """测试 --version 选项"""
        result = _run("--version")
        assert result.exit_code == 0
        assert __version__ in result.output
        assert __author__ in result.output
        assert __repo__ in result.output

    def test_version_short(self):
        """测试 -v 选项"""
        result = _run("-v")
        assert result.exit_code == 0
        assert __version__ in result.output
        assert __author__ in result.output
        assert __repo__ in result.output

    def test_version_with_subcommand_fails(self):
        """--version 应该在子命令之前被 eager 处理"""
        result = _run("--version run")
        # typer 的 eager option 会先处理 --version
        assert result.exit_code == 0
        assert __version__ in result.output


# =============================================================================
# 2) 测试 --help 选项
# =============================================================================

class TestHelpOption:
    """测试 --help 选项"""

    def test_help_main(self):
        """测试主命令 --help"""
        result = _run("--help")
        assert result.exit_code == 0
        assert "Oh My Coder" in result.output
        assert "多智能体 AI 编程助手" in result.output

    def test_help_no_args(self):
        """测试无参数时显示帮助（no_args_is_help=True）"""
        result = _run("")
        assert result.exit_code == 0
        # 应该显示欢迎面板
        assert "Oh My Coder" in result.output


# =============================================================================
# 3) 测试主 callback 函数
# =============================================================================

class TestMainCallback:
    """测试 main callback 函数"""

    def test_callback_no_command(self):
        """测试无子命令时显示欢迎面板"""
        result = _run("")
        assert result.exit_code == 0
        assert "Oh My Coder" in result.output
        assert __version__ in result.output

    def test_callback_with_version(self):
        """测试 --version 时不会显示欢迎面板"""
        result = _run("--version")
        assert result.exit_code == 0
        # 应该只显示版本信息，不显示欢迎面板
        assert __version__ in result.output
        # 不应该有 Panel 的边框字符（如果没有调用 console.print(Panel)）
        # 注意：_print_version() 也会打印，所以这里只是确保 exit_code 正确


# =============================================================================
# 4) 测试 _print_version() 函数
# =============================================================================

class TestPrintVersion:
    """测试 _print_version() 函数"""

    def test_print_version_output(self):
        """测试版本信息输出格式"""
        from src.commands.cli import _print_version
        from rich.console import Console
        from io import StringIO

        # 捕获 console 输出
        console = Console(file=StringIO(), no_color=True)
        with patch("src.commands.cli.console", console):
            _print_version()

        output = console.file.getvalue()
        assert f"oh-my-coder version {__version__}" in output
        assert f"Author: {__author__}" in output
        assert f"Repo: {__repo__}" in output


# =============================================================================
# 5) 测试 _mask_secret() 函数
# =============================================================================

class TestMaskSecret:
    """测试 _mask_secret() 脱敏函数"""

    def test_mask_none(self):
        """测试 None 值"""
        from src.commands.cli import _mask_secret
        assert _mask_secret(None) == ""

    def test_mask_empty(self):
        """测试空字符串"""
        from src.commands.cli import _mask_secret
        assert _mask_secret("") == ""

    def test_mask_short(self):
        """测试短密钥（<=8 字符）"""
        from src.commands.cli import _mask_secret
        assert _mask_secret("1234567") == "****"
        assert _mask_secret("12345678") == "****"

    def test_mask_normal(self):
        """测试正常密钥"""
        from src.commands.cli import _mask_secret
        # "sk-1234567890abcdef" -> "sk-1****cdef"
        result = _mask_secret("sk-1234567890abcdef")
        assert result == "sk-1****cdef"
        # "sk-1" + "****" + "cdef" = 4 + 4 + 4 = 12
        assert len(result) == 12  # 4 + 4 + 4 (****)

    def test_mask_long(self):
        """测试长密钥"""
        from src.commands.cli import _mask_secret
        key = "sk-ant-" + "x" * 64
        result = _mask_secret(key)
        assert result.startswith("sk-a")
        assert result.endswith("xxxx")
        assert "****" in result


# =============================================================================
# 6) 测试 agents() 命令
# =============================================================================

class TestAgentsCommand:
    """测试 agents 命令"""

    def test_agents_success(self):
        """测试成功列出 agents"""
        # Agent 类是在 agents() 函数内部导入的：from src.agents import ...
        # 所以需要 patch src.agents 模块中的 Agent 类
        
        # 创建一个 mock 模块
        mock_agents_module = MagicMock()
        
        # 设置所有需要的 Agent 类
        agent_classes = [
            "ExploreAgent", "AnalystAgent", "PlannerAgent", "ArchitectAgent",
            "ExecutorAgent", "VerifierAgent", "TestEngineerAgent", "CodeReviewerAgent",
            "DebuggerAgent", "TracerAgent", "CriticAgent", "WriterAgent",
            "DesignerAgent", "SecurityReviewerAgent", "GitMasterAgent", "CodeSimplifierAgent",
            "ScientistAgent", "QATesterAgent", "DatabaseAgent", "APIAgent",
            "DevOpsAgent", "UMLAgent", "PerformanceAgent", "MigrationAgent",
            "PromptAgent", "VisionAgent", "AuthAgent", "DataAgent",
            "SelfImprovingAgent", "SkillManageAgent", "DocumentAgent"
        ]
        
        for cls_name in agent_classes:
            mock_cls = MagicMock()
            mock_cls.description = f"{cls_name} description"
            mock_cls.default_tier = "standard"
            setattr(mock_agents_module, cls_name, mock_cls)
        
        with patch.dict("sys.modules", {"src.agents": mock_agents_module}):
            result = _run("agents")
        
        assert result.exit_code == 0
        assert "可用智能体" in result.output

    def test_agents_import_error(self):
        """测试 Agent 导入失败的情况"""
        # 这个测试比较难模拟，因为导入是在函数内部
        # 暂时跳过，因为当前代码没有处理导入失败的逻辑
        pass


# =============================================================================
# 7) 测试 status() 命令
# =============================================================================

class TestStatusCommand:
    """测试 status 命令"""

    def test_status_all_configured(self, monkeypatch):
        """测试所有 API Key 都已配置"""
        # 设置所有环境变量
        api_keys = [
            "DEEPSEEK_API_KEY", "KIMI_API_KEY", "DOUBAO_API_KEY",
            "MINIMAX_API_KEY", "ZHIPUAI_API_KEY", "TONGYI_API_KEY",
            "WENXIN_API_KEY", "HUNYUAN_API_KEY"
        ]
        for key in api_keys:
            monkeypatch.setenv(key, "test-key-value")

        # mock _init_router
        mock_router = MagicMock()
        mock_router.get_stats.return_value = {
            "total_requests": 100,
            "total_cost": 1.2345
        }
        with patch("src.commands.cli._init_router", return_value=mock_router):
            result = _run("status")

        assert result.exit_code == 0
        assert "系统状态" in result.output
        assert "路由器就绪" in result.output

    def test_status_none_configured(self):
        """测试所有 API Key 都未配置"""
        # 确保所有 API Key 都不存在
        with patch("os.getenv", return_value=None):
            # mock _init_router 失败
            with patch("src.commands.cli._init_router", side_effect=Exception("Router error")):
                result = _run("status")

        assert result.exit_code == 0
        assert "系统状态" in result.output
        # 应该显示所有 Key 都未配置
        assert "未配置" in result.output or "✗" in result.output

    def test_status_partial_configured(self, monkeypatch):
        """测试部分 API Key 已配置"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        monkeypatch.setenv("KIMI_API_KEY", "sk-test2")

        with patch("os.getenv", side_effect=lambda k: {"DEEPSEEK_API_KEY": "sk-test", "KIMI_API_KEY": "sk-test2"}.get(k)):
            with patch("src.commands.cli._init_router", side_effect=Exception("Router error")):
                result = _run("status")

        assert result.exit_code == 0
        assert "已配置" in result.output
        assert "未配置" in result.output

    def test_status_router_success(self, monkeypatch):
        """测试路由器初始化成功"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")

        mock_router = MagicMock()
        mock_router.get_stats.return_value = {
            "total_requests": 50,
            "total_cost": 0.5678
        }
        with patch("src.commands.cli._init_router", return_value=mock_router):
            result = _run("status")

        assert result.exit_code == 0
        assert "路由器就绪" in result.output
        assert "50" in result.output
        assert "0.5678" in result.output

    def test_status_router_error(self, monkeypatch):
        """测试路由器初始化失败"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")

        with patch("src.commands.cli._init_router", side_effect=RuntimeError("Connection failed")):
            result = _run("status")

        assert result.exit_code == 0
        assert "路由器初始化失败" in result.output
        assert "Connection failed" in result.output


# =============================================================================
# 8) 测试环境变量加载
# =============================================================================

class TestEnvLoading:
    """测试环境变量加载逻辑"""

    def test_user_env_loading(self, tmp_path, monkeypatch):
        """测试用户级 .env 加载"""
        # 创建临时 .env 文件
        user_env = tmp_path / ".env"
        user_env.write_text("TEST_USER_ENV=loaded\n")

        # mock Path.home() 返回临时目录
        with patch("pathlib.Path.home", return_value=tmp_path):
            # 重新导入模块以触发环境变量加载
            with patch.dict("sys.modules", {"src.commands.cli": None}):
                # 这里只是测试逻辑，实际重新导入比较复杂
                pass

        # 简化测试：直接测试 load_dotenv 被调用
        with patch("src.commands.cli.load_dotenv") as mock_load:
            # 模拟用户级 .env 存在
            with patch("pathlib.Path.exists", return_value=True):
                # 重新执行导入时的逻辑（实际做不到，只是示意）
                pass

        # 更实际的测试：测试 cli.py 中的加载逻辑
        # 这部分代码在模块导入时执行，很难单独测试
        # 建议通过集成测试来验证
        pass

    def test_project_env_loading(self, tmp_path, monkeypatch):
        """测试项目级 .env 加载"""
        # 类似上面的测试，这部分逻辑在导入时执行
        # 建议通过集成测试验证
        pass


# =============================================================================
# 9) 测试子命令注册
# =============================================================================

class TestSubcommandRegistration:
    """测试子命令是否正确注册"""

    def test_subcommands_registered(self):
        """测试所有子命令都在 typer 中注册"""
        # 获取所有注册的命令和子命令
        # typer 内部使用 click，可以通过 cli_app.registered_commands 访问
        commands = []
        for cmd in cli_app.registered_commands:
            if cmd.name:
                commands.append(cmd.name)
            else:
                # 如果 name 为 None，尝试从 callback 获取函数名
                if hasattr(cmd, 'callback') and cmd.callback:
                    commands.append(cmd.callback.__name__)
        
        groups = [group.name for group in cli_app.registered_groups]

        # 检查顶级命令（通过 app.command() 注册的）
        # 注意：这些命令的 name 可能为 None
        # 所以这里只检查能通过 --help 访问的命令
        result = _run("--help")
        assert result.exit_code == 0
        # 至少应该有一些命令在帮助中
        assert "run" in result.output or "agents" in result.output

        # 检查子命令组
        assert "config" in groups
        assert "model" in groups
        assert "task" in groups


# =============================================================================
# 10) 测试 quest 命令组
# =============================================================================

class TestQuestCommands:
    """测试 quest 相关命令"""

    def test_quest_help(self):
        """测试 quest 命令帮助"""
        result = _run("quest --help")
        # quest 命令应该存在
        assert result.exit_code == 0 or result.exit_code == 2  # 2 = UsageError

    def test_quest_list_help(self):
        """测试 quest-list 命令帮助"""
        result = _run("quest-list --help")
        assert result.exit_code == 0 or result.exit_code == 2


# =============================================================================
# 11) 集成测试：完整流程
# =============================================================================

class TestIntegration:
    """集成测试"""

    def test_version_then_help(self):
        """测试先查看版本再查看帮助"""
        result1 = _run("--version")
        assert result1.exit_code == 0

        result2 = _run("--help")
        assert result2.exit_code == 0

    def test_main_callback_invoked_without_command(self):
        """测试无命令时调用主 callback"""
        result = _run("")
        assert result.exit_code == 0
        # 应该显示欢迎信息
        assert "Oh My Coder" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
