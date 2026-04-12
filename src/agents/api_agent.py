"""
API Agent - REST API 设计与实现智能体

职责：
1. RESTful API 设计与规范编写
2. API 端点实现（FastAPI/Flask）
3. API 文档生成（OpenAPI/Swagger）
4. API 认证与权限设计

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
class APIAgent(BaseAgent):
    """REST API 设计与实现智能体"""

    name = "api"
    description = "REST API 设计与实现智能体 - 端点、认证、文档"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🔌"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个专业的 API 架构师。

## 角色
你擅长 RESTful API 设计与实现，关注规范性、可扩展性和开发者体验。

## RESTful 设计原则
1. **资源导向** - 用名词不用动词：/users, /orders
2. **HTTP 方法** - GET(查询), POST(创建), PUT(全量更新), PATCH(部分更新), DELETE(删除)
3. **状态码** - 200/201/204/400/401/403/404/500
4. **版本管理** - /v1/users, /v2/users

## API 认证方案
- JWT Bearer Token
- API Key
- OAuth 2.0

## 输出格式

### 1. API 端点设计
```
端点                        方法    描述
────────────────────────────────────────────────────────
/api/v1/users              GET     获取用户列表
/api/v1/users/{id}         GET     获取单个用户
/api/v1/users              POST    创建用户
/api/v1/users/{id}         PUT     更新用户
/api/v1/users/{id}         DELETE  删除用户
```

### 2. 端点详细定义
```
GET /api/v1/users

请求参数:
  - page: int (query)     页码，默认1
  - page_size: int (query) 每页数量，默认20，最大100
  - keyword: str (query)  搜索关键词

响应:
  200 OK
  {
    "data": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
```

### 3. FastAPI 实现示例
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/users", tags=["用户"])

class UserCreate(BaseModel):
    username: str
    email: str

@router.get("")
async def list_users(page: int = 1, page_size: int = 20):
    ...

@router.post("")
async def create_user(user: UserCreate):
    ...
```
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行 API 设计"""
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 架构设计\n{context.previous_outputs['architect'].result}",
                }
            )

        api_hint = """

请设计 RESTful API：
1. 分析业务需求，确定资源与端点
2. 定义 HTTP 方法和状态码
3. 设计请求/响应格式
4. 实现 FastAPI 代码
5. 生成 OpenAPI 文档

请优先使用 FastAPI 框架。
"""
        prompt.append({"role": "user", "content": api_hint})

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
                "在 app.py 中注册路由",
                "为端点添加单元测试",
                "生成交互式 API 文档",
            ],
            next_agent="executor",
        )
