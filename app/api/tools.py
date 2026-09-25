"""Live call check and payment proof checker."""

from typing import Dict, List, Optional

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from app.core.exceptions import ValidationError
from app.schemas.common import APIResponse
from app.services.call_check import QUESTIONS, assess_call
from app.services.ocr_service import ocr_service
from app.services.payment_proof import check_payment_proof
from app.utils.validators import validate_image_upload

router = APIRouter(tags=["Call & Payment Checks"])


class CallQuestion(BaseModel):
    id: str
    text: str


class CallAnswers(BaseModel):
    answers: Dict[str, bool]


class CallAssessment(BaseModel):
    verdict: str
    score: int
    headline: str
    scam_type: Optional[str] = None
    reasons: List[dict]
    say_this: str
    do_now: List[str]
    answered_yes: List[str]


class PaymentProofResult(BaseModel):
    status: str
    headline: str
    flags: List[dict]
    found: Dict[str, List[str]]
    verify_steps: List[str]
    text: str


@router.get("/call-check/questions", response_model=APIResponse[List[CallQuestion]])
def get_call_questions():
    """Yes/no questions to assess a phone or video call in progress."""
    return APIResponse(message="Call check questions", data=[CallQuestion(id=q["id"], text=q["text"]) for q in QUESTIONS])


@router.post("/call-check/assess", response_model=APIResponse[CallAssessment])
def assess_call_endpoint(payload: CallAnswers):
    """Assess a call from the yes/no answers."""
    return APIResponse(message="Call assessed", data=CallAssessment(**assess_call(payload.answers)))


@router.post("/payment-proof/check", response_model=APIResponse[PaymentProofResult])
async def check_payment_proof_endpoint(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    expected_amount: Optional[float] = Form(None),
):
    """Check a payment screenshot (or its pasted text) for signs it is fake, pending or reused."""
    if file is not None and file.filename:
        image_bytes, _, _ = await validate_image_upload(file)
        text, _ = await ocr_service.extract_text(image_bytes)
    if not text or not text.strip():
        raise ValidationError("Upload the payment screenshot or paste its text.")
    if expected_amount is not None and expected_amount <= 0:
        expected_amount = None
    return APIResponse(message="Payment proof checked", data=PaymentProofResult(**check_payment_proof(text, expected_amount)))
