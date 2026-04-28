#!/usr/bin/env python3
"""
Oh My Coder - 多智能体协作演示脚本

本脚本演示如何使用 Oh My Coder 的多智能体系统：
1. explore Agent - 探索代码库结构
2. analyst Agent - 分析需求
3. executor Agent - 生成代码

运行方式：
    cd ~/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder
    python demo.py
"""
import asyncio
import os
from pathlib import Path

from src.agents import (  # Agent 列表
    AnalystAgent,  # 分析 Agent
    ExecutorAgent,  # 执行 Agent
    ExploreAgent,  # 探索 Agent
)
from src.agents.base import AgentContext  # Agent 上下文

# ============================================================
# 步骤 1: 导入 Oh My Coder 核心模块
# ============================================================
from src.core.router import ModelRouter, RouterConfig  # 模型路由器


# ============================================================
# 步骤 2: 初始化 Oh My Coder
# ============================================================
def init_oh_my_coder():
    """
    初始化 Oh My Coder
    
    1. 从环境变量获取 API Key
    2. 创建路由器配置
    3. 初始化模型路由器
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise ValueError(
            "❌ 请先设置 DeepSeek API Key:\n"
            "   export DEEPSEEK_API_KEY=sk-xxx\n"
            "   或创建 .env 文件写入 DEEPSEEK_API_KEY=sk-xxx"
        )

    # 创建路由器配置
    config = RouterConfig(
        deepseek_api_key=api_key,    # DeepSeek API Key
        daily_budget=10.0,           # 每日预算（元）
    )

    # 初始化路由器
    router = ModelRouter(config)

    print("✅ Oh My Coder 初始化成功!")
    print("   - 模型: DeepSeek")
    print(f"   - 每日预算: ¥{config.daily_budget}")
    print()

    return router


# ============================================================
# 步骤 3: 定义演示任务
# ============================================================
DEMO_TASK = """
开发一个简单的待办事项 CLI 应用（todo.py），功能如下：
- 添加任务：python todo.py add "买牛奶"
- 查看任务：python todo.py list
- 完成任务：python todo.py done <序号>
- 删除任务：python todo.py delete <序号>
- 数据存储：使用 JSON 文件保存
"""


# ============================================================
# 步骤 4: 定义工作流
# ============================================================
async def run_workflow(router: ModelRouter, project_path: Path):
    """
    执行多 Agent 协作工作流
    
    工作流：
    1. Explore Agent → 探索代码库结构
    2. Analyst Agent → 分析需求
    3. Executor Agent → 生成代码
    """
    print("=" * 70)
    print("🚀 开始执行多智能体工作流")
    print("=" * 70)
    print()

    # 存储各 Agent 的输出
    outputs = {}

    # --------------------------------------------------
    # 步骤 4.1: Explore Agent - 探索代码库
    # --------------------------------------------------
    print("📌 步骤 1/3: Explore Agent - 探索代码库结构")
    print("-" * 70)

    explore_agent = ExploreAgent(router)
    explore_context = AgentContext(
        project_path=project_path,           # 项目路径
        task_description="探索项目结构，了解现有代码组织方式",
    )

    explore_result = await explore_agent.execute(explore_context)
    outputs["explore"] = explore_result

    if explore_result.status.value == "completed":
        print("✅ Explore Agent 执行成功!\n")
        print("探索结果摘要:")
        print("-" * 40)
        # 显示前 30 行
        lines = explore_result.result.split("\n")[:30]
        for line in lines:
            print(f"  {line}")
        if len(explore_result.result.split("\n")) > 30:
            print("  ... (更多内容已省略)")
        print()
    else:
        print(f"❌ Explore Agent 执行失败: {explore_result.error}")
        return

    # --------------------------------------------------
    # 步骤 4.2: Analyst Agent - 分析需求
    # --------------------------------------------------
    print("📌 步骤 2/3: Analyst Agent - 分析需求")
    print("-" * 70)

    analyst_agent = AnalystAgent(router)
    analyst_context = AgentContext(
        project_path=project_path,
        task_description=DEMO_TASK,
        previous_outputs=outputs,  # 传递 Explore 的结果
    )

    analyst_result = await analyst_agent.execute(analyst_context)
    outputs["analyst"] = analyst_result

    if analyst_result.status.value == "completed":
        print("✅ Analyst Agent 执行成功!\n")
        print("需求分析摘要:")
        print("-" * 40)
        lines = analyst_result.result.split("\n")[:30]
        for line in lines:
            print(f"  {line}")
        if len(analyst_result.result.split("\n")) > 30:
            print("  ... (更多内容已省略)")
        print()
    else:
        print(f"❌ Analyst Agent 执行失败: {analyst_result.error}")
        return

    # --------------------------------------------------
    # 步骤 4.3: Executor Agent - 生成代码
    # --------------------------------------------------
    print("📌 步骤 3/3: Executor Agent - 生成代码")
    print("-" * 70)

    executor_agent = ExecutorAgent(router)
    executor_context = AgentContext(
        project_path=project_path,
        task_description=DEMO_TASK,
        previous_outputs=outputs,  # 传递前两个 Agent 的结果
    )

    executor_result = await executor_agent.execute(executor_context)
    outputs["executor"] = executor_result

    if executor_result.status.value == "completed":
        print("✅ Executor Agent 执行成功!\n")
        print("生成的代码:")
        print("=" * 50)
        print(executor_result.result)
        print("=" * 50)
        print()

        # 保存代码到文件
        save_code(executor_result.result, project_path)
    else:
        print(f"❌ Executor Agent 执行失败: {executor_result.error}")
        return

    # --------------------------------------------------
    # 步骤 5: 显示执行统计
    # --------------------------------------------------
    print("📊 执行统计")
    print("-" * 70)

    stats = router.get_stats()
    print(f"   总请求数: {stats['total_requests']}")
    print(f"   提供商分布: {stats['provider_distribution']}")
    print(f"   层级分布: {stats['tier_distribution']}")
    print()


def save_code(code: str, project_path: Path):
    """
    保存生成的代码到文件
    """
    # 提取 Python 代码（去掉 markdown 代码块标记）
    if "```python" in code:
        start = code.find("```python") + 9
        end = code.find("```", start)
        code = code[start:end].strip()
    elif "```" in code:
        start = code.find("```") + 3
        end = code.rfind("```")
        code = code[start:end].strip()

    output_file = project_path / "todo_demo.py"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"💾 代码已保存到: {output_file}")
        print(f"   运行方式: python {output_file}")
    except Exception as e:
        print(f"⚠️ 保存代码失败: {e}")


# ============================================================
# 主函数
# ============================================================
async def main():
    """
    主函数 - 演示入口
    """
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "🎯 Oh My Coder 演示" + " " * 21 + "║")
    print("║" + " " * 15 + "多智能体协作 - Explore → Analyst → Executor" + " " * 6 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    try:
        # 1. 初始化
        router = init_oh_my_coder()

        # 2. 获取项目路径
        project_path = Path(__file__).parent

        # 3. 执行工作流
        await run_workflow(router, project_path)

        # 4. 完成
        print()
        print("🎉 演示完成!")
        print()
        print("📚 了解更多:")
        print("   - 查看所有 Agent: python -m src.cli agents")
        print("   - 查看系统状态: python -m src.cli status")
        print("   - 完整文档: cat README.md")
        print()

    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        print()
        print("💡 解决方案:")
        print("   1. 确保已设置 DeepSeek API Key:")
        print("      export DEEPSEEK_API_KEY=sk-xxx")
        print()
        print("   2. 或者在项目目录创建 .env 文件:")
        print("      echo 'DEEPSEEK_API_KEY=sk-xxx' > .env")
        print()


# ============================================================
# 程序入口
# ============================================================
if __name__ == "__main__":
    asyncio.run(main())
