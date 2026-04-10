"""
高级示例：多 Agent 协作和多模型使用

演示：
1. 多 Agent 协作
2. 多模型配置
3. 工作流编排
4. 任务总结
"""

import asyncio
from pathlib import Path

from src.core.orchestrator import Orchestrator
from src.core.router import ModelRouter, RouterConfig
from src.core.summary import generate_summary, print_summary, save_summary


async def example_multi_agent():
    """
    示例 1: 多 Agent 协作

    演示如何让多个 Agent 按顺序或并行执行任务。
    """
    print("=== 多 Agent 协作示例 ===\n")

    # 初始化路由器和编排器
    config = RouterConfig()
    router = ModelRouter(config)
    orchestrator = Orchestrator(router)

    # 定义复杂任务
    task = """
    为电商系统实现商品搜索功能：
    1. 支持关键词搜索
    2. 支持分类筛选
    3. 支持价格区间过滤
    4. 支持分页和排序
    """

    # 执行完整构建工作流
    result = await orchestrator.execute_workflow(
        "build",
        {
            "project_path": ".",
            "task": task,
        },
    )

    print(f"工作流状态: {result.status}")
    print(f"执行时间: {result.execution_time:.2f}s")
    print(f"完成步骤: {result.steps_completed}")
    print(f"Token 消耗: {result.total_tokens:,}")

    return result


async def example_multi_model():
    """
    示例 2: 多模型配置和使用

    演示如何配置和使用多个模型提供商。
    """
    print("=== 多模型使用示例 ===\n")

    # 配置多个模型（实际使用时需要配置真实的 API Key）
    config = RouterConfig(
        deepseek_api_key="your_deepseek_key",
        kimi_api_key="your_kimi_key",
        glm_api_key="your_glm_key",
    )

    router = ModelRouter(config)

    # 查看路由器状态
    stats = router.get_stats()
    print(f"总请求数: {stats['total_requests']}")
    print(f"总成本: ¥{stats['total_cost']:.4f}")

    # 演示模型选择逻辑
    from src.core.router import TaskType

    decision = router.select(TaskType.EXPLORE)
    print(f"\nEXPLORE 任务选择: {decision.selected_provider} {decision.selected_tier}")

    decision = router.select(TaskType.ARCHITECTURE)
    print(
        f"ARCHITECTURE 任务选择: {decision.selected_provider} {decision.selected_tier}"
    )


async def example_workflow_orchestration():
    """
    示例 3: 工作流编排

    演示顺序、并行和条件执行模式。
    """
    print("=== 工作流编排示例 ===\n")

    config = RouterConfig(deepseek_api_key="test_key")
    router = ModelRouter(config)
    orchestrator = Orchestrator(router)

    # 顺序执行示例
    print("顺序执行模式：")
    sequential_workflow = {
        "name": "sequential_review",
        "steps": [
            {"agent": "explore", "required": True},
            {"agent": "code-reviewer", "required": True},
            {"agent": "security-reviewer", "required": True},
        ],
        "execution_mode": "sequential",
    }

    # 并行执行示例
    print("\n并行执行模式：")
    parallel_workflow = {
        "name": "parallel_analysis",
        "steps": [
            {"agent": "analyst", "required": True},
            {"agent": "explore", "required": True},
        ],
        "execution_mode": "parallel",
    }

    # 条件执行示例
    print("\n条件执行模式：")
    conditional_workflow = {
        "name": "adaptive_build",
        "steps": [
            {"agent": "explore", "required": True},
            {"agent": "analyst", "required": True},
            {
                "agent": "architect",
                "required": False,
                "condition": "complexity == 'high'",
            },
            {"agent": "executor", "required": True},
            {"agent": "verifier", "required": True},
        ],
        "execution_mode": "conditional",
    }

    print("工作流模板已定义")


async def example_task_summary():
    """
    示例 4: 任务总结

    演示如何生成和导出任务执行报告。
    """
    print("=== 任务总结示例 ===\n")

    # 模拟任务执行结果
    completed_steps = [
        {
            "agent": "ExploreAgent",
            "status": "completed",
            "duration": 2.3,
            "tokens": 1200,
            "result": "发现 89 个文件，识别为 FastAPI 项目",
        },
        {
            "agent": "AnalystAgent",
            "status": "completed",
            "duration": 5.1,
            "tokens": 3500,
            "result": "识别 3 个实体：Product, Category, Order",
        },
        {
            "agent": "ArchitectAgent",
            "status": "completed",
            "duration": 8.2,
            "tokens": 5200,
            "result": "设计 RESTful API 接口规范",
        },
        {
            "agent": "ExecutorAgent",
            "status": "completed",
            "duration": 15.7,
            "tokens": 12000,
            "result": "生成 8 个文件，共 450 行代码",
        },
        {
            "agent": "VerifierAgent",
            "status": "completed",
            "duration": 10.3,
            "tokens": 4800,
            "result": "pytest 18/18 通过",
        },
    ]

    # 生成总结
    summary = generate_summary(
        task="为电商系统实现商品搜索功能",
        workflow="build",
        completed_steps=completed_steps,
    )

    # 打印到终端
    print_summary(summary)

    # 导出为多种格式
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)

    # JSON 格式（机器解析）
    json_path = save_summary(summary, format="json", output_dir=output_dir)
    print(f"\nJSON 报告已保存: {json_path}")

    # HTML 格式（分享报告）
    html_path = save_summary(summary, format="html", output_dir=output_dir)
    print(f"HTML 报告已保存: {html_path}")

    # TXT 格式（快速查看）
    txt_path = save_summary(summary, format="txt", output_dir=output_dir)
    print(f"TXT 报告已保存: {txt_path}")


async def example_custom_agent_workflow():
    """
    示例 5: 自定义工作流

    演示如何创建和执行自定义工作流。
    """
    print("=== 自定义工作流示例 ===\n")

    # 定义自定义工作流
    custom_workflow = {
        "name": "smart_test",
        "description": "智能测试生成工作流",
        "steps": [
            # 第一步：探索项目结构
            {
                "agent": "explore",
                "required": True,
                "timeout": 30,
            },
            # 第二步：分析需要测试的模块
            {
                "agent": "analyst",
                "required": True,
                "timeout": 60,
            },
            # 第三步：生成测试用例
            {
                "agent": "test-engineer",
                "required": True,
                "timeout": 120,
            },
            # 第四步：运行测试验证
            {
                "agent": "verifier",
                "required": True,
                "timeout": 60,
            },
        ],
        "execution_mode": "sequential",
        "retry_policy": {
            "max_retries": 2,
            "backoff_factor": 2.0,
        },
    }

    print("自定义工作流定义：")
    print(f"名称: {custom_workflow['name']}")
    print(f"描述: {custom_workflow['description']}")
    print(f"执行模式: {custom_workflow['execution_mode']}")
    print(f"步骤数: {len(custom_workflow['steps'])}")

    return custom_workflow


async def main():
    """运行所有示例"""
    examples = [
        ("多 Agent 协作", example_multi_agent),
        ("多模型配置", example_multi_model),
        ("工作流编排", example_workflow_orchestration),
        ("任务总结", example_task_summary),
        ("自定义工作流", example_custom_agent_workflow),
    ]

    for name, example_func in examples:
        print("\n" + "=" * 60)
        print(f"示例: {name}")
        print("=" * 60)
        await example_func()
        print()


if __name__ == "__main__":
    print("=" * 60)
    print("Oh My Coder 高级示例")
    print("=" * 60)

    asyncio.run(main())
