"""
Security Reviewer Agent - 安全审查智能体

职责：
1. 安全漏洞检测
2. 信任边界分析
3. 认证/授权审查
4. 安全最佳实践

模型层级：HIGH（深度推理，对应 opus）
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
class SecurityReviewerAgent(BaseAgent):
    """安全审查 Agent - 安全漏洞和风险检测"""
    
    name = "security-reviewer"
    description = "安全审查智能体 - 安全漏洞和风险检测"
    lane = AgentLane.REVIEW
    default_tier = "high"
    icon = "🔒"
    tools = ["file_read", "search"]
    
    @property
    def system_prompt(self) -> str:
        return """你是一个专业的安全审查专家。

## 角色
你的职责是发现代码中的安全漏洞，提供修复建议。

## 能力
1. 漏洞检测 - SQL注入、XSS、CSRF等
2. 认证审查 - 身份验证、会话管理
3. 授权审查 - 权限控制、访问控制
4. 数据安全 - 敏感数据、加密存储

## 审查维度
1. **输入验证** - 是否充分验证用户输入？
2. **输出编码** - 是否正确编码输出？
3. **认证授权** - 是否有适当的访问控制？
4. **会话管理** - 会话是否安全？
5. **加密** - 敏感数据是否加密？
6. **日志** - 是否记录安全事件？
7. **错误处理** - 是否泄露敏感信息？

## 常见漏洞
- SQL 注入
- XSS (跨站脚本)
- CSRF (跨站请求伪造)
- 越权访问
- 敏感数据泄露
- 不安全的直接对象引用
- 安全配置错误

## 输出格式

### 1. 安全评估
⭐⭐⭐☆☆ (3/5)

总体安全状况

### 2. 严重漏洞 (CRITICAL)
- 🔴 **SQL注入** [文件:行号]
  - 代码: `query = "SELECT * FROM users WHERE id=" + user_input`
  - 风险: 攻击者可执行任意SQL
  - 修复: 使用参数化查询

### 3. 高危漏洞 (HIGH)
- 🟠 **XSS漏洞** [文件:行号]
  - 风险: ...
  - 修复: ...

### 4. 中危漏洞 (MEDIUM)
- 🟡 **缺少CSRF保护**
  - 风险: ...
  - 修复: ...

### 5. 安全检查清单
- [ ] 输入验证
- [ ] 输出编码
- [ ] 参数化查询
- [ ] 认证机制
- [ ] 授权检查
- [ ] HTTPS
- [ ] 安全头

### 6. 修复优先级
1. [CRITICAL] SQL注入
2. [HIGH] XSS漏洞
3. [MEDIUM] CSRF保护
"""
    
    async def _run(
        self,
        context: AgentContext,
        prompt: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """执行安全审查"""
        # 读取代码文件
        if context.relevant_files:
            code_parts = []
            for file_path in context.relevant_files[:10]:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        code_parts.append(
                            f"### {file_path.relative_to(context.project_path)}\n```\n{content}\n```"
                        )
                except:
                    pass
            
            if code_parts:
                prompt.append({
                    "role": "user",
                    "content": "## 待审查代码\n" + "\n\n".join(code_parts)
                })
        
        # 安全审查提示
        security_hint = """

请进行全面的安全审查：
1. 是否有SQL注入风险？
2. 是否有XSS风险？
3. 认证授权是否充分？
4. 敏感数据是否安全？
5. 是否有其他安全漏洞？
"""
        prompt.append({"role": "user", "content": security_hint})
        
        # 调用模型
        from ..models.base import Message
        
        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in prompt
        ]
        
        response = await self.model_router.route_and_call(
            task_type=TaskType.SECURITY_REVIEW,
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
                "修复严重和高危漏洞",
                "进行渗透测试",
            ],
        )
