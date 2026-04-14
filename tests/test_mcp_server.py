"""
MCP Server 单元测试
"""

from pathlib import Path


from src.mcp.server import McpServer
from src.mcp.tools import get_mcp_tools, get_tool_handler, MCP_TOOLS
from src.mcp.resources import get_mcp_resources, MCP_RESOURCES


class TestMcpServerMetadata:
    def test_server_version(self):
        assert McpServer.VERSION == "1.0.0"

    def test_protocol_version(self):
        assert McpServer.PROTOCOL_VERSION == "2024-11-05"


class TestMcpServerCapabilities:
    def test_initialize_returns_capabilities(self):
        server = McpServer(workspace=Path("/tmp"))
        # 直接调用 _capabilities
        caps = server._capabilities()
        assert caps["serverInfo"]["name"] == "oh-my-coder"
        assert caps["serverInfo"]["version"] == "1.0.0"
        assert "capabilities" in caps
        assert "tools" in caps["capabilities"]
        assert "resources" in caps["capabilities"]


class TestListTools:
    def test_list_tools_returns_tools(self):
        server = McpServer()
        result = server._list_tools()
        assert "tools" in result
        tools = result["tools"]
        assert len(tools) >= 4  # 至少 4 个核心工具

    def test_tool_has_required_fields(self):
        server = McpServer()
        result = server._list_tools()
        for tool in result["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_core_tools_present(self):
        server = McpServer()
        result = server._list_tools()
        tool_names = [t["name"] for t in result["tools"]]
        assert "omc_code_review" in tool_names
        assert "omc_debug" in tool_names
        assert "omc_test" in tool_names
        assert "omc_refactor" in tool_names


class TestListResources:
    def test_list_resources_returns_resources(self):
        server = McpServer()
        result = server._list_resources()
        assert "resources" in result
        resources = result["resources"]
        assert len(resources) >= 3

    def test_resource_has_required_fields(self):
        server = McpServer()
        result = server._list_resources()
        for res in result["resources"]:
            assert "uri" in res
            assert "name" in res
            assert "description" in res
            assert "mimeType" in res

    def test_workspace_resources_present(self):
        server = McpServer()
        result = server._list_resources()
        uris = [r["uri"] for r in result["resources"]]
        assert "omc://workspace/summary" in uris
        assert "omc://workspace/structure" in uris


class TestToolHandler:
    def test_get_tool_handler_returns_handler(self):
        handler = get_tool_handler("omc_code_review")
        assert handler is not None
        assert callable(handler)

    def test_get_tool_handler_unknown_returns_none(self):
        handler = get_tool_handler("nonexistent_tool")
        assert handler is None

    def test_all_tools_have_handler(self):
        for tool in MCP_TOOLS:
            handler = get_tool_handler(tool["name"])
            assert handler is not None, f"Tool {tool['name']} has no handler"


class TestToolRegistration:
    def test_tools_have_valid_schema(self):
        for tool in MCP_TOOLS:
            schema = tool["inputSchema"]
            assert schema["type"] == "object"
            if "required" in schema:
                assert isinstance(schema["required"], list)

    def test_code_review_requires_path(self):
        for tool in MCP_TOOLS:
            if tool["name"] == "omc_code_review":
                assert "path" in tool["inputSchema"].get("required", [])

    def test_debug_has_path_and_error(self):
        for tool in MCP_TOOLS:
            if tool["name"] == "omc_debug":
                props = tool["inputSchema"]["properties"]
                assert "path" in props
                assert "error" in props


class TestResourceRegistration:
    def test_resources_have_generators(self):
        for res in MCP_RESOURCES:
            assert "generator" in res
            assert callable(res["generator"])

    def test_uris_are_unique(self):
        uris = [r["uri"] for r in MCP_RESOURCES]
        assert len(uris) == len(set(uris))


class TestMcpServerJSONRPC:
    def test_invalid_jsonrpc_version(self, capsys):
        server = McpServer()
        req = {"jsonrpc": "1.0", "id": 1, "method": "ping"}
        server._handle_request(req)
        # 检查是否有错误输出

    def test_missing_method(self, capsys):
        server = McpServer()
        req = {"jsonrpc": "2.0", "id": 1, "method": "nonexistent_method"}
        server._handle_request(req)


class TestToolsList:
    def test_get_mcp_tools_returns_list(self):
        tools = get_mcp_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 4

    def test_tools_are_dicts(self):
        tools = get_mcp_tools()
        for tool in tools:
            assert isinstance(tool, dict)


class TestResourcesList:
    def test_get_mcp_resources_returns_list(self):
        resources = get_mcp_resources()
        assert isinstance(resources, list)
        assert len(resources) >= 3

    def test_resources_are_dicts(self):
        resources = get_mcp_resources()
        for res in resources:
            assert isinstance(res, dict)
