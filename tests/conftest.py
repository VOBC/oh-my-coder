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
