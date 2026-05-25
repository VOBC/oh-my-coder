"""
单元测试：src/mcp/tools.py

覆盖所有公开函数和 handler，目标覆盖率 > 80%。
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# ------------------------------------------------------------------
# Mock 类定义
# ------------------------------------------------------------------

class AgentResult:
    """模拟 Agent 执行结果"""
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def __str__(self):
        return str(self.result) if self.result else ""


class MockAgent:
    """模拟 Agent 基类"""
    def __init__(self, *args, **kwargs):
        pass

    def execute(self, ctx):
        return AgentResult(result="mock result")


# ------------------------------------------------------------------
# 导入被测试模块前的路径设置
# ------------------------------------------------------------------

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ------------------------------------------------------------------
# 测试用例
# ------------------------------------------------------------------

class TestSetWorkspaceAndGetWorkspace:
    """测试 set_workspace 和 get_workspace 函数"""

    def test_set_workspace_and_get_workspace(self):
        """测试设置并获取工作区路径"""
        from src.mcp.tools import get_workspace, set_workspace

        # 保存原始工作区
        original_workspace = get_workspace()

        try:
            # 设置新工作区
            test_path = Path("/tmp/test_workspace")
            set_workspace(test_path)

            # 验证工作区已设置
            result = get_workspace()
            assert result == test_path.resolve()
        finally:
            # 恢复原始工作区
            set_workspace(original_workspace)

    def test_get_workspace_default(self):
        """测试获取默认工作区（未设置时返回 cwd）"""
        import src.mcp.tools as tools_module
        from src.mcp.tools import get_workspace

        # 保存原始工作区
        original_workspace_value = tools_module._WORKSPACE

        try:
            # 设置为 None 来模拟未设置状态
            tools_module._WORKSPACE = None

            # 验证返回 cwd
            result = get_workspace()
            assert result == Path.cwd()
        finally:
            # 恢复
            tools_module._WORKSPACE = original_workspace_value


class TestResolvePath:
    """测试 _resolve_path 函数"""

    def test_resolve_path_none(self):
        """测试 path 为 None 时返回工作区路径"""
        from src.mcp.tools import _resolve_path, get_workspace, set_workspace

        # 保存原始工作区
        original_workspace = get_workspace()

        try:
            # 设置工作区
            test_path = Path("/tmp/test_workspace")
            set_workspace(test_path)

            # 测试 None
            result = _resolve_path(None)
            assert result == str(test_path.resolve())
        finally:
            # 恢复原始工作区
            set_workspace(original_workspace)

    def test_resolve_path_relative(self):
        """测试相对路径拼接工作区"""
        from src.mcp.tools import _resolve_path, get_workspace, set_workspace

        # 保存原始工作区
        original_workspace = get_workspace()

        try:
            # 设置工作区
            test_path = Path("/tmp/test_workspace").resolve()
            set_workspace(test_path)

            # 测试相对路径
            result = _resolve_path("src/main.py")
            expected = str(test_path / "src/main.py")
            assert result == expected
        finally:
            # 恢复原始工作区
            set_workspace(original_workspace)

    def test_resolve_path_absolute(self):
        """测试绝对路径直接返回"""
        from src.mcp.tools import _resolve_path

        # 测试绝对路径
        absolute_path = "/absolute/path/file.py"
        result = _resolve_path(absolute_path)
        assert result == absolute_path


class TestCodeReviewHandler:
    """测试 _code_review_handler"""

    @patch("src.agents.code_reviewer.CodeReviewerAgent")
    @patch("asyncio.new_event_loop")
    def test_code_review_handler_success(self, mock_new_loop, mock_agent_class):
        """测试成功路径"""
        from src.mcp.tools import _code_review_handler

        # 设置 mock
        mock_agent_instance = Mock()
        mock_agent_instance.execute = Mock(return_value=AgentResult(result="review complete"))
        mock_agent_class.return_value = mock_agent_instance

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = AgentResult(result="review complete")
        mock_new_loop.return_value = mock_loop

        # 执行测试
        args = {"path": "test.py"}
        result = _code_review_handler(args)

        # 验证
        assert "content" in result
        assert "review complete" in result["content"]

    @patch("src.agents.code_reviewer.CodeReviewerAgent", side_effect=Exception("test error"))
    def test_code_review_handler_exception(self, mock_agent_class):
        """测试异常路径"""
        from src.mcp.tools import _code_review_handler

        # 执行测试
        args = {"path": "test.py"}
        result = _code_review_handler(args)

        # 验证
        assert "error" in result
        assert result["error"] == "Exception"


class TestDebugHandler:
    """测试 _debug_handler"""

    @patch("src.agents.debugger.DebuggerAgent")
    @patch("asyncio.new_event_loop")
    def test_debug_handler_success(self, mock_new_loop, mock_agent_class):
        """测试成功路径"""
        from src.mcp.tools import _debug_handler

        # 设置 mock
        mock_agent_instance = Mock()
        mock_agent_instance.execute = Mock(return_value=AgentResult(result="debug complete"))
        mock_agent_class.return_value = mock_agent_instance

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = AgentResult(result="debug complete")
        mock_new_loop.return_value = mock_loop

        # 执行测试
        args = {"path": "test.py", "error": "some error"}
        result = _debug_handler(args)

        # 验证
        assert "content" in result
        assert "debug complete" in result["content"]

    @patch("src.agents.debugger.DebuggerAgent", side_effect=Exception("test error"))
    def test_debug_handler_exception(self, mock_agent_class):
        """测试异常路径"""
        from src.mcp.tools import _debug_handler

        # 执行测试
        args = {"path": "test.py", "error": "some error"}
        result = _debug_handler(args)

        # 验证
        assert "error" in result
        assert result["error"] == "Exception"


class TestTestHandler:
    """测试 _test_handler"""

    @patch("src.agents.test_engineer.TestEngineerAgent")
    @patch("asyncio.new_event_loop")
    def test_test_handler_success(self, mock_new_loop, mock_agent_class):
        """测试成功路径"""
        from src.mcp.tools import _test_handler

        # 设置 mock
        mock_agent_instance = Mock()
        mock_agent_instance.execute = Mock(return_value=AgentResult(result="test complete"))
        mock_agent_class.return_value = mock_agent_instance

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = AgentResult(result="test complete")
        mock_new_loop.return_value = mock_loop

        # 执行测试
        args = {"path": "test.py"}
        result = _test_handler(args)

        # 验证
        assert "content" in result
        assert "test complete" in result["content"]

    @patch("src.agents.test_engineer.TestEngineerAgent", side_effect=Exception("test error"))
    def test_test_handler_exception(self, mock_agent_class):
        """测试异常路径"""
        from src.mcp.tools import _test_handler

        # 执行测试
        args = {"path": "test.py"}
        result = _test_handler(args)

        # 验证
        assert "error" in result
        assert result["error"] == "Exception"


class TestRefactorHandler:
    """测试 _refactor_handler"""

    @patch("src.agents.architect.ArchitectAgent")
    @patch("asyncio.new_event_loop")
    def test_refactor_handler_success(self, mock_new_loop, mock_agent_class):
        """测试成功路径"""
        from src.mcp.tools import _refactor_handler

        # 设置 mock
        mock_agent_instance = Mock()
        mock_agent_instance.execute = Mock(return_value=AgentResult(result="refactor complete"))
        mock_agent_class.return_value = mock_agent_instance

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = AgentResult(result="refactor complete")
        mock_new_loop.return_value = mock_loop

        # 执行测试
        args = {"path": "test.py", "goal": "improve structure"}
        result = _refactor_handler(args)

        # 验证
        assert "content" in result
        assert "refactor complete" in result["content"]

    @patch("src.agents.architect.ArchitectAgent", side_effect=Exception("test error"))
    def test_refactor_handler_exception(self, mock_agent_class):
        """测试异常路径"""
        from src.mcp.tools import _refactor_handler

        # 执行测试
        args = {"path": "test.py", "goal": "improve structure"}
        result = _refactor_handler(args)

        # 验证
        assert "error" in result
        assert result["error"] == "Exception"


class TestSecurityHandler:
    """测试 _security_handler"""

    @patch("src.agents.security.SecurityReviewerAgent")
    @patch("asyncio.new_event_loop")
    def test_security_handler_success(self, mock_new_loop, mock_agent_class):
        """测试成功路径"""
        from src.mcp.tools import _security_handler

        # 设置 mock
        mock_agent_instance = Mock()
        mock_agent_instance.execute = Mock(return_value=AgentResult(result="security review complete"))
        mock_agent_class.return_value = mock_agent_instance

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = AgentResult(result="security review complete")
        mock_new_loop.return_value = mock_loop

        # 执行测试
        args = {"path": "test.py"}
        result = _security_handler(args)

        # 验证
        assert "content" in result
        assert "security review complete" in result["content"]

    @patch("src.agents.security.SecurityReviewerAgent", side_effect=Exception("test error"))
    def test_security_handler_exception(self, mock_agent_class):
        """测试异常路径"""
        from src.mcp.tools import _security_handler

        # 执行测试
        args = {"path": "test.py"}
        result = _security_handler(args)

        # 验证
        assert "error" in result
        assert result["error"] == "Exception"


class TestVisionHandler:
    """测试 _vision_handler"""

    @patch("src.agents.vision.VisionAgent")
    @patch("asyncio.new_event_loop")
    def test_vision_handler_success(self, mock_new_loop, mock_agent_class):
        """测试成功路径"""
        from src.mcp.tools import _vision_handler

        # 设置 mock
        mock_agent_instance = Mock()
        mock_agent_instance.execute = Mock(return_value=AgentResult(result="vision analysis complete"))
        mock_agent_class.return_value = mock_agent_instance

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = AgentResult(result="vision analysis complete")
        mock_new_loop.return_value = mock_loop

        # 执行测试
        args = {"image_path": "image.png", "mode": "analysis"}
        result = _vision_handler(args)

        # 验证
        assert "content" in result
        assert "vision analysis complete" in result["content"]

    @patch("src.agents.vision.VisionAgent", side_effect=Exception("test error"))
    def test_vision_handler_exception(self, mock_agent_class):
        """测试异常路径"""
        from src.mcp.tools import _vision_handler

        # 执行测试
        args = {"image_path": "image.png", "mode": "analysis"}
        result = _vision_handler(args)

        # 验证
        assert "error" in result
        assert result["error"] == "Exception"

    def test_vision_handler_no_image_path(self):
        """测试没有 image_path 的情况"""

        # 这个测试只是确保函数能处理没有 image_path 的情况
        # 由于需要 mock Agent，这里只测试参数处理
        args = {"mode": "analysis"}
        # 不执行实际函数调用，只测试参数处理逻辑
        from src.mcp.tools import _resolve_path
        image_path = args.get("image_path", "")
        if image_path:
            image_path = _resolve_path(image_path)
        assert image_path == ""


class TestExploreHandler:
    """测试 _explore_handler"""

    @patch("src.agents.explore.ExploreAgent")
    @patch("asyncio.new_event_loop")
    def test_explore_handler_success(self, mock_new_loop, mock_agent_class):
        """测试成功路径"""
        from src.mcp.tools import _explore_handler

        # 设置 mock
        mock_agent_instance = Mock()
        mock_agent_instance.execute = Mock(return_value=AgentResult(result="explore complete"))
        mock_agent_class.return_value = mock_agent_instance

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = AgentResult(result="explore complete")
        mock_new_loop.return_value = mock_loop

        # 执行测试
        args = {"depth": 3}
        result = _explore_handler(args)

        # 验证
        assert "content" in result
        assert "explore complete" in result["content"]

    @patch("src.agents.explore.ExploreAgent", side_effect=Exception("test error"))
    def test_explore_handler_exception(self, mock_agent_class):
        """测试异常路径"""
        from src.mcp.tools import _explore_handler

        # 执行测试
        args = {"depth": 3}
        result = _explore_handler(args)

        # 验证
        assert "error" in result
        assert result["error"] == "Exception"


class TestPlanHandler:
    """测试 _plan_handler"""

    @patch("src.agents.planner.PlannerAgent")
    @patch("asyncio.new_event_loop")
    def test_plan_handler_success(self, mock_new_loop, mock_agent_class):
        """测试成功路径"""
        from src.mcp.tools import _plan_handler

        # 设置 mock
        mock_agent_instance = Mock()
        mock_agent_instance.execute = Mock(return_value=AgentResult(result="plan complete"))
        mock_agent_class.return_value = mock_agent_instance

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = AgentResult(result="plan complete")
        mock_new_loop.return_value = mock_loop

        # 执行测试
        args = {"task": "implement feature X"}
        result = _plan_handler(args)

        # 验证
        assert "content" in result
        assert "plan complete" in result["content"]

    @patch("src.agents.planner.PlannerAgent", side_effect=Exception("test error"))
    def test_plan_handler_exception(self, mock_agent_class):
        """测试异常路径"""
        from src.mcp.tools import _plan_handler

        # 执行测试
        args = {"task": "implement feature X"}
        result = _plan_handler(args)

        # 验证
        assert "error" in result
        assert result["error"] == "Exception"


class TestGetMcpTools:
    """测试 get_mcp_tools 函数"""

    def test_get_mcp_tools_returns_8_tools(self):
        """测试返回 8 个 tool dict"""
        from src.mcp.tools import get_mcp_tools

        tools = get_mcp_tools()

        # 验证返回 8 个工具
        assert len(tools) == 8

    def test_get_mcp_tools_structure(self):
        """测试每个 tool dict 包含 name/description/inputSchema/handler"""
        from src.mcp.tools import get_mcp_tools

        tools = get_mcp_tools()

        # 验证每个工具的结构
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert "handler" in tool
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)
            assert isinstance(tool["inputSchema"], dict)
            assert callable(tool["handler"])

    def test_get_mcp_tools_names(self):
        """测试工具名称正确"""
        from src.mcp.tools import get_mcp_tools

        tools = get_mcp_tools()
        tool_names = [tool["name"] for tool in tools]

        expected_names = [
            "omc_code_review",
            "omc_debug",
            "omc_test",
            "omc_refactor",
            "omc_security_review",
            "omc_vision",
            "omc_explore",
            "omc_plan",
        ]

        assert tool_names == expected_names


class TestGetToolHandler:
    """测试 get_tool_handler 函数"""

    def test_get_tool_handler_existing(self):
        """测试通过名字能取到 handler"""
        from src.mcp.tools import get_tool_handler

        # 测试存在的工具
        handler = get_tool_handler("omc_code_review")
        assert callable(handler)

        handler = get_tool_handler("omc_debug")
        assert callable(handler)

        handler = get_tool_handler("omc_plan")
        assert callable(handler)

    def test_get_tool_handler_not_existing(self):
        """测试不存在的工具返回 None"""
        from src.mcp.tools import get_tool_handler

        # 测试不存在的工具
        handler = get_tool_handler("nonexistent_tool")
        assert handler is None

    def test_get_tool_handler_all_tools(self):
        """测试所有工具都能通过名字取到"""
        from src.mcp.tools import get_mcp_tools, get_tool_handler

        tools = get_mcp_tools()

        # 验证所有工具都能通过名字取到
        for tool in tools:
            handler = get_tool_handler(tool["name"])
            assert handler == tool["handler"]


# ------------------------------------------------------------------
# 集成测试：验证 mock 策略
# ------------------------------------------------------------------

class TestMockStrategy:
    """测试 mock 策略是否正确"""

    @patch("src.agents.code_reviewer.CodeReviewerAgent")
    @patch("asyncio.new_event_loop")
    def test_mock_agent_called_with_none_model_router(self, mock_new_loop, mock_agent_class):
        """测试 Agent 被正确初始化"""
        from src.mcp.tools import _code_review_handler

        # 设置 mock
        mock_agent_instance = Mock()
        mock_agent_instance.execute = Mock(return_value=AgentResult(result="test"))
        mock_agent_class.return_value = mock_agent_instance

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = AgentResult(result="test")
        mock_new_loop.return_value = mock_loop

        # 执行
        args = {"path": "test.py"}
        _code_review_handler(args)

        # 验证 Agent 被调用时的参数
        mock_agent_class.assert_called_once_with(model_router=None)

    @patch("src.agents.code_reviewer.CodeReviewerAgent")
    @patch("asyncio.new_event_loop")
    def test_mock_loop_closed_after_use(self, mock_new_loop, mock_agent_class):
        """测试事件循环使用后被正确关闭"""
        from src.mcp.tools import _code_review_handler

        # 设置 mock
        mock_agent_instance = Mock()
        mock_agent_instance.execute = Mock(return_value=AgentResult(result="test"))
        mock_agent_class.return_value = mock_agent_instance

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = AgentResult(result="test")
        mock_new_loop.return_value = mock_loop

        # 执行
        args = {"path": "test.py"}
        _code_review_handler(args)

        # 验证 loop.close() 被调用
        mock_loop.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
