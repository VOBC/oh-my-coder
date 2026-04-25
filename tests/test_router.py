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

        # 扫描当前项目（使用相对路径，兼容 CI 环境）
        project_path = Path(__file__).parent.parent
        structure = agent._scan_directory(project_path, max_depth=2)

        assert "src/" in structure
        assert "tests/" in structure

    def test_collect_file_stats(self):
        """测试文件统计"""
        from pathlib import Path

        from src.agents.explore import ExploreAgent

        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)
        agent = ExploreAgent(router)

        # 使用相对路径，兼容 CI 环境
        project_path = Path(__file__).parent.parent
        stats = agent._collect_file_stats(project_path)

        assert stats["total_files"] > 0
        assert "Python" in stats["language_distribution"]


class TestRateLimitHandling:
    """测试 429 限流错误处理"""

    @pytest.mark.asyncio
    async def test_429_skips_retry_and_switches_provider(self):
        """429 限流应跳过重试，直接切换到下一个 provider"""
        import httpx

        config = RouterConfig(
            deepseek_api_key="test_key",
            glm_api_key="test_glm_key",
        )
        router = ModelRouter(config)

        # 模拟 DeepSeek 429 响应
        mock_429_response = MagicMock()
        mock_429_response.status_code = 429
        http_error_429 = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=mock_429_response,
        )

        # 模拟 GLM 成功响应 - 用真实的 ModelResponse 对象
        from src.models.base import ModelResponse, Usage

        success_response = ModelResponse(
            content="Success from GLM",
            model="glm-4-flash",
            provider="glm",
            tier=ModelTier.LOW,
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            finish_reason="stop",
        )

        # 设置 mock: DeepSeek 抛 429, GLM 成功
        deepseek_model = router._models.get("deepseek", {}).get("low")
        glm_model = router._models.get("glm", {}).get("low")

        if deepseek_model and glm_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = http_error_429

                with patch.object(
                    glm_model, "generate", new_callable=AsyncMock
                ) as mock_glm:
                    mock_glm.return_value = success_response

                    # DeepSeek 429 -> 应立即切换到 GLM，不等 3 次重试
                    messages = [Message(role="user", content="test")]
                    response = await router.route_and_call(TaskType.EXPLORE, messages)

                    # 验证: DeepSeek 只被调用 1 次 (429 后不再重试)
                    assert mock_ds.call_count == 1
                    # 验证: GLM 被调用 (failover 成功)
                    assert mock_glm.call_count >= 1
                    # 验证: 返回的是 GLM 的响应
                    assert response.content == "Success from GLM"

    @pytest.mark.asyncio
    async def test_single_provider_429_raises_rate_limit_error(self):
        """单 provider 时 429 应立即抛 RateLimitError，不重试 3 次"""
        import httpx

        from src.core.router import RateLimitError

        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        # 模拟 429 响应
        mock_429_response = MagicMock()
        mock_429_response.status_code = 429
        http_error_429 = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=mock_429_response,
        )

        deepseek_model = router._models.get("deepseek", {}).get("low")
        if deepseek_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = http_error_429

                messages = [Message(role="user", content="test")]

                # 应立即抛 RateLimitError
                with pytest.raises(RateLimitError) as exc_info:
                    await router.route_and_call(TaskType.EXPLORE, messages)

                # 验证错误信息包含建议
                err_msg = str(exc_info.value)
                assert "限流" in err_msg
                assert "等待" in err_msg or "API Key" in err_msg

                # 验证: 只调用 1 次 (429 不重试)
                assert mock_ds.call_count == 1

    @pytest.mark.asyncio
    async def test_other_http_errors_retry_3_times(self):
        """其他 HTTP 错误（如 500）应重试 3 次"""
        import httpx

        from src.core.router import NoModelAvailableError

        config = RouterConfig(deepseek_api_key="test_key")
        router = ModelRouter(config)

        # 模拟 500 响应
        mock_500_response = MagicMock()
        mock_500_response.status_code = 500
        http_error_500 = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=mock_500_response,
        )

        deepseek_model = router._models.get("deepseek", {}).get("low")
        if deepseek_model:
            with patch.object(
                deepseek_model, "generate", new_callable=AsyncMock
            ) as mock_ds:
                mock_ds.side_effect = http_error_500

                messages = [Message(role="user", content="test")]

                # 500 应重试 3 次后抛 NoModelAvailableError
                with pytest.raises(NoModelAvailableError):
                    await router.route_and_call(TaskType.EXPLORE, messages)

                # 验证: 调用 3 次 (重试)
                assert mock_ds.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
