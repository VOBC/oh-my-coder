# 能力包（Capability Pack）

能力包是 oh-my-coder 的经验沉淀系统，让 Agent 从历史执行中学习。

## 工作原理

```
每次工作流完成
      │
      ▼
 自动评估：是否值得沉淀经验？
      │
 工具调用 ≥5 次
 或 错误 → 解决
 或 用户纠正
 或 ≥3 步骤
      │
      ▼
 生成 Skill 文件
 .omc/skills/<category>/<name>/SKILL.md
      │
      ▼
 Tier 0 自动注入
 Agent 执行前读取 index.json，
 将所有 Skill 追加到系统 Prompt
```

## Skill 文件结构

```
.omc/skills/
├── index.json              # 全量索引
├── debugging/              # 调试经验
│   └── sql-slow-fix/
│       └── SKILL.md       # YAML frontmatter + 正文
├── workflow/               # 工作流经验
├── corrections/           # 被纠正后的修复
└── best-practices/        # 最佳实践
```

## Skill CRUD

```python
from src.memory.skill_manager import SkillManager

sm = SkillManager()

# 创建
sm.create(
    name="SQL 慢查询修复",
    body="# 正文...",
    category="debugging",
    tags=["sql", "performance"],
    triggers=["查询慢"]
)

# Patch（优先于 create）
sm.patch(skill_id="sql-slow-fix", body="更新后的正文...")

# 搜索
results = sm.search("sql 慢查询")

# 列出
sm.list(category="debugging")

# 删除
sm.delete(skill_id="sql-slow-fix")
```

## Tier 0 自动注入

所有 Agent 执行前，Orchestrator 自动：

1. 读取 `.omc/skills/index.json`
2. 将所有 Skill 的名字+描述追加到系统 Prompt 底部（~500 token）
3. Agent "知道" 有哪些历史经验可用

## 数据位置

```
~/.omc/
├── skills/         # 能力包数据
│   └── index.json
└── memory/         # 对话记忆
```
