# Oh My Coder (OMC 中文版)

> 🤖 多智能体 AI 编程助手，支持国内大模型

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/VOBC/oh-my-coder?style=flat-square&logo=github)](https://github.com/VOBC/oh-my-coder/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/VOBC/oh-my-coder?style=flat-square&logo=github)](https://github.com/VOBC/oh-my-coder/commits)
[![Issues](https://img.shields.io/github/issues/VOBC/oh-my-coder?style=flat-square&logo=github)](https://github.com/VOBC/oh-my-coder/issues)

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
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# DeepSeek API Key（推荐，免费额度高）
export DEEPSEEK_API_KEY=your_key_here

# 可选：其他模型
export WENXIN_API_KEY=your_key      # 文心一言
export TONGYI_API_KEY=your_key      # 通义千问
```

### 3. 运行

```bash
# 🌐 Web 界面（推荐，新手友好）
python -m src.web.app
# 浏览器打开: http://localhost:8000

# 💻 CLI
python -m src.cli explore .
python -m src.cli run "实现一个 REST API"
```

---

## 🌐 Web 界面预览

启动后访问 **http://localhost:8000**：

| 功能 | 说明 |
|------|------|
| 🎨 **可视化工作流** | 实时显示 Explore → Analyst → Architect → Executor → Verifier 流水线动画 |
| ⚡ **SSE 实时推送** | 无轮询，任务进度毫秒级更新 |
| 📋 **多视图输出** | 每个 Agent 的输出独立标签页，随时切换 |
| 📊 **成本统计** | Token 消耗、执行时间、步骤完成情况 |
| 🌙 **深色模式** | 明暗主题一键切换 |
| 💡 **示例任务** | 内置 4 种任务模板，一键填入 |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/execute` | 异步执行（SSE 实时推送） |
| `POST` | `/api/execute-sync` | 同步执行（直接返回结果） |
| `GET` | `/api/tasks` | 列出所有任务 |
| `GET` | `/api/tasks/{id}` | 获取任务详情 |
| `GET` | `/sse/execute/{id}` | SSE 流，接收实时进度 |
| `GET` | `/health` | 健康检查 |

### curl 调用示例

```bash
# 异步执行（带 SSE 进度）
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "实现一个 REST API", "workflow": "build"}'

# 同步执行（直接返回）
curl -X POST http://localhost:8000/api/execute-sync \
  -H "Content-Type: application/json" \
  -d '{"task": "审查代码质量", "workflow": "review"}'
```

---

## 🤖 可用智能体

| Agent | 职责 | 模型层级 | 描述 |
|-------|------|----------|------|
| `explore` | 代码探索 | LOW | 快速扫描代码库，生成项目地图 |
| `analyst` | 需求分析 | HIGH | 深度理解需求，发现隐藏约束 |
| `architect` | 架构设计 | HIGH | 系统架构设计，技术选型 |
| `executor` | 代码实现 | MEDIUM | 代码编写，重构，Bug 修复 |
| `verifier` | 验证测试 | MEDIUM | 质量保证，验证完成 |

**模型层级说明：**
- **LOW** - 快速便宜（对应 haiku）
- **MEDIUM** - 平衡性能和成本（对应 sonnet）
- **HIGH** - 最高质量推理（对应 opus）

---

## 🔄 工作流

| 工作流 | 命令 | 说明 |
|--------|------|------|
| 🚀 `build` | `-w build` | 完整开发流程：探索 → 分析 → 设计 → 实现 → 验证 |
| 🔍 `review` | `-w review` | 代码审查 + 安全审查 |
| 🐛 `debug` | `-w debug` | 问题定位 → 修复 → 验证 |
| 🧪 `test` | `-w test` | 设计测试 → 实现测试 → 运行验证 |

---

## 📁 项目结构

```
oh-my-coder/
├── src/
│   ├── agents/              # 智能体模块（18 个 Agent）
│   │   ├── base.py          # Agent 基类 & 注册机制
│   │   ├── explore.py       # 代码探索
│   │   ├── analyst.py       # 需求分析
│   │   ├── architect.py     # 架构设计
│   │   ├── executor.py      # 代码实现
│   │   └── ...
│   ├── core/                # 核心引擎
│   │   ├── router.py        # 三层模型路由器
│   │   └── orchestrator.py  # 智能编排引擎
│   ├── models/              # 模型适配层
│   │   ├── base.py          # 统一接口
│   │   ├── deepseek.py      # DeepSeek 适配器
│   │   ├── wenxin.py        # 文心一言
│   │   └── tongyi.py        # 通义千问
│   ├── web/                 # 🌐 Web 界面
│   │   ├── app.py           # FastAPI 应用 + SSE
│   │   ├── templates/       # HTML 模板
│   │   └── static/          # CSS 样式
│   ├── cli.py               # CLI 入口
│   └── main.py              # API 入口
├── tests/                   # 测试套件
│   ├── test_web.py          # Web 界面测试
│   └── test_integration.py   # 集成测试
├── examples/                # 示例代码
│   ├── web_demo.py          # Web API 使用示例
│   └── cli_demo.py          # CLI 使用示例
├── docs/                    # 文档
├── requirements.txt         # 依赖
└── pyproject.toml          # 项目配置
```

---

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行指定测试
pytest tests/test_web.py -v

# 带覆盖率
pytest --cov=src --cov-report=html

# 仅 Web 界面测试
pytest tests/test_web.py -v

# 仅集成测试
pytest tests/test_integration.py -v
```

---

## 🎨 核心设计

### 三层模型路由

```
任务类型 → 模型层级 → 提供商选择
  EXPLORE    LOW       DeepSeek (免费)
  ARCHITECT  HIGH      DeepSeek (高质量)
  CODE_GEN   MEDIUM    DeepSeek (平衡)
```

### Agent 协作流程

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

---

## 📊 开发进度

- [x] 核心架构设计
- [x] 模型适配层（DeepSeek / 文心 / 通义）
- [x] Agent 基类和注册机制
- [x] 核心 Agent（explore/analyst/architect/executor/verifier）
- [x] 编排引擎（顺序/并行/条件执行）
- [x] CLI 入口
- [x] Web 界面（SSE 实时推送）
- [x] 测试套件
- [x] 示例代码
- [ ] 更多 Agent（debugger, reviewer, tester 完善）
- [ ] 完整测试覆盖
- [ ] Docker 部署

---

## 🤝 贡献

欢迎提交 Issue 和 PR！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) 的启发
- [DeepSeek](https://platform.deepseek.com/) 提供的免费 API
- 所有贡献者
