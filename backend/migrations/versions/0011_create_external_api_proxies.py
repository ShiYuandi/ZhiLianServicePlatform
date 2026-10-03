"""create configurable external API proxies"""

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    options = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    op.create_table(
        "extended_external_api_proxies",
        sa.Column("proxy_uuid", sa.String(length=36), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("proxy_uuid"),
        **options,
    )


def downgrade() -> None:
    op.drop_table("extended_external_api_proxies")
