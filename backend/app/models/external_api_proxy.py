from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ExternalApiProxy(TimestampMixin, Base):
    __tablename__ = "extended_external_api_proxies"

    proxy_uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
