# 工作流

## 执行模式

oh-my-coder 支持三种执行模式：

### Sequential（顺序执行）

按顺序执行每个 Agent，上一个完成后再启动下一个。适合需要严格依赖链的任务。

```bash
omc run "实现一个 REST API" -m sequential
```

### Parallel（并行执行）

多个 Agent 同时工作，适合可以独立拆分子任务。

```bash
omc run "重构前端代码" -m parallel
```

### Auto（自动选择）

系统根据任务复杂度自动选择最合适的执行模式。

```bash
omc run "实现登录功能" -m auto  # 默认
```

## 任务流程

```
用户任务
  │
  ▼
 Explorer ──→ 分析项目结构、git 历史、工作目录上下文
  │
  ▼
 Analyst ──→ 理解需求、约束、依赖关系
  │
  ▼
 Planner ──→ 制定执行步骤、排序
  │
  ▼
 Architect ──→ 设计系统架构、选择技术栈
  │
  ▼
 Executor ──→ 生成代码
  │
  ▼
 Verifier ──→ 运行测试、验证正确性
  │
  ▼
 任务报告
```

## Quest Mode（异步自主编程）

Quest Mode 支持后台执行、实时通知，适合长时间任务。

```bash
# 启动后台任务
omc quest start "实现完整的用户系统"

# 查看状态
omc quest status <quest_id>

# 列出所有任务
omc quest list

# 取消任务
omc quest cancel <quest_id>
```

### SSE 实时推送

访问 `/api/agent/live` 获取 Agent 协作状态实时推送：

```bash
curl -N http://localhost:8000/api/agent/live
```
