"""Base model and timestamp mixins."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, String
from app.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    """Provides created_at and updated_at datetime timestamps."""

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
