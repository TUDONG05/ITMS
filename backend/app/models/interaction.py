from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    __tablename__ = "thong_bao"
    __table_args__ = (
        CheckConstraint(
            "doi_tuong_nhan IN ('ALL', 'ROLE', 'USER')", name="ck_notifications_target_type"
        ),
        Index("ix_notifications_created_by", "nguoi_tao_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column("tieu_de", String(255), nullable=False)
    content: Mapped[str] = mapped_column("noi_dung", Text, nullable=False)
    target_type: Mapped[str] = mapped_column("doi_tuong_nhan", String(20), nullable=False)
    target_data: Mapped[list[Any] | None] = mapped_column(
        "du_lieu_nguoi_nhan", JSONB, nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        "nguoi_tao_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class NotificationRead(Base):
    __tablename__ = "luot_doc_thong_bao"
    __table_args__ = (Index("ix_notification_reads_user_id", "nguoi_dung_id"),)
    notification_id: Mapped[uuid.UUID] = mapped_column(
        "thong_bao_id",
        UUID(as_uuid=True),
        ForeignKey("thong_bao.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        "nguoi_dung_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="CASCADE"),
        primary_key=True,
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
