"""
Architect Agent - 系统架构设计智能体

职责：
1. 系统架构设计
2. 技术选型和权衡分析
3. 接口定义
4. 架构决策记录（ADR）

模型层级：HIGH（深度推理，对应 opus）

工作流程：
1. 分析需求和约束
2. 设计整体架构
3. 技术选型
4. 定义接口和数据流
5. 输出架构文档
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
class ArchitectureDecision:
    """架构决策"""
    title: str
    status: str  # proposed, accepted, deprecated
    context: str
    decision: str
    consequences: str


@register_agent
class ArchitectAgent(BaseAgent):
    """
    架构师 Agent
    
    特点：
    - 使用 HIGH tier 模型
    - 系统性思维
    - 权衡分析
    - 输出 ADR
    """
    
    name = "architect"
    description = "架构师智能体 - 系统架构设计和技术选型"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "high"
    icon = "🏗️"
    tools = ["file_read", "file_write", "diagram"]
    
    @property
    def system_prompt(self) -> str:
        return """你是一个资深软件架构师。

## 角色
你的职责是设计系统架构，进行技术选型，并记录架构决策。

## 能力
1. 架构设计 - 分层、微服务、事件驱动等
2. 技术选型 - 语言、框架、数据库、中间件
3. 权衡分析 - CAP、一致性、性能、成本
4. 接口定义 - API 设计、数据模型、契约

## 工作原则
1. **KISS** - 保持简单，避免过度设计
2. **YAGNI** - 不要提前设计不需要的功能
3. **权衡透明** - 明确每个选择的利弊
4. **可演进** - 架构要能适应变化

## 输出格式

### 1. 架构概览
- 整体架构风格（分层/微服务/单体）
- 核心组件
- 数据流图（文字描述）

### 2. 技术栈
| 层级 | 技术 | 理由 |
|------|------|------|
| 前端 | ... | ... |
| 后端 | ... | ... |
| 数据库 | ... | ... |

### 3. 核心模块
```
project/
├── module1/     # 描述
├── module2/     # 描述
└── module3/     # 描述
```

### 4. 接口设计
#### API 端点
- `GET /api/resource` - 描述
- `POST /api/resource` - 描述

#### 数据模型
```json
{
  "field": "type",
  "description": "说明"
}
```

### 5. 架构决策记录（ADR）

#### ADR-001: [决策标题]
- **状态**: proposed / accepted
- **背景**: ...
- **决策**: ...
- **影响**: ...

### 6. 风险和缓解
- ⚠️ 风险1 → 缓解措施
- ⚠️ 风险2 → 缓解措施

### 7. 下一步
- ...
"""
    
    async def _run(
        self,
        context: AgentContext,
        prompt: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        执行架构设计
        """
        # 添加前序输出
        context_parts = []
        
        if context.previous_outputs.get("explore"):
            context_parts.append(f"## 项目探索\n{context.previous_outputs['explore'].result}")
        
        if context.previous_outputs.get("analyst"):
            context_parts.append(f"## 需求分析\n{context.previous_outputs['analyst'].result}")
        
        if context_parts:
            prompt.append({
                "role": "user",
                "content": "\n\n".join(context_parts)
            })
        
        # 架构设计提示
        design_hint = """

请基于以上信息，设计系统架构。重点关注：
1. 架构风格是否适合项目规模？
2. 技术选型是否合理？
3. 是否有过度设计？
4. 如何保证可扩展性？
"""
        prompt.append({"role": "user", "content": design_hint})
        
        # 调用模型
        from ..models.base import Message
        
        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in prompt
        ]
        
        response = await self.model_router.route_and_call(
            task_type=TaskType.ARCHITECTURE,
            messages=messages,
            complexity="high",
        )
        
        return response.content
    
    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """后处理"""
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "使用 executor Agent 开始实现",
                "使用 critic Agent 审查架构设计",
            ],
            next_agent="executor",
        )
