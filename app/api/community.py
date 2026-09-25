"""Community scam reports: check a number, UPI ID, website or email before paying, and report scammers."""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_analysis_repo, get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.db.session import get_db
from app.models.user import User
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.common import APIResponse
from app.services.community_service import (
    STRONG_REPORT_THRESHOLD,
    InvalidIdentifier,
    ScamReportRepository,
    extract_identifiers,
    is_reportable_domain,
    normalize_identifier,
)
from app.services.link_xray import _official_brand
from app.services.pause_check import build_lookup_pause
from app.utils.constants import ScamCategory

router = APIRouter(prefix="/community", tags=["Community Scam Reports"])


class LookupResult(BaseModel):
    query: str
    identifier_type: str
    identifier: str
    status: str  # official | no_reports | reported | strongly_reported
    report_count: int
    categories: Dict[str, int] = {}
    first_reported: Optional[datetime] = None
    last_reported: Optional[datetime] = None
    official_brand: Optional[str] = None
    advice: str
    pause: Optional[dict] = None


class ReportRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=255)
    scam_category: Optional[ScamCategory] = None
    note: Optional[str] = Field(None, max_length=500)


class ReportResult(BaseModel):
    identifier_type: str
    identifier: str
    created: bool
    report_count: int


def _advice(status: str, count: int, brand: Optional[str]) -> str:
    if status == "official":
        return f"This is an official {brand} domain. Still type the address yourself rather than following links in messages."
    if status == "strongly_reported":
        return (f"Reported by {count} ScamShield users as used in scams. Do not pay, share details or reply. "
                "If you already paid, call 1930 immediately.")
    if status == "reported":
        return (f"Reported by {count} ScamShield user{'s' if count != 1 else ''}. Reports are unverified, so treat it "
                "with caution and confirm the person's identity through a channel you already trust before paying.")
    return ("No community reports yet. That doesn't prove it's safe: scammers change numbers and UPI IDs often, "
            "so still verify before paying a stranger.")


@router.get("/lookup", response_model=APIResponse[LookupResult])
def lookup_identifier(q: str = Query(..., min_length=3, max_length=255), db: Session = Depends(get_db)):
    """Check whether a phone number, UPI ID, website or email has been reported by other users."""
    try:
        kind, value = normalize_identifier(q)
    except InvalidIdentifier as exc:
        raise ValidationError(str(exc))

    brand = _official_brand(value) if kind == "domain" else None
    summary = ScamReportRepository(db).summary(value)
    count = summary["report_count"]
    if brand:
        status = "official"
    elif count >= STRONG_REPORT_THRESHOLD:
        status = "strongly_reported"
    elif count:
        status = "reported"
    else:
        status = "no_reports"
    return APIResponse(
        message="Lookup complete",
        data=LookupResult(query=q, identifier_type=kind, identifier=value, status=status,
                          official_brand=brand.upper() if brand else None,
                          advice=_advice(status, count, brand.upper() if brand else None),
                          pause=build_lookup_pause(value, count) if status == "strongly_reported" else None,
                          **summary),
    )


def _report_one(repo: ScamReportRepository, kind: str, value: str, user: User,
                category: Optional[str], note: Optional[str], analysis_id: Optional[str] = None) -> ReportResult:
    if kind == "domain" and not is_reportable_domain(value):
        raise ValidationError(f"'{value}' is an official or shared service domain and can't be reported.")
    _, created = repo.add_report(kind, value, user.id, scam_category=category, note=note, analysis_id=analysis_id)
    return ReportResult(identifier_type=kind, identifier=value, created=created,
                        report_count=repo.summary(value)["report_count"])


@router.post("/reports", response_model=APIResponse[ReportResult])
def report_identifier(payload: ReportRequest, current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """Report a phone number, UPI ID, website or email used by a scammer (login required)."""
    try:
        kind, value = normalize_identifier(payload.identifier)
    except InvalidIdentifier as exc:
        raise ValidationError(str(exc))
    result = _report_one(ScamReportRepository(db), kind, value, current_user,
                         payload.scam_category.value if payload.scam_category else None, payload.note)
    return APIResponse(message="Thank you, your report helps protect others." if result.created
                       else "You have already reported this.", data=result)


@router.post("/reports/from-analysis/{analysis_id}", response_model=APIResponse[List[ReportResult]])
def report_from_analysis(analysis_id: str, current_user: User = Depends(get_current_user),
                         analysis_repo: AnalysisRepository = Depends(get_analysis_repo)):
    """Report every scammer identifier found in one of your scans (login required)."""
    analysis = analysis_repo.get_by_id(analysis_id)
    if not analysis:
        raise NotFoundError("Analysis")
    if analysis.user_id not in (None, current_user.id):
        raise ForbiddenError("You can only report from your own scans.")

    repo = ScamReportRepository(analysis_repo.db)
    results = [
        _report_one(repo, kind, value, current_user, analysis.scam_category, None, analysis_id=analysis.id)
        for kind, value in extract_identifiers(analysis.raw_text)
    ]
    if not results:
        raise ValidationError("No phone numbers, UPI IDs, websites or emails to report were found in this message.")
    return APIResponse(message=f"Reported {len(results)} detail(s). Thank you for protecting others.", data=results)
