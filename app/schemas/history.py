"""History and dashboard summary Pydantic schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.utils.constants import ScamCategory, RiskLevel, InputSource


class HistoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    input_source: InputSource
    snippet: str
    scam_category: ScamCategory
    category_title: str
    risk_score: float
    risk_level: RiskLevel
    is_scam: bool
    detected_language: str
    indicator_count: int
    created_at: datetime


class HistoryFilterParams(BaseModel):
    page: int = 1
    page_size: int = 20
    scam_category: Optional[ScamCategory] = None
    risk_level: Optional[RiskLevel] = None
    is_scam: Optional[bool] = None
    search_query: Optional[str] = None


class HistoryStatsResponse(BaseModel):
    total_scans: int
    total_scams_flagged: int
    high_critical_count: int
    safe_conversations_count: int
    scam_prevention_rate_percent: float
    scams_by_category: Dict[str, int]
    scams_by_risk_level: Dict[str, int]
    recent_activity_count_last_7_days: int
