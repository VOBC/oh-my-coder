---
title: Oh My Coder — 多智能体 AI 编程助手
description: 🤖 支持国内大模型、30 个专业 Agent、多 Agent 协作的 AI 编程框架
---

# Oh My Coder (OMC)

> 🤖 **多智能体 AI 编程助手 · 支持国内大模型 · 完全开源**

<!--
<style>
.hero { text-align: center; padding: 3rem 0; }
.hero h1 { font-size: 3rem; color: #3f51b5; }
</style>
-->

<div class="hero">

**GLM-4-Flash 永久免费 · 11 家国产模型 · 30 个专业 Agent · 多 Agent 协作 · MIT 开源**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/VOBC/oh-my-coder/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/VOBC/oh-my-coder?style=flat-square)](https://github.com/VOBC/oh-my-coder/stargazers)

</div>

## 核心特性

| 特性 | 说明 |
|------|------|
| **国产模型支持** | 11 家国内模型，GLM-4-Flash 永久免费 |
| **30 个专业 Agent** | Explore、Analyze、Code、Review、Debug、Test 等分工协作 |
| **多 Agent 协作** | Build / Review / Domain / Coordinate 四通道编排 |
| **Quest Mode** | 后台异步任务 + 实时进度推送 |
| **GEP 协议** | 结构化输出（Gene/Capsule）保证 Agent 间可靠通信 |
| **上下文感知** | 自动读取项目结构、历史 git commit，自主理解工作目录 |
| **主动学习** | 每次执行后自我反思，优化路由策略 |

## 效果预览

```
$ omc run "实现一个 REST API"

🤖 [Explorer] 扫描项目结构... ✅
🤖 [Analyst]  理解需求约束...  ✅
🤖 [Planner]  制定执行计划...  ✅
🤖 [Architect] 设计 API 架构... ✅
🤖 [Executor] 生成代码...      ✅
🤖 [Verifier] 运行测试...      ✅

✨ 完成！生成了 src/api/rest.py + tests/test_rest.py
```

## 安装

=== "DeepSeek（推荐）"

    ```bash
    git clone https://github.com/VOBC/oh-my-coder.git
    cd oh-my-coder
    pip install -e .
    export DEEPSEEK_API_KEY=sk-xxxxx
    omc explore .          # 探索当前项目
    omc run "实现一个 REST API"   # 执行任务
    ```

=== "GLM（免费）"

    ```bash
    export GLM_API_KEY=your_key_here
    omc explore .
    ```

## 与同类工具对比

| 工具 | 价格 | 开源 | 国内可用 | 多 Agent |
|------|------|------|----------|----------|
| **oh-my-coder** | **免费** | ✅ MIT | ✅ | ✅ 30 |
| oh-my-claudecode | $25/月 | ✅ | ❌ | ✅ 32 |
| Cursor | $20/月 | ❌ | ⚠️ | ❌ |
| GitHub Copilot | $19/月 | ❌ | ⚠️ | ❌ |
| 腾讯云 CodeBuddy | 免费 | ❌ | ✅ | ❌ |

## 下一步

- [快速开始 →](guide/quick-start.md)
- [安装指南 →](guide/install.md)
- [Agent 系统 →](guide/agents.md)
- [CLI 命令 →](api/cli.md)

---

*[MIT License](https://github.com/VOBC/oh-my-coder/blob/main/LICENSE) · GitHub: [VOBC/oh-my-coder](https://github.com/VOBC/oh-my-coder)*
