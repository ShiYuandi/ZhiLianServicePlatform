from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class SpeechRecognitionModel(TimestampMixin, Base):
    __tablename__ = "extended_speech_recognition_models"
    __table_args__ = (
        UniqueConstraint("model_code", name="uq_extended_speech_model_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_code: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    doc_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)

    baidu_config: Mapped["BaiduASRConfig | None"] = relationship(
        back_populates="model", uselist=False, cascade="all, delete-orphan"
    )
    volcengine_config: Mapped["VolcengineASRConfig | None"] = relationship(
        back_populates="model", uselist=False, cascade="all, delete-orphan"
    )
    frontend_service_bindings: Mapped[
        list["FrontendAIServiceSpeechBinding"]
    ] = relationship(back_populates="model")


class BaiduASRConfig(Base):
    __tablename__ = "extended_asr_baidu_configs"

    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extended_speech_recognition_models.id", ondelete="CASCADE"),
        primary_key=True,
    )
    app_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    dev_pid: Mapped[int] = mapped_column(Integer, default=1537, nullable=False)

    model: Mapped[SpeechRecognitionModel] = relationship(back_populates="baidu_config")


class VolcengineASRConfig(Base):
    __tablename__ = "extended_asr_volcengine_configs"

    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extended_speech_recognition_models.id", ondelete="CASCADE"),
        primary_key=True,
    )
    app_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    boosting_table_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    correct_table_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    model: Mapped[SpeechRecognitionModel] = relationship(
        back_populates="volcengine_config"
    )


__all__ = ["SpeechRecognitionModel", "BaiduASRConfig", "VolcengineASRConfig"]


from app.models.frontend_ai_service import (  # noqa: E402  # isort:skip
    FrontendAIServiceSpeechBinding,
)
