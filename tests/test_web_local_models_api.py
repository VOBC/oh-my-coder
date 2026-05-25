"""
Tests for src/web/local_models_api.py

Tests LocalModelInfo, OllamaStatus, and FastAPI routes for local models.
"""
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 导入被测试模块
from src.web.local_models_api import (
    LocalModelInfo,
    OllamaStatus,
    router,
)


# ========================================
# Fixtures
# ========================================
@pytest.fixture
def app():
    """创建测试 FastAPI app"""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


# ========================================
# Model Tests
# ========================================
class TestLocalModelInfo:
    """测试 LocalModelInfo 模型"""

    def test_create_basic(self):
        """测试创建基本信息"""
        model = LocalModelInfo(name="qwen2:7b")
        assert model.name == "qwen2:7b"
        assert model.size is None
        assert model.modified_at is None
        assert model.tier is None
        assert model.description is None
        assert model.available is True

    def test_create_full(self):
        """测试创建完整信息"""
        model = LocalModelInfo(
            name="llama3:70b",
            size="39.8 GB",
            modified_at="2026-05-20T10:00:00",
            tier="high",
            description="Meta Llama 3 - 通用对话模型",
            available=True,
        )
        assert model.name == "llama3:70b"
        assert model.size == "39.8 GB"
        assert model.tier == "high"


class TestOllamaStatus:
    """测试 OllamaStatus 模型"""

    def test_create_available(self):
        """测试创建可用状态"""
        status = OllamaStatus(
            available=True,
            base_url="http://localhost:11434",
            models=[],
        )
        assert status.available is True
        assert status.base_url == "http://localhost:11434"
        assert status.models == []
        assert status.error is None

    def test_create_unavailable(self):
        """测试创建不可用状态"""
        status = OllamaStatus(
            available=False,
            base_url="http://localhost:11434",
            models=[],
            error="Ollama 服务未运行",
        )
        assert status.available is False
        assert status.error == "Ollama 服务未运行"


# ========================================
# API Route Tests - /status
# ========================================
class TestGetOllamaStatus:
    """测试 GET /api/local-models/status"""

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_available_no_models(self, mock_list_models, mock_is_available, client):
        """测试 Ollama 可用但无模型"""
        mock_is_available.return_value = True
        mock_list_models.return_value = []

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["base_url"] == "http://localhost:11434"
        assert data["models"] == []
        assert data["error"] is None

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_available_with_models(self, mock_list_models, mock_is_available, client):
        """测试 Ollama 可用且有模型"""
        mock_is_available.return_value = True
        mock_list_models.return_value = [
            {"name": "qwen2:7b", "size": 4_300_000_000, "modified_at": "2026-05-20T10:00:00"},
            {"name": "llama3:70b", "size": 39_800_000_000, "modified_at": "2026-05-19T10:00:00"},
        ]

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert len(data["models"]) == 2

        # 检查第一个模型
        assert data["models"][0]["name"] == "qwen2:7b"
        assert data["models"][0]["size"] == "4.3 GB"
        assert data["models"][0]["tier"] == "low"  # :7b -> low
        assert "阿里通义千问" in data["models"][0]["description"]

        # 检查第二个模型
        assert data["models"][1]["name"] == "llama3:70b"
        assert data["models"][1]["size"] == "39.8 GB"
        assert data["models"][1]["tier"] == "high"  # :70b -> high

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_unavailable(self, mock_is_available, client):
        """测试 Ollama 不可用"""
        mock_is_available.return_value = False

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert data["models"] == []
        assert "Ollama 服务未运行" in data["error"]

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_exception(self, mock_is_available, client):
        """测试异常错误"""
        mock_is_available.side_effect = Exception("Connection refused")

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert data["error"] == "Exception"

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_custom_base_url(self, mock_list_models, mock_is_available, client):
        """测试自定义 base_url"""
        mock_is_available.return_value = True
        mock_list_models.return_value = []

        with patch("os.getenv", return_value="http://custom:11434"):
            response = client.get("/api/local-models/status")
            assert response.status_code == 200
            data = response.json()
            assert data["base_url"] == "http://custom:11434"

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_model_tier_inference(self, mock_list_models, mock_is_available, client):
        """测试模型 tier 推断"""
        mock_is_available.return_value = True
        mock_list_models.return_value = [
            {"name": "phi3:1.5b", "size": 1_000_000_000},  # low
            {"name": "qwen2:7b", "size": 4_300_000_000},  # low
            {"name": "mistral:22b", "size": 12_000_000_000},  # medium (default)
            {"name": "llama3:70b", "size": 39_800_000_000},  # high
            {"name": "mixtral:72b", "size": 40_000_000_000},  # high
            {"name": "qwen2:33b", "size": 18_000_000_000},  # high
        ]

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        data = response.json()
        tiers = {m["name"]: m["tier"] for m in data["models"]}
        assert tiers["phi3:1.5b"] == "low"
        assert tiers["qwen2:7b"] == "low"
        assert tiers["mistral:22b"] == "medium"
        assert tiers["llama3:70b"] == "high"
        assert tiers["mixtral:72b"] == "high"
        assert tiers["qwen2:33b"] == "high"

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_model_size_format(self, mock_list_models, mock_is_available, client):
        """测试模型大小格式化"""
        mock_is_available.return_value = True
        mock_list_models.return_value = [
            {"name": "small:1b", "size": 500_000_000},  # < 1GB, 显示 MB
            {"name": "medium:7b", "size": 4_300_000_000},  # > 1GB, 显示 GB
            {"name": "large:70b", "size": 39_800_000_000},  # > 1GB, 显示 GB
            {"name": "no-size", "size": 0},  # 无大小
        ]

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        data = response.json()
        sizes = {m["name"]: m["size"] for m in data["models"]}
        assert sizes["small:1b"] == "500 MB"
        assert sizes["medium:7b"] == "4.3 GB"
        assert sizes["large:70b"] == "39.8 GB"
        assert sizes["no-size"] is None

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_model_descriptions(self, mock_list_models, mock_is_available, client):
        """测试模型描述"""
        mock_is_available.return_value = True
        mock_list_models.return_value = [
            {"name": "qwen2:7b", "size": 4_300_000_000},
            {"name": "llama3:70b", "size": 39_800_000_000},
            {"name": "mistral:7b", "size": 4_100_000_000},
            {"name": "codellama:13b", "size": 7_300_000_000},
            {"name": "deepseek-coder:6.7b", "size": 3_800_000_000},
            {"name": "gemma:2b", "size": 1_700_000_000},
            {"name": "mixtral:8x7b", "size": 28_000_000_000},
            {"name": "phi3:3.8b", "size": 2_300_000_000},
            {"name": "unknown-model", "size": 1_000_000_000},
        ]

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        data = response.json()
        descriptions = {m["name"]: m["description"] for m in data["models"]}
        assert "阿里通义千问" in descriptions["qwen2:7b"]
        assert "Meta Llama 3" in descriptions["llama3:70b"]
        assert "Mistral AI" in descriptions["mistral:7b"]
        assert "Code Llama" in descriptions["codellama:13b"]
        assert "DeepSeek Coder" in descriptions["deepseek-coder:6.7b"]
        assert "Google Gemma" in descriptions["gemma:2b"]
        assert "Mixtral" in descriptions["mixtral:8x7b"]
        assert "Phi-3" in descriptions["phi3:3.8b"]
        assert descriptions["unknown-model"] == "开源大语言模型"


# ========================================
# API Route Tests - /models
# ========================================
class TestListLocalModels:
    """测试 GET /api/local-models/models"""

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_list_models_available(self, mock_list_models, mock_is_available, client):
        """测试列出可用模型"""
        mock_is_available.return_value = True
        mock_list_models.return_value = [
            {"name": "qwen2:7b", "size": 4_300_000_000, "modified_at": "2026-05-20T10:00:00"},
            {"name": "llama3:70b", "size": 39_800_000_000, "modified_at": "2026-05-19T10:00:00"},
        ]

        response = client.get("/api/local-models/models")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "qwen2:7b"
        assert data[1]["name"] == "llama3:70b"

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_list_models_unavailable(self, mock_is_available, client):
        """测试 Ollama 不可用时返回空列表"""
        mock_is_available.return_value = False

        response = client.get("/api/local-models/models")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_list_models_empty(self, mock_list_models, mock_is_available, client):
        """测试无模型时返回空列表"""
        mock_is_available.return_value = True
        mock_list_models.return_value = []

        response = client.get("/api/local-models/models")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_list_models_tier_inference(self, mock_list_models, mock_is_available, client):
        """测试模型 tier 推断"""
        mock_is_available.return_value = True
        mock_list_models.return_value = [
            {"name": "phi3:1.5b", "size": 1_000_000_000},
            {"name": "qwen2:7b", "size": 4_300_000_000},
            {"name": "mistral:22b", "size": 12_000_000_000},
            {"name": "llama3:70b", "size": 39_800_000_000},
        ]

        response = client.get("/api/local-models/models")
        assert response.status_code == 200
        data = response.json()
        tiers = {m["name"]: m["tier"] for m in data}
        assert tiers["phi3:1.5b"] == "low"
        assert tiers["qwen2:7b"] == "low"
        assert tiers["mistral:22b"] == "medium"
        assert tiers["llama3:70b"] == "high"


# ========================================
# API Route Tests - /pull/{model_name}
# ========================================
class TestPullModel:
    """测试 POST /api/local-models/pull/{model_name}"""

    @patch("src.models.ollama.OllamaModel.pull_model")
    def test_pull_model_success(self, mock_pull_model, client):
        """测试成功拉取模型"""
        mock_pull_model.return_value = True

        response = client.post("/api/local-models/pull/qwen2:7b")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "qwen2:7b" in data["message"]

    @patch("src.models.ollama.OllamaModel.pull_model")
    def test_pull_model_failed(self, mock_pull_model, client):
        """测试拉取模型失败"""
        mock_pull_model.return_value = False

        response = client.post("/api/local-models/pull/qwen2:7b")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "qwen2:7b" in data["message"]

    @patch("src.models.ollama.OllamaModel.pull_model")
    def test_pull_model_exception(self, mock_pull_model, client):
        """测试拉取模型异常"""
        mock_pull_model.side_effect = Exception("Pull failed")

        response = client.post("/api/local-models/pull/qwen2:7b")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Internal server error"

    @patch("src.models.ollama.OllamaModel.pull_model")
    def test_pull_model_with_slash(self, mock_pull_model, client):
        """测试模型名称带 / 的情况（路径参数）"""
        mock_pull_model.return_value = True

        # 注意：FastAPI 默认不支持路径参数带 /，需要用 : 代替
        response = client.post("/api/local-models/pull/codellama:13b")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch("src.models.ollama.OllamaModel.pull_model")
    def test_pull_model_different_names(self, mock_pull_model, client):
        """测试不同模型名称"""
        mock_pull_model.return_value = True

        models = ["qwen2:7b", "llama3:70b", "mistral:7b", "phi3:mini"]
        for model_name in models:
            response = client.post(f"/api/local-models/pull/{model_name}")
            assert response.status_code == 200
            mock_pull_model.assert_called_with(model_name)


# ========================================
# API Route Tests - /recommended
# ========================================
class TestGetRecommendedModels:
    """测试 GET /api/local-models/recommended"""

    @patch("src.models.ollama.OLLAMA_MODELS")
    def test_recommended_models(self, mock_ollama_models, client):
        """测试获取推荐模型"""
        from enum import Enum

        # 模拟 OLLAMA_MODELS
        class MockTier(str, Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"

        mock_ollama_models.__getitem__.side_effect = lambda key: {
            MockTier.LOW: [
                {"name": "qwen2:1.5b", "desc": "快速推理", "context": 32768},
                {"name": "phi3:3.8b", "desc": "轻量级", "context": 128000},
            ],
            MockTier.MEDIUM: [
                {"name": "qwen2:7b", "desc": "均衡", "context": 32768},
            ],
            MockTier.HIGH: [
                {"name": "qwen2:72b", "desc": "高质量", "context": 32768},
            ],
        }[key]

        mock_ollama_models.items.return_value = [
            (MockTier.LOW, mock_ollama_models[MockTier.LOW]),
            (MockTier.MEDIUM, mock_ollama_models[MockTier.MEDIUM]),
            (MockTier.HIGH, mock_ollama_models[MockTier.HIGH]),
        ]

        response = client.get("/api/local-models/recommended")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4

        # 检查结构
        for model in data:
            assert "name" in model
            assert "tier" in model
            assert "description" in model
            assert "context_length" in model
            assert "installed" in model
            assert model["installed"] is False  # 默认 False

    @patch("src.models.ollama.OLLAMA_MODELS")
    def test_recommended_empty(self, mock_ollama_models, client):
        """测试无推荐模型"""
        mock_ollama_models.items.return_value = []

        response = client.get("/api/local-models/recommended")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_recommended_structure(self, client):
        """测试推荐模型结构（集成测试）"""
        response = client.get("/api/local-models/recommended")
        assert response.status_code == 200
        data = response.json()

        # 验证返回的是列表
        assert isinstance(data, list)

        # 如果有数据，验证结构
        if len(data) > 0:
            model = data[0]
            assert "name" in model
            assert "tier" in model
            assert "description" in model
            assert "context_length" in model
            assert "installed" in model


# ========================================
# Edge Cases and Error Handling
# ========================================
class TestEdgeCases:
    """测试边界情况和错误处理"""

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_model_missing_fields(self, mock_list_models, mock_is_available, client):
        """测试模型数据缺少字段"""
        mock_is_available.return_value = True
        mock_list_models.return_value = [
            {"name": "test-model"},  # 只有 name
        ]

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        data = response.json()
        assert len(data["models"]) == 1
        assert data["models"][0]["name"] == "test-model"
        assert data["models"][0]["size"] is None
        assert data["models"][0]["modified_at"] is None

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_model_size_zero(self, mock_list_models, mock_is_available, client):
        """测试模型大小为 0"""
        mock_is_available.return_value = True
        mock_list_models.return_value = [
            {"name": "zero-size", "size": 0},
        ]

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        data = response.json()
        assert data["models"][0]["size"] is None

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_large_model_list(self, mock_list_models, mock_is_available, client):
        """测试大量模型"""
        mock_is_available.return_value = True
        # 创建 50 个模型
        mock_list_models.return_value = [
            {"name": f"model-{i}:7b", "size": 4_300_000_000} for i in range(50)
        ]

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        data = response.json()
        assert len(data["models"]) == 50

    def test_pull_model_empty_name(self, client):
        """测试空模型名称（路径问题）"""
        # FastAPI 会拒绝空路径参数，返回 404
        response = client.post("/api/local-models/pull/")
        assert response.status_code == 404

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_response_model_validation(self, mock_list_models, mock_is_available, client):
        """测试响应模型验证"""
        mock_is_available.return_value = True
        mock_list_models.return_value = [
            {"name": "qwen2:7b", "size": 4_300_000_000, "modified_at": "2026-05-20T10:00:00"},
        ]

        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        # 验证响应符合 OllamaStatus schema
        data = response.json()
        assert "available" in data
        assert "base_url" in data
        assert "models" in data
        assert isinstance(data["models"], list)
        if len(data["models"]) > 0:
            model = data["models"][0]
            assert "name" in model
            assert "available" in model


# ========================================
# Integration-style Tests
# ========================================
class TestIntegration:
    """集成测试（较少 mock）"""

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_status_to_models_consistency(self, mock_list_models, mock_is_available, client):
        """测试 /status 和 /models 返回一致的模型列表"""
        mock_is_available.return_value = True
        mock_models = [
            {"name": "qwen2:7b", "size": 4_300_000_000, "modified_at": "2026-05-20T10:00:00"},
            {"name": "llama3:70b", "size": 39_800_000_000, "modified_at": "2026-05-19T10:00:00"},
        ]
        mock_list_models.return_value = mock_models

        # 获取 /status
        status_response = client.get("/api/local-models/status")
        status_data = status_response.json()

        # 获取 /models
        models_response = client.get("/api/local-models/models")
        models_data = models_response.json()

        # 模型数量应该一致
        assert len(status_data["models"]) == len(models_data)

        # 模型名称应该一致
        status_names = [m["name"] for m in status_data["models"]]
        models_names = [m["name"] for m in models_data]
        assert status_names == models_names

    def test_all_routes_exist(self, client):
        """测试所有路由都存在"""
        # GET /status
        response = client.get("/api/local-models/status")
        assert response.status_code != 404

        # GET /models
        response = client.get("/api/local-models/models")
        assert response.status_code != 404

        # POST /pull/{model_name}
        response = client.post("/api/local-models/pull/test:7b")
        assert response.status_code != 404

        # GET /recommended
        response = client.get("/api/local-models/recommended")
        assert response.status_code != 404

    @patch("src.models.ollama.OllamaModel.is_available")
    @patch("src.models.ollama.OllamaModel.list_models")
    @patch("src.models.ollama.OllamaModel.pull_model")
    @patch("src.models.ollama.OLLAMA_DEFAULT_URL", "http://localhost:11434")
    def test_complete_flow(self, mock_pull_model, mock_list_models, mock_is_available, client):
        """测试完整流程：检查状态 -> 列出模型 -> 拉取模型"""
        # 1. 检查状态（不可用）
        mock_is_available.return_value = False
        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        assert response.json()["available"] is False

        # 2. 列出模型（空）
        response = client.get("/api/local-models/models")
        assert response.status_code == 200
        assert response.json() == []

        # 3. 启动 Ollama
        mock_is_available.return_value = True
        mock_list_models.return_value = []

        # 4. 检查状态（可用）
        response = client.get("/api/local-models/status")
        assert response.status_code == 200
        assert response.json()["available"] is True

        # 5. 拉取模型
        mock_pull_model.return_value = True
        response = client.post("/api/local-models/pull/qwen2:7b")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 6. 列出模型（有模型）
        mock_list_models.return_value = [
            {"name": "qwen2:7b", "size": 4_300_000_000, "modified_at": "2026-05-20T10:00:00"},
        ]
        response = client.get("/api/local-models/models")
        assert response.status_code == 200
        models = response.json()
        assert len(models) == 1
        assert models[0]["name"] == "qwen2:7b"
