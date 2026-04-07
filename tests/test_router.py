"""
测试模型路由器和 DeepSeek 适配器

运行: pytest tests/test_router.py -v
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.router import ModelRouter, RouterConfig, TaskType
from src.models.base import (
    Message,
    ModelConfig,
    ModelProvider,
    ModelTier,
)
from src.models.deepseek import DeepSeekModel


class TestDeepSeekModel:
    """测试 DeepSeek 模型适配器"""

    def test_init(self):
        """测试初始化"""
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.DEEPSEEK
        assert model.tier == ModelTier.MEDIUM
        assert model.model_name == "deepseek-chat"

    def test_format_messages(self):
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

    @pytest.mark.asyncio
    async def test_generate_mock(self):
        """测试生成（模拟）"""
        config = ModelConfig(api_key="test_key")
        model = DeepSeekModel(config, ModelTier.MEDIUM)

        # 模拟 HTTP 响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {"content": "Hello! How can I help you?"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        mock_response.raise_for_status = MagicMock()

        # 模拟 HTTP 客户端
        with patch.object(model, "_get_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = client

            messages = [Message(role="user", content="Hello")]
            response = await model.generate(messages)

            assert response.content == "Hello! How can I help you?"
            assert response.usage.total_tokens == 30


class TestModelRouter:
    """测试模型路由器"""

    def test_init(self):
        """测试初始化"""
        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        stats = router.get_stats()
        assert stats["total_requests"] == 0
        assert stats["total_cost"] == 0.0

    def test_select_low_tier(self):
        """测试 LOW tier 任务路由"""
        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        decision = router.select(TaskType.EXPLORE)

        assert decision.selected_tier == "low"
        assert decision.selected_provider == "deepseek"

    def test_select_high_tier(self):
        """测试 HIGH tier 任务路由"""
        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        decision = router.select(TaskType.ARCHITECTURE)

        assert decision.selected_tier == "high"
        assert decision.selected_provider == "deepseek"

    def test_select_with_complexity(self):
        """测试复杂度调整"""
        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        # MEDIUM 任务，高复杂度 -> HIGH
        decision = router.select(TaskType.CODE_GENERATION, complexity="high")
        assert decision.selected_tier == "high"

        # MEDIUM 任务，低复杂度 -> LOW
        decision = router.select(TaskType.CODE_GENERATION, complexity="low")
        assert decision.selected_tier == "low"


class TestExploreAgent:
    """测试 Explore Agent"""

    def test_scan_directory(self):
        """测试目录扫描"""
        from pathlib import Path

        from src.agents.explore import ExploreAgent

        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)
        agent = ExploreAgent(router)

        # 扫描当前项目
        project_path = Path(
            "/Users/vobc/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder"
        )
        structure = agent._scan_directory(project_path, max_depth=2)

        assert "src/" in structure
        assert "docs/" in structure

    def test_collect_file_stats(self):
        """测试文件统计"""
        from pathlib import Path

        from src.agents.explore import ExploreAgent

        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)
        agent = ExploreAgent(router)

        project_path = Path(
            "/Users/vobc/.qclaw/workspace-agent-bf627e2b/projects/oh-my-coder"
        )
        stats = agent._collect_file_stats(project_path)

        assert stats["total_files"] > 0
        assert "Python" in stats["language_distribution"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
