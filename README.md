# Oh My Coder

> 🤖 **31 个专业 Agent · 12 家国产大模型 · 自进化系统** — 国产首个多 Agent 编程框架，开箱即用。

🎯 **GLM-4.7-Flash 完全免费 · 一键 `pip install` 体验 · 无需翻墙 · 本地运行**

✨ **适合谁？** 国内开发者 / 需要免费 AI 编程助手 / 想要私有化部署的团队

[![PyPI version](https://img.shields.io/pypi/v/oh-my-coder?color=blue&label=PyPI)](https://pypi.org/project/oh-my-coder/)
[![PyPI downloads](https://img.shields.io/pypi/dm/oh-my-coder?color=green&label=Downloads)](https://pypi.org/project/oh-my-coder/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/VOBC/oh-my-coder?style=flat-square&logo=github)](https://github.com/VOBC/oh-my-coder/stargazers)
[![Tests](https://img.shields.io/github/actions/workflow/status/VOBC/oh-my-coder/test.yml?branch=main&label=Tests)](https://github.com/VOBC/oh-my-coder/actions)

**💡 灵感来源**: [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) (28.9k ⭐) — 我们为国内开发者提供零门槛替代方案

![Agent System](docs/screenshots/demo-agents.svg)

<!-- DEMO GIF 占位：P24 完成后替换为实际 GIF -->
<!-- 建议尺寸：800x450，展示 omc run 命令执行过程 -->

---

## ✨ 为什么选择 Oh My Coder？

| | Claude Code | Gemini CLI | **Oh My Coder** |
|---|---|---|---|
| **模型** | 仅 Claude（翻墙） | 仅 Gemini | **12 家国产模型** |
| **价格** | $25/月 | 免费 | **完全免费** |
| **国内可用** | ❌ 封号风险 | ❌ | **✅ 直连** |
| **Agent 数** | ~10 | — | **31 个专业 Agent** |
| **开源** | ❌ | 部分 | **MIT 完全开源** |
| **中文交互** | ❌ | ❌ | **✅ 全中文** |

> 💰 **零成本起步** — GLM-4.7-Flash 完全免费，注册即用，无需信用卡

---

## ⚡ 快速开始

### 安装

```bash
pip install oh-my-coder
```

### 配置（三选一，推荐 DeepSeek）

```bash
# DeepSeek（推荐，代码能力强）
omc config set -k DEEPSEEK_API_KEY -v "your_key"    # https://platform.deepseek.com/

# 智谱 GLM（完全免费，200K 上下文）
omc config set -k GLM_API_KEY -v "your_key"          # https://open.bigmodel.cn/
```

### 使用

```bash
# 开始编程
omc run "为用户模块添加 CRUD 接口"

# 代码审查
omc run "审查 src/api 目录" -w review

# 调试问题
omc run "修复登录接口超时" -w debug
```

---

## 🤖 31 个专业 Agent

![Architecture](docs/screenshots/demo-flow.svg)

覆盖完整开发生命周期的五大通道：

| 通道 | Agent | 职责 |
|------|-------|------|
| 🚀 **构建** | Explore → Analyst → Planner → Architect → Executor → Verifier | 探索 → 分析 → 设计 → 实现 → 验证 |
| 🔍 **审查** | CodeReviewer + SecurityReviewer | 质量审查 + 安全扫描 |
| 🎯 **领域** | TestEngineer / Designer / VisionAgent / GitMaster / DatabaseAgent … | 测试、设计、视觉、Git、数据库等 |
| 🧙 **协调** | PromptAgent + SelfImprovingAgent + SkillManageAgent + CriticAgent | 提示词优化 · 自我进化 · 经验沉淀 |
| 🛡️ **安全** | Debugger + Tracer + PerformanceAgent | 调试追踪 + 性能分析 |

> 📖 [完整 Agent 清单](docs/agents/agent-list.md)

---

## 🧙 Quest Mode — 异步自主编程

提交任务后自动执行，完成后通过钉钉/飞书/Telegram 通知：

```bash
omc run "实现用户认证模块" --quest
omc quest-list                          # 查看进度
omc quest-notify --dingtalk <webhook>   # 订阅通知
```

---

## 🔄 工作流

| 工作流 | 命令 | 流程 |
|--------|------|------|
| 🚀 构建 | `-w build` | 探索 → 分析 → 设计 → 实现 → 验证 |
| 🔍 审查 | `-w review` | CodeReview + SecurityReview |
| 🐛 调试 | `-w debug` | 追踪调用链 → 定位根因 → 修复验证 |
| 🧪 测试 | `-w test` | 分析函数 → 生成 pytest → 执行验证 |
| 🤖 自动 | `-w autopilot` | 根据任务关键词自动选择工作流 |

---

## 🧠 支持的模型（12 家）

| 模型 | 推荐度 | 免费额度 | 获取 Key |
|------|--------|----------|----------|
| **DeepSeek V3** | ⭐⭐⭐ | 新用户赠送 | [platform.deepseek.com](https://platform.deepseek.com/) |
| **GLM-4.7-Flash** | ⭐⭐⭐ | **完全免费** | [open.bigmodel.cn](https://open.bigmodel.cn/) |
| 通义千问 / Kimi / 豆包 / 天工 / 百川 / MiniMax / 星火 / 文心 / 混元 / MiMo | ⭐⭐ | 各有免费额度 | `omc config list-models` |

> 📖 [完整模型配置](docs/guide/model-config.md) | [免费模型推荐](docs/guide/free-models.md)

---

## 🌐 多平台 Gateway

内置消息网关，支持双向通信：

```bash
omc gateway start --telegram <token>
omc gateway start --discord <token>
```

支持 Telegram / Discord / WhatsApp / 飞书 / 企业微信 / 钉钉 / Slack

> 📖 [Gateway 文档](docs/guide/gateway.md)

---

## 🔒 安全特性

- **本地执行** — 代码本地运行，不上传云端
- **密钥安全** — API Key 仅存本地环境变量
- **安全审查** — SecurityReviewerAgent 自动扫描
- **Diff 预览** — GitMasterAgent 修改前预览变更
- **沙盒模式** — 支持隔离环境运行

---

## 📁 项目结构

```
oh-my-coder/
├── src/
│   ├── agents/          # 31 个 Agent（base.py + 各专业 Agent）
│   ├── core/            # 编排引擎 · 模型路由 · 任务总结
│   ├── models/          # 12 家模型适配层
│   ├── web/             # FastAPI Web 界面
│   ├── cli.py           # CLI 入口
│   └── main.py          # API 入口
├── tests/               # 730+ 测试用例
├── examples/            # 使用示例
└── docs/                # 详细文档
```

---

## 📖 更多文档

- [Claude Code 迁移指南](docs/guide/claude-migration.md)
- [Agent 完整清单](docs/agents/agent-list.md)
- [Quest Mode 文档](docs/features/quest-mode.md)
- [主动学习模块](docs/features/active-learning.md)
- [分层记忆系统](docs/guide/memory-system.md)
- [MCP Server 协议](docs/features/mcp-server.md)
- [工作目录上下文感知](docs/guide/workspace-context.md)

---

## 🤝 贡献

欢迎 PR！详见 [CONTRIBUTING.md](CONTRIBUTING.md)

1. Fork → 2. `git checkout -b feature/amazing-feature` → 3. Commit → 4. Push → 5. PR

- 🐛 [提交 Issue](https://github.com/VOBC/oh-my-coder/issues)
- 💬 [讨论区](https://github.com/VOBC/oh-my-coder/discussions)

---

## 📄 License

[MIT](LICENSE) · [VOBC/oh-my-coder](https://github.com/VOBC/oh-my-coder)

---

⭐ 如果觉得有用，请给项目一个 Star！

[![Star History](https://api.star-history.com/svg?repos=VOBC/oh-my-coder&type=Date&theme=dark)](https://star-history.com/#VOBC/oh-my-coder&Date)
