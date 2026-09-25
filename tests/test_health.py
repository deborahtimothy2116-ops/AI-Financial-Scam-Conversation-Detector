"""Tests for Health, Ping, and Discovery API Endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_root_discovery(client: TestClient):
    """Test root endpoint / returns project metadata."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "name" in body
    assert "version" in body
    assert "documentation" in body
    assert "disclaimer" in body


def test_health_check_endpoints(client: TestClient):
    """Test /health and /api/v1/health endpoints."""
    resp1 = client.get("/health")
    assert resp1.status_code == 200
    assert resp1.json()["data"]["database"] == "healthy"

    resp2 = client.get("/api/v1/health")
    assert resp2.status_code == 200
    assert resp2.json()["data"]["database"] == "healthy"


def test_ping_endpoints(client: TestClient):
    """Test /ping and /api/v1/ping liveness probes."""
    resp1 = client.get("/ping")
    assert resp1.status_code == 200
    assert resp1.json() == {"status": "ok", "pong": True}

    resp2 = client.get("/api/v1/ping")
    assert resp2.status_code == 200
    assert resp2.json() == {"status": "ok", "pong": True}
