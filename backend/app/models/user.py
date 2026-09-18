from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole, UserStatus

if TYPE_CHECKING:
    from app.models.exam import ExamAttempt
    from app.models.interaction import AuditLog, Feedback, Notification
    from app.models.internship import Internship, MentorAssignment
    from app.models.knowledge import Conversation, Document
    from app.models.roadmap import LearningProgress


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True), nullable=False
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", native_enum=True),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    internships: Mapped[list[Internship]] = relationship(
        "Internship", back_populates="intern", foreign_keys="Internship.intern_id"
    )
    mentor_assignments: Mapped[list[MentorAssignment]] = relationship(
        "MentorAssignment", back_populates="mentor", foreign_keys="MentorAssignment.mentor_id"
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="recipient"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="actor")
    feedbacks: Mapped[list[Feedback]] = relationship("Feedback", back_populates="sender")
    conversations: Mapped[list[Conversation]] = relationship("Conversation", back_populates="user")
    uploaded_documents: Mapped[list[Document]] = relationship("Document", back_populates="uploader")
    exam_attempts: Mapped[list[ExamAttempt]] = relationship("ExamAttempt", back_populates="intern")
    learning_progresses: Mapped[list[LearningProgress]] = relationship(
        "LearningProgress", back_populates="intern"
    )
