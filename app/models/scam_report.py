"""Community scam report: a phone number, UPI ID, website or email that a user reported as used by scammers."""

from sqlalchemy import Column, ForeignKey, String, Text, UniqueConstraint
from app.db.session import Base
from app.models.base import TimestampMixin, generate_uuid


class ScamReport(Base, TimestampMixin):
    __tablename__ = "scam_reports"
    # One report per user per identifier, so a single account can't inflate a count.
    __table_args__ = (UniqueConstraint("identifier", "reporter_user_id", name="uq_scam_report_identifier_reporter"),)

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    identifier_type = Column(String(16), nullable=False)  # phone | upi | domain | email
    identifier = Column(String(255), nullable=False, index=True)  # normalised value
    scam_category = Column(String(64), nullable=True)
    note = Column(Text, nullable=True)
    reporter_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True)

    def __repr__(self) -> str:
        return f"<ScamReport {self.identifier_type}:{self.identifier}>"
