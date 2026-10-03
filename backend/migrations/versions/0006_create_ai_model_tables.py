"""create reusable AI model tables and bind configured project LLMs

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-27
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

from app.core.config import get_settings
from app.core.security import (
    decrypt_secret,
    encrypt_model_credential,
)


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def _common_model_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_code", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("doc_url", sa.String(length=512), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _has_llm_configuration(row: sa.RowMapping) -> bool:
    return any(
        row.get(field)
        for field in (
            "llm_base_url",
            "llm_model",
            "llm_api_key_encrypted",
            "llm_mode",
        )
    )


def upgrade() -> None:
    table_options = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }
    op.create_table(
        "extended_llm_models",
        *_common_model_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_code", name="uq_extended_llm_model_code"),
        **table_options,
    )
    op.create_table(
        "extended_speech_recognition_models",
        *_common_model_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_code", name="uq_extended_speech_model_code"),
        **table_options,
    )
    op.create_table(
        "extended_image_generation_models",
        *_common_model_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_code", name="uq_extended_image_model_code"),
        **table_options,
    )

    op.create_table(
        "extended_llm_openai_configs",
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("upstream_model", sa.String(length=128), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("timeout_seconds", sa.Float(), nullable=False, server_default="30"),
        sa.ForeignKeyConstraint(
            ["model_id"], ["extended_llm_models.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("model_id"),
        **table_options,
    )
    op.create_table(
        "extended_llm_dify_configs",
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("timeout_seconds", sa.Float(), nullable=False, server_default="30"),
        sa.ForeignKeyConstraint(
            ["model_id"], ["extended_llm_models.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("model_id"),
        **table_options,
    )
    op.create_table(
        "extended_asr_baidu_configs",
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("app_id", sa.String(length=128), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("secret_key_encrypted", sa.Text(), nullable=True),
        sa.Column("dev_pid", sa.Integer(), nullable=False, server_default="1537"),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["extended_speech_recognition_models.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("model_id"),
        **table_options,
    )
    op.create_table(
        "extended_asr_volcengine_configs",
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("app_id", sa.String(length=128), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("boosting_table_name", sa.String(length=255), nullable=True),
        sa.Column("correct_table_name", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["extended_speech_recognition_models.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("model_id"),
        **table_options,
    )
    op.create_table(
        "extended_image_volcengine_configs",
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("api_url", sa.String(length=512), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("upstream_model", sa.String(length=128), nullable=True),
        sa.Column("default_width", sa.Integer(), nullable=False, server_default="1024"),
        sa.Column(
            "default_height", sa.Integer(), nullable=False, server_default="1024"
        ),
        sa.Column("timeout_seconds", sa.Float(), nullable=False, server_default="120"),
        sa.Column("watermark", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["extended_image_generation_models.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("model_id"),
        **table_options,
    )

    op.add_column(
        "extended_digital_human_projects",
        sa.Column("llm_model_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_extended_digital_human_projects_llm_model_id",
        "extended_digital_human_projects",
        ["llm_model_id"],
    )
    op.create_foreign_key(
        "fk_extended_digital_human_projects_llm_model",
        "extended_digital_human_projects",
        "extended_llm_models",
        ["llm_model_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    bind = op.get_bind()
    rows = list(
        bind.execute(
            sa.text(
                "SELECT id, project_code, project_name, llm_provider, llm_mode, "
                "llm_base_url, llm_model, llm_api_key_encrypted, created_at, updated_at "
                "FROM extended_digital_human_projects ORDER BY id"
            )
        ).mappings()
    )
    settings = get_settings()
    now = datetime.now(timezone.utc)
    migrated = 0
    for row in rows:
        if not _has_llm_configuration(row):
            continue
        provider = row["llm_provider"] or "openai"
        if provider not in {"openai", "dify"}:
            raise RuntimeError(f"不支持迁移的大语言模型供应器: {provider}")
        model_code = f"legacy-project-llm-{row['id']}"
        bind.execute(
            sa.text(
                "INSERT INTO extended_llm_models "
                "(model_name, model_code, provider, sort_order, doc_url, remark, "
                "enabled, archived_at, created_at, updated_at) "
                "VALUES (:name, :code, :provider, 0, NULL, :remark, :enabled, "
                "NULL, :created, :updated)"
            ),
            {
                "name": f"{row['project_name']} 大语言模型"[:128],
                "code": model_code,
                "provider": provider,
                "remark": f"由小智服务 {row['project_code']} 的原有配置迁移",
                "enabled": True,
                "created": row["created_at"] or now,
                "updated": row["updated_at"] or now,
            },
        )
        model_id = bind.execute(
            sa.text("SELECT id FROM extended_llm_models WHERE model_code = :code"),
            {"code": model_code},
        ).scalar_one()

        new_ciphertext = None
        if row["llm_api_key_encrypted"]:
            plaintext = decrypt_secret(row["llm_api_key_encrypted"], settings)
            new_ciphertext = encrypt_model_credential(plaintext, settings)
        if provider == "openai":
            bind.execute(
                sa.text(
                    "INSERT INTO extended_llm_openai_configs "
                    "(model_id, base_url, upstream_model, api_key_encrypted, timeout_seconds) "
                    "VALUES (:id, :url, :model, :key, 30)"
                ),
                {
                    "id": model_id,
                    "url": row["llm_base_url"],
                    "model": row["llm_model"],
                    "key": new_ciphertext,
                },
            )
        else:
            bind.execute(
                sa.text(
                    "INSERT INTO extended_llm_dify_configs "
                    "(model_id, base_url, mode, api_key_encrypted, timeout_seconds) "
                    "VALUES (:id, :url, :mode, :key, 30)"
                ),
                {
                    "id": model_id,
                    "url": row["llm_base_url"],
                    "mode": row["llm_mode"],
                    "key": new_ciphertext,
                },
            )
        bind.execute(
            sa.text(
                "UPDATE extended_digital_human_projects SET llm_model_id = :model_id "
                "WHERE id = :project_id"
            ),
            {"model_id": model_id, "project_id": row["id"]},
        )
        migrated += 1

    bound_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM extended_digital_human_projects "
            "WHERE llm_model_id IS NOT NULL"
        )
    ).scalar_one()
    if bound_count != migrated:
        raise RuntimeError("大语言模型迁移完整性检查失败")


def downgrade() -> None:
    op.drop_constraint(
        "fk_extended_digital_human_projects_llm_model",
        "extended_digital_human_projects",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_extended_digital_human_projects_llm_model_id",
        table_name="extended_digital_human_projects",
    )
    op.drop_column("extended_digital_human_projects", "llm_model_id")
    op.drop_table("extended_image_volcengine_configs")
    op.drop_table("extended_asr_volcengine_configs")
    op.drop_table("extended_asr_baidu_configs")
    op.drop_table("extended_llm_dify_configs")
    op.drop_table("extended_llm_openai_configs")
    op.drop_table("extended_image_generation_models")
    op.drop_table("extended_speech_recognition_models")
    op.drop_table("extended_llm_models")
