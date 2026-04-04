"""
QA Tester Agent - QA 测试智能体

职责：
1. 交互式 CLI 测试
2. 服务运行时验证
3. 端到端测试
4. 回归测试

模型层级：MEDIUM（平衡，对应 sonnet）
"""

from typing import List, Dict, Any
from pathlib import Path
import subprocess

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
class QATesterAgent(BaseAgent):
    """QA 测试 Agent - 交互式测试和端到端验证"""

    name = "qa-tester"
    description = "QA 测试智能体 - 交互式测试和端到端验证"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🛠️"
    tools = ["bash", "file_read"]

    @property
    def system_prompt(self) -> str:
        return """你是一个 QA 测试专家，擅长端到端测试和交互式验证。

## 角色
你的职责是通过实际运行程序，验证功能是否符合预期。

## 能力
1. CLI 测试 - 实际运行命令行工具
2. API 测试 - 测试 HTTP 接口
3. 集成测试 - 测试组件间协作
4. 回归测试 - 确保修改没有破坏现有功能

## 测试原则
1. **实际运行** - 不只看代码，要实际执行
2. **边界测试** - 测试正常和异常情况
3. **端到端** - 测试完整流程
4. **可重复** - 测试结果可重复

## 输出格式

### 1. 测试环境
- Python: 3.x
- 系统: macOS/Linux
- 测试命令: ...

### 2. 测试用例

#### TC-01: 基本功能
```
输入: command --arg value
期望: 成功执行，输出...
实际: [PASS/FAIL]
```

#### TC-02: 边界情况
```
输入: command --edge-case
期望: 优雅处理
实际: [PASS/FAIL]
```

### 3. 测试结果
| 用例 | 状态 | 说明 |
|------|------|------|
| TC-01 | ✅ PASS | ... |
| TC-02 | ❌ FAIL | ... |

### 4. 发现的问题
- 问题1: ...
- 问题2: ...

### 5. 回归风险
- ⚠️ 高风险: ...
- 🟡 中风险: ...
- 🟢 低风险: ...
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行 QA 测试"""
        # 获取项目信息
        project_path = context.project_path

        # 检查可执行文件
        executables = []
        for pattern in ["*.sh", "start*.sh", "run*.py"]:
            executables.extend(project_path.glob(pattern))

        # 检查入口文件
        main_files = []
        for name in ["main.py", "app.py", "cli.py", "__main__.py"]:
            main_files.extend(project_path.glob(f"**/{name}"))

        test_info = f"""## 测试环境

项目路径: {project_path}
可执行脚本: {[e.name for e in executables]}
入口文件: {[m.name for m in main_files]}

请设计端到端测试用例，实际运行程序验证功能：
1. 基本功能是否正常？
2. 参数解析是否正确？
3. 错误处理是否优雅？
4. 输出格式是否符合预期？
"""
        prompt.append({"role": "user", "content": test_info})

        # 调用模型
        from ..models.base import Message

        messages = [Message(role=msg["role"], content=msg["content"]) for msg in prompt]

        response = await self.model_router.route_and_call(
            task_type=TaskType.TESTING,
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
                "修复发现的问题",
                "添加自动化测试",
            ],
        )
