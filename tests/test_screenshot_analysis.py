"""Tests for Screenshot Upload and OCR Scam Analysis API Endpoints."""

import io
from unittest.mock import AsyncMock, patch
from PIL import Image
from fastapi.testclient import TestClient
from app.utils.constants import ScamCategory


def test_screenshot_invalid_extension(client: TestClient):
    """Test uploading a file with disallowed extension returns 400."""
    file_content = b"fake executable file content"
    files = {"file": ("malicious.exe", file_content, "application/octet-stream")}
    response = client.post("/api/v1/analysis/image", files=files)
    assert response.status_code == 400
    assert response.json()["error_code"] == "FILE_PROCESSING_ERROR"


def test_screenshot_corrupted_image(client: TestClient):
    """Test uploading corrupted image bytes returns 400."""
    corrupt_bytes = b"not an image at all"
    files = {"file": ("corrupt.png", corrupt_bytes, "image/png")}
    response = client.post("/api/v1/analysis/image", files=files)
    assert response.status_code == 400
    assert response.json()["error_code"] == "FILE_PROCESSING_ERROR"


def test_screenshot_analysis_pipeline_mocked_ocr(client: TestClient, sample_image_bytes, auth_headers):
    """Test screenshot analysis pipeline with mocked OCR text extraction."""
    mocked_ocr_text = "Dear User, scan this QR code to claim your Rs 25,000 refund into your bank account immediately."

    with patch("app.services.ocr_service.ocr_service.extract_text", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = (mocked_ocr_text, 92.5)

        files = {"file": ("chat_screenshot.png", sample_image_bytes, "image/png")}
        response = client.post("/api/v1/analysis/image", files=files, headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]

        assert data["input_source"] == "IMAGE_OCR"
        assert data["is_scam"] is True
        assert data["scam_category"] == ScamCategory.UPI_QR_SCAM.value
        assert "QR" in data["raw_text"]
        assert data["risk_score"] >= 75.0


def test_screenshot_empty_ocr_result(client: TestClient, sample_image_bytes):
    """Test when OCR cannot find any text in the image."""
    with patch("app.services.ocr_service.ocr_service.extract_text", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = ("", 0.0)

        files = {"file": ("blank_image.png", sample_image_bytes, "image/png")}
        response = client.post("/api/v1/analysis/image", files=files)
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_screenshot_without_ocr_engine_explains_setup(client: TestClient, sample_image_bytes):
    """With no OCR engine installed, the upload fails with setup instructions, not 'no readable text'."""
    from app.services.ocr_service import ocr_service

    with patch.object(ocr_service, "_winocr_available", False), patch.object(ocr_service, "_tesseract_available", False):
        files = {"file": ("chat_screenshot.png", sample_image_bytes, "image/png")}
        response = client.post("/api/v1/analyze/image", files=files)

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "OCR_ERROR"
    assert "winocr" in body["message"]
