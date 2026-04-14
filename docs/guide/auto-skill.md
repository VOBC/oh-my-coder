# 自动生成 Skills

Oh My Coder 内置 **Self-Improving Agent**，能够从执行经验中自动提取最佳实践，生成可复用的 Skill。

## 概述

自动 Skills 机制的工作流程：

1. **收集反馈**：记录 Agent 执行的成功/失败案例
2. **识别模式**：分析重复出现的错误或成功模式
3. **生成 Skill**：提取为可复用的最佳实践文档
4. **自动升级**：将验证有效的 Skill 升级为 Tier 0 记忆

## 触发条件

Skill 自动生成在以下情况触发：

| 条件 | 说明 |
|------|------|
| 重复成功 | 同类任务连续成功 3 次以上 |
| 用户修正 | 用户提供了有效的修正建议 |
| 高频错误 | 同类错误出现 3 次以上 |
| 手动触发 | `omc skill create` 命令 |

## 自动生成的 Skill 结构

生成的 Skill 文件位于 `~/.omc/skills/auto/`：

```
~/.omc/skills/auto/
├── fastapi-dependency-injection.md
├── pytest-coverage-check.md
├── sql-injection-prevention.md
└── ...
```

**文件格式**：

```markdown
# [Skill Name]

> 自动生成于 YYYY-MM-DD
> 来源：[Agent 类型] 执行反馈

## 触发条件

- 任务类型：[描述]
- 关键词：[触发词列表]

## 最佳实践

1. [步骤 1]
2. [步骤 2]
3. [步骤 3]

## 示例代码

```python
# 示例代码（如果有）
```

## 相关错误

- [错误类型 1]：[解决方案]
- [错误类型 2]：[解决方案]

## 统计

- 成功应用：N 次
- 有效率：X%
```

## CLI 命令

### 手动创建 Skill

```bash
# 从最近执行反馈创建 Skill
omc skill create

# 从特定任务创建 Skill
omc skill create --from-task "Add authentication to API"

# 指定 Skill 名称
omc skill create --name "my-best-practice"
```

### 管理 Skills

```bash
# 列出所有 Skills
omc skill list

# 查看自动生成的 Skills
omc skill list --auto

# 搜索 Skill
omc skill search "FastAPI"

# 删除 Skill
omc skill delete "auto/fastapi-dependency-injection"
```

## Python API

```python
from agents import SelfImprovingAgent
from memory import SkillManager

# 创建 Agent
agent = SelfImprovingAgent()

# 记录执行反馈
agent.record_execution(
    agent_type="executor",
    task_description="Add authentication to FastAPI endpoint",
    success=True,
    execution_time=12.5
)

# 自动生成 Skill（满足条件时）
skill = agent.auto_create_skill(
    pattern_type="best-practice",
    min_success_count=3
)

if skill:
    print(f"Created: {skill.name}")
```

## Skill 层级

自动生成的 Skill 会经过验证流程：

| 层级 | 条件 | 说明 |
|------|------|------|
| Tier 2（Archive） | 新生成 | 所有自动 Skill 默认层级 |
| Tier 1（精选） | 应用 10 次以上 + 成功率 > 80% | 高价值 Skill |
| Tier 0（核心） | 应用 50 次以上 + 成功率 > 90% | 核心最佳实践 |

## 禁用自动 Skills

如果不需要自动生成，可以在配置中禁用：

```yaml
# ~/.omc/config.yaml
agents:
  self-improving:
    auto_skill_enabled: false
```

或者只禁用特定类型：

```yaml
agents:
  self-improving:
    auto_skill_enabled: true
    excluded_patterns:
      - "test-*"      # 排除测试相关
      - "temporary-*" # 排除临时任务
```

## 最佳实践

### 1. 命名规范

自动生成的 Skill 使用小写-连字符命名：

```
fastapi-dependency-injection.md
pytest-cov-coverage-check.md
sql-injection-prevention.md
```

### 2. 及时验证

自动 Skill 可能不完全准确，建议：

```bash
# 查看最近生成的 Skill
omc skill list --auto --recent

# 测试 Skill 是否有效
omc skill test "auto/my-skill"
```

### 3. 手动优化

对于重要的 Skill，可以手动优化后移到 `skills/` 目录：

```bash
# 编辑 Skill
nano ~/.omc/skills/auto/my-skill.md

# 移动到正式目录
mv ~/.omc/skills/auto/my-skill.md ~/.omc/skills/my-skill.md

# 刷新 Skill 索引
omc skill refresh
```

## 示例：自动生成的 Skill

```markdown
# pytest-coverage-check

> 自动生成于 2026-04-14
> 来源：executor 执行反馈

## 触发条件

- 任务类型：测试覆盖率检查
- 关键词：coverage, pytest, 测试覆盖

## 最佳实践

1. 使用 `pytest-cov` 插件
2. 设置覆盖率阈值（建议 80%）
3. 在 CI 中强制检查

## 示例代码

```bash
# 安装
pip install pytest-cov

# 运行
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

## 相关错误

- CoverageError: 覆盖率低于阈值 → 添加更多测试用例
- ModuleNotFoundError: 确保安装了 pytest-cov

## 统计

- 成功应用：15 次
- 有效率：93%
```

## 架构设计

```
agents/
└── self_improving.py
    ├── record_execution()    # 记录执行反馈
    ├── analyze_patterns()    # 分析失败模式
    └── auto_create_skill()   # 自动生成 Skill

memory/
└── skill_manager.py
    ├── create()              # 创建 Skill 文件
    ├── upgrade_tier()        # 升级 Skill 层级
    └── validate()            # 验证 Skill 有效性
```

## 下一步

- [分层记忆系统](./memory-system.md) - Skill 存储与检索
- [Checkpoint/Rollback](./checkpoint.md) - 状态保存与恢复
