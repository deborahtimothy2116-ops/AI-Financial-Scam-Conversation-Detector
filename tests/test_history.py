"""Tests for User History and Analytics API Endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.utils.constants import ScamCategory, RiskLevel


def test_user_history_pagination_and_filters(client: TestClient, auth_headers):
    """Test retrieving user history with filters and pagination."""
    # Create 3 scans under authenticated user
    client.post(
        "/api/v1/analysis/text",
        json={"text": "Scan QR to receive Rs 10000 on Google Pay"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/analysis/text",
        json={"text": "URGENT: Police arrest warrant pay fine now"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/analysis/text",
        json={"text": "Hello friend, let us meet tomorrow for coffee."},
        headers=auth_headers,
    )

    # Fetch history page 1
    resp = client.get("/api/v1/history?page=1&page_size=2", headers=auth_headers)
    assert resp.status_code == 200
    paginated = resp.json()["data"]
    assert paginated["meta"]["total"] == 3
    assert len(paginated["items"]) == 2
    assert paginated["meta"]["has_next"] is True

    # Filter by is_scam=True
    scam_resp = client.get("/api/v1/history?is_scam=true", headers=auth_headers)
    assert scam_resp.status_code == 200
    scam_items = scam_resp.json()["data"]["items"]
    assert len(scam_items) == 2
    assert all(i["is_scam"] for i in scam_items)

    # Filter by search_query
    search_resp = client.get("/api/v1/history?search_query=coffee", headers=auth_headers)
    assert search_resp.status_code == 200
    search_items = search_resp.json()["data"]["items"]
    assert len(search_items) == 1
    assert "coffee" in search_items[0]["snippet"].lower()


def test_user_stats(client: TestClient, auth_headers):
    """Test aggregated threat stats calculation for authenticated user."""
    # Create 2 scams and 1 safe message
    client.post(
        "/api/v1/analysis/text",
        json={"text": "Scan QR code to receive Rs 5000 refund"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/analysis/text",
        json={"text": "Install AnyDesk and tell OTP code"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/analysis/text",
        json={"text": "Good morning! Wishing you a great day."},
        headers=auth_headers,
    )

    resp = client.get("/api/v1/history/stats", headers=auth_headers)
    assert resp.status_code == 200
    stats = resp.json()["data"]

    assert stats["total_scans"] == 3
    assert stats["total_scams_flagged"] == 2
    assert stats["safe_conversations_count"] == 1
    assert stats["scam_prevention_rate_percent"] > 50.0
    assert len(stats["scams_by_category"]) >= 2


def test_delete_single_history_item(client: TestClient, auth_headers):
    """Test deleting an analysis item from user's history."""
    create_resp = client.post(
        "/api/v1/analysis/text",
        json={"text": "Test delete item scan"},
        headers=auth_headers,
    )
    analysis_id = create_resp.json()["data"]["id"]

    del_resp = client.delete(f"/api/v1/history/{analysis_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["id"] == analysis_id

    # Verify item is deleted
    get_resp = client.get(f"/api/v1/analysis/{analysis_id}")
    assert get_resp.status_code == 404


def test_clear_all_history(client: TestClient, auth_headers):
    """Test clearing all analysis history for user."""
    client.post(
        "/api/v1/analysis/text",
        json={"text": "First scan"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/analysis/text",
        json={"text": "Second scan"},
        headers=auth_headers,
    )

    clear_resp = client.delete("/api/v1/history/clear", headers=auth_headers)
    assert clear_resp.status_code == 200
    assert clear_resp.json()["data"]["deleted_count"] == 2

    # Check that history is empty
    history_resp = client.get("/api/v1/history", headers=auth_headers)
    assert history_resp.json()["data"]["meta"]["total"] == 0


def test_cross_user_history_isolation(client: TestClient):
    """Test that User A's history cannot be accessed or deleted by User B."""
    # Register User A
    user_a_reg = client.post(
        "/api/v1/auth/register",
        json={"email": "usera@example.com", "password": "Password123!", "full_name": "User A"},
    )
    assert user_a_reg.status_code == 201
    token_a = user_a_reg.json()["data"]["token"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B
    user_b_reg = client.post(
        "/api/v1/auth/register",
        json={"email": "userb@example.com", "password": "Password123!", "full_name": "User B"},
    )
    assert user_b_reg.status_code == 201
    token_b = user_b_reg.json()["data"]["token"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a scan
    scan_a = client.post(
        "/api/v1/analyze/message",
        json={"message": "URGENT: User A private banking message block notice."},
        headers=headers_a,
    )
    assert scan_a.status_code == 200
    analysis_id_a = scan_a.json()["data"]["analysis_id"]

    # User A can get history detail
    get_a = client.get(f"/api/v1/history/{analysis_id_a}", headers=headers_a)
    assert get_a.status_code == 200
    assert get_a.json()["data"]["analysis_id"] == analysis_id_a

    # User B CANNOT get User A's scan via history detail endpoint (returns 404)
    get_b = client.get(f"/api/v1/history/{analysis_id_a}", headers=headers_b)
    assert get_b.status_code == 404

    # User B CANNOT delete User A's scan (returns 404)
    del_b = client.delete(f"/api/v1/history/{analysis_id_a}", headers=headers_b)
    assert del_b.status_code == 404

    # User B's history list does not contain User A's scan
    hist_b = client.get("/api/v1/history", headers=headers_b)
    assert hist_b.status_code == 200
    assert hist_b.json()["data"]["meta"]["total"] == 0

