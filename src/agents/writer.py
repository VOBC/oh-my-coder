"""
Writer Agent - 文档编写智能体

职责：
1. 技术文档编写
2. API 文档生成
3. README 编写
4. 迁移文档

模型层级：LOW（快速，对应 haiku）
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
class WriterAgent(BaseAgent):
    """文档编写 Agent - 技术文档和 API 文档"""

    name = "writer"
    description = "文档编写智能体 - 技术文档和 API 文档生成"
    lane = AgentLane.DOMAIN
    default_tier = "low"
    icon = "📝"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个专业的技术文档撰写者。

## 角色
你的职责是编写清晰、准确、易读的技术文档。

## 能力
1. API 文档 - 接口说明、参数、示例
2. 用户文档 - 使用指南、教程
3. 开发文档 - 架构说明、贡献指南
4. 迁移文档 - 版本升级、变更说明

## 文档原则
1. **清晰** - 简单易懂，避免歧义
2. **准确** - 信息正确，及时更新
3. **完整** - 覆盖所有必要内容
4. **结构化** - 良好的组织和导航

## 输出格式

### API 文档模板

````markdown
# API 名称

## 描述
简要描述 API 功能

## 端点
`GET /api/resource`

## 参数
| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| id | string | 是 | 资源ID |

## 请求示例
```json
{
  "key": "value"
}
```

## 响应示例
```json
{
  "code": 200,
  "data": {}
}
```

## 错误码
| 错误码 | 描述 |
|--------|------|
| 400 | 参数错误 |

## 注意事项
- ...
````

### README 模板

````markdown
# 项目名称

简短描述

## 特性
- 特性1
- 特性2

## 快速开始

### 安装
```bash
npm install xxx
```

### 使用
```javascript
const x = require('xxx')
```

## API 文档
[链接](docs/api.md)

## 贡献指南
[链接](CONTRIBUTING.md)

## License
MIT
````
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行文档编写"""
        doc_type = context.metadata.get("doc_type", "readme")

        # 添加前序输出
        if context.previous_outputs.get("executor"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 实现代码\n{context.previous_outputs['executor'].result}",
                }
            )

        # 读取现有文档
        readme = context.project_path / "README.md"
        if readme.exists():
            with open(readme, "r", encoding="utf-8") as f:
                prompt.append(
                    {"role": "user", "content": f"## 现有 README\n{f.read()[:2000]}"}
                )

        # 文档提示
        doc_hint = f"""

请为项目编写{doc_type}文档：
1. 项目简介
2. 安装和使用方法
3. API 文档
4. 示例代码
5. 注意事项
"""
        prompt.append({"role": "user", "content": doc_hint})

        # 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.SIMPLE_QA,
            messages=messages,
            complexity="low",
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """后处理"""
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "将文档保存到文件",
                "定期更新文档",
            ],
        )
