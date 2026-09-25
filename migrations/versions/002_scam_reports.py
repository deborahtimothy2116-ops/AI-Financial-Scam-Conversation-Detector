"""Add community scam_reports table.

Revision ID: 002_scam_reports
Revises: 001_initial_schema
Create Date: 2026-09-25 09:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_scam_reports"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scam_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("identifier_type", sa.String(length=16), nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("scam_category", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reporter_user_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier", "reporter_user_id", name="uq_scam_report_identifier_reporter"),
    )
    op.create_index(op.f("ix_scam_reports_id"), "scam_reports", ["id"], unique=False)
    op.create_index(op.f("ix_scam_reports_identifier"), "scam_reports", ["identifier"], unique=False)
    op.create_index(op.f("ix_scam_reports_reporter_user_id"), "scam_reports", ["reporter_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scam_reports_reporter_user_id"), table_name="scam_reports")
    op.drop_index(op.f("ix_scam_reports_identifier"), table_name="scam_reports")
    op.drop_index(op.f("ix_scam_reports_id"), table_name="scam_reports")
    op.drop_table("scam_reports")
