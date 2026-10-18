from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIConversation(Base):
    __tablename__ = "hoi_thoai_ai"
    __table_args__ = (Index("ix_ai_conversations_user_id", "nguoi_dung_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "nguoi_dung_id",
        UUID(as_uuid=True),
        ForeignKey("nguoi_dung.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column("tieu_de", String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class AIMessage(Base):
    __tablename__ = "tin_nhan_ai"
    __table_args__ = (
        CheckConstraint("role IN ('USER', 'ASSISTANT')", name="ck_ai_messages_role"),
        Index("ix_ai_messages_conversation_id", "hoi_thoai_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        "hoi_thoai_id",
        UUID(as_uuid=True),
        ForeignKey("hoi_thoai_ai.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column("noi_dung", Text, nullable=False)
    citations: Mapped[list[Any] | None] = mapped_column("trich_dan", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
