"""
conftest.py - pytest 全局 fixtures
"""

import pytest
from fastapi.testclient import TestClient

from src.web.app import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def tmp_skill_dir(tmp_path):
    """临时 skills 目录（供 SkillManager 测试复用）"""
    d = tmp_path / "skills"
    d.mkdir()
    return d


@pytest.fixture
def make_quest():
    """创建测试用 Quest 对象"""
    def _make(title="Test Quest", status="pending", **kwargs):
        defaults = {"id": "quest-001", "title": title, "status": status,
                    "model": "deepseek-chat", "max_turns": 10}
        return {**defaults, **kwargs}
    return _make


@pytest.fixture
def make_agent():
    """创建测试用 Agent 对象"""
    def _make(name="test-agent", role="coder", **kwargs):
        defaults = {"id": "agent-001", "name": name, "role": role,
                    "model": "deepseek-chat"}
        return {**defaults, **kwargs}
    return _make


@pytest.fixture
def mock_model_response():
    """模拟模型响应，绕过真实 API 调用"""
    def _mock(content="OK", cost=0.001):
        return {"content": content, "usage": {"cost": cost}, "model": "mock"}
    return _mock
