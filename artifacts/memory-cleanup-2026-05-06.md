# 记忆维护 - 2026-05-06

## 目标
压缩记忆、清理无用文件，让对话更顺畅

## 清理内容
- 删除 CHANGELOG.md、CODE_OF_CONDUCT.md、SECURITY.md（项目模板残留）
- 删除旧目录：backend/、config/、deploy/、extensions/、health/、models/、web-ui/、wiki/、skills/
- 创建 MEMORY.md（压缩版，91行）
- 创建 rules/doc-sync-rule.md（可分享的文档同步规则）

## MEMORY.md 压缩
- 删除冗余代码示例（f-string、导入规范、路径处理等显而易见的内容）
- 删除已修复文件清单（已在 git 历史中）
- 删除过时的项目进度和 workspace 结构图
- 保留核心教训：安全门禁、文档同步、ruff.toml 优先级、Desktop fallback

## 推送
- commit bf16adc: chore: add MEMORY.md and doc-sync rule, remove old boilerplate files
