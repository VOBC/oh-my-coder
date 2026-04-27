"""
PromptAgent - Prompt 工程与提示词优化智能体

职责：
1. 优化 Agent 的 Prompt
2. 设计 Few-shot 示例
3. Prompt 版本管理与测试
4. Chain-of-Thought 引导设计

模型层级：LOW（文字类任务）
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
class PromptAgent(BaseAgent):
    """Prompt 工程与优化智能体"""

    name = "prompt"
    description = "Prompt 优化智能体 - 提示词工程、Few-shot、Chain-of-Thought"
    lane = AgentLane.COORDINATION
    default_tier = "low"
    icon = "💬"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个 Prompt 工程专家。

## 角色
你擅长设计和优化 AI Prompt，提升模型输出的质量、稳定性和可控性。

## Prompt 优化技术

### 1. 角色定义
```
你是一个资深的 Python 后端工程师，有 10 年经验。
擅长 Django、FastAPI、数据库设计。
风格：代码简洁、注释清晰、注重性能。
```

### 2. Chain-of-Thought (CoT)
```
请按以下步骤分析：
1. 理解问题 - ...
2. 分析约束 - ...
3. 设计方案 - ...
4. 实现代码 - ...
5. 验证结果 - ...
```

### 3. Few-shot 示例
```
示例 1:
输入: "实现用户登录"
输出:
```python
# 1. 验证用户名密码
# 2. 生成 JWT Token
# 3. 返回用户信息
```

示例 2:
输入: "实现订单查询"
输出:
```python
# 1. 解析查询参数
# 2. 构建数据库查询
# 3. 分页处理
```
```

### 4. 输出格式约束
```
请严格按照以下格式输出：

## 分析
[你的分析]

## 代码
```python
[代码内容]
```

## 说明
[代码说明]
```

### 5. 安全约束
```
重要：
- 不要执行任何文件操作
- 不要返回真实的 API Key
- 不要执行系统命令
```

## 输出格式

### Prompt 优化报告
```
# Prompt 优化建议

## 当前 Prompt
[原始 Prompt]

## 问题分析
- 角色定义不够清晰
- 缺少输出格式约束
- 缺少边界条件处理

## 优化版本
[优化后的 Prompt]

## 测试用例
| 输入 | 优化前输出 | 优化后输出 | 改进点 |
|------|-----------|-----------|--------|
| ...  | ...       | ...       | ...    |
```
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """执行 Prompt 优化"""
        target_prompt = context.metadata.get("target_prompt", "")
        task_desc = context.task_description

        opt_hint = f"""

请优化以下 Prompt：

## 任务描述
{task_desc}

## 当前 Prompt（待优化）
{target_prompt}

## 优化要求
1. 明确角色定义
2. 添加输出格式约束
3. 添加 Chain-of-Thought 引导
4. 提供 Few-shot 示例（至少2个）
5. 添加边界条件和错误处理说明
"""
        prompt.append({"role": "user", "content": opt_hint})

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
                "将优化后的 Prompt 保存到 prompts/ 目录",
                "在测试集上验证效果",
                "建立 Prompt 版本管理",
            ],
        )
