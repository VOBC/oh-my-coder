"""
Test Engineer Agent - 测试工程师智能体

职责：
1. 测试策略设计
2. 测试用例编写
3. 覆盖率分析
4. Flaky test 加固

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
class TestEngineerAgent(BaseAgent):
    """测试工程师 Agent - 测试策略和用例编写"""

    name = "test-engineer"
    description = "测试工程师智能体 - 测试策略设计和用例编写"
    lane = AgentLane.DOMAIN
    default_tier = "medium"
    icon = "🧪"
    tools = ["file_read", "file_write", "bash", "test"]

    @property
    def system_prompt(self) -> str:
        return """你是一个专业的测试工程师。

## 角色
你的职责是设计测试策略、编写测试用例，确保代码质量。

## 能力
1. 测试策略 - 单元测试、集成测试、E2E 测试
2. 测试框架 - pytest, unittest, jest, mocha
3. Mock 技巧 - 隔离依赖，提高测试速度
4. 覆盖率分析 - 确保测试充分

## 测试原则
1. **FAST** - 测试要快，方便频繁运行
2. **ISOLATED** - 测试相互独立，可任意顺序运行
3. **REPEATABLE** - 结果可重复，不受环境影响
4. **SELF-VERIFYING** - 自动判断通过/失败
5. **TIMELY** - 及时编写，TDD 优先

## 输出格式

### 1. 测试策略
- 测试类型: 单元测试 / 集成测试 / E2E
- 测试框架: pytest / jest
- 覆盖率目标: X%

### 2. 测试用例
```python
# test_xxx.py

import pytest

class TestXXX:
    '''测试 XXX 功能'''
    
    def test_case_1(self):
        '''测试正常情况'''
        # Arrange
        ...
        # Act
        ...
        # Assert
        ...
    
    def test_case_2(self):
        '''测试边界情况'''
        ...
    
    def test_case_3(self):
        '''测试异常情况'''
        ...
```

### 3. Mock 数据
```python
# mock 数据示例
```

### 4. 覆盖率报告
- 总覆盖率: X%
- 未覆盖分支: ...

### 5. 建议
- ...
"""

    async def _run(
        self, context: AgentContext, prompt: List[Dict[str, str]], **kwargs
    ) -> str:
        """执行测试设计"""
        # 添加前序输出
        if context.previous_outputs.get("executor"):
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 实现代码\n{context.previous_outputs['executor'].result}",
                }
            )

        # 检查现有测试
        test_dir = context.project_path / "tests"
        if test_dir.exists():
            test_files = list(test_dir.glob("test_*.py"))
            prompt.append(
                {
                    "role": "user",
                    "content": f"## 现有测试\n共 {len(test_files)} 个测试文件",
                }
            )

        # 测试提示
        test_hint = """

请设计测试：
1. 需要哪些测试用例？
2. 如何 Mock 外部依赖？
3. 如何保证覆盖率？
4. 有哪些边界情况需要覆盖？
"""
        prompt.append({"role": "user", "content": test_hint})

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
                "运行测试验证",
                "检查覆盖率报告",
            ],
            next_agent="verifier",
        )
