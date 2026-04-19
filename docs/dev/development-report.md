# 中长期功能开发报告

> 日期: 2026-04-16

---

## 任务1: Web UI - Dashboard 可视化

### 完成状态: ✅ 已完成

### 新增文件

| 文件 | 功能 |
|------|------|
| `src/web/templates/settings.html` | 设置页面（模型选择、API Keys、偏好设置） |
| `src/web/local_models_api.py` | 本地模型 API（状态、列表、拉取） |

### 功能特性

1. **设置页面** (`/settings`)
   - 模型选择面板：显示本地模型和云端模型
   - API Keys 配置：DeepSeek, GLM, Kimi, 通义千问
   - 偏好设置：优先本地模型、默认工作流、超时时间

2. **本地模型检测**
   - 自动检测 Ollama 服务状态
   - 列出本地已安装的模型
   - 显示模型大小、Tier 信息

3. **界面预览**
   - 深色主题，VS Code 风格
   - 本地模型绿色徽章，云端模型蓝色
   - 实时 Toast 提示

---

## 任务2: 本地模型支持 (Ollama)

### 完成状态: ✅ 已完成

### 新增文件

| 文件 | 功能 |
|------|------|
| `src/models/ollama.py` | Ollama 模型适配器（~360行） |
| `src/cli_local_models.py` | 本地模型 CLI 命令 |
| 更新 `src/models/base.py` | 添加 OLLAMA 枚举 |
| 更新 `src/models/__init__.py` | 导出 OllamaModel |
| 更新 `src/core/router.py` | 添加 Ollama 配置和初始化 |
| 更新 `src/cli.py` | 注册 `omc local` 命令 |

### 功能特性

#### 1. OllamaModel 适配器

```python
# 使用示例
from src.models import OllamaModel, create_ollama_model

# 方式1: 直接创建
model = create_ollama_model("qwen2:7b", "http://localhost:11434")

# 方式2: 使用 Router
config = RouterConfig(
    prefer_local=True,
    ollama_base_url="http://localhost:11434",
    ollama_model="qwen2:7b",
)
router = ModelRouter(config)
```

#### 2. 支持的本地模型

| 模型 | 描述 | Tier |
|------|------|------|
| qwen2:1.5b | 通义千问 1.5B | LOW |
| qwen2:7b | 通义千问 7B | MEDIUM |
| qwen2:72b | 通义千问 72B | HIGH |
| llama3:8b | Llama 3 8B | LOW |
| mistral:7b | Mistral 7B | LOW |
| deepseek-coder:6.7b | DeepSeek Coder | MEDIUM |
| codellama:7b | Code Llama | MEDIUM |

#### 3. CLI 命令

```bash
# 检查 Ollama 状态
omc local status

# 列出可用模型
omc local list

# 拉取模型
omc local pull qwen2:7b

# 查看模型信息
omc local info qwen2:7b

# 启动 Ollama
omc local run
```

#### 4. 自动检测和 Fallback

- 启动时自动检测 Ollama 服务
- 本地服务不可用时自动切换云端
- 支持配置 `prefer_local` 控制优先级
- 环境变量: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `PREFER_LOCAL_MODEL`

---

## 运行方式

### 启动 Web UI

```bash
cd oh-my-coder
omc web
# 访问 http://localhost:8000/settings
```

### 使用本地模型

```bash
# 1. 安装 Ollama
# https://ollama.ai/

# 2. 拉取模型
ollama pull qwen2:7b

# 3. 运行 Oh My Coder（自动检测本地模型）
omc run "解释这段代码" --file example.py
```

---

## 测试结果

```
tests/ - 730 passed, 40 skipped
```

---

## 下一步计划

1. [ ] 添加更多本地模型支持（ Gemma, Mixtral）
2. [ ] 支持模型量化选择（Q4_K_M, Q5_K_S 等）
3. [ ] 添加 Web UI 模型对比功能
4. [ ] 完善本地模型文档
