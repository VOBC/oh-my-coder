---
name: code-review-workflow
type: workflow
author: community
version: 1.0.0
description: 自动化代码审查工作流，支持多维度审查和团队协作
tags: [code-review, ci-cd, quality, security]
created: 2024-01-20
agents: [explorer, code-reviewer, security-reviewer, verifier]
estimated_time: 15-30 分钟
---

# Code Review Workflow

## 简介

自动化代码审查工作流，从多个维度对代码进行全面审查。支持安全检查、性能分析、代码风格检查，并生成详细的审查报告。

## 工作流程

```
┌─────────────┐
│   触发审查   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 代码探索     │  explorer
│ 理解代码结构 │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 代码质量审查 │  code-reviewer
│ 风格/可读性  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 安全审查     │  security-reviewer
│ 漏洞检测    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 综合验证     │  verifier
│ 审查结果汇总 │
└─────────────┘
```

## 详细步骤

### Step 1: 代码探索 (explorer)

分析代码结构和依赖关系：

- 解析代码文件结构
- 识别关键模块和接口
- 理解业务逻辑
- 生成代码地图

### Step 2: 代码质量审查 (code-reviewer)

检查代码质量和风格：

- 代码风格一致性
- 命名规范检查
- 注释完整性
- 函数/类复杂度
- 重复代码检测

### Step 3: 安全审查 (security-reviewer)

检测潜在的安全问题：

- SQL 注入风险
- XSS 漏洞
- 敏感信息泄露
- 依赖安全
- 认证/授权问题

### Step 4: 综合验证 (verifier)

汇总审查结果：

- 生成审查报告
- 优先级排序
- 修复建议
- 评分计算

## 使用配置

### 基础配置

```yaml
# ~/.omc/workflows/code-review.yaml
workflow: code-review
settings:
  timeout: 30m
  report_format: markdown
  severity_threshold: medium
```

### 高级配置

```yaml
workflow: code-review
settings:
  timeout: 60m
  report_format: json
  severity_threshold: low
  exclude_patterns:
    - "*.test.js"
    - "*.spec.js"
    - "node_modules/**"
  security_checks:
    - sql-injection
    - xss
    - csrf
    - secrets
  performance_checks:
    - n+1-queries
    - memory-leaks
    - large-files
```

## 命令行使用

```bash
# 基础审查
omc run code-review --path ./src

# 指定配置文件
omc run code-review --path ./src --config ~/.omc/workflows/code-review.yaml

# 只做安全审查
omc run code-review --path ./src --scope security-only

# 生成 JSON 报告
omc run code-review --path ./src --output report.json
```

## 输出示例

### 控制台输出

```
🔍 开始代码审查...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/4] 代码探索 (explorer)
  ✓ 解析完成，识别 23 个模块
  ✓ 依赖关系图生成

[2/4] 代码质量审查 (code-reviewer)
  ✓ 风格检查通过
  ⚠ 发现 3 处命名不规范
  ⚠ 2 个函数复杂度过高

[3/4] 安全审查 (security-reviewer)
  ✓ 无高危漏洞
  ⚠ 发现 2 处 XSS 风险
  ⚠ 1 处敏感信息泄露

[4/4] 综合验证 (verifier)
  ✓ 报告生成完成

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 审查结果: B+ (85/100)

🔒 安全: C (70/100) - 需要关注
⚡ 性能: B (82/100) - 良好
📝 质量: A- (90/100) - 优秀

📄 详细报告: ./code-review-report.md
```

### JSON 报告结构

```json
{
  "workflow": "code-review",
  "timestamp": "2024-01-20T10:30:00Z",
  "score": 85,
  "dimensions": {
    "security": { "score": 70, "issues": [...] },
    "performance": { "score": 82, "issues": [...] },
    "quality": { "score": 90, "issues": [...] }
  },
  "issues": [
    {
      "severity": "high",
      "category": "security",
      "file": "src/auth.py",
      "line": 45,
      "description": "XSS vulnerability",
      "suggestion": "使用 sanitize_html() 函数"
    }
  ],
  "summary": "代码整体质量良好，建议修复 3 个中危安全问题"
}
```

## 集成 CI/CD

### GitHub Actions

```yaml
# .github/workflows/code-review.yml
name: Code Review

on:
  pull_request:
    paths:
      - '**.py'
      - '**.js'
      - '**.ts'

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run omc code-review
        run: |
          pip install oh-my-coder
          omc run code-review --path ./src --output review-report.json
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: review-report
          path: review-report.json
```

### GitLab CI

```yaml
# .gitlab-ci.yml
code-review:
  stage: test
  script:
    - pip install oh-my-coder
    - omc run code-review --path ./src
  artifacts:
    paths:
      - code-review-report.md
    expire_in: 1 week
```

## 最佳实践

1. **定期审查**：建议每次 PR 都运行审查工作流
2. **阈值设置**：根据项目情况设置合理的严重性阈值
3. **报告归档**：保留历史审查报告，便于追踪改进
4. **团队协作**：在团队内共享审查配置，统一代码规范

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| 审查超时 | 增加 `timeout` 配置，或缩小审查范围 |
| 报告生成失败 | 检查写入权限，确保输出目录存在 |
| 漏报严重问题 | 调整 `security_checks` 配置，确保所有检查项开启 |
| 误报过多 | 调整 `exclude_patterns` 或添加白名单 |