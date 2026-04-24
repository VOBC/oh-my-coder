# HEARTBEAT.md

## 当前项目状态

- **oh-my-coder** (CLI): https://github.com/VOBC/oh-my-coder
  - HEAD: `6edd001` ✅ 已 force push
  - README: 31 Agent, SVG, 差异优势
  - 测试：739+ passed

- **桌面端** (oh-my-coder/desktop):
  - HEAD: `6edd001` ✅
  - 可运行 .app，18 个模型，完整 UI

## 待完成任务

- 桌面端：应用图标 / Apple 签名 / notarization
- omc CLI：P2-1 自动测试增强、P2-2 成本优化建议（`omc cost` CLI）
- 桌面端：P4 功能（见 oh-my-coder/desktop 内的 TASK.md）

## Heartbeat 检查项

每 8-12 小时检查一次：

1. **Emails** — 重要邮件？
2. **Weather** — 如果人类要出门？
3. **Memory 维护** — 每隔几天更新 MEMORY.md（整合 daily 日志）

## Self-Improving Check

检查 `./skills/self-improving/` 目录是否存在：
- 如果存在：按其规则运行
- 如果不存在：直接 `HEARTBEAT_OK`
