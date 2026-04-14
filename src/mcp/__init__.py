"""
MCP (Model Context Protocol) 模块

oh-my-coder 作为 MCP Server，向外部客户端（Claude Desktop / Cursor / Dify 等）
暴露 Agent 能力。

协议：JSON-RPC 2.0 over stdio
- 读取 stdin，每行一个 JSON-RPC 请求
- 输出 stdout，每行一个 JSON-RPC 响应

MCP SDK 在 Python 3.10+ 时自动启用（pip install mcp），
Python 3.9 使用原生手动实现（无外部依赖）。
"""

__version__ = "1.0.0"

# Try importing MCP SDK (Python 3.10+), falls back to native impl
try:
    from mcp.server import Server  # noqa: F401
    from mcp.types import Tool, Resource, TextContent  # noqa: F401

    MCP_SDK_AVAILABLE = True
except Exception:  # noqa: BLE001
    MCP_SDK_AVAILABLE = False

from .server import McpServer
from .tools import get_mcp_tools, MCP_TOOLS
from .resources import get_mcp_resources, MCP_RESOURCES

__all__ = [
    "McpServer",
    "get_mcp_tools",
    "get_mcp_resources",
    "MCP_TOOLS",
    "MCP_RESOURCES",
    "MCP_SDK_AVAILABLE",
]
