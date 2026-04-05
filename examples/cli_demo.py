#!/usr/bin/env python3
"""
CLI 使用示例

展示如何使用 Oh My Coder 的命令行界面。

运行方式：
    python examples/cli_demo.py
"""
import subprocess
import sys
import time


def run(cmd: list[str], desc: str = ""):
    """执行命令并打印输出"""
    print(f"\n{'=' * 60}")
    print(f"🔧 {desc or ' '.join(cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd="..",  # 从 examples 目录回到项目根目录
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
        print(f"\n✅ 退出码: {result.returncode}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⏰ 命令执行超时")
        return False
    except FileNotFoundError:
        print(f"❌ 命令未找到: {cmd[0]}")
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════╗
║        Oh My Coder CLI 使用示例                      ║
╚══════════════════════════════════════════════════════╝
""")

    # 示例 1: 帮助信息
    run(
        [sys.executable, "-m", "src.cli", "--help"],
        "示例 1: 查看 CLI 帮助信息"
    )

    # 示例 2: 列出可用 Agent
    run(
        [sys.executable, "-m", "src.cli", "list"],
        "示例 2: 列出所有可用的 Agent"
    )

    # 示例 3: 探索当前目录
    run(
        [sys.executable, "-m", "src.cli", "explore", "."],
        "示例 3: 探索当前项目代码库"
    )

    # 示例 4: 直接提问
    run(
        [sys.executable, "-m", "src.cli", "ask", "Python 的列表推导式是什么？"],
        "示例 4: 直接向 AI 提问"
    )

    # 示例 5: 执行简单任务（展示工作流）
    print("""
    ═══════════════════════════════════════════════════════
    📌 示例 5-8: 执行具体任务

    以下示例展示了完整的工作流执行方式：

    # 完整开发流程（build）
    python -m src.cli run "实现一个 TODO 列表应用" -w build

    # 代码审查流程（review）
    python -m src.cli run "审查项目代码质量" -w review

    # 调试流程（debug）
    python -m src.cli run "修复登录失败的问题" -w debug

    # 测试流程（test）
    python -m src.cli run "为项目添加单元测试" -w test

    ═══════════════════════════════════════════════════════
    """)

    # 示例 6: 指定模型
    print("""
    ═══════════════════════════════════════════════════════
    📌 示例 6: 指定使用的模型

    # 使用 DeepSeek（默认，免费）
    python -m src.cli run "实现一个计算器" --model deepseek

    # 使用通义千问（需要配置 API Key）
    python -m src.cli run "实现一个计算器" --model tongyi

    # 使用文心一言（需要配置 API Key）
    python -m src.cli run "实现一个计算器" --model wenxin

    ═══════════════════════════════════════════════════════
    """)

    # 示例 7: 查看路由统计
    print("""
    ═══════════════════════════════════════════════════════
    📌 示例 7: 查看模型路由统计

    # 运行任务后，查看 Token 消耗和路由决策
    python -m src.cli run "实现一个计算器"
    python -m src.cli stats

    统计信息包括：
    - 各模型调用次数
    - Token 消耗明细
    - 成本估算
    - 路由决策历史

    ═══════════════════════════════════════════════════════
    """)

    print("""
    ╔══════════════════════════════════════════════════════╗
    ║              CLI 使用技巧                             ║
    ╠══════════════════════════════════════════════════════╣
    ║  1. 环境变量配置                                      ║
    ║     export DEEPSEEK_API_KEY=your_key                  ║
    ║                                                        ║
    ║  2. 在指定目录工作                                    ║
    ║     python -m src.cli explore /path/to/project         ║
    ║                                                        ║
    ║  3. 查看详细日志                                     ║
    ║     python -m src.cli run "任务" --verbose            ║
    ║                                                        ║
    ║  4. 保存输出到文件                                    ║
    ║     python -m src.cli run "任务" -o output.md         ║
    ╚══════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
