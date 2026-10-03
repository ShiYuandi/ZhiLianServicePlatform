from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class LLMModel(TimestampMixin, Base):
    __tablename__ = "extended_llm_models"
    __table_args__ = (
        UniqueConstraint("model_code", name="uq_extended_llm_model_code"),
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

    openai_config: Mapped["LLMOpenAIConfig | None"] = relationship(
        back_populates="model", uselist=False, cascade="all, delete-orphan"
    )
    dify_config: Mapped["LLMDifyConfig | None"] = relationship(
        back_populates="model", uselist=False, cascade="all, delete-orphan"
    )
    xiaozhi_services: Mapped[list["XiaozhiMiddlewareService"]] = relationship(
        back_populates="llm_model_config"
    )


class LLMOpenAIConfig(Base):
    __tablename__ = "extended_llm_openai_configs"

    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extended_llm_models.id", ondelete="CASCADE"),
        primary_key=True,
    )
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    upstream_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)

    model: Mapped[LLMModel] = relationship(back_populates="openai_config")


class LLMDifyConfig(Base):
    __tablename__ = "extended_llm_dify_configs"

    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extended_llm_models.id", ondelete="CASCADE"),
        primary_key=True,
    )
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)

    model: Mapped[LLMModel] = relationship(back_populates="dify_config")


from app.models.xiaozhi_service import XiaozhiMiddlewareService  # noqa: E402  # isort:skip

__all__ = ["LLMModel", "LLMOpenAIConfig", "LLMDifyConfig"]
