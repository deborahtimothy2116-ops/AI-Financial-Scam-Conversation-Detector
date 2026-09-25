"""Feedback repository for storing user accuracy ratings and corrections."""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.feedback import Feedback
from app.repositories.base_repository import BaseRepository
from app.schemas.feedback import FeedbackCreateRequest


class FeedbackRepository(BaseRepository[Feedback]):
    def __init__(self, db: Session):
        super().__init__(Feedback, db)

    def get_by_analysis_id(self, analysis_id: str) -> Optional[Feedback]:
        """Fetch existing feedback for an analysis record."""
        return self.db.query(Feedback).filter(Feedback.analysis_id == analysis_id).first()

    def create_or_update_feedback(
        self,
        analysis_id: str,
        feedback_in: FeedbackCreateRequest,
        user_id: Optional[str] = None,
    ) -> Feedback:
        """Create or update feedback for an analysis."""
        existing = self.get_by_analysis_id(analysis_id)
        if existing:
            existing.is_accurate = feedback_in.is_accurate
            existing.user_feedback_text = feedback_in.user_feedback_text
            existing.user_corrected_category = (
                feedback_in.user_corrected_category.value
                if feedback_in.user_corrected_category
                else None
            )
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        feedback = Feedback(
            analysis_id=analysis_id,
            user_id=user_id,
            is_accurate=feedback_in.is_accurate,
            user_feedback_text=feedback_in.user_feedback_text,
            user_corrected_category=(
                feedback_in.user_corrected_category.value
                if feedback_in.user_corrected_category
                else None
            ),
        )
        return self.create(feedback)
