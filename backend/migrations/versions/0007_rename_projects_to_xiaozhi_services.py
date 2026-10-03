"""rename digital human projects to xiaozhi middleware services

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


SERVICE_COLUMNS = (
    "id, service_code, service_name, title, subtitle, questions, "
    "voice_wakeup_enabled, wake_word, wake_listening_texts, "
    "wake_requirement_count, published, qa_table_id, llm_model_id, created_at, "
    "updated_at"
)


def _create_xiaozhi_tables() -> None:
    options = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }
    op.create_table(
        "extended_xiaozhi_services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service_code", sa.String(length=64), nullable=False),
        sa.Column("service_name", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subtitle", sa.String(length=255), nullable=True),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("voice_wakeup_enabled", sa.Boolean(), nullable=False),
        sa.Column("wake_word", sa.String(length=255), nullable=True),
        sa.Column("wake_listening_texts", sa.JSON(), nullable=False),
        sa.Column("wake_requirement_count", sa.Integer(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("qa_table_id", sa.Integer(), nullable=True),
        sa.Column("llm_model_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["qa_table_id"],
            ["extended_qa_tables.id"],
            name="fk_extended_xiaozhi_services_qa_table",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["llm_model_id"],
            ["extended_llm_models.id"],
            name="fk_extended_xiaozhi_services_llm_model",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_code", name="uq_extended_xiaozhi_service_code"),
        **options,
    )
    op.create_index(
        "ix_extended_xiaozhi_services_qa_table_id",
        "extended_xiaozhi_services",
        ["qa_table_id"],
    )
    op.create_index(
        "ix_extended_xiaozhi_services_llm_model_id",
        "extended_xiaozhi_services",
        ["llm_model_id"],
    )
    op.create_table(
        "extended_xiaozhi_service_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("slot", sa.String(length=64), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("etag", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["extended_xiaozhi_services.id"],
            name="fk_extended_xiaozhi_service_asset_service",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "object_key", name="uq_extended_xiaozhi_service_asset_object_key"
        ),
        sa.UniqueConstraint(
            "service_id", "slot", name="uq_extended_xiaozhi_service_asset_slot"
        ),
        **options,
    )
    op.create_index(
        "ix_extended_xiaozhi_service_assets_service_id",
        "extended_xiaozhi_service_assets",
        ["service_id"],
    )


def upgrade() -> None:
    _create_xiaozhi_tables()
    bind = op.get_bind()
    bind.execute(
        sa.text(
            f"INSERT INTO extended_xiaozhi_services ({SERVICE_COLUMNS}) "
            "SELECT id, project_code, project_name, title, subtitle, questions, "
            "voice_wakeup_enabled, wake_word, wake_listening_texts, "
            "wake_requirement_count, published, qa_table_id, llm_model_id, "
            "created_at, updated_at FROM extended_digital_human_projects"
        )
    )
    bind.execute(
        sa.text(
            "INSERT INTO extended_xiaozhi_service_assets "
            "(id, service_id, slot, object_key, original_filename, content_type, "
            "size_bytes, etag, created_at, updated_at) "
            "SELECT id, project_id, slot, object_key, original_filename, content_type, "
            "size_bytes, etag, created_at, updated_at FROM extended_project_assets"
        )
    )
    op.drop_constraint(
        "fk_extended_device_mapping_project",
        "extended_device_name_mappings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_extended_device_mapping_project",
        "extended_device_name_mappings",
        type_="unique",
    )
    with op.batch_alter_table(
        "extended_device_name_mappings", recreate="always"
    ) as batch_op:
        batch_op.alter_column(
            "project_id",
            new_column_name="service_id",
            existing_type=sa.Integer(),
            existing_nullable=True,
        )
    op.create_foreign_key(
        "fk_extended_device_mapping_xiaozhi_service",
        "extended_device_name_mappings",
        "extended_xiaozhi_services",
        ["service_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_extended_device_mapping_xiaozhi_service",
        "extended_device_name_mappings",
        ["service_id"],
    )
    op.drop_table("extended_project_assets")
    op.drop_table("extended_digital_human_projects")


def _create_legacy_project_tables() -> None:
    options = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }
    op.create_table(
        "extended_digital_human_projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_code", sa.String(length=64), nullable=False),
        sa.Column("project_name", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subtitle", sa.String(length=255), nullable=True),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("voice_wakeup_enabled", sa.Boolean(), nullable=False),
        sa.Column("wake_word", sa.String(length=255), nullable=True),
        sa.Column("wake_listening_texts", sa.JSON(), nullable=False),
        sa.Column("wake_requirement_count", sa.Integer(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("qa_table_id", sa.Integer(), nullable=True),
        sa.Column("llm_base_url", sa.String(length=512), nullable=True),
        sa.Column("llm_model", sa.String(length=128), nullable=True),
        sa.Column("llm_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("llm_provider", sa.String(length=32), nullable=False),
        sa.Column("llm_mode", sa.String(length=32), nullable=True),
        sa.Column("llm_model_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["qa_table_id"],
            ["extended_qa_tables.id"],
            name="fk_extended_digital_human_projects_qa_table",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["llm_model_id"],
            ["extended_llm_models.id"],
            name="fk_extended_digital_human_projects_llm_model",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_code"),
        **options,
    )
    op.create_index(
        "ix_extended_digital_human_projects_qa_table_id",
        "extended_digital_human_projects",
        ["qa_table_id"],
    )
    op.create_index(
        "ix_extended_digital_human_projects_llm_model_id",
        "extended_digital_human_projects",
        ["llm_model_id"],
    )
    op.create_table(
        "extended_project_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("slot", sa.String(length=64), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("etag", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["extended_digital_human_projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
        sa.UniqueConstraint(
            "project_id", "slot", name="uq_extended_project_asset_slot"
        ),
        **options,
    )
    op.create_index(
        "ix_extended_project_assets_project",
        "extended_project_assets",
        ["project_id"],
    )


def downgrade() -> None:
    _create_legacy_project_tables()
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO extended_digital_human_projects "
            "(id, project_code, project_name, title, subtitle, questions, "
            "voice_wakeup_enabled, wake_word, wake_listening_texts, "
            "wake_requirement_count, published, qa_table_id, llm_base_url, "
            "llm_model, llm_api_key_encrypted, llm_provider, llm_mode, llm_model_id, "
            "created_at, updated_at) "
            "SELECT id, service_code, service_name, title, subtitle, questions, "
            "voice_wakeup_enabled, wake_word, wake_listening_texts, "
            "wake_requirement_count, published, qa_table_id, NULL, NULL, NULL, "
            "COALESCE((SELECT provider FROM extended_llm_models "
            "WHERE extended_llm_models.id = extended_xiaozhi_services.llm_model_id), "
            "'openai'), NULL, llm_model_id, created_at, updated_at "
            "FROM extended_xiaozhi_services"
        )
    )
    bind.execute(
        sa.text(
            "INSERT INTO extended_project_assets "
            "(id, project_id, slot, object_key, original_filename, content_type, "
            "size_bytes, etag, created_at, updated_at) "
            "SELECT id, service_id, slot, object_key, original_filename, content_type, "
            "size_bytes, etag, created_at, updated_at "
            "FROM extended_xiaozhi_service_assets"
        )
    )
    op.drop_constraint(
        "fk_extended_device_mapping_xiaozhi_service",
        "extended_device_name_mappings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_extended_device_mapping_xiaozhi_service",
        "extended_device_name_mappings",
        type_="unique",
    )
    with op.batch_alter_table(
        "extended_device_name_mappings", recreate="always"
    ) as batch_op:
        batch_op.alter_column(
            "service_id",
            new_column_name="project_id",
            existing_type=sa.Integer(),
            existing_nullable=True,
        )
    op.create_foreign_key(
        "fk_extended_device_mapping_project",
        "extended_device_name_mappings",
        "extended_digital_human_projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_extended_device_mapping_project",
        "extended_device_name_mappings",
        ["project_id"],
    )
    op.drop_table("extended_xiaozhi_service_assets")
    op.drop_table("extended_xiaozhi_services")
