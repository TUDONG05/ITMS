from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ChatMessageSenderType, DocumentStatus

if TYPE_CHECKING:
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_uploaded_by", "uploaded_by"),
        Index("ix_documents_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    access_scope: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", native_enum=True),
        nullable=False,
        default=DocumentStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    uploader: Mapped[User] = relationship("User", back_populates="uploaded_documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_no",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_no", name="uq_document_chunks_no"),
        Index("ix_document_chunks_document_id", "document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_no: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    vector: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    access_scope: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    document: Mapped[Document] = relationship("Document", back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="conversations")
    messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_conversation_id", "conversation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_type: Mapped[ChatMessageSenderType] = mapped_column(
        Enum(ChatMessageSenderType, name="chat_message_sender_type", native_enum=True),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")
