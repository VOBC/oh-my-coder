# 进阶教程

> 深入学习多 Agent 协作和高级功能

---

## 🔄 多 Agent 协作原理

### 工作流执行流程

```
┌─────────────────────────────────────────────────────────────┐
│                     build 工作流                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ explore │───▶│ analyst │───▶│ planner │───▶│architect│  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│       │              │              │              │        │
│       ▼              ▼              ▼              ▼        │
│   项目结构       需求分析        任务计划        架构设计     │
│                                                             │
│  ┌─────────┐    ┌─────────┐                                 │
│  │ executor│───▶│ verifier│                                 │
│  └─────────┘    └─────────┘                                 │
│       │              │                                      │
│       ▼              ▼                                      │
│   代码实现        测试验证                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Agent 上下文传递

每个 Agent 的输出会传递给下一个 Agent：

```python
# Agent 上下文结构
context = {
    "project_path": "/path/to/project",
    "task": "实现用户认证",
    "previous_outputs": {
        "explore": {
            "files_count": 89,
            "tech_stack": ["FastAPI", "SQLAlchemy"],
            "structure": {...}
        },
        "analyst": {
            "entities": ["User", "Session", "Token"],
            "requirements": [...]
        },
        # ...
    }
}
```

---

## 🧠 模型路由策略

### 三层模型分级

| 层级 | 用途 | 模型示例 | Token 成本 |
|------|------|----------|-----------|
| LOW | 简单任务 | DeepSeek Lite | 低 |
| MEDIUM | 常规任务 | DeepSeek Pro | 中 |
| HIGH | 复杂任务 | GLM-4, Kimi | 高 |

### 任务类型映射

```python
# src/core/router.py 中的映射
TASK_TYPE_TO_TIER = {
    TaskType.EXPLORE: Tier.LOW,      # 探索 → 低成本
    TaskType.ANALYZE: Tier.HIGH,     # 分析 → 高能力
    TaskType.PLAN: Tier.HIGH,        # 规划 → 高能力
    TaskType.DESIGN: Tier.HIGH,      # 设计 → 高能力
    TaskType.CODE: Tier.MEDIUM,      # 编码 → 中等
    TaskType.VERIFY: Tier.MEDIUM,    # 验证 → 中等
    TaskType.DEBUG: Tier.MEDIUM,     # 调试 → 中等
}
```

### 智能路由决策

```python
from src.core.router import ModelRouter, RouterConfig, TaskType

config = RouterConfig(deepseek_api_key="your_key")
router = ModelRouter(config)

# 路由决策
decision = router.select(TaskType.CODE)
print(f"选择模型: {decision.selected_provider}")
print(f"选择层级: {decision.selected_tier}")
print(f"预估成本: ${decision.estimated_cost:.4f}")
```

---

## 🔧 自定义工作流

### 定义新工作流

```python
# 在 src/core/workflows/ 中创建新工作流
custom_workflow = {
    "name": "smart_refactor",
    "description": "智能重构工作流",
    "steps": [
        {"agent": "explore", "required": True},
        {"agent": "code-reviewer", "required": True},
        {"agent": "code-simplifier", "required": True},
        {"agent": "verifier", "required": True},
    ],
    "execution_mode": "sequential",
    "retry_policy": {
        "max_retries": 2,
        "backoff_factor": 2.0,
    }
}
```

### 执行模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `sequential` | 顺序执行 | 有依赖关系的步骤 |
| `parallel` | 并行执行 | 独立的步骤 |
| `conditional` | 条件执行 | 根据结果决定下一步 |

### 条件执行示例

```python
conditional_workflow = {
    "name": "adaptive_build",
    "steps": [
        {"agent": "explore", "required": True},
        {"agent": "analyst", "required": True},
        # 只有复杂度 HIGH 时才执行 architect
        {
            "agent": "architect",
            "required": False,
            "condition": "complexity == 'high'"
        },
        {"agent": "executor", "required": True},
        {"agent": "verifier", "required": True},
    ],
    "execution_mode": "conditional"
}
```

---

## 📊 任务总结与报告

### 生成报告

```python
from src.core.summary import generate_summary, save_summary
from pathlib import Path

# 任务完成后生成总结
summary = generate_summary(
    task="实现用户认证模块",
    workflow="build",
    completed_steps=[
        {"agent": "explore", "status": "completed", "duration": 2.3},
        {"agent": "analyst", "status": "completed", "duration": 5.1},
        # ...
    ],
)

# 导出为多种格式
save_summary(summary, format="json", output_dir=Path("reports"))
save_summary(summary, format="html", output_dir=Path("reports"))
save_summary(summary, format="txt", output_dir=Path("reports"))
```

### 报告内容

```json
{
  "task": "实现用户认证模块",
  "workflow": "build",
  "status": "completed",
  "total_duration": 32.5,
  "total_tokens": 28500,
  "estimated_cost": 0.0285,
  "steps": [
    {"agent": "explore", "duration": 2.3, "tokens": 1200},
    {"agent": "analyst", "duration": 5.1, "tokens": 3500},
    {"agent": "planner", "duration": 4.2, "tokens": 2800},
    {"agent": "architect", "duration": 8.5, "tokens": 5200},
    {"agent": "executor", "duration": 10.2, "tokens": 12000},
    {"agent": "verifier", "duration": 2.2, "tokens": 3800}
  ]
}
```

---

## 🌐 Web API 高级用法

### SSE 流式响应

```python
import httpx
import asyncio

async def execute_task():
    url = "http://localhost:8000/api/execute"
    payload = {
        "task": "实现 REST API",
        "workflow": "build"
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    print(line[5:])  # 打印 SSE 数据

asyncio.run(execute_task())
```

### 任务管理

```python
# 列出所有任务
response = httpx.get("http://localhost:8000/api/tasks")
tasks = response.json()

# 获取特定任务
task_id = "task_20260408_123456"
response = httpx.get(f"http://localhost:8000/api/tasks/{task_id}")
task = response.json()

# 取消任务
httpx.post(f"http://localhost:8000/api/tasks/{task_id}/cancel")
```

---

## 🔌 扩展开发

### 添加新模型

```python
# src/models/my_model.py
from src.models.base import BaseModel, ModelConfig

class MyModel(BaseModel):
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.base_url = "https://api.my-model.com"
    
    async def generate(self, messages: list) -> str:
        # 实现生成逻辑
        pass
    
    async def stream(self, messages: list):
        # 实现流式生成
        pass
```

### 添加新 Agent

```python
# src/agents/my_agent.py
from src.agents.base import BaseAgent, AgentContext

class MyAgent(BaseAgent):
    name = "my_agent"
    tier = Tier.MEDIUM
    
    async def execute(self, context: AgentContext) -> dict:
        # 实现执行逻辑
        return {
            "status": "completed",
            "output": "..."
        }
```

---

## 📈 性能优化

### 缓存策略

```python
from src.core.router import ModelRouter

router = ModelRouter(config)

# 查看缓存统计
stats = router.cache.stats()
print(f"缓存命中: {stats['hits']}")
print(f"缓存未命中: {stats['misses']}")

# 清除缓存
router.clear_cache()
```

### 并行执行

```python
# 在工作流中启用并行
parallel_workflow = {
    "name": "parallel_analysis",
    "steps": [
        {"agent": "code-reviewer", "required": True},
        {"agent": "security-reviewer", "required": True},
    ],
    "execution_mode": "parallel"  # 并行执行
}
```

---

## 🛠️ 调试技巧

### 查看详细日志

```bash
# 启用 DEBUG 日志
export OMC_LOG_LEVEL=DEBUG
omc run "实现功能" -w build
```

### 单步调试 Agent

```python
from src.agents.explore import ExploreAgent
from src.core.router import ModelRouter

router = ModelRouter(config)
agent = ExploreAgent(router)

# 单独执行某个 Agent
result = await agent.execute(context)
print(result)
```

### 检查上下文

```python
# 在 Agent 执行前后检查上下文
print("输入上下文:", context)
result = await agent.execute(context)
print("输出结果:", result)
```

---

## 📚 相关文档

- [快速入门](./getting-started.md) - 基础使用
- [API 文档](../API.md) - 完整 API 参考
- [架构设计](../ARCHITECTURE.md) - 系统架构
- [FAQ](../FAQ.md) - 常见问题
