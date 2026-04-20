# 🧠 主动学习模块

> 本文从 README.md 迁移而来。

## 🧠 主动学习模块

Oh My Coder 内置**主动学习**能力，可以从执行结果中学习并优化策略。

### 功能

| 模块 | 说明 |
|------|------|
| **反馈收集** | 收集成功/失败/用户修正反馈 |
| **模式分析** | 分析失败类型（理解错误、执行错误、验证错误） |
| **策略适配** | 根据模式类型推荐不同策略 |
| **提示词调优** | 根据反馈自动调整 Agent system prompt |
| **Skill 自进化** | 工作流完成后自动将经验沉淀为 `.omc/skills/` Skill 文件 |

### Skill 自进化系统

每次工作流完成后，Oh My Coder 自动评估是否值得沉淀经验：

**触发条件（满足任一）：**
- 工具调用 ≥5 次且成功
- 错误 → 解决
- 用户纠正
- 非平凡工作流（≥3 步骤）

**Skill 文件结构：**
```
.omc/skills/
├── index.json           # 全量索引
├── debugging/           # 调试经验（bug fix、troubleshooting）
│   └── sql-slow-fix/
│       └── SKILL.md    # YAML frontmatter + Markdown 正文
├── workflow/           # 工作流经验
├── corrections/        # 被纠正后的修复
└── best-practices/     # 最佳实践
```

**Tier 0 自动注入：** 所有 Agent 执行前，Orchestrator 自动读取 `index.json`，将所有 Skill 的名字+描述追加到系统 Prompt 底部（~500 token），让 Agent 知道有哪些经验可用。

**CRUD 工具：** `skill-manage` Agent 支持 create / patch / delete / list / search 操作，patch 优先于 create。

```python
from src.memory.skill_manager import SkillManager

sm = SkillManager()

# 创建 Skill
sm.create(name="SQL 慢查询修复", body="# 正文...", category="debugging",
          tags=["sql", "performance"], triggers=["查询慢"])

# patch（优先）
sm.patch(skill_id="sql-slow-fix", body="更新后的正文...")

# 搜索
results = sm.search("sql 慢查询")
```

数据存储在 `~/.omc/` 目录。

---

> 📖 详细文档：[主动学习模块](docs/SELF_IMPROVING.md)

---

