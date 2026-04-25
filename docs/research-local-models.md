# 本地模型支持调研报告

## 1. Ollama REST API 梳理

### 1.1 /api/tags - 列出本地模型
```
GET /api/tags
```
返回已下载的模型列表，含名称、大小、修改时间等。

### 1.2 /api/generate - 文本生成（旧版）
```
POST /api/generate
Body: {"model": "qwen2:7b", "prompt": "...", "stream": false}
```
单轮文本生成，非对话模式。

### 1.3 /api/chat - 对话生成（推荐）
```
POST /api/chat
Body: {
  "model": "qwen2:7b",
  "messages": [{"role": "user", "content": "..."}],
  "stream": false,
  "options": {"temperature": 0.7, "num_ctx": 4096}
}
```
支持多轮对话，返回 token 统计（eval_count/prompt_eval_count）。

### 1.4 /api/show - 模型信息
```
POST /api/show
Body: {"model": "qwen2:7b"}
```
返回模型详细信息：参数、模板、license 等。

---

## 2. 当前项目 Ollama 集成现状

### 2.1 已实现功能（src/models/ollama.py）
- ✅ 基础对话生成（/api/chat）
- ✅ 流式响应支持
- ✅ 静态方法 `is_available()` - 检测服务
- ✅ 静态方法 `list_models()` - 获取本地模型列表
- ✅ 模型分级映射（LOW/MEDIUM/HIGH）
- ✅ 零成本、离线可用

### 2.2 路由器集成（src/core/router.py）
- ✅ RouterConfig 支持 ollama_base_url / ollama_model / prefer_local
- ✅ 故障转移顺序支持 ollama（可按 prefer_local 调整优先级）
- ✅ _initialize_models() 中检测并初始化 Ollama
- ✅ 日志记录可用模型列表

---

## 3. 需要新增的功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 模型发现 | P1 | 自动检测本地可用模型，而非硬编码 qwen2:7b |
| 健康检查 | P1 | 定期检测 Ollama 服务状态，避免请求超时 |
| 自动 failover | P1 | Ollama 不可用时快速切换到云端模型 |
| 动态模型选择 | P2 | 根据任务类型自动选择最合适的本地模型 |
| 模型预热 | P2 | 启动时预加载常用模型到显存 |

---

## 4. 实现方案建议

### 4.1 模型发现（Model Discovery）
```python
# 在 router.py 初始化时调用
available_models = OllamaModel.list_models(base_url)
# 按 tier 映射创建多个模型实例
for model_info in available_models:
    tier = _infer_tier(model_info['name'])
    self._models['ollama'][tier] = OllamaModel(cfg, tier, model_info['name'])
```

### 4.2 健康检查（Health Check）
```python
class OllamaHealthChecker:
    async def check(self, base_url: str) -> HealthStatus:
        # 1. /api/tags 检测服务存活
        # 2. 记录响应时间
        # 3. 标记 unhealthy 后跳过该 provider
```

### 4.3 自动 Failover 优化
当前 router.py 的故障转移是顺序尝试，建议：
1. **快速失败**：Ollama 连接超时设为 2-3 秒（本地应很快）
2. **状态缓存**：维护 provider 健康状态，避免重复请求已挂服务
3. **异步预热**：启动时后台检测 Ollama，不阻塞其他模型初始化

### 4.4 代码改动点
```
src/core/router.py:
  - _initialize_models(): 遍历 list_models() 结果创建多 tier 实例
  - 新增 _health_check() 方法
  - route_and_call(): 优先检查健康状态

src/models/ollama.py:
  - 新增 health() 方法返回详细状态
  - 优化 is_available() 超时时间（3s → 2s）
```

---

## 5. 结论

当前 Ollama 集成已完成基础功能，**核心缺口**是：
1. 动态模型发现（而非固定 qwen2:7b）
2. 健康检查机制（避免超时等待）
3. 快速 failover（状态缓存 + 短超时）

建议优先级：健康检查 > 模型发现 > 自动 failover 优化。
