"""
Document Agent - 长篇技术文档撰写智能体

职责：
1. 长篇技术文档编写
2. 结构化文档模板
3. API 参考文档
4. 架构文档 / 设计文档

模型层级：LOW（快速，对应 haiku），但长文档用 MEDIUM 路由
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
class DocumentAgent(BaseAgent):
    """长篇文档 Agent - 结构化技术文档（比 WriterAgent 更专注长文档）"""

    name = "document"
    description = "长篇技术文档智能体 - 结构化文档、API 参考、架构说明"
    lane = AgentLane.DOMAIN
    default_tier = "low"
    icon = "📄"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个专业的技术文档架构师。

## 角色
你擅长编写结构清晰、层次分明的长篇技术文档，包括架构文档、设计文档、API 参考、用户手册等。

## 与 WriterAgent 的区别
- WriterAgent：快速文档、README、单页说明
- DocumentAgent：**长篇结构化文档**、多级章节、表格、交叉引用

## 文档类型

### 1. 架构文档
```
# 项目架构文档

## 1. 概述
## 2. 系统架构
### 2.1 整体架构
### 2.2 核心模块
## 3. 数据流
## 4. 部署架构
## 5. 扩展性设计
```

### 2. API 参考文档
```
# API 参考

## 认证
## 错误码
## 端点列表
### GET /users
### POST /users
```

### 3. 技术规范文档
```
# 开发规范

## 代码风格
## Git 规范
## API 设计规范
## 数据库规范
```

### 4. 用户手册
```
# 用户手册

## 快速开始
## 功能说明
## 配置参考
## 常见问题
```

## 文档结构原则

### 层级结构
```
# H1 - 文档标题（一个文档一个 H1）
## H2 - 主要章节
### H3 - 子章节
#### H4 - 小节（谨慎使用）
```

### 表格使用
- 参数说明用表格
- 对比类信息用表格
- 不要滥用表格

### 代码块
- 每段代码前说明语言
- 关键代码加行号注释
- 长代码分步骤说明

## 输出格式规范

````markdown
# 文档标题

> 文档简介：简要说明这份文档的内容、目标读者、前置条件。

## 1. 概述

### 1.1 背景
### 1.2 目标
### 1.3 范围

## 2. 核心内容

### 2.1 第一部分
说明...

#### 2.1.1 子主题
代码示例：
```python
def example():
    pass
```

### 2.2 第二部分

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|--------|------|
| name | string | 是 | - | 名称 |

## 3. 配置参考

```yaml
# config.yaml
key: value
```

## 4. 常见问题

### Q1: xxx？
A: xxx

## 5. 参考资料
- [链接1](url)
- [链接2](url)
````

## 注意事项
- 长文档要有目录导航
- 每个章节前有简短导语
- 避免长段落，多用列表和表格
- 代码示例要可直接运行
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行长篇文档编写"""
        doc_type = context.metadata.get("doc_type", "technical")
        doc_title = context.metadata.get("title", "技术文档")

        # 添加前序输出作为上下文
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "system",
                    "content": (
                        f"## 架构设计参考\n"
                        f"{context.previous_outputs['architect'].result[:3000]}"
                    ),
                }
            )

        if context.previous_outputs.get("writer"):
            prompt.append(
                {
                    "role": "system",
                    "content": (
                        f"## 现有文档参考\n"
                        f"{context.previous_outputs['writer'].result[:2000]}"
                    ),
                }
            )

        # 读取项目中已有的相关文档
        if context.project_path and context.project_path.exists():
            docs = []
            for pattern in ["*.md", "docs/*.md", "doc/*.md"]:
                docs.extend(context.project_path.glob(pattern))
            for doc in docs[:3]:
                try:
                    content = doc.read_text(encoding="utf-8")
                    if len(content) < 5000:
                        prompt.append({
                            "role": "system",
                            "content": f"## 已有文档: {doc.name}\n```\n{content}\n```",
                        })
                except Exception:
                    pass

        # 文档编写提示
        doc_hint = f"""

请编写类型为「{doc_type}」的长篇文档，标题：「{doc_title}」

要求：
1. 结构清晰，层次分明（H1 → H2 → H3）
2. 每个主要章节前有简短导语
3. 参数和配置用表格说明
4. 代码示例可直接运行，带注释
5. 包含 FAQ / 常见问题章节
6. 文档长度 ≥ 1500 字
7. 输出完整的 Markdown 文档
"""
        prompt.append({"role": "user", "content": doc_hint})

        # 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        # 长文档使用 MEDIUM 路由以获得更好的结构化输出
        response = await self.model_router.route_and_call(
            task_type=TaskType.SIMPLE_QA,
            messages=messages,
            complexity="medium",
        )

        return response.content

    def _post_process(self, result: str, context: AgentContext) -> AgentOutput:
        """后处理"""
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result,
            recommendations=[
                "将文档保存到 docs/ 目录",
                "使用 DocumentAgent 定期更新文档版本",
            ],
        )
