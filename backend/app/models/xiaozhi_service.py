from __future__ import annotations

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class XiaozhiMiddlewareService(TimestampMixin, Base):
    __tablename__ = "extended_xiaozhi_services"
    __table_args__ = (
        UniqueConstraint("service_code", name="uq_extended_xiaozhi_service_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_code: Mapped[str] = mapped_column(String(64), nullable=False)
    service_name: Mapped[str] = mapped_column(String(128), nullable=False)
    digital_human_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    voice_wakeup_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    wake_word: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wake_listening_texts: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    wake_requirement_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_reply_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    default_reply_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qa_table_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("extended_qa_tables.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    llm_model_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("extended_llm_models.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    device_mapping: Mapped["DeviceMapping | None"] = relationship(
        back_populates="service",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    assets: Mapped[list["XiaozhiServiceAsset"]] = relationship(
        back_populates="service",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    qa_table: Mapped["QaTable | None"] = relationship(back_populates="xiaozhi_services")
    llm_model_config: Mapped["LLMModel | None"] = relationship(
        back_populates="xiaozhi_services"
    )

    def asset_map(self) -> dict[str, "XiaozhiServiceAsset"]:
        return {asset.slot: asset for asset in self.assets}


from app.models.device_mapping import DeviceMapping  # noqa: E402  # isort:skip
from app.models.xiaozhi_service_asset import XiaozhiServiceAsset  # noqa: E402  # isort:skip
from app.models.qa import QaTable  # noqa: E402  # isort:skip
from app.models.llm_model import LLMModel  # noqa: E402  # isort:skip

__all__ = ["XiaozhiMiddlewareService"]
