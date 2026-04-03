"""
Agents 模块

所有 Agent 的导出入口。
使用装饰器 @register_agent 自动注册。
"""
from .base import BaseAgent, register_agent, get_agent, list_agents
from .explore import ExploreAgent
from .analyst import AnalystAgent
from .planner import PlannerAgent
from .architect import ArchitectAgent
from .executor import ExecutorAgent
from .verifier import VerifierAgent
from .test_engineer import TestEngineerAgent
from .code_reviewer import CodeReviewerAgent
from .debugger import DebuggerAgent
from .critic import CriticAgent
from .writer import WriterAgent
from .designer import DesignerAgent
from .security import SecurityReviewerAgent
from .git_master import GitMasterAgent
from .code_simplifier import CodeSimplifierAgent
from .tracer import TracerAgent

# 导出所有 Agent
__all__ = [
    "BaseAgent",
    "register_agent",
    "get_agent",
    "list_agents",
    # Build/Analysis Lane
    "ExploreAgent",
    "AnalystAgent",
    "PlannerAgent",
    "ArchitectAgent",
    "DebuggerAgent",
    "ExecutorAgent",
    "VerifierAgent",
    "TracerAgent",
    # Review Lane
    "CodeReviewerAgent",
    "SecurityReviewerAgent",
    # Domain Lane
    "TestEngineerAgent",
    "DesignerAgent",
    "WriterAgent",
    "GitMasterAgent",
    "CodeSimplifierAgent",
    # Coordination Lane
    "CriticAgent",
]
