"""bind digital human projects to reusable QA tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extended_digital_human_projects",
        sa.Column("qa_table_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_extended_digital_human_projects_qa_table_id",
        "extended_digital_human_projects",
        ["qa_table_id"],
    )
    op.create_foreign_key(
        "fk_extended_digital_human_projects_qa_table",
        "extended_digital_human_projects",
        "extended_qa_tables",
        ["qa_table_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_extended_digital_human_projects_qa_table",
        "extended_digital_human_projects",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_extended_digital_human_projects_qa_table_id",
        table_name="extended_digital_human_projects",
    )
    op.drop_column("extended_digital_human_projects", "qa_table_id")
