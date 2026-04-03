"""
Agent 编排器 - 智能体调度和编排引擎

核心功能：
1. Agent 工作流编排
2. 任务分解和分配
3. 状态追踪和持久化
4. 并行执行支持

设计思路：
原项目通过 Skills 系统编排多个 Agent 协作。
我们实现一个轻量级的编排引擎，支持：
- 顺序执行：explore → analyst → planner → executor
- 并行执行：多个 Agent 同时工作
- 条件执行：根据前序结果决定后续步骤
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import json
import asyncio


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionMode(Enum):
    """执行模式"""
    SEQUENTIAL = "sequential"    # 顺序执行
    PARALLEL = "parallel"        # 并行执行
    CONDITIONAL = "conditional"  # 条件执行


@dataclass
class WorkflowStep:
    """工作流步骤"""
    agent_name: str
    description: str
    dependencies: List[str] = field(default_factory=list)  # 依赖的前序步骤
    condition: Optional[Callable[[Dict], bool]] = None     # 执行条件
    retry_count: int = 0
    timeout: float = 300.0  # 5分钟默认超时
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    workflow_id: str
    status: WorkflowStatus
    steps_completed: List[str]
    steps_failed: List[str]
    outputs: Dict[str, Any]  # agent_name -> output
    total_tokens: int
    total_cost: float
    execution_time: float
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# 预定义的工作流模板
WORKFLOW_TEMPLATES = {
    "build": [
        WorkflowStep("explore", "探索代码库"),
        WorkflowStep("analyst", "分析需求", dependencies=["explore"]),
        WorkflowStep("planner", "制定计划", dependencies=["analyst"]),
        WorkflowStep("architect", "设计架构", dependencies=["planner"]),
        WorkflowStep("executor", "实现代码", dependencies=["architect"]),
        WorkflowStep("verifier", "验证完成", dependencies=["executor"]),
    ],
    "review": [
        WorkflowStep("explore", "探索代码库"),
        WorkflowStep("code-reviewer", "代码审查", dependencies=["explore"]),
        WorkflowStep("security-reviewer", "安全审查", dependencies=["explore"]),
    ],
    "debug": [
        WorkflowStep("explore", "探索代码库"),
        WorkflowStep("debugger", "调试问题", dependencies=["explore"]),
        WorkflowStep("verifier", "验证修复", dependencies=["debugger"]),
    ],
    "test": [
        WorkflowStep("explore", "探索代码库"),
        WorkflowStep("test-engineer", "设计测试", dependencies=["explore"]),
        WorkflowStep("executor", "实现测试", dependencies=["test-engineer"]),
        WorkflowStep("verifier", "运行测试", dependencies=["executor"]),
    ],
}


class Orchestrator:
    """
    Agent 编排器
    
    核心方法：
    - execute_workflow(): 执行完整工作流
    - execute_step(): 执行单个步骤
    - save_state(): 保存状态
    - load_state(): 加载状态
    """
    
    def __init__(
        self,
        model_router,
        state_dir: Optional[Path] = None,
    ):
        """
        Args:
            model_router: 模型路由器
            state_dir: 状态持久化目录
        """
        self.model_router = model_router
        self.state_dir = state_dir or Path(".omc/state")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Agent 实例缓存
        self._agents: Dict[str, Any] = {}
        
        # 工作流状态
        self._active_workflows: Dict[str, WorkflowResult] = {}
    
    def register_agent(self, agent):
        """注册 Agent 实例"""
        self._agents[agent.name] = agent
    
    def get_agent(self, name: str):
        """获取 Agent 实例"""
        if name not in self._agents:
            # 动态加载
            from ..agents.base import get_agent
            
            agent_class = get_agent(name)
            if agent_class:
                agent = agent_class(self.model_router)
                self._agents[name] = agent
            else:
                raise ValueError(f"未知的 Agent: {name}")
        
        return self._agents[name]
    
    async def execute_workflow(
        self,
        workflow_name: str,
        context: Dict[str, Any],
        mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
    ) -> WorkflowResult:
        """
        执行工作流
        
        Args:
            workflow_name: 工作流名称或步骤列表
            context: 执行上下文
            mode: 执行模式
            
        Returns:
            WorkflowResult: 执行结果
        """
        import time
        import uuid
        
        workflow_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # 获取工作流模板
        if isinstance(workflow_name, str):
            steps = WORKFLOW_TEMPLATES.get(workflow_name, [])
        else:
            steps = workflow_name
        
        if not steps:
            raise ValueError(f"无效的工作流: {workflow_name}")
        
        # 初始化结果
        result = WorkflowResult(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            steps_completed=[],
            steps_failed=[],
            outputs={},
            total_tokens=0,
            total_cost=0.0,
            execution_time=0.0,
        )
        
        self._active_workflows[workflow_id] = result
        
        try:
            # 根据模式执行
            if mode == ExecutionMode.SEQUENTIAL:
                await self._execute_sequential(steps, context, result)
            elif mode == ExecutionMode.PARALLEL:
                await self._execute_parallel(steps, context, result)
            else:
                await self._execute_conditional(steps, context, result)
            
            result.status = WorkflowStatus.COMPLETED
            
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        
        finally:
            result.execution_time = time.time() - start_time
            self._save_workflow_result(result)
        
        return result
    
    async def _execute_sequential(
        self,
        steps: List[WorkflowStep],
        context: Dict[str, Any],
        result: WorkflowResult,
    ):
        """顺序执行步骤"""
        from ..agents.base import AgentContext
        
        for step in steps:
            # 检查依赖
            for dep in step.dependencies:
                if dep not in result.steps_completed:
                    raise ValueError(f"步骤 {step.agent_name} 的依赖 {dep} 未完成")
            
            try:
                # 执行步骤
                agent = self.get_agent(step.agent_name)
                
                # 构建上下文
                agent_context = AgentContext(
                    project_path=Path(context.get("project_path", ".")),
                    task_description=context.get("task", ""),
                    previous_outputs=result.outputs,
                )
                
                output = await asyncio.wait_for(
                    agent.execute(agent_context),
                    timeout=step.timeout,
                )
                
                if output.status.value == "completed":
                    result.steps_completed.append(step.agent_name)
                    result.outputs[step.agent_name] = output
                    result.total_tokens += output.usage.get("total_tokens", 0)
                else:
                    result.steps_failed.append(step.agent_name)
                    raise Exception(f"Agent {step.agent_name} 执行失败: {output.error}")
                    
            except asyncio.TimeoutError:
                result.steps_failed.append(step.agent_name)
                raise Exception(f"Agent {step.agent_name} 执行超时")
    
    async def _execute_parallel(
        self,
        steps: List[WorkflowStep],
        context: Dict[str, Any],
        result: WorkflowResult,
    ):
        """并行执行步骤"""
        # TODO: 实现并行执行
        await self._execute_sequential(steps, context, result)
    
    async def _execute_conditional(
        self,
        steps: List[WorkflowStep],
        context: Dict[str, Any],
        result: WorkflowResult,
    ):
        """条件执行步骤"""
        # TODO: 实现条件执行
        await self._execute_sequential(steps, context, result)
    
    async def execute_single_agent(
        self,
        agent_name: str,
        context: Dict[str, Any],
    ):
        """
        执行单个 Agent
        
        Args:
            agent_name: Agent 名称
            context: 执行上下文
            
        Returns:
            AgentOutput: 执行结果
        """
        from ..agents.base import AgentContext
        
        agent = self.get_agent(agent_name)
        
        agent_context = AgentContext(
            project_path=Path(context.get("project_path", ".")),
            task_description=context.get("task", ""),
            metadata=context.get("metadata", {}),
        )
        
        return await agent.execute(agent_context)
    
    def _save_workflow_result(self, result: WorkflowResult):
        """保存工作流结果"""
        result_file = self.state_dir / f"workflow_{result.workflow_id}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "workflow_id": result.workflow_id,
                "status": result.status.value,
                "steps_completed": result.steps_completed,
                "steps_failed": result.steps_failed,
                "total_tokens": result.total_tokens,
                "total_cost": result.total_cost,
                "execution_time": result.execution_time,
                "error": result.error,
                "timestamp": result.timestamp,
            }, f, ensure_ascii=False, indent=2)
    
    def load_workflow_result(self, workflow_id: str) -> Optional[WorkflowResult]:
        """加载工作流结果"""
        result_file = self.state_dir / f"workflow_{workflow_id}.json"
        
        if not result_file.exists():
            return None
        
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return WorkflowResult(
            workflow_id=data["workflow_id"],
            status=WorkflowStatus(data["status"]),
            steps_completed=data["steps_completed"],
            steps_failed=data["steps_failed"],
            outputs={},
            total_tokens=data["total_tokens"],
            total_cost=data["total_cost"],
            execution_time=data["execution_time"],
            error=data.get("error"),
            timestamp=data["timestamp"],
        )
    
    def list_active_workflows(self) -> List[str]:
        """列出活跃的工作流"""
        return list(self._active_workflows.keys())
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowResult]:
        """获取工作流状态"""
        return self._active_workflows.get(workflow_id)
