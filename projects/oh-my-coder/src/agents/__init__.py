"""
Agents 模块

所有 Agent 的导出入口。
使用装饰器 @register_agent 自动注册。
"""

from .analyst import AnalystAgent
from .api_agent import APIAgent
from .architect import ArchitectAgent
from .auth_agent import AuthAgent
from .base import BaseAgent, get_agent, list_agents, register_agent
from .code_reviewer import CodeReviewerAgent
from .code_simplifier import CodeSimplifierAgent
from .critic import CriticAgent
from .data_agent import DataAgent

# ---- 新增 Agent（2026-04-12）----
from .database import DatabaseAgent
from .debugger import DebuggerAgent
from .designer import DesignerAgent
from .devops import DevOpsAgent
from .document import DocumentAgent
from .executor import ExecutorAgent
from .explore import ExploreAgent
from .git_master import GitMasterAgent
from .migration import MigrationAgent
from .performance import PerformanceAgent
from .planner import PlannerAgent
from .prompt_agent import PromptAgent
from .qa_tester import QATesterAgent
from .scientist import ScientistAgent
from .security import SecurityReviewerAgent
from .self_improving import LearningStore, SelfImprovingAgent
from .skill_manage import SkillManageAgent
from .test_engineer import TestEngineerAgent
from .tracer import TracerAgent
from .uml import UMLAgent
from .verifier import VerifierAgent
from .vision import VisionAgent
from .writer import WriterAgent

# 导出所有 Agent（分组严格对齐 docs/guide/agents.md）
__all__ = [
    "BaseAgent",
    "register_agent",
    "get_agent",
    "list_agents",
    # ========================
    # 构建 / 分析通道（9）
    # ========================
    "ExploreAgent",
    "AnalystAgent",
    "PlannerAgent",
    "ArchitectAgent",
    "ExecutorAgent",
    "VerifierAgent",
    "DebuggerAgent",
    "TracerAgent",
    "PerformanceAgent",
    # ========================
    # 审查通道（2）
    # ========================
    "CodeReviewerAgent",
    "SecurityReviewerAgent",
    # ========================
    # 领域通道（16）
    # ========================
    "TestEngineerAgent",
    "DesignerAgent",
    "VisionAgent",
    "DocumentAgent",
    "WriterAgent",
    "ScientistAgent",
    "GitMasterAgent",
    "CodeSimplifierAgent",
    "QATesterAgent",
    "DatabaseAgent",
    "APIAgent",
    "DevOpsAgent",
    "UMLAgent",
    "MigrationAgent",
    "AuthAgent",
    "DataAgent",
    # ========================
    # 协调通道（4）
    # ========================
    "PromptAgent",
    "SelfImprovingAgent",
    "SkillManageAgent",
    "CriticAgent",
    # Self-Improving 基础设施
    "LearningStore",
]
