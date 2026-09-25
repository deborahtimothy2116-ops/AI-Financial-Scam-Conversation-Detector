"""Tests for Pause Before You Pay."""

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserRegisterRequest
from app.services.pause_check import WAIT_SECONDS, build_pause


def warnings(pause):
    return {item["id"]: item["warning"] for item in pause["checklist"]}


def test_no_pause_unless_scam():
    assert build_pause("SAFE", []) is None
    assert build_pause("SUSPICIOUS", ["RULE_MONEY_REQUEST"]) is None


def test_checklist_marks_what_this_message_contradicts():
    pause = build_pause("SCAM", ["RULE_CREDENTIAL_SOLICITATION", "RULE_FALSE_URGENCY"], ["legal_case"], "OTP theft")
    w = warnings(pause)
    assert w["no_codes"] == "It asks for an OTP, PIN or password."
    assert w["no_pressure"] == "It rushes you with a deadline."
    assert w["no_fee_to_receive"] is None
    assert pause["failing_checks"] == 2 and pause["wait_seconds"] == WAIT_SECONDS
    assert pause["message"].startswith("This looks like OTP theft.")


def test_claims_add_warnings():
    w = warnings(build_pause("SCAM", [], ["family_emergency", "prize"]))
    assert "number you already have" in w["known_contact"]
    assert "wants money first" in w["no_fee_to_receive"]


def test_scam_scan_returns_pause_and_safe_scan_does_not(client: TestClient):
    scam = client.post("/api/v1/analyze/message", json={
        "message": "Congratulations! You have won Rs 5,00,000 in the KBC lucky draw. Pay Rs 2,000 processing fee within 2 hours to claim."
    }).json()["data"]
    assert scam["verdict"] == "SCAM"
    assert warnings(scam["pause"])["no_fee_to_receive"] == "It asks for a fee to release a prize."
    safe = client.post("/api/v1/analyze/message", json={"message": "See you at lunch tomorrow."}).json()["data"]
    assert safe["pause"] is None


def test_lookup_of_heavily_reported_number_pauses(client: TestClient, db_session):
    repo = UserRepository(db_session)
    for i in range(3):
        user = repo.create_user(UserRegisterRequest(email=f"p{i}@example.com", password="SecurePassword123!", full_name="P"))
        client.post("/api/v1/community/reports", json={"identifier": "98765 43210"},
                    headers={"Authorization": f"Bearer {create_access_token(subject=user.id)}"})
    pause = client.get("/api/v1/community/lookup", params={"q": "9876543210"}).json()["data"]["pause"]
    assert "reported 3 times" in pause["checklist"][0]["warning"]
    assert client.get("/api/v1/community/lookup", params={"q": "9123456789"}).json()["data"]["pause"] is None


def test_pause_outcomes_are_counted(client: TestClient):
    assert client.get("/api/v1/pause/stats").json()["data"]["paused"] == 0
    for outcome in ("stopped", "stopped", "already_paid", "continued"):
        client.post("/api/v1/pause/events", json={"source": "scan", "outcome": outcome, "analysis_id": "unknown-id"})
    assert client.get("/api/v1/pause/stats").json()["data"] == {"paused": 4, "stopped": 2, "continued": 1, "already_paid": 1}
    assert client.post("/api/v1/pause/events", json={"source": "scan", "outcome": "maybe"}).status_code == 422
