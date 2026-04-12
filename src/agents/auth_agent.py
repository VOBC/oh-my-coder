"""
Auth Agent - 认证与授权智能体

职责：
1. JWT / OAuth2 / API Key 认证方案设计
2. RBAC 权限模型设计
3. 登录注册流程实现
4. 安全中间件配置

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
class AuthAgent(BaseAgent):
    """认证与授权智能体"""

    name = "auth"
    description = "认证与授权智能体 - JWT、OAuth、RBAC、登录注册"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🔐"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个身份认证与授权专家。

## 角色
你擅长设计安全的认证方案和权限模型。

## 认证方案

### JWT
```python
import jwt
from datetime import datetime, timedelta

def create_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

### RBAC 权限模型
```
角色: admin, editor, viewer
权限: user.read, user.write, user.delete, post.read, post.write
分配:
  admin → 所有权限
  editor → user.read, post.read, post.write
  viewer → user.read, post.read
```

## 输出格式
1. 认证方案选型建议
2. 核心代码实现
3. 中间件配置
4. 权限装饰器
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行认证设计"""
        auth_hint = """

请设计认证与授权方案：
1. 根据项目需求选择认证方案（JWT / OAuth2 / API Key）
2. 设计权限模型（RBAC / ABAC）
3. 提供完整的认证代码
4. 配置中间件和路由保护
"""
        prompt.append({"role": "user", "content": auth_hint})

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
                "在 .env 中配置 SECRET_KEY",
                "为敏感接口添加权限验证",
                "实现 token 刷新机制",
            ],
            next_agent="executor",
        )
