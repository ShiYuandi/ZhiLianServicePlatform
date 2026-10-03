from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class AITask(TimestampMixin, Base):
    """前端 AI 请求的持久化任务记录。输入和图片结果本体保存在对象存储。"""

    __tablename__ = "extended_ai_tasks"
    __table_args__ = (
        UniqueConstraint("service_id", "task_type", "idempotency_key", name="uq_extended_ai_task_idempotency"),
        Index("ix_extended_ai_task_claim", "status", "lease_expires_at", "created_at"),
        Index("ix_extended_ai_task_service_created", "service_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("extended_frontend_ai_services.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    task_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    model_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    input_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    result_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    service = relationship("FrontendAIService")


__all__ = ["AITask"]
