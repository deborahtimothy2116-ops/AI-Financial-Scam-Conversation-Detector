"""Tests for sender/link mismatch, request, writing-style checks and the SAFE/SUSPICIOUS/SCAM verdict."""

import pytest
from fastapi.testclient import TestClient


def analyze(client: TestClient, message: str) -> dict:
    response = client.post("/api/v1/analyze/message", json={"message": message})
    assert response.status_code == 200
    return response.json()["data"]


def rule_ids(data: dict) -> set:
    return {i["rule_id"] for i in data["indicators"]}


@pytest.mark.parametrize(
    "message, expected_rule",
    [
        ("Dear Customer, your SBI acount will be suspened today. Verify now at www.sbi-secure-login.com",
         "RULE_SENDER_DOMAIN_MISMATCH"),
        ("Your order is on hold. Confirm payment at http://amaz0n-orders.shop/pay",
         "RULE_SENDER_DOMAIN_MISMATCH"),
        ("HDFC Bank Security Team: reply with your card number and expiry date to hdfc.alerts@gmail.com to avoid penalty.",
         "RULE_FREE_EMAIL_SENDER"),
        ("HDFC Bank Security Team: reply with your card number and expiry date to hdfc.alerts@gmail.com to avoid penalty.",
         "RULE_BANK_DETAILS_REQUEST"),
        ("FedEx: your parcel is held at customs. Pay ₹199 customs charge within 2 hours.",
         "RULE_MONEY_REQUEST"),
    ],
)
def test_scam_messages_are_classified_scam(client: TestClient, message, expected_rule):
    data = analyze(client, message)
    assert data["verdict"] == "SCAM"
    assert data["verdict_label"].startswith("SCAM")
    assert expected_rule in rule_ids(data)


def test_spelling_and_generic_greeting_flagged(client: TestClient):
    data = analyze(client, "Dear Customer, your SBI acount will be suspened today. Verify now at www.sbi-secure-login.com")
    assert {"RULE_SPELLING_MISTAKES", "RULE_GENERIC_GREETING"} <= rule_ids(data)


def test_shouty_prize_message_is_scam(client: TestClient):
    data = analyze(client, "CONGRATULATIONS!!! YOU ARE SELECTED FOR FREE GIFT CLICK NOW")
    assert data["verdict"] == "SCAM"
    assert "RULE_UNUSUAL_FORMATTING" in rule_ids(data)


def test_money_request_from_contact_is_suspicious(client: TestClient):
    data = analyze(client, "Can you send me Rs 500 for the movie tickets? I'll pay you back tomorrow.")
    assert data["verdict"] == "SUSPICIOUS"


@pytest.mark.parametrize(
    "message",
    [
        "Dear Customer, Rs 500 debited from A/c XX1234 on 25-Sep. Not you? Visit https://www.onlinesbi.sbi to report.",
        "Your Amazon order #402-123 has shipped. Track it at https://www.amazon.in/orders",
        "Hey, dinner at 8? I'll bring the notes from class.",
        "I attached report.pdf and notes.docx, check when free",
    ],
)
def test_legitimate_messages_are_safe(client: TestClient, message):
    data = analyze(client, message)
    assert data["verdict"] == "SAFE"
    assert "RULE_SENDER_DOMAIN_MISMATCH" not in rule_ids(data)
    assert "RULE_OBFUSCATED_URL" not in rule_ids(data)
