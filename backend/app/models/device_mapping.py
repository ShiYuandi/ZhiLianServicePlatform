from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.xiaozhi_service import XiaozhiMiddlewareService


class DeviceMapping(TimestampMixin, Base):
    __tablename__ = "extended_device_name_mappings"
    __table_args__ = (
        UniqueConstraint(
            "service_id", name="uq_extended_device_mapping_xiaozhi_service"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    agent_id: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    service_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("extended_xiaozhi_services.id", ondelete="CASCADE"),
        nullable=True,
    )
    service: Mapped["XiaozhiMiddlewareService | None"] = relationship(
        back_populates="device_mapping"
    )
