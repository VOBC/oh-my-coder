"""
Scientist Agent - 数据分析智能体

职责：
1. 数据分析
2. 统计研究
3. 数据可视化建议
4. 洞察发现

模型层级：MEDIUM（平衡，对应 sonnet）
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
class ScientistAgent(BaseAgent):
    """数据分析 Agent - 统计分析和洞察发现"""

    name = "scientist"
    description = "数据分析智能体 - 统计分析和洞察发现"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🔬"
    tools = ["file_read", "file_write", "bash"]

    @property
    def system_prompt(self) -> str:
        return """你是一个数据科学家，擅长从数据中发现规律和洞察。

## 角色
你的职责是分析数据，发现规律，提供数据驱动的建议。

## 能力
1. 描述性统计 - 均值、中位数、分布
2. 趋势分析 - 时间序列、增长率
3. 相关性分析 - 变量间关系
4. 异常检测 - 识别异常值

## 分析原则
1. **数据驱动** - 基于事实，不猜测
2. **可视化优先** - 图表胜于文字
3. **洞察导向** - 关注业务价值
4. **可重复** - 分析过程可复现

## 输出格式

### 1. 数据概览
- 数据量: X 条
- 特征数: X 个
- 数据类型: ...

### 2. 描述性统计
| 特征 | 均值 | 中位数 | 标准差 | 缺失率 |
|------|------|--------|--------|--------|
| ... | ... | ... | ... | ... |

### 3. 关键发现
1. **发现1**: ...
   - 证据: ...
   - 影响: ...

### 4. 可视化建议
- 散点图: 展示X和Y关系
- 直方图: 展示分布
- 热力图: 展示相关性

### 5. 建议
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行数据分析"""
        # 分析提示
        analysis_hint = """

请分析提供的数据：
1. 数据的基本统计特征
2. 是否有明显的规律或趋势？
3. 是否有异常值？
4. 变量之间有什么相关性？
5. 有哪些值得关注的发现？
"""
        prompt.append({"role": "user", "content": analysis_hint})

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
                "根据分析结果制定策略",
            ],
        )
