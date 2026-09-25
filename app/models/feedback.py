"""User feedback database model for model evaluation & accuracy reporting."""

from sqlalchemy import Column, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import TimestampMixin, generate_uuid


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedbacks"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    is_accurate = Column(Boolean, nullable=False)
    user_feedback_text = Column(Text, nullable=True)
    user_corrected_category = Column(String(64), nullable=True)

    # Relationships
    analysis = relationship("Analysis", back_populates="feedback")
    user = relationship("User", back_populates="feedbacks")

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} analysis_id={self.analysis_id} is_accurate={self.is_accurate}>"
