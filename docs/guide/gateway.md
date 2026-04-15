# 多平台消息网关

Oh My Coder 内置多平台消息网关，支持 Telegram / Discord 接入，实现统一的 AI Agent 交互接口。

## 概述

Gateway 模块提供：

- **统一消息格式**：`IncomingMessage` / `OutgoingMessage` 抽象
- **平台适配器**：各平台的 Handler 实现
- **灵活配置**：通过环境变量配置各平台凭证

## 支持的平台

| 平台 | 状态 | Handler | 依赖 | 环境变量 |
|------|------|---------|------|----------|
| Telegram | ✅ | `TelegramHandler` | python-telegram-bot | `TELEGRAM_BOT_TOKEN` |
| Discord | ✅ | `DiscordHandler` | discord.py | `DISCORD_BOT_TOKEN` |
| WhatsApp | ✅ | `WhatsAppHandler` | starlette, httpx | `WHATSAPP_*` |
| 飞书 / Lark | ✅ | `FeishuHandler` | httpx | `FEISHU_*` |
| 企业微信 | ✅ | `WeComHandler` | httpx | `WECOM_*` |
| 钉钉 | ✅ | `DingTalkHandler` | httpx | `DINGTALK_*` |
| Slack | ✅ | `SlackHandler` | httpx, starlette | `SLACK_*` |

## 快速开始

### 1. 配置环境变量

```bash
# Telegram
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"

# Discord
export DISCORD_BOT_TOKEN="your-discord-bot-token"
```

### 2. 初始化 Gateway

```python
from gateway import Gateway, Platform

# 创建 Gateway
gw = Gateway()

# 启动所有已配置的平台
await gw.start_all()

# 发送消息
from gateway import OutgoingMessage

msg = OutgoingMessage(
    platform=Platform.TELEGRAM,
    chat_id="123456789",
    text="Hello from Oh My Coder!"
)
await gw.send(msg)

# 停止
await gw.stop_all()
```

### 3. 使用 CLI

```bash
# 列出支持的平台
omc gateway list

# 测试连接
omc gateway test telegram
```

## 消息格式

### IncomingMessage（收件消息）

```python
@dataclass
class IncomingMessage:
    platform: Platform      # 来源平台
    user_id: str           # 用户 ID
    chat_id: str           # 会话 ID
    text: str              # 消息文本
    raw: Dict[str, Any]    # 原始消息数据
    timestamp: str         # 时间戳
    reply_to: Optional[str] # 回复的消息 ID
```

### OutgoingMessage（发件消息）

```python
@dataclass
class OutgoingMessage:
    platform: Platform      # 目标平台
    chat_id: str           # 会话 ID
    text: str              # 消息文本
    reply_to: Optional[str] # 回复的消息 ID
    parse_mode: str        # "markdown" 或 "html"
    extra: Dict[str, Any]  # 平台特定参数
```

## 平台配置详解

### Telegram

1. 创建 Bot：[@BotFather](https://t.me/botfather)
2. 获取 Token：`/newbot` → 复制返回的 Token
3. 配置环境变量：

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
```

### Discord

1. 创建 Bot：[Discord Developer Portal](https://discord.com/developers/applications)
2. 获取 Token：Bot → Build-A-Bot → Token
3. 邀请 Bot 到服务器（需要 `bot` + `messages` scope）
4. 配置环境变量：

```bash
export DISCORD_BOT_TOKEN="your-discord-bot-token"
```



## WhatsApp

1. 创建 Meta App：[Meta Developer Console](https://developers.facebook.com/)
2. 配置 WhatsApp Business 平台，获取 Phone Number ID
3. 生成 Long-lived Access Token
4. 配置 Webhook URL 指向 `http://<your-host>:8080/webhook/whatsapp`

```bash
export WHATSAPP_PHONE_NUMBER_ID="123456789"
export WHATSAPP_ACCESS_TOKEN="EAAxxxx..."
export WHATSAPP_WEBHOOK_URL="https://your-domain.com"
export WHATSAPP_VERIFY_TOKEN="your-verify-token"
```

## 飞书 / Lark

1. 创建自建应用：[飞书开放平台](https://open.feishu.cn/)
2. 获取 App ID 和 App Secret
3. 开通「获取与发送单聊消息」权限

```bash
export FEISHU_APP_ID="cli_xxxxxxxxxxxx"
export FEISHU_APP_SECRET="your-app-secret"
# 可选：加密回调
export FEISHU_ENCRYPT_KEY="your-encrypt-key"
```

## 企业微信

1. 创建自建应用：[企业微信后台](https://work.weixin.qq.com/)
2. 获取企业 ID、应用 AgentId、Secret
3. 配置应用回调地址（需公网可达）

```bash
export WECOM_CORP_ID="wwxxxxxxxxxxxx"
export WECOM_AGENT_ID="1000001"
export WECOM_CORP_SECRET="your-secret"
export WECOM_TOKEN="your-callback-token"
export WECOM_ENCODING_AES_KEY="your-aes-key"
```

## 钉钉

1. 创建企业内部应用：[钉钉开放平台](https://open.dingtalk.com/)
2. 获取 AppKey 和 AppSecret
3. 配置事件订阅（需要公网回调 URL）

```bash
export DINGTALK_APP_KEY="dingxxxxxxxxxxxx"
export DINGTALK_APP_SECRET="your-app-secret"
export DINGTALK_TOKEN="your-callback-token"
export DINGTALK_AES_KEY="your-43-char-aes-key"
```

## Slack

1. 创建 Slack App：[api.slack.com/apps](https://api.slack.com/apps)
2. 启用 Bot TokenScopes：`chat:write`, `channels:history`
3. 启用 Event Subscriptions，URL 指向 `http://<host>:<port>/webhook/slack`
4. 订阅事件：`message.im`, `message.channels`

```bash
export SLACK_BOT_TOKEN="xoxb-xxxxxxxxxxxx"
export SLACK_SIGNING_SECRET="your-signing-secret"
```

## 高级用法

### 自定义消息处理器

```python
from gateway import Gateway, IncomingMessage

async def handle_message(msg: IncomingMessage):
    """自定义消息处理逻辑"""
    print(f"[{msg.platform.value}] {msg.user_id}: {msg.text}")
    # 转发给 Agent 处理...
    # await agent.process(msg.text)

gw = Gateway(on_message=handle_message)
await gw.start_all()
```

### 单平台启动

```python
from gateway import Gateway, Platform

gw = Gateway()

# 只启动 Telegram
await gw.start(Platform.TELEGRAM)

# 发送消息
await gw.send_to(Platform.TELEGRAM, chat_id="123", text="Hi!")

# 停止
await gw.stop(Platform.TELEGRAM)
```

## 架构设计

```
gateway/
├── __init__.py          # 模块入口
├── base.py              # 基础类型定义（Platform, Message 等）
├── gateway.py           # 主 Gateway 类
└── platforms/           # 平台适配器
    ├── __init__.py
    ├── telegram.py      # Telegram Bot Handler
    ├── discord.py       # Discord Bot Handler
    ├── whatsapp.py      # WhatsApp Business Cloud API Handler
    ├── feishu.py        # 飞书 / Lark Handler
    ├── wecom.py         # 企业微信 Handler
    ├── dingtalk.py      # 钉钉 Handler
    └── slack.py         # Slack Bot Handler
```

## 注意事项

1. **依赖安装**：
   - Telegram: `pip install python-telegram-bot`
   - Discord: `pip install discord.py`
   - WhatsApp: `pip install starlette httpx`
   - 飞书: `pip install httpx`
   - 企业微信: `pip install httpx`
   - 钉钉: `pip install httpx`
   - Slack: `pip install httpx starlette`
2. **Token 安全**：不要将 Token 提交到 Git，使用 `.env` 文件管理
3. **错误处理**：未配置的平台会使用 `NoopHandler`（只记录日志不实际连接）

## 下一步

- [CLI 参考](../api/cli.md)
- [工作流](./workflows.md)
