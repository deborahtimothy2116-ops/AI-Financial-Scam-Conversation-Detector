"""'I've been scammed' emergency mode: golden-hour steps and a complaint draft."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.schemas.common import APIResponse
from app.services.emergency_service import INCIDENT_TYPES, build_complaint, emergency_steps

router = APIRouter(prefix="/emergency", tags=["Emergency Response"])

IncidentType = Literal[tuple(INCIDENT_TYPES)]


class EmergencyGuide(BaseModel):
    incident_type: str
    incident_label: str
    incident_types: Dict[str, str]
    steps: List[dict]


class ComplaintRequest(BaseModel):
    incident_type: IncidentType
    amount_lost: Optional[float] = Field(None, ge=0, le=1e10)
    incident_datetime: Optional[datetime] = None
    payment_method: Optional[str] = Field(None, max_length=100)
    transaction_ids: List[str] = Field(default_factory=list, max_length=20)
    complainant_name: Optional[str] = Field(None, max_length=200)
    bank_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=5000)
    message_text: Optional[str] = Field(None, max_length=20000)
    scam_type: Optional[str] = Field(None, max_length=200)


class ComplaintDraft(BaseModel):
    incident_type: str
    incident_label: str
    draft_text: str
    evidence: Dict[str, List[str]]
    where_to_file: List[dict]


@router.get("/guide", response_model=APIResponse[EmergencyGuide])
def get_emergency_guide(incident_type: IncidentType = Query("upi_payment")):
    """Step-by-step actions for the first hour and the following days, tailored to what happened."""
    return APIResponse(
        message="Emergency steps",
        data=EmergencyGuide(incident_type=incident_type, incident_label=INCIDENT_TYPES[incident_type],
                            incident_types=INCIDENT_TYPES, steps=emergency_steps(incident_type)),
    )


@router.post("/complaint-draft", response_model=APIResponse[ComplaintDraft])
def create_complaint_draft(payload: ComplaintRequest):
    """Generate a complaint for 1930 / cybercrime.gov.in / your bank, pre-filled with evidence from the message."""
    return APIResponse(message="Complaint draft ready", data=ComplaintDraft(**build_complaint(**payload.model_dump())))
