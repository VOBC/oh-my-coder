# 快速入门

> 5 分钟上手 Oh My Coder

---

## 📦 安装

### 方式一：pip 安装（推荐）

```bash
# 克隆项目
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder

# 安装依赖
pip install -e .
```

### 方式二：开发模式安装

```bash
pip install -e '.[dev]'
```

这会额外安装测试和开发工具：`pytest`、`ruff`、`black`。

---

## 🔑 配置 API Key

### 最小配置（DeepSeek）

DeepSeek 提供免费额度，性价比最高，推荐作为入门首选。

```bash
export DEEPSEEK_API_KEY=your_deepseek_key
```

获取 API Key：https://platform.deepseek.com/

### 多模型配置

```bash
# 智谱 GLM（推荐第二选择）
export GLM_API_KEY=your_glm_key

# 通义千问
export TONGYI_API_KEY=your_tongyi_key

# Kimi （128K 长上下文）
export KIMI_API_KEY=your_kimi_key
```

---

## 🚀 基本使用

### CLI 命令

```bash
# 查看版本
omc --version

# 查看帮助
omc --help

# 查看所有 Agent
omc agents

# 查看系统状态
omc status
```

### 执行任务

```bash
# 简单任务
omc run "为 utils.py 添加类型注解"

# 指定工作流
omc run "实现用户认证模块" -w build

# 代码审查
omc run "审查 src/api 目录" -w review

# Bug 修复
omc run "修复登录接口空指针异常" -w debug

# 生成测试
omc run "为 src/core 生成单元测试" -w test
```

### 工作流类型

| 工作流 | 用途 | Agent 序列 |
|--------|------|-----------|
| `build` | 构建新功能 | explore → analyst → planner → architect → executor → verifier |
| `review` | 代码审查 | explore → code-reviewer → security-reviewer |
| `debug` | 调试修复 | explore → tracer → debugger → verifier |
| `test` | 测试生成 | explore → test-engineer → verifier |

---

## 🌐 Web 界面

### 启动 Web 服务

```bash
omc web
```

访问 http://localhost:8000

### Web API 调用

```bash
# 异步执行（SSE 流式返回）
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "实现 REST API", "workflow": "build"}'

# 同步执行
curl -X POST http://localhost:8000/api/execute-sync \
  -H "Content-Type: application/json" \
  -d '{"task": "审查代码质量", "workflow": "review"}'

# 查看任务列表
curl http://localhost:8000/api/tasks

# 健康检查
curl http://localhost:8000/health
```

---

## 🤖 Agent 介绍

Oh My Coder 有 18 个专业 Agent，分工协作完成复杂任务。

### 构建类 Agent（BUILD）

| Agent | 层级 | 职责 |
|-------|------|------|
| **explore** | LOW | 探索项目结构，识别技术栈 |
| **analyst** | HIGH | 分析需求，识别实体和关系 |
| **planner** | HIGH | 制定任务计划，拆解步骤 |
| **architect** | HIGH | 设计架构，制定技术方案 |
| **executor** | MEDIUM | 执行代码实现 |
| **verifier** | MEDIUM | 验证测试，确保质量 |
| **debugger** | MEDIUM | 调试修复问题 |
| **tracer** | MEDIUM | 追踪问题根因 |

### 审查类 Agent（REVIEW）

| Agent | 层级 | 职责 |
|-------|------|------|
| **code-reviewer** | MEDIUM | 代码质量审查 |
| **security-reviewer** | HIGH | 安全漏洞审查 |

### 领域类 Agent（DOMAIN）

| Agent | 层级 | 职责 |
|-------|------|------|
| **test-engineer** | MEDIUM | 测试工程 |
| **designer** | MEDIUM | UI/UX 设计 |
| **writer** | LOW | 文档编写 |
| **git-master** | LOW | Git 操作 |
| **code-simplifier** | MEDIUM | 代码简化重构 |
| **scientist** | HIGH | 数据分析 |
| **qa-tester** | MEDIUM | QA 测试 |

### 协调类 Agent（COORDINATION）

| Agent | 层级 | 职责 |
|-------|------|------|
| **critic** | HIGH | 审查计划，提出改进建议 |

---

## 💡 使用技巧

### 1. 选择合适的工作流

```bash
# 新功能开发 → build
omc run "实现商品搜索功能" -w build

# 代码质量检查 → review
omc run "检查代码规范" -w review

# 问题排查 → debug
omc run "排查内存泄漏" -w debug
```

### 2. 任务描述要清晰

```bash
# ❌ 模糊
omc run "改一下代码"

# ✅ 清晰
omc run "为 UserService 添加密码加密功能，使用 bcrypt 算法"
```

### 3. 利用项目上下文

```bash
# 先探索项目
omc explore .

# 再执行任务（Agent 会利用探索结果）
omc run "为现有 API 添加缓存" -w build
```

### 4. 查看执行报告

每次任务完成后会生成报告：

```
reports/
├── task_20260408_123456.json  # JSON 格式（机器解析）
├── task_20260408_123456.html  # HTML 格式（分享报告）
└── task_20260408_123456.txt   # TXT 格式（快速查看）
```

---

## ❓ 常见问题

### Q: 没有 API Key 怎么办？

A: 推荐使用 DeepSeek，注册即送免费额度：
https://platform.deepseek.com/

### Q: 支持哪些模型？

A: 支持 11 家国产大模型：
- DeepSeek（推荐）
- 智谱 GLM
- 通义千问
- 文心一言
- Kimi 
- 腾讯混元
- 字节豆包
- MiniMax
- 天工 AI
- 讯飞星火
- 百川智能

### Q: 如何选择模型？

A: 系统会自动选择，规则如下：
- 探索任务 → 低成本模型
- 架构设计 → 高能力模型
- 代码生成 → 中等模型

### Q: 执行失败怎么办？

A: 检查以下几点：
1. API Key 是否正确配置
2. 网络是否正常
3. 查看错误日志定位问题

---

## 📚 下一步

- [进阶教程](./tutorials.md) - 深入学习多 Agent 协作
- [API 文档](../API.md) - 完整 API 参考
- [架构设计](../ARCHITECTURE.md) - 了解系统架构
- [FAQ](../FAQ.md) - 更多常见问题
