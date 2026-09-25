"""Tests for community scam reports, emergency response and digital-arrest detection."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserRegisterRequest
from app.services.community_service import extract_identifiers, normalize_identifier
from app.services.emergency_service import format_inr


def make_headers(db_session, n: int) -> list:
    repo = UserRepository(db_session)
    users = [
        repo.create_user(UserRegisterRequest(email=f"reporter{i}@example.com", password="SecurePassword123!", full_name=f"Reporter {i}"))
        for i in range(n)
    ]
    return [{"Authorization": f"Bearer {create_access_token(subject=u.id)}"} for u in users]


# --- Identifier handling ---------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("+91 98765-43210", ("phone", "9876543210")),
        ("09876543210", ("phone", "9876543210")),
        ("Fraud.KYC@ybl", ("upi", "fraud.kyc@ybl")),
        ("refunds.itd@gmail.com", ("email", "refunds.itd@gmail.com")),
        ("https://sbi.co.in@secure-kyc.xyz/login", ("domain", "secure-kyc.xyz")),
        ("www.sbi-yono-kyc.xyz/update", ("domain", "sbi-yono-kyc.xyz")),
    ],
)
def test_normalize_identifier(raw, expected):
    assert normalize_identifier(raw) == expected


def test_extract_identifiers_skips_official_domains_shorteners_and_transaction_ids():
    text = ("Pay to fraud.kyc@ybl, call +91 98765 43210, visit sbi-yono-kyc.xyz/update, not https://www.onlinesbi.sbi "
            "or bit.ly/x1. UTR 412345678901 on 25-09-2026")
    assert extract_identifiers(text) == [("upi", "fraud.kyc@ybl"), ("phone", "9876543210"), ("domain", "sbi-yono-kyc.xyz")]


# --- Community reports -----------------------------------------------------

def test_reporting_requires_login(client: TestClient):
    response = client.post("/api/v1/community/reports", json={"identifier": "fraud.kyc@ybl"})
    assert response.status_code == 401


def test_lookup_counts_distinct_reporters(client: TestClient, db_session):
    headers = make_headers(db_session, 3)
    assert client.get("/api/v1/community/lookup", params={"q": "+91 98765 43210"}).json()["data"]["status"] == "no_reports"

    first = client.post("/api/v1/community/reports", json={"identifier": "98765 43210", "scam_category": "PHISHING_CREDENTIAL_HARVESTING"}, headers=headers[0]).json()["data"]
    assert first == {"identifier_type": "phone", "identifier": "9876543210", "created": True, "report_count": 1}
    again = client.post("/api/v1/community/reports", json={"identifier": "+919876543210"}, headers=headers[0]).json()["data"]
    assert again["created"] is False and again["report_count"] == 1  # same user can't inflate the count

    lookup = client.get("/api/v1/community/lookup", params={"q": "09876543210"}).json()["data"]
    assert lookup["status"] == "reported" and lookup["report_count"] == 1
    assert lookup["categories"] == {"PHISHING_CREDENTIAL_HARVESTING": 1}

    for h in headers[1:]:
        client.post("/api/v1/community/reports", json={"identifier": "9876543210"}, headers=h)
    assert client.get("/api/v1/community/lookup", params={"q": "9876543210"}).json()["data"]["status"] == "strongly_reported"


def test_official_domains_cannot_be_reported(client: TestClient, auth_headers):
    response = client.post("/api/v1/community/reports", json={"identifier": "https://www.onlinesbi.sbi"}, headers=auth_headers)
    assert response.status_code == 422
    lookup = client.get("/api/v1/community/lookup", params={"q": "onlinesbi.sbi"}).json()["data"]
    assert lookup["status"] == "official" and lookup["official_brand"] == "SBI"


def test_invalid_lookup_is_rejected(client: TestClient):
    assert client.get("/api/v1/community/lookup", params={"q": "hello"}).status_code == 422


def test_scans_warn_about_reported_identifiers(client: TestClient, db_session):
    message = "Hi, I am your cousin's friend. Please call me on 98765 43210."
    before = client.post("/api/v1/analyze/message", json={"message": message}).json()["data"]
    assert before["verdict"] == "SAFE"

    headers = make_headers(db_session, 3)
    client.post("/api/v1/community/reports", json={"identifier": "9876543210"}, headers=headers[0])
    once = client.post("/api/v1/analyze/message", json={"message": message}).json()["data"]
    assert once["verdict"] == "SUSPICIOUS"
    assert "RULE_COMMUNITY_REPORTED" in {i["rule_id"] for i in once["indicators"]}

    for h in headers[1:]:
        client.post("/api/v1/community/reports", json={"identifier": "9876543210"}, headers=h)
    assert client.post("/api/v1/analyze/message", json={"message": message}).json()["data"]["verdict"] == "SCAM"


def test_report_all_details_from_a_scan(client: TestClient, auth_headers):
    scan = client.post(
        "/api/v1/analyze/message",
        json={"message": "SBI KYC expired. Pay Rs 99 to kyc.help@ybl or call 98765 43210. Visit sbi-kyc-update.xyz/login"},
        headers=auth_headers,
    ).json()["data"]
    response = client.post(f"/api/v1/community/reports/from-analysis/{scan['id']}", headers=auth_headers)
    assert response.status_code == 200
    reported = {(r["identifier_type"], r["identifier"]) for r in response.json()["data"]}
    assert reported == {("upi", "kyc.help@ybl"), ("phone", "9876543210"), ("domain", "sbi-kyc-update.xyz")}


def test_cannot_report_from_someone_elses_scan(client: TestClient, db_session, auth_headers):
    scan = client.post("/api/v1/analyze/message", json={"message": "Call 98765 43210 to claim prize fee Rs 500"}, headers=auth_headers).json()["data"]
    (other,) = make_headers(db_session, 1)
    assert client.post(f"/api/v1/community/reports/from-analysis/{scan['id']}", headers=other).status_code == 403


# --- Emergency response ----------------------------------------------------

def test_emergency_guide_is_tailored(client: TestClient):
    upi = client.get("/api/v1/emergency/guide", params={"incident_type": "upi_payment"}).json()["data"]
    titles = [s["title"] for s in upi["steps"]]
    assert titles[0] == "Call 1930 immediately"
    assert upi["steps"][0]["action"]["href"] == "tel:1930"
    assert any("RBI Ombudsman" in t for t in titles)

    remote = [s["title"] for s in client.get("/api/v1/emergency/guide", params={"incident_type": "remote_app"}).json()["data"]["steps"]]
    assert "Cut the scammer's access" in remote and "Call 1930 immediately" not in remote

    arrest = [s["title"] for s in client.get("/api/v1/emergency/guide", params={"incident_type": "digital_arrest"}).json()["data"]["steps"]]
    assert "Hang up. There is no 'digital arrest'" in arrest
    assert client.get("/api/v1/emergency/guide", params={"incident_type": "bogus"}).status_code == 422


def test_complaint_draft_prefills_evidence(client: TestClient):
    payload = {
        "incident_type": "upi_payment",
        "amount_lost": 125000,
        "incident_datetime": "2026-09-24T18:05:00",
        "transaction_ids": ["412345678901"],
        "bank_name": "SBI",
        "message_text": "Your SBI KYC expired. Pay Rs 25,000 to kyc.help@ybl or call +91 98765 43210. Visit https://sbi-kyc.xyz/login",
    }
    data = client.post("/api/v1/emergency/complaint-draft", json=payload).json()["data"]
    draft = data["draft_text"]
    assert "₹1,25,000 lost on 24 Sep 2026, 06:05 PM" in draft
    assert "412345678901" in draft and "kyc.help@ybl" in draft and "+91 98765 43210" in draft
    assert "hxxps://sbi-kyc[.]xyz/login" in draft and "https://sbi-kyc.xyz" not in draft
    assert data["evidence"]["upi_ids"] == ["kyc.help@ybl"]


@pytest.mark.parametrize("amount, text", [(999, "₹999"), (2000, "₹2,000"), (150000, "₹1,50,000"), (12345678.5, "₹1,23,45,678.50")])
def test_format_inr(amount, text):
    assert format_inr(amount) == text


# --- Digital arrest --------------------------------------------------------

def test_digital_arrest_detected(client: TestClient):
    data = client.post("/api/v1/analyze/message", json={"message": (
        "This is Mumbai Police Crime Branch. A parcel containing drugs was found in your name. You are under digital arrest. "
        "Stay on the video call and do not tell anyone. Transfer your savings to the RBI verification account."
    )}).json()["data"]
    assert data["verdict"] == "SCAM"
    assert "RULE_DIGITAL_ARREST" in {i["rule_id"] for i in data["indicators"]}


@pytest.mark.parametrize("message", [
    "The police station called about the lost wallet I reported, they found it!",
    "Customs clearance for my parcel is done, delivery tomorrow.",
])
def test_harmless_mentions_of_authorities_are_safe(client: TestClient, message):
    assert client.post("/api/v1/analyze/message", json={"message": message}).json()["data"]["verdict"] == "SAFE"
