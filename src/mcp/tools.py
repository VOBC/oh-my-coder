"""
MCP Tools — 把 oh-my-coder Agent 能力暴露为 MCP tools

每个 tool 对应一个 Agent 调用，参数透传到 Agent。
工作区上下文自动注入，无需每次传 workspace path。

MCP SDK 可用时（Python 3.10+）返回 Tool 对象，
否则返回 dict 格式（手动 stdio 实现）。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------------
# MCP Tool 注册表
# ------------------------------------------------------------------

# 工作区根目录（运行时由 MCPServer 注入）
_WORKSPACE: Optional[Path] = None


def set_workspace(workspace: Path) -> None:
    """设置工作区路径（MCPServer 启动时调用）"""
    global _WORKSPACE
    _WORKSPACE = workspace.resolve()


def get_workspace() -> Path:
    """获取工作区路径"""
    return _WORKSPACE or Path.cwd()


def _resolve_path(path: Optional[str]) -> str:
    """解析路径：相对路径 → 工作区绝对路径"""
    if path is None:
        return str(get_workspace())
    p = Path(path)
    if p.is_absolute():
        return path
    return str(get_workspace() / path)


# ------------------------------------------------------------------
# Tool 处理器（每个工具对应一个 Agent 调用）
# ------------------------------------------------------------------


def _code_review_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """omc_code_review — 执行代码审查"""
    path = _resolve_path(args.get("path"))
    from ..agents.code_reviewer import CodeReviewerAgent
    from ..agents.base import AgentContext

    try:
        agent = CodeReviewerAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"审查代码: {path}",
            metadata={"paths": [path]},
        )
        # 同步运行（MCPServer 为隔离进程，同步可接受）
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _debug_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """omc_debug — 自动定位并修复 Bug"""
    path = _resolve_path(args.get("path"))
    error = args.get("error", "")
    from ..agents.debugger import DebuggerAgent
    from ..agents.base import AgentContext

    try:
        agent = DebuggerAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"定位并修复 Bug: {error}",
            metadata={"paths": [path], "error": error},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _test_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """omc_test — 为代码生成测试用例"""
    path = _resolve_path(args.get("path"))
    from ..agents.test_engineer import TestEngineerAgent
    from ..agents.base import AgentContext

    try:
        agent = TestEngineerAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"为代码生成测试用例: {path}",
            metadata={"paths": [path]},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _refactor_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """omc_refactor — 重构代码改善结构和性能"""
    path = _resolve_path(args.get("path"))
    goal = args.get("goal", "改善代码结构和性能")
    from ..agents.architect import ArchitectAgent
    from ..agents.base import AgentContext

    try:
        agent = ArchitectAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"重构 {path}，目标: {goal}",
            metadata={"paths": [path], "goal": goal},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _security_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """omc_security_review — 安全审查"""
    path = _resolve_path(args.get("path"))
    from ..agents.security import SecurityReviewerAgent
    from ..agents.base import AgentContext

    try:
        agent = SecurityReviewerAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"安全审查: {path}",
            metadata={"paths": [path]},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _vision_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """omc_vision — 视觉分析（截图 / UI 代码生成）"""
    image_path = args.get("image_path", "")
    mode = args.get("mode", "analysis")
    if image_path:
        image_path = _resolve_path(image_path)
    from ..agents.vision import VisionAgent
    from ..agents.base import AgentContext

    try:
        agent = VisionAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=f"视觉分析: {image_path} (mode={mode})",
            metadata={"image_path": image_path, "mode": mode},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _explore_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """omc_explore — 项目探索"""
    from ..agents.explore import ExploreAgent
    from ..agents.base import AgentContext

    try:
        agent = ExploreAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description="探索项目结构",
            metadata=args,
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


def _plan_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """omc_plan — 任务规划和拆分"""
    task = args.get("task", "")
    from ..agents.planner import PlannerAgent
    from ..agents.base import AgentContext

    try:
        agent = PlannerAgent(model_router=None)
        ctx = AgentContext(
            project_path=get_workspace(),
            task_description=task,
            metadata={"task": task},
        )
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(agent.execute(ctx))
        finally:
            loop.close()
        return {"content": str(result.result or result)}
    except Exception as e:
        return {"error": type(e).__name__}


# ------------------------------------------------------------------
# MCP Tool 定义（dict 格式，兼容 Python 3.9 原生实现）
# ------------------------------------------------------------------

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "omc_code_review",
        "description": "执行代码审查，分析代码质量、潜在问题和改进建议",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "代码路径（文件或目录，相对路径自动拼接工作区）",
                }
            },
            "required": ["path"],
        },
        "handler": _code_review_handler,
    },
    {
        "name": "omc_debug",
        "description": "自动定位并修复 Bug，分析错误日志和代码",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "代码路径",
                },
                "error": {
                    "type": "string",
                    "description": "错误信息或日志片段",
                },
            },
            "required": ["path"],
        },
        "handler": _debug_handler,
    },
    {
        "name": "omc_test",
        "description": "为代码生成测试用例（pytest 格式）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "代码路径（生成测试的文件）",
                }
            },
            "required": ["path"],
        },
        "handler": _test_handler,
    },
    {
        "name": "omc_refactor",
        "description": "重构代码改善结构和性能",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "代码路径",
                },
                "goal": {
                    "type": "string",
                    "description": "重构目标（可选，默认：改善代码结构和性能）",
                },
            },
            "required": ["path"],
        },
        "handler": _refactor_handler,
    },
    {
        "name": "omc_security_review",
        "description": "安全审查，扫描注入、XSS、敏感信息等安全漏洞",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "代码路径",
                }
            },
            "required": ["path"],
        },
        "handler": _security_handler,
    },
    {
        "name": "omc_vision",
        "description": "视觉分析：截图 UI 分析 + UI 代码自动生成（截图 → HTML/CSS）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "截图路径（文件路径）",
                },
                "mode": {
                    "type": "string",
                    "enum": ["analysis", "ui_code"],
                    "description": "模式: analysis/ui_code (视觉分析或UI代码生成)",
                },
            },
        },
        "handler": _vision_handler,
    },
    {
        "name": "omc_explore",
        "description": "探索项目结构，生成文件树和项目摘要",
        "inputSchema": {
            "type": "object",
            "properties": {
                "depth": {
                    "type": "integer",
                    "description": "目录遍历深度（默认 3）",
                },
                "include_patterns": {
                    "type": "string",
                    "description": "包含的文件模式，逗号分隔（如：*.py,*.js）",
                },
            },
        },
        "handler": _explore_handler,
    },
    {
        "name": "omc_plan",
        "description": "任务规划和拆分，生成可执行步骤列表",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "要规划的任务描述",
                }
            },
            "required": ["task"],
        },
        "handler": _plan_handler,
    },
]


def get_mcp_tools() -> List[Dict[str, Any]]:
    """获取所有 MCP tools（dict 格式，兼容 Python 3.9）"""
    return MCP_TOOLS


def get_tool_handler(name: str):
    """根据工具名获取处理器"""
    for tool in MCP_TOOLS:
        if tool["name"] == name:
            return tool["handler"]
    return None
