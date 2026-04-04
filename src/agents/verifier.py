"""
Verifier Agent - 验证智能体

职责：
1. 验证代码功能正确性
2. 检查测试覆盖率
3. 运行测试套件
4. 确认任务完成

模型层级：MEDIUM（平衡，对应 sonnet）
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
class VerifierAgent(BaseAgent):
    """验证 Agent - 确保代码质量和功能正确"""
    
    name = "verifier"
    description = "验证智能体 - 检查功能正确性和测试覆盖"
    lane = AgentLane.BUILD_ANALYSIS
    default_tier = "medium"
    icon = "✅"
    tools = ["bash", "file_read", "test"]
    
    @property
    def system_prompt(self) -> str:
        return """你是一个严谨的质量保证工程师。

## 角色
你的职责是验证代码是否正确实现了需求，确保质量达标。

## 能力
1. 功能验证 - 运行测试，检查结果
2. 覆盖率检查 - 确保测试充分
3. 集成测试 - 端到端验证
4. 回归检查 - 确保没有破坏现有功能

## 验证标准
- ✅ BUILD: 代码编译通过
- ✅ TEST: 所有测试通过
- ✅ LINT: 无 lint 错误
- ✅ FUNCTIONALITY: 功能按预期工作
- ✅ NO_TODO: 无遗留 TODO
- ✅ ERROR_FREE: 无未解决错误

## 输出格式

### 1. 验证结果
| 检查项 | 状态 | 说明 |
|--------|------|------|
| BUILD | ✅/❌ | ... |
| TEST | ✅/❌ | ... |

### 2. 测试覆盖
- 总测试数: X
- 通过: X
- 失败: X
- 覆盖率: X%

### 3. 发现的问题
- 问题1: ...
- 问题2: ...

### 4. 建议
- ...
"""
    
    async def _run(
        self,
        context: AgentContext,
        prompt: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """执行验证"""
        # 添加前序输出
        if context.previous_outputs.get("executor"):
            prompt.append({
                "role": "user",
                "content": f"## 实现代码\n{context.previous_outputs['executor'].result}"
            })
        
        # 读取测试文件
        test_dir = context.project_path / "tests"
        if test_dir.exists():
            test_files = list(test_dir.glob("test_*.py"))
            if test_files:
                tests_info = f"## 现有测试\n共 {len(test_files)} 个测试文件"
                prompt.append({"role": "user", "content": tests_info})
        
        # 验证提示
        verify_hint = """

请验证实现是否正确：
1. 代码是否能编译/运行？
2. 测试是否通过？
3. 功能是否符合需求？
4. 是否有遗漏的边界情况？
"""
        prompt.append({"role": "user", "content": verify_hint})
        
        # 调用模型
        from ..models.base import Message
        
        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in prompt
        ]
        
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
                "如果验证通过，可以提交代码",
                "如果验证失败，返回 executor 修复",
            ],
        )
