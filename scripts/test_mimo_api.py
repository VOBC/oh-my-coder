#!/usr/bin/env python3
"""
测试小米 MiMo API 连通性

使用方式:
    export MIMOAPIKEY=your_api_key
    python scripts/test_mimo_api.py

或者直接运行:
    MIMOAPIKEY=your_api_key python scripts/test_mimo_api.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import MimoModel
from src.models.base import ModelConfig, ModelTier


async def test_mimo():
    """测试 MiMo API"""
    api_key = os.environ.get("MIMOAPIKEY")
    if not api_key:
        print("❌ 请设置环境变量 MIMOAPIKEY")
        print("   export MIMOAPIKEY=your_api_key")
        sys.exit(1)

    print("🔗 正在连接 MiMo API...")
    print(f"   API Key: {api_key[:8]}...{api_key[-4:]}")

    config = ModelConfig(api_key=api_key)

    # 测试 LOW tier (mimo-v2-flash)
    print("\n📝 测试 mimo-v2-flash (LOW tier)...")
    model_low = MimoModel(config, ModelTier.LOW)
    try:
        from src.models.base import Message
        response = await model_low.generate([
            Message(role="user", content="你好，请用一句话介绍自己")
        ])
        print(f"✅ LOW tier 成功!")
        print(f"   回复: {response.content[:100]}...")
        print(f"   延迟: {response.latency_ms:.0f}ms")
        print(f"   Token 使用: {response.usage.total_tokens}")
    except Exception as e:
        print(f"❌ LOW tier 失败: {e}")
        return False
    finally:
        await model_low.close()

    # 测试 HIGH tier (mimo-v2-pro)
    print("\n📝 测试 mimo-v2-pro (HIGH tier)...")
    model_high = MimoModel(config, ModelTier.HIGH)
    try:
        response = await model_high.generate([
            Message(role="user", content="你好，请用一句话介绍自己")
        ])
        print(f"✅ HIGH tier 成功!")
        print(f"   回复: {response.content[:100]}...")
        print(f"   延迟: {response.latency_ms:.0f}ms")
    except Exception as e:
        print(f"❌ HIGH tier 失败: {e}")
    finally:
        await model_high.close()

    # 测试函数调用
    print("\n📝 测试函数调用 (Function Calling)...")
    model = MimoModel(config, ModelTier.LOW)
    try:
        tools = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取指定城市的天气",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称"}
                    },
                    "required": ["city"]
                }
            }
        }]
        response = await model.generate([
            Message(role="user", content="北京天气怎么样?")
        ], tools=tools)

        if response.metadata.get("tool_calls"):
            print(f"✅ 函数调用成功!")
            print(f"   调用函数: {response.metadata['tool_calls'][0]['function']['name']}")
            print(f"   参数: {response.metadata['tool_calls'][0]['function']['arguments']}")
        else:
            print(f"⚠️ 未触发函数调用 (正常，取决于模型判断)")
    except Exception as e:
        print(f"❌ 函数调用测试失败: {e}")
    finally:
        await model.close()

    print("\n🎉 MiMo API 测试完成!")
    return True


if __name__ == "__main__":
    asyncio.run(test_mimo())
