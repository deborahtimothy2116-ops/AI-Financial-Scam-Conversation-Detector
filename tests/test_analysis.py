"""Tests for Text Analysis and Scam Detection API Endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.utils.constants import ScamCategory, RiskLevel


def test_upi_qr_scam_detection(client: TestClient, auth_headers):
    """Test detecting reverse QR code payment scam."""
    payload = {
        "text": "Hello sir, I have scanned your OLX ad. Please open your Google Pay and scan this QR code to receive Rs 15,000 credit in your account immediately.",
    }
    response = client.post("/api/v1/analysis/text", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["is_scam"] is True
    assert data["scam_category"] == ScamCategory.UPI_QR_SCAM.value
    assert data["risk_level"] in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]
    assert data["risk_score"] >= 75.0
    assert len(data["indicators"]) >= 1
    assert "QR" in data["category_title"]
    assert len(data["recommendations"]) >= 1
    assert len(data["helplines"]) >= 1


def test_kyc_phishing_scam_detection(client: TestClient):
    """Test detecting bank KYC expiry phishing text (Guest mode)."""
    payload = {
        "text": "Dear Customer, your HDFC bank account will be blocked today within 24 hours due to expired PAN KYC. Click here immediately to update: http://hdfc-kyc-update.xyz/login",
    }
    response = client.post("/api/v1/analysis/text", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["is_scam"] is True
    assert data["scam_category"] == ScamCategory.PHISHING_CREDENTIAL_HARVESTING.value
    assert data["risk_score"] >= 65.0
    assert len(data["extracted_entities"]["urls"]) >= 1
    assert len(data["extracted_entities"]["suspicious_shorteners"]) >= 0


def test_remote_access_otp_theft(client: TestClient):
    """Test detecting AnyDesk/TeamViewer remote access scam."""
    payload = {
        "text": "I am calling from bank technical support. To get your refund of Rs 4000, please download AnyDesk app from play store and share the 6-digit OTP code sent to your mobile.",
    }
    response = client.post("/api/v1/analysis/text", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["is_scam"] is True
    assert data["scam_category"] == ScamCategory.OTP_REMOTE_ACCESS_SCAM.value
    assert data["risk_level"] == RiskLevel.CRITICAL.value
    assert data["risk_score"] >= 85.0
    assert any("anydesk" in t.lower() for t in data["extracted_entities"]["remote_access_tools"])



def test_job_offer_task_fraud(client: TestClient):
    """Test detecting part-time job/YouTube task scam."""
    payload = {
        "text": "Part time work from home opportunity! Like YouTube videos and rate hotels to earn Rs 5000 daily income. Pay Rs 2000 prepaid task deposit to unlock VIP commission.",
    }
    response = client.post("/api/v1/analysis/text", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["is_scam"] is True
    assert data["scam_category"] == ScamCategory.JOB_OFFER_TASK_FRAUD.value
    assert data["risk_score"] >= 65.0


def test_crypto_ponzi_scam(client: TestClient):
    """Test detecting guaranteed profit crypto scheme."""
    payload = {
        "text": "Guaranteed 100% daily profit! Double your money in 24 hours with our VIP crypto trading bot. Deposit USDT to wallet 0x71C7656EC7ab88b098defB751B7401B5f6d8976F now.",
    }
    response = client.post("/api/v1/analysis/text", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["is_scam"] is True
    assert data["scam_category"] == ScamCategory.INVESTMENT_CRYPTO_PONZI.value
    assert len(data["extracted_entities"]["crypto_wallets"]) >= 1


def test_lottery_prize_scam(client: TestClient):
    """Test detecting fake lottery/lucky draw scam."""
    payload = {
        "text": "Congratulations! You won 25 Lakh in KBC Jio Lucky Draw 2026. To claim your lottery prize money, contact manager and pay Rs 12,500 customs tax and processing fee.",
    }
    response = client.post("/api/v1/analysis/text", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["is_scam"] is True
    assert data["scam_category"] == ScamCategory.LOTTERY_PRIZE_SCAM.value
    assert data["risk_score"] >= 65.0


def test_normal_safe_conversation(client: TestClient):
    """Test evaluating a normal, harmless message returns SAFE."""
    payload = {
        "text": "Hi Mom, what time is dinner ready tonight? I will pick up some fresh bread on my way back from work.",
    }
    response = client.post("/api/v1/analysis/text", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["is_scam"] is False
    assert data["scam_category"] == ScamCategory.SAFE_NORMAL_CONVERSATION.value
    assert data["risk_level"] == RiskLevel.SAFE.value
    assert data["risk_score"] < 40.0


def test_language_detection_and_override(client: TestClient):
    """Test language detection and explicit language override."""
    # Auto-detection
    payload_auto = {
        "text": "Aapka account block ho jayega turant paise bhejo aur OTP share karo.",
    }
    resp1 = client.post("/api/v1/analysis/text", json=payload_auto)
    assert resp1.status_code == 200
    assert resp1.json()["data"]["detected_language"] in ["hinglish", "hi", "en"]

    # Explicit override
    payload_override = {
        "text": "Su cuenta bancaria ha sido bloqueada. Ingrese su PIN para desbloquear.",
        "language": "es",
    }
    resp2 = client.post("/api/v1/analysis/text", json=payload_override)
    assert resp2.status_code == 200
    assert resp2.json()["data"]["detected_language"] == "es"


def test_analysis_get_by_id(client: TestClient, auth_headers):
    """Test retrieving a previously stored analysis record by ID."""
    # Create analysis
    create_resp = client.post(
        "/api/v1/analysis/text",
        json={"text": "URGENT: Police warrant issued. Pay fine to avoid arrest."},
        headers=auth_headers,
    )
    analysis_id = create_resp.json()["data"]["id"]

    # Fetch by ID
    get_resp = client.get(f"/api/v1/analysis/{analysis_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()["data"]
    assert data["id"] == analysis_id
    assert "warrant" in data["raw_text"].lower()


def test_analysis_not_found(client: TestClient):
    """Test fetching a non-existent analysis ID returns 404."""
    response = client.get("/api/v1/analysis/non-existent-uuid-12345")
    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_get_categories_metadata(client: TestClient):
    """Test getting educational metadata on all scam categories."""
    response = client.get("/api/v1/analysis/categories/metadata")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 10
    categories = [c["category"] for c in data]
    assert ScamCategory.UPI_QR_SCAM.value in categories
    assert ScamCategory.LOTTERY_PRIZE_SCAM.value in categories


def test_submit_analysis_feedback(client: TestClient, auth_headers):
    """Test submitting user accuracy evaluation for a scan."""
    # Create scan
    scan_resp = client.post(
        "/api/v1/analysis/text",
        json={"text": "Test message for accuracy evaluation"},
        headers=auth_headers,
    )
    analysis_id = scan_resp.json()["data"]["id"]

    # Submit feedback
    feedback_payload = {
        "is_accurate": True,
        "user_feedback_text": "Correctly caught the scan pattern.",
        "user_corrected_category": ScamCategory.SAFE_NORMAL_CONVERSATION.value,
    }
    fb_resp = client.post(f"/api/v1/analysis/{analysis_id}/feedback", json=feedback_payload)
    assert fb_resp.status_code == 200
    fb_data = fb_resp.json()["data"]
    assert fb_data["analysis_id"] == analysis_id
    assert fb_data["is_accurate"] is True


def test_text_input_validation_empty(client: TestClient):
    """Test sending empty text fails validation."""
    response = client.post("/api/v1/analysis/text", json={"text": "   "})
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_demo_example_1_fake_kyc(client: TestClient):
    """Demo Example 1: Urgent Bank Account Block / Fake KYC."""
    payload = {
        "message": "URGENT! Your bank account will be blocked today. Send ₹2,000 to complete KYC immediately.",
        "language": "auto",
    }
    resp = client.post("/api/v1/analyze/message", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["success"] is True
    data = res["data"]
    assert data["risk"]["score"] >= 60.0
    assert data["risk"]["level"] in ["HIGH", "CRITICAL"]
    assert data["scam"]["potential_scam"] is True
    assert "KYC" in data["scam"]["category_label"] or "Impersonation" in data["scam"]["category_label"] or "PHISHING" in str(data["scam"]["category"]).upper()
    assert len(data["indicators"]) >= 1
    assert len(data["recommendations"]) >= 1


def test_demo_example_2_lottery_prize_scam(client: TestClient):
    """Demo Example 2: Lottery Prize Fee Scam."""
    payload = {
        "message": "Congratulations! You have won ₹5,00,000. Pay ₹2,000 processing fee to claim your prize.",
        "language": "auto",
    }
    resp = client.post("/api/v1/analyze/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["risk"]["score"] >= 60.0
    assert data["scam"]["potential_scam"] is True
    assert "LOTTERY" in str(data["scam"]["category"]).upper() or "PRIZE" in str(data["scam"]["category_label"]).upper()


def test_demo_example_3_investment_scam(client: TestClient):
    """Demo Example 3: Guaranteed Profit Investment Scam."""
    payload = {
        "message": "Guaranteed 30% profit every week. Invest ₹10,000 now.",
        "language": "auto",
    }
    resp = client.post("/api/v1/analyze/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["risk"]["score"] >= 60.0
    assert data["scam"]["potential_scam"] is True
    assert "INVESTMENT" in str(data["scam"]["category"]).upper() or "INVEST" in str(data["scam"]["category_label"]).upper()


def test_demo_example_4_safe_meeting_notes(client: TestClient):
    """Demo Example 4: Normal safe message."""
    payload = {
        "message": "Your friend sent the meeting notes. See you tomorrow.",
        "language": "auto",
    }
    resp = client.post("/api/v1/analyze/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["risk"]["score"] < 30.0
    assert data["scam"]["potential_scam"] is False
    assert "No major scam indicators detected" in data["explanation"]


def test_demo_example_5_tamil_fake_kyc(client: TestClient):
    """Demo Example 5: Tamil Bank Block Scam."""
    payload = {
        "message": "உங்கள் வங்கி கணக்கு இன்று முடக்கப்படும். KYC update செய்ய உடனே ₹2000 அனுப்பவும்.",
        "language": "auto",
    }
    resp = client.post("/api/v1/analyze/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["language"]["code"] == "ta"
    assert data["risk"]["score"] >= 60.0
    assert data["scam"]["potential_scam"] is True



def test_suspicious_message_never_labelled_safe(client: TestClient):
    """A message scoring MEDIUM+ must not carry the safe-conversation category."""
    response = client.post(
        "/api/v1/analyze/message",
        json={"message": "Pay ₹5000 now to claim prize urgent OTP"},
    )
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["is_scam"] is True
    assert data["risk_level"] != RiskLevel.SAFE.value
    assert data["scam_category"] != ScamCategory.SAFE_NORMAL_CONVERSATION.value
