"""Tests for the Link X-ray, red-flag highlighter and Spot-the-Scam quiz."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.schemas.analysis import verdict_for_score
from app.services.highlighter import find_highlights
from app.services.link_xray import xray_links
from app.services.scam_detector import scam_detector
from app.utils.quiz_bank import QUIZ_BANK, quiz_analysis_text


def codes(text):
    (report,) = xray_links(text)
    return report, {f["code"] for f in report["flags"]}


@pytest.mark.parametrize(
    "text, code, real_domain",
    [
        ("Verify at https://sbi.co.in@secure-kyc.xyz/login", "USERINFO_TRICK", "secure-kyc.xyz"),
        ("Update KYC: sbi.co.in.verify-kyc.xyz/update", "BRAND_IN_SUBDOMAIN", "verify-kyc.xyz"),
        ("Pay here https://pаypal.com/signin", "HOMOGLYPH", "pаypal.com"),
        ("Go to http://xn--pypal-4ve.com/login", "PUNYCODE", "xn--pypal-4ve.com"),
        ("Claim http://bit.ly/3xYz12", "SHORTENER", "bit.ly"),
        ("Open http://192.168.10.5/bank/login", "RAW_IP", "192.168.10.5"),
        ("Order at amaz0n-orders.shop/pay now.", "LOOKALIKE_DOMAIN", "amaz0n-orders.shop"),
    ],
)
def test_link_xray_exposes_tricks(text, code, real_domain):
    report, found = codes(text)
    assert code in found
    assert report["real_domain"] == real_domain
    assert report["risk"] in ("danger", "caution")


@pytest.mark.parametrize("text", ["Login at https://www.onlinesbi.sbi/retail/login.htm", "Track at https://www.amazon.in/orders."])
def test_link_xray_recognises_official_domains(text):
    report, found = codes(text)
    assert report["risk"] == "safe"
    assert found == {"OFFICIAL_DOMAIN"}


def test_link_xray_ignores_file_names_and_numbers():
    assert xray_links("see report.pdf and 3.5 stars") == []


def test_highlighter_marks_exact_phrases():
    text = "URGENT! Dear Customer, share OTP and pay ₹2,000 at https://sbi.co.in@secure-kyc.xyz/login"
    spans = find_highlights(text)
    by_text = {s["text"]: s for s in spans}
    assert by_text["OTP"]["severity"] == "high"
    assert by_text["https://sbi.co.in@secure-kyc.xyz/login"]["label"] == "Hidden real destination"
    assert "Dear Customer" in by_text and "URGENT" in by_text
    assert all(text[s["start"]:s["end"]] == s["text"] for s in spans)
    assert all(a["end"] <= b["start"] for a, b in zip(spans, spans[1:]))


def test_highlighter_leaves_normal_messages_alone():
    assert find_highlights("Hey, dinner at 8? I'll bring the notes.") == []


def test_analysis_response_includes_highlights_and_xray(client: TestClient):
    response = client.post("/api/v1/analyze/message", json={"message": "Verify your SBI KYC at https://sbi.co.in@secure-kyc.xyz/login"})
    data = response.json()["data"]
    assert data["verdict"] == "SCAM"
    assert "RULE_DECEPTIVE_LINK" in {i["rule_id"] for i in data["indicators"]}
    assert data["link_xray"][0]["real_domain"] == "secure-kyc.xyz"
    assert any(h["category"] == "link" for h in data["highlights"])


@pytest.mark.parametrize("question", QUIZ_BANK, ids=lambda q: q["id"])
def test_detector_agrees_with_every_quiz_answer(question):
    result = asyncio.run(scam_detector.analyze(quiz_analysis_text(question)))
    assert verdict_for_score(result["risk_score"]) == question["answer"]


def test_quiz_questions_hide_answers(client: TestClient):
    response = client.get("/api/v1/quiz/questions?count=5")
    assert response.status_code == 200
    questions = response.json()["data"]
    assert len(questions) == 5 and len({q["id"] for q in questions}) == 5
    assert all("answer" not in q and "lesson" not in q for q in questions)


def test_quiz_answer_checks_guess(client: TestClient):
    right = client.post("/api/v1/quiz/answer", json={"question_id": "q03", "guess": "SCAM"}).json()["data"]
    assert right["correct"] is True and right["answer"] == "SCAM" and right["red_flags"]
    wrong = client.post("/api/v1/quiz/answer", json={"question_id": "q02", "guess": "SCAM"}).json()["data"]
    assert wrong["correct"] is False and wrong["answer"] == "SAFE"
    assert client.post("/api/v1/quiz/answer", json={"question_id": "nope", "guess": "SAFE"}).status_code == 404


def test_shortener_is_not_reported_as_impersonation(client: TestClient):
    data = client.post("/api/v1/analyze/message", json={"message": "SBI KYC update: http://bit.ly/3xYz12"}).json()["data"]
    assert "RULE_SENDER_DOMAIN_MISMATCH" not in {i["rule_id"] for i in data["indicators"]}
    assert "SHORTENER" in {f["code"] for f in data["link_xray"][0]["flags"]}
