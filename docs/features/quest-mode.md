# 🧙 Quest Mode（异步自主编程）

> 本文从 README.md 迁移而来。

## 🧙 Quest Mode（异步自主编程）

Oh My Coder 支持**异步自主编程任务**，可以后台执行、实时通知。

### 核心特性

| 特性 | 说明 |
|------|------|
| **SPEC 生成** | 自动生成任务规格文档 |
| **步骤拆分** | 智能拆分任务为可执行步骤 |
| **断点续跑** | Checkpoint 快照（SHA256 差异检测）+ 一键回滚，任务中断不丢进度 |
| **验收确认** | 每个步骤执行完需要用户验收 |
| **失败重试** | 步骤失败自动触发重规划 |
| **桌面通知** | macOS 原生 + 8 种 Webhook 渠道（钉钉/Telegram/Discord/Slack/Teams/飞书/企业微信/PushPlus） |

### 工作流程

```
创建 Quest → 生成 SPEC → 用户确认 → 后台执行 → 步骤验收 → 完成
                                                      ↓
                                              失败 → 重试/跳过
```

### 使用方式

```bash
# 创建并执行 Quest（自动生成 SPEC）
omc run "实现用户认证模块" --quest

# 查看 Quest 列表
omc quest-list

# 查看详细状态
omc quest-status <quest-id>

# 订阅通知（桌面 + 钉钉）
omc quest-notify --dingtalk https://oapi.dingtalk.com/robot/send?access_token=xxx

# === 国际平台 ===
# Telegram
omc quest-notify <quest-id> --telegram-bot-token <TOKEN> --telegram-chat-id <CHAT_ID>

# Discord
omc quest-notify <quest-id> --discord https://discord.com/api/webhooks/xxx/xxx

# Slack
omc quest-notify <quest-id> --slack https://hooks.slack.com/services/xxx/xxx/xxx

# Microsoft Teams
omc quest-notify <quest-id> --teams https://outlook.office.com/webhook/xxx

# === 国内平台 ===
# 飞书（Lark）
omc quest-notify <quest-id> --feishu https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# 企业微信
omc quest-notify <quest-id> --wecom https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# PushPlus（微信公众号推送，只需 Token）
omc quest-notify <quest-id> --pushplus <your_pushplus_token>

# 阻塞等待完成
omc quest-wait <quest-id>
```

### 通知渠道

| 渠道 | 配置参数 | 说明 |
|------|----------|------|
| **桌面通知** | 默认开启 | macOS 原生通知 |
| **钉钉** | `--dingtalk <url>` | 自定义机器人 Webhook |
| **Telegram** | `--telegram-bot-token` + `--telegram-chat-id` | Bot API，Markdown 格式 |
| **Discord** | `--discord <webhook_url>` | Webhook，Embed 格式 |
| **Slack** | `--slack <webhook_url>` | Incoming Webhook，Block Kit 格式 |
| **Microsoft Teams** | `--teams <webhook_url>` | Incoming Webhook，Adaptive Card 格式 |
| **飞书（Lark）** | `--feishu <webhook_url>` | 自定义机器人，支持卡片消息 |
| **企业微信** | `--wecom <webhook_url>` | Webhook，Markdown 格式 |
| **PushPlus** | `--pushplus <token>` | 微信公众号推送，最简配置 |

> 📖 详细文档：[Quest Mode 详解](docs/QUEST_MODE.md)

---

