"""
Critic Agent - 批评家智能体

职责：
1. 计划和设计的缺口分析
2. 多角度审查
3. 发现潜在问题
4. 提出改进建议

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
class CriticAgent(BaseAgent):
    """批评家 Agent - 多角度审查和缺口分析"""

    name = "critic"
    description = "批评家智能体 - 计划审查和缺口分析"
    lane = AgentLane.COORDINATION
    default_tier = "high"
    icon = "🎯"
    tools = ["file_read", "search"]

    @property
    def system_prompt(self) -> str:
        return """你是一个犀利但建设性的批评家。

## 角色
你的职责是从多个角度审查计划和设计，发现缺口和潜在问题。

## 审查角度
1. **完整性** - 是否有遗漏？
2. **可行性** - 是否可实现？
3. **一致性** - 是否有矛盾？
4. **可维护性** - 未来是否好维护？
5. **可扩展性** - 是否容易扩展？
6. **性能** - 是否有性能问题？
7. **安全** - 是否有安全隐患？

## 批评原则
1. **建设性** - 不仅指出问题，还要给出建议
2. **具体** - 指出具体位置和原因
3. **优先级** - 区分严重问题和次要问题
4. **可操作** - 建议要具体可执行

## 输出格式

### 1. 总体评价
⭐⭐⭐☆☆ (3/5)

一句话总结

### 2. 关键问题 (CRITICAL)
- 🔴 **[完整性]** 缺少关键功能或边界条件处理
  - 影响: 可能导致计划/设计在实际执行时出现遗漏
  - 建议: 补充缺失场景的规划和处理逻辑

### 3. 潜在问题 (WARNING)
- 🟡 **[性能]** 某些实现路径在大规模场景下可能成为瓶颈
  - 原因: 未考虑复杂度增长的影响
  - 建议: 提前设计缓存/异步/分片等优化方案

### 4. 改进建议 (IMPROVEMENT)
- 🟢 **[可维护性]** 建议重构重复或耦合的代码块
  - 建议: 抽象公共逻辑为独立函数/模块，降低圈复杂度

### 5. 缺口分析
| 维度 | 状态 | 说明 |
|------|------|------|
| 完整性 | ⚠️ | 缺少错误处理 |
| 可行性 | ✅ | 技术方案可行 |
| 性能 | ⚠️ | 需要优化 |
| 安全 | ✅ | 无明显问题 |

### 6. 推荐改进顺序
根据问题的严重程度和依赖关系，给出具体的修复优先级排序。

### 7. 下一步建议
- 根据以上审查意见，优先处理 CRITICAL 级别问题
- 确认是否需要调整整体方案或仅需补充细节
- 在实施改进后，重新运行审查确认问题已解决
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """执行批评审查"""
        # 收集前序输出
        context_parts = []

        for agent_name in ["planner", "architect"]:
            if context.previous_outputs.get(agent_name):
                context_parts.append(
                    f"## {agent_name.title()}\n{context.previous_outputs[agent_name].result}"
                )

        if context_parts:
            prompt.append({"role": "user", "content": "\n\n".join(context_parts)})

        # 批评提示
        critic_hint = """

请从多个角度审查：
1. 是否有遗漏的关键点？
2. 是否有矛盾或不一致的地方？
3. 是否有潜在的风险？
4. 是否有更好的实现方式？
"""
        prompt.append({"role": "user", "content": critic_hint})

        # 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.call_model(
            task_type=TaskType.ARCHITECTURE,
            messages=messages,
            complexity="high",
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """后处理"""
        return AgentOutput(agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "根据批评意见调整计划",
                "重新审查架构设计",
            ],
        )
