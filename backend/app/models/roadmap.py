from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.internship import InternshipMember
    from app.models.quiz import Quiz
    from app.models.user import User


class Roadmap(Base):
    __tablename__ = "roadmaps"
    __table_args__ = (
        Index("ix_roadmaps_created_by", "created_by"),
        Index("ix_roadmaps_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
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
    creator: Mapped[User | None] = relationship(
        "User", back_populates="created_roadmaps", foreign_keys=[created_by]
    )
    phases: Mapped[list[Phase]] = relationship(
        "Phase",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="Phase.order_no",
    )
    members: Mapped[list[InternshipMember]] = relationship(
        "InternshipMember", back_populates="roadmap"
    )


class Phase(Base):
    __tablename__ = "phases"
    __table_args__ = (
        UniqueConstraint("roadmap_id", "order_no", name="uq_phases_order"),
        Index("ix_phases_roadmap_id", "roadmap_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
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
    roadmap: Mapped[Roadmap] = relationship("Roadmap", back_populates="phases")
    learning_contents: Mapped[list[LearningContent]] = relationship(
        "LearningContent",
        back_populates="phase",
        cascade="all, delete-orphan",
        order_by="LearningContent.order_no",
    )
    quizzes: Mapped[list[Quiz]] = relationship(
        "Quiz", back_populates="phase", cascade="all, delete-orphan"
    )


class LearningContent(Base):
    __tablename__ = "learning_contents"
    __table_args__ = (
        UniqueConstraint("phase_id", "order_no", name="uq_learning_contents_order"),
        Index("ix_learning_contents_phase_id", "phase_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("phases.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="TEXT")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
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
    phase: Mapped[Phase] = relationship("Phase", back_populates="learning_contents")
    progresses: Mapped[list[LearningProgress]] = relationship(
        "LearningProgress", back_populates="content", cascade="all, delete-orphan"
    )


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = (
        UniqueConstraint(
            "internship_member_id", "content_id", name="uq_learning_progress_member_content"
        ),
        Index("ix_learning_progress_member_id", "internship_member_id"),
        Index("ix_learning_progress_content_id", "content_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internship_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("internship_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_contents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_STARTED")
    progress_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    member: Mapped[InternshipMember] = relationship(
        "InternshipMember", back_populates="learning_progresses"
    )
    content: Mapped[LearningContent] = relationship("LearningContent", back_populates="progresses")
