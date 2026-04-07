#!/usr/bin/env python3
"""
高级示例 - 展示 Oh My Coder 的进阶用法

覆盖：
1. 多模型动态切换
2. Agent 协作与并行执行
3. 复杂任务处理
4. 任务总结生成

运行方式：
    python examples/advanced_demo.py

前置条件：
    export DEEPSEEK_API_KEY=your_key_here
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.base import ModelConfig, ModelProvider, ModelTier
from src.models.deepseek import DeepSeekModel
from src.models.kimi import KimiModel
from src.models.glm import GLMModel
from src.core.router import ModelRouter, RouterConfig, TaskType
from src.core.orchestrator import Orchestrator, WORKFLOW_TEMPLATES
from src.core.summary import TaskSummary, generate_summary, print_summary
from src.agents.explore import ExploreAgent
from src.agents.analyst import AnalystAgent
from src.agents.architect import ArchitectAgent
from src.agents.executor import ExecutorAgent


# ============================================================
# 示例 1: 多模型动态切换
# ============================================================
def demo_multi_model_routing():
    """演示如何在运行时动态切换不同模型"""
    print("\n" + "=" * 60)
    print("示例 1: 多模型动态切换")
    print("=" * 60)

    # 初始化路由器（可配置多个模型）
    config = RouterConfig(
        deepseek_api_key="your-deepseek-key",  # 替换为真实 Key
        kimi_api_key="your-kimi-key",          # 替换为真实 Key
        glm_api_key="your-glm-key",            # 替换为真实 Key
    )
    router = ModelRouter(config)

    # 查看可用模型
    stats = router.get_stats()
    print(f"\n📊 已注册模型数: {stats['total_requests']} (刚初始化)")
    print(f"💰 累计成本: ¥{stats['total_cost']:.4f}")

    # 针对不同任务类型，系统自动选择最优模型
    tasks = [
        (TaskType.EXPLORE, "探索项目结构"),
        (TaskType.ANALYSIS, "分析需求细节"),
        (TaskType.ARCHITECTURE, "设计系统架构"),
        (TaskType.CODE_GENERATION, "生成 REST API 代码"),
        (TaskType.REVIEW, "审查代码质量"),
    ]

    print("\n🔄 路由决策演示：")
    print("-" * 50)
    for task_type, desc in tasks:
        decision = router.select(task_type)
        print(f"  {desc:<30} → {decision.selected_tier:>6} tier "
              f"({decision.provider.value:>10}, ¥{decision.estimated_cost:.4f})")

    # 手动强制使用特定模型
    print("\n🔧 手动指定模型示例：")
    print("-" * 50)

    # 强制使用 Kimi（长上下文任务）
    kimi_config = ModelConfig(
        api_key="your-kimi-key",
        provider=ModelProvider.KIMI,
        tier=ModelTier.HIGH,
    )
    kimi_model = KimiModel(kimi_config, ModelTier.HIGH)
    print(f"  强制使用 Kimi: {kimi_model.model_name} "
          f"(适合 128K 上下文的大代码库分析)")

    # 强制使用 DeepSeek（低成本任务）
    deepseek_config = ModelConfig(
        api_key="your-deepseek-key",
        provider=ModelProvider.DEEPSEEK,
        tier=ModelTier.LOW,
    )
    deepseek_model = DeepSeekModel(deepseek_config, ModelTier.LOW)
    print(f"  强制使用 DeepSeek: {deepseek_model.model_name} "
          f"(性价比最高，免费额度)")

    # 强制使用 GLM（快速响应）
    glm_config = ModelConfig(
        api_key="your-glm-key",
        provider=ModelProvider.GLM,
        tier=ModelTier.MEDIUM,
    )
    glm_model = GLMModel(glm_config, ModelTier.MEDIUM)
    print(f"  强制使用 GLM: {glm_model.model_name} "
          f"(函数调用支持好)")

    return router


# ============================================================
# 示例 2: Agent 协作示例
# ============================================================
async def demo_agent_collaboration():
    """演示多个 Agent 如何协作完成复杂任务"""
    print("\n" + "=" * 60)
    print("示例 2: Agent 协作（构建工作流）")
    print("=" * 60)

    config = RouterConfig(deepseek_api_key="your-deepseek-key")
    router = ModelRouter(config)
    orchestrator = Orchestrator(router)

    project_path = Path(__file__).parent.parent

    # 场景：为一个新模块设计架构并生成代码
    task = "为电商系统添加订单管理模块"

    print(f"\n📋 任务: {task}")
    print(f"📁 项目: {project_path}")

    # 方式 A：使用编排引擎自动协作
    print("\n🔄 方式 A: Orchestrator 自动编排")
    print("-" * 50)

    workflow_steps = [
        ("explore", {"path": str(project_path), "depth": 2}),
        ("analyst", {"task": task}),
        ("architect", {"task": task}),
        ("executor", {"task": task, "language": "python"}),
    ]

    print("  工作流步骤:")
    for i, (agent_name, params) in enumerate(workflow_steps, 1):
        print(f"    {i}. {agent_name} - {params}")

    # 注意：由于没有真实 API Key，这里演示结构
    # 实际运行时替换 your-deepseek-key 为真实 Key
    print("\n  ⚠️  注意：需要配置真实的 API Key 才能运行")
    print("  export DEEPSEEK_API_KEY=sk-xxxxx")

    # 方式 B：手动 Agent 协作链
    print("\n🔄 方式 B: 手动 Agent 协作链")
    print("-" * 50)

    agents = [
        ("ExploreAgent", "扫描项目结构，识别技术栈"),
        ("AnalystAgent", "分析订单模块需求和实体"),
        ("ArchitectAgent", "设计 RESTful API 架构"),
        ("ExecutorAgent", "生成 Python 代码"),
        ("VerifierAgent", "验证代码语法和测试"),
    ]

    for i, (agent_name, desc) in enumerate(agents, 1):
        status = "✅" if i < len(agents) else "⏳"
        print(f"  {status} {i}. {agent_name:<20} - {desc}")

    print("\n  数据流向:")
    print("    探索结果 ──→ 分析结果 ──→ 架构设计 ──→ 代码生成 ──→ 验证通过")

    # 方式 C：并行执行（适合独立任务）
    print("\n🔄 方式 C: 并行 Agent 执行")
    print("-" * 50)

    parallel_tasks = [
        ("CodeReviewerAgent", "审查 src/agents/ 代码"),
        ("SecurityReviewerAgent", "扫描 src/agents/ 安全"),
        ("TestEngineerAgent", "生成 src/agents/ 测试"),
    ]

    print("  三个 Agent 同时执行（互相独立）：")
    for agent_name, desc in parallel_tasks:
        print(f"  ⚡ {agent_name:<25} - {desc}")

    print("  总耗时 ≈ max(t1, t2, t3) 而非 t1 + t2 + t3")

    return orchestrator


# ============================================================
# 示例 3: 复杂任务处理
# ============================================================
def demo_complex_task():
    """演示如何处理需要多轮交互的复杂任务"""
    print("\n" + "=" * 60)
    print("示例 3: 复杂任务处理")
    print("=" * 60)

    # 场景：重构整个后端模块
    complex_task = """
    重构 user 模块：
    1. 将同步 API 改为异步
    2. 添加 JWT 认证
    3. 实现 Redis 缓存
    4. 添加完整的单元测试
    5. 更新 Swagger 文档
    """

    print(f"\n📋 复杂任务分解：")
    print("-" * 50)
    steps = [
        ("探索", "ExploreAgent", "分析现有 user 模块结构"),
        ("分析", "AnalystAgent", "识别依赖关系和技术债务"),
        ("计划", "PlannerAgent", "制定重构步骤和风险点"),
        ("设计", "ArchitectAgent", "设计新的异步架构"),
        ("执行", "ExecutorAgent", "逐步重构代码"),
        ("验证", "VerifierAgent", "运行测试确保功能正常"),
        ("审查", "CodeReviewerAgent", "代码质量审查"),
        ("安全", "SecurityReviewerAgent", "安全漏洞扫描"),
        ("文档", "WriterAgent", "更新 API 文档"),
    ]

    for i, (step, agent, desc) in enumerate(steps, 1):
        print(f"  {i}. [{step}] {agent}")
        print(f"     └─ {desc}")

    # 使用任务总结功能
    print("\n📊 任务总结示例（模拟）：")
    print("-" * 50)

    # 模拟执行结果
    mock_summary = TaskSummary(
        task="重构 user 模块为异步架构",
        workflow="build",
        duration_seconds=125.5,
        total_tokens=45230,
        cost=0.89,
        steps_completed=[
            ("explore", True, "发现 12 个文件，识别为 FastAPI 项目"),
            ("analyst", True, "识别 8 个端点，3 个模型实体"),
            ("architect", True, "设计异步架构，引入 httpx + SQLAlchemy 2.0"),
            ("executor", True, "重构 8 个文件，新增 3 个文件"),
            ("verifier", True, "pytest 通过 24/24"),
            ("review", True, "代码质量评分: 8.5/10"),
            ("security", True, "发现 0 个高危漏洞"),
        ],
        agent_count=7,
        models_used=["deepseek-chat", "deepseek-chat", "deepseek-reasoner"],
    )

    print_summary(mock_summary)

    return mock_summary


# ============================================================
# 示例 4: 任务总结功能
# ============================================================
def demo_summary_feature():
    """演示任务总结功能的使用"""
    print("\n" + "=" * 60)
    print("示例 4: 任务总结功能")
    print("=" * 60)

    from src.core.summary import generate_summary, save_summary, load_summary

    # 场景：记录一次完整的工作流执行
    completed_steps = [
        {
            "agent": "ExploreAgent",
            "status": "completed",
            "duration": 2.3,
            "tokens": 1200,
            "result": "发现项目包含 45 个 Python 文件，技术栈为 FastAPI + SQLAlchemy",
        },
        {
            "agent": "AnalystAgent",
            "status": "completed",
            "duration": 5.1,
            "tokens": 3500,
            "result": "识别出 User/Order/Product 三个核心实体，8 个 API 端点",
        },
        {
            "agent": "ArchitectAgent",
            "status": "completed",
            "duration": 8.2,
            "tokens": 5200,
            "result": "设计了基于 Repository 模式的分层架构",
        },
        {
            "agent": "ExecutorAgent",
            "status": "completed",
            "duration": 15.7,
            "tokens": 12000,
            "result": "生成了 user_crud.py (180行), order_crud.py (210行)",
        },
        {
            "agent": "VerifierAgent",
            "status": "completed",
            "duration": 10.3,
            "tokens": 4800,
            "result": "pytest 全部通过 (18/18)，覆盖率 85%",
        },
    ]

    # 生成总结
    summary = generate_summary(
        task="为电商系统实现用户和订单 CRUD 模块",
        workflow="build",
        completed_steps=completed_steps,
        project_path="/path/to/project",
    )

    print("\n📋 自动生成的总结：")
    print("-" * 50)
    print_summary(summary)

    # 保存到文件
    output_dir = Path(__file__).parent.parent / "reports"
    output_dir.mkdir(exist_ok=True)
    save_path = save_summary(summary, output_dir=output_dir)
    print(f"\n💾 总结已保存到: {save_path}")

    # 从文件加载
    loaded = load_summary(save_path)
    print(f"📖 从文件加载: {loaded.task}")

    return summary


# ============================================================
# 示例 5: 自定义工作流
# ============================================================
def demo_custom_workflow():
    """演示如何定义和使用自定义工作流"""
    print("\n" + "=" * 60)
    print("示例 5: 自定义工作流")
    print("=" * 60)

    from src.core.orchestrator import WORKFLOW_TEMPLATES

    # 查看内置工作流
    print("\n📦 内置工作流模板：")
    print("-" * 50)
    for name, steps in WORKFLOW_TEMPLATES.items():
        agent_names = [s["agent"] for s in steps]
        print(f"  {name:<10}: {' → '.join(agent_names)}")

    # 自定义工作流：技术调研
    research_workflow = [
        {"agent": "ExploreAgent", "mode": "sequential", "timeout": 30},
        {"agent": "ScientistAgent", "mode": "sequential", "timeout": 120},
        {"agent": "WriterAgent", "mode": "sequential", "timeout": 60},
        {"agent": "CriticAgent", "mode": "sequential", "timeout": 30},
    ]

    print("\n🛠️  自定义工作流示例（技术调研）：")
    print("-" * 50)
    for i, step in enumerate(research_workflow, 1):
        print(f"  {i}. {step['agent']} (timeout={step['timeout']}s)")

    # 自定义工作流：代码重构
    refactor_workflow = [
        {"agent": "ExploreAgent", "mode": "sequential"},
        {"agent": "AnalystAgent", "mode": "sequential"},
        {"agent": "CodeSimplifierAgent", "mode": "sequential"},
        {"agent": "CodeReviewerAgent", "mode": "sequential"},
        {"agent": "VerifierAgent", "mode": "sequential"},
    ]

    print("\n🛠️  自定义工作流示例（代码重构）：")
    print("-" * 50)
    for i, step in enumerate(refactor_workflow, 1):
        print(f"  {i}. {step['agent']}")

    return research_workflow


# ============================================================
# 主函数
# ============================================================
async def main():
    print("""
╔══════════════════════════════════════════════════════╗
║        Oh My Coder 高级示例                         ║
║  多模型切换 · Agent 协作 · 复杂任务 · 任务总结        ║
╚══════════════════════════════════════════════════════╝
    """)

    demos = [
        ("多模型动态切换", demo_multi_model_routing),
        ("Agent 协作示例", demo_agent_collaboration),
        ("复杂任务处理", demo_complex_task),
        ("任务总结功能", demo_summary_feature),
        ("自定义工作流", demo_custom_workflow),
    ]

    for i, (name, demo_fn) in enumerate(demos, 1):
        try:
            if asyncio.iscoroutinefunction(demo_fn):
                await demo_fn()
            else:
                demo_fn()
        except Exception as e:
            print(f"\n⚠️  示例 {i} 执行时出现非关键错误: {e}")
            import traceback
            traceback.print_exc()

    print("""
╔══════════════════════════════════════════════════════╗
║                   示例运行完毕                        ║
║                                                        ║
║  提示：                                               ║
║  • 需要配置真实的 API Key 才能调用模型                 ║
║  • 查看 src/core/summary.py 了解总结功能               ║
║  • 查看 src/agents/ 了解所有 Agent                    ║
╚══════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    asyncio.run(main())
