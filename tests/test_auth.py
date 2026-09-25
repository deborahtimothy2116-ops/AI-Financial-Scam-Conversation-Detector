"""Tests for authentication and user management API endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_user_registration(client: TestClient):
    """Test registering a new user."""
    payload = {
        "email": "newuser@example.com",
        "password": "StrongPassword123!",
        "full_name": "Test Citizen",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "token" in body["data"]
    assert body["data"]["user"]["email"] == "newuser@example.com"
    assert "access_token" in body["data"]["token"]


def test_duplicate_user_registration(client: TestClient, test_user):
    """Test registering with an already existing email returns error."""
    payload = {
        "email": test_user.email,
        "password": "AnotherPassword123!",
        "full_name": "Duplicate User",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "VALIDATION_ERROR"


def test_user_login_success(client: TestClient, test_user):
    """Test logging in with valid credentials."""
    payload = {
        "email": "testvictim@example.com",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["user"]["id"] == test_user.id
    assert "access_token" in body["data"]["token"]


def test_user_login_invalid_password(client: TestClient, test_user):
    """Test logging in with invalid password returns 401."""
    payload = {
        "email": "testvictim@example.com",
        "password": "WrongPassword999!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "AUTH_ERROR"


def test_oauth2_token_endpoint(client: TestClient, test_user):
    """Test Swagger UI compatible /auth/token endpoint."""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "testvictim@example.com", "password": "SecurePassword123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_get_current_user_profile(client: TestClient, auth_headers, test_user):
    """Test getting current logged-in profile."""
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == test_user.id
    assert body["data"]["email"] == test_user.email


def test_get_current_user_unauthorized(client: TestClient):
    """Test accessing /auth/me without token returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
