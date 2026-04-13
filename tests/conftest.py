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
