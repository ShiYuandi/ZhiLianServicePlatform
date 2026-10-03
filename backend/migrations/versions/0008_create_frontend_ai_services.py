"""create frontend AI services and typed model bindings

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    options = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }
    op.create_table(
        "extended_frontend_ai_services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service_name", sa.String(length=128), nullable=False),
        sa.Column("service_code", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False),
        sa.Column("api_key_prefix", sa.String(length=8), nullable=False),
        sa.Column("api_key_suffix", sa.String(length=4), nullable=False),
        sa.Column("api_key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "rate_limit_per_minute", sa.Integer(), nullable=False, server_default="60"
        ),
        sa.Column(
            "max_inflight_tasks", sa.Integer(), nullable=False, server_default="3"
        ),
        sa.Column("allowed_origins", sa.JSON(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "service_code", name="uq_extended_frontend_ai_service_code"
        ),
        **options,
    )
    op.create_table(
        "extended_frontend_ai_service_speech_bindings",
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["extended_frontend_ai_services.id"],
            name="fk_extended_frontend_ai_speech_binding_service",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["extended_speech_recognition_models.id"],
            name="fk_extended_frontend_ai_speech_binding_model",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("service_id"),
        **options,
    )
    op.create_index(
        "ix_extended_frontend_ai_service_speech_bindings_model_id",
        "extended_frontend_ai_service_speech_bindings",
        ["model_id"],
    )
    op.create_table(
        "extended_frontend_ai_service_image_bindings",
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["extended_frontend_ai_services.id"],
            name="fk_extended_frontend_ai_image_binding_service",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["extended_image_generation_models.id"],
            name="fk_extended_frontend_ai_image_binding_model",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("service_id"),
        **options,
    )
    op.create_index(
        "ix_extended_frontend_ai_service_image_bindings_model_id",
        "extended_frontend_ai_service_image_bindings",
        ["model_id"],
    )


def downgrade() -> None:
    op.drop_table("extended_frontend_ai_service_image_bindings")
    op.drop_table("extended_frontend_ai_service_speech_bindings")
    op.drop_table("extended_frontend_ai_services")
