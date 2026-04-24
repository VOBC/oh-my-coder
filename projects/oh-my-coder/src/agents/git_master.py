"""
Git Master Agent - Git 操作智能体

职责：
1. Git 操作执行
2. 提交管理
3. 分支管理
4. 历史管理

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
class GitMasterAgent(BaseAgent):
    """Git 操作 Agent - 版本控制管理"""

    name = "git-master"
    description = "Git 操作智能体 - 版本控制和提交管理"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🔀"
    tools = ["bash", "file_read"]

    @property
    def system_prompt(self) -> str:
        return """你是一个 Git 版本控制专家。

## 角色
你的职责是执行 Git 操作，管理代码版本。

## 能力
1. 提交管理 - commit, amend, message
2. 分支管理 - branch, merge, rebase
3. 历史管理 - log, diff, blame
4. 远程操作 - push, pull, fetch

## Git 最佳实践
1. **原子提交** - 每个提交只做一件事
2. **语义化消息** - feat/fix/docs/refactor/test
3. **频繁提交** - 小步快跑
4. **写好消息** - 标题简短，正文详细

## Commit 消息格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

类型：
- feat: 新功能
- fix: Bug 修复
- docs: 文档更新
- refactor: 代码重构
- test: 测试相关
- chore: 构建/工具

## 输出格式

### 1. 当前状态
```
On branch main
Changes to be committed:
  modified:   src/xxx.py

Changes not staged for commit:
  modified:   src/yyy.py

Untracked files:
  src/zzz.py
```

### 2. 推荐操作
```bash
# 添加修改
git add src/xxx.py

# 提交
git commit -m "feat(core): 添加新功能"

# 推送
git push origin main
```

### 3. 提交历史
```
abc123 feat(core): 添加新功能
def456 fix: 修复 Bug
...
```

### 4. 分支策略建议
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行 Git 操作"""
        import subprocess

        # 获取 Git 状态
        try:
            status_result = subprocess.run(
                ["git", "status", "--short"],
                cwd=context.project_path,
                capture_output=True,
                text=True,
            )
            status = status_result.stdout
        except:
            status = "无法获取 Git 状态"

        # 获取最近的提交
        try:
            log_result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                cwd=context.project_path,
                capture_output=True,
                text=True,
            )
            recent_commits = log_result.stdout
        except:
            recent_commits = "无法获取提交历史"

        prompt.append(
            {
                "role": "user",
                "content": f"""## 当前 Git 状态
```
{status}
```

## 最近提交
```
{recent_commits}
```

请分析状态并给出 Git 操作建议：
1. 应该提交哪些文件？
2. 如何编写提交消息？
3. 是否需要创建分支？
""",
            }
        )

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
                "执行推荐的 Git 命令",
                "推送到远程仓库",
            ],
        )
