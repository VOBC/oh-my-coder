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
from .document import DocumentAgent
from .executor import ExecutorAgent
from .explore import ExploreAgent
from .git_master import GitMasterAgent
from .planner import PlannerAgent
from .qa_tester import QATesterAgent
from .scientist import ScientistAgent
from .security import SecurityReviewerAgent
from .self_improving import LearningStore, SelfImprovingAgent
from .test_engineer import TestEngineerAgent
from .tracer import TracerAgent
from .verifier import VerifierAgent
from .vision import VisionAgent
from .writer import WriterAgent

# ---- 新增 Agent（2026-04-12）----
from .database import DatabaseAgent
from .api_agent import APIAgent
from .devops import DevOpsAgent
from .uml import UMLAgent
from .performance import PerformanceAgent
from .migration import MigrationAgent
from .prompt_agent import PromptAgent
from .auth_agent import AuthAgent
from .data_agent import DataAgent
from .skill_manage import SkillManageAgent

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
    "VisionAgent",
    "DocumentAgent",
    "WriterAgent",
    "GitMasterAgent",
    "CodeSimplifierAgent",
    "ScientistAgent",
    "QATesterAgent",
    # 新增 Domain Agent（2026-04-12）
    "DatabaseAgent",
    "APIAgent",
    "DevOpsAgent",
    "UMLAgent",
    "PerformanceAgent",
    "MigrationAgent",
    "PromptAgent",
    "AuthAgent",
    "DataAgent",
    # Coordination Lane
    "CriticAgent",
    "SkillManageAgent",
    # Self-Improving
    "LearningStore",
    "SelfImprovingAgent",
]
