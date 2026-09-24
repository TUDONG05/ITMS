from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ai import AIConversation
    from app.models.evaluation import Evaluation, InternshipRequest
    from app.models.internship import Internship, InternshipMember
    from app.models.notification import Notification, NotificationRead
    from app.models.roadmap import Roadmap
    from app.models.task import Task, TaskComment, TaskSubmission


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('ADMIN','MENTOR','INTERN')", name="ck_users_role"),
        CheckConstraint("status IN ('ACTIVE','LOCKED','INACTIVE')", name="ck_users_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="INTERN")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    created_internships: Mapped[list[Internship]] = relationship(
        "Internship", back_populates="creator", foreign_keys="Internship.created_by"
    )
    created_roadmaps: Mapped[list[Roadmap]] = relationship(
        "Roadmap", back_populates="creator", foreign_keys="Roadmap.created_by"
    )
    intern_memberships: Mapped[list[InternshipMember]] = relationship(
        "InternshipMember", back_populates="intern", foreign_keys="InternshipMember.intern_id"
    )
    mentor_memberships: Mapped[list[InternshipMember]] = relationship(
        "InternshipMember", back_populates="mentor", foreign_keys="InternshipMember.mentor_id"
    )
    created_tasks: Mapped[list[Task]] = relationship(
        "Task", back_populates="creator", foreign_keys="Task.created_by"
    )
    reviewed_submissions: Mapped[list[TaskSubmission]] = relationship(
        "TaskSubmission", back_populates="reviewer", foreign_keys="TaskSubmission.reviewed_by"
    )
    task_comments: Mapped[list[TaskComment]] = relationship("TaskComment", back_populates="user")
    evaluations_given: Mapped[list[Evaluation]] = relationship(
        "Evaluation", back_populates="mentor", foreign_keys="Evaluation.mentor_id"
    )
    requests_made: Mapped[list[InternshipRequest]] = relationship(
        "InternshipRequest",
        back_populates="requester",
        foreign_keys="InternshipRequest.requested_by",
    )
    requests_reviewed: Mapped[list[InternshipRequest]] = relationship(
        "InternshipRequest",
        back_populates="reviewer",
        foreign_keys="InternshipRequest.reviewed_by",
    )
    created_notifications: Mapped[list[Notification]] = relationship(
        "Notification",
        back_populates="creator",
        foreign_keys="Notification.created_by",
    )
    notification_reads: Mapped[list[NotificationRead]] = relationship(
        "NotificationRead", back_populates="user"
    )
    ai_conversations: Mapped[list[AIConversation]] = relationship(
        "AIConversation", back_populates="user"
    )
