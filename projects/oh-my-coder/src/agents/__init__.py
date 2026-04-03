"""
Agents 模块

所有 Agent 的导出入口。
使用装饰器 @register_agent 自动注册。
"""
from .base import BaseAgent, register_agent, get_agent, list_agents
from .explore import ExploreAgent
from .analyst import AnalystAgent
from .architect import ArchitectAgent
from .executor import ExecutorAgent
from .verifier import VerifierAgent
from .code_reviewer import CodeReviewerAgent
from .debugger import DebuggerAgent

# 导出所有 Agent
__all__ = [
    "BaseAgent",
    "register_agent",
    "get_agent",
    "list_agents",
    "ExploreAgent",
    "AnalystAgent",
    "ArchitectAgent",
    "ExecutorAgent",
    "VerifierAgent",
    "CodeReviewerAgent",
    "DebuggerAgent",
]
