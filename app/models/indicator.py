"""Indicator database model for detected scam red flags."""

from sqlalchemy import Column, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import TimestampMixin, generate_uuid


class Indicator(Base, TimestampMixin):
    __tablename__ = "indicators"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(32), nullable=False, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    confidence = Column(Float, default=1.0, nullable=False)    # 0.0 to 1.0
    snippet = Column(Text, nullable=True)                      # Suspicious text quote
    rule_id = Column(String(64), nullable=True)                # e.g. "RULE_QR_RECEIVE", "RULE_URGENT_KYC"

    # Relationships
    analysis = relationship("Analysis", back_populates="indicators")

    def __repr__(self) -> str:
        return f"<Indicator id={self.id} title={self.title} severity={self.severity}>"
