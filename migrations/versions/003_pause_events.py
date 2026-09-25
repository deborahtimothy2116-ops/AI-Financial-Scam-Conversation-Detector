"""Add pause_events table.

Revision ID: 003_pause_events
Revises: 002_scam_reports
Create Date: 2026-09-25 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_pause_events"
down_revision: Union[str, None] = "002_scam_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pause_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("analysis_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pause_events_id"), "pause_events", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pause_events_id"), table_name="pause_events")
    op.drop_table("pause_events")
