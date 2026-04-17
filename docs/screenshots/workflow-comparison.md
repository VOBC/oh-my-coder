# 工作流对比图

## 七种执行模式一览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Oh My Coder 7 种工作流                               │
└─────────────────────────────────────────────────────────────────────────────┘

① build      [开发流程]     explore → analyst → planner → architect → executor → verifier
② review     [审查流程]     explore → code-reviewer ─┬→ security-reviewer
                                                    └→ verifier
③ debug      [调试流程]     explore → debugger → verifier
④ test       [测试流程]     explore → test-engineer → executor → verifier
⑤ autopilot  [自动路由]    analyst（自动识别任务类型 → 路由到最合适的工作流）
⑥ pair       [结对编程]    explore → critic → explorer → critic → ...
⑦ refactor   [重构流程]    analyst → planner → code-simplifier → verifier → test-engineer
⑧ doc        [文档流程]    architect → writer → document → verifier  ← NEW!
⑨ sequential [顺序编排]    explore → analyst → planner → executor → verifier  ← NEW!
```

## 快速选择指南

```
任务类型                  推荐工作流              命令
─────────────────────────────────────────────────────────────────────
新功能开发                build                  omc run "..." -w build
代码审查                  review                 omc run "..." -w review
Bug 修复                  debug                  omc run "..." -w debug
写测试                    test                   omc run "..." -w test
不知道用什么              autopilot              omc run "..." -w autopilot
结对 Code Review          pair                   omc run "..." -w pair
重构优化                  refactor               omc run "..." -w refactor
生成技术文档              doc                    omc run "..." -w doc
深度定制顺序执行           sequential             omc run "..." -w sequential
```

## 各模式详解

### build — 开发流程
```
  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌───────────┐    ┌──────────┐    ┌───────────┐
  │ explore │───→│ analyst  │───→│ planner │───→│ architect │───→│ executor │───→│ verifier  │
  └─────────┘    └──────────┘    └─────────┘    └───────────┘    └──────────┘    └───────────┘
     探索           分析            规划           架构           执行            验证
```

### doc — 文档生成（新增）
```
  ┌───────────┐    ┌─────────┐    ┌───────────┐    ┌───────────┐
  │ architect │───→│ writer  │───→│ document  │───→│ verifier  │
  └───────────┘    └─────────┘    └───────────┘    └───────────┘
     架构设计         内容初稿        文档精修         完整性校验
```

### sequential — 顺序编排（新增）
```
  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐    ┌───────────┐
  │ explore │───→│ analyst  │───→│ planner │───→│ executor │───→│ verifier  │
  └─────────┘    └──────────┘    └─────────┘    └──────────┘    └───────────┘
     探索          深度分析         制定计划        执行实现        验证结果
```

### autopilot — 自动路由
```
  ┌──────────┐
  │ analyst   │  ← 自动识别任务关键词，路由到最适合的工作流
  └────┬─────┘
       │
       ├── bug/debug → "实现一个待办列表" ──→ refactor
       │                   
       ├── test   → "给这个项目写测试"  ──→ test
       │
       ├── review → "审查代码"           ──→ review
       │
       └── default → "实现新功能"       ──→ build
```

## 截图位置说明

| 文件名 | 内容 | 优先级 |
|--------|------|--------|
| `cli-help.png` | omc --help 主界面 | ⭐⭐⭐ |
| `cli-agents.png` | omc agents 31个Agent | ⭐⭐⭐ |
| `workflow-run.png` | omc run -w build 执行中 | ⭐⭐ |
| `quest-mode.png` | omc quest 异步编程 | ⭐⭐ |
| `doc-workflow.png` | omc run -w doc 文档生成 | ⭐⭐ |
| `multiagent.png` | omc multiagent 协作 | ⭐ |

> 📸 请将实际截图保存到本目录，替换上方占位说明
