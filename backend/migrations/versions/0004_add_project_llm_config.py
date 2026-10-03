"""add per-project OpenAI-compatible LLM configuration

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extended_digital_human_projects",
        sa.Column("llm_base_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "extended_digital_human_projects",
        sa.Column("llm_model", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "extended_digital_human_projects",
        sa.Column("llm_api_key_encrypted", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("extended_digital_human_projects", "llm_api_key_encrypted")
    op.drop_column("extended_digital_human_projects", "llm_model")
    op.drop_column("extended_digital_human_projects", "llm_base_url")
