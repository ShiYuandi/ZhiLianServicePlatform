"""add digital human projects and project assets

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-25
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_code"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
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
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "ix_extended_project_assets_project", "extended_project_assets", ["project_id"]
    )

    with op.batch_alter_table(
        "extended_device_name_mappings", recreate="always"
    ) as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, name, enabled FROM extended_device_name_mappings ORDER BY id"
        )
    ).mappings()
    now = datetime.now(timezone.utc)
    for row in rows:
        project_code = f"legacy-{row['id']}"
        bind.execute(
            sa.text(
                "INSERT INTO extended_digital_human_projects "
                "(project_code, project_name, title, subtitle, questions, "
                "voice_wakeup_enabled, wake_word, wake_listening_texts, "
                "wake_requirement_count, published, created_at, updated_at) "
                "VALUES (:code, :name, :title, :subtitle, :questions, :voice, "
                ":wake_word, :listening, :count, :published, :created, :updated)"
            ),
            {
                "code": project_code,
                "name": row["name"],
                "title": row["name"],
                "subtitle": None,
                "questions": "[]",
                "voice": False,
                "wake_word": None,
                "listening": "[]",
                "count": 0,
                "published": False,
                "created": now,
                "updated": now,
            },
        )
        project_id = bind.execute(
            sa.text(
                "SELECT id FROM extended_digital_human_projects "
                "WHERE project_code = :code"
            ),
            {"code": project_code},
        ).scalar_one()
        bind.execute(
            sa.text(
                "UPDATE extended_device_name_mappings SET project_id = :project_id "
                "WHERE id = :mapping_id"
            ),
            {"project_id": project_id, "mapping_id": row["id"]},
        )

    with op.batch_alter_table(
        "extended_device_name_mappings", recreate="always"
    ) as batch_op:
        batch_op.create_foreign_key(
            "fk_extended_device_mapping_project",
            "extended_digital_human_projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_extended_device_mapping_project", ["project_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "extended_device_name_mappings", recreate="always"
    ) as batch_op:
        batch_op.drop_constraint("uq_extended_device_mapping_project", type_="unique")
        batch_op.drop_constraint(
            "fk_extended_device_mapping_project", type_="foreignkey"
        )
        batch_op.drop_column("project_id")
    op.drop_index(
        "ix_extended_project_assets_project", table_name="extended_project_assets"
    )
    op.drop_table("extended_project_assets")
    op.drop_table("extended_digital_human_projects")
