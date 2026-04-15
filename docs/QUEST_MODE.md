# Quest Mode — 异步自主编程

## 概述

Quest Mode 是 Oh My Coder 的核心特色功能，支持你描述需求后 Agent 在后台自主完成编码任务。

## 工作流程

```
描述需求 → 生成 Spec → 后台自主编码 → 完成通知 → 用户验收
```

## 使用方式

```bash
# 创建并启动任务
oh-my-coder quest "实现用户认证模块，支持 JWT + 刷新令牌"

# 查看任务状态
oh-my-coder quest status

# 暂停任务
oh-my-coder quest pause

# 继续任务
oh-my-coder quest continue

# 验收步骤
oh-my-coder quest verify
```

## 核心机制

### Spec 自动生成

QuestAgent 会将你的自然语言需求自动拆解为结构化 Spec：
- 任务目标
- 技术方案
- 实现步骤
- 验收标准

### 后台自主编码

任务启动后，Orchestrator 编排多个 Agent 按步骤执行：
1. **Planner** — 生成实现计划
2. **Architect** — 设计模块结构
3. **Executor** — 编写代码
4. **Verifier** — 运行测试验证
5. **Debugger** — 修复发现的问题

### 交互式验收

每一步完成后，你可以选择：
- ✅ 通过 — 继续下一步
- 🔄 重试 — 重新执行当前步骤
- ⏭ 跳过 — 跳过当前步骤

### 通知机制

任务完成或出现错误时，通过以下方式通知你：
- 桌面通知
- 钉钉 Webhook
- 终端输出
