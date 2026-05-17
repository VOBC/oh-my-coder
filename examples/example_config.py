#!/usr/bin/env python3
"""
配置系统示例 - 展示如何加载和使用 Agent 配置文件

运行方式：
    python examples/example_config.py

本示例演示：
1. 加载 YAML 配置
2. 使用配置创建 Agent
3. 配置验证
4. 批量加载目录
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.agent_config import (
    AgentConfig,
    load_config_dir,
    load_config_file,
    validate_config_file,
)


def demo_load_single():
    """演示 1: 加载单个配置文件"""
    print("\n" + "=" * 60)
    print("演示 1: 加载单个配置文件")
    print("=" * 60)

    config_path = Path(__file__).parent.parent / "config" / "code-review.yaml"

    if not config_path.exists():
        print(f"⚠️  配置文件不存在: {config_path}")
        print("  先运行创建配置示例")
        return

    config = load_config_file(config_path)

    print(f"\n  名称: {config.name}")
    print(f"  描述: {config.description}")
    print(f"  模型: {config.model}")
    print(f"  温度: {config.environment.temperature}")
    print(f"  最大 Token: {config.environment.max_tokens}")
    print(f"  工具数量: {len(config.tools)}")

    print("\n  权限配置:")
    print(f"    白名单规则数: {len(config.permissions.get('allowed_patterns', []))}")
    print(f"    黑名单规则数: {len(config.permissions.get('denied_patterns', []))}")
    print(f"    需审批规则数: {len(config.permissions.get('require_approval', []))}")

    print("\n  System Prompt 预览（前 200 字）:")
    system_prompt = config.get_system_prompt()
    print(f"  {system_prompt[:200]}...")


def demo_validate():
    """演示 2: 验证配置文件"""
    print("\n" + "=" * 60)
    print("演示 2: 验证配置文件")
    print("=" * 60)

    config_path = Path(__file__).parent.parent / "config" / "code-review.yaml"

    if not config_path.exists():
        print("  ⚠️  配置文件不存在，跳过验证")
        return

    valid, errors = validate_config_file(config_path)

    if valid:
        print(f"  ✅ {config_path.name} 验证通过")
    else:
        print(f"  ❌ {config_path.name} 验证失败:")
        for error in errors:
            print(f"     - {error}")


def demo_batch_load():
    """演示 3: 批量加载配置目录"""
    print("\n" + "=" * 60)
    print("演示 3: 批量加载配置目录")
    print("=" * 60)

    config_dir = Path(__file__).parent.parent / "config"

    if not config_dir.exists():
        print(f"  ⚠️  配置目录不存在: {config_dir}")
        return

    configs = load_config_dir(config_dir)
    print(f"\n  发现 {len(configs)} 个配置文件:")

    for cfg in configs:
        print(f"  • {cfg.name:<25} | {cfg.description[:40]}")


def demo_render_template():
    """演示 4: 渲染 Prompt 模板"""
    print("\n" + "=" * 60)
    print("演示 4: 渲染 Prompt 模板")
    print("=" * 60)

    config_path = Path(__file__).parent.parent / "config" / "code-review.yaml"

    if not config_path.exists():
        print("  ⚠️  配置文件不存在，跳过模板演示")
        return

    config = load_config_file(config_path)

    # 模拟渲染 review_task 模板
    rendered = config.render_template(
        key="review_task",
        file_path="src/utils/helpers.py",
        language="python",
        code="def add(a, b):\n    return a + b",
    )

    print("\n  渲染后的 Prompt:")
    print("-" * 50)
    print(rendered)


def demo_agent_config_usage():
    """演示 5: 配置与 Agent 的实际使用"""
    print("\n" + "=" * 60)
    print("演示 5: Agent 配置实际使用场景")
    print("=" * 60)

    scenarios = [
        ("代码审查", "config/code-review.yaml", "审查 src/api/user.py 的代码质量"),
        ("安全扫描", "config/security-review.yaml", "扫描 src/auth 模块的安全漏洞"),
        ("快速评审", "config/quick-review.yaml", "快速检查 src/core 的代码"),
    ]

    for title, config_file, task in scenarios:
        config_path = Path(__file__).parent.parent / config_file
        status = "✅" if config_path.exists() else "⏳"

        print(f"\n  {status} {title}: {config_file}")
        if config_path.exists():
            cfg = load_config_file(config_path)
            print(f"     模型: {cfg.model} | 温度: {cfg.environment.temperature}")
            print(f"     任务示例: {task}")
        else:
            print("     配置文件待创建")


def demo_create_config():
    """演示 6: 程序化创建配置"""
    print("\n" + "=" * 60)
    print("演示 6: 程序化创建配置")
    print("=" * 60)

    # 创建一个自定义配置
    custom_config = AgentConfig(
        name="my-custom-agent",
        description="我的自定义 Agent",
        model="kimi",
        tools=["read", "grep", "shell"],
        permissions={
            "allowed_patterns": ["^ls", "^grep", "^cat"],
            "denied_patterns": ["rm -rf /", "drop database"],
            "require_approval": ["git push", "docker run"],
        },
        environment={
            "max_tokens": 12000,
            "temperature": 0.5,
            "timeout": 90,
            "retry": 3,
        },
        prompts={
            "system": "你是一个专注 Python 的开发助手，遵循 PEP 8 规范。",
            "review_task": "请审查以下代码: {{code}}",
        },
    )

    print("\n  创建的配置:")
    print(f"    名称: {custom_config.name}")
    print(f"    模型: {custom_config.model}")
    print(f"    工具: {', '.join(custom_config.tools)}")
    print(f"    Token 上限: {custom_config.environment.max_tokens}")

    # 验证
    errors = custom_config.validate()
    if errors:
        print("\n  验证错误:")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  ✅ 验证通过")

    # 序列化为 dict
    config_dict = custom_config.to_dict()
    print(f"\n  序列化后包含 {len(config_dict)} 个顶层字段")


def main():
    print(
        """
╔══════════════════════════════════════════════════════╗
║        Oh My Coder - 配置系统示例                   ║
╚══════════════════════════════════════════════════════╝
    """
    )

    demo_load_single()
    demo_validate()
    demo_batch_load()
    demo_render_template()
    demo_agent_config_usage()
    demo_create_config()

    print(
        """
╔══════════════════════════════════════════════════════╗
║                   示例运行完毕                       ║
║                                                        ║
║  相关命令:                                             ║
║  • omc config load config/code-review.yaml            ║
║  • omc config validate config/code-review.yaml        ║
║  • omc config create my_agent.yaml                    ║
╚══════════════════════════════════════════════════════╝
    """
    )


if __name__ == "__main__":
    main()
