#!/usr/bin/env python3
"""
Gateway 功能验证脚本

验证：
1. Gateway 初始化（无 token 时用 NoopHandler）
2. 消息格式转换（IncomingMessage / OutgoingMessage）
3. Telegram/Discord Handler 依赖检查逻辑
"""

import sys

# 1. 测试基本导入
print("1. 测试 Gateway 模块导入...")
try:
    from src.gateway import (
        Gateway,
        IncomingMessage,
        OutgoingMessage,
        Platform,
    )
    print("   ✅ 模块导入成功")
except Exception as e:
    print(f"   ❌ 模块导入失败: {e}")
    sys.exit(1)

# 2. 测试 Gateway 无 token 初始化
print("\n2. 测试 Gateway 无 token 初始化...")
try:
    gateway = Gateway(orchestrator=None)
    status = gateway.status()
    assert "handlers" in status
    assert "telegram" in status["handlers"]
    assert "discord" in status["handlers"]
    print(f"   ✅ 初始化成功，状态: {status['started_platforms']}")
except Exception as e:
    print(f"   ❌ 初始化失败: {e}")
    sys.exit(1)

# 3. 测试 NoopHandler
print("\n3. 测试 NoopHandler...")
try:
    from src.gateway.base import NoopHandler

    def dummy_handler(msg):
        pass

    handler = NoopHandler(platform=Platform.TELEGRAM, on_message=dummy_handler)
    assert handler.is_started is False
    print("   ✅ NoopHandler 创建成功")
except Exception as e:
    print(f"   ❌ NoopHandler 测试失败: {e}")
    sys.exit(1)

# 4. 测试消息格式转换
print("\n4. 测试消息格式转换...")
try:
    # IncomingMessage
    incoming = IncomingMessage(
        platform=Platform.TELEGRAM,
        user_id="12345",
        chat_id="67890",
        text="/start",
    )
    assert incoming.platform == Platform.TELEGRAM
    assert incoming.user_id == "12345"
    assert incoming.text == "/start"
    assert incoming.timestamp is not None
    print(f"   ✅ IncomingMessage: {incoming.platform.value} | {incoming.user_id} | {incoming.text}")

    # OutgoingMessage
    outgoing = OutgoingMessage(
        platform=Platform.DISCORD,
        chat_id="111",
        text="Hello!",
    )
    assert outgoing.platform == Platform.DISCORD
    assert outgoing.text == "Hello!"
    assert outgoing.parse_mode == "markdown"
    print(f"   ✅ OutgoingMessage: {outgoing.platform.value} | {outgoing.text}")
except Exception as e:
    print(f"   ❌ 消息格式测试失败: {e}")
    sys.exit(1)

# 5. 测试平台枚举
print("\n5. 测试 Platform 枚举...")
try:
    platforms = [Platform.TELEGRAM, Platform.DISCORD, Platform.WHATSAPP, Platform.SLACK, Platform.WECHAT]
    for p in platforms:
        assert p.value in ["telegram", "discord", "whatsapp", "slack", "wechat"]
    print(f"   ✅ Platform 枚举: {[p.value for p in platforms]}")
except Exception as e:
    print(f"   ❌ Platform 枚举测试失败: {e}")
    sys.exit(1)

# 6. 测试依赖检查函数
print("\n6. 测试依赖检查函数...")
try:
    from src.gateway.platforms.discord import check_discord_dependencies
    from src.gateway.platforms.telegram import check_telegram_dependencies

    tg_available = check_telegram_dependencies()
    dc_available = check_discord_dependencies()
    print(f"   ✅ Telegram 依赖: {tg_available}")
    print(f"   ✅ Discord 依赖: {dc_available}")
except Exception as e:
    print(f"   ⚠️ 依赖检查失败（正常，依赖可能未安装）: {e}")

# 7. 测试 status 输出格式
print("\n7. 测试 status 输出格式...")
try:
    gateway = Gateway(orchestrator=None)
    status = gateway.status()
    assert "started_platforms" in status
    assert "handlers" in status
    for platform_name, info in status["handlers"].items():
        assert "configured" in info
        assert "started" in info
        assert "type" in info
    print(f"   ✅ status 格式正确: {status}")
except Exception as e:
    print(f"   ❌ status 测试失败: {e}")
    sys.exit(1)

# 8. 测试 get_handler
print("\n8. 测试 get_handler...")
try:
    gateway = Gateway(orchestrator=None)
    tg_handler = gateway.get_handler(Platform.TELEGRAM)
    dc_handler = gateway.get_handler(Platform.DISCORD)
    assert tg_handler is not None
    assert dc_handler is not None
    assert isinstance(tg_handler, NoopHandler)
    print("   ✅ get_handler 正常")
except Exception as e:
    print(f"   ❌ get_handler 测试失败: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("🎉 所有验证通过！Gateway 功能正常")
print("=" * 50)
