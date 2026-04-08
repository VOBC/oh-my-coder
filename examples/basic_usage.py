"""
基础示例：使用 Oh My Coder 完成简单任务

演示：
1. CLI 基本用法
2. Web API 调用
3. 工作流选择
"""

import httpx
import asyncio


def example_cli_basic():
    """
    示例 1: CLI 基本用法
    
    在终端执行这些命令：
    """
    commands = [
        "# 查看版本",
        "omc --version",
        "",
        "# 探索项目",
        "omc explore .",
        "",
        "# 查看所有 Agent",
        "omc agents",
        "",
        "# 查看系统状态",
        "omc status",
    ]
    
    for cmd in commands:
        print(cmd)


def example_cli_tasks():
    """
    示例 2: CLI 任务执行
    
    在终端执行这些命令：
    """
    tasks = [
        "# 执行简单任务",
        'omc run "为 utils.py 添加类型注解"',
        "",
        "# 使用特定工作流",
        'omc run "实现用户认证模块" -w build',
        "",
        "# 代码审查",
        'omc run "审查 src/api 目录的代码质量" -w review',
        "",
        "# Bug 修复",
        'omc run "修复登录接口的空指针异常" -w debug',
        "",
        "# 生成测试",
        'omc run "为 src/core 生成单元测试" -w test',
    ]
    
    for task in tasks:
        print(task)


async def example_web_api():
    """
    示例 3: Web API 异步调用（SSE）
    """
    url = "http://localhost:8000/api/execute"
    payload = {
        "task": "为用户模型添加 CRUD 接口",
        "workflow": "build"
    }
    
    print("=== Web API 异步调用示例 ===")
    print(f"POST {url}")
    print(f"Payload: {payload}\n")
    
    # 实际调用示例（需要服务器运行）
    # async with httpx.AsyncClient() as client:
    #     async with client.stream("POST", url, json=payload) as response:
    #         async for line in response.aiter_lines():
    #             if line.startswith("data:"):
    #                 print(line)


async def example_web_api_sync():
    """
    示例 4: Web API 同步调用
    """
    url = "http://localhost:8000/api/execute-sync"
    payload = {
        "task": "审查代码质量",
        "workflow": "review"
    }
    
    print("=== Web API 同步调用示例 ===")
    print(f"POST {url}")
    print(f"Payload: {payload}\n")
    
    # 实际调用示例（需要服务器运行）
    # async with httpx.AsyncClient(timeout=60) as client:
    #     response = await client.post(url, json=payload)
    #     result = response.json()
    #     print(result)


def example_curl():
    """
    示例 5: curl 命令调用
    """
    commands = [
        "# 异步执行（SSE）",
        'curl -X POST http://localhost:8000/api/execute \\',
        '  -H "Content-Type: application/json" \\',
        '  -d \'{"task": "实现 REST API", "workflow": "build"}\'',
        "",
        "# 同步执行",
        'curl -X POST http://localhost:8000/api/execute-sync \\',
        '  -H "Content-Type: application/json" \\',
        '  -d \'{"task": "审查代码质量", "workflow": "review"}\'',
        "",
        "# 列出所有任务",
        'curl http://localhost:8000/api/tasks',
        "",
        "# 获取任务详情",
        'curl http://localhost:8000/api/tasks/task_id_here',
        "",
        "# 健康检查",
        'curl http://localhost:8000/health',
    ]
    
    print("=== curl 命令示例 ===")
    for cmd in commands:
        print(cmd)


if __name__ == "__main__":
    print("=" * 60)
    print("Oh My Coder 基础示例")
    print("=" * 60)
    print()
    
    example_cli_basic()
    print()
    
    example_cli_tasks()
    print()
    
    print(example_web_api.__doc__)
    asyncio.run(example_web_api())
    print()
    
    print(example_web_api_sync.__doc__)
    asyncio.run(example_web_api_sync())
    print()
    
    example_curl()
