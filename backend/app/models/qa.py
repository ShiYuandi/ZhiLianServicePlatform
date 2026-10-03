from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.xiaozhi_service import XiaozhiMiddlewareService


class QaTable(TimestampMixin, Base):
    __tablename__ = "extended_qa_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    items: Mapped[list["QaItem"]] = relationship(
        back_populates="table", cascade="all, delete-orphan", passive_deletes=True
    )
    xiaozhi_services: Mapped[list["XiaozhiMiddlewareService"]] = relationship(
        back_populates="qa_table"
    )


class QaItem(TimestampMixin, Base):
    __tablename__ = "extended_qa_items"
    __table_args__ = (
        UniqueConstraint(
            "table_id", "question_fingerprint", name="uq_extended_qa_item_question"
        ),
        Index("ix_extended_qa_items_table_sort", "table_id", "sort_order", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("extended_qa_tables.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_question: Mapped[str] = mapped_column(Text, nullable=False)
    question_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    table: Mapped[QaTable] = relationship(back_populates="items")
