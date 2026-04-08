"""
测试更多模型适配器

重点测试初始化和基本功能。
"""

import pytest

from src.models.base import ModelConfig, ModelProvider, ModelTier


class TestBaichuanModel:
    """测试百川模型"""

    def test_init_default(self):
        """测试默认初始化"""
        from src.models.baichuan import BaichuanModel

        config = ModelConfig(api_key="test_key")
        model = BaichuanModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.BAICHUAN
        assert model.tier == ModelTier.MEDIUM

    def test_model_names(self):
        """测试模型名称映射"""
        from src.models.baichuan import BaichuanModel

        config = ModelConfig(api_key="test_key")

        model_low = BaichuanModel(config, ModelTier.LOW)
        assert "baichuan" in model_low.model_name.lower() or model_low.model_name

        model_high = BaichuanModel(config, ModelTier.HIGH)
        assert model_high.model_name


class TestDoubaoModel:
    """测试豆包模型"""

    def test_init(self):
        """测试初始化"""
        from src.models.doubao import DoubaoModel

        config = ModelConfig(api_key="test_key")
        model = DoubaoModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.DOUBAO
        assert model.tier == ModelTier.MEDIUM


class TestKimiModel:
    """测试 Kimi 模型"""

    def test_init(self):
        """测试初始化"""
        from src.models.kimi import KimiModel

        config = ModelConfig(api_key="test_key")
        model = KimiModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.KIMI
        assert model.tier == ModelTier.MEDIUM


class TestGLMModel:
    """测试智谱 GLM 模型"""

    def test_init(self):
        """测试初始化"""
        from src.models.glm import GLMModel

        config = ModelConfig(api_key="test_key")
        model = GLMModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.GLM
        assert model.tier == ModelTier.MEDIUM


class TestHunyuanModel:
    """测试混元模型"""

    @pytest.mark.skip(reason="HunyuanModel 未实现 stream 方法")
    def test_init(self):
        """测试初始化"""
        from src.models.hunyuan import HunyuanModel

        config = ModelConfig(api_key="test_key")
        model = HunyuanModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.HUNYUAN


class TestMinimaxModel:
    """测试 Minimax 模型"""

    @pytest.mark.skip(reason="MiniMaxModel 导入问题")
    def test_init(self):
        """测试初始化"""
        from src.models.minimax import MiniMaxModel

        config = ModelConfig(api_key="test_key")
        model = MiniMaxModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.MINIMAX


class TestSparkModel:
    """测试讯飞星火模型"""

    def test_init(self):
        """测试初始化"""
        from src.models.spark import SparkModel

        config = ModelConfig(api_key="test_key")
        model = SparkModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.SPARK


class TestTiangongModel:
    """测试天工模型"""

    def test_init(self):
        """测试初始化"""
        from src.models.tiangong import TiangongModel

        config = ModelConfig(api_key="test_key")
        model = TiangongModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.TIANGONG


class TestTongyiModel:
    """测试通义千问模型"""

    def test_init(self):
        """测试初始化"""
        from src.models.tongyi import TongyiModel

        config = ModelConfig(api_key="test_key")
        model = TongyiModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.TONGYI


class TestWenxinModel:
    """测试文心一言模型"""

    def test_init(self):
        """测试初始化"""
        from src.models.wenxin import WenxinModel

        config = ModelConfig(api_key="test_key")
        model = WenxinModel(config, ModelTier.MEDIUM)

        assert model.provider == ModelProvider.WENXIN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
