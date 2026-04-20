# 模板说明

oh-my-coder 提供多种工作流模板，帮助你快速启动不同类型的项目。

## 模板列表

### 开发类模板

| 模板名称 | 说明 | 预计时间 |
|---------|------|---------|
| flask-api | Flask API 开发工作流 | 30-60 分钟 |
| enterprise | 企业级开发工作流 | 60-120 分钟 |
| multimodal | 多模态开发工作流 | 30-60 分钟 |

### 质量类模板

| 模板名称 | 说明 | 预计时间 |
|---------|------|---------|
| code-review | 代码审查工作流 | 15-30 分钟 |

### 调试类模板

| 模板名称 | 说明 | 预计时间 |
|---------|------|---------|
| bug-fix | Bug 修复工作流 | 20-40 分钟 |

## 使用方法

### 列出所有模板

```bash
omc template list
```

### 查看模板详情

```bash
omc template show flask-api
```

### 使用模板

```bash
omc template use flask-api --task "创建一个用户管理 API"
```

## 新增模板说明

### 企业级模板 (enterprise)

适用于企业项目开发，包含：
- 团队协作支持
- 审计日志配置
- 安全合规检查
- CI/CD 集成

涉及 Agent：Architect → Planner → Executor → TestEngineer → Verifier → SecurityReviewer → DocumentAgent

### 多模态模板 (multimodal)

适用于需要视觉理解的项目，包含：
- 截图/UI 布局分析
- UI 代码自动生成
- 视觉理解与交互

涉及 Agent：VisionAgent → Executor → DesignerAgent → Verifier

## 自定义模板

你也可以创建自己的模板：

```bash
omc template create my-template --base flask-api
```

模板将保存在 `~/.omc/templates/` 目录下。
