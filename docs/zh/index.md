# 中文文档

欢迎使用 Oh My Coder 中文文档！

## 目录

- [快速开始 →](getting-started.md)
- [教程 →](tutorials.md)

## 项目简介

Oh My Coder（OMC）是一个**多智能体 AI 编程助手**，支持 12 家国内大模型、30 个专业 Agent、多 Agent 协作。

### 核心特点

- 🤖 **30 个专业 Agent**：Explore、Analyze、Code、Review、Debug、Test 等分工协作
- 🌐 **国产模型支持**：DeepSeek、GLM、文心、通义、Kimi、混元、MiMo 等 12 家
- 💰 **永久免费**：GLM-4-Flash 永久免费，DeepSeek 性价比极高
- 🔄 **多 Agent 协作**：Build / Review / Domain / Coordinate 四通道编排
- 🧙 **Quest Mode**：后台异步任务，实时推送进度
- 📚 **主动学习**：从执行结果中学习，优化路由策略
- 🔒 **安全优先**：危险命令拦截、沙箱执行、审计日志

## 安装

```bash
git clone https://github.com/VOBC/oh-my-coder.git
cd oh-my-coder
pip install -e .
export DEEPSEEK_API_KEY=sk-xxxxx
```

## 快速体验

```bash
omc explore .              # 探索当前项目
omc run "实现一个 REST API" # 执行任务
python -m src.web.app      # 启动 Web 界面
```

## 文档导航

| 文档 | 说明 |
|------|------|
| [快速开始](getting-started.md) | 从零开始，5 分钟上手 |
| [教程](tutorials.md) | 常见场景实战教程 |
| [安装指南](../guide/install.md) | 详细安装步骤 |
| [Agent 系统](../guide/agents.md) | 30 个 Agent 详细介绍 |
| [CLI 参考](../api/cli.md) | 命令行详细文档 |
