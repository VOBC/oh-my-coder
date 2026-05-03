# 🎉 oh-my-coder 社区模板

欢迎来到 oh-my-coder 社区！这里汇聚了社区贡献者分享的优秀 Agent 和 Workflow 配置。

## 📖 目录

- [快速开始](#快速开始)
- [使用模板](#使用模板)
- [贡献模板](#贡献模板)
- [模板格式](#模板格式)

---

## 🚀 快速开始

### 浏览社区模板

```bash
omc community list
```

### 安装模板

```bash
omc community install <template-name>
```

---

## 📦 使用模板

### 列出可用模板

```bash
omc community list
```

输出示例：

```
📦 社区模板
═══════════════════════════════════════
 名称                    类型     作者            标签
═══════════════════════════════════════
 code-review-guru        agent    alice           code-review, security
 react-workflow          workflow bob             frontend, react
 python-api-tpl          workflow carol          python, fastapi
═══════════════════════════════════════
```

### 安装模板

```bash
# 安装 Agent 模板
omc community install code-review-guru

# 安装 Workflow 模板
omc community install react-workflow
```

安装后，模板会保存到 `~/.omc/community/` 目录。

### 查看模板详情

```bash
omc community show <template-name>
```

---

## 🤝 贡献模板

### 提交流程

1. **Fork** 本仓库
2. 在 `community/agents/` 或 `community/workflows/` 目录下创建你的模板文件
3. 按照 [模板格式](#模板格式) 编写内容
4. 创建 Pull Request，描述模板用途和使用场景

### 提交前检查

- ✅ 模板文件格式正确（YAML frontmatter + Markdown 内容）
- ✅ 内容真实可用，有实际使用价值
- ✅ 包含清晰的 README 说明
- ✅ 通过 ruff 检查：`python3 -m ruff check community/`

---

## 📝 模板格式

### Agent 模板格式

```markdown
---
name: template-name
type: agent
author: your-username
version: 1.0.0
description: 模板简短描述
tags: [tag1, tag2, tag3]
created: 2024-01-01
---

# Agent 名称

## 简介

这里是 Agent 的详细介绍。

## 使用场景

- 场景 1
- 场景 2

## 配置说明

描述如何配置和使用此 Agent。

## 示例

提供使用示例。
```

### Workflow 模板格式

```markdown
---
name: template-name
type: workflow
author: your-username
version: 1.0.0
description: 工作流简短描述
tags: [tag1, tag2, tag3]
created: 2024-01-01
agents: [agent1, agent2]
estimated_time: 30-60 分钟
---

# Workflow 名称

## 简介

这里是 Workflow 的详细介绍。

## 工作流程

1. 步骤 1
2. 步骤 2
3. 步骤 3

## 使用场景

描述适用的使用场景。

## 配置说明

描述如何配置此工作流。

## 示例

提供使用示例。
```

---

## 📋 标签分类

建议使用的标签：

| 标签 | 说明 |
|------|------|
| `code-review` | 代码审查相关 |
| `security` | 安全相关 |
| `frontend` | 前端开发 |
| `backend` | 后端开发 |
| `debug` | 调试相关 |
| `testing` | 测试相关 |
| `documentation` | 文档相关 |
| `refactor` | 重构相关 |

---

## ❓ 常见问题

**Q: 模板安装在哪里？**
A: 模板会安装到 `~/.omc/community/` 目录。

**Q: 如何删除已安装的模板？**
A: 直接删除 `~/.omc/community/<template-name>.md` 文件。

**Q: 模板可以修改吗？**
A: 可以，安装后的模板保存在本地，你可以自由修改。

---

## 🙏 致谢

感谢所有社区贡献者！

模板格式参考 [Stripe V2 Conventions](https://devhub.vc/) 和 GitHub 社区最佳实践。