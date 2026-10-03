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


class ImageGenerationModel(TimestampMixin, Base):
    __tablename__ = "extended_image_generation_models"
    __table_args__ = (
        UniqueConstraint("model_code", name="uq_extended_image_model_code"),
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

    volcengine_config: Mapped["VolcengineImageConfig | None"] = relationship(
        back_populates="model", uselist=False, cascade="all, delete-orphan"
    )
    frontend_service_bindings: Mapped[
        list["FrontendAIServiceImageBinding"]
    ] = relationship(back_populates="model")


class VolcengineImageConfig(Base):
    __tablename__ = "extended_image_volcengine_configs"

    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extended_image_generation_models.id", ondelete="CASCADE"),
        primary_key=True,
    )
    api_url: Mapped[str] = mapped_column(
        String(512),
        default="https://ark.cn-beijing.volces.com/api/v3/images/generations",
        nullable=False,
    )
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    upstream_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    default_width: Mapped[int] = mapped_column(Integer, default=1024, nullable=False)
    default_height: Mapped[int] = mapped_column(Integer, default=1024, nullable=False)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=120.0, nullable=False)
    watermark: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    model: Mapped[ImageGenerationModel] = relationship(
        back_populates="volcengine_config"
    )


__all__ = ["ImageGenerationModel", "VolcengineImageConfig"]


from app.models.frontend_ai_service import (  # noqa: E402  # isort:skip
    FrontendAIServiceImageBinding,
)
