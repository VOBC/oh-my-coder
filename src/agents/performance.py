"""
Performance Agent - 性能分析与优化智能体

职责：
1. 性能瓶颈定位与分析
2. 数据库查询优化
3. 缓存策略设计
4. 并发与异步优化建议

模型层级：HIGH（分析类任务）
"""

from typing import Dict, List

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
class PerformanceAgent(BaseAgent):
    """性能分析与优化智能体"""

    name = "performance"
    description = "性能分析与优化智能体 - 瓶颈定位、查询优化、缓存设计"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "high"
    icon = "⚡"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个性能优化专家。

## 角色
你擅长定位性能瓶颈，提供可量化的优化方案。

## 优化领域

### 1. 数据库
- 慢查询分析
- 索引优化（添加/删除/复合索引）
- 查询重写
- 连接池配置

### 2. 缓存
- 缓存策略（Read-Through / Write-Through / Write-Behind）
- 缓存失效策略
- 多级缓存设计

### 3. 并发
- 异步 I/O 改造
- 连接池配置
- 批量操作优化

### 4. 算法
- 时间复杂度优化
- 空间换时间
- 数据结构选型

## 输出格式

### 性能报告
```
# 性能分析报告

## 问题 1：慢查询
- 位置：src/queries.py:42
- 查询：SELECT * FROM orders WHERE user_id = ?
- 执行时间：1200ms
- 原因：全表扫描，缺少索引
- 建议：添加 idx_user_id(user_id)
- 预期收益：10ms

## 问题 2：N+1 查询
- 位置：src/api.py:88
- 问题：循环内查询用户信息
- 建议：使用 JOIN 或批量查询
- 预期收益：500ms → 50ms
```

### 优化代码
```python
# Before
for order in orders:
    user = db.query(User, order.user_id)  # N+1

# After
user_ids = {o.user_id for o in orders}
users = db.query(User).filter(User.id.in_(user_ids)).all()
user_map = {u.id: u for u in users}
```
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行性能分析"""
        if context.previous_outputs.get("explore"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 代码结构\n{context.previous_outputs['explore'].result[:3000]}",
                }
            )

        perf_hint = """

请进行性能分析与优化：
1. 扫描代码中的性能问题（N+1 查询、循环内查询、全表扫描）
2. 分析数据库查询效率
3. 识别同步阻塞和并发瓶颈
4. 提供优化前后的代码对比
5. 给出量化预期收益（执行时间、内存）

请优先分析最影响性能的关键路径。
"""
        prompt.append({"role": "user", "content": perf_hint})

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
                "使用 APM 工具验证优化效果",
                "添加性能监控指标",
                "建立性能回归测试",
            ],
            next_agent="executor",
        )
