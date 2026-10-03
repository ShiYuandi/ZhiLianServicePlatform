from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class XiaozhiServiceAsset(TimestampMixin, Base):
    __tablename__ = "extended_xiaozhi_service_assets"
    __table_args__ = (
        UniqueConstraint(
            "service_id", "slot", name="uq_extended_xiaozhi_service_asset_slot"
        ),
        UniqueConstraint(
            "object_key", name="uq_extended_xiaozhi_service_asset_object_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("extended_xiaozhi_services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    etag: Mapped[str] = mapped_column(String(255), nullable=False)

    service: Mapped["XiaozhiMiddlewareService"] = relationship(back_populates="assets")


from app.models.xiaozhi_service import XiaozhiMiddlewareService  # noqa: E402  # isort:skip

__all__ = ["XiaozhiServiceAsset"]
