from __future__ import annotations

"""
MCP Server — JSON-RPC 2.0 stdio 协议实现

支持 Claude Desktop / Cursor / Dify 等 MCP 客户端。
协议：每行一个 JSON-RPC 请求/响应。

手动实现（无外部依赖，Python 3.9 兼容）。
如已安装 MCP SDK（pip install mcp），自动优先使用。
"""

import json
import sys
from pathlib import Path
from typing import Any

from .resources import get_mcp_resources
from .tools import get_mcp_tools, get_tool_handler


class McpServer:
    """
    MCP Server（手动 stdio 实现，Python 3.9 兼容）

    支持的 JSON-RPC 方法：
    - initialize          — 初始化，返回服务端能力
    - tools/list          — 列出所有工具
    - tools/call          — 调用工具
    - resources/list      — 列出所有资源
    - resources/read      — 读取资源内容
    - ping                — 心跳检测
    """

    VERSION = "1.0.0"
    PROTOCOL_VERSION = "2024-11-05"

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()
        self._initialized = False
        self._tools = get_mcp_tools()
        self._resources = get_mcp_resources()

    # ------------------------------------------------------------------
    # JSON-RPC 协议处理
    # ------------------------------------------------------------------

    def _send_response(self, id: Any, result: Any) -> None:
        """发送 JSON-RPC 响应"""
        msg = {
            "jsonrpc": "2.0",
            "id": id,
            "result": result,
        }
        print(json.dumps(msg, ensure_ascii=False), flush=True)

    def _send_error(self, id: Any, code: int, message: str) -> None:
        """发送 JSON-RPC 错误"""
        msg = {
            "jsonrpc": "2.0",
            "id": id,
            "error": {
                "code": code,
                "message": message,
            },
        }
        print(json.dumps(msg, ensure_ascii=False), flush=True)

    def _handle_request(self, req: dict[str, Any]) -> None:
        """处理单个 JSON-RPC 请求"""
        jsonrpc = req.get("jsonrpc")
        if jsonrpc != "2.0":
            self._send_error(req.get("id"), -32600, "Invalid Request")
            return

        method = req.get("method", "")
        params = req.get("params", {})
        req_id = req.get("id")

        # 方法路由
        if method == "initialize":
            self._initialized = True
            self._send_response(req_id, self._capabilities())
        elif method == "tools/list":
            self._send_response(req_id, self._list_tools())
        elif method == "tools/call":
            self._handle_tool_call(req_id, params)
        elif method == "resources/list":
            self._send_response(req_id, self._list_resources())
        elif method == "resources/read":
            self._handle_resource_read(req_id, params)
        elif method == "ping":
            self._send_response(req_id, {"pong": True})
        elif method == "notifications/initialized":
            # Claude Desktop sends this after initialize
            pass
        else:
            self._send_error(req_id, -32601, f"Method not found: {method}")

    # ------------------------------------------------------------------
    # 协议方法实现
    # ------------------------------------------------------------------

    def _capabilities(self) -> dict[str, Any]:
        """服务端能力声明"""
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "serverInfo": {
                "name": "oh-my-coder",
                "version": self.VERSION,
            },
            "capabilities": {
                "tools": {},
                "resources": {},
            },
        }

    def _list_tools(self) -> dict[str, Any]:
        """列出所有 MCP tools"""
        tools = []
        for tool in self._tools:
            tools.append(
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": tool["inputSchema"],
                }
            )
        return {"tools": tools}

    def _handle_tool_call(self, req_id: Any, params: dict[str, Any]) -> None:
        """调用工具"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        handler = get_tool_handler(tool_name)
        if handler is None:
            self._send_error(req_id, -32602, f"Tool not found: {tool_name}")
            return

        try:
            result = handler(arguments)
            if "error" in result:
                self._send_response(
                    req_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ Error: {result['error']}",
                            }
                        ],
                        "isError": True,
                    },
                )
            else:
                content = result.get("content", result.get("text", ""))
                self._send_response(
                    req_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": content,
                            }
                        ],
                    },
                )
        except Exception as e:
            self._send_error(req_id, -32603, f"Tool execution error: {e}")

    def _list_resources(self) -> dict[str, Any]:
        """列出所有 MCP resources"""
        resources = []
        for res in self._resources:
            resources.append(
                {
                    "uri": res["uri"],
                    "name": res["name"],
                    "description": res["description"],
                    "mimeType": res.get("mimeType", "text/plain"),
                }
            )
        return {"resources": resources}

    def _handle_resource_read(self, req_id: Any, params: dict[str, Any]) -> None:
        """读取资源内容"""
        uri = params.get("uri", "")

        for res in self._resources:
            if res["uri"] == uri:
                try:
                    content = res["generator"]()
                    self._send_response(
                        req_id,
                        {
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": res.get("mimeType", "text/plain"),
                                    "text": content,
                                }
                            ],
                        },
                    )
                except Exception as e:
                    self._send_error(req_id, -32603, f"Resource read error: {e}")
                return

        self._send_error(req_id, -32602, f"Resource not found: {uri}")

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def run(self) -> None:
        """启动 stdio 主循环"""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                self._handle_request(req)
            except json.JSONDecodeError:
                self._send_error(None, -32700, "Parse error")
            except Exception as e:
                self._send_error(None, -32603, f"Internal error: {e}")


# ------------------------------------------------------------------
# 入口点
# ------------------------------------------------------------------


def main() -> None:
    """CLI 入口：python -m src.mcp.server"""
    import argparse

    parser = argparse.ArgumentParser(description="oh-my-coder MCP Server")
    parser.add_argument(
        "--workspace",
        "-w",
        type=Path,
        default=Path("."),
        help="工作区路径（默认当前目录）",
    )
    args = parser.parse_args()

    server = McpServer(workspace=args.workspace)
    server.run()


if __name__ == "__main__":
    main()
