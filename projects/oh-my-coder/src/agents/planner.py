"""
Planner Agent - 任务规划智能体

职责：
1. 任务分解
2. 执行计划创建
3. 任务排序
4. 依赖分析

模型层级：HIGH（深度推理，对应 opus）
"""
from typing import List, Dict, Any
from pathlib import Path
from dataclasses import dataclass

from .base import (
    BaseAgent,
    AgentContext,
    AgentOutput,
    AgentStatus,
    AgentLane,
    register_agent,
)
from ..core.router import TaskType


@dataclass
class Task:
    """任务项"""
    id: str
    description: str
    priority: str  # high, medium, low
    dependencies: List[str]
    estimated_time: str
    agent: str  # 推荐执行的 Agent


@register_agent
class PlannerAgent(BaseAgent):
    """规划 Agent - 任务分解和计划制定"""
    
    name = "planner"
    description = "规划智能体 - 任务分解和执行计划"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "high"
    icon = "📋"
    tools = ["file_read", "search"]
    
    @property
    def system_prompt(self) -> str:
        return """你是一个资深的项目规划师。

## 角色
你的职责是将复杂任务分解为可执行的小任务，并制定合理的执行计划。

## 能力
1. 任务分解 - 将大任务拆分为小任务
2. 依赖分析 - 识别任务间依赖关系
3. 优先级排序 - 确定最优执行顺序
4. 时间估算 - 评估任务耗时

## 规划原则
1. **SMART** - 具体、可衡量、可达成、相关、有时限
2. **自顶向下** - 从大到小，逐步细化
3. **依赖优先** - 先完成被依赖的任务
4. **风险前置** - 先处理高风险任务

## 输出格式

### 1. 任务概览
- 总任务数: X
- 预计总耗时: X小时
- 关键路径: ...

### 2. 任务分解

#### 阶段 1: [阶段名称]
| ID | 任务 | 优先级 | 依赖 | 耗时 | Agent |
|----|------|--------|------|------|-------|
| T1 | ... | high | - | 1h | explore |
| T2 | ... | high | T1 | 2h | analyst |

#### 阶段 2: [阶段名称]
...

### 3. 执行顺序（拓扑排序）
```
1. T1 (explore)
2. T2 (analyst) - 依赖 T1
3. T3 (architect) - 依赖 T2
...
```

### 4. 关键里程碑
- [ ] 里程碑1: ...
- [ ] 里程碑2: ...

### 5. 风险提示
- ⚠️ 风险1: ...
- ⚠️ 风险2: ...

### 6. 下一步
- 推荐从 T1 开始执行
- ...
"""
    
    async def _run(
        self,
        context: AgentContext,
        prompt: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """执行规划"""
        # 添加前序输出
        if context.previous_outputs.get("explore"):
            prompt.append({
                "role": "user",
                "content": f"## 项目探索\n{context.previous_outputs['explore'].result}"
            })
        
        if context.previous_outputs.get("analyst"):
            prompt.append({
                "role": "user",
                "content": f"## 需求分析\n{context.previous_outputs['analyst'].result}"
            })
        
        # 规划提示
        plan_hint = """

请制定执行计划：
1. 如何分解这个任务？
2. 各子任务的依赖关系是什么？
3. 最优执行顺序是什么？
4. 有哪些风险需要注意？
"""
        prompt.append({"role": "user", "content": plan_hint})
        
        # 调用模型
        from ..models.base import Message
        
        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in prompt
        ]
        
        response = await self.model_router.route_and_call(
            task_type=TaskType.PLANNING,
            messages=messages,
            complexity="high",
        )
        
        return response.content
    
    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """后处理"""
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "按计划顺序执行",
                "使用 architect 设计架构",
            ],
            next_agent="architect",
        )
