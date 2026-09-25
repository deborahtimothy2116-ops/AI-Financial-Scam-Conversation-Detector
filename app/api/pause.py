"""Record what people chose when paused before a risky payment, and report the totals."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.pause_event import PauseEvent
from app.schemas.common import APIResponse

router = APIRouter(prefix="/pause", tags=["Pause Before You Pay"])


class PauseEventRequest(BaseModel):
    source: Literal["scan", "lookup"]
    outcome: Literal["stopped", "continued", "already_paid"]
    analysis_id: Optional[str] = None


class PauseStats(BaseModel):
    paused: int
    stopped: int
    continued: int
    already_paid: int


def _stats(db: Session) -> PauseStats:
    counts = dict(db.query(PauseEvent.outcome, func.count(PauseEvent.id)).group_by(PauseEvent.outcome).all())
    stopped, continued, paid = counts.get("stopped", 0), counts.get("continued", 0), counts.get("already_paid", 0)
    return PauseStats(paused=stopped + continued + paid, stopped=stopped, continued=continued, already_paid=paid)


@router.post("/events", response_model=APIResponse[PauseStats])
def record_pause_event(payload: PauseEventRequest, db: Session = Depends(get_db)):
    """Record the choice made on a pause screen (anonymous)."""
    analysis_id = payload.analysis_id if payload.analysis_id and db.get(Analysis, payload.analysis_id) else None
    db.add(PauseEvent(source=payload.source, outcome=payload.outcome, analysis_id=analysis_id))
    db.commit()
    return APIResponse(message="Recorded", data=_stats(db))


@router.get("/stats", response_model=APIResponse[PauseStats])
def get_pause_stats(db: Session = Depends(get_db)):
    """How many risky payments were paused, and how people responded."""
    return APIResponse(message="Pause statistics", data=_stats(db))
