---
name: Pull Request
description: 提交 Pull Request
title: "[PR] "
labels: []
assignees: []
body:
  - type: markdown
    attributes:
      value: |
        ## 📋 Pull Request 信息

  - type: textarea
    id: description
    attributes:
      label: 描述
      description: 简要描述此 PR 的变更内容和目的
      placeholder: |
        ## 变更内容
        - ...
        
        ## 解决的问题
        - Closes #[issue number]
        
        ## 测试方式
        - [ ] ...
    validations:
      required: true

  - type: dropdown
    id: type
    attributes:
      label: PR 类型
      options:
        - feat: 新功能
        - fix: Bug 修复
        - refactor: 重构
        - docs: 文档更新
        - test: 测试更新
        - chore: 构建/工具变更
        - perf: 性能优化
        - ci: CI/CD 更新
    validations:
      required: true

  - type: checkboxes
    id: checklist
    attributes:
      label: 
      options:
        - label: 代码符合项目的代码风格（ruff / black）
          required: true
        - label: 已添加必要的单元测试
          required: false
        - label: 所有测试通过 (`pytest`)
          required: true
        - label: 文档已更新（如涉及新功能）
          required: false
        - label: commit message 符合规范
          required: true
        - label: ⚠️ 安全检查：无 str(e) 泄露、无 in url 模式、无明文密码
          required: false
        - label: ⚠️ 如修改异常处理，请确认错误信息已脱敏
          required: false

  - type: input
    id: testing
    attributes:
      label: 测试环境
      description: 描述你本地测试的环境
      placeholder: "macOS 14, Python 3.11, DeepSeek v3"
    validations:
      required: false
