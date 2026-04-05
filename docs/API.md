# API 文档

> Oh My Coder v0.2.0 - 完整 API 参考手册

---

## 目录

- [快速开始](#快速开始)
- [Web API](#web-api)
  - [基础信息](#基础信息)
  - [任务执行](#任务执行)
  - [任务管理](#任务管理)
  - [SSE 实时推送](#sse-实时推送)
- [Python SDK](#python-sdk)
  - [Orchestrator](#orchestrator)
  - [ModelRouter](#modelrouter)
  - [AgentContext](#agentcontext)
- [模型适配器](#模型适配器)
  - [DeepSeek](#deepseek)
  - [文心一言](#文心一言)
  - [通义千问](#通义千问)
- [错误处理](#错误处理)
- [类型参考](#类型参考)

---

## 快速开始

```python
from src.core.orchestrator import Orchestrator
from src.core.router import ModelRouter, RouterConfig

# 初始化
router = ModelRouter(RouterConfig())
orch = Orchestrator(router)

# 执行任务
result = await orch.execute_workflow("build", {
    "project_path": ".",
    "task": "实现一个 REST API",
})
```

---

## Web API

启动 Web 服务：

```bash
python -m src.web.app
# http://localhost:8000
```

### 基础信息

| 属性 | 值 |
|------|-----|
| Base URL | `http://localhost:8000` |
| 协议 | HTTP |
| 格式 | JSON |
| 字符编码 | UTF-8 |

### 认证

当前版本无需认证。请通过环境变量配置 API Key：

```bash
export DEEPSEEK_API_KEY=your_key_here
```

---

### 任务执行

#### POST `/api/execute`

异步提交任务，通过 SSE 接收实时进度。

**请求体：**

```json
{
  "task": "实现一个用户认证系统",
  "project_path": ".",
  "model": "deepseek",
  "workflow": "build"
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `task` | string | ✅ | - | 任务描述 |
| `project_path` | string | ❌ | `.` | 项目路径 |
| `model` | string | ❌ | `deepseek` | 模型：`deepseek` / `tongyi` / `wenxin` |
| `workflow` | string | ❌ | `build` | 工作流：`build` / `review` / `debug` / `test` |

**响应：**

```json
{
  "status": "started",
  "task_id": "a1b2c3d4",
  "message": "任务已启动，请通过 SSE 连接获取进度"
}
```

**错误响应：**

```json
{
  "detail": "Missing 'task' field"
}
```

---

#### POST `/api/execute-sync`

同步执行任务，直接返回结果（适合小任务）。

**请求体：** 同 `/api/execute`

**响应：**

```json
{
  "status": "success",
  "result": {
    "task": "实现一个加法函数",
    "workflow": "build",
    "steps_completed": ["explore", "analyst", "architect", "executor", "verifier"],
    "total_tokens": 1234,
    "execution_time": 15.2,
    "outputs": {
      "explore": "## 项目结构\n- src/\n...",
      "executor": "```python\ndef add(a, b): return a + b\n```"
    }
  }
}
```

---

### 任务管理

#### GET `/api/tasks`

列出所有任务。

**响应：**

```json
{
  "tasks": [
    {
      "task_id": "a1b2c3d4",
      "status": "completed",
      "started_at": "2026-04-05T10:30:00",
      "completed_at": "2026-04-05T10:31:00"
    }
  ]
}
```

---

#### GET `/api/tasks/{task_id}`

获取任务详情。

**响应：**

```json
{
  "status": "completed",
  "started_at": "2026-04-05T10:30:00",
  "completed_at": "2026-04-05T10:31:00",
  "result": { ... },
  "step_status": {
    "explore": "completed",
    "analyst": "completed",
    "executor": "completed"
  },
  "step_outputs": {
    "explore": "项目结构已扫描"
  },
  "stats": {
    "total_tokens": 1234,
    "total_cost": 0.0,
    "execution_time": 60.5,
    "steps_completed": ["explore", "analyst", "executor"],
    "steps_failed": [],
    "steps_total": 5
  }
}
```

---

### SSE 实时推送

#### GET `/sse/execute/{task_id}`

通过 Server-Sent Events 接收任务实时进度。

**事件格式：**

```
event: message
data: {"type": "step_start", "step": "explore", "content": null}
data: {"type": "step_complete", "step": "explore", "content": "项目结构已扫描"}
data: {"type": "step_start", "step": "analyst", "content": null}
data: {"type": "complete", "result": {...}, "stats": {...}}
```

**事件类型：**

| type | 说明 | 字段 |
|------|------|------|
| `step_start` | 步骤开始 | `step`, `content` |
| `step_complete` | 步骤完成 | `step`, `content` |
| `step_failed` | 步骤失败 | `step`, `content` |
| `stats` | 统计更新 | `stats` |
| `complete` | 任务完成 | `result`, `stats` |
| `error` | 任务失败 | `content` |

**前端使用示例：**

```javascript
const es = new EventSource(`/sse/execute/${taskId}`);
es.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === 'step_start') {
    highlightStep(data.step, 'active');
  } else if (data.type === 'step_complete') {
    highlightStep(data.step, 'completed');
  } else if (data.type === 'complete') {
    showResult(data.result);
    es.close();
  }
};
```

---

### 健康检查

#### GET `/health`

**响应：**

```json
{
  "status": "healthy",
  "version": "0.2.0"
}
```

---

### 配置信息

#### GET `/api/config`

获取可用配置。

**响应：**

```json
{
  "models": ["deepseek", "tongyi", "wenxin"],
  "workflows": ["build", "review", "debug", "test"]
}
```

---

## Python SDK

### Orchestrator

编排器，负责管理和调度多个 Agent 协作。

```python
from src.core.orchestrator import Orchestrator

orch = Orchestrator(model_router=router)
```

#### `execute_workflow(workflow_name, context, mode)`

执行完整工作流。

```python
result = await orch.execute_workflow(
    "build",
    {
        "project_path": ".",
        "task": "实现一个 REST API",
    }
)
# result: WorkflowResult
```

#### `execute_single_agent(agent_name, context)`

执行单个 Agent。

```python
output = await orch.execute_single_agent(
    "explore",
    {"project_path": ".", "task": "探索代码库"}
)
# output: AgentOutput
```

#### `get_agent(name)`

获取 Agent 实例（惰性加载）。

```python
agent = orch.get_agent("executor")
```

#### `register_agent(agent)`

注册 Agent 实例。

```python
orch.register_agent(MyAgent(router))
```

---

### ModelRouter

模型路由器，智能选择最优模型。

```python
from src.core.router import ModelRouter, RouterConfig, TaskType

config = RouterConfig()
router = ModelRouter(config)
```

#### `select(task_type, complexity, budget_remaining)`

选择最优模型，返回路由决策。

```python
decision = router.select(
    task_type=TaskType.CODE_GENERATION,
    complexity="medium",
)
# decision: RoutingDecision
print(f"选择: {decision.selected_provider} / {decision.selected_tier}")
```

#### `route_and_call(task_type, messages, complexity)`

路由并执行，带故障转移。

```python
response = await router.route_and_call(
    task_type=TaskType.EXPLORE,
    messages=[Message(role="user", content="探索代码库")],
    complexity="low",
)
# response: ModelResponse
```

#### `get_stats()`

获取路由统计。

```python
stats = router.get_stats()
# {
#   "total_requests": 10,
#   "total_cost": 0.0,
#   "provider_distribution": {"deepseek": 10},
#   "tier_distribution": {"low": 5, "medium": 3, "high": 2},
# }
```

#### `get_model(provider, tier)`

直接获取指定模型。

```python
model = router.get_model(ModelProvider.DEEPSEEK, ModelTier.HIGH)
```

---

### AgentContext

Agent 执行上下文。

```python
from src.agents.base import AgentContext

ctx = AgentContext(
    project_path=Path("."),
    task_description="实现一个加法函数",
    previous_outputs={"explore": explore_output},
    metadata={"file": "calculator.py"},
)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_path` | `Path` | 项目路径 |
| `task_description` | `str` | 任务描述 |
| `working_directory` | `Path` | 工作目录（可选） |
| `relevant_files` | `List[Path]` | 相关文件（可选） |
| `previous_outputs` | `Dict` | 前序 Agent 输出（可选） |
| `metadata` | `Dict` | 其他元数据（可选） |

---

## 模型适配器

### DeepSeek

免费额度高，默认优先使用。

```python
from src.models.deepseek import DeepSeekModel
from src.models.base import ModelConfig, ModelTier

config = ModelConfig(api_key="your_key")
model = DeepSeekModel(config, ModelTier.MEDIUM)

response = await model.generate(messages)
```

**层级映射：**

| Tier | 模型 |
|------|------|
| LOW | `deepseek-chat` (快速) |
| MEDIUM | `deepseek-chat` (平衡) |
| HIGH | `deepseek-reasoner` (深度推理) |

**成本：** 完全免费（每日 4000 万 token 额度）

---

### 文心一言

```python
from src.models.wenxin import WenxinModel
from src.models.base import ModelConfig, ModelTier

config = ModelConfig(
    api_key="your_api_key",
)
model = WenxinModel(
    config,
    ModelTier.MEDIUM,
    secret_key="your_secret_key",
)
```

---

### 通义千问

```python
from src.models.tongyi import TongyiModel
from src.models.base import ModelConfig, ModelTier

config = ModelConfig(api_key="your_key")
model = TongyiModel(config, ModelTier.MEDIUM)
```

---

## 错误处理

### 异常类型

| 异常 | 说明 |
|------|------|
| `NoModelAvailableError` | 没有可用模型（所有提供商均不可用） |
| `HTTPError` | HTTP 请求错误 |
| `ValidationError` | 请求参数校验失败 |
| `TimeoutError` | 请求超时 |

### 处理示例

```python
from src.core.router import NoModelAvailableError

try:
    response = await router.route_and_call(task_type, messages)
except NoModelAvailableError as e:
    print(f"所有模型均不可用: {e}")
    # 降级处理
except TimeoutError as e:
    print(f"请求超时: {e}")
    # 重试
except Exception as e:
    print(f"未知错误: {e}")
```

### 重试策略

默认重试 3 次，每次等待 2 秒：

```
Attempt 1: → 失败 → 等待 2s
Attempt 2: → 失败 → 等待 4s
Attempt 3: → 失败 → 抛出异常
```

可通过 `ModelConfig` 自定义：

```python
config = ModelConfig(
    max_retries=5,
    retry_delay=3.0,
    timeout=120.0,
)
```

---

## 类型参考

### Message

```python
@dataclass
class Message:
    role: str           # "system" | "user" | "assistant"
    content: str        # 消息内容
    name: Optional[str] # 角色名称（可选）
```

### Usage

```python
@dataclass
class Usage:
    prompt_tokens: int      # prompt token 数量
    completion_tokens: int  # completion token 数量
    total_tokens: int       # 总 token 数量
```

### ModelResponse

```python
@dataclass
class ModelResponse:
    content: str           # 响应内容
    model: str             # 实际使用的模型名
    provider: ModelProvider # 提供商
    tier: ModelTier         # 层级
    usage: Usage           # token 使用统计
    finish_reason: str     # 结束原因
    latency_ms: float       # 延迟（毫秒）
    metadata: Dict          # 其他元数据
```

### WorkflowResult

```python
@dataclass
class WorkflowResult:
    workflow_id: str              # 工作流 ID
    status: WorkflowStatus         # 状态
    steps_completed: List[str]    # 已完成步骤
    steps_failed: List[str]       # 失败步骤
    outputs: Dict[str, AgentOutput] # 各步骤输出
    total_tokens: int             # 总 token
    total_cost: float             # 总成本
    execution_time: float         # 执行时间（秒）
    error: Optional[str]           # 错误信息
    timestamp: str                 # 时间戳
```

### AgentOutput

```python
@dataclass
class AgentOutput:
    agent_name: str              # Agent 名称
    status: AgentStatus          # 执行状态
    result: Optional[str]        # 主要结果
    artifacts: Dict              # 产物
    recommendations: List[str]   # 推荐后续步骤
    next_agent: Optional[str]    # 推荐下一个 Agent
    usage: Dict                 # Token 使用
    execution_time: float        # 执行时间
    error: Optional[str]         # 错误信息
    timestamp: str               # 时间戳
```
