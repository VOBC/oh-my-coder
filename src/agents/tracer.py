"""
Tracer Agent - 因果追踪智能体

职责：
1. 证据驱动的因果追踪
2. 竞争假设分析
3. 问题根因定位
4. 调用链分析

模型层级：MEDIUM（平衡，对应 sonnet）
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
class Hypothesis:
    """假设"""

    description: str
    evidence_for: List[str]
    evidence_against: List[str]
    confidence: float  # 0-1


@register_agent
class TracerAgent(BaseAgent):
    """追踪 Agent - 因果分析和根因定位"""

    name = "tracer"
    description = "追踪智能体 - 证据驱动的因果分析"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "🔍"
    tools = ["file_read", "search", "bash"]

    @property
    def system_prompt(self) -> str:
        return """你是一个问题分析专家，擅长追踪问题的根因。

## 角色
你的职责是通过证据驱动的分析，找到问题的真正原因。

## 能力
1. 因果追踪 - 分析事件序列
2. 假设验证 - 提出并验证假设
3. 证据收集 - 从代码和日志中找证据
4. 根因定位 - 找到问题的起点

## 分析方法
1. **观察** - 看到什么现象？
2. **假设** - 可能的原因是什么？
3. **验证** - 如何验证这个假设？
4. **结论** - 根因是什么？

## 分析原则
1. **证据驱动** - 不猜测，基于事实
2. **竞争假设** - 考虑多种可能性
3. **奥卡姆剃刀** - 最简单的解释往往是对的
4. **完整链路** - 从现象到根因的完整路径

## 输出格式

### 1. 问题现象
```
错误信息
堆栈跟踪
```

### 2. 竞争假设分析

| 假设 | 支持证据 | 反对证据 | 置信度 |
|------|----------|----------|--------|
| H1: ... | ... | ... | 0.8 |
| H2: ... | ... | ... | 0.3 |

### 3. 证据链
```
现象A
  ↓ 因为
代码B
  ↓ 因为
配置C
  ↓ 因为
根因D
```

### 4. 根因分析
**根本原因**: ...

**直接原因**: ...

**促成因素**: ...

### 5. 验证步骤
```bash
# 验证步骤1
# 验证步骤2
```

### 6. 修复建议
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行因果追踪"""
        # 添加错误信息
        error_info = context.metadata.get("error")
        if error_info:
            prompt.append(
                {"role": "user", "content": f"## 问题现象\n```\n{error_info}\n```"}
            )

        # 添加相关代码
        if context.relevant_files:
            code_parts = []
            for file_path in context.relevant_files[:5]:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        code_parts.append(
                            f"### {file_path.name}\n```\n{content[:2000]}\n```"
                        )
                except:
                    pass

            if code_parts:
                prompt.append(
                    {
                        "role": "user",
                        "content": "## 相关代码\n" + "\n\n".join(code_parts),
                    }
                )

        # 追踪提示
        trace_hint = """

请分析问题根因：
1. 可能的原因有哪些？（竞争假设）
2. 每个假设有什么支持/反对证据？
3. 最可能的根因是什么？
4. 如何验证你的结论？
"""
        prompt.append({"role": "user", "content": trace_hint})

        # 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.DEBUGGING,
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
                "根据分析结果修复问题",
                "添加测试防止复发",
            ],
            next_agent="debugger",
        )
