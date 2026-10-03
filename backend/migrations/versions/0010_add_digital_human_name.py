"""add optional digital human name to Xiaozhi middleware services"""

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"]
        for column in inspector.get_columns("extended_xiaozhi_services")
    }
    if "digital_human_name" not in columns:
        op.add_column(
            "extended_xiaozhi_services",
            sa.Column("digital_human_name", sa.String(length=128), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"]
        for column in inspector.get_columns("extended_xiaozhi_services")
    }
    if "digital_human_name" in columns:
        op.drop_column("extended_xiaozhi_services", "digital_human_name")
