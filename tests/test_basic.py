"""快速验证脚本"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.explore import ExploreAgent
from src.core.router import ModelRouter, RouterConfig, TaskType
from src.models.base import (
    Message,
    ModelConfig,
    ModelProvider,
    ModelTier,
)
from src.models.deepseek import DeepSeekModel


def test_deepseek_init():
    """测试 DeepSeek 初始化"""
    config = ModelConfig(api_key="test_key")
    model = DeepSeekModel(config, ModelTier.MEDIUM)

    assert model.provider == ModelProvider.DEEPSEEK
    assert model.tier == ModelTier.MEDIUM
    assert model.model_name == "deepseek-chat"


def test_deepseek_format():
    """测试消息格式化"""
    config = ModelConfig(api_key="test_key")
    model = DeepSeekModel(config, ModelTier.MEDIUM)

    messages = [
        Message(role="system", content="You are a helpful assistant"),
        Message(role="user", content="Hello"),
    ]

    formatted = model._format_messages(messages)

    assert len(formatted) == 2
    assert formatted[0]["role"] == "system"
    assert formatted[1]["role"] == "user"


def test_router_init():
    """测试路由器初始化"""
    config = RouterConfig(deepseek_api_key="test_key")
    router = ModelRouter(config)

    stats = router.get_stats()
    assert stats["total_requests"] == 0
    assert stats["total_cost"] == 0.0


def test_router_select():
    """测试路由选择"""
    config = RouterConfig(deepseek_api_key="test_key")
    router = ModelRouter(config)

    # LOW tier
    decision = router.select(TaskType.EXPLORE)
    assert decision.selected_tier == "low"

    # HIGH tier
    decision = router.select(TaskType.ARCHITECTURE)
    assert decision.selected_tier == "high"

    # 复杂度调整
    decision = router.select(TaskType.CODE_GENERATION, complexity="high")
    assert decision.selected_tier == "high"


def test_explore_agent():
    """测试 Explore Agent"""
    config = RouterConfig(deepseek_api_key="test_key")
    router = ModelRouter(config)
    agent = ExploreAgent(router)

    # 测试属性
    assert agent.name == "explore"
    assert agent.default_tier == "low"

    # 测试目录扫描 - 使用当前项目路径
    project_path = Path(__file__).parent.parent
    structure = agent._scan_directory(project_path, max_depth=2)

    assert "src/" in structure
    assert "docs/" in structure

    # 测试文件统计
    stats = agent._collect_file_stats(project_path)

    assert stats["total_files"] > 0
    assert "Python" in stats["language_distribution"]


if __name__ == "__main__":
    try:
        test_deepseek_init()
        test_deepseek_format()
        test_router_init()
        test_router_select()
        test_explore_agent()

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)
