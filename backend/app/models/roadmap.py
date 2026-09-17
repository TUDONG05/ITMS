from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ContentType, LearningProgressStatus, RoadmapStatus

if TYPE_CHECKING:
    from app.models.exam import Exam
    from app.models.internship import InternshipPeriod
    from app.models.user import User


class Roadmap(Base):
    __tablename__ = "roadmaps"
    __table_args__ = (Index("ix_roadmaps_period_id", "period_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("internship_periods.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RoadmapStatus] = mapped_column(
        Enum(RoadmapStatus, name="roadmap_status", native_enum=True),
        nullable=False,
        default=RoadmapStatus.DRAFT,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    period: Mapped[InternshipPeriod] = relationship("InternshipPeriod", back_populates="roadmaps")
    phases: Mapped[list[RoadmapPhase]] = relationship(
        "RoadmapPhase",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapPhase.sequence_no",
    )


class RoadmapPhase(Base):
    __tablename__ = "roadmap_phases"
    __table_args__ = (
        UniqueConstraint("roadmap_id", "sequence_no", name="uq_roadmap_phases_sequence"),
        CheckConstraint(
            "duration_days IS NULL OR duration_days > 0", name="ck_roadmap_phases_duration"
        ),
        Index("ix_roadmap_phases_roadmap_id", "roadmap_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_rule: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    roadmap: Mapped[Roadmap] = relationship("Roadmap", back_populates="phases")
    contents: Mapped[list[Content]] = relationship(
        "Content",
        back_populates="phase",
        cascade="all, delete-orphan",
        order_by="Content.sequence_no",
    )
    exams: Mapped[list[Exam]] = relationship(
        "Exam", back_populates="phase", cascade="all, delete-orphan"
    )


class Content(Base):
    __tablename__ = "contents"
    __table_args__ = (
        UniqueConstraint("phase_id", "sequence_no", name="uq_contents_sequence"),
        CheckConstraint(
            "content_type != 'TEXT' OR (content_body IS NOT NULL AND content_body != '')",
            name="ck_contents_text_body",
        ),
        Index("ix_contents_phase_id", "phase_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roadmap_phases.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="content_type", native_enum=True), nullable=False
    )
    content_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    phase: Mapped[RoadmapPhase] = relationship("RoadmapPhase", back_populates="contents")
    learning_progresses: Mapped[list[LearningProgress]] = relationship(
        "LearningProgress", back_populates="content", cascade="all, delete-orphan"
    )


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = (
        UniqueConstraint("intern_id", "content_id", name="uq_learning_progress_intern_content"),
        Index("ix_learning_progress_intern_id", "intern_id"),
        Index("ix_learning_progress_content_id", "content_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intern_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[LearningProgressStatus] = mapped_column(
        Enum(LearningProgressStatus, name="learning_progress_status", native_enum=True),
        nullable=False,
        default=LearningProgressStatus.NOT_STARTED,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    intern: Mapped[User] = relationship("User", back_populates="learning_progresses")
    content: Mapped[Content] = relationship("Content", back_populates="learning_progresses")
