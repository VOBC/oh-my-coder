# 分层记忆系统

## 概述

Oh My Coder 采用三层记忆架构，在保持上下文精简的同时不丢失关键信息。

## 三层结构

| 层级 | Token 上限 | 内容 | 用途 |
|------|-----------|------|------|
| Tier 0 | 500 | 核心记忆 | 系统 Prompt 注入 |
| Tier 1 | 2,000 | 精选记忆 | 上下文补充 |
| Tier 2 | 无限制 | 完整存档 | 导出/查询 |

## Tier 0 — 核心记忆

自动提取的最关键信息，始终注入到系统 Prompt 中：
- 最近活跃项目
- 用户偏好（编辑器、Shell 等）
- 最重要的经验教训

```bash
# 查看 Tier 0
oh-my-coder memory tier0
```

## Tier 1 — 精选记忆

按需加载的精选内容：
- 项目详情（架构、依赖、配置）
- 常用命令和工作流
- 重要经验教训

```bash
# 查看 Tier 1
oh-my-coder memory tier1
```

## Tier 2 — 完整存档

所有记忆的完整归档，无 token 限制：
- 所有项目记录
- 完整学习历史
- 所有偏好设置

```bash
# 查看完整存档
oh-my-coder memory summary

# 查看统计
oh-my-coder memory stats
```

## CLI 命令

```bash
oh-my-coder memory tier0    # 核心记忆 (< 500 token)
oh-my-coder memory tier1    # 精选记忆 (< 2000 token)
oh-my-coder memory summary  # 完整存档（无限制）
oh-my-coder memory stats    # 记忆统计
```
