"""
Agent 基类 - 所有智能体的基类

设计原则：
1. 每个 Agent 职责单一、明确
2. 通过 Prompt 定义角色和行为
3. 自动记录工作过程和产出
4. 支持与其他 Agent 协作

Agent 生命周期：
1. 初始化（加载配置和 Prompt）
2. 接收任务
3. 执行（调用模型、使用工具）
4. 输出结果
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Callable, Type
from pathlib import Path
import json


class AgentStatus(Enum):
    """Agent 状态"""
    IDLE = "idle"           # 空闲
    WORKING = "working"     # 工作中
    WAITING = "waiting"     # 等待输入
    COMPLETED = "completed" # 已完成
    FAILED = "failed"       # 失败


class AgentLane(Enum):
    """Agent 通道 - 对应原项目的四大通道"""
    BUILD_ANALYSIS = "build_analysis"   # 构建/分析
    REVIEW = "review"                   # 审查
    DOMAIN = "domain"                   # 领域
    COORDINATION = "coordination"       # 协调


@dataclass
class AgentContext:
    """Agent 执行上下文"""
    project_path: Path                       # 项目路径
    task_description: str                    # 任务描述
    working_directory: Optional[Path] = None # 工作目录
    relevant_files: List[Path] = field(default_factory=list)  # 相关文件
    previous_outputs: Dict[str, Any] = field(default_factory=dict)  # 前序 Agent 输出
    metadata: Dict[str, Any] = field(default_factory=dict)    # 其他元数据


@dataclass
class AgentOutput:
    """Agent 输出"""
    agent_name: str                          # Agent 名称
    status: AgentStatus                      # 执行状态
    result: Optional[str] = None             # 主要结果
    artifacts: Dict[str, Any] = field(default_factory=dict)  # 产物（文件、数据等）
    recommendations: List[str] = field(default_factory=list) # 推荐后续步骤
    next_agent: Optional[str] = None         # 推荐下一个 Agent
    usage: Dict[str, int] = field(default_factory=dict)      # Token 使用
    execution_time: float = 0.0              # 执行时间（秒）
    error: Optional[str] = None              # 错误信息
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BaseAgent(ABC):
    """
    Agent 基类
    
    核心方法：
    - execute(): 执行任务（模板方法）
    - _prepare_prompt(): 准备 Prompt
    - _run(): 实际执行逻辑（子类实现）
    - _post_process(): 后处理
    
    子类需要实现：
    - _run(): 核心执行逻辑
    - 定义 name, description, default_tier 等属性
    """
    
    # 子类必须覆盖的属性
    name: str = "base_agent"
    description: str = "基类 Agent"
    lane: AgentLane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"  # low, medium, high
    
    # 可选属性
    icon: str = "🤖"
    tools: List[str] = field(default_factory=list)  # 可用工具列表
    
    def __init__(
        self,
        model_router,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            model_router: 模型路由器
            config: Agent 特定配置
        """
        self.model_router = model_router
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self._output_history: List[AgentOutput] = []
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """返回系统提示词（定义 Agent 的角色和行为）"""
        pass
    
    def get_context_prompt(self, context: AgentContext) -> str:
        """根据上下文生成额外提示词"""
        parts = []
        
        if context.task_description:
            parts.append(f"## 当前任务\n{context.task_description}")
        
        if context.project_path:
            parts.append(f"## 项目路径\n{context.project_path}")
        
        if context.relevant_files:
            files_str = "\n".join(str(f) for f in context.relevant_files)
            parts.append(f"## 相关文件\n{files_str}")
        
        if context.previous_outputs:
            parts.append("## 前序工作成果")
            for agent_name, output in context.previous_outputs.items():
                parts.append(f"### {agent_name}\n{output}")
        
        return "\n\n".join(parts)
    
    async def execute(
        self,
        context: AgentContext,
        **kwargs
    ) -> AgentOutput:
        """
        执行任务（模板方法）
        
        流程：
        1. 更新状态
        2. 准备 Prompt
        3. 调用模型
        4. 后处理
        5. 记录输出
        """
        import time
        start_time = time.time()
        
        self.status = AgentStatus.WORKING
        
        try:
            # 准备 Prompt
            prompt = self._prepare_prompt(context)
            
            # 执行
            result = await self._run(context, prompt, **kwargs)
            
            # 后处理
            output = self._post_process(result, context)
            
            output.execution_time = time.time() - start_time
            self.status = AgentStatus.COMPLETED
            
        except Exception as e:
            output = AgentOutput(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
            )
            self.status = AgentStatus.FAILED
        
        # 记录历史
        self._output_history.append(output)
        
        return output
    
    def _prepare_prompt(self, context: AgentContext) -> List[Dict[str, str]]:
        """
        准备完整的 Prompt
        
        Returns:
            List[Dict]: 消息列表（系统 + 用户）
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        context_prompt = self.get_context_prompt(context)
        if context_prompt:
            messages.append({"role": "user", "content": context_prompt})
        
        return messages
    
    @abstractmethod
    async def _run(
        self,
        context: AgentContext,
        prompt: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        实际执行逻辑（子类实现）
        
        Args:
            context: 执行上下文
            prompt: 准备好的 Prompt
            **kwargs: 额外参数
            
        Returns:
            str: 执行结果
        """
        pass
    
    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """
        后处理（子类可覆盖）
        
        默认实现：直接包装为输出
        """
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
        )
    
    def get_last_output(self) -> Optional[AgentOutput]:
        """获取最后一次输出"""
        return self._output_history[-1] if self._output_history else None
    
    def get_output_history(self) -> List[AgentOutput]:
        """获取输出历史"""
        return self._output_history.copy()
    
    def save_output(self, output_path: Path):
        """保存输出到文件"""
        if not self._output_history:
            return
        
        last_output = self._output_history[-1]
        output_file = output_path / f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "agent": last_output.agent_name,
                "status": last_output.status.value,
                "result": last_output.result,
                "artifacts": last_output.artifacts,
                "recommendations": last_output.recommendations,
                "error": last_output.error,
                "timestamp": last_output.timestamp,
            }, f, ensure_ascii=False, indent=2)


# Agent 注册表（用于动态发现和创建）
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {}


def register_agent(agent_class: Type[BaseAgent]):
    """注册 Agent"""
    AGENT_REGISTRY[agent_class.name] = agent_class
    return agent_class


def get_agent(name: str) -> Optional[Type[BaseAgent]]:
    """获取已注册的 Agent"""
    return AGENT_REGISTRY.get(name)


def list_agents() -> List[str]:
    """列出所有已注册的 Agent"""
    return list(AGENT_REGISTRY.keys())
