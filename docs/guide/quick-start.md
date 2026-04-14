# 快速开始

## CLI 基本用法

### 探索项目

```bash
omc explore .          # 探索当前目录
omc explore /path/to/project
```

### 执行任务

```bash
omc run "实现一个 REST API"     # 单任务
omc run "实现登录功能" -m sequential  # 顺序执行
omc run "重构代码" -m parallel      # 并行执行
```

### Quest Mode（异步任务）

```bash
omc quest start "实现完整的用户系统"
# 后台执行，实时推送进度
omc quest status <quest_id>      # 查看状态
omc quest list                    # 查看所有任务
omc quest cancel <quest_id>       # 取消任务
```

### Agent 管理

```bash
omc agents              # 列出所有 Agent
omc agents --model deepseek-chat  # 指定模型
```

### Web 界面

```bash
python -m src.web.app
# 打开 http://localhost:8000
```

## 执行流程

```
用户输入任务
    │
    ▼
 Explorer → 分析项目结构、历史 git commit
    │
    ▼
 Analyst → 理解需求、发现隐藏约束
    │
    ▼
 Planner → 制定执行步骤
    │
    ▼
 Architect → 设计系统架构和技术选型
    │
    ▼
 Executor → 生成代码（14 种语言）
    │
    ▼
 Verifier → 运行测试、验证正确性
    │
    ▼
 输出结果 + 任务总结报告
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `omc explore <path>` | 探索项目结构 |
| `omc run <task>` | 执行任务 |
| `omc quest start <task>` | 后台任务 |
| `omc quest status <id>` | 查看任务状态 |
| `omc quest list` | 列出所有任务 |
| `omc agents` | 列出 Agent |
| `omc checkpoint save <msg>` | 保存检查点 |
| `omc checkpoint list` | 查看检查点 |

## 下一步

- [Agent 列表 →](agents.md)
- [执行模式 →](workflows.md)
- [CLI 详细参考 →](../api/cli.md)
