"""
Agents 模块

所有 Agent 的导出入口。
使用装饰器 @register_agent 自动注册。
"""

from .analyst import AnalystAgent
from .architect import ArchitectAgent
from .base import BaseAgent, get_agent, list_agents, register_agent
from .code_reviewer import CodeReviewerAgent
from .code_simplifier import CodeSimplifierAgent
from .critic import CriticAgent
from .debugger import DebuggerAgent
from .designer import DesignerAgent
from .executor import ExecutorAgent
from .explore import ExploreAgent
from .git_master import GitMasterAgent
from .planner import PlannerAgent
from .qa_tester import QATesterAgent
from .scientist import ScientistAgent
from .security import SecurityReviewerAgent
from .test_engineer import TestEngineerAgent
from .tracer import TracerAgent
from .verifier import VerifierAgent
from .writer import WriterAgent

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
    "ScientistAgent",
    "QATesterAgent",
    # Coordination Lane
    "CriticAgent",
]
