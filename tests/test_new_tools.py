"""Tests for the call check, payment proof checker, multilingual detection, share target and benchmark."""

import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.schemas.analysis import verdict_for_score
from app.services.call_check import assess_call
from app.services.highlighter import find_highlights
from app.services.payment_proof import check_payment_proof
from app.services.scam_detector import scam_detector
from benchmark.evaluate import DATA, load, summarize

TODAY = date(2026, 9, 25)


def verdict(message: str) -> str:
    return verdict_for_score(asyncio.run(scam_detector.analyze(message))["risk_score"])


# --- Call check -------------------------------------------------------------

def test_call_questions_endpoint(client: TestClient):
    questions = client.get("/api/v1/call-check/questions").json()["data"]
    assert len(questions) == 10 and {"otp_pin", "secrecy", "authority"} <= {q["id"] for q in questions}


def test_digital_arrest_call_is_scam(client: TestClient):
    r = client.post("/api/v1/call-check/assess", json={"answers": {"authority": True, "threat": True, "video_uniform": True}}).json()["data"]
    assert r["verdict"] == "SCAM"
    assert r["scam_type"] == "Fake police / 'digital arrest' call"
    assert any("digital arrest" in step for step in r["do_now"])


@pytest.mark.parametrize("decisive", ["otp_pin", "remote_app", "secrecy", "pay_transfer"])
def test_any_decisive_answer_means_scam(decisive):
    assert assess_call({decisive: True})["verdict"] == "SCAM"


def test_ordinary_call_is_safe():
    r = assess_call({"bank_company": True, "they_called": True, "otp_pin": False})
    assert r["verdict"] == "SAFE" and r["scam_type"] is None


# --- Payment proof ----------------------------------------------------------

GOOD = "Payment Successful ₹1,500 Paid to Ravi Stores 25 Sep 2026, 10:42 am UPI Ref No 412345678901"


def flag_titles(text, amount=None):
    return {f["title"] for f in check_payment_proof(text, amount, today=TODAY)["flags"]}


def test_clean_payment_screenshot_is_never_called_genuine():
    r = check_payment_proof(GOOD, 1500, today=TODAY)
    assert r["status"] == "no_obvious_flags" and "not proof" in r["headline"]
    assert r["found"]["reference_numbers"] == ["412345678901"]
    assert any("412345678901" in step for step in r["verify_steps"])


@pytest.mark.parametrize(
    "text, amount, expected",
    [
        (GOOD.replace("Successful", "Pending"), 1500, "Payment not completed"),
        (GOOD, 15000, "Amount doesn't match"),
        (GOOD.replace("25 Sep", "12 Sep"), 1500, "Old payment screenshot"),
        (GOOD.replace("25 Sep", "28 Sep"), 1500, "Date is in the future"),
        ("Fake Payment - for entertainment only ₹20,000 Paid 25 Sep 2026", None, "Made with a fake-payment app"),
        ("Payment request from Rahul ₹999 Approve to pay", None, "Payment not completed"),
        ("Paid ₹1,500 to Ravi Stores on 25/09/2026", 1500, "No UPI reference number (UTR)"),
    ],
)
def test_payment_red_flags(text, amount, expected):
    assert expected in flag_titles(text, amount)


def test_payment_proof_endpoint_requires_input(client: TestClient):
    assert client.post("/api/v1/payment-proof/check", data={}).status_code == 422
    r = client.post("/api/v1/payment-proof/check", data={"text": GOOD, "expected_amount": "999"}).json()["data"]
    assert r["status"] == "red_flags"


# --- Multilingual -----------------------------------------------------------

@pytest.mark.parametrize("message", [
    "आपका बैंक खाता आज बंद हो जाएगा। केवाईसी के लिए तुरंत ओटीपी बताएं।",
    "Aapka khata band ho jayega. Turant OTP batao warna account block ho jayega.",
    "உங்கள் வங்கி கணக்கு முடக்கப்படும். உடனே ஓடிபி அனுப்பவும்.",
    "Unga account mudakkappadum. Udane 2000 anuppunga.",
])
def test_indian_language_scams_detected(message):
    assert verdict(message) == "SCAM"


@pytest.mark.parametrize("message", ["कल शाम को मिलते हैं, खाना साथ में खाएंगे।", "நாளை காலை சந்திப்போம், நன்றி!"])
def test_indian_language_normal_messages_safe(message):
    assert verdict(message) == "SAFE"


def test_native_words_are_highlighted():
    spans = find_highlights("आपका खाता बंद हो जाएगा, तुरंत ओटीपी बताएं")
    assert {"बंद हो जाएगा", "तुरंत", "ओटीपी बताएं"} <= {s["text"] for s in spans}


# --- Genuine bank messages must not be flagged -------------------------------

@pytest.mark.parametrize("message", [
    "482913 is your OTP for transaction of Rs 1,250.00 at AMAZON on HDFC Bank card XX4321. Do not share it with anyone.",
    "Use 918273 as your one time password to verify your Swiggy account. Do not share this code.",
    "Your KYC is due for periodic update. Please visit your nearest branch with ID proof. -Axis Bank",
    "Your electricity bill of Rs 1,240 is due on 30 Sep. Pay via the TNEB app or website.",
    "Dear customer, your fixed deposit of Rs 1,00,000 has matured and been credited to your savings account.",
])
def test_genuine_bank_messages_are_safe(message):
    assert verdict(message) == "SAFE"


def test_otp_in_safety_warning_is_not_highlighted():
    assert find_highlights("736521 is your OTP. Please do not share it with anyone.") == []


# --- Installable app / share target -----------------------------------------

def test_manifest_declares_share_target(client: TestClient):
    manifest = client.get("/manifest.webmanifest").json()
    assert manifest["share_target"]["action"] == "/share-target"
    assert client.get("/sw.js").headers["service-worker-allowed"] == "/"
    assert client.get("/static/icons/icon-192.png").status_code == 200


def test_share_target_fallback_redirects_text(client: TestClient):
    r = client.post("/share-target", data={"text": "Your KYC expired, pay now"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/?text=Your+KYC")


# --- Benchmark regression guard ---------------------------------------------

def test_benchmark_accuracy_does_not_regress():
    rows = []
    for item in load(DATA):
        result = asyncio.run(scam_detector.analyze(item["message"]))
        rows.append({**item, "verdict": verdict_for_score(result["risk_score"]), "score": result["risk_score"]})
    s = summarize(rows)
    assert s["detection_rate"] >= 0.95
    assert s["false_alarm_rate"] <= 0.05
