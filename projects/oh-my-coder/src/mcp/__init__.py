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
    from mcp.types import Resource, TextContent, Tool  # noqa: F401

    from mcp.server import Server  # noqa: F401

    MCP_SDK_AVAILABLE = True
except Exception:
    MCP_SDK_AVAILABLE = False

from .resources import MCP_RESOURCES, get_mcp_resources
from .server import McpServer
from .tools import MCP_TOOLS, get_mcp_tools

__all__ = [
    "MCP_RESOURCES",
    "MCP_SDK_AVAILABLE",
    "MCP_TOOLS",
    "McpServer",
    "get_mcp_resources",
    "get_mcp_tools",
]
