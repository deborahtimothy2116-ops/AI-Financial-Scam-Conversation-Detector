"""What people did when ScamShield paused them before a risky payment."""

from sqlalchemy import Column, ForeignKey, String
from app.db.session import Base
from app.models.base import TimestampMixin, generate_uuid


class PauseEvent(Base, TimestampMixin):
    __tablename__ = "pause_events"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    source = Column(String(16), nullable=False)   # scan | lookup
    outcome = Column(String(16), nullable=False)  # stopped | continued | already_paid
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True)
