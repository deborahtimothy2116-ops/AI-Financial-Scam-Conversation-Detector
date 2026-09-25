"""Initial database migration for users, analyses, indicators, and feedback.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-09-25 08:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. Create analyses table
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("input_source", sa.String(length=32), nullable=False, server_default="TEXT"),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("cleaned_text", sa.Text(), nullable=False),
        sa.Column("detected_language", sa.String(length=32), nullable=False, server_default="en"),
        sa.Column("language_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("scam_category", sa.String(length=64), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("is_scam", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("recommendations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("extracted_entities_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("llm_provider_used", sa.String(length=64), nullable=False, server_default="rule_based"),
        sa.Column("processing_time_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analyses_id"), "analyses", ["id"], unique=False)
    op.create_index(op.f("ix_analyses_user_id"), "analyses", ["user_id"], unique=False)
    op.create_index(op.f("ix_analyses_scam_category"), "analyses", ["scam_category"], unique=False)
    op.create_index(op.f("ix_analyses_risk_score"), "analyses", ["risk_score"], unique=False)
    op.create_index(op.f("ix_analyses_risk_level"), "analyses", ["risk_level"], unique=False)
    op.create_index(op.f("ix_analyses_is_scam"), "analyses", ["is_scam"], unique=False)

    # 3. Create indicators table
    op.create_table(
        "indicators",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("analysis_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("rule_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_indicators_id"), "indicators", ["id"], unique=False)
    op.create_index(op.f("ix_indicators_analysis_id"), "indicators", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_indicators_severity"), "indicators", ["severity"], unique=False)

    # 4. Create feedbacks table
    op.create_table(
        "feedbacks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("analysis_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("is_accurate", sa.Boolean(), nullable=False),
        sa.Column("user_feedback_text", sa.Text(), nullable=True),
        sa.Column("user_corrected_category", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feedbacks_id"), "feedbacks", ["id"], unique=False)
    op.create_index(op.f("ix_feedbacks_analysis_id"), "feedbacks", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_feedbacks_user_id"), "feedbacks", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("feedbacks")
    op.drop_table("indicators")
    op.drop_table("analyses")
    op.drop_table("users")
