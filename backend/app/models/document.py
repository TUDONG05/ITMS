from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.roadmap import LearningContent

DOCUMENT_FILE_FORMATS = (
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "md",
    "csv",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "mp4",
    "webm",
    "mp3",
    "wav",
    "zip",
)


content_documents = Table(
    "learning_content_documents",
    Base.metadata,
    Column(
        "content_id",
        UUID(as_uuid=True),
        ForeignKey("noi_dung_dao_tao.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("document_library.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Index("ix_content_documents_document_id", "document_id"),
)


class Document(Base):
    __tablename__ = "document_library"
    __table_args__ = (
        CheckConstraint(
            "format IN (" + ",".join(repr(value) for value in DOCUMENT_FILE_FORMATS) + ")",
            name="ck_documents_file_format",
        ),
        CheckConstraint("format = lower(format)", name="ck_documents_format_lower"),
        CheckConstraint("size_bytes IS NULL OR size_bytes >= 0", name="ck_documents_size"),
        CheckConstraint(
            "jsonb_typeof(positions) = 'array' AND positions <@ "
            '\'["BACKEND","FRONTEND","FULLSTACK","AI","BA","OTHER"]\'::jsonb',
            name="ck_documents_positions",
        ),
        Index("ix_documents_positions", "positions", postgresql_using="gin"),
        Index("ix_documents_format", "format"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    positions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nguoi_dung.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    contents: Mapped[list[LearningContent]] = relationship(
        "LearningContent",
        secondary=content_documents,
        back_populates="documents",
        passive_deletes=True,
    )
