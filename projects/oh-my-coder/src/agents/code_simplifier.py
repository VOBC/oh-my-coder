"""
Code Simplifier Agent - 代码简化智能体

职责：
1. 代码清晰度改进
2. 复杂度降低
3. 可维护性提升
4. 死代码清理

模型层级：HIGH（深度推理，对应 opus）
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
class CodeSimplifierAgent(BaseAgent):
    """代码简化 Agent - 提高代码质量和可读性"""

    name = "code-simplifier"
    description = "代码简化智能体 - 提高代码清晰度和可维护性"
    lane = AgentLane.DOMAIN
    default_tier = "high"
    icon = "🧹"
    tools = ["file_read", "file_write", "bash"]

    @property
    def system_prompt(self) -> str:
        return """你是一个代码重构专家，专注于简化代码。

## 角色
你的职责是让代码更清晰、更易维护，而不改变其行为。

## 能力
1. 复杂度降低 - 拆分长函数、减少嵌套
2. 命名改进 - 更有意义的变量名和函数名
3. 重复消除 - 提取公共逻辑
4. 死代码清理 - 移除未使用的代码

## 简化原则
1. **单一职责** - 每个函数只做一件事
2. **减少嵌套** - 提前返回，减少 if-else
3. **提取函数** - 复杂逻辑拆分为小函数
4. **有意义的命名** - 代码即文档

## 代码异味检测
- 长函数 (>50行)
- 深嵌套 (>3层)
- 重复代码
- 魔法数字
- 过长参数列表 (>4个)
- 注释过多

## 输出格式

### 1. 代码质量评估
| 指标 | 原始 | 简化后 |
|------|------|--------|
| 行数 | X | X |
| 圈复杂度 | X | X |
| 函数数 | X | X |

### 2. 发现的问题
- 🔴 **长函数**: `process_data()` 有 120 行
- 🟡 **深嵌套**: 第 45-80 行有 4 层嵌套
- 🟢 **可提取**: 第 50-60 行可提取为独立函数

### 3. 简化建议

**原始代码**:
```python
# 问题代码
```

**简化后**:
```python
# 改进代码
```

**改进说明**:
- ...

### 4. 进一步优化建议
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行代码简化分析"""
        # 读取要分析的代码
        if context.relevant_files:
            code_parts = []
            for file_path in context.relevant_files[:5]:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        lines = len(content.split("\n"))
                        code_parts.append(
                            f"### {file_path.name} ({lines} 行)\n```\n{content}\n```"
                        )
                except:
                    pass

            if code_parts:
                prompt.append(
                    {
                        "role": "user",
                        "content": "## 待分析代码\n" + "\n\n".join(code_parts),
                    }
                )

        # 简化提示
        simplify_hint = """

请分析代码质量并提供简化建议：
1. 哪些地方过于复杂？
2. 如何改进可读性？
3. 是否有重复代码？
4. 是否有死代码？
"""
        prompt.append({"role": "user", "content": simplify_hint})

        # 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.CODE_REVIEW,
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
                "应用简化建议",
                "运行测试验证",
            ],
        )
