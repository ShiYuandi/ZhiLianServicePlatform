"""create durable frontend AI tasks"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    options = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}
    op.create_table(
        "extended_ai_tasks",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.String(128), nullable=True),
        sa.Column("model_code", sa.String(64), nullable=True),
        sa.Column("provider", sa.String(32), nullable=True),
        sa.Column("model_snapshot", sa.JSON(), nullable=True),
        sa.Column("input_object_key", sa.String(512), nullable=True),
        sa.Column("result_object_key", sa.String(512), nullable=True),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("worker_id", sa.String(128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["extended_frontend_ai_services.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_id", "task_type", "idempotency_key", name="uq_extended_ai_task_idempotency"),
        **options,
    )
    op.create_index("ix_extended_ai_tasks_service_id", "extended_ai_tasks", ["service_id"])
    op.create_index("ix_extended_ai_tasks_status", "extended_ai_tasks", ["status"])
    op.create_index("ix_extended_ai_task_claim", "extended_ai_tasks", ["status", "lease_expires_at", "created_at"])


def downgrade() -> None:
    op.drop_table("extended_ai_tasks")
