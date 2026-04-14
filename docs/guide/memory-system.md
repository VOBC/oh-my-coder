# 分层记忆系统

Oh My Coder 采用**分层有限记忆**架构，借鉴 Hermes Agent 设计，在不同上下文窗口限制下提供最优记忆注入。

## 设计理念

LLM 的上下文窗口有限（4K-200K token），无法无限加载历史记忆。分层有限记忆通过优先级划分，确保最重要的信息始终可用：

- **Tier 0**：核心记忆，< 500 token，系统 Prompt 注入
- **Tier 1**：精选记忆，< 2000 token，上下文补充
- **Tier 2**：完整存档，无限制，按需搜索

## 架构概览

```
MemoryManager
├── ShortTermMemory    # 短期会话记忆（当前任务）
├── LongTermMemory     # 长期记忆（项目偏好、用户设置）
└── LearningsMemory    # 学习记忆（经验、教训）

分层视图：
├── Tier 0 (Tiny)      # < 500 token，核心记忆
├── Tier 1 (精选)      # < 2000 token，高价值条目
└── Tier 2 (Archive)   # 完整存档，无限存储
```

## Tier 0：核心记忆

**用途**：注入到系统 Prompt，每个请求都携带。

**内容**：
- 最近项目（3 个）
- 用户核心偏好（模型、工作流）
- 最近学习经验（3 条）

**使用示例**：

```python
from memory import MemoryManager

mm = MemoryManager.from_project(project_path)

# 获取 Tier 0 摘要（< 500 token）
tier0 = mm.get_tier0_summary()

# 注入到 Prompt
system_prompt = f"""
你是一个代码助手。

## 核心记忆
{tier0}

请根据以上上下文回答用户问题。
"""
```

**输出示例**：

```
## 最近项目
- my-project: Python/FastAPI
- web-app: React/Next.js
- cli-tool: Python/Typer

## 用户偏好
- 模型: deepseek
- 工作流: tdd

## 最近经验
- 使用 pytest-cov 检查覆盖率: 测试覆盖率应 > 80%
- FastAPI 依赖注入: 使用 Depends() 进行依赖注入
- SQL 注入防护: 永远使用参数化查询
```

## Tier 1：精选记忆

**用途**：补充上下文，在 token 充裕时提供更多项目细节。

**内容**：
- 项目详情（5 个）
- 项目特定知识
- 常用命令
- 更多学习记录（10 条）

**使用示例**：

```python
# 获取 Tier 1 摘要（< 2000 token）
tier1 = mm.get_tier1_summary(max_tokens=2000)

# 在多轮对话中作为历史补充
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"参考以下项目信息：\n{tier1}\n\n问题：..."}
]
```

## Tier 2：完整存档

**用途**：导出、搜索、审计，无 token 限制。

**内容**：
- 完整用户偏好
- 所有项目详情（20 个）
- 所有学习记录（50 条）

**使用示例**：

```python
# 获取完整存档
archive = mm.get_tier2_archive()

# 搜索
results = mm.recall("FastAPI")

# 按类别获取学习记录
errors = mm.get_learnings_by_category("error")
best_practices = mm.get_learnings_by_category("best-practice")
```

## CLI 命令

```bash
# 查看记忆统计
omc memory stats

# 查看核心记忆（Tier 0）
omc memory core

# 查看精选记忆（Tier 1）
omc memory selected

# 查看完整存档（Tier 2）
omc memory archive

# 搜索记忆
omc memory search "FastAPI"

# 添加学习记录
omc memory add "SQL 注入防护" "永远使用参数化查询" --category error
```

## 记忆类型

### ShortTermMemory（短期会话）

- 存储当前任务的上下文
- 自动过期（默认 24 小时）
- 最大消息数限制（默认 100 条）

### LongTermMemory（长期记忆）

- **UserPreference**：用户级偏好
  - 默认模型、工作流、主题、编辑器、Shell
- **ProjectPreference**：项目级偏好
  - 框架、语言、测试命令、自定义命令、备注

### LearningsMemory（学习记忆）

- **LearningEntry**：经验/教训记录
  - 标题、内容、类别、标签、上下文

## 适用场景

| 场景 | 推荐层级 | 原因 |
|------|----------|------|
| 单次问答 | Tier 0 | 快速响应，核心信息足够 |
| 多轮对话 | Tier 0 + Tier 1 | 需要更多项目上下文 |
| 代码生成 | Tier 0 + Tier 1 | 需要项目框架、语言信息 |
| 调试问题 | Tier 2 搜索 | 需要搜索历史错误经验 |
| 导出备份 | Tier 2 完整 | 需要所有数据 |

## 最佳实践

1. **定期清理**：使用 `omc memory clean` 清理过期记忆
2. **主动添加**：遇到重要经验时，使用 `omc memory add` 记录
3. **项目配置**：在项目根目录创建 `.omc/project.yaml` 预设偏好
4. **搜索优先**：遇到新问题时，先 `omc memory search` 查看是否有相关经验

## 配置

```python
from memory import MemoryConfig, MemoryManager

config = MemoryConfig(
    storage_dir=Path.home() / ".oh-my-coder" / "memory",
    short_term_max_messages=100,
    short_term_max_age_hours=24,
    tier0_max_tokens=500,
    tier1_max_tokens=2000,
)

mm = MemoryManager(config)
```

## 下一步

- [Checkpoint/Rollback](./checkpoint.md) - 状态保存与恢复
- [自动 Skills](./auto-skill.md) - 从经验自动生成 Skill
