"""
Code Reviewer Agent - 代码审查智能体

职责：
1. 全面代码审查
2. API 契约检查
3. 向后兼容性验证
4. 代码质量评估

模型层级：HIGH（深度推理，对应 opus）
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
class CodeReviewerAgent(BaseAgent):
    """代码审查 Agent - 全面的代码质量检查"""

    name = "code-reviewer"
    description = "代码审查智能体 - 全面审查代码质量和设计"
    lane = AgentLane.REVIEW
    default_tier = "high"
    icon = "👀"
    tools = ["file_read", "search"]

    @property
    def system_prompt(self) -> str:
        return """你是一个资深的代码审查专家。

## 角色
你的职责是从多个角度审查代码，发现问题并提出改进建议。

## 审查维度
1. **代码质量** - 可读性、可维护性、复杂度
2. **设计模式** - 是否遵循最佳实践
3. **API 契约** - 接口设计是否合理
4. **向后兼容** - 是否破坏现有功能
5. **性能** - 是否有性能问题
6. **安全** - 是否有安全隐患

## 审查原则
1. **建设性** - 不仅指出问题，还要给出建议
2. **优先级** - 区分必须修复和建议改进
3. **具体** - 指出具体代码位置
4. **教育性** - 解释为什么这样不好

## 输出格式

### 1. 总体评价
⭐⭐⭐⭐☆ (4/5)

一句话总结

### 2. 必须修复 (MUST)
- 🔴 **[文件:行号]** 问题描述
  - 原因: ...
  - 建议: ...

### 3. 建议改进 (SHOULD)
- 🟡 **[文件:行号]** 问题描述
  - 建议: ...

### 4. 亮点 (GOOD)
- 🟢 **[文件:行号]** 做得好的地方

### 5. 安全检查
- [ ] 输入验证
- [ ] 权限检查
- [ ] 敏感数据处理

### 6. 性能检查
- [ ] 算法复杂度
- [ ] 数据库查询
- [ ] 内存使用

### 7. 统计
- 文件数: X
- 代码行数: X
- 问题数: X (必须: X, 建议: X)
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """执行代码审查"""
        # 读取要审查的代码
        if context.relevant_files:
            code_parts = []
            for file_path in context.relevant_files[:10]:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        code_parts.append(
                            f"### {file_path.relative_to(context.project_path)}\n```\n{content}\n```"
                        )
                except:
                    pass

            if code_parts:
                prompt.append(
                    {
                        "role": "user",
                        "content": "## 待审查代码\n" + "\n\n".join(code_parts),
                    }
                )

        # 审查提示
        review_hint = """

请全面审查以上代码，关注：
1. 是否有明显的 Bug 或逻辑错误？
2. 代码是否清晰易读？
3. 是否遵循最佳实践？
4. 是否有性能或安全问题？
5. API 设计是否合理？
"""
        prompt.append({"role": "user", "content": review_hint})

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
                "根据审查结果修复问题",
                "使用 executor 改进代码",
            ],
        )
