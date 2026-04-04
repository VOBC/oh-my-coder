#!/usr/bin/env python3
"""
Oh My Coder - 多智能体协作演示

这个脚本展示如何使用 Oh My Coder 的多智能体系统
来完成一个简单的编程任务。
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from src.core.router import ModelRouter, RouterConfig
from src.agents.base import AgentContext
from src.agents import (
    ExploreAgent,
    AnalystAgent,
    PlannerAgent,
    ArchitectAgent,
    ExecutorAgent,
    VerifierAgent,
)


async def main():
    print("=" * 70)
    print("🎯 Oh My Coder - 多智能体协作演示")
    print("=" * 70)
    print()
    
    # 获取 API Key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置 DEEPSEEK_API_KEY 环境变量")
        print("   export DEEPSEEK_API_KEY=your_key")
        return
    
    # 初始化路由器
    print("📡 初始化模型路由器...")
    config = RouterConfig(deepseek_api_key=api_key)
    router = ModelRouter(config)
    print("   ✓ DeepSeek 模型已就绪\n")
    
    # 演示任务
    task = "开发一个简单的计算器 CLI 应用，支持加减乘除运算"
    
    print(f"📝 任务: {task}")
    print()
    print("=" * 70)
    
    # 工作流步骤
    steps = [
        ("🔍 探索", ExploreAgent, "探索现有代码库结构"),
        ("📊 分析", AnalystAgent, "分析需求和约束"),
        ("📋 规划", PlannerAgent, "制定执行计划"),
        ("🏗️ 设计", ArchitectAgent, "设计系统架构"),
    ]
    
    results = {}
    
    for i, (name, agent_class, description) in enumerate(steps, 1):
        print(f"\n{i}. {name} Agent")
        print(f"   📌 {description}")
        print("-" * 70)
        
        agent = agent_class(router)
        context = AgentContext(
            project_path=Path("."),
            task_description=task,
            previous_outputs=results,
        )
        
        result = await agent.execute(context)
        results[agent_class.name] = result
        
        if result.status.value == "completed":
            # 显示结果摘要
            content = result.result
            lines = content.split("\n")
            # 显示前 15 行
            for line in lines[:15]:
                print(f"   {line}")
            if len(lines) > 15:
                print(f"   ... ({len(lines) - 15} more lines)")
        else:
            print(f"   ❌ 失败: {result.error}")
        
        print()
    
    # 显示统计
    print("=" * 70)
    print("📊 执行统计")
    print("=" * 70)
    
    stats = router.get_stats()
    print(f"   总请求数: {stats['total_requests']}")
    print(f"   提供商分布: {stats['provider_distribution']}")
    print(f"   层级分布: {stats['tier_distribution']}")
    print()
    
    print("=" * 70)
    print("✅ 演示完成!")
    print("=" * 70)
    print()
    print("💡 提示:")
    print("   - 查看完整结果，运行: python -m src.cli agents")
    print("   - 测试其他 Agent，运行: python -m src.cli status")
    print()


if __name__ == "__main__":
    asyncio.run(main())
