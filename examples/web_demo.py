#!/usr/bin/env python3
"""
Web 界面使用示例

展示如何使用 Web 界面的 API 端点。

运行方式：
    python examples/web_demo.py
"""
import httpx
import asyncio
import json
import time


BASE_URL = "http://localhost:8000"


# ============================================================
# Helper Functions
# ============================================================
def pretty_json(data):
    """格式化打印 JSON"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


async def wait_for_task(
    client: httpx.AsyncClient,
    task_id: str,
    timeout: int = 60,
) -> dict:
    """
    通过 SSE 等待任务完成

    Args:
        client: httpx 客户端
        task_id: 任务 ID
        timeout: 超时时间（秒）

    Returns:
        任务结果
    """
    events = []

    async with client.stream(
        "GET",
        f"{BASE_URL}/sse/execute/{task_id}",
        timeout=timeout,
    ) as response:
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:]  # 去掉 "data: " 前缀
            try:
                event = json.loads(data_str)
                events.append(event)

                # 打印进度
                if event["type"] == "step_start":
                    print(f"  🔄 开始执行: {event['step']}")
                elif event["type"] == "step_complete":
                    print(f"  ✅ {event['step']} 完成")
                elif event["type"] == "complete":
                    print("  🎉 任务完成！")
                    return event
                elif event["type"] == "error":
                    print(f"  ❌ 错误: {event['content']}")
                    return event
            except json.JSONDecodeError:
                pass

    return {"events": events}


# ============================================================
# 示例 1: 基础调用 - 异步任务 + SSE
# ============================================================
async def demo_async_with_sse():
    """异步提交任务，通过 SSE 实时获取进度"""
    print("\n" + "=" * 60)
    print("📡 示例 1: 异步任务 + SSE 实时进度推送")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. 检查服务状态
        print("\n[1] 检查服务状态...")
        response = await client.get(f"{BASE_URL}/health")
        pretty_json(response.json())

        # 2. 获取配置
        print("\n[2] 获取可用配置...")
        response = await client.get(f"{BASE_URL}/api/config")
        pretty_json(response.json())

        # 3. 提交任务
        print("\n[3] 提交任务...")
        payload = {
            "task": "实现一个简单的计算器类，支持加减乘除运算",
            "project_path": ".",
            "model": "deepseek",
            "workflow": "build",
        }
        response = await client.post(
            f"{BASE_URL}/api/execute",
            json=payload,
            timeout=10.0,
        )
        result = response.json()
        print(f"任务 ID: {result['task_id']}")
        task_id = result["task_id"]

        # 4. 通过 SSE 等待完成
        print("\n[4] 等待执行（SSE 实时推送）...")
        start = time.time()
        final_result = await wait_for_task(client, task_id, timeout=120)
        print(f"\n⏱️  总耗时: {time.time() - start:.1f} 秒")

        # 5. 获取任务详情
        print("\n[5] 任务详情...")
        response = await client.get(f"{BASE_URL}/api/tasks/{task_id}")
        task_info = response.json()
        print(f"状态: {task_info['status']}")
        if task_info.get("stats"):
            stats = task_info["stats"]
            print(f"完成步骤: {stats.get('steps_completed', [])}")
            print(f"失败步骤: {stats.get('steps_failed', [])}")
            print(f"Token 消耗: {stats.get('total_tokens', 0)}")


# ============================================================
# 示例 2: 同步调用 - 直接获取结果
# ============================================================
async def demo_sync_execution():
    """同步调用，直接返回结果（适合小任务）"""
    print("\n" + "=" * 60)
    print("⚡ 示例 2: 同步执行（直接返回结果）")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        payload = {
            "task": "用一句话解释什么是 REST API",
            "workflow": "build",
        }

        print("\n发送请求...")
        start = time.time()
        response = await client.post(
            f"{BASE_URL}/api/execute-sync",
            json=payload,
            timeout=60.0,
        )
        elapsed = time.time() - start

        result = response.json()
        print(f"\n状态: {result.get('status')}")
        print(f"耗时: {elapsed:.1f} 秒")

        if result.get("status") == "success":
            data = result.get("result", {})
            print(f"\n完成步骤: {data.get('steps_completed', [])}")
            print(f"Token 消耗: {data.get('total_tokens', 0)}")
            print(f"执行时间: {data.get('execution_time', 0)} 秒")
        else:
            print(f"\n错误: {result.get('message')}")


# ============================================================
# 示例 3: 代码审查工作流
# ============================================================
async def demo_review_workflow():
    """使用代码审查工作流"""
    print("\n" + "=" * 60)
    print("🔍 示例 3: 代码审查工作流")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        payload = {
            "task": "审查当前项目的代码质量和潜在安全漏洞",
            "project_path": ".",
            "model": "deepseek",
            "workflow": "review",
        }

        print("\n提交代码审查任务...")
        response = await client.post(
            f"{BASE_URL}/api/execute",
            json=payload,
            timeout=10.0,
        )
        result = response.json()
        print(f"任务 ID: {result['task_id']}")

        print("\n等待执行...")
        final_result = await wait_for_task(client, result["task_id"])


# ============================================================
# 示例 4: 列出所有任务
# ============================================================
async def demo_list_tasks():
    """列出所有任务"""
    print("\n" + "=" * 60)
    print("📋 示例 4: 任务管理")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/tasks")
        tasks = response.json()
        print(f"\n当前任务数: {len(tasks['tasks'])}")
        for task in tasks["tasks"]:
            print(f"  - {task['task_id']} | {task['status']} | {task.get('started_at', 'N/A')}")


# ============================================================
# Main
# ============================================================
async def main():
    """运行所有示例"""
    print("\n" + "🚀" * 20)
    print("Oh My Coder Web 界面使用示例")
    print("🚀" * 20)
    print("\n⚠️  请确保 Web 服务已启动: python -m src.web.app")
    print(f"   服务地址: {BASE_URL}\n")

    # 检查服务是否可用
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code != 200:
                print("❌ 服务未正常响应")
                return
    except Exception as e:
        print(f"❌ 无法连接服务: {e}")
        print("\n请先启动服务:")
        print("  cd oh-my-coder")
        print("  python -m src.web.app")
        return

    print("✅ 服务连接正常\n")

    # 运行示例
    await demo_async_with_sse()
    # await demo_sync_execution()  # 取消注释可测试同步模式
    # await demo_review_workflow()  # 取消注释可测试审查工作流
    await demo_list_tasks()

    print("\n" + "=" * 60)
    print("✨ 示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
