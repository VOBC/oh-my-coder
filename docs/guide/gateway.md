# 多平台消息网关

Oh My Coder 内置多平台消息网关，支持 Telegram / Discord 接入，实现统一的 AI Agent 交互接口。

## 概述

Gateway 模块提供：

- **统一消息格式**：`IncomingMessage` / `OutgoingMessage` 抽象
- **平台适配器**：各平台的 Handler 实现
- **灵活配置**：通过环境变量配置各平台凭证

## 支持的平台

| 平台 | 状态 | Handler | 环境变量 |
|------|------|---------|----------|
| Telegram | ✅ | `TelegramHandler` | `TELEGRAM_BOT_TOKEN` |
| Discord | ✅ | `DiscordHandler` | `DISCORD_BOT_TOKEN` |
| WhatsApp | 🔜 | `WhatsAppHandler` | — |
| 飞书 | 🔜 | — | — |

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
├── base.py              # 基础类型定义
├── gateway.py           # 主 Gateway 类
└── platforms/           # 平台适配器
    ├── __init__.py
    ├── telegram.py      # Telegram Handler
    └── discord.py       # Discord Handler
```

## 注意事项

1. **依赖安装**：Telegram 需要 `python-telegram-bot`，Discord 需要 `discord.py`
2. **Token 安全**：不要将 Token 提交到 Git，使用 `.env` 文件管理
3. **错误处理**：未配置的平台会使用 `NoopHandler`（只记录日志不实际连接）

## 下一步

- [CLI 参考](../api/cli.md)
- [工作流](./workflows.md)
