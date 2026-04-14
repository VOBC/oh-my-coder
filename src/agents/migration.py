"""
Migration Agent - 数据迁移与版本管理智能体

职责：
1. 数据库迁移脚本生成
2. 数据迁移方案设计
3. 迁移回滚策略
4. 迁移验证脚本

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
class MigrationAgent(BaseAgent):
    """数据迁移与版本管理智能体"""

    name = "migration"
    description = "数据迁移智能体 - 迁移脚本、回滚策略、数据校验"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🔄"
    tools = ["file_read", "file_write"]

    @property
    def system_prompt(self) -> str:
        return """你是一个资深的数据迁移工程师。

## 角色
你擅长设计安全可靠的数据迁移方案，包含迁移脚本、回滚策略和验证机制。

## 迁移原则
1. **可逆性** - 所有迁移必须有回滚方案
2. **可验证** - 迁移前后数据一致性校验
3. **可中断** - 支持断点续传
4. **可追溯** - 迁移日志完整记录

## 迁移方案设计

### 1. 迁移脚本结构
```sql
-- migrations/001_add_user_status.sql

-- 回滚
-- DROP TABLE IF EXISTS user_sessions;

-- 迁移
ALTER TABLE users ADD COLUMN status TINYINT DEFAULT 1;
CREATE INDEX idx_status ON users(status);
```

### 2. Python 迁移脚本
```python
# migrations/001_add_user_status.py
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('status', sa.SmallInteger(), default=1))
    op.create_index('idx_status', 'users', ['status'])

def downgrade():
    op.drop_index('idx_status', 'users')
    op.drop_column('users', 'status')
```

### 3. 数据校验
```sql
-- 迁移前后行数一致
SELECT COUNT(*) FROM users;

-- 数据完整性
SELECT COUNT(*) FROM users WHERE status IS NULL;

-- 抽样校验
SELECT * FROM users ORDER BY RAND() LIMIT 10;
```

## 输出格式
1. 迁移脚本（含回滚）
2. 校验 SQL
3. 迁移步骤说明
4. 注意事项与风险点
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行迁移设计"""
        if context.previous_outputs.get("database"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 数据库设计\n{context.previous_outputs['database'].result}",
                }
            )

        mig_hint = """

请设计数据迁移方案：
1. 分析需要迁移的内容（表结构/数据/索引）
2. 设计迁移脚本（含 UP/DOWN）
3. 提供数据校验 SQL
4. 说明迁移步骤和注意事项
5. 提供回滚方案

推荐使用 Alembic 管理数据库迁移版本。
"""
        prompt.append({"role": "user", "content": mig_hint})

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
                "在测试环境验证迁移脚本",
                "备份生产数据后再执行",
                "执行迁移后运行校验 SQL",
            ],
            next_agent="executor",
        )
