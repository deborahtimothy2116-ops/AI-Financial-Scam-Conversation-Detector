"""Feedback Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.utils.constants import ScamCategory


class FeedbackCreateRequest(BaseModel):
    is_accurate: bool
    user_feedback_text: Optional[str] = None
    user_corrected_category: Optional[ScamCategory] = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    is_accurate: bool
    user_feedback_text: Optional[str] = None
    user_corrected_category: Optional[str] = None
    created_at: datetime
