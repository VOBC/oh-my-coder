"""Tests for src/main.py - FastAPI 主入口。

覆盖两个 HTTP 端点：
- GET /        根路径，返回 API 元信息
- GET /health  健康检查
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    """GET / 返回 API 元信息。"""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Oh My Coder API"
    assert data["version"] == "0.2.0"


def test_health_endpoint(client):
    """GET /health 返回 ok 状态。"""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_app_metadata():
    """app 应携带正确的 title/version。"""
    assert app.title == "Oh My Coder"
    assert app.version == "0.2.0"
