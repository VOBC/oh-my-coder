"""
Debugger Agent - 调试智能体

职责：
1. 根因分析
2. 构建错误解决
3. 运行时错误修复
4. 日志分析

模型层级：MEDIUM（平衡，对应 sonnet）
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
class DebuggerAgent(BaseAgent):
    """调试 Agent - 定位和修复 Bug"""

    name = "debugger"
    description = "调试智能体 - 根因分析和错误修复"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "🐛"
    tools = ["bash", "file_read", "search", "test"]

    @property
    def system_prompt(self) -> str:
        return """你是一个经验丰富的调试专家。

## 角色
你的职责是快速定位问题根因并提供修复方案。

## 调试方法
1. **复现问题** - 明确错误现象
2. **收集信息** - 错误日志、堆栈跟踪
3. **定位根因** - 分析代码逻辑
4. **验证修复** - 确保问题解决

## 调试原则
1. **证据驱动** - 基于事实而非猜测
2. **最小修改** - 只改必要的部分
3. **验证充分** - 确保修复有效
4. **防止复发** - 添加测试用例

## 输出格式

### 1. 问题分析
**错误现象**:
```
错误信息
```

**根因分析**:
1. ...
2. ...
3. ...

### 2. 定位问题
- 文件: `path/to/file.py`
- 函数: `function_name`
- 行号: XX

### 3. 修复方案
```python
# 修复前
问题代码

# 修复后
修复后代码
```

### 4. 验证步骤
1. 运行测试: `pytest tests/test_xxx.py`
2. 检查日志: ...

### 5. 预防措施
- 添加单元测试
- 增加错误处理
- 改进日志记录
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """执行调试"""
        # 添加错误信息
        error_info = context.metadata.get("error")
        if error_info:
            prompt.append(
                {"role": "user", "content": f"## 错误信息\n```\n{error_info}\n```"}
            )

        # 读取相关代码
        if context.relevant_files:
            code_parts = []
            for file_path in context.relevant_files[:5]:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        code_parts.append(
                            f"### {file_path.name}\n```\n{content[:3000]}\n```"
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

        # 调试提示
        debug_hint = """

请分析问题并提供修复方案：
1. 根因是什么？
2. 如何修复？
3. 如何验证修复有效？
4. 如何防止再次发生？
"""
        prompt.append({"role": "user", "content": debug_hint})

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
                "应用修复方案",
                "运行测试验证",
            ],
            next_agent="verifier",
        )
