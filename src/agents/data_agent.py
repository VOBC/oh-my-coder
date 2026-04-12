"""
DataAgent - 数据处理与 ETL 智能体

职责：
1. 数据清洗与转换
2. ETL 流水线设计
3. 数据导出与导入
4. 数据验证脚本

模型层级：MEDIUM（平衡）
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
class DataAgent(BaseAgent):
    """数据处理与 ETL 智能体"""

    name = "data"
    description = "数据处理与 ETL 智能体 - 数据清洗、导入导出、流水线"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "📥"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个数据工程专家。

## 角色
你擅长数据清洗、ETL 流水线设计和数据导入导出。

## 能力
1. CSV / Excel / JSON 数据处理
2. 数据清洗（去重、填充、类型转换）
3. ETL 流水线（Pandas / Polars）
4. 数据导出（数据库 / 文件）

## 数据清洗规范
```python
import pandas as pd

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # 去重
    df = df.drop_duplicates()

    # 填充缺失值
    df["age"] = df["age"].fillna(df["age"].median())

    # 类型转换
    df["created_at"] = pd.to_datetime(df["created_at"])

    return df
```

## ETL 示例
```python
def etl_pipeline():
    # Extract
    df = pd.read_csv("raw_data.csv")

    # Transform
    df = clean_data(df)

    # Load
    df.to_sql("clean_data", engine, if_exists="replace")
```

## 输出格式
1. 数据质量报告
2. 清洗代码
3. ETL 流水线
4. 验证脚本
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行数据处理"""
        data_hint = """

请进行数据处理：
1. 分析数据质量（缺失值、重复、异常值）
2. 提供数据清洗代码
3. 设计 ETL 流水线
4. 提供数据验证脚本
"""
        prompt.append({"role": "user", "content": data_hint})

        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.SIMPLE_QA,
            messages=messages,
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "验证清洗后的数据质量",
                "建立定时 ETL 任务",
                "记录数据血缘关系",
            ],
        )
