from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class FrontendAIService(TimestampMixin, Base):
    __tablename__ = "extended_frontend_ai_services"
    __table_args__ = (
        UniqueConstraint("service_code", name="uq_extended_frontend_ai_service_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_name: Mapped[str] = mapped_column(String(128), nullable=False)
    service_code: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    api_key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    api_key_suffix: Mapped[str] = mapped_column(String(4), nullable=False)
    api_key_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    rate_limit_per_minute: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False
    )
    max_inflight_tasks: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    allowed_origins: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)

    speech_binding: Mapped["FrontendAIServiceSpeechBinding | None"] = relationship(
        back_populates="service", uselist=False, cascade="all, delete-orphan"
    )
    image_binding: Mapped["FrontendAIServiceImageBinding | None"] = relationship(
        back_populates="service", uselist=False, cascade="all, delete-orphan"
    )


class FrontendAIServiceSpeechBinding(Base):
    __tablename__ = "extended_frontend_ai_service_speech_bindings"

    service_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extended_frontend_ai_services.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extended_speech_recognition_models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    service: Mapped[FrontendAIService] = relationship(back_populates="speech_binding")
    model: Mapped["SpeechRecognitionModel"] = relationship(
        back_populates="frontend_service_bindings"
    )


class FrontendAIServiceImageBinding(Base):
    __tablename__ = "extended_frontend_ai_service_image_bindings"

    service_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extended_frontend_ai_services.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extended_image_generation_models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    service: Mapped[FrontendAIService] = relationship(back_populates="image_binding")
    model: Mapped["ImageGenerationModel"] = relationship(
        back_populates="frontend_service_bindings"
    )


from app.models.image_model import ImageGenerationModel  # noqa: E402  # isort:skip
from app.models.speech_model import SpeechRecognitionModel  # noqa: E402  # isort:skip

__all__ = [
    "FrontendAIService",
    "FrontendAIServiceSpeechBinding",
    "FrontendAIServiceImageBinding",
]
