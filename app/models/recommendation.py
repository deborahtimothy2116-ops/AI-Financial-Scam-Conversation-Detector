"""Recommendation database model for actionable safety guidance."""

from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import TimestampMixin, generate_uuid


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)

    priority = Column(String(32), default="high", nullable=False)  # high, medium, low
    text = Column(Text, nullable=False)

    # Relationships
    analysis = relationship("Analysis", back_populates="recommendation_records")

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} priority={self.priority}>"
