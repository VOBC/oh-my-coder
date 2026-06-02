"""
Simple tests for API endpoints
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.server_api import create_app


def test_health_endpoint():
    """Test the health check endpoint returns ok status."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_tasks_empty():
    """Test getting tasks list when empty."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
