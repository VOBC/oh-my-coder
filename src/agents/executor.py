"""
Executor Agent - 代码实现智能体

职责：
1. 代码实现
2. 重构
3. Bug 修复
4. 代码优化

模型层级：MEDIUM（平衡性能和成本，对应 sonnet）

工作流程：
1. 理解任务
2. 分析现有代码
3. 实现功能
4. 自我测试
5. 输出代码
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
class ExecutorAgent(BaseAgent):
    """
    执行者 Agent

    特点：
    - 使用 MEDIUM tier 模型
    - 代码实现为主
    - 支持 Python、JavaScript、Go 等多语言
    """

    name = "executor"
    description = "执行者智能体 - 代码实现和重构"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "💻"
    tools = ["file_read", "file_write", "bash", "test"]

    @property
    def system_prompt(self) -> str:
        return """你是一个资深的软件工程师。

## 角色
你的职责是实现代码，确保功能正确、代码质量高。

## 能力
1. 代码实现 - 根据设计编写代码
2. 重构 - 改善代码结构
3. 调试 - 定位和修复 Bug
4. 测试 - 编写单元测试

## 工作原则
1. **可读性优先** - 代码要让人看懂
2. **测试驱动** - 先写测试，再写实现
3. **渐进式** - 小步提交，频繁验证
4. **最佳实践** - 遵循语言惯例和设计模式

## 编码规范
- Python: PEP 8 + 类型注解
- JavaScript/TypeScript: ESLint + Prettier
- Go: gofmt + Effective Go

## 输出格式

### 实现方案
简要说明实现思路

### 代码变更
```language
// 文件路径: path/to/file.ext
// 变更说明: ...

代码内容
```

### 测试用例
```language
测试代码
```

### 注意事项
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """
        执行代码实现
        """
        # 添加前序输出
        context_parts = []

        if context.previous_outputs.get("architect"):
            context_parts.append(
                f"## 架构设计\n{context.previous_outputs['architect'].result}"
            )

        if context_parts:
            prompt.append({"role": "user", "content": "\n\n".join(context_parts)})

        # 读取相关文件
        if context.relevant_files:
            files_content = []
            for file_path in context.relevant_files[:5]:  # 最多 5 个文件
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        files_content.append(
                            f"### {file_path.name}\n```\n{content[:2000]}\n```"
                        )
                except:
                    pass

            if files_content:
                prompt.append(
                    {
                        "role": "user",
                        "content": "## 现有代码\n" + "\n\n".join(files_content),
                    }
                )

        # 实现提示
        impl_hint = """

请实现所需功能。注意：
1. 遵循架构设计
2. 保持代码简洁
3. 添加必要的注释
4. 编写测试用例
"""
        prompt.append({"role": "user", "content": impl_hint})

        # 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.CODE_GENERATION,
            messages=messages,
            complexity="medium",
        )

        return response.content

    def _post_process(
        self,
        result: str,
        context: AgentContext,
    ) -> AgentOutput:
        """后处理 - 提取代码"""
        # TODO: 从结果中提取代码并保存到文件

        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "使用 verifier Agent 验证实现",
                "使用 code-reviewer Agent 审查代码",
            ],
            next_agent="verifier",
        )
