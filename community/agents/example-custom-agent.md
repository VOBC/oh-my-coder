---
name: code-review-expert
type: agent
author: community
version: 1.0.0
description: 专业的代码审查 Agent，专注于代码质量、安全和性能
tags: [code-review, security, quality, backend]
created: 2024-01-15
---

# Code Review Expert Agent

## 简介

Code Review Expert 是一款专注于代码审查的 Agent。它能够全面分析代码质量问题、安全漏洞、性能瓶颈，并提供专业的改进建议。

## 核心能力

- **代码质量分析**：检查代码风格、可读性、可维护性
- **安全漏洞检测**：识别潜在的安全问题（SQL注入、XSS、CSRF等）
- **性能优化建议**：发现性能瓶颈并提供优化方案
- **最佳实践检查**：验证是否遵循语言/框架的最佳实践
- **测试覆盖率**：评估测试是否充分

## Agent 配置

```yaml
# ~/.omc/community/code-review-expert.yaml
name: code-review-expert
type: agent
model: gpt-4
capabilities:
  - code-analysis
  - security-scan
  - performance-check
  - best-practice-verify
rules:
  - 安全优先
  - 性能第二
  - 可读性第三
```

## 使用示例

### 命令行使用

```bash
omc agents use code-review-expert --path ./src
```

### 编程调用

```python
from oh_my_coder import Agent

agent = Agent("code-review-expert")
result = agent.review(path="./src", options={
    "security": True,
    "performance": True,
    "style": True
})
```

## 审查维度

| 维度 | 检查项 |
|------|--------|
| 安全性 | SQL注入、XSS、CSRF、敏感信息泄露、依赖漏洞 |
| 性能 | 循环效率、缓存策略、数据库查询、内存使用 |
| 可读性 | 命名规范、注释完整性、函数长度、复杂度 |
| 可维护性 | 耦合度、内聚性、重复代码、僵化代码 |
| 测试 | 覆盖率、边界情况、Mock 使用 |

## 报告格式

审查完成后，生成如下报告：

```
## Code Review Report

### 安全性 🔒
- [HIGH] 发现 XSS 漏洞: user_input.py:45
- [MEDIUM] 敏感信息硬编码: config.py:12

### 性能 ⚡
- [LOW] 可优化循环: utils.py:78

### 建议 💡
- 重构 user_input.py 中的输入验证逻辑
- 使用环境变量替代硬编码的敏感信息

---
总体评分: B (85/100)
```