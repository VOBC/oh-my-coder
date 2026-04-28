"""
UML Agent - 架构图与可视化智能体

职责：
1. 架构图生成（Mermaid / PlantUML）
2. 类图、时序图、用例图
3. 流程图与数据流图
4. 架构决策记录（ADR）

模型层级：LOW（快速）
"""

from ..core.router import TaskType
from .base import (
    AgentContext,
    AgentLane,
    AgentOutput,
    AgentStatus,
    BaseAgent,
    register_agent,
)


@register_agent
class UMLAgent(BaseAgent):
    """架构图与可视化智能体"""

    name = "uml"
    description = "架构图与 UML 可视化智能体 - 类图、时序图、流程图"
    lane = AgentLane.DOMAIN
    default_tier = "low"
    icon = "📊"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个专业的软件架构可视化专家。

## 角色
你擅长用 Mermaid/PlantUML 语法生成清晰的架构图和 UML 图。

## 支持的图表类型

### 1. Mermaid 类图
```mermaid
classDiagram
    class User {
        +int id
        +str name
        +str email
        +create()
        +update()
    }
    class Order {
        +int id
        +float total
        +create()
    }
    User "1" o-- "N" Order : places
```

### 2. Mermaid 时序图
```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    participant DB as Database

    C->>S: POST /api/orders
    S->>DB: INSERT order
    DB-->>S: order_id
    S-->>C: 201 Created
```

### 3. Mermaid 架构图
```mermaid
graph LR
    subgraph Frontend
        A[Web App]
    end
    subgraph Backend
        B[API Server]
        C[Worker]
    end
    subgraph Storage
        D[(Database)]
        E[(Cache)]
    end
    A --> B
    B --> D
    B --> E
    C --> D
```

### 4. 流程图
```mermaid
flowchart TD
    A[开始] --> B{条件判断}
    B -->|是| C[处理A]
    B -->|否| D[处理B]
    C --> E[结束]
    D --> E
```

## 输出格式
1. Mermaid 语法代码块
2. 对应的 SVG/PNG 渲染说明
3. 在 Markdown 中的嵌入方式
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """执行架构图生成"""
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 架构设计\n{context.previous_outputs['architect'].result}",
                }
            )
        if context.previous_outputs.get("explore"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 代码结构\n{context.previous_outputs['explore'].result[:2000]}",
                }
            )

        uml_hint = """

请生成架构可视化图表：
1. 根据架构设计生成 Mermaid 类图
2. 关键交互流程生成时序图
3. 业务逻辑生成流程图
4. 系统架构生成部署/架构图
5. 全部使用 Mermaid 语法

请提供完整的 Mermaid 代码，可直接在 GitHub/GitLab/Notion 中渲染。
"""
        prompt.append({"role": "user", "content": uml_hint})

        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.SIMPLE_QA,
            messages=messages,
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """后处理"""
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "将图表保存到 docs/diagrams/ 目录",
                "在 README.md 中嵌入图表",
                "使用 Mermaid Preview 插件预览",
            ],
            next_agent="writer",
        )
