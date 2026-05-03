# 社区工作流模板

oh-my-coder 社区贡献者使用的工作流模板集合。

## 模板列表

| 模板文件 | 说明 | 适用场景 |
|----------|------|----------|
| `bug-fix-workflow.md` | Bug 修复工作流 | 发现问题→定位根因→修复→验证 |
| `feature-development-workflow.md` | 特性开发工作流 | 新功能从设计到上线 |
| `code-review-workflow.md` | Code Review 工作流 | PR 审查、质量把控 |

## 使用方式

```bash
# 使用模板
omc template show bug-fix       # 查看 bug 修复模板
omc template show feature        # 查看特性开发模板
omc template show code-review    # 查看代码审查模板

# 基于模板启动工作流
omc template use bug-fix --task "修复登录页面崩溃问题"
```

## 贡献新模板

1. 在 `templates/` 目录下创建 `.md` 文件
2. 参考现有模板格式
3. 提交 PR 到社区仓库

## 模板格式规范

```markdown
# 模板名称

## 概述
描述这个工作流解决什么问题。

## 适用场景
- 场景 1
- 场景 2

## 工作流步骤
### 步骤 1: [步骤名称]
具体操作说明...

### 步骤 2: [步骤名称]
...
```

---

*由 oh-my-coder 社区维护，贡献请见 [CONTRIBUTING.md](../CONTRIBUTING.md)*