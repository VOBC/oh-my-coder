# Oh My Coder (OMC 中文版)

> 🤖 多智能体 AI 编程助手，支持国内大模型

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**原项目**: [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) (17.8k ⭐)

---

## 🎯 项目简介

Oh My Coder 是一个**多智能体协作编程系统**，通过多个专业 Agent 协作完成复杂开发任务。

**核心优势：**
- 🧠 **智能路由** - 根据任务类型自动选择合适模型，节省 30-50% Token
- 🔄 **协作模式** - 多个 Agent 分工协作，像真实团队一样工作
- 🇨🇳 **中文优先** - 本土化设计，支持国内主流大模型
- ⚡ **成本优化** - 优先使用 DeepSeek 免费额度，几乎零成本

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd oh-my-coder
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# 设置 DeepSeek API Key（推荐，免费额度 4000 万 token/天）
export DEEPSEEK_API_KEY=your_key_here

# 可选：其他模型
export WENXIN_API_KEY=your_key      # 文心一言
export TONGYI_API_KEY=your_key      # 通义千问
export GLM_API_KEY=your_key         # ChatGLM
```

### 3. 运行

```bash
# 方式1: Web 界面（推荐，新手友好）
python -m src.web.app

# 然后浏览器打开: http://localhost:8000

# 方式2: CLI
python -m src.cli explore .                    # 探索代码库
python -m src.cli run "实现一个 REST API"      # 执行任务

# 方式3: API
python -m uvicorn src.main:app --reload        # 启动 API 服务
```

---

## 🌐 Web 界面

启动 Web 界面：

```bash
python -m src.web.app
```

浏览器打开 **http://localhost:8000**

### 功能特性

| 功能 | 说明 |
|------|------|
| 🎨 **可视化工作流** | 实时显示 Explore → Analyst → Architect → Executor → Verifier 流水线 |
| ⚡ **SSE 实时推送** | 无轮询，任务进度实时推送，毫秒级更新 |
| 📋 **多视图输出** | 每个 Agent 的输出独立展示，可随时切换查看 |
| 📊 **成本统计** | Token 消耗、执行时间、步骤完成情况一目了然 |
| 🌙 **深色模式** | 支持明暗主题切换 |
| 💡 **示例任务** | 内置 4 种常用任务模板，一键填入 |
| 🔄 **工作流选择** | 支持构建、审查、调试、测试等多种工作流 |

### API 端点

```
POST /api/execute        # 异步执行任务（SSE 实时推送进度）
POST /api/execute-sync   # 同步执行任务（直接返回结果）
GET  /api/tasks          # 列出所有任务
GET  /api/tasks/{id}     # 获取任务详情
GET  /sse/execute/{id}   # SSE 流，接收任务实时进度
GET  /health             # 健康检查
```

### 调用示例

```bash
# 异步执行（带 SSE 进度推送）
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "实现一个 REST API",
    "project_path": ".",
    "model": "deepseek",
    "workflow": "build"
  }'

# 同步执行（直接返回结果）
curl -X POST http://localhost:8000/api/execute-sync \
  -H "Content-Type: application/json" \
  -d '{
    "task": "审查当前项目的代码质量",
    "workflow": "review"
  }'
```

---

## 🤖 可用智能体

| Agent | 职责 | 模型层级 | 描述 |
|-------|------|----------|------|
| `explore` | 代码探索 | LOW | 快速扫描代码库，生成项目地图 |
| `analyst` | 需求分析 | HIGH | 深度理解需求，发现隐藏约束 |
| `architect` | 架构设计 | HIGH | 系统架构设计，技术选型 |
| `executor` | 代码实现 | MEDIUM | 代码编写，重构，Bug 修复 |

**模型层级说明：**
- **LOW** - 快速便宜（对应原项目 haiku）
- **MEDIUM** - 平衡性能和成本（对应 sonnet）
- **HIGH** - 最高质量推理（对应 opus）

---

## 🔄 工作流示例

### 完整开发流程

```bash
# 自动执行: explore → analyst → architect → executor
python -m src.cli run "实现一个用户认证系统" -w build
```

### 代码审查

```bash
python -m src.cli run "审查当前代码" -w review
```

### 调试问题

```bash
python -m src.cli run "修复登录功能的 Bug" -w debug
```

---

## 📁 项目结构

```
oh-my-coder/
├── src/
│   ├── agents/           # 智能体模块
│   │   ├── base.py       # Agent 基类
│   │   ├── explore.py    # 代码探索
│   │   ├── analyst.py    # 需求分析
│   │   ├── architect.py  # 架构设计
│   │   └── executor.py   # 代码实现
│   ├── core/             # 核心引擎
│   │   ├── router.py     # 模型路由器
│   │   └── orchestrator.py  # 编排引擎
│   ├── models/           # 模型适配器
│   │   ├── base.py       # 模型基类
│   │   └── deepseek.py   # DeepSeek 适配器
│   ├── web/              # Web 界面
│   │   ├── app.py        # FastAPI 应用
│   │   ├── templates/    # HTML 模板
│   │   └── static/       # CSS/JS 静态资源
│   ├── cli.py            # CLI 入口
│   └── main.py           # API 入口
├── tests/                # 测试
├── docs/                 # 文档
└── requirements.txt      # 依赖
```

---

## 🎨 核心设计

### 1. 三层模型路由

```
任务类型 → 模型层级 → 提供商选择

示例：
- 代码探索 (EXPLORE) → LOW tier → DeepSeek (免费)
- 架构设计 (ARCHITECTURE) → HIGH tier → DeepSeek (高质量)
- 代码生成 (CODE_GENERATION) → MEDIUM tier → DeepSeek (平衡)
```

### 2. Agent 协作流程

```
用户输入
    ↓
[explore] 探索代码库
    ↓
[analyst] 分析需求
    ↓
[architect] 设计架构
    ↓
[executor] 实现代码
    ↓
[verifier] 验证完成
```

### 3. 成本优化

- 优先使用 DeepSeek 免费额度（4000 万 token/天）
- 简单任务用 LOW tier，节省 Token
- 复杂任务才用 HIGH tier，保证质量

---

## 📊 开发进度

- [x] 核心架构设计
- [x] 模型适配层（DeepSeek）
- [x] Agent 基类和注册机制
- [x] 4 个核心 Agent（explore/analyst/architect/executor）
- [x] 编排引擎
- [x] CLI 入口
- [x] Web 界面
- [ ] 更多 Agent（debugger, reviewer, tester...）
- [ ] 其他模型适配器（文心/通义/GLM）
- [ ] 完整测试

---

## 🤝 贡献

欢迎贡献代码、提出问题或建议！

---

## 📄 License

MIT License

---

## 🙏 致谢

- 原项目 [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) 的启发
- DeepSeek 提供的免费 API
- 所有贡献者
