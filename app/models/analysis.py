"""Analysis record database model."""

import json
from typing import Any, Dict, List
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import TimestampMixin, generate_uuid


class Analysis(Base, TimestampMixin):
    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    input_source = Column(String(32), default="TEXT", nullable=False)  # TEXT or IMAGE_OCR
    raw_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=False)

    detected_language = Column(String(32), default="en", nullable=False)
    language_confidence = Column(Float, default=1.0, nullable=False)

    scam_category = Column(String(64), nullable=False, index=True)
    risk_score = Column(Float, nullable=False, index=True)  # 0 to 100
    risk_level = Column(String(32), nullable=False, index=True)  # SAFE, LOW, MEDIUM, HIGH, CRITICAL
    is_scam = Column(Boolean, default=False, nullable=False, index=True)

    explanation = Column(Text, nullable=False)
    recommendations_json = Column(Text, default="[]", nullable=False)
    extracted_entities_json = Column(Text, default="{}", nullable=False)

    llm_provider_used = Column(String(64), default="rule_based", nullable=False)
    processing_time_ms = Column(Float, default=0.0, nullable=False)

    ai_score = Column(Float, nullable=True, default=0.0)
    rule_score = Column(Float, nullable=True, default=0.0)
    analysis_mode = Column(String(64), default="ai_plus_rules", nullable=False)

    # Relationships
    user = relationship("User", back_populates="analyses")
    indicators = relationship(
        "Indicator",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="desc(Indicator.confidence)",
    )
    recommendation_records = relationship(
        "Recommendation",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    feedback = relationship(
        "Feedback",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def recommendations(self) -> List[str]:
        try:
            return json.loads(self.recommendations_json)
        except Exception:
            return []

    @recommendations.setter
    def recommendations(self, val: List[str]) -> None:
        self.recommendations_json = json.dumps(val)

    @property
    def extracted_entities(self) -> Dict[str, Any]:
        try:
            return json.loads(self.extracted_entities_json)
        except Exception:
            return {}

    @extracted_entities.setter
    def extracted_entities(self, val: Dict[str, Any]) -> None:
        self.extracted_entities_json = json.dumps(val)

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} category={self.scam_category} score={self.risk_score}>"
