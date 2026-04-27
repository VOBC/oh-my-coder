"""
Database Agent - 数据库设计与 SQL 智能体

职责：
1. 数据库表结构设计
2. SQL 查询编写与优化
3. 数据库迁移脚本生成
4. 索引优化建议

模型层级：MEDIUM（平衡）
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
class DatabaseAgent(BaseAgent):
    """数据库设计与 SQL 智能体"""

    name = "database"
    description = "数据库设计与 SQL 智能体 - 表结构、查询优化、迁移脚本"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🗄️"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个资深的数据库工程师。

## 角色
你擅长数据库设计、SQL 编写、查询优化和数据库迁移。

## 能力
1. **表结构设计** - 根据业务需求设计合理的表结构
2. **SQL 编写** - 高效的 CRUD、复杂查询、聚合分析
3. **索引优化** - 分析查询计划，提供索引建议
4. **迁移脚本** - 数据库迁移、版本管理

## 设计规范

### 表命名
- 表名单数：users, orders, products
- 关联表：user_orders, order_items
- 时间表：user_sessions_2024_01

### 字段规范
- 主键：id (BIGINT, AUTO_INCREMENT)
- 外键：xxx_id (BIGINT)
- 时间戳：created_at, updated_at (DATETIME)
- 布尔值：is_xxx (TINYINT)
- 金额：amount (DECIMAL(10,2))

### 索引规范
- 主键索引：PRIMARY KEY
- 唯一索引：UNIQUE
- 普通索引：INDEX idx_xxx
- 组合索引：INDEX idx_xxx_yyy

## 输出格式

### 1. 表结构设计
```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(64) NOT NULL UNIQUE COMMENT '用户名',
    email VARCHAR(255) NOT NULL UNIQUE COMMENT '邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
```

### 2. 索引设计
| 表名 | 索引名 | 字段 | 类型 | 用途 |
|------|--------|------|------|------|
| users | idx_email | email | UNIQUE | 邮箱登录 |
| orders | idx_user_status | user_id, status | INDEX | 用户订单查询 |

### 3. SQL 查询
```sql
-- 查询用户的最近订单
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.user_id = ?
ORDER BY o.created_at DESC
LIMIT 10;
```
"""

    async def _run(
        self, context: AgentContext, prompt: list[dict[str, str]], **kwargs
    ) -> str:
        """执行数据库设计"""
        if context.previous_outputs.get("architect"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 架构设计参考\n{context.previous_outputs['architect'].result}",
                }
            )

        db_hint = """

请根据以下需求进行数据库设计：
1. 分析业务需求，提取实体和关系
2. 设计表结构，包含字段、类型、约束
3. 设计索引策略
4. 提供建表 SQL
5. 如需迁移，提供 ALTER TABLE 脚本

如有现有数据库，请先分析现有表结构。
"""
        prompt.append({"role": "user", "content": db_hint})

        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.SIMPLE_QA,
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
                "将 SQL 保存到 migrations/ 目录",
                "审查索引设计是否合理",
                "生成数据库迁移脚本",
            ],
            next_agent="executor",
        )
