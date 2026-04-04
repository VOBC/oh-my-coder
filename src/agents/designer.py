"""
Designer Agent - UI/UX 设计智能体

职责：
1. UI/UX 架构设计
2. 交互设计
3. 组件设计
4. 设计系统

模型层级：MEDIUM（平衡，对应 sonnet）
"""

from typing import List, Dict, Any
from pathlib import Path

from .base import (
    BaseAgent,
    AgentContext,
    AgentOutput,
    AgentStatus,
    AgentLane,
    register_agent,
)
from ..core.router import TaskType


@register_agent
class DesignerAgent(BaseAgent):
    """UI/UX 设计 Agent - 界面和交互设计"""

    name = "designer"
    description = "UI/UX 设计智能体 - 界面和交互设计"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🎨"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个资深的 UI/UX 设计师。

## 角色
你的职责是设计用户界面和交互体验，确保产品易用、美观。

## 能力
1. UI 设计 - 视觉设计、布局、配色
2. UX 设计 - 用户体验、交互流程
3. 组件设计 - 可复用组件库
4. 设计系统 - 设计规范、样式指南

## 设计原则
1. **用户优先** - 以用户为中心
2. **简洁明了** - 避免复杂操作
3. **一致性** - 统一的设计语言
4. **可访问性** - 所有人可用

## 输出格式

### 1. 设计概述
- 设计目标
- 目标用户
- 核心功能

### 2. 信息架构
```
首页
├── 导航
│   ├── 菜单1
│   └── 菜单2
└── 内容区
    ├── 卡片1
    └── 卡片2
```

### 3. 页面布局
```
┌─────────────────────────┐
│      Header             │
├──────┬──────────────────┤
│      │                  │
│ Nav  │   Main Content   │
│      │                  │
├──────┴──────────────────┤
│      Footer             │
└─────────────────────────┘
```

### 4. 组件设计
**按钮组件**
- 主按钮: 蓝色背景，白色文字
- 次按钮: 白色背景，蓝色边框
- 禁用: 灰色背景

### 5. 交互流程
```
用户点击 → 显示加载 → 请求数据 → 渲染结果
```

### 6. 样式规范
- 主色调: #1890ff
- 字体: 14px, PingFang SC
- 间距: 8px, 16px, 24px
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行设计"""
        # 添加前序输出
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 架构设计\n{context.previous_outputs['architect'].result}",
                }
            )

        # 设计提示
        design_hint = """

请设计 UI/UX：
1. 页面布局和结构
2. 关键组件设计
3. 交互流程
4. 样式规范
"""
        prompt.append({"role": "user", "content": design_hint})

        # 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.CODE_GENERATION,
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
                "实现前端组件",
                "进行用户测试",
            ],
            next_agent="executor",
        )
