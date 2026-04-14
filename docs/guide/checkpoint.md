# Checkpoint & Rollback

Oh My Coder 提供 Checkpoint 机制，支持在关键节点保存工作状态，出错时快速回滚。

## 概述

Checkpoint 模块提供：

- **状态快照**：保存代码、配置、环境状态
- **差异对比**：查看当前状态与 Checkpoint 的差异
- **一键回滚**：恢复到任意 Checkpoint

## 使用场景

| 场景 | 说明 |
|------|------|
| 重构前 | 创建 Checkpoint，重构失败时回滚 |
| 实验性修改 | 尝试新方案，保留回退路径 |
| 多方案对比 | 创建多个 Checkpoint，快速切换 |
| 定时备份 | 自动创建 Checkpoint，防止意外丢失 |

## CLI 命令

### 创建 Checkpoint

```bash
# 创建 Checkpoint（自动命名）
omc checkpoint create

# 创建命名 Checkpoint
omc checkpoint create "before-refactor"

# 创建带描述的 Checkpoint
omc checkpoint create "v1.0" --desc "重构前的稳定版本"
```

### 查看 Checkpoint

```bash
# 列出所有 Checkpoint
omc checkpoint list

# 查看 Checkpoint 详情
omc checkpoint show "before-refactor"

# 查看当前状态与 Checkpoint 的差异
omc checkpoint diff "before-refactor"
```

### 回滚

```bash
# 回滚到指定 Checkpoint
omc checkpoint rollback "before-refactor"

# 强制回滚（不确认）
omc checkpoint rollback "before-refactor" --force
```

### 删除 Checkpoint

```bash
# 删除单个 Checkpoint
omc checkpoint delete "v1.0"

# 清理旧 Checkpoint（保留最近 10 个）
omc checkpoint clean --keep 10
```

## Python API

```python
from checkpoint import CheckpointManager

# 创建管理器
manager = CheckpointManager(project_path)

# 创建 Checkpoint
cp = manager.create(
    name="before-refactor",
    description="重构前的稳定版本"
)
print(f"Created: {cp.id} at {cp.timestamp}")

# 列出 Checkpoint
checkpoints = manager.list()
for cp in checkpoints:
    print(f"- {cp.name}: {cp.timestamp}")

# 查看差异
diff = manager.diff("before-refactor")
print(diff)  # Git-style diff

# 回滚
manager.rollback("before-refactor")

# 删除
manager.delete("before-refactor")
```

## Checkpoint 内容

每个 Checkpoint 包含：

| 内容 | 说明 |
|------|------|
| Git 状态 | 当前分支、未提交的更改 |
| 文件快照 | 修改过的文件内容 |
| 环境配置 | `.env` 文件（不含敏感信息） |
| 项目元数据 | `pyproject.toml`、`package.json` 等 |
| 自定义数据 | 用户指定的额外文件 |

## 配置

```yaml
# .omc/checkpoint.yaml
retention_days: 30      # Checkpoint 保留天数
max_checkpoints: 50     # 最大 Checkpoint 数量
auto_checkpoint: true   # 任务执行前自动创建
exclude:
  - "*.pyc"
  - "__pycache__"
  - ".venv"
  - "node_modules"
```

## 最佳实践

### 1. 重构前创建 Checkpoint

```bash
# 创建带描述的 Checkpoint
omc checkpoint create "before-auth-refactor" --desc "认证模块重构前"

# 执行重构...

# 如果重构成功，删除 Checkpoint
omc checkpoint delete "before-auth-refactor"

# 如果重构失败，回滚
omc checkpoint rollback "before-auth-refactor"
```

### 2. 多方案对比

```bash
# 方案 A
omc checkpoint create "approach-a"
# ... 实现方案 A ...

# 方案 B
omc checkpoint create "approach-b"
# ... 实现方案 B ...

# 对比后选择方案 A
omc checkpoint rollback "approach-a"
omc checkpoint delete "approach-b"
```

### 3. 定时自动备份

在 CI/CD 或 Cron 中配置：

```bash
# 每天凌晨 2 点创建 Checkpoint
0 2 * * * cd /path/to/project && omc checkpoint create "daily-$(date +\%Y\%m\%d)"
```

## 与 Git 的区别

| 特性 | Git | Checkpoint |
|------|-----|------------|
| 粒度 | Commit 级别 | 工作目录级别 |
| 未提交更改 | 不保存 | 保存 |
| 回滚速度 | 需要 stash/reset | 一键恢复 |
| 描述信息 | Commit message | 自定义描述 |
| 适用场景 | 版本控制 | 临时备份/实验 |

**建议**：Checkpoint 用于短期临时备份，Git 用于长期版本控制。两者结合使用。

## 注意事项

1. **磁盘空间**：Checkpoint 会复制修改过的文件，注意磁盘空间
2. **敏感信息**：`.env` 中的敏感信息会被排除（只保留 key，不保留 value）
3. **大文件**：大文件（如数据集、模型文件）默认排除
4. **并发**：不要同时创建多个 Checkpoint（可能导致不一致）

## 下一步

- [分层记忆系统](./memory-system.md) - 项目偏好与学习记录
- [自动 Skills](./auto-skill.md) - 从经验自动生成 Skill
