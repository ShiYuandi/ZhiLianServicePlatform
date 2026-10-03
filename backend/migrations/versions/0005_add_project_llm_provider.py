"""add project LLM provider and Dify mode

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extended_digital_human_projects",
        sa.Column("llm_provider", sa.String(length=32), nullable=False, server_default="openai"),
    )
    op.add_column(
        "extended_digital_human_projects",
        sa.Column("llm_mode", sa.String(length=32), nullable=True),
    )
    op.alter_column(
        "extended_digital_human_projects",
        "llm_provider",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("extended_digital_human_projects", "llm_mode")
    op.drop_column("extended_digital_human_projects", "llm_provider")
