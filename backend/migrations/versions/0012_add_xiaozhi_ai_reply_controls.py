"""add AI reply toggle and default reply text to Xiaozhi middleware services"""

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {
        column["name"]
        for column in inspector.get_columns("extended_xiaozhi_services")
    }


def upgrade() -> None:
    columns = _columns()
    if "ai_reply_enabled" not in columns:
        op.add_column(
            "extended_xiaozhi_services",
            sa.Column(
                "ai_reply_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )
    if "default_reply_text" not in columns:
        op.add_column(
            "extended_xiaozhi_services",
            sa.Column("default_reply_text", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    columns = _columns()
    if "default_reply_text" in columns:
        op.drop_column("extended_xiaozhi_services", "default_reply_text")
    if "ai_reply_enabled" in columns:
        op.drop_column("extended_xiaozhi_services", "ai_reply_enabled")
