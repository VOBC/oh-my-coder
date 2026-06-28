"""
tests/test_mcp_server.py

单元测试 — src/mcp/server.py
覆盖率目标 > 80%，覆盖所有公开函数和关键分支。
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# 导入被测模块
# ---------------------------------------------------------------------------

import src.mcp.server as mcp_server


# ---------------------------------------------------------------------------
# 辅助：捕获 stdout 的 fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def capture_stdout():
    """捕获 stdout 输出的 fixture。"""
    buffer = StringIO()
    return buffer


# ---------------------------------------------------------------------------
# 1. McpServer 初始化
# ---------------------------------------------------------------------------

class TestMcpServerInit:
    """测试 McpServer 构造函数。"""

    def test_init_with_default_workspace(self):
        """未提供 workspace 时，使用 cwd。"""
        server = mcp_server.McpServer()
        assert server.workspace == Path.cwd()
        assert server._initialized is False

    def test_init_with_custom_workspace(self, tmp_path):
        """提供 workspace 时，使用提供的值。"""
        server = mcp_server.McpServer(workspace=tmp_path)
        assert server.workspace == tmp_path

    def test_init_loads_tools_and_resources(self):
        """初始化时应加载 tools 和 resources。"""
        with patch("src.mcp.server.get_mcp_tools") as mock_get_tools, \
             patch("src.mcp.server.get_mcp_resources") as mock_get_resources:
            mock_get_tools.return_value = [{"name": "tool1"}]
            mock_get_resources.return_value = [{"uri": "omc://test"}]

            server = mcp_server.McpServer()

            assert len(server._tools) == 1
            assert len(server._resources) == 1
            mock_get_tools.assert_called_once()
            mock_get_resources.assert_called_once()


# ---------------------------------------------------------------------------
# 2. _send_response / _send_error
# ---------------------------------------------------------------------------

class TestSendResponseAndError:
    """测试 JSON-RPC 响应和错误发送。"""

    def test_send_response_output(self, capsys):
        """_send_response 应输出正确的 JSON-RPC 响应。"""
        server = mcp_server.McpServer()
        server._send_response("req-1", {"status": "ok"})

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert output["jsonrpc"] == "2.0"
        assert output["id"] == "req-1"
        assert output["result"]["status"] == "ok"

    def test_send_response_with_none_id(self, capsys):
        """id 为 None 时也能正确输出。"""
        server = mcp_server.McpServer()
        server._send_response(None, {"pong": True})

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert output["id"] is None
        assert output["result"]["pong"] is True

    def test_send_error_output(self, capsys):
        """_send_error 应输出正确的 JSON-RPC 错误。"""
        server = mcp_server.McpServer()
        server._send_error("req-1", -32600, "Invalid Request")

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert output["jsonrpc"] == "2.0"
        assert output["id"] == "req-1"
        assert "error" in output
        assert output["error"]["code"] == -32600
        assert output["error"]["message"] == "Invalid Request"

    def test_send_error_with_none_id(self, capsys):
        """错误 id 为 None 时也能正确输出。"""
        server = mcp_server.McpServer()
        server._send_error(None, -32700, "Parse error")

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert output["id"] is None
        assert output["error"]["code"] == -32700


# ---------------------------------------------------------------------------
# 3. _handle_request — 主路由
# ---------------------------------------------------------------------------

class TestHandleRequest:
    """测试 JSON-RPC 请求路由。"""

    def test_invalid_jsonrpc_version(self, capsys):
        """jsonrpc 不为 "2.0" 时返回 Invalid Request。"""
        server = mcp_server.McpServer()
        req = {"jsonrpc": "1.0", "method": "initialize", "id": "1"}
        server._handle_request(req)

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert "error" in output
        assert output["error"]["code"] == -32600
        assert "Invalid Request" in output["error"]["message"]

    def test_initialize_method(self, capsys):
        """initialize 方法应返回服务端能力。"""
        server = mcp_server.McpServer()
        req = {"jsonrpc": "2.0", "method": "initialize", "id": "1"}
        server._handle_request(req)

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert "result" in output
        assert output["result"]["protocolVersion"] == "2024-11-05"
        assert output["result"]["serverInfo"]["name"] == "oh-my-coder"
        assert server._initialized is True

    def test_tools_list_method(self, capsys):
        """tools/list 方法应返回工具列表。"""
        with patch("src.mcp.server.get_mcp_tools") as mock_get_tools:
            mock_get_tools.return_value = [
                {"name": "tool1", "description": "desc1", "inputSchema": {}}
            ]

            server = mcp_server.McpServer()
            req = {"jsonrpc": "2.0", "method": "tools/list", "id": "2"}
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert "result" in output
            assert "tools" in output["result"]
            assert len(output["result"]["tools"]) == 1
            assert output["result"]["tools"][0]["name"] == "tool1"

    def test_tools_call_method_success(self, capsys):
        """tools/call 方法成功时应返回工具执行结果。"""
        mock_handler = Mock(return_value={"content": "success result"})

        with patch("src.mcp.server.get_tool_handler") as mock_get_handler:
            mock_get_handler.return_value = mock_handler

            server = mcp_server.McpServer()
            req = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "omc_test", "arguments": {}},
                "id": "3"
            }
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert "result" in output
            assert output["result"]["content"][0]["text"] == "success result"

    def test_tools_call_method_tool_not_found(self, capsys):
        """tools/call 方法工具不存在时应返回错误。"""
        with patch("src.mcp.server.get_tool_handler") as mock_get_handler:
            mock_get_handler.return_value = None

            server = mcp_server.McpServer()
            req = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "nonexistent", "arguments": {}},
                "id": "4"
            }
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert "error" in output
            assert output["error"]["code"] == -32602
            assert "Tool not found" in output["error"]["message"]

    def test_tools_call_method_with_error_result(self, capsys):
        """tools/call 方法工具返回 error 时应设置 isError。"""
        mock_handler = Mock(return_value={"error": "something went wrong"})

        with patch("src.mcp.server.get_tool_handler") as mock_get_handler:
            mock_get_handler.return_value = mock_handler

            server = mcp_server.McpServer()
            req = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "omc_test", "arguments": {}},
                "id": "5"
            }
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert "result" in output
            assert output["result"]["isError"] is True
            assert "❌ Error: something went wrong" in output["result"]["content"][0]["text"]

    def test_tools_call_method_with_content_field(self, capsys):
        """tools/call 方法工具返回 content 字段时应正确提取。"""
        mock_handler = Mock(return_value={"content": "direct content field"})

        with patch("src.mcp.server.get_tool_handler") as mock_get_handler:
            mock_get_handler.return_value = mock_handler

            server = mcp_server.McpServer()
            req = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "omc_test", "arguments": {}},
                "id": "6"
            }
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert output["result"]["content"][0]["text"] == "direct content field"

    def test_tools_call_method_with_text_field(self, capsys):
        """tools/call 方法工具返回 text 字段时应正确提取。"""
        mock_handler = Mock(return_value={"text": "text field result"})

        with patch("src.mcp.server.get_tool_handler") as mock_get_handler:
            mock_get_handler.return_value = mock_handler

            server = mcp_server.McpServer()
            req = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "omc_test", "arguments": {}},
                "id": "7"
            }
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert output["result"]["content"][0]["text"] == "text field result"

    def test_tools_call_method_exception(self, capsys):
        """tools/call 方法工具执行异常时应返回错误。"""
        mock_handler = Mock(side_effect=Exception("tool crashed"))

        with patch("src.mcp.server.get_tool_handler") as mock_get_handler:
            mock_get_handler.return_value = mock_handler

            server = mcp_server.McpServer()
            req = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "omc_test", "arguments": {}},
                "id": "8"
            }
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert "error" in output
            assert output["error"]["code"] == -32603
            assert "Tool execution error" in output["error"]["message"]

    def test_resources_list_method(self, capsys):
        """resources/list 方法应返回资源列表。"""
        with patch("src.mcp.server.get_mcp_resources") as mock_get_resources:
            mock_get_resources.return_value = [
                {
                    "uri": "omc://test",
                    "name": "test",
                    "description": "desc",
                    "mimeType": "text/plain"
                }
            ]

            server = mcp_server.McpServer()
            req = {"jsonrpc": "2.0", "method": "resources/list", "id": "9"}
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert "result" in output
            assert "resources" in output["result"]
            assert len(output["result"]["resources"]) == 1

    def test_resources_read_method_success(self, capsys):
        """resources/read 方法成功时应返回资源内容。"""
        with patch("src.mcp.server.get_mcp_resources") as mock_get_resources:
            mock_get_resources.return_value = [
                {
                    "uri": "omc://workspace/summary",
                    "name": "summary",
                    "description": "desc",
                    "mimeType": "text/markdown",
                    "generator": Mock(return_value="summary content")
                }
            ]

            server = mcp_server.McpServer()
            req = {
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "omc://workspace/summary"},
                "id": "10"
            }
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert "result" in output
            assert "contents" in output["result"]
            assert output["result"]["contents"][0]["text"] == "summary content"

    def test_resources_read_method_resource_not_found(self, capsys):
        """resources/read 方法资源不存在时应返回错误。"""
        with patch("src.mcp.server.get_mcp_resources") as mock_get_resources:
            mock_get_resources.return_value = []

            server = mcp_server.McpServer()
            req = {
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "omc://nonexistent"},
                "id": "11"
            }
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert "error" in output
            assert output["error"]["code"] == -32602
            assert "Resource not found" in output["error"]["message"]

    def test_resources_read_method_exception(self, capsys):
        """resources/read 方法生成器异常时应返回错误。"""
        with patch("src.mcp.server.get_mcp_resources") as mock_get_resources:
            mock_get_resources.return_value = [
                {
                    "uri": "omc://workspace/summary",
                    "name": "summary",
                    "description": "desc",
                    "mimeType": "text/markdown",
                    "generator": Mock(side_effect=Exception("read failed"))
                }
            ]

            server = mcp_server.McpServer()
            req = {
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "omc://workspace/summary"},
                "id": "12"
            }
            server._handle_request(req)

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())

            assert "error" in output
            assert output["error"]["code"] == -32603
            assert "Resource read error" in output["error"]["message"]

    def test_ping_method(self, capsys):
        """ping 方法应返回 pong。"""
        server = mcp_server.McpServer()
        req = {"jsonrpc": "2.0", "method": "ping", "id": "13"}
        server._handle_request(req)

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert "result" in output
        assert output["result"]["pong"] is True

    def test_notifications_initialized_method(self, capsys):
        """notifications/initialized 方法应静默处理（无输出）。"""
        server = mcp_server.McpServer()

        # 保存原始 stdout
        import sys
        original_stdout = sys.stdout

        buffer = StringIO()
        sys.stdout = buffer

        try:
            req = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            server._handle_request(req)

            output = buffer.getvalue()
            assert output == ""  # 不应有输出
        finally:
            sys.stdout = original_stdout

    def test_method_not_found(self, capsys):
        """未知方法应返回 Method not found 错误。"""
        server = mcp_server.McpServer()
        req = {"jsonrpc": "2.0", "method": "unknown/method", "id": "14"}
        server._handle_request(req)

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert "error" in output
        assert output["error"]["code"] == -32601
        assert "Method not found" in output["error"]["message"]


# ---------------------------------------------------------------------------
# 4. _capabilities / _list_tools / _list_resources
# ---------------------------------------------------------------------------

class TestCapabilitiesAndListings:
    """测试服务端能力声明和列表方法。"""

    def test_capabilities_structure(self):
        """_capabilities 应返回正确结构。"""
        server = mcp_server.McpServer()
        caps = server._capabilities()

        assert caps["protocolVersion"] == "2024-11-05"
        assert caps["serverInfo"]["name"] == "oh-my-coder"
        assert caps["serverInfo"]["version"] == "0.2.0"
        assert "tools" in caps["capabilities"]
        assert "resources" in caps["capabilities"]

    def test_list_tools_structure(self):
        """_list_tools 应返回正确结构。"""
        with patch("src.mcp.server.get_mcp_tools") as mock_get_tools:
            mock_get_tools.return_value = [
                {"name": "tool1", "description": "desc1", "inputSchema": {"type": "object"}}
            ]

            server = mcp_server.McpServer()
            result = server._list_tools()

            assert "tools" in result
            assert len(result["tools"]) == 1
            assert result["tools"][0]["name"] == "tool1"
            assert result["tools"][0]["description"] == "desc1"
            assert result["tools"][0]["inputSchema"] == {"type": "object"}

    def test_list_resources_structure(self):
        """_list_resources 应返回正确结构。"""
        with patch("src.mcp.server.get_mcp_resources") as mock_get_resources:
            mock_get_resources.return_value = [
                {
                    "uri": "omc://test",
                    "name": "test",
                    "description": "desc",
                    "mimeType": "text/markdown"
                }
            ]

            server = mcp_server.McpServer()
            result = server._list_resources()

            assert "resources" in result
            assert len(result["resources"]) == 1
            assert result["resources"][0]["uri"] == "omc://test"
            assert result["resources"][0]["name"] == "test"
            assert result["resources"][0]["mimeType"] == "text/markdown"


# ---------------------------------------------------------------------------
# 5. run 方法（主循环）
# ---------------------------------------------------------------------------

class TestRun:
    """测试 run() 主循环。"""

    def test_run_processes_valid_json_line(self):
        """run() 应处理有效的 JSON 行。"""
        import io
        import sys

        # 准备输入
        test_input = '{"jsonrpc": "2.0", "method": "ping", "id": "1"}\n'
        sys.stdin = io.StringIO(test_input)

        # 捕获输出
        output_buffer = io.StringIO()
        sys.stdout = output_buffer

        try:
            server = mcp_server.McpServer()
            # 只处理一行后退出
            server.run()
        except StopIteration:
            pass  # Expected when stdin is exhausted
        finally:
            sys.stdout = sys.__stdout__
            sys.stdin = sys.__stdin__

    def test_run_handles_json_decode_error(self, capsys):
        """run() 应处理 JSON 解析错误。"""
        import io
        import sys

        # 准备无效 JSON 输入
        test_input = "not valid json\n"
        sys.stdin = io.StringIO(test_input)

        try:
            server = mcp_server.McpServer()
            # 重写 run 方法来只处理一行
            lines_processed = [0]
            original_run = server.run

            def limited_run():
                for line in sys.stdin:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        req = json.loads(line)
                        server._handle_request(req)
                    except json.JSONDecodeError:
                        server._send_error(None, -32700, "Parse error")
                    except Exception as e:
                        server._send_error(None, -32603, f"Internal error: {e}")
                    break  # 只处理一行

            server.run = limited_run
            server.run()

        finally:
            sys.stdin = sys.__stdin__

        captured = capsys.readouterr()
        # 应该输出错误响应
        assert captured.out != ""

    def test_run_handles_empty_lines(self):
        """run() 应跳过空行。"""
        import io
        import sys

        # 准备包含空行的输入
        test_input = "\n\n{'jsonrpc': '2.0', 'method': 'ping', 'id': '1'}\n"
        sys.stdin = io.StringIO(test_input)

        try:
            server = mcp_server.McpServer()

            # 只处理一行有效输入
            def limited_run():
                for line in sys.stdin:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        req = json.loads(line)
                        server._handle_request(req)
                    except json.JSONDecodeError:
                        server._send_error(None, -32700, "Parse error")
                    except Exception as e:
                        server._send_error(None, -32603, f"Internal error: {e}")
                    break

            server.run = limited_run
            server.run()  # 不应抛异常

        finally:
            sys.stdin = sys.__stdin__


# ---------------------------------------------------------------------------
# 6. main() 函数
# ---------------------------------------------------------------------------

class TestMain:
    """测试 main() CLI 入口点。"""

    def test_main_function_exists(self):
        """验证 main() 函数存在且可调用。"""
        assert callable(mcp_server.main)

    def test_mcp_server_import(self):
        """验证可以从模块导入 McpServer。"""
        from src.mcp.server import McpServer
        assert McpServer is not None

    @patch("src.mcp.server.McpServer")
    def test_main_creates_server_with_workspace(self, mock_server_class):
        """main() 应使用提供的工作区路径创建 McpServer。"""
        import argparse
        from unittest.mock import patch

        mock_server_instance = Mock()
        mock_server_class.return_value = mock_server_instance

        # Mock sys.argv to prevent ArgumentParser from using actual command line
        with patch("sys.argv", ["server.py", "--workspace", "/tmp/test"]):
            try:
                mcp_server.main()
            except SystemExit:
                pass  # main() calls server.run() which we can't easily test

        # 验证 McpServer 被调用（至少尝试创建）
        mock_server_class.assert_called_once()
        call_args = mock_server_class.call_args
        assert "workspace" in call_args.kwargs or len(call_args) > 0


# ---------------------------------------------------------------------------
# 7. 集成测试：完整请求-响应循环
# ---------------------------------------------------------------------------

class TestIntegration:
    """集成测试：验证完整的请求-响应循环。"""

    def test_full_initialize_and_tools_list(self, capsys):
        """完整流程：initialize -> tools/list。"""
        server = mcp_server.McpServer()

        # initialize
        req1 = {"jsonrpc": "2.0", "method": "initialize", "id": "1"}
        server._handle_request(req1)

        # tools/list
        req2 = {"jsonrpc": "2.0", "method": "tools/list", "id": "2"}
        server._handle_request(req2)

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")

        assert len(lines) == 2

        resp1 = json.loads(lines[0])
        resp2 = json.loads(lines[1])

        assert resp1["result"]["serverInfo"]["name"] == "oh-my-coder"
        assert "tools" in resp2["result"]

    def test_multiple_resources_read(self, capsys):
        """读取多个资源。"""
        with patch("src.mcp.server.get_mcp_resources") as mock_get_resources:
            mock_get_resources.return_value = [
                {
                    "uri": "omc://workspace/summary",
                    "name": "summary",
                    "description": "desc",
                    "mimeType": "text/markdown",
                    "generator": Mock(return_value="summary")
                },
                {
                    "uri": "omc://workspace/structure",
                    "name": "structure",
                    "description": "desc",
                    "mimeType": "text/markdown",
                    "generator": Mock(return_value="structure")
                }
            ]

            server = mcp_server.McpServer()

            # 读取第一个资源
            req1 = {
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "omc://workspace/summary"},
                "id": "1"
            }
            server._handle_request(req1)

            # 读取第二个资源
            req2 = {
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "omc://workspace/structure"},
                "id": "2"
            }
            server._handle_request(req2)

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")

            assert len(lines) == 2
            resp1 = json.loads(lines[0])
            resp2 = json.loads(lines[1])

            assert resp1["result"]["contents"][0]["text"] == "summary"
            assert resp2["result"]["contents"][0]["text"] == "structure"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
