# 代码审查工作流

## 模板信息
- **名称**: code-review
- **类别**: workflow
- **适用场景**: 代码质量审查、安全性检查、最佳实践验证
- **预计时间**: 15-30 分钟

## 工作流定义

```yaml
name: code-review
description: 多维度代码审查工作流 - 质量、安全、性能
version: 1.0.0

steps:
  - agent: explore
    description: 探索代码库结构，识别变更范围
    timeout: 120
    
  - agent: code-reviewer
    description: 代码质量审查 - 命名、结构、可读性
    dependencies: [explore]
    timeout: 300
    
  - agent: security-reviewer
    description: 安全性审查 - 漏洞、敏感信息、权限
    dependencies: [explore]
    timeout: 300

execution_mode: parallel  # code-reviewer 和 security-reviewer 并行执行

output:
  format: markdown
  include:
    - 问题列表（按严重程度排序）
    - 改进建议
    - 代码片段引用
```

## 使用说明

### 快速开始

```bash
omc template use code-review --task "审查 src/api/ 目录下的代码"
```

### 指定审查重点

```bash
omc run review --task "重点检查用户认证模块的安全性"
```

### 预期产出

1. **质量审查报告**
   - 代码风格问题
   - 设计模式建议
   - 可读性评分

2. **安全审查报告**
   - 安全漏洞列表
   - 风险等级
   - 修复建议

3. **综合评分**
   - 总体质量分数
   - 关键问题数量
   - 改进优先级

## 审查维度

### 1. 代码质量

| 维度 | 检查项 |
|------|--------|
| 命名规范 | 变量、函数、类命名是否清晰 |
| 代码结构 | 模块划分、职责分离 |
| 注释文档 | 文档字符串、注释质量 |
| 复杂度 | 圈复杂度、函数长度 |
| 测试覆盖 | 单元测试是否存在 |

### 2. 安全性

| 维度 | 检查项 |
|------|--------|
| 输入验证 | 参数校验、类型检查 |
| 注入漏洞 | SQL、XSS、命令注入 |
| 认证授权 | 权限控制、会话管理 |
| 敏感信息 | 密码、密钥、日志脱敏 |
| 依赖安全 | 第三方库漏洞 |

### 3. 性能

| 维度 | 检查项 |
|------|--------|
| 算法复杂度 | 时间复杂度、空间复杂度 |
| 数据库查询 | N+1 问题、索引使用 |
| 缓存策略 | 缓存粒度、过期策略 |
| 异步处理 | IO 密集型任务优化 |

## 最佳实践

1. **审查前准备**
   - 明确审查范围
   - 了解业务背景
   - 准备检查清单

2. **审查过程**
   - 优先处理高严重度问题
   - 提供可执行的建议
   - 引用代码片段说明问题

3. **审查后跟进**
   - 跟踪问题修复
   - 验证改进效果
   - 更新团队规范

## 示例输出

```markdown
# 代码审查报告

## 概述
- **审查范围**: src/api/
- **文件数量**: 12
- **总体评分**: B+ (85/100)

## 关键问题

### 🔴 高优先级 (2)
1. **SQL 注入风险** - `user.py:45`
   ```python
   # 问题代码
   query = f"SELECT * FROM users WHERE id = {user_id}"
   
   # 建议修复
   query = "SELECT * FROM users WHERE id = ?"
   cursor.execute(query, (user_id,))
   ```

2. **敏感信息泄露** - `config.py:12`
   - 发现硬编码的 API Key

### 🟡 中优先级 (3)
...

## 改进建议
...
```

## 相关资源

- [Python 代码规范 (PEP 8)](https://pep8.org/)
- [OWASP 安全指南](https://owasp.org/www-project-web-security-testing-guide/)
- [Clean Code 原则](https://github.com/ryanmcdermott/clean-code-javascript)
